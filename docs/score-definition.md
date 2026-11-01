# What the percentage means

**Current implementation:** v2 and the Chrome client still return/display no estimate; no combined percentage is available. The [offline scoring pipeline](scoring.md) has fitted and evaluated real pilot evidence, but [the measured candidates](scoring-pilot-results.md) did not establish ensemble benefit or meet release gates. No profile is deployed. Historical “implemented today” statements below describe the original design step, not the present runtime.

Prepared **1 November 2026**; the user subsequently approved the target/result-policy direction through [decisions C–D](design-brief.md#7-specific-decisions-for-approval). This is a product/evidence specification, **not an implemented scoring rule or permission to claim calibrated accuracy**. The [implementation plan](implementation-plan.md) carries it forward; actual implementation/release remains separately authorized.

## Recommended target

**The percentage should estimate the probability that the post's own text contains substantive LLM-generated or LLM-rewritten wording.**

It concerns the **text**, not whether its author used a particular product, whether a person is a bot, whether the ideas are original, or whether the post is useful or true.

“Substantive” distinguishes supplying/rephrasing the message from mechanical assistance. It does **not** impose a minimum post length or mean “more than 50% of the words.” A fully generated short reply still has AI provenance; the text alone may provide too little evidence to detect it.

### Why this target

| Possible target | Problem | Recommendation |
| --- | --- | --- |
| Only completely AI-generated posts | Excludes substantial AI rewriting and mixed writing; a small human edit creates an unstable boundary. | Do not use as the only headline target. Keep fully generated examples as a distinct evaluation cohort. |
| Any use of AI during the writing process | Includes ideas, fact lookup, spelling correction, and discarded drafts that may leave no detectable signal in the final text. | Do not claim text-only detection can identify every such workflow. |
| Substantive AI-generated/rewritten wording remains in the text | Covers the relevant generated, rewritten, and mixed cases while excluding merely mechanical assistance. | **Approved target**, requiring an auditable label protocol and evidence. |

This resolves the earlier “AI-written” ambiguity as a product choice, not an assumption that existing binary detector labels already match this event.

## Fully generated, assisted, and mixed writing

The final text and retained process evidence determine the evaluation label. Whether AI was ever opened is not enough.

| Writing process | Proposed headline target | Separate cohort to retain |
| --- | --- | --- |
| Human composes the post unaided | Negative | Unaided human |
| Human wording; spelling, punctuation, formatting, or narrowly mechanical grammar corrections only | Negative | Mechanically assisted human; important false-positive controls |
| AI supplies ideas/research, but the person independently writes the final wording | Negative | Ideas/research assistance |
| AI drafts the wording and the person posts it directly | Positive | Fully generated |
| Human edits an AI draft and substantive generated phrasing remains | Positive | Edited AI draft |
| AI substantially rewrites the expression/style of a human draft, even if the facts/ideas are human | Positive | AI-rewritten human draft |
| AI translates a post and that translation is used | Positive | AI translation |
| Human and AI passages are combined, with substantive AI wording retained | Positive | Mixed writing; not a fraction-of-words label |
| AI draft was discarded and the final text was independently rewritten by the person | Negative, if the process record supports that description | Discarded AI assistance |
| Provenance or the distinction between correction and rewriting cannot be established | Unknown label | Do not force into a binary calibration label |

For labeling, substantive contribution includes composing a message or replacing its expression with generated phrasing, beyond mechanical corrections. Borderline edit cases require documented review of drafts and edits; do not invent a universal edit-distance or word-count cutoff.

The same surface text can have different provenance: a person and an LLM can independently produce “Yes.” Process records can establish the example's origin, but the detector may still have no discriminating evidence. That is an **input/evidence limitation**, not permission to label AI-generated short replies human or exclude them from reported coverage.

Quoted **posts** remain separate inputs. A verbatim AI passage quoted within the author's own text can provide evidence about that passage's origin; it does not establish that the quoting person used a generator or that their surrounding commentary was generated. Keep attribution/quotation examples separate in evaluation and explain this text-level scope in results. Do not infer author intent or misconduct.

## Probability interpretation

For a supported scoring profile, the intended quantity is:

$$
P(Y=1 \mid \text{observed text evidence, checker results and availability, profile})
$$

where $Y=1$ is the recommended substantive-wording event above. This is the **target definition**, not a formula that makes existing outputs calibrated.

A displayed **72%** would mean: *the validated estimator assigns a 0.72 probability to that event under its documented scope*. Good calibration means that across comparable held-out cases assigned scores near 0.72, roughly 72% have the target provenance. It does not mean:

- 72% of the post's words are AI-generated.
- 72% of detectors voted AI.
- The author is 72% likely to be a bot, dishonest, or using a particular account.
- There is 72% certainty in the evidence itself or a 72% watermark match.
- The result is proof about this individual post.

Calibration depends on the deployment population, language/length/generator coverage, and AI prevalence. A balanced evaluation dataset does not establish X's real-world base rate. If no defensible deployment population or prevalence treatment is available, do not label a benchmark-calibrated number as a universal real-world authorship probability.

## How different evidence contributes

| Evidence | Meaning to preserve | What it cannot automatically do |
| --- | --- | --- |
| Classifier output | A model-specific class score, with its labels, revision, preprocessing, and precision | Become the final target probability by renaming the field; some models were trained only on human versus raw generation |
| Fast-DetectGPT criterion | A token-probability discrepancy statistic for its exact scoring configuration | Become a probability via the demo's preset distribution assumptions or an invented rescaling |
| Provider watermark result | Evidence of the provider's supported generation/processing watermark, within its coverage and error limits | Prove the whole post was AI-authored; set the percentage to 100%; identify the user; measure human contribution |
| Known-key local watermark result | Evidence consistent with that exact scheme, tokenizer, key/configuration, and test procedure | Verify an unrelated commercial provider or arbitrary unknown key |
| No supported watermark detected | A completed negative for that specific check | Prove human authorship or become an automatic “human vote.” Any score adjustment needs validated applicability/power and error characteristics |
| Unicode/formatting finding | An actual text artifact | Become authorship probability or substitute for a provider watermark |
| File provenance/signature | A validated assertion bound to its asset and issuer | Describe copied plain-text authorship when the asset/manifest is absent |

Watermark verification can be particularly useful positive provenance evidence, but it is not the same target as substantive wording. Light assistance, quoting, editing, and provider false positives complicate that mapping. Preserve the native evidence even when no headline number can be justified.

**Forbidden shortcuts:** arithmetic mean of raw detector scores, majority-vote percentage, hand-selected weights, assuming independence, “take the maximum,” a fixed probability boost for watermark detection, and `(1 − p-value) × 100`. A watermark p-value is a tail probability under a null model, not a posterior authorship probability; implementation approximations and multiple testing also matter.

A future combination must be learned/estimated and evaluated against the declared target, with source correlations and missing-result patterns represented. The approved evaluation direction starts with regularized logistic stacking and separate sigmoid calibration. No weights, thresholds, or fitted calibration have been obtained; method approval does not establish performance.

## Disagreement, unsupported input, and unavailable checks

There are two distinct questions:

1. Did each checker run successfully, and what native result did it produce?
2. Is the complete evidence pattern supported by a validated profile that can produce the intended probability?

One high and one low model score is not automatically “50%.” Disagreement is retained, not hidden. A validated combiner may legitimately assign an intermediate or non-intermediate probability; if that kind of disagreement is outside validated support, the result is inconclusive. Any disagreement/abstention rule must be evaluated, not invented after seeing the holdout.

| Situation | Required meaning | Approved presentation direction; details still need implementation/review |
| --- | --- | --- |
| Validated profile, supported evidence/input | A target probability with declared scope | One percentage in the existing header location; tooltip identifies target/profile and limitations |
| Successful checkers disagree | Native evidence differs | Keep individual results/reasons available; show a percentage only if the profile supports that pattern |
| Too little evidence, unsupported language/length, or unsupported score pattern | No justified target estimate | No invented number; discreet `—` with a specific explanation |
| Checker unavailable because access/configuration is missing | That checker made no observation | Report `unavailable`, not `not detected`; show what was not checked |
| Checker failed, timed out, or was rate-limited | No valid result from that checker | Report the failure; no zero substitution or silent stale result |
| Suite/profile not calibrated or target not supported | Raw diagnostics only, not the proposed probability | No feed percentage by default; control-panel diagnostics can show native scores with explicit labels |
| Loading / paused / server unreachable | Operational state, not a detection result | Distinct loading/paused/unreachable explanation; never 0% or a synthetic 50% |

The dash/control-panel direction is **approved** for honest unsupported/research results, not permission to call inadequate coverage a completed percentage-on-posts experience. If meaningful coverage cannot be achieved, bring that product constraint back to the user rather than redefine completion.

### No silent reduced suite

A scoring **profile** means the identified checker/model versions, input transformations and limits, score-target definition, evidence availability rules, and validated combination/calibration scope. It is not a configurable set of arbitrary weights.

- If the selected profile requires a check that fails or is unavailable, do not silently produce the same-looking percentage from fewer checks.
- A reduced/missing-evidence profile may produce a number only if that exact rule or supported missingness handling has been validated, identified to the client, and accepted as product scope.
- Do not renormalize weights over whatever happens to respond or divide by the number of available checkers.
- Permanently inaccessible provider verification cannot be called part of the suite merely because its adapter is listed. A classifier-only or known-key-only profile is a **different coverage proposition**, not silent fulfillment of the desired provider-signature layer.
- “Unsupported,” “insufficient evidence,” “unavailable,” “failed,” and a completed “not detected” must remain distinct in evidence records and coverage measurements.

Preserve native values, per-check status/reason, checker/model/configuration revisions, scored input length, selected profile, and calibration/support status for review. These are semantic requirements, not an implemented API schema. The current server's existing `ai_percentage` field does not satisfy them.

## Experimental release decision

There are three different claims:

| Release behavior | Assessment |
| --- | --- |
| Raw individual scores in an explicitly labeled diagnostic control panel | Honest for research use, provided they retain native meanings and are not called the combined probability |
| An unvalidated ensemble percentage, labeled “experimental” | **Not recommended.** The adjective does not justify an arbitrary combination or change an index into P(AI) |
| A data-backed target estimator with limited, clearly stated validation scope, still called experimental | Approved direction only; the actual profile, coverage, evidence, and release still need review/acceptance before deployment |

**Recommended default:** no unvalidated combined percentage in the feed. Keep research diagnostics separate until there is a defensible target-aligned estimator and coverage evidence. Even a later validated prototype should disclose its experimental status while generator/domain robustness remains limited.

This preserves the meaning of “percentage” instead of silently switching the product to an opaque AI-likeness index. It also means current operational feasibility alone does **not** justify calling the requested extension complete. It is not a demand to build a large evaluation platform before drafting the implementation plan.

Approved display direction: whole percentages, not several decimal places. Preserve full internal precision. A rounded 0%/100% must not be described as certainty; exact endpoint formatting and uncertain-state appearance remain UI details for review.

## Approval record and remaining gates

**Directions explicitly approved under C–D:**

1. **Target:** include generated drafts, substantive AI rewriting, translation, and retained mixed AI wording; exclude ideas/research assistance and merely mechanical corrections from the headline event.
2. **Launch policy:** do not show an unvalidated combined percentage in the feed. Permit clearly labeled raw diagnostics during research; allow an experimental probability only once its target/profile/coverage are backed by appropriate validation.

The user's subsequent “approve a-h” selects these product choices; it does not certify a scoring model or authorize implementation/deployment. Changing the target later requires changing labels and evaluating the estimator, not relabeling the same score. Provider coverage, deployment-population calibration, and acceptance of actual supported profiles remain unresolved gates.

**Implemented today:** still only Tabularis's uncalibrated AI-class estimate × 100 in the prototype API, and separate diagnostic probe outputs. No target-aligned fusion, trained calibration, changed API, new UI, or release permission was created in this step. [Evaluation work](evaluation.md) must address the proposed labels, population assumptions, correlations, and coverage before a combined probability claim.
