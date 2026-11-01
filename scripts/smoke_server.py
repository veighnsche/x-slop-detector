"""Real-model API smoke test; run against an isolated test instance.

Uses DETECTOR_URL and DETECTOR_API_TOKEN from the environment. Never prints
credentials or submitted text. This changes server residency and pause state.
"""

import json
import os
import time
import urllib.error
import urllib.request


def main():
    base = os.environ.get("DETECTOR_URL", "http://127.0.0.1:8765").rstrip("/")
    token = os.environ["DETECTOR_API_TOKEN"]

    def request(path, payload=None, method="GET", expected=200):
        req = urllib.request.Request(
            base + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method=method,
        )
        try:
            response = urllib.request.urlopen(req, timeout=1800)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = json.load(response)
            assert response.code == expected, (path, response.code, body)
            return body

    print("Checking authenticated API and on-demand model loading")
    assert request("/health")["status"] == "ok"
    initial = request("/v1/model")
    assert initial["state"] == "unloaded" and not initial["paused"], (
        "Start a fresh test instance before running this test"
    )
    payload = {"posts": [
        {"id": "a", "text": "The train is late again. Anyone know what happened?"},
        {"id": "b", "text": "I tried the new coffee shop today and liked the quiet tables by the window."},
    ]}
    result = request("/v1/detect", payload, "POST")
    assert result["calibrated_for_x"] is False
    assert [p["id"] for p in result["results"]] == ["a", "b"]
    for prediction in result["results"]:
        assert 0 <= prediction["ai_score"] <= 1
        assert prediction["ai_percentage"] == round(100 * prediction["ai_score"], 1)
    print("Real inference returned valid scores; this is not an accuracy test")
    assert request("/v1/model")["state"] == "ready"
    request("/v1/model/unload", method="POST")
    assert request("/v1/model")["paused"]
    request("/v1/detect", payload, "POST", expected=409)
    request("/v1/model/load", method="POST")
    assert not request("/v1/model")["paused"]
    print("Manual unload/pause and reload passed")
    timeout = request("/v1/model")["idle_timeout_seconds"]
    assert timeout <= 15, "Use DETECTOR_IDLE_SECONDS=3 for this test"
    deadline = time.monotonic() + timeout + 10
    while request("/v1/model")["state"] != "unloaded":
        assert time.monotonic() < deadline, "Idle unload did not finish"
        time.sleep(0.5)
    request("/v1/detect", payload, "POST")
    assert request("/v1/model")["state"] == "ready"
    request("/v1/model/unload", method="POST")
    print("Idle unload and automatic reload passed; test instance left unloaded/paused")


if __name__ == "__main__":
    main()
