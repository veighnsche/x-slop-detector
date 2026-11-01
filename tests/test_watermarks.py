import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import weakref
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from detector_server.app import Settings, create_app
from detector_server.contracts import (
    AnalyzeRequest, CheckEvidence, ClassifierScore, Coverage, ProviderRoute, WatermarkFinding,
)
from detector_server.suite import LocalSuite
from detector_server.watermarks import (
    KgwConfiguration, KgwVerifier, ProviderPolicy, WatermarkConfiguration,
    WatermarkRoutes, read_configuration,
)

TOKEN = "test-only-token-not-for-deployment"


def request(text="Synthetic fixture text."):
    return AnalyzeRequest(
        schema_version="2", extraction_version="fixture-v1",
        posts=[{"id": "1", "text": text}],
    )


def scoped_config(**overrides):
    values = {
        "enabled": True, "applicability": "operator_scoped",
        "scope_description": "Synthetic controlled research only",
    }
    values.update(overrides)
    return KgwConfiguration(**values)


class ConfigurationTests(unittest.TestCase):
    def test_operator_scope_and_key_are_explicit_not_http_metadata(self):
        for values in [
            {"enabled": True},
            {"enabled": True, "applicability": "operator_scoped"},
            {"purpose": "known_configuration", "key_source": "public_fixture"},
            {"key_source": "environment"},
            {"key_source": "environment", "key_env": "PRIVATE_WATERMARK_KEY", "purpose": "known_configuration"},
            {"key": "private"},
            {"tokenizer": "arbitrary-model"},
            {"matching_generation_device": "cuda"},
            {"keys": [123, 456]},
        ]:
            with self.assertRaises(ValidationError):
                KgwConfiguration(**values)
        self.assertEqual(scoped_config().purpose, "research_fixture")

    def test_provider_registry_states_are_recorded_not_connections(self):
        policies = [
            ProviderPolicy(id="anthropic", access="pending"),
            ProviderPolicy(id="openai", access="granted", configured=True),
            ProviderPolicy(id="google", access="granted", configured=True, approved=True),
            ProviderPolicy(id="xai", failure="contract_unverified"),
        ]
        routes = WatermarkRoutes(WatermarkConfiguration(providers=policies))
        self.assertEqual(
            [route.state for route in routes.providers],
            ["access_pending", "configured", "approved", "failed"],
        )
        for route in routes.providers:
            self.assertFalse(route.enabled)
            self.assertFalse(route.connected)
            self.assertIn("adapter_not_integrated", route.blockers)
            self.assertIn("free_unlimited_unverified", route.blockers)
        self.assertEqual(ProviderRoute(id="google", access="unconfirmed").state, "discovered")
        self.assertEqual(ProviderRoute(
            id="google", access="granted", support="unsupported",
        ).state, "unsupported")
        for cls in (ProviderPolicy, ProviderRoute):
            with self.assertRaises(ValidationError):
                cls(id="openai", access="granted", configured=True, approved=True, enabled=True)

    def test_provider_credentials_urls_and_duplicates_are_rejected(self):
        for extra in ({"api_key": "private"}, {"endpoint": "https://example.com"}, {"headers": {}}):
            with self.assertRaises(ValidationError):
                ProviderPolicy(id="openai", **extra)
        with self.assertRaises(ValidationError):
            WatermarkConfiguration(providers=[
                ProviderPolicy(id="openai"), ProviderPolicy(id="openai"),
            ])

    def test_config_file_is_bounded_strict_and_errors_do_not_echo(self):
        self.assertIsNone(read_configuration(None).kgw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "routes.json")
            for content in ('{"private": "secret"}', "not-json-private", "x" * 65_537):
                path.write_text(content)
                with self.assertRaisesRegex(ValueError, "^invalid_watermark_route_configuration$"):
                    read_configuration(path)
            path.write_text('{"schema_version":"1","kgw":null}')
            self.assertIsNone(read_configuration(path).kgw)

    def test_default_and_disabled_have_no_observation_or_heavy_load(self):
        post = request().posts[0]
        for config, status, reason in [
            (None, "unsupported", "no_matching_configuration"),
            (scoped_config(enabled=False), "unavailable", "route_disabled"),
        ]:
            verifier = KgwVerifier(config)
            with patch.dict("sys.modules", {"torch": None, "transformers": None}):
                verifier.load()
                result = verifier.predict(post)
            self.assertEqual(result.status, status)
            self.assertEqual(result.reason, reason)
            self.assertIsNone(result.output)

    def test_key_material_and_environment_name_are_not_public_identity(self):
        config = scoped_config(
            purpose="known_configuration", key_source="environment",
            key_env="PRIVATE_WATERMARK_KEY", key_id="approved-local-config-v1",
        )
        routes = WatermarkRoutes(WatermarkConfiguration(kgw=config))
        serialized = json.dumps({
            "identity": routes.public_identity(), "status": routes.verifier.status().model_dump(),
        })
        self.assertNotIn("PRIVATE_WATERMARK_KEY", serialized)
        self.assertIn("known_configuration", serialized)

    def test_missing_implementation_is_unavailable_not_a_negative(self):
        verifier = KgwVerifier(scoped_config())
        with patch.dict("sys.modules", {"torch": None, "transformers": None}):
            result = verifier.predict(request().posts[0])
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "implementation_unavailable")
        self.assertIsNone(result.output)

    def test_prewarm_failure_is_visible_and_sanitized_not_a_required_model_failure(self):
        class BrokenVerifier(KgwVerifier):
            def load(self):
                raise RuntimeError("private-key-value")
        routes = WatermarkRoutes(
            WatermarkConfiguration(kgw=scoped_config()), verifier_factory=BrokenVerifier,
        )
        with self.assertLogs("detector_server.watermarks", level="ERROR") as logs:
            routes.load()
        result = routes.predict(request().posts[0])
        self.assertEqual(result.reason, "configuration_invalid")
        self.assertIsNone(result.output)
        self.assertEqual(routes.verifier.state, "error")
        self.assertNotIn("private-key-value", "".join(logs.output))

    def test_invalid_native_kind_becomes_explicit_failure_without_numeric_output(self):
        class BadVerifier(KgwVerifier):
            def predict(self, post):
                return CheckEvidence(
                    checker=self.spec.checker, status="completed",
                    coverage=Coverage(characters=len(post.text), token_limit=512),
                    output=ClassifierScore(value=0.9),
                )
        routes = WatermarkRoutes(verifier_factory=BadVerifier)
        result = routes.predict(request().posts[0])
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "invalid_checker_output")
        self.assertIsNone(result.output)


class NoClassifierAdapter:
    def __init__(self, spec, device):
        self.spec = spec
        self.loads = 0

    def load(self):
        self.loads += 1
        raise AssertionError("Watermark-only request loaded classifiers")

    def unload(self):
        pass


class FakeVerifier(KgwVerifier):
    def load(self):
        if self.configuration and self.configuration.enabled:
            self.state = "ready"

    def predict(self, post):
        self.load()
        return CheckEvidence(
            checker=self.spec.checker, status="completed",
            coverage=Coverage(characters=len(post.text), input_tokens=40, scored_tokens=39, token_limit=512),
            output=WatermarkFinding(
                decision="detected", verification_scope="known_configuration", z_score=6.0,
            ),
        )


class BlockingVerifier(FakeVerifier):
    def __init__(self, config):
        super().__init__(config)
        self.started = threading.Event()
        self.release = threading.Event()
        self.active = False

    def predict(self, post):
        self.load()
        self.active = True
        self.started.set()
        try:
            assert self.release.wait(timeout=5)
            return super().predict(post)
        finally:
            self.active = False

    def unload(self):
        assert not self.active
        super().unload()


class RouteApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_even_recorded_approval_cannot_create_hosted_egress(self):
        policies = [ProviderPolicy(
            id=id, access="granted", configured=True, approved=True,
            support="supported", terms_approved=True, free_unlimited_verified=True,
        ) for id in ("anthropic", "openai", "google", "xai")]
        with tempfile.TemporaryDirectory() as directory:
            suite = LocalSuite("cpu", 3, directory, watermark_routes=WatermarkRoutes(
                WatermarkConfiguration(providers=policies),
            ))
            app = create_app(Settings(TOKEN, "cpu"), suite=suite)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ) as client:
                with patch("socket.socket.connect", side_effect=AssertionError("No network allowed")):
                    response = await client.post("/v2/watermarks", json=request().model_dump())
                    self.assertEqual(response.status_code, 200)
                    state = (await client.get("/v2/status")).json()
                for route in state["suite"]["provider_routes"]:
                    self.assertEqual(route["state"], "approved")
                    self.assertEqual(route["blockers"], ["adapter_not_integrated"])
                    self.assertFalse(route["enabled"])
                    self.assertFalse(route["connected"])
            await suite.close()

    async def test_cpu_only_route_never_loads_gpu_and_keeps_no_estimate(self):
        with tempfile.TemporaryDirectory() as directory:
            routes = WatermarkRoutes(
                WatermarkConfiguration(kgw=scoped_config()), verifier_factory=FakeVerifier,
            )
            now = [100.0]
            suite = LocalSuite(
                "cuda:0", 3, directory, adapter_factory=NoClassifierAdapter,
                watermark_routes=routes, clock=lambda: now[0],
            )
            app = create_app(Settings(TOKEN, "cpu"), suite=suite)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ) as client:
                response = await client.post("/v2/watermarks", json=request().model_dump())
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()["results"][0]
                self.assertEqual(len(result["checks"]), 1)
                self.assertEqual(result["checks"][0]["output"]["decision"], "detected")
                self.assertEqual(result["aggregate"]["kind"], "no_estimate")
                self.assertEqual([adapter.loads for adapter in suite.adapters], [0] * 4)
                self.assertIsNone(suite.verified_gpu_uuid)
                self.assertTrue(routes.resident)
                now[0] = 104
                await suite.expire()
                self.assertFalse(routes.resident)
                self.assertFalse(suite.paused)
                await client.post("/v2/watermarks", json=request().model_dump())
                await suite.control("unload")
                await suite.wait_control()
                self.assertFalse(routes.resident)
                self.assertEqual((await client.post(
                    "/v2/watermarks", json=request().model_dump(),
                )).status_code, 409)
                self.assertTrue(all(not route.enabled for route in suite.status().provider_routes))
            await suite.close()

    async def test_default_route_is_unsupported_not_a_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(TOKEN, "cuda:0", state_dir=directory))
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test",
                headers={"Authorization": f"Bearer {TOKEN}"},
            ) as client:
                response = await client.post("/v2/watermarks", json=request().model_dump())
                self.assertEqual(response.status_code, 200)
                check = response.json()["results"][0]["checks"][0]
                self.assertEqual(check["reason"], "no_matching_configuration")
                self.assertIsNone(check["output"])
                before = [route.model_dump() for route in app.state.suite.status().provider_routes]
                bad = request().model_dump()
                bad["provider_enabled"] = True
                self.assertEqual((await client.post("/v2/watermarks", json=bad)).status_code, 422)
                self.assertEqual(before, [r.model_dump() for r in app.state.suite.status().provider_routes])
            await app.state.suite.close()

    async def test_cancelled_cpu_verification_holds_shared_ownership_until_done(self):
        with tempfile.TemporaryDirectory() as directory:
            routes = WatermarkRoutes(
                WatermarkConfiguration(kgw=scoped_config()), verifier_factory=BlockingVerifier,
            )
            suite = LocalSuite("cpu", 3, directory, watermark_routes=routes)
            task = asyncio.create_task(suite.verify_watermarks(request()))
            async with asyncio.timeout(3):
                while not routes.verifier.started.is_set():
                    await asyncio.sleep(0.001)
            try:
                task.cancel()
                await asyncio.sleep(0.01)
                self.assertTrue(suite.lock.locked())
                await suite.control("unload")
                self.assertTrue(suite.paused)
                self.assertTrue(routes.resident)
            finally:
                routes.verifier.release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                await suite.wait_control()
                self.assertFalse(routes.resident)
                await suite.close()


HAS_INFERENCE = importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None


@unittest.skipUnless(HAS_INFERENCE, "optional inference dependencies not installed")
class NativeVerifierTests(unittest.TestCase):
    def test_invalid_environment_key_is_sanitized_and_has_no_observation(self):
        # Reading the public demo key from an environment variable must not
        # bypass its research-only policy.
        for key in ("not-a-real-secret", "15485863"):
            verifier = KgwVerifier(scoped_config(
                key_source="environment", key_env="PRIVATE_WATERMARK_KEY",
                purpose="known_configuration", key_id="local-key-v1",
            ))
            with patch.dict("os.environ", {"PRIVATE_WATERMARK_KEY": key}):
                with self.assertLogs("detector_server.watermarks", level="ERROR") as logs:
                    result = verifier.predict(request().posts[0])
            self.assertEqual(result.reason, "configuration_invalid")
            self.assertIsNone(result.output)
            self.assertNotIn("not-a-real-secret", "".join(logs.output) + result.model_dump_json())
            self.assertNotIn("PRIVATE_WATERMARK_KEY", verifier.status().model_dump_json())

    def test_no_generator_is_constructed_and_sparse_input_is_not_human(self):
        from transformers import AutoModelForCausalLM
        with patch.object(AutoModelForCausalLM, "from_pretrained", side_effect=AssertionError("No generator")):
            verifier = KgwVerifier(scoped_config())
            verifier.load()
            self.assertEqual(verifier.state, "ready", verifier.failure)
            result = verifier.predict(request("Yes.").posts[0])
            self.assertEqual(result.status, "insufficient_evidence")
            self.assertIsNone(result.output)
            repeated = verifier.predict(request("test " * 100).posts[0])
            self.assertEqual(repeated.status, "insufficient_evidence")
            self.assertEqual(verifier.detector._get_ngram_score_cached.cache_info().maxsize, 0)
            reference = weakref.ref(verifier.detector)
            verifier.unload()
            self.assertIsNone(verifier.tokenizer)
            self.assertIsNone(verifier.detector)
            self.assertIsNone(reference())
