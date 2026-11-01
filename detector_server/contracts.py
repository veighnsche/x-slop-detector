"""V2 wire contracts. No model imports, weights, inference, or score fusion."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

MAX_BODY_BYTES = 128_000
MAX_POSTS = 16
MAX_TEXT_CHARACTERS = 10_000
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._:-]+$")]
UnitInterval = Annotated[FiniteFloat, Field(ge=0, le=1)]
Count = Annotated[int, Field(ge=0)]
TARGET_ID = "substantive_llm_wording_v1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Post(Contract):
    id: Identifier
    text: Annotated[str, Field(min_length=1, max_length=MAX_TEXT_CHARACTERS)]

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("blank_input")
        return value


class AnalyzeRequest(Contract):
    schema_version: Literal["2"]
    extraction_version: Identifier
    posts: Annotated[list[Post], Field(min_length=1, max_length=MAX_POSTS)]

    @field_validator("posts")
    @classmethod
    def unique_ids(cls, posts):
        if len({post.id for post in posts}) != len(posts):
            raise ValueError("duplicate_post_ids")
        return posts


class CheckerRef(Contract):
    id: Identifier
    configuration_id: Identifier
    artifact_revision: str


class CheckerSpec(Contract):
    checker: CheckerRef
    kind: Literal["classifier", "statistical", "watermark"]
    role: Literal["candidate", "challenger", "research_fixture", "conditional_verifier"]
    artifact_id: str
    license: str
    method_revision: str | None = None
    precision: Literal["float32", "float16", "not_applicable"]
    ai_label_index: Literal[1] | None = None
    max_tokens: Annotated[int, Field(ge=1)] | None
    preprocessing: Literal["raw_text"]


class Coverage(Contract):
    characters: Count
    input_tokens: Count | None = None
    scored_tokens: Count | None = None
    token_limit: Annotated[int, Field(ge=1)] | None = None
    truncated: Literal[False] = False

    @model_validator(mode="after")
    def counts_agree(self):
        if self.scored_tokens is not None and self.input_tokens is not None:
            if self.scored_tokens > self.input_tokens:
                raise ValueError("invalid_scored_token_count")
        return self


class ClassifierScore(Contract):
    kind: Literal["classifier_ai_score"] = "classifier_ai_score"
    value: UnitInterval
    ai_label_index: Literal[1] = 1


class Discrepancy(Contract):
    kind: Literal["token_probability_discrepancy"] = "token_probability_discrepancy"
    value: FiniteFloat


class WatermarkFinding(Contract):
    kind: Literal["watermark_detection"] = "watermark_detection"
    decision: Literal["detected", "not_detected", "inconclusive"]
    verification_scope: Literal["known_configuration", "provider"]
    z_score: FiniteFloat | None = None
    p_value: UnitInterval | None = None
    tests_performed: Annotated[int, Field(ge=1)] = 1
    configuration_purpose: Literal["research_fixture", "known_configuration"] | None = None


NativeOutput = Annotated[
    ClassifierScore | Discrepancy | WatermarkFinding, Field(discriminator="kind")
]
CheckStatus = Literal[
    "completed", "unavailable", "unsupported", "insufficient_evidence", "failed", "timed_out"
]
Reason = Literal[
    "adapter_not_integrated", "access_pending", "route_disabled", "model_not_loaded",
    "manually_paused", "token_limit_exceeded", "unsupported_language",
    "no_matching_configuration", "too_little_signal", "no_next_token_observations",
    "checker_error", "invalid_checker_output", "checker_timeout",
    "configuration_invalid", "implementation_unavailable",
]
REASONS_BY_STATUS = {
    "unavailable": {
        "adapter_not_integrated", "access_pending", "route_disabled",
        "model_not_loaded", "manually_paused",
        "configuration_invalid", "implementation_unavailable",
    },
    "unsupported": {"token_limit_exceeded", "unsupported_language", "no_matching_configuration"},
    "insufficient_evidence": {"too_little_signal", "no_next_token_observations"},
    "failed": {"checker_error", "invalid_checker_output"},
    "timed_out": {"checker_timeout"},
}


class CheckEvidence(Contract):
    checker: CheckerRef
    status: CheckStatus
    coverage: Coverage
    output: NativeOutput | None = None
    reason: Reason | None = None

    @model_validator(mode="after")
    def result_matches_status(self):
        if self.status == "completed":
            if self.output is None or self.reason is not None:
                raise ValueError("completed_check_requires_output_only")
            if (
                self.coverage.input_tokens is not None
                and self.coverage.token_limit is not None
                and self.coverage.input_tokens > self.coverage.token_limit
            ):
                raise ValueError("completed_check_exceeds_token_limit")
        elif self.output is not None or self.reason not in REASONS_BY_STATUS[self.status]:
            raise ValueError("incomplete_check_requires_reason_without_output")
        return self


def validate_check(check: CheckEvidence, spec: CheckerSpec, characters: int):
    """Shared adapter/API invariant; never reinterpret a native value."""
    if check.checker != spec.checker or check.coverage.characters != characters:
        raise ValueError("invalid_evidence_configuration")
    if check.coverage.token_limit != spec.max_tokens:
        raise ValueError("invalid_token_contract")
    if check.output is not None:
        expected = {
            "classifier": "classifier_ai_score",
            "statistical": "token_probability_discrepancy",
            "watermark": "watermark_detection",
        }[spec.kind]
        if check.output.kind != expected:
            raise ValueError("invalid_native_output_kind")
        if spec.kind in ("classifier", "statistical"):
            if check.coverage.input_tokens is None or check.coverage.input_tokens < 1:
                raise ValueError("missing_local_token_count")
            if spec.kind == "statistical" and check.coverage.input_tokens < 2:
                raise ValueError("insufficient_next_token_observations")


class PostEvidence(Contract):
    id: Identifier
    checks: Annotated[list[CheckEvidence], Field(min_length=1)]

    @field_validator("checks")
    @classmethod
    def unique_checkers(cls, checks):
        if len({check.checker.id for check in checks}) != len(checks):
            raise ValueError("duplicate_checker_ids")
        return checks


class NoEstimate(Contract):
    kind: Literal["no_estimate"] = "no_estimate"
    target_id: Literal["substantive_llm_wording_v1"] = TARGET_ID
    reason: Literal["no_validated_profile", "required_evidence_missing"]


class ProbabilityEstimate(Contract):
    """Reserved for validated scoring artifacts; the phase-1 API never emits this."""

    kind: Literal["probability"] = "probability"
    target_id: Literal["substantive_llm_wording_v1"] = TARGET_ID
    probability: UnitInterval
    profile_id: Identifier
    calibration_artifact_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    validation_scope_id: Identifier


Aggregate = Annotated[NoEstimate | ProbabilityEstimate, Field(discriminator="kind")]


class AnalysisResult(PostEvidence):
    aggregate: Aggregate


class AnalyzeResponse(Contract):
    schema_version: Literal["2"] = "2"
    configuration_id: Identifier
    extraction_version: Identifier
    # No calibrated profile is installed in phase 1. A later scoring change
    # must extend this contract and implement artifact/support validation.
    calibration_status: Literal["not_configured"] = "not_configured"
    results: list[AnalysisResult]

    @model_validator(mode="after")
    def no_probability_without_validation(self):
        if any(isinstance(result.aggregate, ProbabilityEstimate) for result in self.results):
            raise ValueError("no_validated_scoring_profile")
        return self


class ComponentState(Contract):
    checker_id: Identifier
    required: bool
    state: Literal["unavailable", "unloaded", "loading", "ready", "unloading", "error"]


class ProviderRoute(Contract):
    id: Literal["anthropic", "openai", "google", "xai"]
    access: Literal["pending", "unconfirmed", "granted"]
    application_submitted: bool = False
    approved: bool = False
    enabled: bool = False
    configured: bool = False
    support: Literal["unconfirmed", "supported", "unsupported"] = "unconfirmed"
    terms_approved: bool = False
    free_unlimited_verified: bool = False
    failure: Literal["configuration_invalid", "contract_unverified"] | None = None
    adapter_implemented: Literal[False] = False
    connected: Literal[False] = False
    state: Literal[
        "discovered", "access_pending", "configured", "approved", "unsupported", "failed",
    ] = "discovered"
    blockers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enabled_requires_access_and_approval(self):
        if self.enabled:
            raise ValueError("provider_adapter_not_integrated")
        state = (
            "failed" if self.failure else
            "unsupported" if self.support == "unsupported" else
            "approved" if self.approved else
            "configured" if self.configured else
            "access_pending" if self.access == "pending" else "discovered"
        )
        blockers = ["adapter_not_integrated"]
        if self.access != "granted":
            blockers.append("access_pending" if self.access == "pending" else "access_unconfirmed")
        if not self.configured:
            blockers.append("configuration_missing")
        if not self.approved:
            blockers.append("approval_missing")
        if self.support != "supported":
            blockers.append("unsupported_input" if self.support == "unsupported" else "coverage_unverified")
        if not self.terms_approved:
            blockers.append("terms_unapproved")
        if not self.free_unlimited_verified:
            blockers.append("free_unlimited_unverified")
        if self.failure:
            blockers.append(self.failure)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "blockers", blockers)
        return self


class LocalWatermarkRoute(Contract):
    id: Literal["kgw"] = "kgw"
    configuration_id: Identifier
    configured: bool
    enabled: bool
    applicability: Literal["unconfigured", "operator_scoped"]
    purpose: Literal["research_fixture", "known_configuration"]
    key_id: Identifier | None = None
    scope_description: str | None = None
    state: Literal["unavailable", "unloaded", "ready", "error"]
    blocker: Literal[
        "no_matching_configuration", "route_disabled", "configuration_invalid",
        "implementation_unavailable",
    ] | None = None
    device: Literal["cpu"] = "cpu"
    minimum_unique_bigrams: int = 32
    tests_performed_per_post: Literal[1] = 1
    p_value_policy: Literal["omitted_unvalidated_library_approximation"] = "omitted_unvalidated_library_approximation"


class DeviceMemory(Contract):
    allocated_bytes: Count
    reserved_bytes: Count
    peak_allocated_bytes: Count
    peak_reserved_bytes: Count


class SuiteState(Contract):
    configuration_id: Identifier
    integrated: bool
    paused: bool
    pause_persisted: bool = True
    busy: bool
    operation: Literal["idle", "loading", "analyzing", "unloading"]
    pending_control: Literal["load", "unload"] | None = None
    last_error: Literal[
        "device_configuration_error", "load_failed", "unload_failed",
        "inference_failed", "out_of_memory", "state_persistence_failed",
    ] | None = None
    configured_device: str
    verified_gpu_uuid: str | None = None
    device_memory: DeviceMemory | None = None
    idle_timeout_seconds: Annotated[FiniteFloat, Field(ge=1)]
    unload_in_seconds: Annotated[FiniteFloat, Field(ge=0)] | None = None
    components: Annotated[list[ComponentState], Field(min_length=1)]
    provider_routes: list[ProviderRoute]
    local_watermark_routes: list[LocalWatermarkRoute] = Field(default_factory=list)


class StatusResponse(Contract):
    schema_version: Literal["2"] = "2"
    suite: SuiteState
    diagnostics_ready: bool
    probability_ready: Literal[False] = False
    calibration_status: Literal["not_configured"] = "not_configured"
    blockers: list[Literal[
        "suite_not_integrated", "manually_paused", "busy", "required_components_not_ready",
        "no_validated_profile",
    ]]


class ControlRequest(Contract):
    schema_version: Literal["2"]
    action: Literal["load", "unload"]


class ControlResponse(Contract):
    schema_version: Literal["2"] = "2"
    action: Literal["load", "unload"]
    disposition: Literal["completed", "pending"]
    status: StatusResponse


class Limits(Contract):
    max_body_bytes: int = MAX_BODY_BYTES
    max_posts: int = MAX_POSTS
    max_text_characters: int = MAX_TEXT_CHARACTERS
    local_execution_slots: Literal[1] = 1
    queued_analysis_requests: Literal[0] = 0
    hosted_requests_enabled: Literal[False] = False


class Capabilities(Contract):
    schema_version: Literal["2"] = "2"
    supported_schema_versions: list[Literal["2"]] = ["2"]
    legacy_v1: Literal["uncalibrated_tabularis_diagnostics"] = "uncalibrated_tabularis_diagnostics"
    checkers: list[CheckerSpec]
    limits: Limits = Field(default_factory=Limits)


ErrorCode = Literal[
    "unauthorized", "body_too_large", "invalid_request", "suite_not_integrated",
    "busy", "manually_paused", "operation_failed", "not_found", "method_not_allowed",
    "resource_exhausted",
]


class ErrorDetail(Contract):
    code: ErrorCode
    retryable: bool = False


class ErrorResponse(Contract):
    schema_version: Literal["2"] = "2"
    error: ErrorDetail
