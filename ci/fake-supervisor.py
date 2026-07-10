"""Minimal Home Assistant Supervisor stand-in for the add-on smoke test.

bashio reads BOTH the add-on options and the MQTT broker details from the
Supervisor API (not from /data/options.json), so this serves:

  GET /addons/self/options/config  -> the add-on options
  GET /services/mqtt               -> an anonymous broker (the smoke mosquitto)

Everything else gets a benign OK. bashio reads the ``.data`` object from each.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

OPTIONS = {
    "result": "ok",
    "data": {
        "latitude": 48.14,
        "longitude": 11.58,
        "elevation": 519,
        "timezone": "Europe/Berlin",
        "observatory_name": "Addon",
        "observation_date": "12/15/25",
        "objects": True,
        "bodies": False,
        "comets": False,
        "horizon": False,
        "alttime": False,
    },
}
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
        path = self.path.rstrip("/")
        if path.endswith("/addons/self/options/config"):
            self._send(OPTIONS)
        elif path.endswith("/services/mqtt"):
            self._send(MQTT)
        else:
            self._send(OK)

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", 80), Handler).serve_forever()
