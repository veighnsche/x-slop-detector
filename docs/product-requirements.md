# Product requirements

See [consolidated state](requirements-and-state.md). Approved implementation now covers the API contract, local suite/residency, [conditional watermark/provider-policy framework](watermark-routes.md), [thin Chrome research client](extension.md), and separately approved [private operational deployment](private-deployment.md). No hosted verifier is connected; live-X/manual acceptance, calibration, and completed-product release remain open.

## Requested behavior

1. A Chrome extension for X/Twitter.
2. Automatically estimate whether each post's text was written by AI.
3. A single, unobtrusive percentage in the top-right post header, immediately before X's existing buttons. The reference screenshot resolves the original left/right wording.
4. A dedicated analysis server with the Chrome extension as a thin client. Prefer the passive RTX 3060, with CPU checks and suitable hosted APIs allowed; the architecture is not restricted to GPU inference.
5. A compact control panel and cogwheel configuration dialog for the server connection, suite/profile status, route applicability/access/privacy, and operational controls.
6. Use a dedicated AI-text detector. Jev and general-purpose LLM judging are explicitly excluded.
7. A public GitHub repository with a README and documentation.
8. Multiple dedicated detectors and applicable signature/watermark checks, not the single Tabularis adapter treated as the complete system. The initial validation roster and score semantics are approved in the [design brief](design-brief.md); final production membership and validated scoring remain unresolved.

Do not replace AI-authorship detection with content-quality filtering, bot-account detection, or keyword matching.

## Scope of the current milestone

The initial milestone created detector research, a single-model prototype, and standalone probes. Approved implementation then added the v2 contract and real local suite/shared residency, tested via `ssh gpu`. These establish bounded operation, not combined-score accuracy or complete signature/extension coverage. Subsequent phases remain separately authorized.

Load on demand, idle-unload, and expose quick Load/Unload in the implemented extension. Manual unload cannot be immediately undone by background analysis; its pause persists across restart. See [runtime and validation status](suite-runtime.md) and [extension installation/evidence](extension.md). No normal-profile installation or live-X acceptance has been performed.

## Interpretation needed for a useful score

The approved percentage target is the probability that the post's own text contains substantive LLM-generated/rewritten wording, including translation and retained mixed text but excluding mechanical/ideas-only assistance. The fraction of words classified as AI, a raw classifier score, and a watermark significance test are not interchangeable with that probability. No unvalidated combined percentage is shown in the feed.

Analyze only the text belonging to the post being scored. Do not pad a short post with its quoted post, replies, author biography, or other posts to satisfy a detector's minimum length. That would answer a different question.

Text-only detection does not determine whether an attached image, video, or audio clip is AI-generated.

## Unresolved constraints

- Many X posts are shorter than dedicated detectors' documented minimum or recommended input sizes. The requested per-post experience remains a requirement; partial length coverage must be made explicit and must not be called a complete solution.
- A percentage on every post needs evidence that a detector can meaningfully score those lengths. An unsupported, failed, or insufficient-evidence result must never become an invented percentage.
- The approved insufficient-evidence direction is a discreet `—` with an explanation. This is not permission to call inadequate coverage a complete implementation of the requested experience.
- A dedicated statistical classifier can still make mistakes. Its training objective does not itself establish accuracy on current short social posts.
- Provider watermark detection is distinct from statistical authorship inference. No watermark found does not establish human authorship.

## Implementation boundaries

Keep the core experience small: post extraction, dedicated detection, result caching, percentage placement, and configuration. No automatic hiding, category labels, account scoring, community voting, telemetry, or general-purpose judgment prompts are requested.

The extension sends own-post text to the configured analysis server by default. Hosted provider submissions require individual route approval after terms/privacy review. Provider credentials stay server-side; only the server connection credential belongs in extension-local storage, not sync, page state, or this public repository. Include only permissions and data needed for the selected workflow.
