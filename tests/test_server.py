import asyncio
import threading
import unittest

import httpx

from detector_server.app import Settings, create_app
from detector_server.backend import InputTooLong, Prediction
from detector_server.lifecycle import BusyError, ModelManager

TOKEN = "test-only-token-not-for-deployment"


class FakeBackend:
    def __init__(self):
        self.loads = 0
        self.unloads = 0
        self.loaded = False
        self.fail_load = False
        self.started = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def load(self):
        self.loads += 1
        if self.fail_load:
            raise RuntimeError("private diagnostic")
        self.loaded = True

    def predict(self, texts):
        assert self.loaded
        self.started.set()
        self.release.wait(timeout=5)
        if texts == ["too long"]:
            raise InputTooLong("Each post must fit within 512 tokens")
        if texts == ["fail"]:
            raise RuntimeError("private text")
        return [Prediction(0.7234, 12) for _ in texts]

    def unload(self):
        self.unloads += 1
        self.loaded = False


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = FakeBackend()
        self.app = create_app(Settings(TOKEN, "cpu", 60), self.backend)
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    async def asyncTearDown(self):
        self.backend.release.set()
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    async def detect(self, text="hello"):
        return await self.client.post("/v1/detect", json={"posts": [{"id": "1", "text": text}]})

    async def test_lazy_load_reuse_and_percentage(self):
        self.assertEqual(self.backend.loads, 0)
        self.assertEqual((await self.client.get("/ready")).status_code, 503)
        response = await self.detect()
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["api_status"], "legacy_diagnostics")
        self.assertFalse(result["calibrated_for_x"])
        self.assertEqual(result["results"][0]["ai_percentage"], 72.3)
        self.assertEqual(result["results"][0]["ai_score"], 0.7234)
        await self.detect()
        self.assertEqual(self.backend.loads, 1)
        self.assertEqual((await self.client.get("/ready")).status_code, 200)

    async def test_manual_controls_are_idempotent(self):
        for _ in range(2):
            self.assertEqual((await self.client.post("/v1/model/load")).status_code, 200)
        self.assertEqual(self.backend.loads, 1)
        for _ in range(2):
            self.assertEqual((await self.client.post("/v1/model/unload")).status_code, 200)
        self.assertEqual(self.backend.unloads, 1)
        self.assertEqual((await self.detect()).status_code, 409)
        self.assertTrue((await self.client.get("/v1/model")).json()["paused"])
        await self.client.post("/v1/model/load")
        await self.detect()
        self.assertEqual(self.backend.loads, 2)

    async def test_unauthorized_does_not_load(self):
        response = await self.client.post(
            "/v1/model/load", headers={"Authorization": "Bearer wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.backend.loads, 0)

    async def test_invalid_requests_do_not_echo_or_load(self):
        for posts in [
            [], [{"id": "1", "text": " "}], [{"id": "1", "text": "x" * 10001}],
            [{"id": "1", "text": "private"}] * 2,
            [{"id": str(i), "text": "private"} for i in range(17)],
        ]:
            response = await self.client.post("/v1/detect", json={"posts": posts})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("private", response.text)
        self.assertEqual(self.backend.loads, 0)

    async def test_chunked_body_limit(self):
        async def chunks():
            for _ in range(130):
                yield b"x" * 1000

        response = await self.client.post("/v1/detect", content=chunks())
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.backend.loads, 0)

    async def test_failures_never_become_zero(self):
        response = await self.detect("fail")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)
        self.assertNotIn("ai_percentage", response.text)
        self.assertEqual((await self.detect("too long")).status_code, 422)

    async def test_failed_load_cleans_up_and_can_retry(self):
        self.backend.fail_load = True
        self.assertEqual((await self.detect()).status_code, 503)
        self.assertFalse(self.backend.loaded)
        self.assertEqual(self.app.state.manager.state, "unloaded")
        self.backend.fail_load = False
        self.assertEqual((await self.detect()).status_code, 200)

    async def test_busy_unload_does_not_interrupt_inference(self):
        self.backend.release.clear()
        task = asyncio.create_task(self.detect())
        while not self.backend.started.is_set():
            await asyncio.sleep(0.001)
        response = await self.client.post("/v1/model/unload")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.backend.unloads, 0)
        self.backend.release.set()
        self.assertEqual((await task).status_code, 200)
        self.assertEqual((await self.client.post("/v1/model/unload")).status_code, 200)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_request_keeps_model_owned_until_inference_finishes(self):
        backend = FakeBackend()
        backend.release.clear()
        manager = ModelManager(backend, 1)
        task = asyncio.create_task(manager.operate("detect", ["hello"]))
        try:
            while not backend.started.is_set():
                await asyncio.sleep(0.001)
            task.cancel()
            await asyncio.sleep(0.01)
            self.assertTrue(manager.lock.locked())
            with self.assertRaises(BusyError):
                await manager.operate("unload")
        finally:
            backend.release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await manager.close()

    async def test_idle_expiry_and_load_refresh(self):
        now = [100.0]
        backend = FakeBackend()
        manager = ModelManager(backend, 10, clock=lambda: now[0])
        await manager.operate("load")
        now[0] = 109
        await manager.expire()
        self.assertTrue(backend.loaded)
        await manager.operate("load")
        now[0] = 111
        await manager.expire()
        self.assertTrue(backend.loaded)
        now[0] = 119
        await manager.expire()
        self.assertFalse(backend.loaded)
        await manager.operate("detect", ["hello"])
        self.assertEqual(backend.loads, 2)
        await manager.close()
        self.assertFalse(backend.loaded)

    async def test_busy_expiry_skips_model(self):
        backend = FakeBackend()
        manager = ModelManager(backend, 1)
        await manager.operate("load")
        manager.last_used -= 5
        async with manager.lock:
            await manager.expire()
            with self.assertRaises(BusyError):
                await manager.operate("unload")
        self.assertTrue(backend.loaded)
        await manager.expire()
        self.assertFalse(backend.loaded)


class SettingsTests(unittest.TestCase):
    def test_fail_closed(self):
        for settings in [
            {"token": ""}, {"token": TOKEN, "idle_seconds": float("nan")},
            {"token": TOKEN, "idle_seconds": 0}, {"token": TOKEN, "device": "cuda"},
        ]:
            with self.assertRaises(ValueError):
                Settings(**settings)
