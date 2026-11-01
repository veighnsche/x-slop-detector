"""One bounded inference slot; load, inference, and unload cannot overlap."""

import asyncio
import math
import time
from collections.abc import Callable

import anyio


class BusyError(Exception):
    pass


class ModelPausedError(Exception):
    pass


async def finish_before_cancelling(awaitable):
    """Don't release model ownership while an uncancellable worker still runs.

    AnyIO shields handle cancel scopes, but a direct asyncio Task.cancel() also
    needs shielding. Defer that cancellation until the entire operation finishes,
    including its state updates, rather than only protecting the worker await.
    """
    task = asyncio.create_task(awaitable)
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            cancelled = True
        except Exception:
            if cancelled:
                raise asyncio.CancelledError() from None
            raise
        else:
            if cancelled:
                raise asyncio.CancelledError()
            return result


class ModelManager:
    def __init__(self, backend, idle_seconds: float, clock: Callable = time.monotonic):
        self.backend = backend
        self.idle_seconds = idle_seconds
        self.clock = clock
        self.lock = asyncio.Lock()
        self.state = "unloaded"
        self.last_used = None
        self.paused = False

    def status(self):
        remaining = None
        if self.state == "ready" and self.last_used is not None:
            remaining = max(0, self.idle_seconds - (self.clock() - self.last_used))
        return {
            "state": self.state,
            "busy": self.lock.locked(),
            "paused": self.paused,
            "idle_timeout_seconds": self.idle_seconds,
            "unload_in_seconds": remaining,
        }

    async def _load(self):
        if self.state == "ready":
            return
        self.state = "loading"
        try:
            await anyio.to_thread.run_sync(self.backend.load)
        except Exception:
            # Drop even a partially loaded model after download/device failures.
            await self._unload()
            raise
        self.state = "ready"
        self.last_used = self.clock()

    async def _unload(self):
        self.state = "unloading"
        try:
            await anyio.to_thread.run_sync(self.backend.unload)
        except Exception:
            self.state = "error"
            raise
        self.state = "unloaded"
        self.last_used = None

    async def operate(self, operation: str, texts: list[str] | None = None):
        # No await between checking and acquiring an uncontended asyncio lock.
        # Reject excess work instead of accumulating an unbounded GPU queue.
        if self.lock.locked():
            raise BusyError()
        async with self.lock:
            # Worker threads cannot safely be interrupted mid-inference. Keep
            # residency ownership until they finish, even on client cancellation.
            with anyio.CancelScope(shield=True):
                return await finish_before_cancelling(self._operate(operation, texts))

    async def _operate(self, operation, texts):
        if operation == "unload":
            # Explicit unload pauses detection so background feed scans
            # cannot immediately reload the model behind the user's back.
            self.paused = True
            if self.state != "unloaded":
                await self._unload()
            return None
        if operation == "detect" and self.paused:
            raise ModelPausedError()
        if operation == "load":
            self.paused = False
        await self._load()
        if operation == "load":
            self.last_used = self.clock()
            return None
        try:
            predictions = await anyio.to_thread.run_sync(self.backend.predict, texts)
            if len(predictions) != len(texts) or any(
                not math.isfinite(p.ai_score) or not 0 <= p.ai_score <= 1
                for p in predictions
            ):
                raise RuntimeError("Invalid detector predictions")
            return predictions
        finally:
            # The idle period starts after inference finishes.
            self.last_used = self.clock()

    async def expire(self):
        if self.lock.locked():
            return
        async with self.lock:
            if (
                self.state == "ready"
                and self.last_used is not None
                and self.clock() - self.last_used >= self.idle_seconds
            ):
                with anyio.CancelScope(shield=True):
                    await finish_before_cancelling(self._unload())

    async def watch_idle(self):
        while True:
            await asyncio.sleep(min(5, self.idle_seconds / 2))
            await self.expire()

    async def close(self):
        async with self.lock:
            with anyio.CancelScope(shield=True):
                if self.state != "unloaded":
                    await finish_before_cancelling(self._unload())
