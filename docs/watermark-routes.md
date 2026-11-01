# Conditional watermark routes and provider policy

**Phase 3 is implemented:** a real CPU KGW-style verification adapter, a watermark-only API, integration with full analysis/shared residency, and a non-callable provider-policy registry. **No provider verifier is connected, access granted, application submitted, or hosted call enabled by this work.** This is not universal signature detection or calibrated authorship scoring.

## What executes

- `POST /v2/analyze` returns the four local detector results **plus an optional `kgw` check**. Its configuration/availability is explicit and it does not change the no-estimate aggregate into a probability.
- `POST /v2/watermarks` accepts the **same strict v2 request envelope**, but executes only conditional CPU verification. It does not load the classifier/Neo weights or select/initialize a GPU. It can work even when the configured classifier GPU is unavailable.
- Both endpoints use the existing bounded slot, cancellation protection, manual pause, idle timer, and Unload. Watermark-only assets participate in idle release even when classifier weights never loaded. Manual Load prewarms the selected suite; watermark-only requests need not call it.
- `GET /v2/status` exposes `local_watermark_routes` and expanded `provider_routes`. Capabilities include the KGW specification; optional routes do not falsely block required-model diagnostic readiness.

Example request:

```json
{
  "schema_version": "2",
  "extraction_version": "own-post-text-v1",
  "posts": [{"id": "post-123", "text": "The original text, unchanged."}]
}
```

Without operator configuration, KGW returns **`unsupported / no_matching_configuration`**, with no numeric output. A scoped but disabled route returns **`unavailable / route_disabled`**. Neither is a completed negative or human vote. HTTP input cannot select keys, configure a route, declare a provider, or authorize a submission.

## Exact supported local configuration

This adapter supports **one whole-passage test with one configured key**, not a sweep of schemes, keys, providers, or sliding windows:

| Property | Fixed configuration |
| --- | --- |
| Tokenizer/config | `openai-community/gpt2`, revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; vocabulary 50,257 |
| Implementation | Transformers **5.22.1**, torch **2.15.0** (build suffix allowed); mismatched/missing implementations report unavailable |
| Matching generation RNG | **CPU**, not arbitrary CUDA-generated KGW output |
| Scheme | `lefthash`, context width 1, green-list ratio 0.25, generation bias 2.0 |
| Decision | Native z score **>4**; repeated bigrams ignored |
| Input | Original unnormalized text, at most **512 tokenizer tokens**; no truncation/padding/concatenation |
| Sparse evidence | At least **32 unique scored bigrams**, otherwise `insufficient_evidence` |
| Retention | Detector n-gram cache disabled; no application text persistence |
| Residency | Tokenizer/config and CPU detector only; **no generator model weights** |

The 32-bigram guard is an operational evidence floor, **not a validated short-post accuracy threshold**. The verifier checks that its unique-bigram count agrees with the library's count. That is a compatibility check, not proof of independent watermark trials, a population false-positive rate, or robustness after arbitrary editing.

The default research key is public demonstration material, not any provider's secret. Keyed verification is useful only for its exact matching signal. **Operator-scoped** means an operator has deliberately selected a legitimate hypothesis/input context; it does not authenticate an individual post's origin. Do not enable a demo configuration on arbitrary X text and describe that as Claude/GPT/Gemini/Grok coverage.

## Server-only configuration

Set `DETECTOR_WATERMARK_CONFIG` to a bounded JSON file read at startup. Unknown fields, duplicate provider IDs, unsupported generation-device settings, multiple keys, and attempts to enable a hosted route are rejected. Invalid configuration fails startup with a sanitized error rather than dumping its contents. No configuration mutation endpoint is exposed.

For **controlled synthetic research only**, a file can contain:

```json
{
  "schema_version": "1",
  "kgw": {
    "enabled": true,
    "applicability": "operator_scoped",
    "purpose": "research_fixture",
    "scope_description": "Controlled public synthetic fixtures only",
    "key_source": "public_fixture",
    "key_id": "public-fixture-key",
    "matching_generation_device": "cpu"
  },
  "providers": []
}
```

This opts into a **research fixture**, not production signature coverage. No such configuration is enabled by default.

For a legitimate non-demo matching channel, use `purpose: "known_configuration"`, `key_source: "environment"`, an explicit non-demo public `key_id`, and `key_env` naming a privately supplied server environment variable. Supply a decimal integer key through the protected environment/secret manager, **not in JSON, repository, request, browser, or chat**. The public fixture key is rejected for this purpose even when supplied through an environment variable. Use non-secret scope descriptions/key aliases.

The key and its environment-variable name are omitted from public metadata/configuration identity. Change/version the public `key_id` whenever key material changes; a label is an operator-managed identity, not verification of a secret. Configuration is fixed for the process lifetime. Public parameters/policy affect the suite identity so clients can invalidate configuration-dependent results.

## Findings retain their native meaning

An actual marked research fixture returned:

```json
{
  "kind": "watermark_detection",
  "decision": "detected",
  "verification_scope": "known_configuration",
  "z_score": 6.813299687492027,
  "p_value": null,
  "tests_performed": 1,
  "configuration_purpose": "research_fixture"
}
```

The native library's p-value approximation was not independently validated, so it is **omitted**, as is its derived “confidence.” No `1 - p`, 100% override, score averaging, or human vote is created. A matching watermark positive is conditional statistical provenance evidence, not cryptographic certainty or proof about the whole post/author. An unmarked AI fixture and wrong-key check can correctly return `not_detected`.

Too-short/repetitive input has no numeric finding. Overlength is unsupported. Missing implementation/invalid key configuration is unavailable; unexpected checker failures preserve a sanitized failed result, not zero. Optional watermark load/failure does not replace/drop the four required detectors or silently select a calibrated profile. Current aggregates remain **`no_estimate`**, including for positive marked text.

One key and one whole-post test is the current multiple-testing policy. Batch/feed scanning does not receive a family-wide false-positive guarantee. Adding keys, windows, schemes, or provider results requires a new explicit policy and validation; do not select the most confident result.

## Provider registry: progress records, not transports

The registry covers Anthropic, OpenAI, Google, and xAI. Defaults record the source-review access gaps, `application_submitted: false`, no approval/configuration, and **`enabled: false`, `connected: false`, `adapter_implemented: false`**.

| Public state | Meaning |
| --- | --- |
| `discovered` | Route identified; access/capability still unconfirmed |
| `access_pending` | Access is an unresolved gate, **not a claim an application was submitted** |
| `configured` | Operator has recorded configuration progress, not a tested API connection |
| `approved` | Operator approval recorded; remaining blockers still apply |
| `unsupported` | Recorded input/capability mismatch |
| `failed` | Recorded configuration/contract failure |

Separate fields retain access, application submission, configuration, approval, support, terms, and free/unlimited-verification records. Blockers are derived from those fields, including missing adapter, access, configuration, approval, coverage, or terms. Operator-provided records are **not independently verified by the server**. Effective connection/enablement remains false even if every progress flag is set true.

Server config may contain provider-policy records for these fields; provider URLs, headers, keys, arbitrary IDs, and `enabled: true` are not accepted. There is **no hosted transport or guessed endpoint**. Body fields cannot activate one. A network-fenced test verifies that even fully approved synthetic policy records cannot cause provider egress.

Actual provider integration still requires authorized access, the real text request/response contract, model/version and length/edit applicability, auth, cost/quotas/automation/retention acceptance, deadlines/rate handling, and live tests. Those requirements were not bypassed or declared solved by adding this registry. The [provider access investigation](signature-checkers.md) remains the access evidence.

## Validation and reproduction

Isolated host directory: `/home/vince/x-slop-watermark-test.ZBoPO7`; pre-existing test venv/model cache reused without modifying dependencies or services. Public synthetic fixtures only. The fixture generator runs separately; actual verification loads no generation model and runs with CUDA hidden.

- **64 tests passed on Linux**; locally 60 passed and four optional inference tests were skipped.
- The same model-free subset passed in a fresh pinned environment. The wheel build passed, with runtime/license contents checked against workspace bytes.
- CPU-only real Uvicorn HTTP matrix: unconfigured, disabled, matching research key, wrong public fixture key; marked/unmarked-AI, sparse/repeated input, overlength, and a whitespace-edited variant. Edited-fixture results are observations, not a robustness guarantee.
- Matching 128-token copied/re-tokenized fixture: **114 scored unique bigrams**, z **6.8133**, detected. Wrong-key fixture: z **−0.3244**, not detected. No p-values or aggregate probabilities were emitted.
- CPU verification warm loopback calls were approximately **131–134 ms** on the tested fixtures. This excludes fixture generation and is not an accuracy/throughput promise.
- The full 3060 API/lifecycle regression passed with an explicitly unsupported default KGW slot; full GPU analysis with the configured CPU fixture verifier returned all five native results and **no-estimate**.
- Provider applications and hosted verifier calls: **none**. All temporary servers stopped; recorded GPU aggregates returned to **15 MiB on the 3060 / 6105 MiB on the 3090**, with the existing ComfyUI processes unchanged.

With pinned artifacts cached and the private server token supplied, generate public controls separately:

```sh
.venv/bin/python scripts/probe_watermark.py \
  --output generation-probe.json --fixtures-output synthetic-fixtures.json
```

That script uses GPT-2 **only to create fixtures** and releases it before its own detection checks. Do not mistake this fixture-generation step for a serving requirement. Start an isolated, loopback-only API process with the research config, `DETECTOR_IDLE_SECONDS=3`, and a separate state directory, then run:

```sh
DETECTOR_URL=http://127.0.0.1:18767 \
.venv/bin/python scripts/smoke_watermark_server.py \
  --fixtures synthetic-fixtures.json --expectation marked --output watermark-smoke.json
```

The HTTP smoke exercises CPU-only idle release/reload and manual pause/unload. It leaves the server paused; restart/resume deliberately. Other expectations are `unconfigured`, `disabled`, and `wrong_key`, each against a matching separate server configuration; there is no client key override.

Raw artifacts include `watermark-final-*.json`, `watermark-release.json`, `synthetic-fixtures.json`, generation/server/smoke logs, `gpu-final.json`, and `combined-release.json`; earlier intermediate runs remain separately. Explicit unload also collects the library's bound-method/LRU reference cycle; a native weak-reference test confirms the verifier is actually released. No user posts, provider secrets, or committed service credentials were collected.

**Still unvalidated/unavailable:** real-world configuration adoption/coverage, empirical short-text false-positive/recall targets, general edit robustness, provider verifier access/terms/auth/quotas, combined calibration, Chrome integration, and production deployment. A working research configuration does not satisfy the provider-signature launch gate.
