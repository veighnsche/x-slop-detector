"""One process-wide owner for the local suite and its persistent manual pause."""

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import time

import anyio

from .adapters import DeviceConfigurationError, ResourceExhausted, TransformerAdapter, initialized_cuda, verify_device
from .catalog import E5, FAKESPOT, NEO, TABULARIS, TMR
from .contracts import (
    AnalyzeRequest, CheckEvidence, ComponentState, Coverage, DeviceMemory, Post, PostEvidence,
    SuiteState, validate_check,
)
from .lifecycle import BusyError, ModelPausedError, finish_before_cancelling
from .watermarks import WatermarkRoutes

logger = logging.getLogger(__name__)


class PauseStore:
    def __init__(self, directory):
        self.path = Path(directory) / "manual-pause.json"

    def read(self):
        if not self.path.exists():
            return False
        value = json.loads(self.path.read_text())
        if set(value) != {"manual_pause"} or type(value["manual_pause"]) is not bool:
            raise ValueError("invalid_pause_state")
        return value["manual_pause"]

    def write(self, paused):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, delete=False) as file:
                temporary = file.name
                json.dump({"manual_pause": paused}, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)


class LocalSuite:
    def __init__(
        self, device, idle_seconds, state_dir, gpu_uuid=None, roberta="fakespot",
        *, adapter_factory=TransformerAdapter, device_verifier=verify_device, clock=time.monotonic,
        watermark_routes=None,
    ):
        base = (TABULARIS, E5, TMR if roberta == "tmr" else FAKESPOT, NEO)
        # CPU/GPU calculations (especially FP16 Neo) are not identical profiles.
        self.local_specs = tuple(spec.model_copy(update={
            "checker": spec.checker.model_copy(update={
                "configuration_id": f"{spec.checker.configuration_id}.{device.replace(':', '-')}",
            }),
        }) for spec in base)
        self.watermarks = watermark_routes if watermark_routes is not None else WatermarkRoutes()
        self.watermark_specs = self.watermarks.specs
        self.specs = (*self.local_specs, *self.watermark_specs)
        self.device = device
        self.gpu_uuid = gpu_uuid
        self.verified_gpu_uuid = None
        self.idle_seconds = idle_seconds
        self.clock = clock
        self.store = PauseStore(state_dir)
        self.last_error = None
        self.pause_persisted = True
        try:
            self.paused = self.store.read()
        except Exception:
            self.paused = True  # Corrupt/unreadable state cannot silently resume.
            self.pause_persisted = False
            self.last_error = "state_persistence_failed"
        self.adapters = [adapter_factory(spec, device) for spec in self.local_specs]
        self.states = {spec.checker.id: "unloaded" for spec in self.local_specs}
        identity = json.dumps({
            "checkers": [spec.model_dump() for spec in self.specs],
            "device": device, "gpu_uuid": gpu_uuid,
            "watermark_routes": self.watermarks.public_identity(),
        }, sort_keys=True)
        self.configuration_id = "local-suite-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        self.lock = asyncio.Lock()
        self.operation = "idle"
        self.pending_control = None
        self.control_task = None
        self.last_used = None
        self.closed = False
        self.device_verifier = device_verifier

    def status(self):
        remaining = None
        if self._resident() and self.last_used is not None:
            remaining = max(0.0, self.idle_seconds - (self.clock() - self.last_used))
        memory = None
        cuda = initialized_cuda() if self.device.startswith("cuda") else None
        if cuda is not None:
            memory = DeviceMemory(
                allocated_bytes=cuda.memory_allocated(self.device),
                reserved_bytes=cuda.memory_reserved(self.device),
                peak_allocated_bytes=cuda.max_memory_allocated(self.device),
                peak_reserved_bytes=cuda.max_memory_reserved(self.device),
            )
        return SuiteState(
            configuration_id=self.configuration_id, integrated=True,
            paused=self.paused, busy=self.lock.locked() or self.pending_control is not None,
            pause_persisted=self.pause_persisted,
            operation=self.operation, pending_control=self.pending_control, last_error=self.last_error,
            configured_device=self.device, verified_gpu_uuid=self.verified_gpu_uuid,
            device_memory=memory,
            idle_timeout_seconds=float(self.idle_seconds), unload_in_seconds=remaining,
            components=[
                ComponentState(checker_id=spec.checker.id, required=True, state=self.states[spec.checker.id])
                for spec in self.local_specs
            ] + [
                ComponentState(
                    checker_id=spec.checker.id, required=False,
                    state=self.watermarks.verifier.state,
                ) for spec in self.watermark_specs
            ],
            provider_routes=list(self.watermarks.providers),
            local_watermark_routes=[self.watermarks.verifier.status()],
        )

    def _loaded(self):
        return all(value == "ready" for value in self.states.values())

    def _resident(self):
        return self.watermarks.resident or any(
            state != "unloaded" for state in self.states.values()
        )

    async def _unload(self):
        self.operation = "unloading"
        failed = False
        for adapter in reversed(self.adapters):
            id = adapter.spec.checker.id
            self.states[id] = "unloading"
            try:
                await anyio.to_thread.run_sync(adapter.unload)
            except Exception as error:
                logger.error("Suite unload failed (%s)", type(error).__name__)
                self.states[id] = "error"
                failed = True
            else:
                self.states[id] = "unloaded"
        try:
            await anyio.to_thread.run_sync(self.watermarks.unload)
        except Exception as error:
            logger.error("Watermark unload failed (%s)", type(error).__name__)
            failed = True
        self.last_used = None
        if failed:
            self.last_error = "unload_failed"
            raise RuntimeError("unload_failed")

    async def _load(self):
        if self._loaded():
            await anyio.to_thread.run_sync(self.watermarks.load)
            return
        if any(state == "error" for state in self.states.values()):
            await self._unload()
        self.operation = "loading"
        failed_id = None
        failure = None
        try:
            self.verified_gpu_uuid = await anyio.to_thread.run_sync(
                self.device_verifier, self.device, self.gpu_uuid,
            )
            for adapter in self.adapters:
                id = adapter.spec.checker.id
                failed_id = id
                self.states[id] = "loading"
                await anyio.to_thread.run_sync(adapter.load)
                self.states[id] = "ready"
            # CPU verification is optional and keeps its own failure status.
            await anyio.to_thread.run_sync(self.watermarks.load)
        except Exception as error:
            logger.error("Suite load failed (%s)", type(error).__name__)
            failure = "device_configuration_error" if isinstance(error, DeviceConfigurationError) else "load_failed"
        if failure is not None:
            # Cleanup outside the exception handler, after worker tracebacks
            # holding partially allocated weights have been discarded.
            await self._unload()
            if failed_id is not None:
                self.states[failed_id] = "error"
            self.last_error = failure
            raise RuntimeError(failure)
        self.last_error = None
        self.last_used = self.clock()

    async def analyze(self, request):
        return await self._admit(request, watermarks_only=False)

    async def verify_watermarks(self, request):
        return await self._admit(request, watermarks_only=True)

    async def _admit(self, request, *, watermarks_only):
        if self.closed:
            raise RuntimeError("suite_closed")
        if self.paused:
            raise ModelPausedError()
        if self.lock.locked() or self.pending_control is not None:
            raise BusyError()
        async with self.lock:
            with anyio.CancelScope(shield=True):
                return await finish_before_cancelling(
                    self._analyze_owned(request, watermarks_only=watermarks_only),
                )

    async def _analyze_owned(self, request, *, watermarks_only=False):
        try:
            if not watermarks_only:
                await self._load()
            self.operation = "analyzing"
            checks = [[] for _ in request.posts]
            failed_ids = []
            exhausted = False
            for adapter in (() if watermarks_only else self.adapters):
                checker_failed = False
                failure_reason = "checker_error"
                for index, post in enumerate(request.posts):
                    result = None
                    if not checker_failed:
                        try:
                            raw = await anyio.to_thread.run_sync(adapter.predict, post)
                            result = CheckEvidence.model_validate(raw.model_dump())
                            validate_check(result, adapter.spec, len(post.text))
                        except (ResourceExhausted, MemoryError):
                            exhausted = True
                        except ValueError:
                            checker_failed = True
                            result = None
                            failure_reason = "invalid_checker_output"
                        except Exception as error:
                            logger.error("Suite checker failed (%s)", type(error).__name__)
                            checker_failed = True
                    if exhausted:
                        break
                    if result is None:
                        result = CheckEvidence(
                            checker=adapter.spec.checker, status="failed", reason=failure_reason,
                            coverage=Coverage(characters=len(post.text), token_limit=adapter.spec.max_tokens),
                        )
                    checks[index].append(result)
                if exhausted:
                    break
                if checker_failed:
                    failed_ids.append(adapter.spec.checker.id)
            if exhausted or failed_ids:
                await self._unload()
                for id in failed_ids:
                    self.states[id] = "error"
                self.last_error = "out_of_memory" if exhausted else "inference_failed"
                if exhausted:
                    raise ResourceExhausted()
            for index, post in enumerate(request.posts):
                result = await anyio.to_thread.run_sync(self.watermarks.predict, post)
                validate_check(result, self.watermark_specs[0], len(post.text))
                checks[index].append(result)
            return [
                PostEvidence(id=post.id, checks=post_checks)
                for post, post_checks in zip(request.posts, checks)
            ]
        finally:
            if self._resident():
                self.last_used = self.clock()
            self.operation = "idle"

    async def control(self, action):
        if self.closed:
            raise RuntimeError("suite_closed")
        if action == "unload":
            self.paused = True
            # A persistence failure must not prevent freeing the models.
            self._save_pause(True)
            if self.control_task is not None:
                self.pending_control = "unload"  # Supersede prewarm; never undo unload.
                return "pending"
            if not self.lock.locked() and not self._resident():
                if self.pause_persisted:
                    self.last_error = None
                return "completed"
        else:
            if self.control_task is not None:
                if self.pending_control == "load":
                    return "pending"
                raise BusyError()
            if self.lock.locked():
                raise BusyError()
            if not self._save_pause(False):
                raise RuntimeError("state_persistence_failed")
            self.paused = False
            if self._loaded() and self.watermarks.ready_or_inactive:
                self.last_used = self.clock()
                return "completed"
        self.pending_control = action
        self.control_task = asyncio.create_task(self._run_control())
        return "pending"

    def _save_pause(self, paused):
        try:
            self.store.write(paused)
        except Exception as error:
            logger.error("Pause persistence failed (%s)", type(error).__name__)
            self.pause_persisted = False
            self.last_error = "state_persistence_failed"
            return False
        self.pause_persisted = True
        if self.last_error == "state_persistence_failed":
            self.last_error = None
        return True

    async def _run_control(self):
        try:
            async with self.lock:
                while True:
                    action = self.pending_control
                    try:
                        if action == "load":
                            await self._load()
                            self.last_used = self.clock()
                        else:
                            await self._unload()
                            if self.pause_persisted:
                                self.last_error = None
                    except Exception as error:
                        logger.error("Suite control failed (%s)", type(error).__name__)
                    if self.pending_control == action:
                        break
        finally:
            self.pending_control = None
            self.control_task = None
            self.operation = "idle"

    async def wait_control(self):
        task = self.control_task
        if task is not None:
            await asyncio.shield(task)

    async def expire(self):
        if self.lock.locked() or self.pending_control is not None:
            return
        async with self.lock:
            if self._resident() and self.last_used is not None and self.clock() - self.last_used >= self.idle_seconds:
                with anyio.CancelScope(shield=True):
                    try:
                        await finish_before_cancelling(self._unload())
                    finally:
                        self.operation = "idle"

    async def watch_idle(self):
        while True:
            await asyncio.sleep(min(5, self.idle_seconds / 2))
            try:
                await self.expire()
            except Exception as error:
                logger.error("Suite expiry failed (%s)", type(error).__name__)

    async def close(self):
        self.closed = True
        await self.wait_control()
        async with self.lock:
            with anyio.CancelScope(shield=True):
                try:
                    await finish_before_cancelling(self._unload())
                finally:
                    self.operation = "idle"


class LegacySuiteManager:
    """V1 diagnostics share the same tensors, slot, pause, and idle timer as v2."""

    def __init__(self, suite):
        self.suite = suite
        self.lock = suite.lock

    @property
    def state(self):
        if self.suite._loaded():
            return "ready"
        if self.suite.operation in ("loading", "unloading"):
            return self.suite.operation
        return "error" if any(s == "error" for s in self.suite.states.values()) else "unloaded"

    def status(self):
        status = self.suite.status()
        return {
            "state": self.state, "busy": status.busy, "paused": status.paused,
            "idle_timeout_seconds": status.idle_timeout_seconds,
            "unload_in_seconds": status.unload_in_seconds,
        }

    async def operate(self, operation, texts=None):
        from .backend import InputTooLong, Prediction

        if operation in ("load", "unload"):
            await self.suite.control(operation)
            await self.suite.wait_control()
            if self.suite.last_error is not None:
                raise RuntimeError("suite_control_failed")
            return
        results = await self.suite.analyze(AnalyzeRequest(
            schema_version="2", extraction_version="legacy-v1",
            posts=[Post(id=str(i), text=text) for i, text in enumerate(texts)],
        ))
        predictions = []
        for result in results:
            check = next(c for c in result.checks if c.checker.id == "tabularis")
            if check.reason == "token_limit_exceeded":
                raise InputTooLong("Each post must fit within 512 tokens")
            if check.status != "completed":
                raise RuntimeError("legacy_checker_failed")
            predictions.append(Prediction(check.output.value, check.coverage.input_tokens))
        return predictions

    async def watch_idle(self):
        await self.suite.watch_idle()

    async def close(self):
        await self.suite.close()
