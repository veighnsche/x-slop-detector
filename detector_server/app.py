"""Run with uvicorn detector_server.app:create_app --factory --workers 1."""

import asyncio
import contextlib
import hmac
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from .backend import MODEL_ID, MODEL_REVISION, InputTooLong, TransformersBackend
from .contracts import MAX_BODY_BYTES
from .lifecycle import BusyError, ModelManager, ModelPausedError
from .suite import LegacySuiteManager, LocalSuite
from .v2 import EvidenceSuite, create_router, error_response
from .watermarks import WatermarkRoutes, read_configuration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    token: str
    device: str = "cuda:0"
    idle_seconds: float = 600
    gpu_uuid: str | None = None
    state_dir: str = ".cache/detector-state"
    roberta: str = "fakespot"
    watermark_config: str | None = None

    def __post_init__(self):
        import math

        if len(self.token) < 24 or not self.token.isascii() or any(c.isspace() for c in self.token):
            raise ValueError("DETECTOR_API_TOKEN must be at least 24 non-whitespace ASCII characters")
        if not math.isfinite(self.idle_seconds) or self.idle_seconds < 1:
            raise ValueError("DETECTOR_IDLE_SECONDS must be finite and at least 1")
        if self.roberta not in ("fakespot", "tmr"):
            raise ValueError("DETECTOR_ROBERTA must be fakespot or tmr")
        if self.device != "cpu" and not (
            self.device.startswith("cuda:") and self.device[5:].isdigit()
        ):
            raise ValueError("DETECTOR_DEVICE must be cpu or cuda:<index>")

    @classmethod
    def from_env(cls):
        return cls(
            token=os.environ.get("DETECTOR_API_TOKEN", ""),
            device=os.environ.get("DETECTOR_DEVICE", "cuda:0"),
            idle_seconds=float(os.environ.get("DETECTOR_IDLE_SECONDS", "600")),
            gpu_uuid=os.environ.get("DETECTOR_GPU_UUID") or os.environ.get("CUDA_VISIBLE_DEVICES"),
            state_dir=os.environ.get("DETECTOR_STATE_DIR", ".cache/detector-state"),
            roberta=os.environ.get("DETECTOR_ROBERTA", "fakespot"),
            watermark_config=os.environ.get("DETECTOR_WATERMARK_CONFIG"),
        )


class Post(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Post text must not be blank")
        return value


class DetectRequest(BaseModel):
    posts: Annotated[list[Post], Field(min_length=1, max_length=16)]

    @field_validator("posts")
    @classmethod
    def unique_ids(cls, posts):
        if len({post.id for post in posts}) != len(posts):
            raise ValueError("Post IDs must be unique within a batch")
        return posts


class RequestBoundary:
    """Authenticate before reading a body; bound bytes even without Content-Length."""

    def __init__(self, app, token):
        self.app = app
        self.expected = f"Bearer {token}".encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if not hmac.compare_digest(headers.get(b"authorization", b""), self.expected):
            response = (
                error_response("unauthorized", 401)
                if scope["path"].startswith("/v2/") else
                JSONResponse({"detail": "Unauthorized"}, status_code=401)
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return await response(scope, receive, send)
        body = bytearray()
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            body.extend(event.get("body", b""))
            if len(body) > MAX_BODY_BYTES:
                response = (
                    error_response("body_too_large", 413)
                    if scope["path"].startswith("/v2/") else
                    JSONResponse({"detail": "Request body too large"}, status_code=413)
                )
                return await response(scope, receive, send)
            if not event.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(
    settings: Settings | None = None, backend=None, *, suite: EvidenceSuite | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    suite = suite if suite is not None else LocalSuite(
        settings.device, settings.idle_seconds, settings.state_dir,
        settings.gpu_uuid, settings.roberta,
        watermark_routes=WatermarkRoutes(read_configuration(settings.watermark_config)),
    )
    # Never create a second real model owner for the legacy API. The separate
    # backend injection remains only for legacy deterministic tests.
    manager = LegacySuiteManager(suite) if isinstance(suite, LocalSuite) and backend is None else ModelManager(
        backend if backend is not None else TransformersBackend(settings.device),
        settings.idle_seconds,
    )

    @asynccontextmanager
    async def lifespan(app):
        watcher = asyncio.create_task(manager.watch_idle())
        try:
            yield
        finally:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher
            await manager.close()

    app = FastAPI(
        title="X Slop Detector API", version="0.1.0",
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None,
    )
    app.state.manager = manager
    app.state.suite = suite
    app.add_middleware(RequestBoundary, token=settings.token)
    app.include_router(create_router(suite))

    # FastAPI's default validation response can echo rejected text. Never send
    # submitted post text back in validation errors or log it here.
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        if request.url.path.startswith("/v2/"):
            return error_response("invalid_request", 422)
        return JSONResponse({"detail": "Invalid request fields"}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        if request.url.path.startswith("/v2/"):
            code = {404: "not_found", 405: "method_not_allowed"}.get(
                error.status_code, "operation_failed",
            )
            response = error_response(code, error.status_code)
            if error.headers:
                response.headers.update(error.headers)
            return response
        return JSONResponse({"detail": error.detail}, error.status_code, headers=error.headers)

    async def operate(operation, texts=None):
        try:
            return await manager.operate(operation, texts)
        except BusyError:
            raise HTTPException(409, "Detector busy; retry shortly", headers={"Retry-After": "2"})
        except ModelPausedError:
            raise HTTPException(409, "Detector manually unloaded; press Load to resume")
        except InputTooLong as error:
            raise HTTPException(422, str(error))
        except Exception as error:
            # Exception messages from libraries can contain input data or paths.
            logger.error("Detector operation failed (%s)", type(error).__name__)
            raise HTTPException(503, "Detector operation failed; retry or check server")

    def status():
        return {
            **manager.status(),
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "device": settings.device,
        }

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        current = manager.status()
        if current["state"] != "ready" or current["busy"] or current["paused"]:
            raise HTTPException(503, "Detector is not ready")
        return {"status": "ready"}

    @app.get("/v1/model")
    async def model_status():
        return status()

    @app.post("/v1/model/load")
    async def load():
        await operate("load")
        return status()

    @app.post("/v1/model/unload")
    async def unload():
        await operate("unload")
        return status()

    @app.post("/v1/detect")
    async def detect(payload: DetectRequest):
        predictions = await operate("detect", [post.text for post in payload.posts])
        return {
            "api_status": "legacy_diagnostics",
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "score_kind": "uncalibrated_ai_class_probability",
            "calibrated_for_x": False,
            "results": [
                {
                    "id": post.id,
                    "ai_score": prediction.ai_score,
                    "ai_percentage": round(100 * prediction.ai_score, 1),
                    "tokens": prediction.tokens,
                    "warnings": ["not_validated_for_short_x_posts"],
                }
                for post, prediction in zip(payload.posts, predictions)
            ],
        }

    return app
