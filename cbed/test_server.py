import base64
import json
import os
import socket
import struct
import threading
import unittest

from cbed.server import WaterfallApplication, WaterfallServer


def read_exact(reader, size):
    value = reader.read(size)
    if len(value) != size:
        raise EOFError("WebSocket frame ended early")
    return value


def read_frame(reader):
    first, second = read_exact(reader, 2)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", read_exact(reader, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_exact(reader, 8))[0]
    return first & 0x0F, read_exact(reader, length)


def masked_text_frame(value):
    payload = value.encode("utf-8")
    mask = os.urandom(4)
    length = len(payload)
    if length <= 125:
        header = bytes((0x81, 0x80 | length))
    else:
        header = bytes((0x81, 0x80 | 126)) + struct.pack("!H", length)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return header + mask + masked


def connect_client(server_address):
    client = socket.create_connection(server_address, timeout=2)
    client.settimeout(2)
    reader = client.makefile("rb")
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        "GET /ws/ HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Key: {}\r\n\r\n".format(key)
    )
    client.sendall(request.encode("ascii"))
    if b"101 Switching Protocols" not in reader.readline():
        raise ConnectionError("WebSocket upgrade failed")
    while reader.readline() != b"\r\n":
        pass
    return client, reader


def complete_handshake(client, reader):
    client.sendall(masked_text_frame("SERVER DE CLIENT client=cbed type=receiver"))
    opcode, acknowledgement = read_frame(reader)
    if opcode != 0x1 or not acknowledgement.startswith(b"CLIENT DE SERVER"):
        raise ConnectionError("Application handshake failed")
    opcode, config_payload = read_frame(reader)
    if opcode != 0x1 or json.loads(config_payload)["type"] != "config":
        raise ConnectionError("Configuration not received")
    opcode, status_payload = read_frame(reader)
    if opcode != 0x1:
        raise ConnectionError("Status not received")
    return json.loads(status_payload)["value"]


def read_binary_frame(reader, attempts=4):
    for _ in range(attempts):
        opcode, payload = read_frame(reader)
        if opcode == 0x2:
            return payload
    return None


class WaterfallServerTest(unittest.TestCase):
    def setUp(self):
        self.application = WaterfallApplication()
        self.server = WaterfallServer(("127.0.0.1", 0), self.application)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.application.close()
        self.thread.join(timeout=2)

    def test_start_command_streams_fft_frame(self):
        client, reader = connect_client(self.server.server_address)
        complete_handshake(client, reader)

        command = json.dumps({"type": "start", "value": {"rows_per_second": 8}})
        client.sendall(masked_text_frame(command))
        binary_payload = read_binary_frame(reader)

        self.assertIsNotNone(binary_payload)
        self.assertEqual(binary_payload[0], 0x01)
        self.assertEqual(len(binary_payload), 1 + self.application.source.fft_size * 4)
        client.close()

    def test_multiple_clients_share_stream_and_late_joiners_receive_it(self):
        first_client, first_reader = connect_client(self.server.server_address)
        second_client, second_reader = connect_client(self.server.server_address)
        self.assertEqual(complete_handshake(first_client, first_reader), "Ready")
        self.assertEqual(complete_handshake(second_client, second_reader), "Ready")

        command = json.dumps({"type": "start", "value": {"rows_per_second": 8}})
        first_client.sendall(masked_text_frame(command))
        first_payload = read_binary_frame(first_reader)
        second_payload = read_binary_frame(second_reader)

        self.assertIsNotNone(first_payload)
        self.assertEqual(second_payload, first_payload)

        late_client, late_reader = connect_client(self.server.server_address)
        self.assertEqual(complete_handshake(late_client, late_reader), "Streaming 8 rows/s")
        late_payload = read_binary_frame(late_reader)
        self.assertIsNotNone(late_payload)
        self.assertEqual(late_payload[0], 0x01)

        first_client.close()
        second_client.close()
        late_client.close()


if __name__ == "__main__":
    unittest.main()