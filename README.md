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

We have not selected or validated a detector yet. An API accepting a short string is not evidence that its predictions work on short posts. Missing or unsupported results must not be presented as 0% AI.

## Documentation

- [Documentation index](docs/README.md)
- [Product requirements](docs/product-requirements.md)

Research findings and the detector recommendation will be recorded in `docs/` before extension implementation.

## License

[MIT](LICENSE). Detector models, datasets, and hosted services have their own licenses and terms.
