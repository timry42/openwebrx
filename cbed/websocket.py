import base64
import hashlib
import json
import struct
import threading


OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class WebSocketClosed(ConnectionError):
    pass


class WebSocketConnection:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.send_lock = threading.Lock()
        self.open = True

    @staticmethod
    def accept_key(client_key):
        digest = hashlib.sha1(
            (client_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
        ).digest()
        return base64.b64encode(digest).decode("ascii")

    def send_json(self, value):
        self.send_text(json.dumps(value, allow_nan=False, separators=(",", ":")))

    def send_text(self, value):
        self._send_frame(OPCODE_TEXT, value.encode("utf-8"))

    def send_binary(self, value):
        self._send_frame(OPCODE_BINARY, value)

    def receive(self):
        while self.open:
            first, second = self._read_exact(2)
            opcode = first & 0x0F
            length = second & 0x7F

            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]

            mask = self._read_exact(4) if second & 0x80 else None
            payload = self._read_exact(length)
            if mask:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

            if opcode == OPCODE_TEXT:
                return opcode, payload.decode("utf-8")
            if opcode == OPCODE_BINARY:
                return opcode, payload
            if opcode == OPCODE_PING:
                self._send_frame(OPCODE_PONG, payload)
                continue
            if opcode == OPCODE_PONG:
                continue
            if opcode == OPCODE_CLOSE:
                self.close()
                raise WebSocketClosed()

        raise WebSocketClosed()

    def close(self):
        if not self.open:
            return
        try:
            self._send_frame(OPCODE_CLOSE, b"")
        except (OSError, WebSocketClosed):
            pass
        self.open = False

    def _send_frame(self, opcode, payload):
        if not self.open:
            raise WebSocketClosed()

        length = len(payload)
        if length <= 125:
            header = bytes((0x80 | opcode, length))
        elif length <= 0xFFFF:
            header = bytes((0x80 | opcode, 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x80 | opcode, 127)) + struct.pack("!Q", length)

        with self.send_lock:
            try:
                self.writer.write(header + payload)
                self.writer.flush()
            except OSError as error:
                self.open = False
                raise WebSocketClosed() from error

    def _read_exact(self, length):
        value = self.reader.read(length)
        if value is None or len(value) != length:
            self.open = False
            raise WebSocketClosed()
        return value