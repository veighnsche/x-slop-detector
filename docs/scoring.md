# Offline combined scoring — pilot executed, release gates unmet

**The real pilot has now been collected, fitted, and evaluated; product scoring validation is not complete.** After explicit permission to temporarily resume the shared service, all 818 evidence records were collected on the 3060, nine candidates were fitted/frozen, and held-out evaluation reproduced successfully. The combined scorer did not establish improvement over the development-selected baseline, and calibration worsened held-out probability metrics. See the [measured results and decision](scoring-pilot-results.md).

The shared service was restored to persisted pause with all four required models unloaded. This is implementation and pilot evaluation of the scoring work, **not** the separate API/UI percentage path. The running service code and extension were not changed or redeployed; the extension still displays `—`.

**Subsequent benchmark repair:** [independent-group gates and process-record intake](benchmark-acquisition.md) are now implemented. Collection/fitting/evaluation refuse inadequate independent-class/native-short counts; the original pilot fails. Its artifacts/results remain historical and unchanged, but the strengthened CLI intentionally refuses to refit/evaluate it. The replacement adequately sized corpus has **not** been acquired.

## What the code does

| Component | Implemented behavior |
| --- | --- |
| [Provenance and evidence records](../detector_eval/data.py#L1) | Strict source permissions/revision/hash, original text hash, process-label basis, author/root/lineage groups, language/cohort, and native checker records. Unknown labels are not negative examples. |
| [Pinned pilot importer](../detector_eval/aitdna.py#L1) | Downloads a specific process-recorded source file, verifies SHA-256, constructs exact whole/derived passage records, retains ambiguous assistance as unknown, and labels deliberately constructed retained mixtures separately. No upstream code or LLM-judge annotations executed. |
| [Collector](../detector_eval/collect.py#L1) | Authenticated private HTTPS, bounded four-post batches/retries, resumable journal, exact IDs/text coverage/checker revision validation, code/library/driver runtime audit, and configuration-change rejection. No Load/Unload requests, no hosted route activation, no token persistence/logging. |
| [Fitting/freeze](../detector_eval/train.py#L1) | Learned L2 logistic stack of the three classifier outputs and raw Neo discrepancy, development-only scaling, separate sigmoid calibration, development-group-CV baseline selection, and operating-partition thresholds. No manual detector weights or raw-score averaging. |
| Comparisons | Full four-checker model, each fitted individual detector, and four leave-one-out ablations. Raw classifier outputs also appear as diagnostic score references, not calibrated probabilities. All comparisons use the same complete-evidence rows; no silent reduced-profile claim. TMR replacement is not evaluated in this pilot. |
| [Evaluation](../detector_eval/metrics.py#L1) | Brier/log loss, AUROC, ten-bin reliability/ECE, frozen-point FPR/recall, coverage/unknown/failure counts, effective rates including abstentions, length/cohort/language/generator strata, and paired connected-group bootstrap comparisons. |
| [Portable artifact](../detector_eval/profile.py#L1) | Strict hash-checked JSON with exact checker/configuration/extraction/runtime identities, learned scaling/coefficients/calibration, corpus/split/fit/calibration fingerprints, population and limitations. No pickle or model-library import required for inference. |

The artifact has `validation_state: "benchmark_only"` and `deployment_approved: false`. Its prediction method is usable for offline evaluation; its evidence-scoring method requires explicit benchmark opt-in. **A fitted number is not proof of a supported feed probability.** No API probability or client rendering behavior is enabled by writing this artifact.

## Data and provenance

Source: [UKPLab/AITDNA](https://huggingface.co/datasets/UKPLab/AITDNA), associated with [Dycke et al., “Your AI Text is not Mine”](https://arxiv.org/abs/2606.04906).

- Pinned dataset revision: `21d77f7d44833507750c0da309295c4147c1bda5`.
- Input: `span/test-00000-of-00001.parquet`.
- File SHA-256: `0641d20f9326522061bee792cad5f8963faf26bf37268e491f901cb7c2ce5cfb`.
- Observed: **362 sessions, 99 pseudonymous authors, 95 human-only sessions**, and source-reported GPT, DeepSeek, Qwen, Llama and Gemini interactions.
- The source contains writing-process/genesis information rather than a detector-generated “human” label. Participant compliance is source-reported, not independent forensic proof.

**Licensing conflict:** the publisher's dataset metadata says **CC BY-SA 4.0**, while the prose card says **GPL-2.0**. Both advertised licenses permit private evaluation; this pilot is kept private/nonredistributed, and no release entitlement is inferred. Resolve this conflict before redistributing data/artifacts or claiming production rights. The code repository's license is not substituted for the dataset license. CoAuthor was investigated but not used: no unambiguous dataset-license grant was established from its official page.

### Pilot construction

Prepared **818 examples**:

| Cohort | Count | Label treatment |
| --- | ---: | --- |
| Unaided human whole/derived passages | 374 | Negative only when source `human_only` is true and all retained spans are `User`. |
| Recorded generation/style-rewriting passages | 142 | Positive verbatim `Bot` passages under a conservative exact set of composing/style-rewriting instructions. They are not independently authored short posts. |
| Controlled retained mixtures | 35 | Intact unaided-human passage plus an intact recorded model passage from the same pseudonymous author. Both source roots are grouped. These are **constructed mixtures, not natural human-edited examples**. |
| Assisted source documents requiring target review | 267 | **Unknown**, excluded from binary fitting/accuracy, retained in coverage accounting. “Polish this text” or mere AI involvement is not silently relabeled substantive generation or human authorship. |

The importer preserves exact source substrings. Its English regex sentence segmentation can split abbreviations and is a declared limitation; it is not a replacement for natural short-social collection. Character buckets are 1–80, 81–160, 161–280, >280; whitespace-English word buckets follow the evaluation protocol.

No input text, individual author record, fitted weight file, or per-item prediction is published in these docs. The prepared corpus lives in ignored local `.cache/evaluation/aitdna-pilot-v1/`; it is not assumed replicated to other machines.

### Split prepared before detector collection

Author/root/declared prompt/lineage groups and exact/near duplicates form connected components. Entire components stay together. Duplicate normalization is **only for grouping**, never detector preprocessing. Gemini and every connected author/root touching it are reserved outside fitting/calibration/threshold selection.

| Partition | Examples | Connected groups | Negative / positive / unknown |
| --- | ---: | ---: | --- |
| Development | 154 | 22 | 68 / 35 / 51 |
| Calibration | 103 | 10 | 51 / 23 / 29 |
| Operating point | 84 | 13 | 45 / 14 / 25 |
| Main holdout | 79 | 11 | 36 / 13 / 30 |
| Unseen-family challenge block | 398 | 41 | 174 / 92 / 132 |

These are **corpus/split counts, not scored coverage or performance results**. Actual supported coverage and performance are recorded [separately](scoring-pilot-results.md#coverage-and-denominators): 658 examples had complete evidence, including 527 known-label examples. The challenge block also includes other-model passages from withheld authors; evaluation separately reports Gemini-positive examples plus the challenge human controls.

“Unseen” means unseen to this combiner. Base-detector training overlap is unknown. Source topic/prompt/event IDs are insufficient to prove independence on those axes; this limitation is retained explicitly and blocks a release claim.

## Learning and holdout safeguards

1. Only complete, compatible four-checker evidence and known target labels enter fitting. Missing/unsupported/failed checks are **not zero**, and watermark values are **not fusion features**.
2. Each connected group contributes one unit of fitting/calibration mass, split equally among its eligible records. The constructed calibration mixture and its positive fraction are recorded; no prevalence for X is invented.
3. Fixed starting hyperparameters: `C=1`, `lbfgs`, tight convergence tolerance, at most 2,000 iterations. Nonconvergence is an error. Development-only group CV selects the individual baseline; no final-test selection.
4. The scaler and stacker fit on development only. A regularized sigmoid fits on calibration only. Frozen thresholds targeting nominal **0.5%/1%** FPR are selected on operating data only, with conservative tie handling.
5. `fit` writes the candidate artifacts and `frozen.json` **before evaluating holdout/challenge metrics**. `evaluate` never fits. It verifies all fingerprints, feature indices, versions and profile files, then records `holdout-use.json`.
6. Exact frozen reproduction is allowed for studies meeting the current pinned policy. Evaluating a different frozen model against an already consumed study holdout is rejected. This guards accidental reuse; it is not cryptographic protection against an operator deleting/copying files or deliberately examining labels. The historical pilot reproduced under its original code; it is intentionally rejected by the new adequacy gate.
7. Paired proper-score differences use connected-group resampling, not independent-row bootstrap. For rare false positives, a separate one-sided exact bound concerns **any false flag within a negative group**, under explicitly stated independent-group/uniform-group assumptions. A zero-error bootstrap is never sufficient evidence of a zero FPR.

The report includes hypothetical prior-shift sensitivity under **unverified label-shift assumptions**. These scenarios are not estimates of real prevalence and cannot authorize a feed probability.

### Why this pilot cannot establish product accuracy

Even perfect observed performance on this small heldout group count cannot establish a 0.5% FPR. Derived passages are not independent contributors or naturally short posts. The source does not supply validated natural-human editing, translation, mechanical-only and ideas-only controls. Its population and class mixture are not X.

The report therefore records unresolved gates instead of relabeling them as passes: source rights, deployment population/prevalence, short-social distribution, unsupported grouping axes, missing target cohorts, meaningful minimum recall/coverage, rare-FPR evidence, and incremental suite value. A separate profile review plus API/UI implementation remains necessary. **This is not completion of the requested scoring validation.**

## Reproduce

Separate optional environment; the running server's dependencies are not modified:

```sh
uv venv --python 3.11 .venv-evaluation
uv pip sync --python .venv-evaluation/bin/python requirements/evaluation.txt

# Choose a NEW output directory; never overwrite a consumed study.
.venv-evaluation/bin/python -m detector_eval.aitdna \
  --source-file .cache/evaluation/aitdna/span.parquet \
  --output .cache/evaluation/aitdna-pilot-v1

# Shared service must be unpaused by its operator. This does not issue Load.
.venv-evaluation/bin/python -m detector_eval.collect \
  --study .cache/evaluation/aitdna-pilot-v1

.venv-evaluation/bin/python -m detector_eval.train fit \
  --study .cache/evaluation/aitdna-pilot-v1 \
  --output .cache/evaluation/aitdna-pilot-v1/run

.venv-evaluation/bin/python -m detector_eval.train evaluate \
  --study .cache/evaluation/aitdna-pilot-v1 \
  --run .cache/evaluation/aitdna-pilot-v1/run
```

Skip the importer when the prepared directory already exists. Retain exact corpus/split/evidence/frozen files to reproduce a run; a new acquisition timestamp changes its provenance fingerprint. Reimporting the same texts does **not** create a new independent holdout.

The collector reads the operator token into memory over `ssh gpu`; it never stores or prints it. It audits the deployed `/home/xslop/venv` context before and after collection and refuses changes. This is a trusted-operator audit, **not remote attestation**. It stops on manual pause, bounded busy exhaustion, incompatible output, critical errors, or suite/runtime changes. A truncated/corrupt journal is rejected rather than silently accepted.

The real run produced `evidence.json`, nine candidate JSON profiles, `frozen.json`, `holdout-use.json`, and `report.json`; these remain private local artifacts. [Fingerprints and measured results](scoring-pilot-results.md#artifacts-and-reproducibility) identify the run. The holdout is consumed. Historical exact reproduction passed before the new adequacy policy; the current strengthened commands intentionally reject that inadequate study. A changed model needs new independent final data.

## Verification boundary

The new regression suite exercises strict provenance/hash/native-output handling, unknowns/missingness, watermark exclusion, group leakage, unseen-family separation, portable inference, no-production gating, actual fixture fit/calibration, freeze/evaluate/reproduction, rare-FPR uncertainty and final-feature isolation. **All fitted data in these tests is explicitly artificial unit-test data, not an accuracy benchmark.**

Run:

```sh
.venv/bin/python -m unittest discover -s tests -v
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv-evaluation/bin/python -m unittest discover -s tests -v
node --test tests/extension/*.test.cjs
```

Recorded local results after contributor-study preparation: **108 Python tests discovered** in each environment; **104 passed / 4 optional inference tests skipped** in the evaluation environment, and **97 passed / 11 optional inference/evaluation tests skipped** in the lightweight environment. **30 Node tests** passed. `git diff --check` and wheel construction/source-content verification passed; relative documentation links/anchors were checked. All 18 historical pilot candidate-table rows and published artifact fingerprints were checked against the real report/files. These new scoring/benchmark tests were not run on the Linux GPU host.

The subsequent real pilot passed collection → fit/freeze → evaluate → exact evaluation reproduction, separately from those synthetic regression tests. Shared Load/Unload was temporarily exercised with explicit permission, then pause was restored. No production service code changes, provider submissions, user-post collection, live-X benchmark, or new contributor recruitment were performed. **Next work is better independent data and development-only investigation, not activation of this unsuccessful pilot scorer.** Scientific/release gates remain unmet.
