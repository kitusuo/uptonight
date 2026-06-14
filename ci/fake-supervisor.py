"""Minimal Home Assistant Supervisor stand-in for the add-on smoke test.

bashio resolves the MQTT broker via ``GET http://supervisor/services/mqtt`` and
reads the ``.data`` object. Return an anonymous broker pointing at the smoke
test's mosquitto container; everything else gets a benign OK.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

MQTT = {
    "result": "ok",
    "data": {
        "host": "mosquitto",
        "port": 1883,
        "ssl": False,
        "username": "",
        "password": "",
        "protocol": "3.1.1",
        "addon": "core_mosquitto",
    },
}
OK = {"result": "ok", "data": {}}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(MQTT if self.path.rstrip("/").endswith("/services/mqtt") else OK)

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", 80), Handler).serve_forever()
