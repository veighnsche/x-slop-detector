# V2 API and evidence contract

**Implemented scope:** typed contract, [local suite/residency](suite-runtime.md), and [conditional CPU watermark routes](watermark-routes.md), now used by the Chrome client through the separately approved [private HTTPS deployment](private-deployment.md). Four required detectors are lazy-loaded; optional KGW is unsupported without matching operator configuration. **No calibrated profile or active hosted route** exists. V1 shares the suite locally but is not exposed through the private HTTPS site.

## Endpoints and version negotiation

All endpoints require `Authorization: Bearer <server token>`, including metadata and liveness. No permissive CORS policy or public listener was added.

| Method/path | Contract |
| --- | --- |
| `GET /health` | Existing process liveness. No inference/import of model libraries. |
| `GET /v2/capabilities` | Supported schema version, reviewed candidate catalog, legacy-v1 warning, and admission limits. A catalog entry is **not an integrated adapter**. |
| `GET /v2/status` | Shared suite/control state, component inventory, separate diagnostics/probability readiness, disabled provider routes, and blockers. Does not load anything. |
| `GET /v2/ready?mode=diagnostics` | 200 only for an integrated, unpaused, non-busy suite whose required components are ready; otherwise 503 with the status contract. Initial unloaded state returns 503 without triggering loading. |
| `GET /v2/ready?mode=probability` | 503 in this phase: no validated scoring profile exists, even if a test suite's components are ready. Not a restart/liveness probe. |
| `POST /v2/analyze` | Strict request → lazy-loaded real local evidence and no-estimate aggregates. Ordinary per-check failures/unsupported inputs retain other outcomes; critical load/resource failures are explicit 503s. |
| `POST /v2/watermarks` | Same request/response envelope, but only the optional local KGW check; no classifier weights/GPU initialization. Shared pause, slot, controls, and idle expiry still apply. |
| `POST /v2/control` | Shared Load/Unload: 200 completed or 202 pending, followed by status polling. Unload latches pause before waiting for owned work to finish. |

V2 bodies require `"schema_version": "2"` explicitly. Missing/unsupported/string-vs-number mismatches and unknown fields return sanitized 422 errors. Responses identify schema version 2. Clients must negotiate this contract; they must not fall back to v1's percentage or treat a 503 as a human score.

The injection boundary is a Python `EvidenceSuite` protocol, not a user-supplied model/endpoint selector. The production factory uses `LocalSuite`; unintegrated/fake suites remain test injections only. No environment flag or HTTP option enables fake scores.

## Request

```json
{
  "schema_version": "2",
  "extraction_version": "own-post-text-v1",
  "posts": [
    {"id": "post-123", "text": "The post's own text, unchanged."},
    {"id": "post-456", "text": "Yes."}
  ]
}
```

Identifiers are 1–100 ASCII letters/digits or `.`, `_`, `:`, `-`. Post IDs must be unique within the batch. Text is preserved, not normalized, trimmed, truncated, or combined with quoted/reply text. Whitespace-only inputs are invalid.

Admission limits: **128,000 body bytes**, **1–16 posts**, **1–10,000 Unicode code points per post**. The byte boundary applies while consuming the body, including chunked input. Authentication happens **before** body consumption. No tokenization or heavy import is required to enforce envelope limits.

Token admission is per checker: local configurations have a **512-token cap** and raw-text preprocessing. Actual tokenizer counts and limits are reported; completed local output requires a positive token count, with at least two tokens for Neo. Overlength is per-check `unsupported`, never silent truncation or failure of unrelated posts. Real admission and inference are implemented.

No request field can enable a provider, choose a model/key, supply a calibration profile, or alter probability weights. Invalid envelopes reject the request; valid mixed batches retain IDs/order and explicit per-check outcomes.

## Native evidence, not interchangeable probabilities

Each check identifies its checker, configuration, artifact revision, input coverage/counts, status, and either a native output or a reason. Character coverage must match the original input. Output type must match the selected checker specification.

Illustrative native outputs below are **synthetic contract values**, not detection measurements:

```json
{"kind": "classifier_ai_score", "value": 0.7234, "ai_label_index": 1}
```

```json
{"kind": "token_probability_discrepancy", "value": -2.5}
```

```json
{
  "kind": "watermark_detection",
  "decision": "not_detected",
  "verification_scope": "known_configuration",
  "z_score": -0.3,
  "p_value": 0.6,
  "tests_performed": 1
}
```

Classifier scores and p-values must be finite and within `[0, 1]`; discrepancy/z scores are finite but may be negative or exceed 1. A watermark negative is not a human label; its p-value is never inverted into authorship confidence. Detection scope stays explicit. Research fixture support does not imply provider access or validated short-text power.

The implemented KGW route emits z/decision and `configuration_purpose`, but **omits the unvalidated library p-value approximation** (`p_value: null`). It applies one key/configuration to one whole passage only. Default full analysis includes a fifth optional KGW result, `unsupported / no_matching_configuration`; it is not silently counted as a negative.

| Check status | Output / reason rule |
| --- | --- |
| `completed` | Native output required; no failure reason. Watermark decision is detected/not-detected/inconclusive, not an aggregate percentage. |
| `unavailable` | No output. Reasons include adapter not integrated, access pending, route disabled, model not loaded, or manually paused. |
| `unsupported` | No output. Token limit, language, or no matching watermark configuration. |
| `insufficient_evidence` | No output. Too little signal or no next-token observations. |
| `failed` | No output. Sanitized checker error or invalid checker output. |
| `timed_out` | No output. Explicit checker timeout. |

Unsuccessful checks cannot contain a numeric output, not even zero. Unknown status/reason combinations, duplicate/missing/unknown checkers, mismatched revisions, changed input coverage, wrong native output types, and non-finite results are rejected by the boundary. Malformed internal results return a sanitized 503, not a partial fabricated success. An adapter that encounters an ordinary per-check failure must return the corresponding typed failure instead.

## Aggregate and readiness

Every successful v2 analysis response has `calibration_status: "not_configured"`. Each result has one of:

```json
{
  "kind": "no_estimate",
  "target_id": "substantive_llm_wording_v1",
  "reason": "no_validated_profile"
}
```

or the same shape with `"reason": "required_evidence_missing"` if a required check did not complete. Both are **no estimate**, not 0%, 50%, or proof of human writing. Optional watermark negatives do not automatically lower an aggregate.

The schema reserves a distinct probability shape with profile ID, calibration-artifact hash, and validation-scope ID. **Current analysis responses reject that shape unconditionally.** It is reserved for later artifact/support validation, not activated by adding metadata or an “experimental” flag. There is no scoring/fusion implementation here.

Status distinguishes:

- The suite's configuration ID, integration flag, configured device, and **verified GPU UUID**. The latter is null until actual verification; `cuda:0` is not proof of the selected physical GPU.
- Required component residency and diagnostic readiness. A partially loaded/failed required component cannot claim ready or silently select a smaller profile.
- Shared pause/busy state, `pause_persisted`, pending control, sanitized last error, idle countdown, and per-provider access/approval/enabled state. Optional device-memory counters do not import/init CUDA merely for status.
- Conditional local-route scope/purpose/public key alias, CPU residency, sparse-input floor, and blocker. No secret key or key-environment name is exposed.
- `probability_ready: false` and `no_validated_profile`, independently of whether model diagnostics are ready.

Provider routes remain disabled: the model and boundary reject enabled hosted routes because no transport exists. The expanded registry derives progress/blockers from server-only access, application, configuration, approval, support, and terms records. A synthetic “approved” record still cannot connect a provider. No endpoint, auth, quota, deadline, or retention contract is invented; real access/live validation is still required.

The control request is:

```json
{"schema_version": "2", "action": "unload"}
```

The response carries action, `disposition` (`completed` or `pending`), and the full status snapshot. Shared suite controls, persistent manual pause, cancellation-safe ownership, and idle unload/reload are implemented and real-API tested. There is at most one pending control transition and no queued analysis.

## Error/privacy boundary and v1 migration

V2 errors use:

```json
{"schema_version": "2", "error": {"code": "invalid_request", "retryable": false}}
```

Codes/statuses: `unauthorized`/401; `body_too_large`/413; `invalid_request`/422; `busy` or `manually_paused`/409; `resource_exhausted`, `suite_not_integrated`, or `operation_failed`/503; `not_found`/404; `method_not_allowed`/405. Busy errors include bounded retry guidance. Readiness failure uses its richer status body instead of this error envelope.

Validation errors never echo input text or extra fields. Unexpected backend failures log only the exception class, not its message, request, or stack. Successful results return client IDs and coverage metadata but not submitted text. Default execution has no text persistence, hosted call, or result cache. The private deployment adds source restrictions, proxy body/time limits and access-log policy; these are **not** a claim of complete internet-facing abuse protection or authorization for public exposure.

V1 keeps its paths and numeric fields, with `api_status: "legacy_diagnostics"` and `calibrated_for_x: false`. The real factory projects Tabularis diagnostics from the shared suite; its controls now use the same ownership/pause rather than creating a second model copy. These fields are not the aggregate target. See the [shared runtime](suite-runtime.md#legacy-compatibility-without-a-second-model-owner) for compatibility details.

## Reproduce the contract tests without model dependencies

From the repository, using a disposable or dedicated Python **3.11+** environment:

```sh
uv venv --python 3.11 .venv-contract
uv pip sync --python .venv-contract/bin/python requirements/contract-tests.txt
.venv-contract/bin/python -m unittest discover -s tests -v
```

`uv pip sync` removes packages not in that file; this dedicated environment keeps an existing inference `.venv` untouched. No editable install is necessary when running these commands at the repository root. The pinned file contains the complete tested web/test dependency set, **not** CUDA/inference packages, wheel hashes, or a Linux GPU lock.

The model-free subset runs without torch/transformers; four optional inference tests are skipped in that environment. A fresh-process test verifies metadata does not import either library. Linux versions are captured in `requirements/linux-cu132-observed.txt`; this is an observed snapshot, not a rebuilt/hash-locked inference environment.

**Server validation:** 69 tests passed on Linux; 65 passed locally and four optional inference tests skipped. Real CPU-watermark HTTP, combined GPU/local-watermark, and default-suite lifecycle regression checks passed. [Watermark evidence](watermark-routes.md#validation-and-reproduction) and [phase-2 measurements](suite-runtime.md#recorded-validation) remain bounded operational checks. The subsequent [private deployment](private-deployment.md#actual-runtime-and-browser) adds actual Chrome/HTTPS/3060 evidence and cold-import regression coverage; no live-X, hosted-verifier, or accuracy benchmark was run.

Lightweight dependency license inventory from installed package metadata:

| License | Packages |
| --- | --- |
| MIT | annotated-doc, annotated-types, anyio, fastapi, h11, pydantic, pydantic-core, typing-inspection |
| BSD-3-Clause | click, httpcore, httpx, idna, starlette, uvicorn |
| PSF-2.0 | typing-extensions |
| Apache-2.0 | opentelemetry-api |
| MPL-2.0 | certifi |

No telemetry exporter is configured by this work. Preserve dependency licenses/notices when distributing them; this inventory is not a bundled-license audit. Reviewed model/method revisions and declared licenses are centralized in the checker catalog, with provenance in the [suite assessment](detector-suite-assessment.md#source-revisions-observed). No model assets or research watermark secrets were added to the repository.
