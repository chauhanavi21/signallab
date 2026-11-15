"""Real loopback HTTP fixture, with an isolated database and no live-app writes."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

import core
from httpkit import Server
from server import API


class BoundaryCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = core.Store(Path(self.tmp.name) / "test.sqlite") if hasattr(core, "Store") else None
        self.server = Server(0, API, Path(__file__).resolve().parents[1], self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def request(self, method, path, body=None, headers=None, raw=None):
        headers = dict(headers or {})
        if body is not None:
            raw = json.dumps(body)
            headers.setdefault("Content-Type", "application/json")
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        try:
            conn.request(method, path, raw, headers)
            response = conn.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), json.loads(data) if "application/json" in response.getheader("Content-Type", "") else data
        finally:
            conn.close()
