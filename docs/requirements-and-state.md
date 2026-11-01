# Requirements and current state

Consolidated **1 November 2026** from the user's requests and the repository, updated after explicit approval of decisions A–H. This is the reference for scope and actual state; approval of a validation roster is not evidence of a validated final production suite. Earlier recommendations and UI mockups do not silently override it.

The user approved **A–H**, then separately requested phases 1–4 and explicitly approved the [private LAN/Tailscale HTTPS deployment](private-deployment.md). These slices and the private operational research service are implemented. Chrome manual/live-X acceptance, actual hosted verifier access/adapters, scoring/calibration, and completed-product release remain unfinished; provider access and score/coverage are still launch gates.

## Required product direction

| Area | Requirement |
| --- | --- |
| Architecture | A thin Chrome extension for X, backed by the user's dedicated analysis server. The browser is not the primary inference host. |
| Compute | Prefer the otherwise idle **RTX 3060** on `linux.dimensionlab.net`. CPU work and appropriate hosted APIs are allowed. Do not reserve the active 3090 merely because it is faster. |
| Detection | A **multi-detector system**, including applicable signature/watermark checks. Approved validation roster: Tabularis + E5 + Fakespot + single-Neo Fast-DetectGPT, TMR as challenger, with a separate conditional watermark track. Final membership depends on evidence. |
| Hosted services | Free, unlimited automated use is acceptable if access, terms, and capabilities can be verified. Neither a GPU-only restriction nor permission for paid services should be inferred. A free website or quota-limited free tier is not an unlimited API. |
| Model residency | Approved: lazy load, configurable ten-minute default idle unload, quick Load/Unload, and shared server state. Manual Unload pauses automatic loading until authenticated Load; idle unload allows later on-demand loading. |
| Entry points | Clicking the extension icon opens a compact control panel. Its cogwheel opens a configuration dialog. |
| Feed presentation | A discreet percentage in the post header, immediately before the existing Grok/menu buttons. No automatic hiding, fading, or quality-filtering presentation. |
| Input | Analyze each post's own text. Keep quoted posts separate; do not concatenate replies, author biography, or other posts to manufacture enough evidence. |
| Meaning | Approved target: probability of substantive generated/rewritten wording, including translation and retained mixed text; exclude mechanical/ideas-only assistance. Not truth, quality, bot identity, or fraction of words. No unvalidated combined feed percentage. |
| Unsupported results | Approved explained `—` states and labeled research diagnostics; whole percentages only within validated scope. Missing/failed/unsupported checks are not 0% AI or human evidence. Reduced profiles need validation and explicit acceptance. |
| Exclusions | No Jev or general-purpose LLM judge. Hand-written style/Unicode heuristics must not masquerade as authorship probabilities. Text analysis does not determine whether attached media is AI-generated. |
| Repository | Public-facing documentation and source; no committed credentials. Detector weights, datasets, and services have their own licenses and terms. |

## What exists, and what the evidence supports

| Component | Actual state | Evidence boundary |
| --- | --- | --- |
| Detector research | Source comparisons in [initial research](detector-research.md) and [expanded shortlist](open-source-detectors.md). | Source review nominates candidates; it is not measured accuracy evidence. |
| API server | Authenticated local suite plus CPU watermark-only endpoint, shared ownership; persistent private HTTPS endpoint on the GPU host, enabled non-root service. | Operational research deployment only; no hosted verifier, calibrated probability, public exposure, or completed-product release. |
| V2 contract boundary | Strict requests, typed native evidence, explicit no-estimate, readiness/control schemas, catalog, sanitized failures, and metadata without heavy imports. | Real local evidence only; probability readiness remains false and provider routes disabled. |
| Detector adapters | Tabularis + E5 + Fakespot + single-Neo Fast-DetectGPT; TMR replacement; optional conditional KGW. Pinned detector metadata in [catalog](../detector_server/catalog.py#L1). | Real CPU/3060 inference exercised. KGW requires an exact matching operator scope, not arbitrary provider coverage; learned fusion exists offline only and failed release gates. |
| Current percentage | Legacy v1 projects Tabularis AI-class softmax × 100 with `calibrated_for_x: false`; v2 returns no-estimate aggregates. | The legacy number is not the approved target probability. |
| Deterministic testing | Deployment baseline: **69 Python tests passed on Linux** and **30 Node client tests**. New offline scoring regression tests are documented in the [scoring record](scoring.md#verification-boundary). | Fault-injected OOM is not hardware-OOM stress. Artificial fitting fixtures are not accuracy evidence. Browser/inference evidence is separate. |
| Real-model testing | [Real v2 API/lifecycle smoke](suite-runtime.md#recorded-validation) on the 3060, including 16 near-limit posts, cancellation, manual/idle reload, and restart pause. TMR replacement and explicit CPU also exercised. | Bounded runtime evidence, not accuracy, error complementarity, sustained load, or full product readiness. |
| Remote environment | Earlier isolated test artifacts remain. Private service now uses dedicated `/home/xslop` environment/cache and versioned wheel under `/opt/x-slop-detector`; root-only credential, shared pause state, Caddy and private DNS. | Service enabled/active, paused/unloaded again after the pilot; latest 3060 snapshot 160 MiB residual context and zero allocated/reserved allocator bytes. 3090 snapshot remained 18041 MiB with its existing workload. Historical deployment restart measured 15 MiB; these are different observations. |
| Extension | Unpacked MV3 client; actual Chrome → private HTTPS → real 3060 passed with synthetic text/page. User subsequently reported `—` while testing. | No percentage path exists; systematic live-X/permission/accuracy acceptance and store publication remain open. |
| UI | Working compact toolbar panel and cogwheel configuration with collapsible profile/component/watermark/provider/privacy sections. | Native permission prompt, live-X layout, complete manual keyboard/visual acceptance remain open. Old [SVG concepts](ui/README.md) are historical only. |
| Signature routes | [Conditional KGW CPU adapter and policy registry](watermark-routes.md) implemented; marked/unmarked-AI/wrong-key fixtures tested via real HTTP. | Default unsupported without matching scope; public demo is research-only. No real-world adoption/short-X accuracy established. |
| Provider route policy | Explicit access/application/configuration/approval/support/terms records and derived blockers; no transport, enabled=false, connected=false. | No applications, access grants, free/unlimited entitlement, or live provider validation obtained. Metadata progress cannot activate egress. |
| Suite assessment | [Source comparison](detector-suite-assessment.md); validation roster approved under A and now integrated for local evidence. | No measured error complementarity or final accuracy-selected production membership. |
| Suite feasibility | Earlier [standalone measurements](feasibility-checks.md) followed by [actual API/lifecycle evidence](suite-runtime.md). | Sequential single-post execution; no final percentage, provider validation, or sustained production scheduling evidence. |
| Score semantics | [Target/result policy](score-definition.md) approved under C–D, distinguishing substantive wording, assistance, watermark evidence, and unavailable checks. | Semantics are agreed; pilot candidates fitted/evaluated, but missing target cohorts and deployment-population calibration remain unresolved. |
| Evaluation approach | Protocol approved under E; **818 real pilot evidence records** collected on the 3060 after explicit temporary-resume approval. Nine candidates fitted/frozen/evaluated; exact evaluation reproduced. | [Measured results](scoring-pilot-results.md) are not X calibration. Source rights/domain/size limitations remain; no new contributor consents, rare-FPR proof, or production approval. Shared pause/unload restored. |
| Benchmark repair | [Native-short independent-group gates and private process-record intake](benchmark-acquisition.md) implemented; actual old-pilot refit rejected before a run was created. | Replacement corpus/contributors not yet acquired. Floors and synthetic intake tests are not accuracy evidence; permissions/reviewer identities require real operator verification. |
| Contributor study | User approved pursuing the recommendation; [paid pilot proposal, budget calculator, consent/reviewer drafts and preassigned slot intake](contributor-study.md) prepared. | No recruitment, spend, account terms, public collection hosting or full-study budget approved/commissioned. Participant collector/payment/withdrawal implementation and controller/terms decisions remain required. |
| Combined scoring | [Offline learned fitting/calibration/evaluation/artifact implementation](scoring.md), synthetic regressions plus a real held-out pilot. | **Product validation remains incomplete.** Ensemble benefit not established; calibration worsened held-out probability metrics. Research profiles remain private and undeployed; no feed percentage. |
| Implementation plan | [Phased work, tests, and launch gates](implementation-plan.md); phases 1–4 implemented, private operational deployment separately authorized and completed. | Remaining live/manual/sustained acceptance, calibration, public/product release, actual provider applications/access, and paid calls remain separate. |

The 3060's measured 748 MiB after inference, 132 MiB after unload, and approximately 18–22 ms median short-batch latency apply only to the tested Tabularis process. The initial 3090-first implementation and single-model UI were prototype choices, not requirements.

## Prototype choices, not settled product decisions

- Tabularis as the sole adapter, its pinned version, FP32/eager execution, 512-token limit, batch size, and current API schema.
- One inference slot with busy responses rather than a scheduler for multiple detectors.
- The old dark evergreen/mint single-model SVGs and their exact dimensions. The implemented multi-detector client retains the compact flow/palette but replaces those contents with server-owned suite/route state.
- Earlier rosters such as Tabularis + TMR + E5 + Fast-DetectGPT; A selects Fakespot for the initial roster and TMR as challenger, not a validated final winner.
- Any assumption that multiple agreeing detectors are independent, that a watermark result is infallible, or that their scores can simply be averaged.

The ten-minute configurable idle default and shared manual-pause semantics are approved under F and now implemented across the selected suite. API smoke used a three-second idle timeout to exercise expiry.

## Remaining decisions and evidence gates

1. Final useful membership, error complementarity, and validated local watermark configurations after same-input evaluation.
2. Provider access under acceptable cost/quota/automation/retention terms and acceptable provider/model coverage. B permits planning, not a signature-incomplete launch.
3. Collection consent/use terms, actual corpus acquisition, study size, and numerical minimum recall/coverage before the final test.
4. Deployment-population calibration and validated language/length/missing-checker profiles. The score target is approved; scientific evidence is not supplied by that approval.
5. Sustained/competing-memory behavior beyond the bounded suite lifecycle and near-limit tests already completed.
6. Live-X extraction/layout and manual Chrome permission/keyboard validation; the implemented client's synthetic tests do not settle those.
7. Authorization for subsequent implementation phases/public or completed-product release, and any provider applications or off-server route activation. Private connection details are now recorded in the deployment runbook.

**Approval scope:** A–H approve the design/plan; later comments authorize phases 1–4/tests, private HTTPS deployment, implementation of the combined scoring/validation step, and temporary shared-service resume to collect/fit/evaluate the pilot before restoring pause. The latter does not authorize API/UI percentage activation, deployment of a scoring profile, unrelated service changes, public/store release, provider applications, paid use, contributor agreements, or off-server provider submissions. The shared manual pause was restored and verified. No production scoring profile or signature-incomplete product release has been accepted.

## Work boundary

Requested phases 1–4 are implemented: real local detector evidence, residency, conditional CPU verification, closed provider-policy gates, and the thin research client. Remaining browser/live-X acceptance is recorded separately. This is not accurate combined detection or general provider-signature coverage. Subsequent work and launch gates remain explicit.
