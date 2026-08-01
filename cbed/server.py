import argparse
import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cbed.datasource import RandomCompassSource, RandomWaterfallSource
from cbed.websocket import OPCODE_TEXT, WebSocketClosed, WebSocketConnection


LOGGER = logging.getLogger(__name__)
STATIC_DIRECTORY = Path(__file__).with_name("static")


class WaterfallApplication:
    def __init__(self):
        self.source = RandomWaterfallSource()
        self.compass_source = RandomCompassSource()

    def config_message(self):
        return {
            "type": "config",
            "value": {
                "fft_size": self.source.fft_size,
                "fft_compression": "none",
                "samp_rate": 2400000,
                "center_freq": 145000000,
                "waterfall_levels": {"min": -115, "max": -45},
                "waterfall_colors": ["#05070d", "#132d46", "#146c70", "#f4d35e", "#ee6c4d"],
            },
        }

    def handle_websocket(self, handler):
        client_key = handler.headers.get("Sec-WebSocket-Key")
        if not client_key or handler.headers.get("Upgrade", "").lower() != "websocket":
            handler.send_error(400, "Invalid WebSocket upgrade")
            return

        handler.send_response(101, "Switching Protocols")
        handler.send_header("Upgrade", "websocket")
        handler.send_header("Connection", "Upgrade")
        handler.send_header("Sec-WebSocket-Accept", WebSocketConnection.accept_key(client_key))
        handler.end_headers()

        connection = WebSocketConnection(handler.rfile, handler.wfile)
        try:
            self._websocket_loop(connection)
        except (OSError, WebSocketClosed):
            pass
        finally:
            self.source.unsubscribe(connection.send_binary)
            self.compass_source.unsubscribe(connection.send_json)
            connection.close()

    def close(self):
        self.source.stop()
        self.compass_source.stop()

    def _websocket_loop(self, connection):
        handshake_complete = False
        while connection.open:
            opcode, message = connection.receive()
            if opcode != OPCODE_TEXT:
                continue

            if not handshake_complete and message.startswith("SERVER DE CLIENT"):
                connection.send_text("CLIENT DE SERVER server=cbed version=1")
                connection.send_json(self.config_message())
                status = (
                    "Streaming {} rows/s".format(self.source.rows_per_second) if self.source.running else "Ready"
                )
                connection.send_json({"type": "status", "value": status})
                self.source.subscribe(connection.send_binary)
                self.compass_source.subscribe(connection.send_json)
                handshake_complete = True
                continue

            try:
                command = json.loads(message)
            except json.JSONDecodeError:
                connection.send_json({"type": "error", "value": "Invalid JSON command"})
                continue

            if command.get("type") == "start":
                try:
                    rows_per_second = int(command.get("value", {}).get("rows_per_second", 12))
                except (AttributeError, TypeError, ValueError):
                    connection.send_json({"type": "error", "value": "Rate must be a whole number"})
                    continue
                self.source.start(rows_per_second)
                connection.send_json(
                    {"type": "status", "value": "Streaming {} rows/s".format(self.source.rows_per_second)}
                )
            else:
                connection.send_json({"type": "error", "value": "Unknown command"})


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CBED/1"

    @property
    def application(self):
        return self.server.application

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/ws", "/ws/"):
            self.application.handle_websocket(self)
            return
        if path == "/":
            self._serve_file(STATIC_DIRECTORY / "index.html")
            return
        if path in ("/app.js", "/styles.css"):
            self._serve_file(STATIC_DIRECTORY / path[1:])
            return
        self.send_error(404, "Not Found")

    def log_message(self, message_format, *args):
        LOGGER.info("%s - %s", self.address_string(), message_format % args)

    def _serve_file(self, path):
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            self.send_error(404, "Not Found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)


class WaterfallServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, application):
        self.application = application
        super().__init__(address, RequestHandler)


def run(host="127.0.0.1", port=8073):
    application = WaterfallApplication()
    server = WaterfallServer((host, port), application)
    LOGGER.info("CBED listening on http://%s:%s", host, server.server_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        application.close()


def main():
    parser = argparse.ArgumentParser(description="Standalone OpenWebRX waterfall data-source demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8073, type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.host, args.port)


if __name__ == "__main__":
    main()
