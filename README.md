# X Slop Detector

A planned Chrome extension that adds a small AI-writing estimate to X posts: just a percentage in the post header, immediately before the existing Grok/menu buttons.

**Status: detector research and project setup. There is no installable extension yet.**

## Intended experience

- Automatically evaluate a post's own text as it appears in the feed.
- Show a discreet percentage in the top-right header, without extra badges, panels, or automatic hiding.
- Run a dedicated text detector on local CPU or through an API.
- Provide a configuration screen for the chosen detector and its connection settings.
- Keep quoted posts separate from the author's own text.

The score concerns estimated AI authorship, not whether a post is useful, truthful, or worth reading.

## Detector requirements

No Jev, general-purpose LLM judging, or hand-written style heuristics presented as authorship probabilities. Detector selection must consider short X posts, false positives, supported input lengths, and what the returned score actually means. A statistical detector and a provider watermark checker are different kinds of evidence.

No detector is validated for this project yet. An API accepting a short string is not evidence that its predictions work on short posts. Missing or unsupported results must not be presented as 0% AI.

## What we can use today

Research checked **1 November 2026**:

| Path | Recommended first candidate | Why it is provisional |
| --- | --- | --- |
| API | **GPTZero** | Its dedicated detector exposes class probabilities, fitting the requested number. Published evaluation starts at 250 characters; coverage and calibration for shorter posts are unverified. |
| Local CPU | **TMR RoBERTa-base, int8 ONNX** | An existing ~126 MB export offers a practical browser CPU path. Its model card warns about short/casual text; download size is not runtime memory, and X accuracy is unverified. |
| Accuracy comparison | **Pangram 4** | Promising short-text research, but documented product scope starts at 50 words and its current API returns classified text fractions rather than authorship probabilities. |

These are candidates to evaluate, not claims of a proven best detector. No reviewed option establishes reliable probabilities across the full range of short X posts. See [the evidence and alternatives](docs/detector-research.md) and [the evaluation plan](docs/evaluation.md).

## Documentation

- [Documentation index](docs/README.md)
- [Product requirements](docs/product-requirements.md)
- [Detector comparison and recommendation](docs/detector-research.md)
- [Short-post evaluation](docs/evaluation.md)

The current milestone includes source research only: no paid detection calls, model downloads, accuracy benchmark, or browser runtime test has been performed.

## License

[MIT](LICENSE). Detector models, datasets, and hosted services have their own licenses and terms.
