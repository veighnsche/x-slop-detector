"""Real HTTP suite/lifecycle smoke; synthetic inputs, NOT accuracy validation."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import time

import httpx


async def run(restart_only=False):
    token = os.environ["DETECTOR_API_TOKEN"]
    expected = os.environ["DETECTOR_GPU_UUID"]
    report = {"restart_only": restart_only, "accuracy_test": False}

    def process_memory():
        pid = os.environ.get("DETECTOR_SERVER_PID")
        if pid is None:
            return None
        rows = subprocess.check_output([
            "nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory",
            "--format=csv,noheader,nounits",
        ], text=True)
        return [row.strip() for row in rows.splitlines() if row.split(",")[0].strip() == pid]

    async with httpx.AsyncClient(
        base_url=os.environ["DETECTOR_URL"],
        headers={"Authorization": f"Bearer {token}"}, timeout=150,
    ) as client:
        async def status():
            response = await client.get("/v2/status")
            response.raise_for_status()
            return response.json()

        async def wait_for(predicate, timeout=120):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                value = await status()
                if predicate(value):
                    return value
                await asyncio.sleep(0.05)
            raise AssertionError("Timed out waiting for suite state")

        def unloaded(value):
            # Optional unconfigured routes own no assets and remain unavailable.
            return all(c["state"] in ("unloaded", "unavailable") for c in value["suite"]["components"])

        async def analyze(texts):
            return await client.post("/v2/analyze", json={
                "schema_version": "2", "extraction_version": "synthetic-smoke-v1",
                "posts": [{"id": str(i), "text": text} for i, text in enumerate(texts)],
            })

        async def control(action):
            response = await client.post("/v2/control", json={"schema_version": "2", "action": action})
            assert response.status_code in (200, 202), response.text
            return response

        first = await status()
        assert unloaded(first), first
        if restart_only:
            assert first["suite"]["paused"], first
            assert (await analyze(["This is a synthetic test."])).status_code == 409
            report["restart_kept_pause"] = True
            return report

        assert not first["suite"]["paused"], first
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/v2/ready")).status_code == 503
        short = ["The train is late again. Anyone know what happened?", "A synthetic smoke test, not ground truth."]
        start = time.monotonic()
        response = await analyze(short)
        assert response.status_code == 200, response.text
        report["first_lazy_load_and_analysis_seconds"] = time.monotonic() - start
        result = response.json()
        assert [c["checker"]["id"] for c in result["results"][0]["checks"]] == [
            "tabularis", "e5", "fakespot", "fast_detect_gpt", "kgw",
        ]
        for row in result["results"]:
            assert all(check["status"] == "completed" for check in row["checks"][:4]), row
            assert row["checks"][4]["reason"] == "no_matching_configuration", row
            assert row["aggregate"]["kind"] == "no_estimate"
        report["native_synthetic_results"] = result
        loaded = await status()
        assert loaded["suite"]["verified_gpu_uuid"] == expected
        assert loaded["diagnostics_ready"] and not loaded["probability_ready"]
        report["loaded"] = loaded
        report["loaded_process_memory"] = process_memory()
        assert (await client.get("/v2/ready?mode=probability")).status_code == 503

        mixed = await analyze([short[0], "a", "test " * 1600])
        assert mixed.status_code == 200, mixed.text
        rows = mixed.json()["results"]
        assert rows[1]["checks"][3]["reason"] == "no_next_token_observations", rows[1]
        assert all(c["reason"] == "token_limit_exceeded" for c in rows[2]["checks"][:4]), rows[2]
        report["mixed_admission_passed"] = True

        timings = []
        for _ in range(3):
            start = time.monotonic()
            response = await analyze(short)
            assert response.status_code == 200
            timings.append(1000 * (time.monotonic() - start))
        report["warm_batch2_http_ms"] = timings

        # One slot, no queued analysis. At least one request must be refused.
        concurrent = await asyncio.gather(analyze(short * 8), analyze(short * 8))
        assert sorted(r.status_code for r in concurrent) == [200, 409]
        report["concurrent_statuses"] = [r.status_code for r in concurrent]

        # Manual unload latches pause while existing work retains ownership.
        task = asyncio.create_task(analyze(short * 8))
        await wait_for(lambda value: value["suite"]["busy"])
        await control("unload")
        pending = await status()
        assert pending["suite"]["paused"]
        assert (await analyze(short)).status_code == 409
        conflict = await client.post("/v2/control", json={"schema_version": "2", "action": "load"})
        assert conflict.status_code == 409
        assert (await task).status_code == 200
        released = await wait_for(lambda value: unloaded(value) and not value["suite"]["busy"])
        assert released["suite"]["device_memory"]["allocated_bytes"] == 0, released
        assert released["suite"]["device_memory"]["reserved_bytes"] == 0, released
        report["manual_release"] = released

        await control("load")
        await wait_for(lambda value: value["diagnostics_ready"])
        # Cancel a network client, then request unload. Never free under a worker.
        task = asyncio.create_task(analyze(short * 8))
        await wait_for(lambda value: value["suite"]["busy"])
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await control("unload")
        await wait_for(lambda value: unloaded(value) and not value["suite"]["busy"])
        report["cancelled_client_unload_passed"] = True

        await control("load")
        await wait_for(lambda value: value["diagnostics_ready"])
        # Test one near-limit real input; there is deliberately no silent trim.
        near = await analyze(["The train was late. " * 98])
        assert near.status_code == 200, near.text
        assert all(c["status"] == "completed" for c in near.json()["results"][0]["checks"][:4]), near.text
        report["near_limit_tokens"] = [
            c["coverage"]["input_tokens"] for c in near.json()["results"][0]["checks"][:4]
        ]
        start = time.monotonic()
        near_batch = await analyze(["The train was late. " * 98] * 16)
        assert near_batch.status_code == 200, near_batch.text
        assert all(
            check["status"] == "completed"
            for row in near_batch.json()["results"] for check in row["checks"][:4]
        ), near_batch.text
        report["batch16_near_limit_http_ms"] = 1000 * (time.monotonic() - start)
        report["after_near_limit"] = await status()
        report["after_near_limit_process_memory"] = process_memory()
        idle = await wait_for(lambda value: unloaded(value), timeout=20)
        assert not idle["suite"]["paused"]
        assert idle["suite"]["device_memory"]["allocated_bytes"] == 0
        report["idle_release"] = idle
        response = await analyze(short)
        assert response.status_code == 200, response.text
        report["idle_auto_reload_passed"] = True
        # Shared legacy API uses the same loaded suite and pauses v2 as well.
        legacy = await client.post("/v1/detect", json={"posts": [{"id": "1", "text": short[0]}]})
        assert legacy.status_code == 200 and legacy.json()["api_status"] == "legacy_diagnostics"
        await client.post("/v1/model/unload")
        assert (await status())["suite"]["paused"]
        assert (await analyze(short)).status_code == 409
        await control("load")
        await wait_for(lambda value: value["diagnostics_ready"])
        await control("unload")
        final = await wait_for(lambda value: unloaded(value) and not value["suite"]["busy"])
        assert final["suite"]["paused"]
        assert final["suite"]["device_memory"]["allocated_bytes"] == 0
        report["final"] = final
        report["released_process_memory"] = process_memory()
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart-only", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = asyncio.run(run(args.restart_only))
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result, indent=2, allow_nan=False))
