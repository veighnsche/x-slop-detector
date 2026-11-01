# Multi-detector design brief and approval decisions

Prepared **1 November 2026** from the prerequisite investigations. **Decisions A–H subsequently approved** by the user's explicit “approve a-h.” Approval selects the recommended directions, including writing the [implementation plan](implementation-plan.md); it does not authorize implementation/deployment or certify accuracy/access. The earlier “go” responses authorized investigations only.

**Historical decision snapshot:** the state descriptions below are from before implementation. Later explicit approvals implemented phases 1–4; see [current state](requirements-and-state.md) and [Chrome client](extension.md). The original approval record is preserved rather than rewritten as if these results existed during research.

## 1. Product boundary and current state

The requested product is a thin Chrome extension for X, backed by the user's dedicated server. The server uses the passive **RTX 3060**, CPU, and acceptable hosted verification; it must not silently consume the active 3090. Analyze each post's own text, with quoted posts separate. Keep the discreet header-result location, no hiding/fading, and compact control-panel → cogwheel configuration flow.

Load on demand, reuse while active, unload after an idle interval, and offer quick manual Load/Unload. Multi-detector and applicable watermark evidence are required tracks; one classifier or a Unicode scanner is not a substitute.

**What exists:** a Tabularis-only API prototype; standalone multi-model and known-key watermark probes; research and static UI concepts. **What does not:** production ensemble adapters, learned fusion/calibration, provider verification access, a Chrome extension, or a deployed production service. See [requirements and state](requirements-and-state.md).

## 2. Proposed detector/checker suite

Recommend this **validation roster**, not unconditional permanent membership:

| Component | Role and reason | Qualification |
| --- | --- | --- |
| Tabularis ModernBERT | Existing supervised-classifier baseline | Existing integration is not proof of best accuracy. |
| E5-small | Compact classifier with documented tweet/rewrite training | No held-out short-X accuracy established. |
| Fakespot RoBERTa | Preferred additional classifier, with a broader documented training pool | Shares RAID exposure with the other encoders; not independent evidence. |
| Fast-DetectGPT, one GPT-Neo-2.7B used for both roles | Statistical token-probability discrepancy, distinct from a trained binary head | Use this measured configuration, not the heavier Falcon defaults or demo probability conversion. |
| TMR | Controlled challenger to Fakespot | Compare rather than automatically add a fifth agreeing score. |
| Known-configuration local watermark verification | Start validation with the tested KGW-style CPU path | Only recognizes its matching scheme/tokenizer/key/configuration; the demo key does not cover arbitrary commercial output. |
| Provider watermark verification | Retain Anthropic, OpenAI, Google, and xAI as explicit access tracks | None is currently usable by this project. Do not list these as connected detectors. |

For local verification, use only justified, legitimately available matching configurations; do not sweep arbitrary demo keys and call that provider coverage. SynthID Text, TextSeal, and other public/asymmetric schemes remain conditional candidates, not additional tested adapters.

Keep or replace members based on same-input evaluation and incremental value. Do not silently remove the statistical/signature tracks or regress to one model if they disappoint; bring that scope decision back. Stock Binoculars and heavier/specially licensed candidates are deferred for the reasons in the [suite assessment](detector-suite-assessment.md).

## 3. Verified access and licensing

| Route | Evidence established | Remaining limits |
| --- | --- | --- |
| Tabularis, E5, TMR | Public weights, declared MIT licenses; downloaded/executed in earlier probes | Preserve notices and review packaged dependencies/assets before distribution. Weight licensing does not establish rights to all training or evaluation source text. |
| Fakespot | Public weights, Apache-2.0 declaration; executed in earlier probes | Preserve applicable license/notice requirements; preprocessing and exact checkpoint training coverage need care. |
| Fast-DetectGPT + GPT-Neo | MIT method code and MIT model; selected configuration executed | Pin source/model/precision; the demo's fitted percentage is not our calibration. |
| Local watermark tooling | Source licenses recorded for KGW, SynthID Text, TextSeal, and MarkLLM; known-key CPU verification exercised through Transformers | These are distinct implementations, not interchangeable adapters. No production provider keys/configurations supplied. Separate model/tokenizer/dependency licenses apply. |
| Anthropic/OpenAI | Official gated text-verification access routes identified | No approval, usable text API contract/credentials, or verified free/unlimited automation and retention terms. |
| Google | Official open-source text watermark code and hosted product material identified | Current authorized automated hosted text-verification access remains unconfirmed. |
| xAI | Official team-admin application route identified; source schedules marking from 7 November 2026 | Future relative to this review; no access grant, usable contract, or verified free/unlimited entitlement. |
| Evaluation data | Concrete consented-collection/local-generation route proposed | No collected corpus/consents. MultiSocial is restricted with conflicting use statements; RAID overlaps detector training. |

**No reviewed hosted route satisfies all required access, relevant text coverage, free pricing, unlimited automation, and acceptable retention today.** That is an unresolved access finding, not a claim that no such service exists. A free web page or a normal generation API key does not resolve it.

License/source details and observed revisions: [detectors](detector-suite-assessment.md#source-revisions-observed), [signature tooling/access register](signature-checkers.md#access-register-and-unresolved-facts), and [evaluation sources](evaluation.md#1-acquire-evidence-backed-examples). This brief summarizes prior evidence; it does not renew provider terms or substitute for a distribution license audit.

## 4. Measured hardware feasibility

Earlier standalone probes on the **12 GiB RTX 3060** established:

| Measurement | Recorded result |
| --- | --- |
| Tabularis + E5 + Fakespot + Neo resident after inference | **7142 MiB ≈ 6.97 GiB** process VRAM |
| Four-model suite, two short posts | **101 ms median** for all four outputs |
| Four-model suite, 16 short posts | **535 ms median** for all four outputs |
| Ordered cached suite-load calls | **5.62 seconds total** in the tested fresh process |
| Adding TMR alongside the four | **7290 MiB ≈ 7.12 GiB** after its short inference |
| Known-key 128-token CPU watermark verification | **89.7 ms median**, generator already released |
| Release | PyTorch allocated/reserved memory returned to zero; about **140 MiB** process overhead remained until exit |

All four encoders and Neo also ran on CPU. Neo's tested short CPU call was about **916 ms**, versus **31 ms** warm on GPU; CPU is not an equivalent fast fallback. CPU/GPU Neo outputs were not numerically identical.

These were **co-resident models executed sequentially**, bounded synthetic inputs, and a 512-token probe cap. Timings exclude HTTP, network, queueing, and extension overhead. They do not establish accuracy, concurrency, worst-case memory, full API load/unload behavior, or sustained throughput. The active 3090 was unchanged in the recorded before/after checks; the host was not re-inspected for this brief. See [exact measurements and boundaries](feasibility-checks.md).

## 5. Proposed score meaning and evidence handling

Recommend: **probability that the post's own text contains substantive LLM-generated or LLM-rewritten wording**.

- Include generated drafts, retained generated wording after editing, substantive rewrites, translation, and mixed writing.
- Exclude ideas/research assistance and merely mechanical spelling/punctuation/grammar corrections. Preserve those as separate evaluation cohorts.
- This is not the fraction of words generated, a detector-vote percentage, a bot score, a truth judgment, or proof about the poster. Quoted material needs attribution-aware interpretation.
- Preserve each model's native output and each watermark result. Watermark evidence is conditional provenance evidence, not an automatic 100%; a negative does not prove human writing.
- Learn a combination from target-aligned data, initially testing regularized logistic stacking and separate sigmoid calibration. No arbitrary mean, manual weights, or `1 - p-value` conversion. No coefficients or calibration have been fitted.
- Keep disagreement, failed checks, unsupported input, and inaccessible providers visible. A reduced suite may produce a percentage only under an identified, validated, approved profile; never silently substitute zero or renormalize.

Recommend **no unvalidated combined feed percentage**, even if called experimental. Raw per-detector diagnostics may support research. A later experimental probability needs held-out evidence for its stated scope; unknown deployment prevalence/population remains a calibration limitation. Propose whole percentages for supported results and a discreet `—` with an explanation otherwise, subject to UI approval. This does not claim that incomplete coverage fulfills the requested experience.

Full semantics: [score-definition proposal](score-definition.md). Validation route: [evaluation/calibration proposal](evaluation.md), including independent grouped splits, unseen-generator challenges, false positives, recall, coverage, and calibration. A balanced benchmark is not automatically a calibrated probability for X.

## 6. Known gaps and blockers

| Gap | What it blocks | Required evidence or decision |
| --- | --- | --- |
| No granted provider text verification | Claiming provider signature coverage or shipping a profile that requires it | Authorized access plus coverage, automation, cost/quota, retention, and live input validation; otherwise explicit scope reconsideration. |
| Known-key local check only | Claiming broad real-world watermark detection | Legitimately available matching configurations and representative tests; a synthetic success is insufficient. |
| No provenance-backed corpus or fitted combination | Reliable combined score and incremental-accuracy claims | Collect permitted human/AI/mixed data, compare individual/suite outputs, fit and independently evaluate. |
| Unknown deployment population/prevalence | Universal “probability of AI on X” claims | Defensible target-population evidence/assumptions, validation, and agreed claim limits. |
| Short/language/edited-text coverage unvalidated | Promising a meaningful number on every post | Cohort-specific evidence and approved unsupported-result behavior. English-first evaluation is not approval of an English-only product. |
| Prototype lifecycle covers one model only | Full-suite readiness/load/unload/concurrency guarantees | Later implementation and tests for all local components and request states. |
| No real extension or expanded configuration | End-to-end X extraction, evidence preservation, settings and user controls | Later implementation after decisions; current mockups are not final. |
| Deployment/security/privacy contract unfinished | Safe remotely accessible operation and off-server submissions | Authenticated secure transport, secret handling, data-flow/retention choices, and separately authorized deployment. |

These do not all prevent writing a conditional implementation plan. They **do** prevent presenting the desired system as finished or accurately calibrated. No full benchmark is required before planning, but no unresolved gate should disappear from that plan.

## 7. Specific decisions for approval

**Approval record:** the user explicitly approved **A–H**, selecting the recommended-choice column below, not the alternatives. The table preserves the choices and consequences reviewed. Approval chooses the direction; it does not certify evidence, grant provider access, approve a signature-incomplete release, or guarantee accuracy.

| ID | Decision and recommended choice | Alternative / consequence |
| --- | --- | --- |
| **A — Validation suite** | Approve Tabularis + E5 + Fakespot + single-Neo Fast-DetectGPT as the initial roster; TMR is a challenger. Keep conditional watermark verification as a separate track. Final membership depends on evaluation. | Change the roster or require an additional comparison now. No final accuracy winner is known. |
| **B — Signature gate** | Allow planning local multi-detector development while keeping production provider verification an explicit **unresolved launch gate**. Do not approve a signature-incomplete release by approving this brief. | Require provider access before even writing the implementation plan. Acceptable provider/model coverage must be approved once access is known; one accessible provider is not general coverage. Any later decision to ship without provider verification needs separate explicit approval. |
| **C — Percentage target** | Approve substantive generated/rewritten wording, including translation and retained mixed text; exclude mechanical/ideas-only assistance. | Choose fully generated text only or another target; labels and calibration must change before fitting. |
| **D — Honest result policy** | Approve raw research diagnostics, no unvalidated combined feed percentage, whole percentages only within validated scope, and explained `—` states otherwise. Identify approved reduced-checker profiles. | Reconsider whether a differently named non-probability indicator is wanted. It cannot silently replace the requested probability, and arbitrary averaging remains unjustified. |
| **E — Evaluation direction** | Approve the provenance-backed pilot/staged protocol, English-first primary study (not a final product restriction), learned fusion, separate calibration and holdout; nominal **0.5% FPR** primary / **1%** comparison targets. | Change scope/targets. Numerical minimum recall/coverage and full study size still need pilot-informed agreement before the final test; these FPR targets are not achieved guarantees. No recruitment or data-sharing terms accepted by this approval alone. |
| **F — Residency controls** | Keep local inference on the 3060/CPU, no automatic 3090 spillover. Propose a configurable **10-minute idle timeout**; Load loads the selected local suite and clears manual pause, Unload safely releases local models and globally pauses automatic loading until authenticated Load. Idle unload still permits later on-demand loading. Show shared server state in every client. | Choose another interval or per-client ownership semantics. One-click Load may take several seconds; Load/Unload controls do not make GPU work instantaneous. This extends the prototype behavior, not an already tested suite lifecycle. |
| **G — Privacy/configuration boundary** | Default to local-server processing; provider routes disabled until individually approved after terms/retention review. Keep provider credentials server-side; extension holds only its server connection credential locally, not in sync. Show route applicability/access/status and reasons in the expanded configuration, not user-invented probability weights. | Permit specific off-server routes explicitly, with accepted data handling. No provider applications, organization submissions, paid usage, public endpoint exposure, or remote-service changes are authorized merely by approving the design. |
| **H — Next deliverable** | After resolving A–G, authorize writing the **implementation plan only**, with the gates and tests carried forward. | Revise this brief first. Implementation, deployment, and provider applications remain separate authorizations. |

**Result:** proceed with the implementation plan under H, carrying the gates and tests forward. Actual implementation, deployment, provider applications, paid use, and off-server route activation still need their specific authorizations. Pilot-informed recall/coverage criteria and acceptable provider/model coverage remain future evidence-dependent decisions. The compact panel/configuration flow is approved; old single-model SVG contents and dimensions are not final.
