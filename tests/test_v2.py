"""Contract fixtures only. Fake tokenization/scores are not detection evidence."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
from pydantic import ValidationError

from detector_server.app import Settings, create_app
from detector_server.catalog import CHECKER_CATALOG, INITIAL_ROSTER, TABULARIS, NEO
from detector_server.v2 import UnintegratedSuite
from detector_server.contracts import (
    AnalysisResult, AnalyzeResponse, CheckEvidence, CheckerRef, CheckerSpec,
    ClassifierScore, ComponentState, Coverage, Discrepancy, NoEstimate,
    PostEvidence, ProbabilityEstimate, ProviderRoute, SuiteState, WatermarkFinding,
)

TOKEN = "test-only-token-not-for-deployment"
WATERMARK = CheckerSpec(
    checker=CheckerRef(
        id="fixture_watermark", configuration_id="synthetic-known-key-v1",
        artifact_revision="fixture-not-a-provider-key",
    ),
    kind="watermark", role="research_fixture", artifact_id="synthetic-test-only",
    license="MIT", precision="not_applicable", max_tokens=None, preprocessing="raw_text",
)


class FakeSuite:
    specs = (*INITIAL_ROSTER, WATERMARK)

    def __init__(self):
        self.calls = 0
        self.controls = []
        self.paused = False
        self.busy = False
        self.component_error = False
        self.raise_error = False
        self.corrupt = None
        self.disposition = "completed"

    def status(self):
        return SuiteState(
            configuration_id="fake-contract-suite-v1", integrated=True,
            paused=self.paused, busy=self.busy, operation="idle", configured_device="cpu",
            idle_timeout_seconds=600.0,
            components=[
                ComponentState(
                    checker_id=spec.checker.id, required=spec.kind != "watermark",
                    state="error" if self.component_error and spec == NEO else "ready",
                ) for spec in self.specs
            ],
            provider_routes=[],
        )

    async def analyze(self, request):
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("private-text-and-secret-must-not-escape")
        results = []
        for post in request.posts:
            # Deliberately fake: words are not model tokens.
            tokens = len(post.text.split())
            checks = []
            for spec in self.specs:
                coverage = Coverage(
                    characters=len(post.text), input_tokens=tokens,
                    token_limit=spec.max_tokens,
                )
                common = {"checker": spec.checker, "coverage": coverage}
                if spec.max_tokens is not None and tokens > spec.max_tokens:
                    check = CheckEvidence(
                        **common, status="unsupported", reason="token_limit_exceeded",
                    )
                elif spec.kind == "statistical" and tokens < 2:
                    check = CheckEvidence(
                        **common, status="insufficient_evidence",
                        reason="no_next_token_observations",
                    )
                elif spec.kind == "watermark":
                    check = CheckEvidence(
                        **common, status="completed",
                        output=WatermarkFinding(
                            decision="not_detected", verification_scope="known_configuration",
                            z_score=-0.3, p_value=0.6,
                        ),
                    )
                elif spec.kind == "statistical":
                    check = CheckEvidence(
                        **common, status="completed", output=Discrepancy(value=-2.5),
                    )
                else:
                    check = CheckEvidence(
                        **common, status="completed", output=ClassifierScore(value=0.7234),
                    )
                checks.append(check)
            results.append(PostEvidence(id=post.id, checks=checks))
        if self.corrupt is not None:
            return self.corrupt(results)
        return results

    async def control(self, action):
        self.controls.append(action)
        self.paused = action == "unload"
        return self.disposition


class V2ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.suite = FakeSuite()
        self.app = create_app(Settings(TOKEN, "cpu"), suite=self.suite)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def analyze(self, texts=None, **overrides):
        payload = {
            "schema_version": "2", "extraction_version": "own-text-fixture-v1",
            "posts": [
                {"id": str(i), "text": text}
                for i, text in enumerate(texts or ["two words"])
            ],
        }
        payload.update(overrides)
        return await self.client.post("/v2/analyze", json=payload)

    async def test_native_outputs_remain_distinct_without_probability(self):
        response = await self.analyze()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        AnalyzeResponse.model_validate(data)
        checks = data["results"][0]["checks"]
        self.assertEqual(checks[0]["output"]["value"], 0.7234)
        self.assertEqual(checks[3]["output"], {
            "kind": "token_probability_discrepancy", "value": -2.5,
        })
        self.assertEqual(checks[4]["output"]["decision"], "not_detected")
        self.assertEqual(checks[4]["output"]["p_value"], 0.6)
        self.assertEqual(data["results"][0]["aggregate"], {
            "kind": "no_estimate", "target_id": "substantive_llm_wording_v1",
            "reason": "no_validated_profile",
        })
        self.assertNotIn('"probability":', response.text)
        self.assertNotIn("ai_percentage", response.text)
        self.assertNotIn("two words", response.text)

    async def test_published_request_fixture_roundtrips(self):
        fixture = Path(__file__).parent / "fixtures" / "v2_request.json"
        request = json.loads(fixture.read_text())
        response = await self.client.post("/v2/analyze", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [result["id"] for result in response.json()["results"]], ["normal", "short"],
        )

    async def test_mixed_short_and_overlength_inputs_preserve_order_and_status(self):
        response = await self.analyze(["two words", "one " * 513, "Yes."])
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([result["id"] for result in results], ["0", "1", "2"])
        self.assertEqual(results[0]["checks"][3]["status"], "completed")
        self.assertEqual(results[1]["checks"][0]["reason"], "token_limit_exceeded")
        self.assertIsNone(results[1]["checks"][0]["output"])
        self.assertEqual(results[2]["checks"][3]["status"], "insufficient_evidence")
        self.assertEqual(results[2]["aggregate"]["reason"], "required_evidence_missing")
        self.assertEqual(results[2]["checks"][0]["status"], "completed")

    async def test_failed_and_missing_checks_never_become_zero(self):
        def fail(results):
            for result in results:
                for index, (status, reason) in enumerate([
                    ("unavailable", "access_pending"), ("failed", "checker_error"),
                    ("timed_out", "checker_timeout"),
                ]):
                    old = result.checks[index]
                    result.checks[index] = CheckEvidence(
                        checker=old.checker, coverage=old.coverage, status=status, reason=reason,
                    )
            return results
        self.suite.corrupt = fail
        response = await self.analyze()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["aggregate"]["reason"], "required_evidence_missing")
        for check in response.json()["results"][0]["checks"][:3]:
            self.assertIsNone(check["output"])

    async def test_authentication_precedes_body_consumption(self):
        consumed = False

        async def receive():
            nonlocal consumed
            consumed = True
            raise AssertionError("Unauthorized body consumed")

        messages = []

        async def send(message):
            messages.append(message)

        await self.app({
            "type": "http", "asgi": {"version": "3.0"}, "method": "POST",
            "path": "/v2/analyze", "headers": [], "query_string": b"",
        }, receive, send)
        self.assertFalse(consumed)
        self.assertEqual(messages[0]["status"], 401)
        self.assertEqual(self.suite.calls, 0)
        self.assertIn(b"unauthorized", messages[1]["body"])

    async def test_chunked_body_limit(self):
        async def chunks():
            for _ in range(129):
                yield b"x" * 1000
        response = await self.client.post("/v2/analyze", content=chunks())
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "body_too_large")
        self.assertEqual(self.suite.calls, 0)

    async def test_invalid_envelopes_are_sanitized_before_suite_calls(self):
        for overrides in [
            {"schema_version": "3"}, {"schema_version": 2}, {"posts": []},
            {"extraction_version": ""}, {"provider_enabled": True},
            {"posts": [{"id": "1", "text": "private"}] * 2},
            {"posts": [{"id": "1", "text": "private", "enable_provider": True}]},
            {"posts": [{"id": "1", "text": " "}]},
            {"posts": [{"id": "1", "text": "private" * 1500}]},
            {"posts": [{"id": str(i), "text": "private"} for i in range(17)]},
        ]:
            response = await self.analyze(**overrides)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(response.json()["error"]["code"], "invalid_request")
            self.assertNotIn("private", response.text)
        malformed = await self.client.post("/v2/analyze", content=b'{"private"')
        self.assertEqual(malformed.status_code, 422)
        self.assertNotIn("private", malformed.text)
        self.assertEqual(self.suite.calls, 0)

    async def test_backend_exceptions_and_invalid_outputs_are_sanitized(self):
        self.suite.raise_error = True
        with self.assertLogs("detector_server.v2", level="ERROR") as logs:
            response = await self.analyze()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text + "".join(logs.output))
        self.suite.raise_error = False
        for corrupt in [
            lambda results: [],
            lambda results: list(reversed(results)),
            lambda results: [results[0].model_copy(update={"id": "wrong"})],
            lambda results: [results[0].model_copy(update={"checks": results[0].checks[:1]})],
        ]:
            self.suite.corrupt = corrupt
            with self.assertLogs("detector_server.v2", level="ERROR"):
                response = await self.analyze(["two words", "three more words"])
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("probability", response.text)

    async def test_wrong_native_kind_or_nan_from_internal_adapter_is_rejected(self):
        def corrupt(results):
            check = results[0].checks[3]
            results[0].checks[3] = check.model_copy(update={"output": ClassifierScore(value=0.5)})
            return results
        self.suite.corrupt = corrupt
        with self.assertLogs("detector_server.v2", level="ERROR"):
            self.assertEqual((await self.analyze()).status_code, 503)

        def nan(results):
            results[0].checks[0].output.__dict__["value"] = float("nan")
            return results
        self.suite.corrupt = nan
        with self.assertLogs("detector_server.v2", level="ERROR"):
            self.assertEqual((await self.analyze()).status_code, 503)

    async def test_wrong_revision_coverage_and_duplicate_checkers_are_rejected(self):
        def revision(results):
            check = results[0].checks[0]
            wrong = check.checker.model_copy(update={"artifact_revision": "wrong"})
            results[0].checks[0] = check.model_copy(update={"checker": wrong})
            return results

        def coverage(results):
            check = results[0].checks[0]
            results[0].checks[0] = check.model_copy(
                update={"coverage": check.coverage.model_copy(update={"characters": 999})},
            )
            return results

        def duplicates(results):
            results[0].checks.append(results[0].checks[0])
            return results

        for corrupt in (revision, coverage, duplicates):
            self.suite.corrupt = corrupt
            with self.assertLogs("detector_server.v2", level="ERROR"):
                self.assertEqual((await self.analyze()).status_code, 503)

    async def test_readiness_distinguishes_models_from_probability_and_partial_load(self):
        self.assertEqual((await self.client.get("/v2/ready")).status_code, 200)
        probability = await self.client.get("/v2/ready?mode=probability")
        self.assertEqual(probability.status_code, 503)
        self.assertFalse(probability.json()["probability_ready"])
        self.assertIn("no_validated_profile", probability.json()["blockers"])
        self.suite.component_error = True
        response = await self.client.get("/v2/ready")
        self.assertEqual(response.status_code, 503)
        self.assertIn("required_components_not_ready", response.json()["blockers"])

    async def test_busy_and_paused_do_not_call_suite(self):
        self.suite.busy = True
        response = await self.analyze()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.headers["Retry-After"], "2")
        self.suite.busy = False
        self.suite.paused = True
        response = await self.analyze()
        self.assertEqual(response.json()["error"]["code"], "manually_paused")
        self.assertEqual(self.suite.calls, 0)

    async def test_control_contract_has_pending_and_completed_states(self):
        for disposition, status in [("completed", 200), ("pending", 202)]:
            self.suite.disposition = disposition
            response = await self.client.post("/v2/control", json={
                "schema_version": "2", "action": "unload",
            })
            self.assertEqual(response.status_code, status)
            self.assertTrue(response.json()["status"]["suite"]["paused"])
        await self.client.post("/v2/control", json={"schema_version": "2", "action": "load"})
        self.assertFalse(self.suite.paused)
        response = await self.client.post("/v2/control", json={
            "schema_version": "2", "action": "unload", "provider_key": "private",
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private", response.text)

    async def test_not_found_and_wrong_method_use_v2_error_contract(self):
        self.assertEqual((await self.client.get("/v2/missing")).json()["error"]["code"], "not_found")
        response = await self.client.get("/v2/analyze")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"]["code"], "method_not_allowed")
        self.assertEqual(response.headers["Allow"], "POST")


class UnintegratedApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_v2_is_honest_and_allocates_nothing(self):
        app = create_app(Settings(TOKEN, "cpu"), suite=UnintegratedSuite("cpu", 600))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
            headers={"Authorization": f"Bearer {TOKEN}"},
        ) as client:
            self.assertEqual((await client.get("/health")).status_code, 200)
            capabilities = (await client.get("/v2/capabilities")).json()
            self.assertEqual(len(capabilities["checkers"]), len(CHECKER_CATALOG))
            self.assertFalse(capabilities["limits"]["hosted_requests_enabled"])
            state = (await client.get("/v2/status")).json()
            self.assertFalse(state["suite"]["integrated"])
            self.assertIsNone(state["suite"]["verified_gpu_uuid"])
            self.assertTrue(all(not route["enabled"] for route in state["suite"]["provider_routes"]))
            self.assertEqual((await client.get("/v2/ready")).status_code, 503)
            response = await client.post("/v2/analyze", json={
                "schema_version": "2", "extraction_version": "fixture-v1",
                "posts": [{"id": "1", "text": "private original text"}],
            })
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "suite_not_integrated")
            self.assertNotIn("private", response.text)
            control = await client.post("/v2/control", json={"schema_version": "2", "action": "load"})
            self.assertEqual(control.status_code, 503)
            self.assertEqual(app.state.manager.state, "unloaded")


class ContractTests(unittest.TestCase):
    def test_native_domains_and_status_invariants(self):
        for value in (-1.0, 1.1, float("nan"), float("inf"), True, "0.5"):
            with self.assertRaises(ValidationError):
                ClassifierScore(value=value)
        self.assertEqual(Discrepancy(value=-20.0).value, -20.0)
        for value in (float("nan"), float("inf")):
            with self.assertRaises(ValidationError):
                Discrepancy(value=value)
        for fields in [
            {"status": "completed"},
            {"status": "failed", "output": ClassifierScore(value=0.4), "reason": "checker_error"},
            {"status": "timed_out", "reason": "access_pending"},
            {"status": "unavailable"},
        ]:
            with self.assertRaises(ValidationError):
                CheckEvidence(checker=TABULARIS.checker, coverage=Coverage(characters=2), **fields)
        with self.assertRaises(ValidationError):
            Coverage(characters=2, input_tokens=1, scored_tokens=2)
        with self.assertRaises(ValidationError):
            WatermarkFinding(
                decision="detected", verification_scope="provider", p_value=1.2,
            )

    def test_probability_requires_a_real_validation_implementation(self):
        aggregate = ProbabilityEstimate(
            probability=0.72, profile_id="fixture-only",
            calibration_artifact_sha256="a" * 64, validation_scope_id="fixture-only",
        )
        check = CheckEvidence(
            checker=TABULARIS.checker, status="completed", coverage=Coverage(characters=2),
            output=ClassifierScore(value=0.9),
        )
        with self.assertRaises(ValidationError):
            AnalyzeResponse(
                configuration_id="fixture", extraction_version="fixture",
                results=[AnalysisResult(id="1", checks=[check], aggregate=aggregate)],
            )
        with self.assertRaises(ValidationError):
            NoEstimate(reason="no_validated_profile", probability=0.0)
        with self.assertRaises(ValidationError):
            ProviderRoute(id="openai", access="pending", approved=True, enabled=True)

    def test_fresh_process_import_and_health_do_not_import_model_runtime(self):
        script = """
import asyncio, sys
import httpx
from detector_server.app import Settings, create_app
async def main():
    app = create_app(Settings('test-only-token-not-for-deployment', 'cpu'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test',
        headers={'Authorization': 'Bearer test-only-token-not-for-deployment'}) as client:
        for path in ['/health', '/v2/capabilities', '/v2/status', '/v2/ready']:
            await client.get(path)
    assert 'torch' not in sys.modules
    assert 'transformers' not in sys.modules
asyncio.run(main())
"""
        subprocess.run([sys.executable, "-c", script], check=True, timeout=30)

    def test_json_schema_is_serializable_and_discriminated(self):
        schema = AnalyzeResponse.model_json_schema()
        json.dumps(schema, allow_nan=False)
        self.assertEqual(
            schema["$defs"]["AnalysisResult"]["properties"]["aggregate"]["discriminator"]["propertyName"],
            "kind",
        )
