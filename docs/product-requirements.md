# Product requirements

## Requested behavior

1. A Chrome extension for X/Twitter.
2. Automatically estimate whether each post's text was written by AI.
3. A single, unobtrusive percentage in the top-right post header, immediately before X's existing buttons. The reference screenshot resolves the original left/right wording.
4. Detection on local CPU or through an API. Either execution path is acceptable; supporting both is not a prerequisite to choosing a detector.
5. A custom configuration screen for the selected detector's settings.
6. Use a dedicated AI-text detector. Jev and general-purpose LLM judging are explicitly excluded.
7. A public GitHub repository with a README and documentation.

Do not replace AI-authorship detection with content-quality filtering, bot-account detection, or keyword matching.

## Scope of the current milestone

Create the public repository and compare available dedicated detectors using primary documentation and research, with particular attention to short X posts. Produce a recommendation with its practical limitations. Extension implementation and installation are subsequent work.

## Interpretation needed for a useful score

The intended percentage is the detector's estimate that the post was AI-written. The percentage of words classified as AI, confidence in a predicted class, a raw classifier score, and a watermark significance test are not interchangeable.

Analyze only the text belonging to the post being scored. Do not pad a short post with its quoted post, replies, author biography, or other posts to satisfy a detector's minimum length. That would answer a different question.

Text-only detection does not determine whether an attached image, video, or audio clip is AI-generated.

## Unresolved constraints

- Many X posts are shorter than dedicated detectors' documented minimum or recommended input sizes. The requested per-post experience remains a requirement; partial length coverage must be made explicit and must not be called a complete solution.
- A percentage on every post needs evidence that a detector can meaningfully score those lengths. An unsupported, failed, or insufficient-evidence result must never become an invented percentage.
- The presentation for insufficient evidence is not agreed yet. A blank result or a discreet dash with a tooltip is a possible design, not an approved reduction of the requested behavior.
- A dedicated statistical classifier can still make mistakes. Its training objective does not itself establish accuracy on current short social posts.
- Provider watermark detection is distinct from statistical authorship inference. No watermark found does not establish human authorship.

## Implementation boundaries

Keep the core experience small: post extraction, dedicated detection, result caching, percentage placement, and configuration. No automatic hiding, category labels, account scoring, community voting, telemetry, or general-purpose judgment prompts are requested.

An API mode will send the selected post text to its configured detection provider. Credentials belong in extension configuration, never in this public repository. Include only the permissions and data needed for the chosen implementation.
