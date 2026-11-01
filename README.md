# X Slop Detector

**Project stopped on 2 November 2026.** The implementation, research findings and proposal history are retained for reference. Plans and funding options below are historical; no further development, recruitment or expenditure is authorized. The intended percentage feature was not completed or validated.

**Not a finished percentage detector.** The extension currently shows `—`, not a combined percentage. The [first real scoring pilot](docs/scoring-pilot-results.md) was collected, fitted and evaluated, but did not establish a useful combined scorer or pass release gates. Its research profiles are not deployed.

The [benchmark repair](docs/benchmark-acquisition.md) now rejects inadequate independent-group/native-short studies and provides private writing-process intake. A sufficiently large replacement corpus has **not** been collected.

The [contributor-study proposal](docs/contributor-study.md) prepares a capped collection-method pilot and shows the much larger full-study cost separately. It is not recruitment or spending authorization; no public participant collector is deployed.

A thin Chrome extension backed by a dedicated multi-detector analysis server. The intended validated result is a small AI-writing percentage before the existing Grok/menu buttons; the current research client shows an explained `—`, not an invented score.

**Status: unpacked Manifest V3 extension plus a private HTTPS research service on the RTX 3060. Actual Chrome → HTTPS → GPU inference has passed with synthetic text/pages. No calibrated aggregate, active hosted verifier, or completed-product release yet.**

The server runs **Tabularis + E5 + Fakespot + single-Neo Fast-DetectGPT**, plus an optional [matching-configuration CPU watermark route](docs/watermark-routes.md). TMR can explicitly replace Fakespot. KGW is unsupported without operator configuration; it is not general provider coverage. **No hosted verifier or learned score combination is integrated.**

Design decisions A–H and implementation of phases 1–4 were approved separately. See [extension installation/testing](docs/extension.md), [runtime evidence](docs/suite-runtime.md), [watermark routes](docs/watermark-routes.md), [v2 contract](docs/v2-api.md), and the [remaining plan](docs/implementation-plan.md). Private deployment was separately authorized; it does not waive the provider/score launch gates or authorize public release.

## Try the research extension

In Chrome, open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select `extension/`. No build is needed. Click the toolbar icon for the control panel, then the cogwheel to enter your server origin/token. Scanning starts off; Load/Unload affect the shared server, while scanning is client-local.

The separately authorized private service is now **`https://slop-detection.dimensionlab.net`**, available through private DNS/LAN/Tailscale routing and protected authentication. Follow the [private connection/token instructions](docs/private-deployment.md#connect-the-extension). It is left paused/unloaded; press Load to resume. The extension does not automatically configure itself or install into your normal browser. Do not expect percentages before a profile has been fitted and validated.

## Intended experience

- Automatically evaluate a post's own text as it appears in the feed.
- Show a discreet percentage in the top-right header, without extra badges, panels, or automatic hiding.
- Run a dedicated text detector on local CPU or through an API.
- Provide a configuration screen for the chosen detector and its connection settings.
- Keep quoted posts separate from the author's own text.

The score concerns estimated AI authorship, not whether a post is useful, truthful, or worth reading.

## Detector requirements

No Jev, general-purpose LLM judging, or hand-written style heuristics presented as authorship probabilities. Detector selection must consider short X posts, false positives, supported input lengths, and what the returned score actually means. A statistical detector and a provider watermark checker are different kinds of evidence.

No detector's short-post accuracy is validated for this project yet. An API accepting a short string is not evidence that its predictions work on short posts. Missing or unsupported results must not be presented as 0% AI.

## What we can use today

Implemented/tested scope, **1 November 2026**:

| Path | Available now | Boundary |
| --- | --- | --- |
| Local v2 evidence | Three classifiers + one Neo statistical method, 3060 or explicit CPU | Real inference and full-suite loading/unloading work. Native outputs are not a combined probability. |
| Legacy v1 diagnostics | Tabularis output projected from the same suite | No second model owner; legacy percentage remains uncalibrated, not the approved target probability. |
| Local watermark route | Conditional KGW CPU verification, standalone endpoint or optional full-analysis check | Exact matching configuration only; demo material explicitly research-only. Not arbitrary commercial-model verification. |
| Provider watermark routes | Explicit access/configuration/approval/blocker registry | Disabled, not connected; no adapter, granted access, or free/unlimited entitlement established. |
| Aggregate probability | Explicit no-estimate result; offline pilot profiles fitted and evaluated separately | No production-approved profile. Pilot did not establish ensemble benefit; no invented averaging or missing-check zeros. |
| Chrome client | Own-post extraction, header `—`, compact toolbar panel, cogwheel configuration, background-only connection, shared controls | Actual Chrome → private HTTPS → real 3060 has passed with synthetic X-shaped pages. Live X/manual permission-prompt checks remain. |
| Private HTTPS service | Authenticated, source-restricted Caddy endpoint and enabled non-root GPU service | Operational research deployment, not a validated detector release or public inference service. |

The roster is approved for validation, not proven to improve accuracy. See [suite assessment](docs/detector-suite-assessment.md) and [evaluation approach](docs/evaluation.md).

Earlier commercial/browser recommendations remain historical research in the [initial comparison](docs/detector-research.md) and [expanded shortlist](docs/open-source-detectors.md); they do not override the selected server-side roster.

## Documentation

- [Multi-detector runtime, model residency, and GPU validation](docs/suite-runtime.md)
- [Chrome extension: install, security, and browser evidence](docs/extension.md)
- [Private HTTPS service: connection, deployment evidence, and rollback](docs/private-deployment.md)
- [Offline combined scoring: implemented pipeline and release boundaries](docs/scoring.md)
- [First real scoring pilot: measured results and unsuccessful release gates](docs/scoring-pilot-results.md)
- [V2 API and evidence contract](docs/v2-api.md)
- [Documentation index](docs/README.md)
- [Product requirements](docs/product-requirements.md)
- [Detector comparison and recommendation](docs/detector-research.md)
- [Short-post evaluation](docs/evaluation.md)

The earlier deployment baseline had **69 Python tests passed on Linux**; locally 65 passed and four optional inference tests were skipped. The new [offline-scoring/benchmark checks](docs/scoring.md#verification-boundary) discovered 108 tests locally: 104 passed / four skipped with evaluation dependencies, and 97 passed / eleven skipped in the lightweight environment. These new tests were not run on the Linux GPU host. Real HTTP checks covered the CPU watermark route, marked/unmarked-AI/wrong-key fixtures, and full-suite integration without turning a watermark positive into a probability. The prior 3060 lifecycle study verified lazy/manual/idle controls, cancellation, and restart pause; its 16-post near-limit batch took about **3.95 s**, with **7142 MiB** process VRAM sampled afterward. Release returned allocator counters to zero, leaving **140 MiB** overhead until exit.

The temporary GPU probes were stopped. A separately authorized [persistent private service](docs/private-deployment.md) is now enabled, paused and unloaded; after its final restart the 3060 was **15 MiB**. During deployment the 3090's existing ComfyUI workload changed, reaching **18041 MiB** aggregate; the detector was observed only on the 3060. Earlier [runtime measurements](docs/suite-runtime.md#recorded-validation) and [standalone probes](docs/feasibility-checks.md) remain separate historical evidence, not accuracy or sustained-load claims.

The extension adds **30 passing Node tests**, a real **Google Chrome 156** synthetic-adapter smoke, and a subsequent [real private-HTTPS/3060 browser smoke](docs/private-deployment.md#actual-runtime-and-browser). These verify client boundaries and actual transport/inference separately. No live X, native permission-prompt acceptance, hosted verifier, or calibrated accuracy result is claimed. Disposable Chrome processes were stopped; only the authorized private service remains running.

## License

[MIT](LICENSE). Detector models, datasets, and hosted services have their own licenses and terms.
