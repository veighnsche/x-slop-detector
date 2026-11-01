import asyncio
import json
from pathlib import Path
import tempfile
import threading
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from detector_server.adapters import DeviceConfigurationError, ResourceExhausted, verify_device
from detector_server.app import Settings, create_app
from detector_server.contracts import (
    AnalyzeRequest, CheckEvidence, ClassifierScore, Coverage, Discrepancy,
)
from detector_server.lifecycle import BusyError, ModelPausedError
from detector_server.suite import LocalSuite

TOKEN = "test-only-token-not-for-deployment"


def request(texts=None):
    return AnalyzeRequest(
        schema_version="2", extraction_version="fixture-v1",
        posts=[{"id": str(i), "text": text} for i, text in enumerate(texts or ["two words"])],
    )


class FakeAdapter:
    def __init__(self, spec, device):
        self.spec = spec
        self.loaded = False
        self.loads = 0
        self.unloads = 0
        self.fail_load = False
        self.fail_predict = False
        self.fail_unload = False
        self.oom = False
        self.invalid = False
        self.started = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.inference_active = False
        self.block_load = False
        self.load_started = threading.Event()

    def load(self):
        self.loads += 1
        self.loaded = True  # Partial allocation even on failure.
        self.load_started.set()
        if self.block_load:
            assert self.release.wait(timeout=10)
        if self.fail_load:
            raise RuntimeError("private-load-diagnostic")

    def predict(self, post):
        assert self.loaded
        self.inference_active = True
        self.started.set()
        try:
            assert self.release.wait(timeout=10)
            if self.oom:
                raise ResourceExhausted()
            if self.fail_predict:
                raise RuntimeError("private-post-and-secret")
            count = len(post.text.split())
            common = {
                "checker": self.spec.checker,
                "coverage": Coverage(
                    characters=len(post.text), input_tokens=count, token_limit=512,
                ),
            }
            if count > 512:
                return CheckEvidence(**common, status="unsupported", reason="token_limit_exceeded")
            if self.spec.kind == "statistical" and count < 2:
                return CheckEvidence(
                    **common, status="insufficient_evidence", reason="no_next_token_observations",
                )
            output = (
                Discrepancy(value=-0.25) if self.spec.kind == "statistical"
                else ClassifierScore(value=0.7)
            )
            if self.invalid:
                output = Discrepancy(value=-2.0)
            return CheckEvidence(**common, status="completed", output=output)
        finally:
            self.inference_active = False

    def unload(self):
        assert not self.inference_active
        self.unloads += 1
        if self.fail_unload:
            raise RuntimeError("private-unload-diagnostic")
        self.loaded = False


async def event_set(event):
    async with asyncio.timeout(5):
        while not event.is_set():
            await asyncio.sleep(0.001)


class SuiteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.now = [100.0]
        self.suite = LocalSuite(
            "cpu", 10, self.directory.name, adapter_factory=FakeAdapter,
            clock=lambda: self.now[0],
        )

    async def asyncTearDown(self):
        for adapter in self.suite.adapters:
            adapter.release.set()
            adapter.fail_unload = False
        await self.suite.close()
        self.directory.cleanup()

    async def test_status_during_partial_torch_import_does_not_touch_cuda(self):
        def forbidden():
            raise AssertionError("CUDA must not be queried during torch import")
        self.suite.device = "cuda:0"
        try:
            for partial in (
                SimpleNamespace(),
                SimpleNamespace(
                    __spec__=SimpleNamespace(_initializing=True),
                    cuda=SimpleNamespace(is_initialized=forbidden),
                ),
            ):
                with patch.dict(sys.modules, {"torch": partial}):
                    self.assertIsNone(self.suite.status().device_memory)
        finally:
            self.suite.device = "cpu"

    async def test_status_reads_memory_only_after_runtime_initialization(self):
        cuda = SimpleNamespace(
            is_initialized=lambda: True, memory_allocated=lambda device: 1,
            memory_reserved=lambda device: 2, max_memory_allocated=lambda device: 3,
            max_memory_reserved=lambda device: 4,
        )
        self.suite.device = "cuda:0"
        try:
            with patch.dict(sys.modules, {"torch": SimpleNamespace(cuda=cuda)}):
                self.assertEqual(self.suite.status().device_memory.allocated_bytes, 1)
            cuda.is_initialized = lambda: False
            with patch.dict(sys.modules, {"torch": SimpleNamespace(cuda=cuda)}):
                self.assertIsNone(self.suite.status().device_memory)
        finally:
            self.suite.device = "cpu"

    async def test_lazy_load_reuse_all_members_and_idle_reload(self):
        self.assertEqual([a.loads for a in self.suite.adapters], [0] * 4)
        self.assertTrue(self.suite.status().integrated)
        result = await self.suite.analyze(request())
        self.assertEqual(len(result[0].checks), 5)
        self.assertEqual(result[0].checks[4].reason, "no_matching_configuration")
        self.assertEqual(result[0].checks[3].output.kind, "token_probability_discrepancy")
        await self.suite.analyze(request())
        self.assertEqual([a.loads for a in self.suite.adapters], [1] * 4)
        self.now[0] = 111
        self.suite.status()  # Polling cannot postpone expiry.
        await self.suite.expire()
        self.assertFalse(self.suite.paused)
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))
        await self.suite.analyze(request())
        self.assertEqual([a.loads for a in self.suite.adapters], [2] * 4)

    async def test_manual_controls_persist_pause_and_are_idempotent(self):
        self.assertEqual(await self.suite.control("load"), "pending")
        self.assertEqual(await self.suite.control("load"), "pending")
        await self.suite.wait_control()
        self.assertEqual(await self.suite.control("load"), "completed")
        self.assertEqual([a.loads for a in self.suite.adapters], [1] * 4)
        await self.suite.control("unload")
        await self.suite.wait_control()
        self.assertTrue(self.suite.paused)
        with self.assertRaises(ModelPausedError):
            await self.suite.analyze(request())
        restarted = LocalSuite("cpu", 10, self.directory.name, adapter_factory=FakeAdapter)
        self.assertTrue(restarted.paused)
        await restarted.close()
        self.assertEqual(await self.suite.control("unload"), "completed")
        await self.suite.control("load")
        await self.suite.wait_control()
        self.assertFalse(self.suite.paused)
        self.assertEqual([a.loads for a in self.suite.adapters], [2] * 4)

    async def test_unload_during_inference_latches_pause_then_safely_releases(self):
        adapter = self.suite.adapters[0]
        adapter.release.clear()
        task = asyncio.create_task(self.suite.analyze(request()))
        await event_set(adapter.started)
        self.assertEqual(await self.suite.control("unload"), "pending")
        self.assertEqual(await self.suite.control("unload"), "pending")
        self.assertTrue(self.suite.paused)
        self.assertEqual(self.suite.status().pending_control, "unload")
        with self.assertRaises(ModelPausedError):
            await self.suite.analyze(request())
        with self.assertRaises(BusyError):
            await self.suite.control("load")
        self.assertEqual(adapter.unloads, 0)
        adapter.release.set()
        await task
        await self.suite.wait_control()
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))

    async def test_cancelled_request_keeps_slot_until_worker_finishes(self):
        adapter = self.suite.adapters[0]
        adapter.release.clear()
        task = asyncio.create_task(self.suite.analyze(request()))
        await event_set(adapter.started)
        task.cancel()
        await asyncio.sleep(0.01)
        self.assertTrue(self.suite.lock.locked())
        with self.assertRaises(BusyError):
            await self.suite.analyze(request())
        await self.suite.control("unload")
        adapter.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await self.suite.wait_control()
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))

    async def test_unload_supersedes_pending_prewarm_without_undoing_pause(self):
        adapter = self.suite.adapters[0]
        adapter.block_load = True
        adapter.release.clear()
        await self.suite.control("load")
        await event_set(adapter.load_started)
        await self.suite.control("unload")
        with self.assertRaises(BusyError):
            await self.suite.control("load")
        adapter.release.set()
        await self.suite.wait_control()
        self.assertTrue(self.suite.paused)
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))

    async def test_failed_load_cleans_all_partial_allocations_and_retries(self):
        self.suite.adapters[1].fail_load = True
        with self.assertLogs("detector_server.suite", level="ERROR") as logs:
            with self.assertRaises(RuntimeError):
                await self.suite.analyze(request())
        self.assertNotIn("private", "".join(logs.output))
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))
        self.assertEqual(self.suite.status().last_error, "load_failed")
        self.assertEqual(self.suite.states["e5"], "error")
        self.suite.adapters[1].fail_load = False
        await self.suite.analyze(request())
        self.assertTrue(self.suite._loaded())

    async def test_invalid_or_failed_checker_keeps_other_evidence_then_releases(self):
        for invalid in (False, True):
            self.suite.adapters[1].invalid = invalid
            self.suite.adapters[1].fail_predict = not invalid
            results = await self.suite.analyze(request(["two words", "other words"]))
            for result in results:
                self.assertEqual(result.checks[0].status, "completed")
                self.assertEqual(result.checks[1].status, "failed")
                self.assertIsNone(result.checks[1].output)
                self.assertEqual(result.checks[3].status, "completed")
            self.assertTrue(all(not a.loaded for a in self.suite.adapters))
            self.assertEqual(self.suite.last_error, "inference_failed")

    async def test_oom_releases_whole_suite_and_is_not_a_reduced_result(self):
        self.suite.adapters[2].oom = True
        with self.assertRaises(ResourceExhausted):
            await self.suite.analyze(request())
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))
        self.assertEqual(self.suite.status().last_error, "out_of_memory")
        self.suite.adapters[2].oom = False
        await self.suite.analyze(request())
        self.assertTrue(self.suite._loaded())

    async def test_mixed_admission_is_per_checker_and_post(self):
        results = await self.suite.analyze(request(["two words", "Yes.", "word " * 513]))
        self.assertEqual(results[0].checks[3].status, "completed")
        self.assertEqual(results[1].checks[3].reason, "no_next_token_observations")
        self.assertTrue(all(c.reason == "token_limit_exceeded" for c in results[2].checks[:4]))

    async def test_shutdown_waits_for_worker_and_rejects_new_work(self):
        adapter = self.suite.adapters[0]
        adapter.release.clear()
        task = asyncio.create_task(self.suite.analyze(request()))
        await event_set(adapter.started)
        close = asyncio.create_task(self.suite.close())
        await asyncio.sleep(0.01)
        self.assertFalse(close.done())
        with self.assertRaises(RuntimeError):
            await self.suite.analyze(request())
        adapter.release.set()
        await task
        await close
        self.assertTrue(all(not a.loaded for a in self.suite.adapters))

    async def test_unload_failure_is_visible_and_all_other_assets_are_released(self):
        await self.suite.analyze(request())
        self.suite.adapters[1].fail_unload = True
        await self.suite.control("unload")
        await self.suite.wait_control()
        self.assertEqual(self.suite.last_error, "unload_failed")
        self.assertEqual(self.suite.states["e5"], "error")
        self.assertFalse(self.suite.adapters[0].loaded)
        self.assertFalse(self.suite.adapters[2].loaded)

    async def test_corrupt_pause_file_fails_closed_and_tmr_is_explicit_challenger(self):
        Path(self.directory.name, "manual-pause.json").write_text('{"manual_pause": "false"}')
        restarted = LocalSuite("cpu", 10, self.directory.name, roberta="tmr", adapter_factory=FakeAdapter)
        self.assertTrue(restarted.paused)
        self.assertEqual(restarted.last_error, "state_persistence_failed")
        self.assertEqual(restarted.specs[2].checker.id, "tmr")
        self.assertTrue(all(spec.checker.configuration_id.endswith(".cpu") for spec in restarted.local_specs))
        await restarted.close()

    async def test_device_verification_failure_never_loads_any_adapter(self):
        def refuse(device, uuid):
            raise DeviceConfigurationError()
        self.suite.device_verifier = refuse
        with self.assertRaises(RuntimeError):
            await self.suite.analyze(request())
        self.assertEqual([a.loads for a in self.suite.adapters], [0] * 4)
        self.assertEqual(self.suite.last_error, "device_configuration_error")

    async def test_pause_write_failure_still_releases_models_and_blocks_resume(self):
        await self.suite.analyze(request())
        with patch.object(self.suite.store, "write", side_effect=OSError("private path")):
            await self.suite.control("unload")
            await self.suite.wait_control()
            self.assertTrue(all(not a.loaded for a in self.suite.adapters))
            self.assertTrue(self.suite.paused)
            self.assertFalse(self.suite.status().pause_persisted)
            self.assertEqual(self.suite.last_error, "state_persistence_failed")
            with self.assertRaises(RuntimeError):
                await self.suite.control("load")
            self.assertTrue(self.suite.paused)
        await self.suite.control("load")
        await self.suite.wait_control()
        self.assertFalse(self.suite.paused)
        self.assertTrue(self.suite.status().pause_persisted)


class SharedApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_v1_and_v2_clients_share_residency_pause_and_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            suite = LocalSuite("cpu", 600, directory, adapter_factory=FakeAdapter)
            app = create_app(Settings(TOKEN, "cpu"), suite=suite)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                ) as first, httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                ) as second:
                    response = await first.post("/v2/analyze", json=request().model_dump())
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertNotIn("probability", response.json()["results"][0]["aggregate"])
                    legacy = await second.post("/v1/detect", json={"posts": [{"id": "1", "text": "two words"}]})
                    self.assertEqual(legacy.status_code, 200)
                    self.assertEqual([a.loads for a in suite.adapters], [1] * 4)
                    suite.paused = True
                    self.assertEqual((await first.get("/ready")).status_code, 503)
                    suite.paused = False
                    unload = await first.post("/v2/control", json={"schema_version": "2", "action": "unload"})
                    self.assertEqual(unload.status_code, 202)
                    await suite.wait_control()
                    self.assertTrue((await second.get("/v1/model")).json()["paused"])
                    self.assertEqual((await second.post("/v2/analyze", json=request().model_dump())).status_code, 409)
                    await second.post("/v1/model/load")
                    self.assertTrue((await first.get("/v2/status")).json()["diagnostics_ready"])

    async def test_gpu_is_never_selected_implicitly(self):
        with self.assertRaises(DeviceConfigurationError):
            verify_device("cuda:0", None)
        with self.assertRaises(DeviceConfigurationError):
            verify_device("cuda:1", "GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db")
