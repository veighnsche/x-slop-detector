# Open-source detector shortlist

Follow-up to the [initial detector research](detector-research.md). Sources reviewed on **1 November 2026**. This is a deployment/evidence assessment, not a benchmark: no weights were downloaded, no inference was run, and no browser compatibility or accuracy was measured.

**Historical browser-oriented shortlist:** the current architecture is server-first. The [suite assessment](detector-suite-assessment.md) supersedes the deployment priorities below for current discussion and compares overlap and candidate roles. Subsequent [bounded feasibility probes](feasibility-checks.md) ran the shortlisted encoders and the smaller Fast-DetectGPT configuration; browser inference and accuracy remain untested.

## Recommendation

**Add E5-small to the first local comparison with TMR.** E5-small is the most compelling new browser candidate because it combines small weights, tweet-related training, permissive licensing, and an existing third-party quantized ONNX export. TMR remains the existing ready-export baseline, not an accuracy champion.

**Add Tabularis ModernBERT R1 if a local Python service is acceptable.** It has broader training and useful RAID evidence, but a verified browser export and short-X validation are missing. Use rasbt's DistilBERT as a smaller, well-documented alternative if E5/TMR disappoint.

“Most viable” here means practical to evaluate and potentially ship under this project's CPU, privacy, and short-post constraints. It does not mean “most accurate.” None of the reviewed releases establishes calibrated authorship probabilities across 20–280-character X posts.

## Ranked practical shortlist

Sizes below are decimal artifact sizes, not peak RAM. License entries describe the published model declarations; inspect the exact pinned release and required notices before redistribution. Open weights, open inference code, and fully reproducible training are separate properties.

| Priority | Detector | Availability and license | Why consider it | Main unresolved issue |
| --- | --- | --- | --- | --- |
| **1 — new browser challenger** | [MayZhou/e5-small-lora-ai-generated-detector](https://huggingface.co/MayZhou/e5-small-lora-ai-generated-detector) | About 33M parameters; MIT; full `model.safetensors` about 133 MB. Third-party [limanup/e5-small ONNX](https://huggingface.co/limanup/e5-small/tree/main/onnx) includes a **39 MB quantized** artifact. | Training explicitly includes 10,000 tweets and 10,000 GPT-4o-mini rewrites, plus RAID examples. Smaller than TMR; most directly relevant new training description found. | Tweet training is not held-out tweet validation. Card reports 89.0% accuracy / 0.976 AUC without enough split detail to establish X generalization; its separate RAID metadata reports 0.939 under an `accuracy` field. Do not combine those metrics. Third-party export needs provenance, tokenizer, output-label, quantization-parity, and WASM checks. |
| **2 — existing browser baseline** | [Oxidane/TMR](https://huggingface.co/Oxidane/tmr-ai-text-detector) | 125M-parameter RoBERTa-base; MIT; existing [community int8 ONNX export](https://huggingface.co/onnx-community/tmr-ai-text-detector-ONNX/tree/main/onnx), about 126 MB. | Already the project's practical first export; standard small encoder trained on RAID. | Explicit short/casual-text warnings. No demonstrated superiority over E5 on X, or measured browser latency/memory. |
| **3 — local-service challenger** | [tabularisai/ai-text-detection](https://huggingface.co/tabularisai/ai-text-detection) | MIT; ModernBERT-base, about 149.6M parameters / 600 MB weights; 512-token training length. Standard Transformers inference. | Card describes ~10.93M training rows from RAID and six other datasets. Reports RAID AUROC 0.9904 and TPR 0.9306 at 1% FPR; linked [RAID submission PR #137](https://github.com/liamdugan/raid/pull/137) is merged and contains results. Strong reason to include in evaluation. | Those are card-reported benchmark aggregates, not a current-generator or short-X result. No ready browser export verified here. The sample uses CUDA; CPU feasibility still needs measurement. |
| **4 — compact alternative** | [rasbt/ai-text-detector-distilbert](https://huggingface.co/rasbt/ai-text-detector-distilbert) | Apache-2.0; about 67M parameters / 268 MB FP32 weights; 512-token context; [inference/source repository](https://github.com/rasbt/ai-detector). | Standard encoder with documented temperature scaling and label mapping. Smaller than RoBERTa-base and straightforward to try in Python. | The reported 99.74% best validation accuracy is on its own training distribution, not X. [Dataset card](https://huggingface.co/datasets/rasbt/human-vs-ai-50k) has provenance fields but says “More details coming soon” and declares `license: other`. Do not assume the dataset is Apache-licensed because the model is. Browser export not verified. |
| **5 — second encoder family** | [fakespot-ai/roberta-base-ai-text-detection-v1](https://huggingface.co/fakespot-ai/roberta-base-ai-text-detection-v1) | Apache-2.0; approximately 125M parameters. | Established dedicated small-encoder comparator from the original shortlist. | No new short-X evidence found in this pass. Full APOLLO-system results are not this checkpoint's results. Retain as a backup rather than adding every similar encoder to the first run. |

The E5 weight size was checked in the Hugging Face file metadata at revision `483fc4969592dc20e00e5130e7187b5dd25dbcc7`; the DistilBERT size at `66e301801e7057ec118553b8c7ba1b6abd7d2e6b`. The third-party E5 export is a separate artifact, not an author-endorsed conversion.

## Other newly reviewed options

### rasbt ModernBERT: usable, but not ahead of the compact alternatives

[rasbt/ai-text-detector-modernbert](https://huggingface.co/rasbt/ai-text-detector-modernbert) is Apache-2.0, supports up to 8,192 tokens, and provides temperature-scaled inference. It reports 99.71% best validation accuracy on the same `human-vs-ai-50k` dataset used by the DistilBERT release. Long context is not an advantage for ordinary X posts. Try it if the shared inference tooling is useful; do not treat the validation score as evidence that it beats TMR, E5, or Tabularis on our task.

Temperature scaling fitted elsewhere does not establish calibration on X. Preserve the release's temperature and label metadata, then measure deployment-domain calibration separately.

### GigaCheck / LLMTrace: viable self-hosted GPU research, poor browser fit

[GigaCheck-Classifier-Multi](https://huggingface.co/iitolstykh/GigaCheck-Classifier-Multi) declares Apache-2.0 and uses Mistral-7B-v0.3 with English/Russian training. Its card reports 97.93% TPR at 1% FPR on the LLMTrace classification holdout. This is a dedicated detector, not a prompted general-purpose judge.

Its 7B backbone and custom `gigacheck` integration make it a much heavier deployment than a small encoder. The example uses `trust_remote_code=True`; review and pin the custom code before running it. CPU fallback in an example is not evidence of acceptable feed-scanning latency.

The separate [GigaCheck-Detector-Multi](https://huggingface.co/iitolstykh/GigaCheck-Detector-Multi) localizes AI spans. Its span scores and overlap metrics must not be substituted for whole-post authorship probabilities. Consider the classifier only if a self-hosted GPU backend and English/Russian evaluation become priorities.

### RADAR: open code does not mean permissive detector weights

[IBM/RADAR](https://github.com/IBM/RADAR) has Apache-2.0 code and adversarial/paraphrase training. However, the published [TrustSafeAI/RADAR-Vicuna-7B model card](https://huggingface.co/TrustSafeAI/RADAR-Vicuna-7B) explicitly restricts the weights to noncommercial use.

Despite the checkpoint name, the detector is **RoBERTa-large**, not a 7B inference model; Vicuna supplied training generations. That makes it smaller than GigaCheck but still not the preferred browser baseline. Keep as a research comparator, not a permissively redistributable default.

### SuperAnnotate: custom model license requires review

[SuperAnnotate/ai-detector](https://huggingface.co/SuperAnnotate/ai-detector) is an English RoBERTa-large-based custom classifier, trained on 44k balanced text-label samples spanning custom generations and RAID. The [service code](https://github.com/superannotateai/generated_text_detector) has an Apache-2.0 license, while the **model card declares SAIPL**. Do not apply the code's license to the weights or call the model permissively open source without reviewing SAIPL. Larger/custom architecture and no verified short-X result reduce its priority.

## Research methods and datasets, not first-choice extension models

| Project | What is available | Verdict for this project |
| --- | --- | --- |
| [Binoculars](https://github.com/ahans30/Binoculars) | BSD-3-Clause code; default Falcon-7B / Falcon-7B-Instruct scoring pair. Computes a statistical score with a model-specific threshold. | Legitimate detector, but large-model cost and non-probability output make it a GPU/backend comparator, not a lightweight CPU default. Repository cautions that it is academic software, not a consumer product. |
| [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) | MIT code; README describes a GPT-Neo-2.7B local default, but inspected `scripts/local_infer.py` actually defaults to **Falcon-7B + Falcon-7B-Instruct**. Explicit equal GPT-Neo aliases reuse one model. | See the [suite assessment](detector-suite-assessment.md#statistical-detectors) for the smaller candidate configuration. More efficient than perturbation-based DetectGPT is not browser-lightweight; the demo probability mapping is not validated on X. |
| [MultiSocial](https://github.com/kinit-sk/multisocial) | GPL-3.0 experiment code and a 22-language social-media benchmark. No ready fine-tuned checkpoint verified in this pass. | Strong domain-relevant research direction, not a drop-in detector. The [Zenodo data release](https://zenodo.org/records/13846152) is restricted and states noncommercial research intent; do not treat the code license as permission to reuse all social posts commercially. |
| [DetectRL](https://github.com/NLP2CT/DetectRL) | Benchmark and experiment code for edits, prompts, spelling errors, and generalization. | Useful evaluation design, not a single shippable detector. Do not rank benchmark projects against trained checkpoints. |

The previously reviewed Desklib, tropa-mini, and Open Pangram/EditLens remain in the [original comparison](detector-research.md#local-cpu-candidates). None gains priority over the compact shortlist from this follow-up.

## Smallest useful next test

1. **Browser/CPU track:** compare E5-small quantized ONNX against TMR int8 on exactly the same posts. First check tokenizer/label semantics and native-versus-ONNX output parity, including any extra attention outputs in the E5 export. Measure cold start, per-post latency, download, and peak memory using actual browser WASM.
2. **Optional local-service track:** add Tabularis ModernBERT in Python on CPU. Keep its reported RAID scores separate from our results. Test raw and its recommended normalized inputs as explicit configurations; NFKC alone does not remove zero-width characters or collapse whitespace, despite loose wording in the card.
3. Use the existing [length-bucketed evaluation plan](evaluation.md): human false positives first, then AI recall, coverage, and calibration. Include unseen generators, casual human replies, non-native writing, and human edits. Do not just score training-like essays.
4. Pin original and converted revisions, record licenses, preserve raw outputs, and never attach a percent sign to a statistical score without a justified probability mapping.

**Decision:** prioritize **E5 + TMR**, with **Tabularis** as the first service-side challenger. Keep **rasbt DistilBERT** as the next lightweight alternative. No paid API, generic LLM judge, model download, or inference is required to reach this research shortlist; selecting a production detector still requires measured evidence.
