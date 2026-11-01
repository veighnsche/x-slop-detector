# Short-post evaluation

Status: proposed validation; **not executed**. This is the evidence needed to choose a detector, not a requirement to build an elaborate evaluation platform before testing anything.

## Small first comparison

Run GPTZero, Sapling, and TMR int8 on the same labeled examples. Use Pangram 4 as an accuracy comparator, retaining its native output meaning. Add Fakespot only if the first local candidate is weak. Record unsupported inputs rather than silently dropping them.

Start with a small, manually audited set to test input coverage, output semantics, latency, cost, and obvious failure cases. Call this a feasibility run, not an accuracy validation. Paid API evaluation needs provider credentials and an explicit spending limit; this repository contains neither.

## Ground truth

- Human controls: consented, unaided writing with retained process evidence; optionally supplement with clearly dated pre-LLM social posts whose reuse is permitted. Include short factual replies, polished prose, jokes, slang, non-native English, quotations, URLs, emoji, and lists.
- AI examples: preserve raw generation outputs, exact prompts, model/version, date, and any subsequent edits. Include informal and concise prompts from several current generator families. Models may generate test inputs; they must not judge authorship or supply purported human controls.
- Mixed/AI-assisted examples: label separately. Agree what counts as AI-written before collapsing classes into one percentage. Grammar-only edits, AI drafts revised by humans, and human drafts rewritten by AI are different cases.
- Keep all variants of a source post, author, prompt, or event in the same data split. Choose thresholds/calibration on one partition and freeze them before the final holdout.

Publish only data whose license or consent permits redistribution. Keep source provenance and licensing records. A public model card or dataset listing does not automatically license every source post for republication.

## Required measurements

Report results separately for **1–80, 81–160, 161–280, and over-280 characters**, and **1–4, 5–15, 16–30, and 31–60 words** where samples exist. Report language and generator groups separately; do not imply multilingual validation from English tests.

1. Human false-positive rate and AI recall at fixed thresholds, with sample counts and confidence intervals.
2. Recall at 0.5% and 1% false-positive targets; freeze operating thresholds before final testing.
3. Coverage: rejected, unsupported, low-confidence, and scored posts. Include those abstentions in the coverage denominator; do not claim success on all posts after excluding hard cases.
4. Reliability of the displayed percentage using calibration plots and a proper probability score such as Brier score. A raw softmax is not automatically calibrated on X.
5. Cost per scored post, API response time, and local cold-start time, steady-state CPU latency, download size, and peak memory. Measure on the actual target hardware. Check float/quantized output differences for a local export.

A tiny test with zero false positives does not demonstrate a low population error rate. Roughly 600 independent human examples with zero errors give an approximate 95% upper bound of 0.5% by the rule of three. That is a rough sample-size guide, not a validated project result.

## Result handling

Preserve the provider's native classification, probability fields, confidence flag, model version, and input length in evaluation results. Never mix a content fraction, class probability, and watermark p-value into an unvalidated common score.

An unsupported or uncertain result is not 0% AI and is not evidence of human writing. If no candidate can support meaningful short-post scores, report that as an unresolved constraint and discuss the presentation with the user. Do not declare a longer-post-only extension to fulfill the complete requested experience.

## Completion condition

Select an implementation candidate only after its input coverage, score meaning, and operational cost are demonstrated. A successful feasibility run can justify an explicitly experimental extension; a claim of reliable AI-authorship confidence requires the stronger holdout and calibration evidence above. No extension implementation is included in the current documentation milestone.
