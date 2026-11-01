# Dedicated detectors for short X posts

Research date: **1 November 2026**. Evidence comes from published documentation, model cards, code, and research. No detector was run during this investigation. Prices, endpoints, and model versions can change.

## Recommendation

**Evaluate GPTZero first for the API path and TMR int8 ONNX first for the local CPU path.** GPTZero provides an explicit AI-class probability; TMR has an available small encoder and browser-compatible model export. Neither is established as accurate on the full target length range. This is a practical shortlist, not a measured accuracy ranking.

Pangram 4 is the strongest commercial accuracy challenger found in this review, but its current public output contract does not directly provide the requested authorship probability. Retain it in the comparison rather than converting its text fractions into confidence.

For this investigation, the short-post target is **roughly 20–280 ordinary characters and 5–60 words**, including shorter replies as a separate cohort. These are evaluation buckets, not a claim that X uses ordinary character counts for its limits. Longer X posts remain in scope and must be evaluated separately.

No reviewed evidence establishes a current winner on precisely this task. The requested experience remains intact; any insufficient-evidence presentation needs a separate product decision, not a silent exclusion of short posts.

## API candidates

### GPTZero: first probability-output candidate

This is a dedicated classifier. Its current response separates `human`, `ai`, and `mixed` probabilities from confidence in the winning class. `class_probabilities.ai` can express the model's AI-class estimate. It is not a measured percentage of words written by AI. See the [API quickstart](https://docs.gptzero.me/quickstart/) and [interpretation guide](https://support.gptzero.me/articles/8947054519-how-do-i-use-and-interpret-the-results-from-your-api).

The [published benchmark](https://gptzero.me/news/gptzero-ai-detection-benchmarking-the-industry-standard-in-accuracy-transparency-and-fairness) uses a 250-character minimum, described as the dashboard minimum. **The current API's enforced lower limit was not established from its readable reference.** Neither acceptance nor reliability below that length should be assumed.

Integration uses `POST https://api.gptzero.me/v2/predict/text` and `x-api-key`. Log the returned model version during evaluation. API pricing/access must be verified in the API account; consumer subscriptions should not be assumed to include it. The [privacy policy](https://gptzero.me/privacy-policy.html) says API submissions are not stored by default or used for product improvement unless storage is opted into.

Before UI integration, define how mixed/AI-assisted writing relates to the requested number. A low probability of the pure-AI class does not imply human authorship when `mixed` is high. Do not silently discard `mixed`, sum it into `ai`, or use averaged sentence scores as a document probability.

### Pangram 4: strongest accuracy challenger, output mismatch

The vendor's [October limitations guidance](https://www.pangram.com/blog/is-pangram-accurate) scopes the product to prose of at least 50 words, mostly complete sentences. A shorter API example is not a supported-accuracy guarantee.

The [Pangram 4 technical report, Table 18](https://arxiv.org/html/2607.27183v1) includes an under-50-word group: 1,312 samples, reporting 99.70% true-positive rate at 1% false-positive rate on standard text, falling to 73.32% on humanized text. These are vendor-run results and do not establish performance on five-word replies or a held-out X corpus.

The [current API](https://docs.pangram.com/api-reference/ai-detection) uses asynchronous tasks and exposes `fraction_ai`, `fraction_ai_assisted`, and `fraction_human`. These measure classified portions of text, not P(AI authorship); window confidence is categorical. New integrations should select a model explicitly. The [legacy probability-like fields](https://docs.pangram.com/api-reference/deprecated-endpoints) belong to deprecated endpoints and are not a sound basis for a new integration.

Published [developer pricing](https://www.pangram.com/solutions/api) is $0.05 per 100 words, with a 20% bulk discount. The [bulk contract](https://docs.pangram.com/api-reference/bulk-api) rounds each Pangram 4 item to a started 100-word billing unit. Enterprise zero-retention options are advertised; do not assume default zero retention. A documented suitable probability output or an explicitly agreed change in score meaning would be needed before this becomes the header's confidence source.

### Sapling: inexpensive exploratory baseline

The dedicated endpoint returns a whole-text `score`, distinct from `ai_fraction`. It recommends at least 300 characters and marks all inputs below 500 characters as `low_confidence`. Therefore every 20–280-character target falls in its declared low-confidence range. The API accepts batches of up to 10 independently scored texts. `zero_retention: true` avoids retaining text, cache, and history, although hashes remain. [Detector documentation](https://sapling.ai/docs/api/detector/)

Published pricing starts at $0.005 per 1,000 characters. This makes it a useful cost comparison, not the accuracy winner. [API pricing](https://sapling.ai/docs/api/pricing/)

### Copyleaks and ZeroGPT

Copyleaks requires at least **255 characters** at its [REST endpoint](https://docs.copyleaks.com/reference/actions/writer-detector/check/); its [V11 evaluation](https://copyleaks.com/ai-detector/testing-methodology) used texts longer than 350 characters. Its `summary.ai` measures the share of words classified AI. These coverage and score differences make it a weaker fit here. API pricing is separately quoted.

ZeroGPT has a [Business API](https://api.zerogpt.com/docs), but this review did not establish strong current primary short-post validation. It is not GPTZero and is not shortlisted on name similarity or advertised general accuracy.

## Local CPU candidates

**Follow-up:** the [expanded open-source review](open-source-detectors.md) adds E5-small (tweet-related training and a ~39 MB third-party quantized ONNX export), Tabularis ModernBERT, and rasbt DistilBERT. Evaluate **E5 alongside TMR** for browser CPU; add **Tabularis** for a local-service comparison. This expands the deployment shortlist without establishing an accuracy winner.

| Candidate | Available artifact and licensing | Suitability |
| --- | --- | --- |
| **TMR RoBERTa-base** | 125M parameters; MIT; [model card](https://huggingface.co/Oxidane/tmr-ai-text-detector). Existing [ONNX export](https://huggingface.co/onnx-community/tmr-ai-text-detector-ONNX/tree/main/onnx), about 126 MB int8 versus 499 MB FP32. | First deployment candidate. Dedicated binary classifier trained on RAID. The card explicitly warns of false positives on short/casual text. Verify export parity and actual CPU latency/RAM before integration. |
| **Fakespot RoBERTa-base** | About 125M parameters; Apache-2.0; [weights and card](https://huggingface.co/fakespot-ai/roberta-base-ai-text-detection-v1). | Useful second small-encoder candidate. Longer text is preferred. Do not attribute the [full APOLLO system's results](https://github.com/fakespot-ai/apollodft/blob/main/apollo-text.md) to this one model. |
| **Desklib v1.01** | MIT; DeBERTa-v3-large, roughly 435M parameters and 1.74 GB weights; [model](https://huggingface.co/desklib/ai-text-detector-v1.01). | Larger local-process challenger. Custom pooling/classification code; no verified short-X evaluation or ready browser path in this review. |
| **tropa-mini** | Apache-2.0; large DeBERTa derivative; [model](https://huggingface.co/wasitaigeneratedcom/ai-text-detector-small). | Four classes including edited/humanized text; explicitly aimed at English prose of 50+ words. Its non-human score has different semantics from a pure AI-written class. |
| **Open Pangram / EditLens** | [Open research release](https://www.pangram.com/blog/introducing-open-pangram), CC BY-NC-SA 4.0; gated weights. | Estimates extent of AI intervention rather than the desired binary authorship probability. Noncommercial licensing and larger models make this a research comparator, not the default. |

[Transformers.js](https://huggingface.co/docs/transformers.js/en/index) supports ONNX inference using CPU/WASM. This establishes a feasible execution path, not a performance measurement. Model download size is not peak runtime memory. None of these models was downloaded or timed here.

[Binoculars](https://github.com/ahans30/Binoculars) and [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) are legitimate statistical detectors using model logits, not general LLM judgment prompts. Their multi-billion-parameter reference models make them poor first choices for a lightweight local CPU extension. Their raw statistical scores also need interpretation rather than a percent sign.

## What independent evidence establishes

The [Jabarian–Imas study, section 4.1](https://bfi.uchicago.edu/wp-content/uploads/2025/09/BFI_WP_2025-116.pdf) compared older commercial detectors on under-50-word stubs and supports investigating Pangram. Those stubs came from reviews, blogs, and news, not a current X-post corpus. It used only 160 human stubs and selected thresholds on the evaluation data. GPTZero also [disputes the score field used](https://gptzero.me/news/chicago-booth-2026). The results cannot establish a current API ranking for this project.

[MultiSocial](https://arxiv.org/html/2406.12549v2) is more domain-relevant: its Twitter texts have a median of 18 words. However, its cap is 200 words, not 280 characters, and generated lengths differ. Its aggregate results cannot be substituted for a short-post result. The [official repository](https://github.com/kinit-sk/multisocial) provides experiments and training instructions; a ready-to-use fine-tuned checkpoint was not verified in this review. Treat it as research guidance, not an available extension model.

## Existing extension worth inspecting

[rbilgil/slop-detector](https://github.com/rbilgil/slop-detector) is MIT-licensed and has a [direct GPTZero integration](https://github.com/rbilgil/slop-detector/blob/main/src/gptzero-direct.ts). It automatically scans visible X posts but uses stamp/fade/hide presentation. Its optional Jev path is excluded from this project's design. It may supply useful implementation references; no code has been imported, and its existence does not validate detector accuracy.

## Decision boundary

The next useful evidence is a direct comparison on the same labeled short posts, measuring false positives, recall, coverage, calibration, and cost. See [the evaluation plan](evaluation.md). Do not add a generic judge, pad inputs with other posts, reinterpret text fractions as probabilities, or replace missing results with 0% merely to produce a number everywhere.
