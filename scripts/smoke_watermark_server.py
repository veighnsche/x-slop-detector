"""Verify the real CPU watermark HTTP route against public synthetic fixtures."""

import argparse
import json
import os
from pathlib import Path
import time

import httpx


def run(fixtures, expectation):
    report = {"expectation": expectation, "provider_coverage": False, "accuracy_test": False}
    with httpx.Client(
        base_url=os.environ["DETECTOR_URL"],
        headers={"Authorization": "Bearer " + os.environ["DETECTOR_API_TOKEN"]},
        timeout=60,
    ) as client:
        def check(text):
            start = time.monotonic()
            response = client.post("/v2/watermarks", json={
                "schema_version": "2", "extraction_version": "synthetic-watermark-v1",
                "posts": [{"id": "fixture", "text": text}],
            })
            assert response.status_code == 200, response.text
            result = response.json()["results"][0]
            assert result["aggregate"]["kind"] == "no_estimate"
            assert len(result["checks"]) == 1
            return result["checks"][0], 1000 * (time.monotonic() - start)

        marked, ms = check(fixtures["texts"]["marked"])
        report["marked"] = marked
        report["first_request_ms"] = ms
        if expectation in ("unconfigured", "disabled"):
            assert marked["output"] is None
            assert marked["reason"] == (
                "no_matching_configuration" if expectation == "unconfigured" else "route_disabled"
            )
        else:
            assert marked["status"] == "completed", marked
            assert marked["output"]["decision"] == (
                "detected" if expectation == "marked" else "not_detected"
            ), marked
            assert marked["output"]["p_value"] is None
            assert marked["output"]["tests_performed"] == 1
            assert marked["output"]["configuration_purpose"] == "research_fixture"
            unmarked, _ = check(fixtures["texts"]["unmarked"])
            assert unmarked["status"] == "completed", unmarked
            assert unmarked["output"]["decision"] == "not_detected", unmarked
            report["unmarked_ai"] = unmarked
            short, _ = check("Yes.")
            assert short["status"] == "insufficient_evidence"
            repeated, _ = check("test " * 100)
            assert repeated["status"] == "insufficient_evidence"
            long, _ = check("test " * 1500)
            assert long["reason"] == "token_limit_exceeded"
            report["short_and_repeated_insufficient"] = True
            report["overlength_unsupported"] = True
            # Edited inputs retain their native outcome; never assert generic
            # robustness from a one-fixture edit test.
            edited, _ = check(" ".join(fixtures["texts"]["marked"].split()))
            report["whitespace_edited"] = edited
            times = [check(fixtures["texts"]["marked"])[1] for _ in range(3)]
            report["warm_verification_http_ms"] = times
        state = client.get("/v2/status").json()
        assert all(c["state"] == "unloaded" for c in state["suite"]["components"] if c["required"])
        assert state["suite"]["verified_gpu_uuid"] is None
        assert state["suite"]["device_memory"] is None
        assert all(not route["enabled"] and not route["connected"] for route in state["suite"]["provider_routes"])
        assert state["probability_ready"] is False
        report["status"] = state
        if expectation in ("marked", "wrong_key"):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                idle = client.get("/v2/status").json()
                if not idle["suite"]["busy"] and idle["suite"]["local_watermark_routes"][0]["state"] == "unloaded":
                    break
                time.sleep(0.05)
            assert idle["suite"]["local_watermark_routes"][0]["state"] == "unloaded", idle
            assert not idle["suite"]["paused"]
            reloaded, _ = check(fixtures["texts"]["marked"])
            assert reloaded["status"] == "completed", reloaded
            report["idle_release_and_lazy_reload_passed"] = True
        unload = client.post("/v2/control", json={"schema_version": "2", "action": "unload"})
        assert unload.status_code in (200, 202)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            final = client.get("/v2/status").json()
            if not final["suite"]["busy"]:
                break
            time.sleep(0.02)
        assert final["suite"]["paused"]
        assert final["suite"]["local_watermark_routes"][0]["state"] != "ready"
        assert client.post("/v2/watermarks", json={
            "schema_version": "2", "extraction_version": "fixture-v1",
            "posts": [{"id": "fixture", "text": "Yes."}],
        }).status_code == 409
        report["manual_unload_and_pause_passed"] = True
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--expectation", choices=("marked", "wrong_key", "unconfigured", "disabled"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(json.loads(args.fixtures.read_text()), args.expectation)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
