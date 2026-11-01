"""Typed v2 evidence boundary. No probability fusion or hosted verification."""

import logging
from typing import Literal, Protocol

from fastapi import APIRouter
from starlette.responses import JSONResponse

from .catalog import CHECKER_CATALOG, INITIAL_ROSTER
from .adapters import ResourceExhausted
from .lifecycle import BusyError, ModelPausedError
from .contracts import (
    AnalysisResult, AnalyzeRequest, AnalyzeResponse, Capabilities, CheckerSpec,
    ComponentState, ControlRequest, ControlResponse, ErrorDetail, ErrorResponse,
    NoEstimate, PostEvidence, ProviderRoute, StatusResponse, SuiteState, validate_check,
)

logger = logging.getLogger(__name__)


class SuiteUnavailable(Exception):
    pass


class EvidenceSuite(Protocol):
    """No aggregate or provider policy can be supplied by an HTTP client."""

    specs: tuple[CheckerSpec, ...]
    watermark_specs: tuple[CheckerSpec, ...]

    def status(self) -> SuiteState: ...
    async def analyze(self, request: AnalyzeRequest) -> list[PostEvidence]: ...
    async def verify_watermarks(self, request: AnalyzeRequest) -> list[PostEvidence]: ...
    async def control(self, action: Literal["load", "unload"]) -> Literal["completed", "pending"]: ...


class UnintegratedSuite:
    specs = INITIAL_ROSTER
    watermark_specs = ()

    def __init__(self, device, idle_seconds):
        self.device = device
        self.idle_seconds = idle_seconds

    def status(self):
        return SuiteState(
            configuration_id="initial-roster-not-integrated-v1",
            integrated=False, paused=False, busy=False, operation="idle",
            configured_device=self.device, idle_timeout_seconds=float(self.idle_seconds),
            components=[
                ComponentState(checker_id=spec.checker.id, required=True, state="unavailable")
                for spec in self.specs
            ],
            provider_routes=[
                ProviderRoute(id=id, access="unconfirmed" if id == "google" else "pending")
                for id in ("anthropic", "openai", "google", "xai")
            ],
        )

    async def analyze(self, request):
        raise SuiteUnavailable()

    async def verify_watermarks(self, request):
        raise SuiteUnavailable()

    async def control(self, action):
        raise SuiteUnavailable()


def error_response(code, status_code, *, retryable=False):
    return JSONResponse(
        ErrorResponse(error=ErrorDetail(code=code, retryable=retryable)).model_dump(mode="json"),
        status_code=status_code,
        headers={"Retry-After": "2"} if retryable else None,
    )


def readiness(state: SuiteState) -> StatusResponse:
    blockers = []
    if not state.integrated:
        blockers.append("suite_not_integrated")
    if state.paused:
        blockers.append("manually_paused")
    if state.busy:
        blockers.append("busy")
    if any(component.required and component.state != "ready" for component in state.components):
        blockers.append("required_components_not_ready")
    return StatusResponse(
        suite=state, diagnostics_ready=not blockers, blockers=[*blockers, "no_validated_profile"],
    )


def create_router(suite: EvidenceSuite):
    router = APIRouter(prefix="/v2")

    @router.get("/capabilities", response_model=Capabilities)
    async def capabilities():
        selected = {spec.checker.id for spec in suite.specs}
        return Capabilities(checkers=[
            *suite.specs, *(spec for spec in CHECKER_CATALOG if spec.checker.id not in selected),
        ])

    def snapshot():
        # Revalidate even model instances received from an internal adapter.
        state = SuiteState.model_validate(suite.status().model_dump())
        expected = {spec.checker.id for spec in suite.specs}
        ids = [component.checker_id for component in state.components]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise ValueError("invalid_component_inventory")
        if not any(component.required for component in state.components):
            raise ValueError("missing_required_components")
        if any(route.enabled for route in state.provider_routes):
            raise ValueError("hosted_routes_not_implemented")
        return readiness(state)

    @router.get("/status", response_model=StatusResponse)
    async def status():
        try:
            return snapshot()
        except Exception as error:
            logger.error("Suite status failed (%s)", type(error).__name__)
            return error_response("operation_failed", 503)

    @router.get("/ready", response_model=StatusResponse)
    async def ready(mode: Literal["diagnostics", "probability"] = "diagnostics"):
        try:
            state = snapshot()
            is_ready = state.diagnostics_ready if mode == "diagnostics" else state.probability_ready
            return JSONResponse(state.model_dump(mode="json"), status_code=200 if is_ready else 503)
        except Exception as error:
            logger.error("Suite readiness failed (%s)", type(error).__name__)
            return error_response("operation_failed", 503)

    async def analyze_request(request: AnalyzeRequest, *, watermarks_only=False):
        try:
            state = snapshot()
            if not state.suite.integrated:
                return error_response("suite_not_integrated", 503)
            if state.suite.paused:
                return error_response("manually_paused", 409)
            if state.suite.busy:
                return error_response("busy", 409, retryable=True)
            selected_specs = getattr(suite, "watermark_specs", ()) if watermarks_only else suite.specs
            if not selected_specs:
                return error_response("suite_not_integrated", 503)
            evidence = (
                await suite.verify_watermarks(request) if watermarks_only
                else await suite.analyze(request)
            )
            if len(evidence) != len(request.posts):
                raise ValueError("invalid_result_count")
            specs = {spec.checker.id: spec for spec in selected_specs}
            required = {c.checker_id for c in state.suite.components if c.required}
            results = []
            for post, raw_result in zip(request.posts, evidence):
                result = PostEvidence.model_validate(raw_result.model_dump())
                if result.id != post.id or {check.checker.id for check in result.checks} != set(specs):
                    raise ValueError("invalid_result_identity")
                for check in result.checks:
                    spec = specs[check.checker.id]
                    validate_check(check, spec, len(post.text))
                missing = any(
                    check.checker.id in required and check.status != "completed"
                    for check in result.checks
                )
                results.append(AnalysisResult(
                    **result.model_dump(), aggregate=NoEstimate(
                        reason="required_evidence_missing" if missing else "no_validated_profile",
                    ),
                ))
            return AnalyzeResponse(
                configuration_id=state.suite.configuration_id,
                extraction_version=request.extraction_version, results=results,
            )
        except SuiteUnavailable:
            return error_response("suite_not_integrated", 503)
        except BusyError:
            return error_response("busy", 409, retryable=True)
        except ModelPausedError:
            return error_response("manually_paused", 409)
        except ResourceExhausted:
            return error_response("resource_exhausted", 503)
        except Exception as error:
            logger.error("Suite analysis failed (%s)", type(error).__name__)
            return error_response("operation_failed", 503)

    @router.post("/analyze", response_model=AnalyzeResponse)
    async def analyze(request: AnalyzeRequest):
        return await analyze_request(request)

    @router.post("/watermarks", response_model=AnalyzeResponse)
    async def verify_watermarks(request: AnalyzeRequest):
        return await analyze_request(request, watermarks_only=True)

    @router.post("/control", response_model=ControlResponse)
    async def control(request: ControlRequest):
        try:
            if not snapshot().suite.integrated:
                return error_response("suite_not_integrated", 503)
            disposition = await suite.control(request.action)
            response = ControlResponse(
                action=request.action, disposition=disposition, status=snapshot(),
            )
            return JSONResponse(
                response.model_dump(mode="json"),
                status_code=202 if disposition == "pending" else 200,
            )
        except SuiteUnavailable:
            return error_response("suite_not_integrated", 503)
        except BusyError:
            return error_response("busy", 409, retryable=True)
        except Exception as error:
            logger.error("Suite control failed (%s)", type(error).__name__)
            return error_response("operation_failed", 503)

    return router
