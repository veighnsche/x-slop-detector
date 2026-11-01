# Bounded operational feasibility checks

Executed **1 November 2026** on `linux.dimensionlab.net` through `ssh gpu`. This tests the [proposed candidates](detector-suite-assessment.md), not just the original Tabularis adapter. It is **not an accuracy/calibration benchmark, production integration, or implementation plan**.

## Outcome and remaining blockers

- **Tabularis, E5, Fakespot, and TMR loaded and ran on CPU and the RTX 3060.**
- **One-model GPT-Neo-2.7B Fast-DetectGPT ran on the 3060 and CPU.** The reviewed reference discrepancy function produced finite results on the tested samples; its demo probability mapping was deliberately not used.
- **Tabularis + E5 + Fakespot + Neo coexisted** on the 3060 and produced all four outputs for bounded two/16-post batches. TMR was then loaded alongside them and exercised. Sequential residency is therefore not necessary for these tested sizes; execution was sequential, **not** simultaneous GPU streams or concurrent clients.
- **A real local known-key watermark check worked on CPU**, with the generating model released before verification. It correctly distinguished marked, unmarked-AI, and wrong-key controls for the specific test configuration.
- **Hosted provider verification remains access-blocked/unverified.** No authorized usable text-verifier credentials/endpoints with established acceptable usage terms were available for this project. Those routes were not input-tested or replaced with unrelated artifact APIs.
- All probe processes exited; the 3060 returned to **15 MiB aggregate usage** and the active 3090's before/after readings were **6105 MiB**, with the same two existing ComfyUI processes. No service, public port, server adapter, or Chrome code was changed.

## Environment and test boundary

Python **3.12.15**, PyTorch **2.15.0+cu132**, Transformers **5.22.1**, NVIDIA driver **615.71.10**. The GPU probe required the **RTX 3060 selected by UUID**, exposed as only `cuda:0`; it refuses an unselected/wrong GPU rather than spilling to the 3090. CPU work used **four intra-op threads** and one inter-op thread.

Pinned model/code revisions are in the [assessment record](detector-suite-assessment.md#source-revisions-observed) and the probe scripts. Encoders used **FP32**, GPT-Neo **FP16**, eager attention, safetensors, and no remote model code. No quantization or offload changed the candidate definitions.

Six fixed synthetic strings covered a tiny reply, an ordinary sentence, informal emoji text, Japanese text, code/URL text, and a short paragraph. They are smoke inputs **without accuracy labels**. They were neither collected X posts nor representative evaluation data. Raw text was used, without publisher cleaning; Japanese scores do not imply multilingual support.

Classifier batch timing used two short samples, repeated to form a 16-post batch. Near-limit measurements used artificial repetitive text of **491 encoder tokens / 490 Neo tokens**. The probe imposed a **512-token cap**, even though Neo's backbone supports longer contexts. There was no 16-long-post stress test, sustained traffic, client/network overhead measurement, or concurrency benchmark.

Latencies below are wall-clock and include tokenization, device input transfer, inference, and result extraction/synchronization. They exclude HTTP, network transit, queueing, and extension work. CPU medians use three calls, GPU short medians five, near-limit and suite medians three. A warm median is not a worst case or a production throughput guarantee.

## Individual classifier measurements

Latest diagnostic-enabled run; VRAM is process usage sampled after the short and near-limit checks, **not a universally sufficient allocation**.

| Candidate | Cached load to GPU | CPU batch 2 median | GPU batch 2 median | GPU batch 16 median | Near-limit single median | Process VRAM after checks |
| --- | --- | --- | --- | --- | --- | --- |
| Tabularis | **0.539 s** | **44.281 ms** | **18.377 ms** | **19.222 ms** | **32.625 ms** | **782 MiB** |
| E5-small | **0.343 s** | **15.452 ms** | **10.008 ms** | **10.808 ms** | **10.441 ms** | **310 MiB** |
| Fakespot | **0.468 s** | **32.721 ms** | **10.124 ms** | **10.889 ms** | **19.403 ms** | **690 MiB** |
| TMR | **0.459 s** | **33.076 ms** | **10.060 ms** | **10.665 ms** | **19.333 ms** | **690 MiB** |

Cached loading includes tokenizer/model initialization and transfer; it is not first-download latency. The first GPU batch of a process/model ranged from about 11 to 166 ms. Model deletion, collection, and allocator release returned PyTorch allocated/reserved memory to **zero**, leaving about **132 MiB** CUDA/process overhead until exit. CPU RSS did not necessarily fall immediately; GPU unload is not a promise that all host memory is returned to the OS.

All four encoders reported **no missing, mismatched, or unexpected checkpoint keys**. Scores repeated exactly on the tested GPU calls. FP32 CPU/GPU score differences on the two parity samples were at most **6.56×10⁻⁷**. This establishes operational repeatability for these cases, not cross-version reproducibility or confidence calibration.

## Statistical method and co-resident suite

The probe uses the pinned `get_sampling_discrepancy_analytic` function, extracted from the reviewed MIT reference source, with **one Neo model's logits occupying both method roles**. No Falcon pair or demo normal-density probability conversion was used.

| Measurement | Observed |
| --- | --- |
| Neo cached load to GPU | **2.294 s** |
| Neo first short GPU inference in latest process | **357.837 ms** |
| Neo warm short GPU inference, one post | **30.777 ms median** |
| Neo near-limit GPU inference, 490 tokens | **177.811 ms median** |
| Neo short CPU inference, FP16, four threads | **915.844 ms median** |
| Four-model suite, two short posts, all four outputs | **101.069 ms median** |
| Four-model suite, 16 short posts, all four outputs | **534.830 ms median** |
| Four models after inference, process VRAM | **7142 MiB ≈ 6.97 GiB** |
| Four models, PyTorch peak allocated / reserved in inference phase | **6615.45 / 7002 MiB** |
| Five models including TMR, after its short inference, process VRAM | **7290 MiB ≈ 7.12 GiB** |
| After releasing all models, PyTorch allocated / reserved | **0 / 0 MiB** |
| After releasing all models, process VRAM | **140 MiB**, then no probe allocation after exit |

The cached ordered suite-load calls took approximately **5.62 s total** in a fresh probe process with an already populated disk cache. Initial Neo download-plus-load in the first pass took **92.266 s**, including roughly 10.67 GB of weight download; this one network observation is not a download-time guarantee. The model cache now occupies approximately **13 GiB** (`du -sh`).

Neo emitted **48 unexpected legacy attention-mask buffer keys** (`attn.attention.bias` / `masked_bias`), with **zero missing/mismatched keys or loading errors**. The diagnostic-enabled probe accepts only those exact buffer-name patterns and rejects other loading discrepancies. These are not randomly initialized missing learned weights; nevertheless, this does not prove parity with an older reference Transformers implementation.

The raw Neo criterion for one short sample was **−0.097229** on GPU and differed by approximately **0.004211** on FP16 CPU. GPU repeat difference was zero for that sample; all six synthetic criteria were finite. CPU and GPU are therefore not interchangeable exact-score configurations. Numerical precision, sparse next-token evidence, and near-zero variance still need systematic checks before assigning thresholds.

Classifier outputs also differed substantially: on one informal smoke string, Tabularis returned about **0.829**, E5 **0.517**, Fakespot **0.0046**, and TMR **0.602**. These are **not** a labeled accuracy comparison, but they concretely show why “all softmaxes agree” or a simple mean cannot be presumed meaningful.

## Local watermark feasibility

The [CPU watermark probe](../scripts/probe_watermark.py#L1) used Transformers' **KGW-style** public configuration:

- GPT-2 revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, used only to generate controls.
- Public demonstration key `15485863`, green-list fraction 0.25, bias 2, left-hash seeding, context width 1.
- Generate marked and unmarked **128-token** continuations with the same seed/prompt settings. Decode to text, then re-tokenize for verification, rather than verifying generation tensors directly.
- Release the GPT-2 generator and verify by weak reference that it is gone **before** constructing/running detection-only checks.
- CPU verifier, repeated n-grams ignored, z threshold 4. No CUDA context was initialized.

| Control | Outcome | Native z score |
| --- | --- | --- |
| Marked text, matching configuration | **Detected** | **6.8133**, 114 scored tokens |
| First 32 tokens of that marked control | **Detected in this one fixture** | **4.0056**, 30 scored tokens |
| Unmarked AI-generated control | **Not detected** | **−0.1081** |
| Marked control, wrong key | **Not detected** | **−0.3244** |

Cached 128-token CPU verification took **89.699 ms median across ten calls**. This measurement excludes generating controls/model loading; the generator was not resident during verification. The marked/unmarked continuations took about 3.7/3.5 s to generate on CPU, but generation is **not part of detecting someone else's text**.

**This is real local conditional watermark verification, not Claude/Gemini/Grok/textGrain verification.** The correct negative on unmarked AI text is especially important: “not detected” is not “human.” One 32-token positive fixture does not validate short-post recall or a population false-positive rate.

The library's reported p-values are preserved in the raw JSON, not converted into authorship confidence. Source inspection showed `WatermarkDetector._compute_pval` uses an approximation, not an independently calibrated X-text null distribution. We used its z-threshold decision for this fixture; this pass did not validate the p-value approximation or statistical assumptions.

Other local schemes (SynthID Text, TextSeal, public-key variants) were **not** runtime-tested in this pass. Known-configuration KGW success does not establish their compatibility, performance, or real-world configuration coverage.

## Failures, boundaries, and hosted routes

- The probe guards rejected blank/whitespace text and overlength input before inference; the statistical probe also rejected a single-token case with no next-token evidence. Guards returned explicit reason strings, not zeros.
- Tokenizers emitted length warnings when preparing oversized/near-limit fixtures. Oversized token sequences were not fed into model forward calls.
- All successfully tested classifier probabilities were finite in [0,1]; all tested statistical criteria were finite and retained their different meaning. No aggregate percentage was calculated.
- These are **probe-script guards**, not new production adapters or API error contracts. The existing server still runs only Tabularis. Its 12 deterministic API/lifecycle tests were re-run on the host and passed; that does not prove multi-model API load/unload/cancellation behavior.
- The suite was co-resident and executed sequentially. Parallel requests/streams, full suite idle unload/reload through the API, low-memory competition, long-input worst cases, library upgrades, and a production scheduler were not tested.
- Provider access findings remain as recorded in the [signature investigation](signature-checkers.md#access-register-and-unresolved-facts). No approved callable hosted text verifier was available to check our inputs. No form was submitted, quota evaded, undocumented endpoint scraped, or paid call made.

**Readiness conclusion:** local operational feasibility is demonstrated for the bounded configurations above. Hosted verification is still blocked on access/terms, and neither combined detection quality nor final score semantics is established. This does not select a final suite or authorize dropping inaccessible signature routes.

## Reproduction and artifacts

The two new scripts are diagnostics only, separate from `detector_server`. On the isolated host environment, the executed commands were:

```sh
export HF_HOME=/home/vince/x-slop-test.Tsn5iXQm/models
export HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false
export CUDA_VISIBLE_DEVICES=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db

.venv/bin/python -u scripts/probe_suite.py --phase encoders --output probe-encoders.json
.venv/bin/python -u scripts/probe_suite.py --phase suite --output probe-suite.json
.venv/bin/python -u scripts/probe_watermark.py --output probe-watermark.json
.venv/bin/python -m unittest discover -s tests -v
```

Individual remote probe commands were bounded with `timeout --signal=TERM --kill-after=10s 175s`. The watermark script hides all CUDA devices before importing torch, independently of the shell selection. It uses GPT-2 weights to create controls, not to judge authorship.

Raw results remain in `/home/vince/x-slop-test.Tsn5iXQm/{probe-encoders,probe-suite,probe-watermark}.json`; the source snapshot, cached weights, and pinned reference function/license remain there too. Local and remote diagnostic source hashes were compared during testing. The probes create no service, persistent credentials, or collection of user posts. No private text was uploaded; only public artifact/source downloads occurred.
