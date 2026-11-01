# Text signature and watermark checker investigation

Source/access review: **1 November 2026 (UTC)**. This is prerequisite research, **not an implementation plan**. Scope includes hosted verification, CPU-capable local detection, public-key approaches, and artifact/file checks; it is not restricted to GPU inference.

**Subsequent execution:** [bounded feasibility checks](feasibility-checks.md#local-watermark-feasibility) exercised one self-configured KGW-style CPU verifier with marked/unmarked/wrong-key controls. That does not supply commercial-provider keys or clear the hosted access gates. Statements about no execution below describe this source/access review, not that later test.

## Findings

1. **Real provider text-verification services exist.** Anthropic and OpenAI describe gated access; xAI documents an application route and a future watermark rollout. They are access candidates, not connected project capabilities.
2. **Self-operated verification is available.** SynthID Text, Meta TextSeal, KGW/Unigram and other MarkLLM algorithms, and public-key research implementations can check matching watermarks. They do not supply the production keys/configurations needed to verify arbitrary commercial-model text.
3. **No reviewed hosted service established all of: relevant production-text verification, access for this project, free pricing, unlimited automated use, and acceptable retention.** This is a bounded investigation result, not proof no such service exists.
4. A free hidden-character scanner, an open-source watermark algorithm, an application form, and a working free/unlimited provider API are **four different availability claims**.
5. None of the reviewed evidence establishes reliable coverage across the project's shortest X replies. A supported positive signal may be valuable; an absent signal does not establish human authorship.

## What was and was not verified

Read official provider pages, source READMEs/configurations, repository license/revision metadata, a provider-linked xAI application form, and third-party capability/methodology pages. A public capability `GET` was inspected; **no text was submitted for detection**, no provider account was inspected, no application was submitted, no key was obtained, no checker was installed/run, and no private material was sent.

Provider-specific quotas, authentication contracts, automation rights, or retention not established by these sources are explicitly unknown below. A normal generation API key is not evidence of permission to use its provider's text verifier.

Some direct HTML reads of Anthropic/OpenAI returned 403; their readable content was obtained through the web-fetch tool. The Google developer guide redirected through a login loop, so the open-source repository and official product/announcement pages are the primary Google evidence here. These limitations must not be presented as authenticated product testing.

## Availability matrix

| Checker | What it recognizes | Input/evidence needed | Access for this project |
| --- | --- | --- | --- |
| Anthropic provider verifier | Supported Claude text watermark, a SynthID-Text variant | Copied text containing enough surviving signal; provider performs keyed verification | **Gated** private preview. No access granted or endpoint contract verified. |
| OpenAI textGrain verifier | Supported OpenAI text watermark | Text from a supported marked output path; matching provider verifier | **Gated** approval. Public image/audio endpoint is not a text-verification endpoint. |
| Hosted Google SynthID Detector | Supported provider watermarks; older launch announcement includes text | A supported input modality and authorized verifier | **Public automated text access unconfirmed**. Current public rollout advertises image/video/audio. |
| xAI/Grok provider verifier | Supported Grok output watermark | Copied text for statistical verification; original generation header is separate evidence | **Gated** per-team application. Documented generation rollout starts **7 November 2026**, after this review. |
| Open-source SynthID Text | Its configured keyed watermark | Matching key/configuration, tokenizer, and appropriate detector parameters | **Source available**, not production Gemini/Claude verification access. |
| Meta TextSeal / TextSeal2 | Its configured watermark; includes public/private-channel research | Matching tokenizer/configuration and authorized key or public detection channel | **Source available**, including detection-only mode; no evidence that all Meta/Llama outputs use a publicly supplied production configuration. |
| KGW / Unigram / MarkLLM | Specific configured research watermarks | Matching scheme, key, tokenizer, and implementation settings | **Source available**. Default-key tests can cover those exact research configurations, not all LLM text. |
| Publicly detectable/asymmetric watermark research | A watermark embedded by the matching generator | Published detection key/parameters or trained verifier, depending on scheme | **Research available**. Cannot recover missing production signatures from ordinary text. |
| Unicode/HTML artifact scanners | Actual hidden code points or formatting artifacts | Preserved characters/markup | Often locally available, but **not provider watermark verification or authorship evidence**. |
| C2PA verification | Signed provenance assertions on supported assets | Original asset/manifest and trust/signature validation | Available tooling, but **not applicable to plain copied X text** without its signed asset/provenance. Attached-media analysis is outside current scope. |

## Provider findings

### Anthropic / Claude

Sources: [current support/coverage table](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content), [technical explanation](https://www.anthropic.com/news/claude-text-watermark).

- **Signal and coverage:** a SynthID-Text-style keyed token-choice watermark, not hidden Unicode. The support table observed in this review marks Fable 5/5.1, Mythos 5.1, Opus 4.8/5/5.5, Sonnet 5/5.5, and Haiku 5.5 as text-watermarked on first-party and listed cloud-partner surfaces. Other listed older models are not all marked. This is an observed table, not a durable promise that all Claude versions carry the signal.
- **Copied X text:** the provider says the mark travels with copy/paste and can survive some edits. It also explicitly warns about very short passages, heavy editing, translation, mixing, and sparse signal in factual/code/grammar-only output. No numeric supported minimum or short-X performance guarantee was established.
- **Access:** private preview for eligible regulators, law enforcement, media, fact-checkers, independent researchers, educational organizations, EU civil-society groups, and qualifying compliance enterprises. The support page links the **Claude Watermark Detector Access Request Form**. Project eligibility and approval are unknown.
- **Endpoint/authentication:** no usable public detection endpoint, request schema, verifier credential, or production key was established. The application route is real; an application is not access.
- **Cost/quotas/automation/retention:** verifier-specific pricing, unlimited entitlement, numeric quotas, permitted feed-scanning automation, and submitted-text retention were not established. “Watermarking does not cost more” in the generation explanation is **not** free/unlimited detection pricing.
- **Result meaning:** evidence Claude generated/processed some content, not proof of original authorship, amount of human contribution, identity, or truth.
- **Disposition:** credible provider-access candidate, currently blocked on eligibility/access and service terms. Not part of the working suite.

### OpenAI / textGrain

Sources: [5 October announcement](https://openai.com/index/eu-text-provenance/), [Content Provenance API guide](https://developers.openai.com/api/docs/guides/content-provenance), [current provenance support article](https://help.openai.com/en/articles/8912793-provenance-signals-in-openai-generated-content), [technical report](https://cdn.openai.com/pdf/e9508624-d767-41b6-a26d-e34ca798ada6/textgrain-entropy-calibrated-watermarking-for-language-model-text.pdf).

- **Signal and coverage:** textGrain statistical watermark. API generation marking is globally opt-in for selected models and off by default; eligible ChatGPT/Codex output is being rolled out in the EU. Exact model/version eligibility was not established without the supported-model account controls; do not claim universal GPT coverage. The report/announcement does not grant production detection keys.
- **Copied X text:** the signal resides in word choices rather than a file manifest, making text-only verification relevant in principle. Shortening, constraint-heavy text, editing, and translation weaken it. In vendor evaluations at 1% FPR, about 80% of 200-token versus 95% of 400-token psychology passages were detected; substituting 25% of words reduced detection in one 400-token experiment from about 92% to 17%. These are vendor results on longer passages, **not** a 200-token enforced minimum or validation on short X posts.
- **Access:** approved research/expert organizations can apply through the official announcement/API guide. A generation account, watermark opt-in, or consumer subscription does not establish detector approval.
- **Endpoint/authentication:** text endpoint, text response schema, and text-specific credential provisioning were not established. The documented `POST /v1/content_provenance_checks` accepts supported **image/audio files** and must not be relabeled as a text endpoint.
- **Cost/quotas/automation/retention:** no free/unlimited text entitlement, numeric text quota, feed-scanning permission, or text-verifier retention contract established. The public file guide explicitly describes strict rate limits and service terms; those do not specify a text quota or make text unlimited. Generic API data controls are not a verified text-preview retention agreement.
- **Result meaning:** evidence of a supported watermark, not P(all text AI-authored), and not a percentage of words.
- **Disposition:** credible access candidate, blocked on approval and a documented acceptable text-verification contract.

### Google / Gemini / SynthID

Sources: [current product page](https://deepmind.google/models/synthid/), [2025 early-access launch](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/), [October 2026 expansion, updated 29 October](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/synth-id-ai-content/), [official open-source reference](https://github.com/google-deepmind/synthid-text).

- **Signal/coverage:** Google describes SynthID Text on Gemini app/web output. Exact Gemini-version, API-output, and historical coverage is not established by those pages.
- **Public versus early access:** the May 2025 portal announcement includes text and a rollout/early-tester caveat. The current public page and October expansion describe image, video, and audio. Neither establishes a public automated pasted-text verification API. Do not resolve that mismatch by assuming text is publicly supported or by asserting the internal text verifier does not exist.
- **Access/authentication:** early access is described for journalists/media/researchers in the older announcement. No current usable text endpoint, production key, or public API credential entitlement was verified. A hosted demo using a public demonstration key is not Google's production Gemini checker.
- **Open-source option:** local verification is possible for a matching key/configuration and tokenizer. The frequentist implementation returns a p-value; the Bayesian detector needs matching training/parameters. The reference README warns it is not production software. Possession of this code does not supply production Gemini keys.
- **Limits/privacy/terms:** no hosted text minimum, free/unlimited quota, automation grant, or verifier-specific retention was established. Local source use has no provider per-call fee or remote submission requirement, but compute is finite and licenses apply. No universal short-X guarantee.
- **Disposition:** retain local configured SynthID as a research option; mark production Google text verification as unconfirmed access, not an installed capability.

### xAI / Grok

Sources: [official Output Watermarking documentation, updated 31 October 2026](https://docs.x.ai/developers/advanced-api-usage/watermarking), [application form linked from that documentation](https://docs.google.com/forms/d/e/1FAIpQLSc6zpONhSgvde0GbNmfGajT6QoyO0T-fX8UBMhmd14h-UtabQ/viewform).

- **Coverage and timing:** documentation schedules marking from **7 November 2026** for grok-4.7, 4.6, 4.5, 4.3, and the three listed 4.20 reasoning/non-reasoning/multi-agent variants. It describes Responses/Chat Completions text, structured outputs, and tool arguments, with per-team/model controls. This is future-dated relative to this review; it is not evidence that existing X posts carry the mark.
- **Copied X text:** the planned signal is statistical token-choice marking without added hidden characters. The documentation says longer text strengthens detection and mentions watermarked/not-watermarked/uncertain outcomes. No technical minimum, short-X validation, or quantitative edit robustness was established.
- **Header versus verification:** `x-watermark: true` is metadata on an original generation response. We cannot retrieve that header by examining someone else's copied post. A statistical detection request is a different operation.
- **Access:** application-based, per team. The fetched form requires an organization, role, team ID, intended use, and email associated with the team; the requester must be a team admin. No form was submitted and no team was inspected.
- **Endpoint/authentication/cost/retention:** a detection API is documented, but a callable endpoint/schema, granted detection credentials, quotas, free/unlimited terms, automation permission, and retention were not established. A generation API example is not the verifier contract.
- **Disposition:** newly identified access candidate with an explicit future rollout and approval gate. Do not omit it just because the project uses a local GPU; do not count it as live.

### Other providers

Targeted searches also considered Mistral/Le Chat, Meta/Llama, DeepSeek, and Microsoft/Copilot. This pass did not establish an authorized free/unlimited production-text verification endpoint for them. That is **not** a finding that none watermarks or that no private checker exists. Meta's source toolkit is documented below; “Mistral watermark checker” marketing pages encountered described artifact scanning, not an official production verifier. These remain unverified, not negative votes.

## Self-operated and public-detection options

No software in this table was installed or executed during this investigation. Source availability is verified separately from runtime compatibility, accuracy, and real-world adoption.

| Tool | Requirements and possible local execution | License/access and limits | Relevance |
| --- | --- | --- | --- |
| [SynthID Text](https://github.com/google-deepmind/synthid-text) | Matching key, n-gram/depth/configuration, tokenizer, masks and detector. Bayesian scoring requires trained parameters for that configuration. | Apache-2.0 software; reference implementation, not a production product. No hosted quota for local use, but no production Gemini key provided. Current reference defaults skip the first `ngram_len - 1` generated tokens. Technical ability to score is not a minimum reliable length. | Genuine conditional verification; not a universal commercial-model signature test. |
| [Meta TextSeal / TextSeal2](https://github.com/facebookresearch/textseal), [detection-only API](https://github.com/facebookresearch/textseal/blob/main/docs/README_posthoc_api.md), [public/private channels](https://github.com/facebookresearch/textseal/blob/main/docs/README_attack.md) | Matching tokenizer, method, configuration and key/channel. Detection-only mode avoids loading the LLM **unless entropy thresholds require token probabilities**. Public-channel design exposes one key, keeps another for full/tamper checking. | Apache-2.0 plus required NOTICE; model/tokenizer licenses separate. No project runtime measurements or short-X validated minimum. Local no per-call provider fee does not mean infinite throughput. | Strong candidate to evaluate **when a matching legitimately available configuration exists**. Open code is not evidence ordinary Meta AI/Llama posts use a known public key. |
| [KGW official implementation](https://github.com/jwkirchenbauer/lm-watermarking) | Correct tokenizer/vocabulary, key, gamma, PRF/context scheme, and compatible RNG. Source explicitly warns CUDA/CPU RNG types differ and detection must match the generation RNG device type. | Apache-2.0. Ignore repeated n-grams as recommended; repetitions can invalidate naive p-values. Source advises deployments not to reuse its demo key. No universal supported minimum. | Honest CPU/GPU choice must follow the implementation, not assume all watermark verification is CPU interchangeable. Demo-key support covers only that configuration. |
| [MarkLLM](https://github.com/THU-BPM/MarkLLM), including [Unigram configuration](https://github.com/THU-BPM/MarkLLM/blob/main/config/Unigram.json) and KGW/UPV/SIR/SynthID/SemStamp families | Matching algorithm-specific key/configuration, tokenizer, and sometimes trained detector/embedding weights or an LM. It is a toolkit of methods, not one detector covering all text. | Apache-2.0 toolkit; separate assets/licenses still need review. Public Unigram example key is `15485863`, gamma 0.5, z threshold 4; this is a **research configuration, not a provider secret**. No common minimum or robustness guarantee across algorithms. | Potential source of specific adapters and controlled verification fixtures. Running every algorithm with default keys does not establish broad provider coverage. |
| [Publicly-Detectable Watermarking](https://github.com/jfairoze/publicly-detectable-watermark) | Asymmetric verification takes the generator's **public detection key**, signature parameters, and matching generation settings. Research output must actually contain that encoded signature. | GPL-3.0; repository archived. Public code available, but compatibility, dependency risk, and enough surviving signature length are untested here. | Corrects any blanket assertion that every text-watermark checker needs a private provider key. Public-key verification is real, but only for outputs using its corresponding scheme/key. |
| [UPV original research](https://github.com/THU-BPM/unforgeable_watermark) | Matching trained generator/detector components and model/token vocabulary settings; public-verification research, not a general human-vs-AI classifier. | Standalone repo license not established by its GitHub license metadata in this pass. MarkLLM advertises an implementation under its toolkit license; trained assets require their own checks. Example evaluation uses 200 generated tokens, not a validated X minimum. | Conditional research candidate, not a production Claude/GPT checker. |

**Correction to earlier wording:** public/asymmetric and public-channel verification exist. A provider-private key is not a universal requirement of every possible watermark scheme. The practical blocker is the absence of the **matching authorized verification material/service for the text being checked**, not GPU availability.

## Third-party “signature checker” claims

### Clean My Copy / AI Text Watermark Scanner

[Developer documentation](https://aitextwatermark.com/developers) exposes scan/batch routes; its MIT [local scanning engine](https://github.com/GeeDotDee/ai-text-watermark-scanner) inspects literal Unicode/formatting.

The public [provider capability endpoint](https://aitextwatermark.com/api/v1/providers), actually fetched in this review, returned all three listed providers (Anthropic, Google, OpenAI) with `officialDetectorConnected: false` and `availability: unavailable`. Its metadata says updated 17 August; do not use its outdated provider summaries instead of current official pages. It is evidence about **that service's declared connections**, not proof no provider API exists.

This may be useful artifact tooling; it is not currently a connected production watermark verifier. Its developer page alone does not establish unlimited hosted use or an acceptable retention/automation agreement. Local code avoids uploading text for artifact scanning, with no authorship inference.

### Watermarkend

[Methodology](https://watermarkend.com/methodology/) describes:

- Local hidden-character analysis, not authorship proof.
- A beta **Unigram/MarkLLM default-key + OPT vocabulary** test. It does not use Claude/GPT/Gemini production keys.
- No test below **50 tokens** in that service; its watermarked evaluation examples are about 200 tokens. Vendor-reported results on 60 watermarked samples do not establish reliability on short X posts.
- Correction for the number of key-based tests (Bonferroni). A p-value is not an AI-authorship probability; the site's “verified” label must not be adopted as cryptographic certainty.

The page advertises free, no-account, browser-local use. That is not a documented unlimited automation API or a license to import its engine. A reusable endpoint, engine redistribution license, automation rights, and complete engine data-flow audit were not established; no text was submitted. The public reference Unigram implementation is a separate, license-visible local research route.

### “Claude Watermark Remover” API

The [developer landing page](https://claudewatermarkremover.dev/) advertises hidden-character scan/clean endpoints, **1,000 free requests/month**, and both keyless use and a sign-up/API-key call to action. Its “nothing stored” assertion is a marketing claim, not a verified retention contract.

Neither naming nor a Unicode scan demonstrates access to Anthropic's statistical verifier; the documented free allowance is not unlimited. No endpoint was invoked and no removal/rewrite functionality is needed for this project.

### C2PA and other signed file provenance

[C2PA Tool](https://opensource.contentauthenticity.org/docs/c2patool/) reads asset manifests; [trust lists](https://opensource.contentauthenticity.org/docs/conformance/trust-lists.md) matter in establishing signer trust. A valid signature and relevant issuer/AI-generation assertion are different checks.

A post's copied text does not carry the original image/document's signed manifest. Uploading a screenshot of text checks the screenshot's provenance, **not the authorship of the words pictured**. C2PA is therefore not a text-detector adapter for the current input contract. No attached-media expansion is authorized by this research.

## Short-X and evidence constraints

- Provider marks can indicate **generation or processing**, not necessarily a wholly AI-written post.
- Raw text may preserve token-choice signals, but excerpts remove evidence. Whether actual X extraction/reformatting preserves a particular signal has not been tested here.
- Keep original text for verification; do not blindly normalize Unicode/whitespace before every checker or combine other posts to meet a length threshold.
- More keys, algorithms, providers, or overlapping text windows mean more opportunities for false positives. Any eventual detection procedure needs a specified multiple-testing policy and validation; “take the most confident result” is not a justified combined score.
- A p-value is not `1 - P(human)`; do not show `(1 - p) × 100` as authorship confidence.
- `Unavailable`, `unsupported`, `insufficient evidence`, and `failed` are not `not detected`. Even a completed supported negative does not establish human authorship.
- Access to a free provider API would still send posts off the user's server. Verifier-specific data handling must be agreed before using it.

## Access register and unresolved facts

| Route | Evidence obtained | What still prevents counting it as usable |
| --- | --- | --- |
| Anthropic preview | Current official coverage, limitations, eligible categories, request-form route | Approval; exact text endpoint/auth/schema; pricing/quota/automation/retention; supported short input behavior |
| OpenAI text preview | Current official application gate and distinction from file API; vendor length/edit evidence | Approval; text contract/credentials; pricing/quota/automation/retention; account/model coverage and short-X behavior |
| Google hosted text | Historic early-access announcement versus current public modality scope | Current authorized automated text-access route, contract and service terms |
| xAI application | Official detection description, team-admin form requirements, scheduled model rollout | Rollout actually active; approval; text API contract and acceptable quotas/cost/retention |
| Self-operated schemes | Public source/configuration/license evidence and conditional detection APIs | A justified set of matching real-world configurations, dependency/license checks, runtime and short-text validation |
| Third-party hosted scanners | Public capability/methodology/marketing inspected | Provider verification absent/unconfirmed; free website not API entitlement; no demonstrated added authorship evidence |

**Disposition for subsequent decisions:** retain provider access as a real research/access track and local known-configuration verification as a real technical track. Do not report either as integrated, promise free/unlimited production access, or silently replace the requested signature layer with Unicode heuristics. If gated provider verification is essential, access is a product blocker to discuss—not permission to omit it.

The source/access investigation is documented; **access acquisition and live validation remain unfinished**. Applying on the user's behalf, providing organization identity, accepting terms, supplying credentials, or spending money requires a separate decision. No applications were submitted in this step.

## Source revision record

Repository metadata observed in this review; these are research references, not selected implementation pins. Provider web pages are mutable and should be rechecked before integration.

| Repository | Observed revision |
| --- | --- |
| `google-deepmind/synthid-text` | `9c055d932e042b75197e337371448a120bbc65bb` |
| `facebookresearch/textseal` | `0b76bc64013081c570b8633d3d3585e3ee9a495a` |
| `THU-BPM/MarkLLM` | `0a4fe8c642b31b8a8c4993615b1c70a0c300d918` |
| `jwkirchenbauer/lm-watermarking` | `82922516930c02f8aa322765defdb5863d07a00e` |
| `jfairoze/publicly-detectable-watermark` | `08269490aab51334afcc42235e5eee0ba6201de1` |
| `THU-BPM/unforgeable_watermark` | `1fb9526bd8d932816927cfb67e44ee20741b5d9c` |
| `GeeDotDee/ai-text-watermark-scanner` | `9faa0cdaebec8c87b9ef96f3638c71c5bb7a15b5` |
