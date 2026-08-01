# CBED waterfall demo

This folder is a standalone extraction of the OpenWebRX HTTP, WebSocket, GUI-to-model command, and waterfall data paths. It uses only the Python standard library.

## Run

From the repository root:

```sh
python3 -m cbed --host 127.0.0.1 --port 8073
```

Open `http://127.0.0.1:8073`, enter a rate from 1 to 30 rows per second, and press **Start**.

## Protocol

- The browser opens `/ws/` and sends the OpenWebRX-style `SERVER DE CLIENT` handshake.
- The server replies with `CLIENT DE SERVER`, then a JSON `config` message.
- The Start button sends `{"type":"start","value":{"rows_per_second":12}}`.
- Each generated FFT row is a binary WebSocket message containing byte `0x01`, followed by 1024 little-endian 32-bit floating-point dB values. This is the uncompressed FFT format used by OpenWebRX.
- One shared data source broadcasts each FFT row to every connected client. Clients joining an active stream receive configuration and current status before their first row.

Run the focused tests with:

```sh
python3 -m unittest cbed.test_datasource cbed.test_server
```