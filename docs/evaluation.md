# Short-post evaluation

**Implementation update:** the user subsequently requested scoring implementation and explicitly authorized temporary shared-service resume for the pilot. The [offline pipeline](scoring.md) collected 818 real evidence records, fitted/froze nine candidates, and reproduced held-out evaluation. [Measured pilot results](scoring-pilot-results.md) did not establish ensemble benefit or meet release gates; calibration worsened probability metrics. The shared service is paused/unloaded again. The original protocol below is preserved and is not satisfied by this limited pilot.

**Subsequent benchmark-repair authorization:** independent-group/native-short [adequacy gates and process-record intake](benchmark-acquisition.md) are implemented; the original pilot is now rejected before fitting or final evaluation. The replacement process-backed corpus and contributors have not yet been obtained. Historical protocol statements below are not new acquisition results.

Original protocol status, **1 November 2026**, before the implementation update above: evaluation/calibration direction was approved through [decision E](design-brief.md#7-specific-decisions-for-approval), not yet an executed benchmark. The subsequent private pilot supplies measured outcomes, but no new contributor recruitment/consent or validated X percentage. The earlier [operational probes](feasibility-checks.md) establish runtime feasibility only.

This replaces the earlier browser/commercial-API comparison with evaluation of the [current server-side candidate suite](detector-suite-assessment.md). The [score target and release policy](score-definition.md), study direction, and nominal 0.5%/1% FPR targets are now approved. Collection consent/use terms, actual study size, and numerical minimum recall/coverage still require agreement; targets are not achieved results. The [implementation plan](implementation-plan.md) specifies the work without authorizing its execution.

## 1. Acquire evidence-backed examples

### Primary corpus: collect original material with permission

Recommend a prospective, consented short-writing collection rather than treating scraped public posts as verified human controls:

| Cohort | Acquisition and evidence | Label handling |
| --- | --- | --- |
| Unaided human | Volunteers write original short posts/replies before seeing any generated alternatives. Retain a declaration of tools used and voluntarily supplied drafts/revision history. Use familiar social-writing tasks, not only essays. | Human control when the process evidence supports it; consent or a declaration alone does not prove authorship. |
| Fully generated | Generate from original, rights-cleared prompts with pinned local models. Preserve exact prompt, model revision, tokenizer/chat template, decoding parameters, seed, date, and raw output. | Fully generated, including very short outputs. Poor detectability does not change provenance. |
| AI draft, human edited | Give a participant a recorded generated draft and retain the final text and volunteered revisions. | Separate edited-AI cohort; judge retained generated wording using process evidence, not detector scores. |
| Human draft, AI rewritten or translated | Start from a consented human draft; record the rewrite/translation instruction and exact output, plus any final human edits. | Separate rewrite and translation cohorts. |
| Light assistance or discarded draft | Record mechanical corrections, ideas-only assistance, or an AI draft discarded before independent rewriting. | Keep these distinct from substantive rewriting; borderline cases remain unknown. |
| Mixed or quoted wording | Retain the human and generated source spans and editing history where available. Include clearly identified quotations as a separate cohort. | Do not equate a generated quotation with the poster personally using a generator. Keep quoted posts separate from own-post text. |

Collect workflow/cohort labels first, then map to the **approved score definition**: substantive generation/rewriting/translation positive, mechanical corrections and independently written wording negative. Do not invent a word-count or edit-distance cutoff to settle borderline cases. Two reviewers should independently review ambiguous process evidence without seeing detector outputs, reconcile disagreements, and retain an unknown label if unresolved. No LLM judges or detector-generated ground truth.

Participation must specify permission for private evaluation, derivative generation/editing, and public redistribution separately. Collect no private conversations or third-party text without suitable permission. Keep consent/contact records and sensitive process evidence outside the public repository; use pseudonymous contributor IDs in results. Agree retention, withdrawal, and publication handling before recruitment. No participants or consents have been secured yet.

### Free local generation route

These are acquisition candidates verified through public model metadata, **not models loaded or benchmarked in this step**:

| Candidate | Revision checked | Weight license / access |
| --- | --- | --- |
| [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | `1cfa9a7208912126459214e8b04321603b3df60c` | Apache-2.0; ungated |
| [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) | `cfbefacb99257ffa30c83adab238a50856ac3083` | MIT; ungated |
| [SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) | `a07cc9a04f16550a088caea529712d1d335b0ac1` | Apache-2.0; ungated |

This provides a concrete route to fresh examples from three model families without paid calls. Weight licensing does not by itself establish rights to every prompt or output: retain source/permission records and check applicable terms before collection and publication. Test generation memory/throughput separately on the 3060, with detectors unloaded if necessary; parameter count alone is not a fit test. No need to reserve the active 3090.

Use matched topics and intended lengths for human and generated writing, varied informal/formal instructions, and different decoding settings. Avoid the shortcut where humans write casual replies but every AI prompt requests a polished paragraph. Include generation failures in an acquisition log; define exclusion rules before examining detector scores.

These local models do **not** establish coverage of contemporary hosted GPT, Claude, Gemini, or Grok outputs. Those require separately authorized generation or provenance-backed exports, with model/version, generation settings, and any known watermark status recorded. Free consumer access is not permission for unlimited automated API use. No paid calls, provider applications, or user-post uploads are authorized by this proposal.

### Existing datasets: supplementary, not automatically lawful independent gold

| Source | Verified access/limitations | Proposed role |
| --- | --- | --- |
| [MultiSocial, official record/API](https://zenodo.org/api/records/13846152) | Record `13846152`, revision 10, reports **restricted** access and 472,097 texts across 22 languages/five platforms. The license field says CC BY 4.0, but the description specifies non-commercial research only. It also warns that older human-source labels and anonymization are imperfect. | Request/clarify access and conflicting use terms before use; inspect underlying source rights and contamination. Potential external social/multilingual stress set, not an already obtained corpus or definitive human ground truth. |
| [RAID dataset card](https://huggingface.co/datasets/liamdugan/raid/raw/main/README.md) and [benchmark repository](https://github.com/liamdugan/raid) | Public artifacts and MIT labeling, but underlying source rights still need checking. Public test labels are not supplied. All four shortlisted encoder detectors report RAID training exposure; exact overlap is not fully known. | Regression/adversarial comparison where permitted, **not primary independent short-X validation or calibration**. A different row is not proof of unseen distribution. |
| Historical public-domain writing, e.g. [Project Gutenberg](https://www.gutenberg.org/policy/license.html) | Check the individual work and applicable jurisdiction. Some works remain copyrighted; US public-domain status is not worldwide clearance. | Optional historical human-prose stress test, not representative short-social data or proof of no detector/pretraining exposure. |

Do not substitute a dataset's repository license for rights to every source text. Do not call pre-LLM dating infallible provenance. No dataset was downloaded or access application submitted in this step. Existing synthetic smoke inputs and the known-key watermark fixture are development fixtures, **not held-out examples or human controls**.

### Minimum provenance record

For each item retain a stable ID/content hash, original text, source and acquisition date, permission/license record and allowed uses, pseudonymous author, root/variant lineage, prompt/topic/event group, workflow label and reviewer confidence, language, and generator/edit records where relevant. Link all derivatives to their root. Preserve original text separately from the exact extension-extracted input; version extraction and preprocessing. Keep personal identities, keys, and sensitive evidence out of distributable manifests.

## 2. Define strata and unseen challenges

Report character buckets **1–80, 81–160, 161–280, and >280**, plus word buckets **1–4, 5–15, 16–30, 31–60, and >60**. Count Unicode code points for this character analysis, not X's weighted character allowance; document the word segmentation method and do not assume whitespace works for every language. Record each detector's own token count and truncation policy. Empty input is a separate invalid-input case.

Include factual replies, jokes, slang, emoji, URLs, lists, polished writing, non-native English, code, quotations, and mixed-language text. Keep natural short originals; shortening long documents is a separate derived-text challenge, not a replacement. Test typos, paraphrasing, human revision, translation, and copy/paste normalization, retaining all variants in one split.

Recommend an English-first primary study for tractable initial collection, **not an approved English-only product**. Report other languages separately with native-language review and adequate counts before making claims. Sparse length/language cells remain unvalidated; pooled performance does not fill them in.

Reserve at least one generator family entirely from combiner development/calibration/threshold selection for a final challenge. Also include unseen prompts/topics and later generator versions where obtainable. Distinguish:

- **Unseen to the combiner:** known from our split records.
- **Unseen to the base detectors:** often unknown because their training mixtures are incomplete. A newer Qwen revision does not establish an unseen family if Qwen outputs were in detector training.
- **Unseen to all underlying pretraining:** generally not provable here; do not claim it.

Keep a seen-family, new-author/prompt holdout as well as the family-held-out challenge so distribution shifts are visible rather than hidden in one aggregate.

## 3. Split before fitting, and seal the final test

Assign author, root/derivative, near-duplicate, prompt family, and event/topic groups before running comparisons. All connected variants belong to one partition. Organize collection around disjoint author/topic blocks so a shared prompt across every contributor does not accidentally connect the entire corpus. Check exact and near duplicates across public supplementary data and our collection; normalization for duplicate search must not silently alter scored text.

Use four disjoint purposes; determine counts from precision requirements, not a convenient random row-level 80/20 split:

| Partition | Permitted use |
| --- | --- |
| Development | Grouped inner cross-validation for feature transforms, combiner fitting, model selection, and suite/ablation choices. |
| Calibration | Fit the selected probability calibration mapping on fresh groups from the stated calibration population. |
| Operating point | Choose thresholds, abstention/support rules, and accepted missing-checker profiles. |
| Final holdout | Evaluate the frozen system once, including the separately identified unseen-family challenge. No tuning on these results. |

Pin corpus versions, split manifests, detector/checker revisions, extraction, target labels, transforms, combiner, calibration, availability profiles, and thresholds before opening the final holdout. Keep holdout text/labels away from model selection. If its results cause a redesign, it becomes development evidence; obtain a new untouched final holdout rather than reusing it as independent proof.

## 4. Test whether combining detectors actually helps

Run all comparisons on the same eligible inputs and report different support/abstention rates:

1. Tabularis, E5, Fakespot, and the single-model Fast-DetectGPT configuration individually.
2. The proposed four-producer suite, using a learned combiner rather than averaging.
3. Leave-one-detector-out ablations, especially removing the expensive Neo discrepancy calculation.
4. TMR as a controlled replacement/challenger, not an automatically added fifth vote.
5. Applicable watermark checks separately, and fusion with them **only when access and representative validation data actually exist**.

Select the best individual baseline using development evidence, not by choosing the winner after seeing the final holdout. Examine paired errors and disagreement by cohort; agreeing RAID-trained encoders are not independent witnesses. Report paired differences with author/root-cluster-aware uncertainty, together with coverage, latency, and memory. Prefer the simpler suite unless extra detectors demonstrate useful gains at the agreed false-positive/coverage constraints; do not infer complementarity from architecture names or a few smoke outputs.

### Recommended starting fusion/calibration method

Start with a small **regularized logistic stacking model**, learned on development data from the detector outputs (including the raw statistical discrepancy), with any feature scaling learned there too. Compare it with individual detectors under the same evaluation. This is a proposed method, **not fitted weights or evidence of improvement**. Keep the component outputs in their native meanings; no hand-set weights, vote count, maximum-score rule, or arithmetic mean masquerading as probability.

Fit a simple sigmoid probability calibration on the separate calibration partition where justified. Consider a more flexible method only if development evidence and calibration sample size support it. Measure calibration before and after; fitting a calibrator does not guarantee it works on a new language, generator, length, or population.

A watermark p-value is not an authorship probability. Do not use `1 - p` as a feature labeled probability or turn a positive into 100%. Validate watermark detection false positives/power separately for the exact scheme/key/configuration, length, editing, wrong-key and unmarked-AI cases. The existing known-key KGW fixture can validate plumbing, **not provider-wide applicability or a production fusion weight**. A negative/unavailable watermark check is not a human vote.

Missing/failed/unsupported checks must retain their status. Validate each allowed reduced-checker profile or a deliberately trained missingness-aware model using representative outages/availability; never substitute zero or silently renormalize. Profiles with no evidence remain unsupported under the approved result policy. Validate each such profile's support and percentage separately.

### Population calibration is a separate unresolved requirement

A balanced human/AI collection can compare detectors, but its calibrated probability describes that constructed population. It does **not** establish the prevalence of AI wording on X. Length, language, topic, generator mixture, and selective scoring can shift calibration even if the overall prevalence matches.

Deployment probability claims require a defensible provenance-backed sampling design for the intended population, or justified sampling weights/transport assumptions and validation. A controlled volunteer study is not automatically representative. Do not estimate the true AI prevalence using the detectors being evaluated. If it remains unknown, report benchmark-conditional calibration and sensitivity analyses at explicitly hypothetical prevalences, not a guessed X prior or a validated feed percentage. The release decision remains subject to the [score-policy proposal](score-definition.md).

## 5. Measurements and uncertainty

Approved direction: **0.5% false-positive rate as the primary operating target and 1% as a secondary comparison**, subject to achievable sample size and scientific evidence, not a guaranteed error rate. Choose thresholds on the operating-point partition, then report the **actual** held-out FPR and recall with intervals. Do not retune on the final holdout to manufacture “recall at 0.5% FPR.”

| Measure | Required reporting |
| --- | --- |
| Human false positives | False AI flags / scored negative examples, plus false flags / all eligible negative examples. Report negative-cohort coverage alongside both, so abstention cannot hide failures. Include unaided and light-assistance cohorts separately. |
| AI recall | True flags / scored positive examples, plus effective recall = true flags / all eligible positive examples. Report fully generated, edited, mixed, rewritten, and translated cohorts separately. |
| Coverage | Scored, abstained, invalid, unsupported, failed, timed out, and inaccessible-checker counts/rates, overall and by class/stratum/profile. Unknown-label items contribute to applicable coverage accounting, not binary accuracy. |
| Probability quality | Brier score and log loss, reliability plots with predeclared bins/counts and uncertainty, before/after calibration. ECE can supplement these, not replace them. State the evaluated population/weights. |
| Incremental suite value | Paired differences versus the selected individual baseline in recall at frozen operating points, proper probability scores, coverage, and resource cost. Include error overlap and ablations. |
| Operations | On the intended 3060/CPU setup: cold/cached loads, sequential suite latency, throughput, peak memory, unloading, failures, and any hosted cost/latency. Earlier bounded probes are reference measurements, not full-workflow results. |

Report counts and intervals overall and by length, language, generator, edit/assistance cohort, and checker availability where sample sizes permit. Use grouped resampling for paired comparisons and repeated-author/root data; state the method and independent group counts. A confidence interval over correlated variants cannot treat them as independent posts. For rare-event FPR, report suitable binomial bounds only when the independence assumptions are defensible; a zero-error bootstrap alone is not a meaningful upper bound.

Sample-size illustration, **not a result or a total corpus budget**: with zero false positives in 600 independent negative examples, the exact **one-sided 95%** binomial upper bound is `1 - 0.05^(1/600)`, about **0.498%**. With 300 it is about **0.994%**. A two-sided 95% interval has a different upper bound; 600 zero-error examples give about **0.613%**, not 0.5%. Repeated variants from a few authors do not provide 600 independent observations. Each claimed subgroup needs its own adequate evidence; 600 pooled examples do not validate every short-length/language cell.

Predefine minimum useful recall and coverage with the user before the final test. Low FPR achieved by scoring almost nothing is not success. Do not promise a numerical recall/coverage guarantee before pilot data and a feasible collection budget exist.

## 6. Staging and decision gates

1. **Protocol pilot:** propose roughly 100–200 original roots, with matched generations/edits, to check permission records, labels, extraction, split feasibility, runtime, and obvious failures. This is a collection/measurement pilot, not proof of sub-1% FPR or reliable percentages. No such pilot has been collected yet.
2. **Size the study:** use pilot event rates, independent contributor/root counts, desired interval widths, supported strata, generator challenges, and resource constraints to set the development/calibration/operating/holdout budgets. Obtaining enough independent human controls may be the main bottleneck. Do not count derived rows as new contributors.
3. **Freeze and evaluate:** execute the protocol only after approving target labels, supported population/profiles, consent/use terms, and minimum acceptable coverage/recall. Preserve all failures and unsupported cases in the report.
4. **Choose based on evidence:** include a detector only if its measurable benefit justifies its cost. If the suite is worse or inconclusive, say so. If short posts remain unsupported, discuss that constraint with the user; a longer-text-only result does not fulfill the requested feed experience.

**Enough to write the implementation plan:** a documented acquisition route, provenance/labeling rules, leakage-resistant splits, comparison/calibration method, metrics, and explicit approval/access/data gaps. The direction is approved and carried into the plan; completing the entire accuracy study is not a prerequisite to planning.

**Not enough to claim an accurate product:** this document, model-card scores, operational smoke tests, a fitted stacker without independent evaluation, or a balanced benchmark passed off as real-world calibration. Corpus acquisition, actual benchmarking, acceptance of a concrete release profile, provider access, and population calibration remain unfinished. No evaluation platform or production integration is implemented by approving the direction or writing the plan.
