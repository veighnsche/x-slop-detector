"""Opt-in real private-service smoke; uses public synthetic text and real models.

Reads the operator credential over SSH into memory only. Requires a quiet,
manually paused service; finishes paused/unloaded even when a check fails.
--check-idle requires a separately configured short test timeout, never changes it.
"""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://slop-detection.dimensionlab.net")
    parser.add_argument("--ssh-host", default="gpu")
    parser.add_argument("--check-idle", action="store_true")
    args = parser.parse_args()
    origin = urllib.parse.urlsplit(args.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path or origin.query or origin.fragment):
        parser.error("use an HTTPS origin without credentials, path, query or fragment")
    token = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.ssh_host, "sudo", "-n", "cat",
         "/etc/x-slop-detector/api-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    opener = urllib.request.build_opener(NoRedirect())

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(args.origin + path, headers=headers, data=data)
        with opener.open(req, timeout=120) as response:
            return json.load(response)

    def status():
        result = request("/v2/status")
        assert result["schema_version"] == "2"
        assert not result["probability_ready"]
        assert all(not r["enabled"] and not r["connected"] for r in result["suite"]["provider_routes"])
        return result

    polls = 0

    def wait(predicate, timeout):
        nonlocal polls
        end = time.monotonic() + timeout
        while True:
            result = status()  # A single 503 during cold import is a failure.
            polls += 1
            if predicate(result):
                return result
            assert not result["suite"]["last_error"], result["suite"]["last_error"]
            if time.monotonic() >= end:
                raise TimeoutError("deployment transition timed out")
            time.sleep(0.1)

    def unloaded(result):
        suite = result["suite"]
        return not suite["busy"] and all(
            c["state"] in ("unloaded", "unavailable") for c in suite["components"]
        )

    initial = status()
    assert initial["suite"]["paused"] and unloaded(initial), "refuse a service that is not quiet/paused"
    if args.check_idle:
        assert initial["suite"]["idle_timeout_seconds"] <= 15, "short test timeout must be configured separately"
    payload = {
        "schema_version": "2", "extraction_version": "deployment-synthetic-v1",
        "posts": [{"id": "synthetic", "text": (
            "This is a public synthetic deployment check. It exercises private HTTPS "
            "and native detector evidence, not authorship accuracy."
        )}],
    }
    report = {"origin": args.origin, "real_inference": True, "accuracy_claim": False}
    try:
        started = time.monotonic()
        receipt = request("/v2/control", {"schema_version": "2", "action": "load"})
        assert receipt["disposition"] in ("pending", "completed")
        ready = wait(lambda s: s["diagnostics_ready"], 120)
        assert ready["suite"]["verified_gpu_uuid"] == "GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db"
        report["cold_load_seconds"] = round(time.monotonic() - started, 3)

        def analyze():
            started = time.monotonic()
            result = request("/v2/analyze", payload)
            assert result["schema_version"] == "2"
            assert result["calibration_status"] == "not_configured"
            assert result["results"][0]["aggregate"]["kind"] == "no_estimate"
            checks = result["results"][0]["checks"]
            assert len(checks) == 5
            assert all(c["status"] == "completed" for c in checks[:4])
            assert checks[4]["status"] == "unsupported"
            assert checks[4]["reason"] == "no_matching_configuration"
            return round(time.monotonic() - started, 3)

        report["https_inference_seconds"] = analyze()
        if args.check_idle:
            expired = wait(unloaded, 30)["suite"]
            assert not expired["paused"]
            assert expired["device_memory"]["allocated_bytes"] == 0
            assert expired["device_memory"]["reserved_bytes"] == 0
            report["idle_release_then_lazy_reload_seconds"] = analyze()
    finally:
        request("/v2/control", {"schema_version": "2", "action": "unload"})
        final = wait(lambda s: s["suite"]["paused"] and unloaded(s), 60)["suite"]
        assert final["pause_persisted"]
        memory = final["device_memory"]
        assert memory is None or (memory["allocated_bytes"] == 0 and memory["reserved_bytes"] == 0)
    try:
        request("/v2/analyze", payload)
    except urllib.error.HTTPError as error:
        body = json.load(error)
        assert error.code == 409 and body["error"]["code"] == "manually_paused"
    else:
        raise AssertionError("manual pause did not block analysis")
    report.update(status_polls=polls, final_state="paused/unloaded", status_poll_errors=0)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
