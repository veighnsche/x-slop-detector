# First real scoring pilot — not approved for deployment

Recorded **1 November 2026**, following explicit permission to temporarily resume the shared RTX 3060 service, collect the prepared pilot, fit/evaluate the frozen candidates, and restore pause.

**Outcome: the pipeline ran successfully, but this scorer failed its release gates.** The four-detector stack did not establish an improvement over the development-selected individual baseline. Its separately fitted calibration worsened held-out probability metrics. Neither this stack nor an individual detector is approved as an X authorship percentage.

The shared service is paused again, all four required models are unloaded, and no production code, model selection, API behavior, or extension behavior was changed. The extension continues to display `—`.

**Later safeguard change:** the [replacement-benchmark policy](benchmark-acquisition.md) now rejects this inadequate study before collection, fitting or evaluation. This report and its original artifacts are preserved as historical evidence; reproducing that historical computation requires its original code/policy, not bypassing the new gate. No replacement benchmark or revised accuracy result has been obtained.

## What actually ran

1. Confirmed the shared service was paused, idle, and unloaded.
2. Armed a temporary remote pause/unload failsafe, then issued authenticated Load.
3. Verified diagnostic readiness on GPU UUID `GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db` — the RTX 3060, not the active 3090.
4. Collected real native evidence for **818 examples** through the private HTTPS endpoint, with configuration `local-suite-4eabaa3f0f48bbcdb252`. The deployed code/library/driver audit matched before and after collection.
5. Issued Unload and verified `paused: true`, `pause_persisted: true`, idle state, all four required components unloaded, and zero allocated/reserved allocator bytes. Stopped the failsafe timer after that verification.
6. Ran `detector_eval.train fit` locally in the pinned evaluation environment. Nine portable candidate profiles and operating thresholds were frozen before computing final metrics. The development-only grouped-CV selection was `single_fakespot`.
7. Ran `detector_eval.train evaluate`, creating the holdout-use receipt and report. Repeated that exact evaluation successfully; the report reproduced without changes.

The post-run GPU snapshot was **160 MiB** on the 3060 (residual process/context overhead), not zero physical VRAM. The service reported peak allocated **6624.55 MiB** and peak reserved **7604 MiB**; these are process-lifetime counters, not a continuously sampled pilot-only peak. The 3090 snapshot remained **18041 MiB**, matching its preexisting workload. There was no service restart or deployment.

The inference runtime audit recorded Python 3.12.15, torch 2.15.0, transformers 5.22.1, tokenizers 0.23.3, safetensors 0.8.0, numpy 2.5.4, and driver 615.71.10. Local fitting used the separate [pinned evaluation environment](../requirements/evaluation.txt#L1), not the deployed inference environment.

## Coverage and denominators

Corpus construction, source provenance, license conflict, labels, split rules, and limitations are described in the [scoring record](scoring.md#data-and-provenance). No raw text, author record, individual prediction, or fitted weights are published here.

- **818** native-evidence records; this does not mean every checker completed.
- **658 / 818 (80.44%)** had complete four-checker evidence within the study's supported input scope.
- Of **551 known-label examples**, **527** were eligible for fitting or accuracy evaluation in their assigned partitions.
- **267 ambiguous assisted documents remained unknown**; 131 had complete evidence, but none was forced into a human/AI accuracy label.
- No collection-level failures or per-check `failed` results occurred. Unsupported inputs were retained explicitly, not truncated or assigned zero.
- KGW remained unconfigured/unsupported; no hosted verifier was activated or included in fusion.

| Checker | Completed | Token-limit unsupported | Insufficient evidence |
| --- | ---: | ---: | ---: |
| Tabularis | 674 | 144 | 0 |
| E5 | 671 | 147 | 0 |
| Fakespot | 676 | 142 | 0 |
| Single-Neo Fast-DetectGPT | 667 | 142 | 9 |

The nine insufficient-evidence cases had no next-token observations. All 81–160 and 161–280 character examples had complete evidence; 104/113 at 1–80 characters and 302/453 above 280 characters did. **Availability is not accuracy.**

| Partition | Total examples | Complete evidence, including unknowns | Eligible known labels | Negative / positive | Eligible known-label groups |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 154 | 117 | 97 | 65 / 32 | 19 |
| Calibration | 103 | 83 | 66 | 47 / 19 | 9 |
| Operating point | 84 | 74 | 58 | 45 / 13 | 11 |
| Main holdout | 79 | 69 | 49 | 36 / 13 | 10 |
| Withheld-author/family challenge block | 398 | 315 | 257 | 169 / 88 | 39 |

These are linked source passages and derived variants, not independent contributors. All comparisons below use the same complete-four-checker known-label examples, even for an individual detector. They do not evaluate a separately supported missing-checker fallback.

## Primary comparison

All probability metrics give equal mass to connected groups; class-conditional FPR/recall give equal mass to groups containing that class. Raw counts therefore need not equal the displayed group-weighted rates. AUROC is a ranking measure, **not percentage accuracy**. Lower Brier/log loss is better.

“Fakespot baseline” below means the **learned, separately calibrated single-feature candidate**, not the raw Fakespot classifier score. It was selected using development-only grouped-CV log loss, not these final results.

| Measure | Main holdout: full suite | Main holdout: Fakespot baseline | Challenge block: full suite | Challenge block: Fakespot baseline |
| --- | ---: | ---: | ---: | ---: |
| Eligible examples / groups | 49 / 10 | 49 / 10 | 257 / 39 | 257 / 39 |
| AUROC | 0.697 | 0.824 | 0.585 | 0.613 |
| Brier | 0.14667 | 0.14533 | 0.16691 | 0.16696 |
| Log loss | 0.48526 | 0.47642 | 0.55168 | 0.55140 |
| Ten-bin ECE | 0.09505 | 0.09326 | 0.11522 | 0.11548 |
| False flags / human examples | 0 / 36 | 0 / 36 | 8 / 169 | 0 / 169 |
| Detected / positive examples | 1 / 13 | 5 / 13 | 13 / 88 | 19 / 88 |
| Group-weighted FPR | 0% | 0% | 4.94% | 0% |
| Group-weighted recall | 5.56% | 41.67% | 8.99% | 15.32% |

Rates use each candidate's own **frozen operating-data threshold** targeting nominal 0.5% FPR. That target was not established on the final data. For the full suite, the nominal 0.5% and 1% operating targets produced the same threshold because of the small operating sample.

The primary paired full-suite-minus-baseline differences were:

- Brier **+0.001343**, exploratory 95% connected-group bootstrap interval **[-0.000172, +0.003564]**.
- Log loss **+0.008839**, interval **[-0.001715, +0.022835]**.

Positive differences favor the individual baseline; both intervals include zero. **No incremental probability-quality benefit was established.** The challenge comparisons also had intervals spanning zero.

Zero observed main-holdout false positives is not evidence of a 0.5% population FPR. There were only **nine negative connected groups**. The one-sided 95% upper bound on the probability of *any false flag in a negative group* was **28.31%**, under independent/uniform-group assumptions. This is a conservative group-event bound, not a measured row-level FPR or an estimate for X.

### Calibration did not help this pilot

| Full-suite probability diagnostic | Main holdout: before sigmoid calibration | Main holdout: after | Challenge: before | Challenge: after |
| --- | ---: | ---: | ---: | ---: |
| Brier | 0.13283 | 0.14667 | 0.15852 | 0.16691 |
| Log loss | 0.42615 | 0.48526 | 0.50139 | 0.55168 |
| Ten-bin ECE | 0.04748 | 0.09505 | 0.08373 | 0.11522 |

Before-calibration values are diagnostics, **not an approved alternative probability**. Removing calibration or selecting a replacement after inspecting these final outcomes would be a new model-selection decision requiring fresh evaluation data. “A calibrator was fitted” is not a claim that calibration improved.

### Unseen-family and short-input checks

The Gemini-specific challenge slice contained **201 eligible examples**: 169 human controls and 32 Gemini positives. It overlaps the larger challenge block and is not an independent second test. Full-suite AUROC was **0.662**, group-weighted FPR **4.94%**, and group-weighted recall **13.57%**. The baseline's corresponding values were **0.673**, **0%**, and **19.29%**. “Unseen” applies to combiner fitting, not proven absence from base-detector training.

Full-suite AUROC by character length:

| Length | Main holdout eligible n | AUROC | Challenge eligible n | AUROC |
| --- | ---: | ---: | ---: | ---: |
| 1–80 | 11 | 0.569 | 51 | 0.175 |
| 81–160 | 12 | 0.664 | 64 | 0.547 |
| 161–280 | 10 | 0.842 | 58 | 0.668 |
| >280 | 16 | 0.875 | 84 | 0.875 |

These small, source-derived strata are descriptive, not independent tests or justification for choosing a new cutoff. In particular, very short text performed poorly despite mostly complete checker availability.

## All frozen candidates

These tables retain every candidate rather than only reporting a favorable ablation. Apart from the predeclared full-suite comparison with the development-selected baseline, comparisons are exploratory. **Do not choose a production winner from this used holdout.**

| Candidate | Holdout AUROC | Brier | Log loss | Group-weighted FPR | Group-weighted recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full suite | 0.69650 | 0.14667 | 0.48526 | 0% | 5.56% |
| E5 alone | 0.79469 | 0.15030 | 0.50923 | 2.78% | 18.06% |
| Fakespot alone — selected baseline | 0.82365 | 0.14533 | 0.47642 | 0% | 41.67% |
| Fast-DetectGPT alone | 0.91283 | 0.15011 | 0.50784 | 2.78% | 23.61% |
| Tabularis alone | 0.86098 | 0.14870 | 0.49755 | 0% | 54.17% |
| Without E5 | 0.68719 | 0.14663 | 0.48510 | 0% | 5.56% |
| Without Fakespot | 0.79675 | 0.14888 | 0.49879 | 0% | 0% |
| Without Fast-DetectGPT | 0.83304 | 0.14373 | 0.46716 | 0% | 59.72% |
| Without Tabularis | 0.68670 | 0.14744 | 0.48964 | 0% | 0% |

E5 alone and Fast-DetectGPT alone each falsely flagged one main-holdout human example. The other seven candidates had zero observed false flags there; the same small-sample uncertainty still applies.

| Candidate | Challenge AUROC | Brier | Log loss | Group-weighted FPR | Group-weighted recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full suite | 0.58489 | 0.16691 | 0.55168 | 4.94% | 8.99% |
| E5 alone | 0.42072 | 0.16974 | 0.56817 | 0.99% | 0.56% |
| Fakespot alone — selected baseline | 0.61281 | 0.16696 | 0.55140 | 0% | 15.32% |
| Fast-DetectGPT alone | 0.64800 | 0.16960 | 0.56711 | 4.42% | 9.83% |
| Tabularis alone | 0.68901 | 0.16831 | 0.55759 | 2.50% | 15.52% |
| Without E5 | 0.59450 | 0.16663 | 0.54981 | 5.81% | 12.73% |
| Without Fakespot | 0.55491 | 0.16912 | 0.56367 | 3.31% | 2.41% |
| Without Fast-DetectGPT | 0.62559 | 0.16603 | 0.54540 | 0.66% | 8.57% |
| Without Tabularis | 0.54471 | 0.16788 | 0.55776 | 0% | 0% |

## Artifacts and reproducibility

Private local artifacts are in ignored `.cache/evaluation/aitdna-pilot-v1/`. They are not assumed replicated or backed up elsewhere. Source licensing remains conflicted; no redistribution of the corpus, individual records, or profiles is authorized by this report.

Raw-file SHA-256 fingerprints:

| File | SHA-256 |
| --- | --- |
| `corpus.json` | `a77733c4381fcea2e5e204095266dfe1943316854a31fe41817e60e70091b30d` |
| `splits.json` | `0016f8cd02a6b6f78dcd87795d9a3dbbe0f7d1d47a6fd84f5be4cc5d10207b3e` |
| `evidence.json` | `513437344a5efeed7b92bc7e466563f6f6f1e35da6d2dfe0eb10a05d33ceaca2` |
| `run/frozen.json` | `1150c319dad054090ba51a62910141f38d32e6fc12d31e62f6266784bb4cd8a6` |
| `holdout-use.json` | `7eed2c3a9801eba12e81d7cc4060b738d1081d5ee1b651c4698511477e01313b` |
| `run/report.json` | `2c24cc14e9777558ff1caf68b14b3048fe08286eb6f80c7807e1c803af551248` |

The full-suite artifact's **canonical payload** SHA-256 is `c9c615e01503182fd1639d794351dc6c96063923cb727a10971c9e067ea3d598`. Canonical payload/receipt hashes use a different representation from the raw-file hashes above.

The run used the [documented commands](scoring.md#reproduce). Exact `evaluate` reproduction passed. Do not rerun `fit` into the existing directory, delete the holdout-use receipt, or treat a reimport of the same texts as a fresh holdout.

## Decision and remaining work

**Do not activate these profiles or silently replace the suite with Fakespot.** The pilot establishes that real collection, learning, freezing, portable inference, and reproducible evaluation work. It does not complete the requested scientifically supported product scorer.

Next work needs:

1. More independent, rights-cleared, naturally short human/AI/mixed examples, including natural edits, translation, mechanical-only and ideas-only controls. The pilot's constructed mixtures are not those controls.
2. A declared supported population and meaningful minimum recall/coverage, plus enough independent human groups to assess the rare-FPR target.
3. Development-only investigation of poor short-input generalization, feature contribution, and calibration behavior. Any changed candidate must be frozen before testing on **new independent evaluation data**; this holdout is consumed.
4. Resolution of source release rights and a separately reviewed scoring profile before the separate API/UI probability implementation or deployment.

No accurate combined score, real X calibration, general provider-watermark coverage, or completed-product release is claimed.
