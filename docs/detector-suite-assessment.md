# Detector candidates assessed as a suite

Source review: **1 November 2026 (UTC)**. Scope: prerequisite candidate comparison and inclusion/exclusion recommendation, **not implementation, a measured ensemble benchmark, or approval of a final suite**.

**Subsequent evidence:** [bounded feasibility checks](feasibility-checks.md) now demonstrate execution/co-residency for the proposed candidates on the 3060 and CPU, plus one known-key CPU watermark configuration. “Not measured” below describes this source-review stage; use the follow-up for operational measurements. Accuracy, complementary errors, provider access, and final membership remain unresolved.

The [consolidated requirements](requirements-and-state.md) govern this assessment: thin Chrome client; server analysis on the passive 12 GiB RTX 3060, CPU, and appropriate hosted services; multiple evidence sources including applicable watermark verification. Small browser downloads are no longer the main selection criterion.

## Recommendation for discussion

**Preferred suite to validate: Tabularis ModernBERT + E5-small + Fakespot RoBERTa + Fast-DetectGPT with one GPT-Neo-2.7B model.** Retain **TMR as a controlled challenger to Fakespot**, not an automatic fifth always-on vote.

This recommendation defines what is worth comparing, not what is proven to improve detection:

| Candidate | Recommendation | Why |
| --- | --- | --- |
| **Tabularis ModernBERT** | Include as the existing classifier baseline | Broad documented training and useful RAID evidence; the exact checkpoint already runs here. Existing integration saves comparison effort but is not evidence of superior accuracy. |
| **E5-small** | Include as the compact, tweet-related classifier | Documented tweet/GPT-4o-mini rewrite training and a small standard encoder. Directly relevant training description, though not held-out short-X validation. |
| **Fakespot RoBERTa** | Include as the preferred additional classifier candidate | Its documented data pool includes TweepFake and multiple additional generators/datasets, rather than RAID alone. Evaluate whether that adds useful coverage; do not assume independence or inherit the full APOLLO ensemble's results. |
| **Fast-DetectGPT / GPT-Neo-2.7B in both roles** | Include as a **conditional statistical-method candidate** | Adds token-probability discrepancy evidence without a RAID-trained classification head. One explicitly selected 2.7B model is more plausible on the 3060 than the current default two-model configuration. Modern-generator/short-text usefulness and operational fit remain open. |
| **TMR RoBERTa** | Include in the comparison as Fakespot's challenger; do not automatically retain both | Hard-negative mining may improve false positives, but its entire declared fine-tuning set is RAID and its card warns about short/casual text. It must demonstrate incremental value, not just add another agreeing number. |

**What changes from earlier suggestions:** the previous proposed Tabularis + TMR + E5 + Fast-DetectGPT list had not compared Fakespot's documented training coverage or inspected the current statistical demo defaults. This pass prefers Fakespot for that RoBERTa slot on source-level coverage grounds, while keeping TMR in the same comparison so the choice can be overturned by measured errors. It is **not** a finding that Fakespot is more accurate.

The statistical slot is genuinely unresolved until feasibility and quality checks pass. If the smaller Fast-DetectGPT configuration fails, do not silently replace statistical evidence with another classifier or move the workload to the active 3090. Bring that gap back for a decision.

Provider/local watermark verification remains a **separate required evidence track**, subject to the [signature-checker access findings](signature-checkers.md). None of these classifiers or Fast-DetectGPT verifies a provider watermark. A missing signature integration does not become solved by selecting four text detectors.

## Evidence boundary

- Only **Tabularis** has been inference/lifecycle-tested by this project. Its previous 3060 measurements are not suite measurements.
- This step inspected cards, source code, configs, file sizes, parameter counts, licenses, and published research. It downloaded no detector weights, ran no new inference, made no paid/hosted detection calls, and changed no runtime code or remote services.
- Model-card metrics are identified as publisher-reported, not reproduced results. No empirical error correlation, record-level training overlap, or incremental accuracy gain has been measured.
- “Include” means include in the proposed validation roster. It does not authorize integration, establish calibration, or select a production default.

## Classifier comparison

Weight sizes are observed decimal file sizes for one representation, not RAM/VRAM requirements. Base architecture capacities, inference examples, and validated input ranges are different facts.

| Model and primary source | Availability/license | Training, overlap and short-text evidence | Output/language/input contract |
| --- | --- | --- | --- |
| [Tabularis](https://huggingface.co/tabularisai/ai-text-detection) | MIT; standard Transformers ModernBERT; 149.6M parameters; **598 MB** safetensors. | ~10.93M rows, including 7.65M RAID train/extra and six other sources. Card reports RAID AUROC 0.9904 / recall 0.9306 at 1% FPR. No short-X or current-generator validation established. | English-declared binary classifier; card maps index **1 to AI**, though config does not supply descriptive labels. Card's training/inference length is **512 tokens** despite backbone capacity 8,192. Current server uses raw text/FP32; publisher example normalizes text and uses BF16. |
| [E5-small](https://huggingface.co/MayZhou/e5-small-lora-ai-generated-detector) | MIT; standard BERT/E5-derived sequence classifier; 33.36M parameters; **133 MB** safetensors. Full merged weights are published despite “LoRA” in the name. | 80k human + 128k AI RAID examples, plus 10k tweets + 10k GPT-4o-mini rewrites. Card reports 89% accuracy / 0.976 AUC without enough split detail to establish X generalization; separate metadata reports 0.939 under an accuracy field. Do not merge these figures. | Card maps **0 human / 1 AI**; config has generic labels. **512 positional capacity**. No published reliable short-text minimum established. English-oriented training description; do not infer multilingual detection from an embedding-model family name. |
| [Fakespot RoBERTa](https://huggingface.co/fakespot-ai/roberta-base-ai-text-detection-v1) | Apache-2.0 weights; standard RoBERTa-base, 124.65M parameters; **499 MB** safetensors. [Project/source report](https://github.com/FakespotAILabs/ApolloDFT). | [Training-pool documentation](https://github.com/FakespotAILabs/ApolloDFT/blob/main/data/README.md) includes RAID, HC3, TweepFake, TuringBench, Ghostbuster data, reviews, and supplemental GPT-4o/mini, Llama 3.x, Qwen 2.5, Gemma 2 and other generations. Exact checkpoint sampling/proportions are not released there. Card explicitly says longer text improves performance; no short-X holdout demonstrated. | English; **0 Human / 1 AI**. A pipeline returns the **winning label's** score, not always AI probability. RoBERTa config has 514 positions (normally a 512-token practical input). Verify tokenizer/call limit; do not silently truncate. Published preprocessing can remove content—see below. |
| [TMR](https://huggingface.co/Oxidane/tmr-ai-text-detector) | MIT; standard RoBERTa-base; 124.65M parameters; **499 MB** safetensors. | 50k stratified RAID samples, 45% human / 55% AI; focal loss and iterative self-hard-negative mining. Card reports RAID recall 0.9017 at 1% FPR; its separate 100k holdout is from the RAID **train** partition, not our target distribution. Explicit short/casual/OOD false-positive warning. | Primarily English; **0 human / 1 ai**. Example uses **512 tokens**. Its 0.5 decision threshold and softmax are not validated X operating thresholds/probabilities. |
| [rasbt DistilBERT](https://huggingface.co/rasbt/ai-text-detector-distilbert) | Apache-2.0 model; standard DistilBERT, 66.96M parameters; **268 MB** weights. | `rasbt/human-vs-ai-50k`; card reports 99.74% best validation accuracy. [Dataset card](https://huggingface.co/datasets/rasbt/human-vs-ai-50k) exposes provenance fields but says “More details coming soon” and `license: other`; generator/domain/record overlap is not established by that card. Model's linked GitHub inference repo could not be verified publicly via the GitHub API (404 in this review). | English; **0 HUMAN / 1 AI**, **512 tokens**. [Metadata](https://huggingface.co/rasbt/ai-text-detector-distilbert/blob/main/detector-config.json) requires temperature scaling, T≈1.2900. Calibration on its own distribution is not calibration on X. Defer rather than treating a high validation headline as a winner. |

### Shared training is a suite-level risk

| Relationship | Evidence | Consequence |
| --- | --- | --- |
| Tabularis ↔ TMR | Tabularis declares ~70% RAID rows; TMR declares all its fine-tuning data from RAID. Different selection/loss/architecture does not eliminate shared-domain bias. | TMR is a meaningful hard-negative challenger, not an independent provenance check. |
| Tabularis ↔ E5 | E5 declares 208k RAID rows of ~228k total (~91%), alongside the tweet-related examples. | Small size and tweets justify testing E5; they do not make it an independent vote. |
| TMR ↔ Fakespot | Same RoBERTa-base family, both use RAID; Fakespot has a broader documented pool. | Prefer comparing them for one slot. Keep both only if observed complementary errors justify extra inference. |
| Tabularis/E5/TMR ↔ Fakespot | All use RAID; extra datasets can contain duplicates or shared underlying sources. | Exact record overlap is **unknown**, not zero. Dataset names or differing authors do not establish independence. |
| Supervised encoders ↔ Fast-DetectGPT | Fast-DetectGPT does not train a human-vs-AI head on RAID; its reference LM has its own pretraining data and shared linguistic regularities. | Different method gives a reason to test complementarity, not a guarantee of uncorrelated mistakes. |
| rasbt DistilBERT ↔ rasbt ModernBERT | Same declared fine-tuning dataset. | Adding both is not adding two independent training distributions. |

Most of these models were evaluated against older generator families. A release date in 2026 or an architecture name does not establish detection against current GPT/Claude/Gemini/Grok outputs. Training/evaluation provenance and near-duplicate checks are needed to make that claim.

### Preprocessing must not silently change the evidence

- Tabularis's sample combines NFKC with **separate** zero-width removal and whitespace collapsing. Its projected gains from normalization are not measured project results. Our raw-text FP32 baseline is a distinct configuration.
- Fakespot's [recommended `clean_text`](https://huggingface.co/fakespot-ai/roberta-base-ai-text-detection-v1/blob/main/utils.py) removes Markdown code/inline code, images, some blockquotes/tables/HTML, and formatting. On a short technical post that can remove most of the author's content. Compare preserved-text versus supported cleaning explicitly; empty/insufficient cleaned text cannot become a human score.
- E5/TMR/other examples using truncation do not authorize silently discarding part of a long X post.
- Do not apply classifier cleaning to watermark verification. That layer needs the relevant original text and matching tokenization.

## Statistical detectors

### Fast-DetectGPT: include a specific small configuration, not the name alone

Primary sources: [current local demo](https://github.com/baoguangsheng/fast-detect-gpt/blob/main/scripts/local_infer.py), [model loader](https://github.com/baoguangsheng/fast-detect-gpt/blob/main/scripts/model.py), [analytic discrepancy](https://github.com/baoguangsheng/fast-detect-gpt/blob/main/scripts/fast_detect_gpt.py), [GPT-Neo-2.7B](https://huggingface.co/EleutherAI/gpt-neo-2.7B).

- **License:** MIT method code and MIT GPT-Neo model. Dependency/license and execution compatibility still need checking before integration.
- **Proposed configuration:** explicitly choose **`gpt-neo-2.7B` for both sampling and scoring**. Source confirms it loads only one model when the names are equal and reuses its logits. Loader selects FP16 for this alias. This is a deliberate candidate configuration, not the current CLI default.
- **Correction:** `scripts/local_infer.py` currently defaults to **Falcon-7B + Falcon-7B-Instruct**; a README passage still calls GPT-Neo the local default. Trust the inspected executable source for resource selection and pin it. The heavier configuration's published performance cannot be assigned to the smaller one.
- **Output:** raw standardized token-probability discrepancy, not watermark evidence. The demo's probability is a separate fitted normal-density mapping with **equal class priors**, preset means/deviations, and an intentionally widened AI distribution. Its own comments warn either tail can get high AI probability. Do not import that display percentage as calibrated P(AI on X).
- **Limits/language:** GPT-Neo's context capacity is **2,048 tokens**, not a short-text accuracy guarantee. Predominantly English-oriented model/evidence; no multilingual validation established. Fewer than two tokens provides no next-token observations; near-zero variance/non-finite criteria need explicit handling. There is no supported “five-word reliable” claim.
- **Batching:** the reference analytic function asserts **batch size 1**. A 16-post classifier batch cannot be sent into that function unchanged. Tokenizer mismatch checks apply if sampling/scoring models differ.
- **Resource estimate:** 2.718B parameters × 2 bytes ≈ **5.44 GB / 5.06 GiB of raw FP16 parameters**, before context, logits, activations, allocator, and framework overhead. Published safetensors are about **10.67 GB** on disk; FP16 loading does not halve the initial download. CPU execution is conceivable but FP16 support/latency is not established; do not promise a fast CPU fallback.
- **Disposition:** source-supported candidate for the statistical slot; actual 3060 coexistence, safe maximum length, latency, numerical behavior, and modern short-text contribution are not measured.

### Binoculars: defer the stock configuration

[Source](https://github.com/ahans30/Binoculars/blob/main/binoculars/detector.py) defaults to two Falcon-7B models at BF16, an observer/performer pair, and a 512-token observed cap. Code is BSD-3-Clause; model licenses must also be checked for the selected artifacts.

Approximately 14B parameters × 2 bytes is **28 GB / 26.1 GiB of raw weights**, before overhead. The stock pair cannot reside on the 12 GiB 3060. The code can automatically spread models over two visible GPUs, which could consume the active 3090 contrary to the preferred deployment boundary. CPU offload, sequential loading, or quantization would be new configurations requiring measurement and threshold validation—not evidence that stock Binoculars fits.

It returns a perplexity/cross-entropy ratio, with **lower scores meaning more AI-like**. Its fixed thresholds were selected for its exact Falcon pair/precision, not X or arbitrary substitute models. Do not invert the ratio into a probability or reuse the threshold after changing the models. Defer as a heavier challenger, not a first-suitability rejection of the method itself.

## What social-text and ensemble research actually supports

- [MultiSocial](https://arxiv.org/html/2406.12549v2) studies five platforms and 22 languages, with Twitter median length **18 words**. It finds social-domain/platform training matters. Its compared pretrained detectors and statistical methods are not these exact proposed checkpoints; Fast-DetectGPT there uses GPT-J-6B, not our proposed Neo configuration. Data processing drops samples below three words and caps at 200 words. Its findings motivate our domain evaluation; they do not validate five-word replies or give our suite an accuracy score.
- [Fakespot's APOLLO technical report](https://github.com/FakespotAILabs/ApolloDFT/blob/main/apollo-text.md) explicitly evaluates combinations of supervised and zero-shot/perplexity evidence. It reports ensemble gains on some OOD/attack settings, but not universal improvement: its non-RAID table has individual methods winning some sources. The full APOLLO service/combination is not simply the downloadable RoBERTa weights.
- That report provides evidence that **multi-method combination is worth investigating**, not that our proposed classifier set + Fast-DetectGPT inherits its results. The final blend, calibration data, and operating point are still separate unanswered questions.
- Card headline accuracy, aggregate AUROC, recall at a specified FPR, and per-class human accuracy are different measurements. No leaderboard here is a current short-X suite comparison.

## Other candidates: exclude or defer, with reasons

“Exclude” below means do not include in the proposed first suite, not that the model can never be useful. Licensing observations are not legal advice.

| Candidate | Availability and semantics | Recommendation and reason |
| --- | --- | --- |
| [rasbt ModernBERT](https://huggingface.co/rasbt/ai-text-detector-modernbert) | Apache-2.0, 149.6M parameters, ~299 MB BF16 artifact; same human-vs-ai-50k dataset as its DistilBERT sibling; up to 8,192 tokens with temperature scaling. | **Defer.** Long context is not an ordinary-post advantage; dataset coverage/overlap needs documentation. Not evidence of a current-X win over Tabularis. |
| [Desklib v1.01](https://huggingface.co/desklib/ai-text-detector-v1.01) | MIT; ~434M parameters, **1.736 GB** weights; DeBERTa-v3-large with custom mean pooling and one sigmoid logit. Declares RAID training. English. Example length 768; config has 512 positional setting, so supported execution/input contract needs verification rather than inference from either number alone. | **Defer as a larger encoder challenger.** Architecture diversity is real, but RAID overlap remains; no short-X incremental benefit shown to justify another model yet. It is not excluded merely because it is larger than browser models. |
| [tropa-mini](https://huggingface.co/wasitaigeneratedcom/ai-text-detector-small) | Apache-2.0 derivative of Desklib; ~434M parameters / **1.736 GB**. Four classes: human, ai, ai_edited, humanized. Headline score is **1−P(human)**, not pure-AI probability. English prose **50+ words**; example uses 768 tokens. | **Exclude from the general short-post first suite; retain as a mixed/longer-text challenger.** Publisher reports 15.6% FPR on non-native TOEFL examples despite 0.5% matched overall human-pool FPR, and only 33.6% frontier-set recall. These are vendor figures, but directly caution against copying its headline threshold into X. Its exact fine-tuning data provenance is less complete than the evaluation description. |
| [GigaCheck classifier](https://huggingface.co/iitolstykh/GigaCheck-Classifier-Multi) | Apache-2.0; ~7.13B parameters / **14.26 GB** weights, Mistral-based custom integration. English/Russian LLMTrace training; reported 97.93% recall at 1% FPR on that holdout. Labels are **0 AI / 1 human**, reversed from several encoders here. | **Defer.** Raw 16-bit weights alone exceed 12 GiB. Quantization/offload would need testing; no 3090 allocation is implied. Potentially useful for English/Russian/mixed-domain research, but no established short-X advantage. |
| [GigaCheck span detector](https://huggingface.co/iitolstykh/GigaCheck-Detector-Multi) | Localizes generated spans; returns intervals/confidence and span-overlap metrics. | **Exclude from the initial whole-post probability slot.** Different task/output, plus heavy runtime. Not a substitute for deciding the meaning of mixed authorship. |
| [RADAR Vicuna checkpoint](https://huggingface.co/TrustSafeAI/RADAR-Vicuna-7B) | RoBERTa-large detector trained with Vicuna/OpenWebText and adversarial paraphrasing, not a 7B inference detector. Code Apache-2.0; model card explicitly **noncommercial**. | **Exclude from a permissively deployable default.** Could be a separately approved research comparison; cannot silently apply the code license to its weights. |
| [SuperAnnotate](https://huggingface.co/SuperAnnotate/ai-detector) | Custom RoBERTa-large sigmoid model; 44k declared text-label pairs split between custom Wikipedia/ELI5/scientific generations and RAID. [SAIPL](https://huggingface.co/SuperAnnotate/ai-detector/blob/main/LICENSE) **permits commercial use**, but requires source availability/network-use sharing and attribution; service code Apache does not override it. | **Defer pending an explicit licensing decision and comparative value.** Not “commercially prohibited.” Card's human-class accuracy 0.731 on its reported evaluation highlights a threshold/false-positive question; it is not our X FPR. Larger/custom loading and no short-X evidence add cost. |
| Open Pangram / EditLens | Earlier review found gated CC BY-NC-SA weights and an AI-intervention task rather than the agreed final authorship target. | **Defer.** Noncommercial/share-alike scope and score mismatch require a separate decision. Earlier source evidence not revalidated as an available artifact in this pass. |
| MultiSocial / DetectRL / RAID | Datasets/evaluation frameworks, not a single shippable trained detector. | **Use as research/evaluation references, not extra score producers.** Dataset access, source licensing, and domain relevance remain separate. |
| GPTZero, Pangram, Sapling and other hosted classifiers | Dedicated detection services, not watermark verification. Previously researched API paths have pricing, minimum-length, or score-semantic constraints; no unlimited free entitlement established here. | **Do not add calls without verified acceptable access/usage terms.** CPU/GPU independence does not make a paid or capped API free/unlimited. Their earlier API rankings are not approvals for this suite. |

## Resource comparison for the 3060 and CPU

| Proposed component | Known or estimated cost | Evidence status |
| --- | --- | --- |
| Tabularis | Previously measured **748 MiB process VRAM after inference**, 132 MiB after unload, ~18–22 ms median for the particular short batches tested on the 3060. | **Measured for this one adapter only.** Not a worst case, full-length test, or suite budget. |
| E5 + Fakespot (FP32 artifacts) | ~133 + 499 MB of stored weights. Standard encoder CPU paths are plausible; actual CPU throughput and GPU overhead unknown. | File metadata, **not runtime measurements**. |
| Tabularis + E5 + Fakespot | ~**1.23 GB / 1.15 GiB raw FP32 parameters** using observed parameter counts, before runtime overhead. TMR adds ~0.50 GB / 0.46 GiB if kept resident. | Arithmetic estimate, not peak VRAM or confirmed coexistence. |
| Neo-2.7B statistical slot | ~**5.44 GB / 5.06 GiB raw FP16 parameters**, plus potentially substantial full-vocabulary logits/intermediates. Reference function handles one post per call. | Source/parameter estimate. **No project inference, load time, or memory measurement.** |
| Whole proposed suite | Small encoders plus Neo look plausible within 12 GiB at bounded lengths, but logits, allocator/context, precision and concurrency can dominate. CPU placement or staged residency may help. | **Feasibility not established.** No claim that simply summing model files proves it fits. |

No chosen configuration may silently use both visible GPUs, change scoring precision/quantization without recording it, or interpret missing capacity as a human result. These are suitability constraints, not an implementation schedule.

## How to decide which members earn a place

The source review can nominate candidates; only same-input evidence can establish the final useful suite. Required comparison questions, not implementation tasks:

1. Does each added member improve AI recall **at the same held-out human false-positive target**, by character/word bucket, language, generator and editing category?
2. Does improvement survive controls for shared authors, prompts, source documents and near duplicates?
3. Which examples are uniquely corrected or newly broken by each member? Report joint human false positives, residual/error correlation and disagreement—not just score correlation.
4. Does the improvement remain after calibration on a separate split and evaluation of the frozen combination on holdout? Do not average softmaxes, demo probabilities, ratios and watermark p-values.
5. Are missing/short/invalid results counted in coverage, rather than dropping difficult examples until metrics improve?
6. Does a member's incremental gain justify cold-load time, per-post latency, memory and operational/license complexity?

In particular compare Tabularis alone, the proposed classifier combination, replacing Fakespot with TMR, and adding/removing the statistical method on the same examples. Classifier votes are not calibrated independent likelihoods. No fusion formula or production score is chosen by this document; [score definition and evaluation](evaluation.md) remain separate prerequisites.

## Source revisions observed

These identify the source/artifact evidence reviewed, not approved implementation pins. Sources are linked in the sections above.

| Model/repository | Observed revision |
| --- | --- |
| Tabularis | `4bf4a146a66df346e5b54e4b5ebda3fee1a19a86` |
| E5-small | `483fc4969592dc20e00e5130e7187b5dd25dbcc7` |
| Fakespot RoBERTa | `f9cdb14d1f8b105f597d80fa7b56f20c6ea0e9db` |
| TMR | `0ceddea903015ef99cbaa040a4d8a216aed9c683` |
| rasbt DistilBERT | `66e301801e7057ec118553b8c7ba1b6abd7d2e6b` |
| rasbt ModernBERT | `a6efd4bf6ecd852f332b2569ae0f98cae13b7985` |
| GPT-Neo-2.7B | `e24fa291132763e59f4a5422741b424fb5d59056` |
| Desklib | `5fdea974cd4287c61674951ec78803aa274e2fb7` |
| tropa-mini | `f1795c86806e6838d4afa33d0b1427f8430c9615` |
| GigaCheck classifier | `1b885318d0317a7c7138a52b3b53e0c747604da4` |
| Fast-DetectGPT code | `971b05202bac2bb504d60c0ac0812fea7a8f7c82` |
| Binoculars code | `c8ae2f90d50ee696418bc71d8d9e5020e5f9d7b8` |
| Fakespot APOLLO report/code | `2a752b9cf569c9da68c3ef397e8d4735485a1726` |

**Status:** candidate source comparison and recommendation recorded. Final membership, whole-suite feasibility, score definition/calibration, signature access, and implementation planning remain open.
