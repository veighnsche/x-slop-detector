"""Loopback-only Chrome smoke fixture: real API/lifecycle, deliberately fake model outputs.

Not an inference entry point or deployable service. Public synthetic tests only.
"""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_suite import FakeAdapter
from detector_server.app import Settings, create_app
from detector_server.suite import LocalSuite


class DelayedFixtureAdapter(FakeAdapter):
    def load(self):
        time.sleep(0.15)
        super().load()

    def predict(self, post):
        time.sleep(0.1)
        return super().predict(post)


if __name__ == "__main__":
    scratch = Path(os.environ.get("DELTA_SCRATCH_DIR", ROOT / ".cache"))
    scratch.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(prefix="extension-fixture-", dir=scratch) as state:
        suite = LocalSuite("cpu", 30, state, adapter_factory=DelayedFixtureAdapter)
        app = create_app(Settings(os.environ["XSD_FIXTURE_TOKEN"], "cpu"), suite=suite)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)
        print(json.dumps({"port": sock.getsockname()[1]}), flush=True)
        uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False)).run(sockets=[sock])
