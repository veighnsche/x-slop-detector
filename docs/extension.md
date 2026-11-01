# Thin Chrome extension — research client

**Implemented after explicit phase-4 approval:** an unpacked Manifest V3 extension, not a static mockup. It uses the current v2 contract and server-owned suite. **It cannot show calibrated percentages:** every accepted aggregate is an explained `—`. No v1 fallback, fake percentages, client-side model inference, fusion, or hosted-verifier activation exists.

**Deployment update:** the user subsequently approved the [private HTTPS research service](private-deployment.md). Actual Chrome → private HTTPS → real 3060 has now passed with synthetic text/pages; the older phase-4 evidence below remains separately labeled. Live X and interactive native permission-prompt checks are still open.

## Install and connect

1. Open `chrome://extensions` in **Chrome**, enable Developer mode, select **Load unpacked**, and choose this repository's `extension/` directory. No build or Node dependencies are needed to run it.
2. Pin the extension. Clicking its toolbar icon opens the compact control panel; the cogwheel opens Configuration in the same popup. Cancel, ×, or Escape returns to the panel, discarding the unsaved token and draft fields. Closing the popup also discards drafts.
3. Enter the **origin** of your analysis server: `https://your-host:port`, without a path, query, user info, or fragment. The only HTTP exceptions are loopback `localhost`, `127.0.0.1`, and `[::1]` for development/tunneling. Do not paste a token in the URL.
4. Enter the API token in the masked field. **Test draft connection** requests Chrome's optional permission for that server and checks v2 capabilities/status without saving or loading models. Save can also save an offline connection; the panel then reports its real connection/authentication error.
5. Turn on **Scan visible posts** when ready to submit visible own-post text. It starts **off** on a new install. A blank token field preserves the stored token only when the server origin is unchanged; changing the origin requires a new token.
6. **Load** prewarms/resumes the shared suite. **Unload** latches shared server pause, then releases models after already-owned work finishes. Status polling shows pending operations. Unload remains available during loading/analysis; Load waits for the pending transition. Client scanning preference is independent and unchanged by either button.

The extension is **not** installed into your normal browser automatically. The separately approved private endpoint is `https://slop-detection.dimensionlab.net`; follow its [private token and routing instructions](private-deployment.md#connect-the-extension). No credential is preconfigured in extension source. Other remote connections need trusted HTTPS or an agreed secure private transport; never expose an unauthenticated/public HTTP inference port.

## Dialogs and ownership

The panel shows connection/auth/offline state, shared model readiness/manual pause, pending operations, server idle countdown, one-click controls, local scanning preference, and collapsible latest native diagnostics. “Models ready” is explicitly **diagnostics only**, never probability readiness.

Configuration uses small collapsible sections rather than a dashboard:

| Section | Displayed state |
| --- | --- |
| Connection | Client-local server origin, masked replacement token, non-saving draft test, Save/Cancel, grant/revoke access. |
| Profile and limits | Configuration identity, target and lack of a validated scope/profile, device/verified GPU, blockers, server idle policy. |
| Components | Selected checker inventory, required/optional status, individual residency/failure state. |
| Local watermark | CPU route scope, research-vs-known configuration, public key alias, enabled/configured state, sparse-input floor and blocker. No secret keys are returned. |
| Provider policy | Access, application submitted, configuration, support, approval, terms, free/unlimited verification, disabled/connected state, and every blocker. These are operator records, not functional client toggles or API connections. |
| Privacy | Exact analysis destination, local memory/storage behavior, server ownership, and optional permission revocation. |

Idle policy, checker selection, watermark configuration/keys, provider credentials/approvals, and calibration are **read-only server-owned** settings. There are no probability-weight sliders or client “enable provider” requests. Hosted routes remain disabled by the current contract; the extension rejects a response claiming otherwise.

## Extraction and feed behavior

- Top-level `article[data-testid="tweet"]` elements only, with exactly one unquoted own-text container and an identifiable menu control.
- Do not concatenate quote cards, nested tweets, author names, replies, biographies, media, or surrounding posts. Inline quoted cards are excluded; a quoted post can be analyzed if it later appears as its own top-level post.
- Preserve Unicode, text-node whitespace, explicit line breaks/block boundaries, and emoji image alt text; do not trim, normalize, translate, pad, or truncate evidence.
- Empty/media-only posts, ambiguous text markup, or missing/unsafe header anchors receive **no misplaced badge and no submission**. A post above 10,000 Unicode code points has an explained client limit; the server enforces its own per-check token caps without truncation.
- Put one discreet `—` before the Grok/menu group (or before menu when no Grok exists). Its tooltip/accessibility label explains no estimate, missing evidence, pause, busy, offline, or another failure. No hiding, fading of the post, bot/account scoring, or extra feed diagnostics.
- Tie async placement to exact text **and** the current DOM anchor. Edited/recycled/unmounted/offscreen nodes cannot receive an old response. DOM mutations, scrolling, navigation changes and periodic reconciliation discover changes. Hidden tabs do not start new scans.

**X markup is not a stable API.** Conservative fixtures are implemented; real authenticated X behavior, all layouts/locales/long-post expansion, visual placement beside current Grok controls, and live navigation still need manual validation. The browser smoke below intercepts a synthetic `https://x.com/__xsd_fixture__` page before network; it is **not** a live X test.

## Request, cache, and privacy boundaries

- Only the MV3 worker contacts the chosen server. There is no page `postMessage` bridge, externally-connectable API, page-selected endpoint, or content-script Load/Unload authority.
- Validate extension identity, exact popup resource, top-level X/Twitter content sender, action allowlist and message keys. Privileged messages from content scripts, other extensions, frames, or unrelated origins are denied.
- Local storage access is restricted with `TRUSTED_CONTEXTS` **before reading credentials**. The token is not sent to content scripts, placed in X DOM, returned by settings reads, logged, or stored in Chrome sync. It is transmitted as a Bearer header to the selected server. The masked field never reads the stored token back; it accepts replacements only.
- Mandatory capabilities are storage plus X/Twitter content-script matching. Optional server permission is requested for the chosen scheme/hostname, not every HTTPS site. **Chrome host grants cover all ports on that hostname**, even when the saved origin specifies one port. Revocation blocks new network requests and cache returns. Unused draft/previous-host grants can also be removed in Chrome settings.
- HTTPS is required off loopback. Fetch omits cookies, cache and referrer, rejects redirects, times out after 15 seconds for metadata/controls or 120 seconds for analysis, and caps responses at 1 MiB. Server errors are mapped to fixed codes, never echoed response text.
- Negotiate schema 2 and validate status, native evidence, checker/configuration/revision, exact character coverage, extraction version and aggregate. Unexpected probability, legacy percentage, truncated/malformed/mismatched output, non-finite numbers or active hosted routes are rejected.
- One one-post inference request is active in the worker; identical in-flight text joins that request, competing work gets bounded busy guidance. No durable/background job queue. Each tab holds at most **24 visible records**, admits **12 at a time**, and processes them serially. Busy retries have 2/4/8-second backoff, at most **four attempts**; exhausted/auth/timeout/OOM failures do not loop automatically for the same mounted record. Toggle scanning off/on to retry deliberately.
- Exact-text result reuse is keyed by server origin, suite configuration identity, extraction version and target. Background memory has **128 entries**, a **five-minute reuse TTL**, and LRU eviction; expired entries are pruned on cache use/status/preferences. No texts/results are written to persistent extension storage. Worker suspension/restart can discard all cache. Native latest-result diagnostics retain no post text.
- Connection/scan changes, controls, observed server pause/configuration changes, permission loss, and failed metadata invalidate acceptance/cache appropriately. Content state polls every five seconds while visible; the worker refreshes scanning metadata at most every ten seconds under healthy operation. Another client's pause may take that long to appear; the server remains the final admission authority. Popup polling never refreshes model residency.

Disabling scanning stops **new** submissions; it cannot recall a request already owned by the server. Saved tokens are not OS-keychain encrypted by this client; Chrome profile/extension developer access remains privileged. The selected server operator governs server-side retention/logging; client code cannot guarantee a remote operator's behavior. No telemetry or third-party resources are included.

## Reproduce validation

The shipped extension has **no runtime npm dependencies or build step**. Node dependencies are dev/test-only and pinned by `package-lock.json`.

```sh
npm ci --ignore-scripts
node --test tests/extension/*.test.cjs
.venv/bin/python -m unittest discover -s tests -v
node scripts/smoke_extension.cjs
```

The browser smoke requires the Python web/test environment and an installed **Google Chrome**, not a substituted Chromium/WebKit browser. macOS defaults to `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`; Linux defaults to `/usr/bin/google-chrome`. Set `CHROME_PATH` and/or `PYTHON` when necessary. It launches a disposable profile below `$DELTA_SCRATCH_DIR` or ignored `.cache/`, not your normal Chrome profile, and a loopback-only test server with an ephemeral test token. Both processes stop in cleanup.

### Recorded evidence

- **30 Node tests pass**: protocol/version rejection, native domains/no-number, permissions, sender/secret boundaries, exact-text/configuration cache and invalidation, in-flight ownership, concurrent settings, retry/record limits, quote/nested exclusion, Unicode/multiline, media/ambiguous/missing anchors, and edit/recycle behavior.
- Current Python baseline after deployment guardrails/cold-import regression: **69 run, 65 pass and four optional inference tests skip locally; all 69 pass on Linux**. Earlier phase-4 and Linux/3060 results remain separately recorded.
- **Google Chrome 156.0.8078.74 on macOS**, headless new mode, real unpacked MV3, actual action popup via `chrome.action.openPopup()`, actual FastAPI/LocalSuite with **synthetic adapters**, not real inference. Passed cogwheel/focus/Escape, draft-test-without-save, permission API/revocation, content-world storage denial, privileged-content rejection, synthetic own/quote separation and edit rescan, diagnostics/no-number, a second API client's shared pause, Load/Unload, authentication and offline failure. No page errors.
- Chrome's native permission prompt is outside the page automation DOM. The smoke pregrants **only loopback** through Chrome's own settings in its disposable profile, then calls the real extension permission API. **Interactive accept/deny of that native prompt was not validated.** No permission API is mocked in the running extension.
- No live X data, hosted verifier, remote GPU inference, accuracy benchmark, calibrated score, normal-profile installation, store publication, or deployment was performed **in the original phase-4 smoke**. The subsequent [private deployment](private-deployment.md#actual-runtime-and-browser) separately exercised real GPU inference through Chrome; it does not supply live-X or accuracy evidence.

### Remaining manual checks

Use the user's agreed live-testing workflow, hosted routes disabled:

1. Load unpacked into normal Chrome **only when you choose to**, then verify clicking the real toolbar icon, keyboard tab/focus order, Escape/Cancel, scrolling long configuration sections, and light/dark X placement.
2. Accept and deny the real chosen-host permission prompt; revoke and reconnect; confirm HTTPS certificate/offline/auth errors. Test draft edits never silently replace the saved connection.
3. On live X, compare own/quoted/nested/media/emoji/multiline/long-expanded posts, edited/recycled virtualized rows, scrolling and SPA navigation. Check no ambiguous markup attaches a result to another post.
4. Against the intended server, verify another client’s pause, loading/analysis superseded by Unload, idle expiry/reload, disconnection and bounded busy retries. This is later end-to-end evidence, not supplied by synthetic adapters.

Provider access and calibrated score/coverage remain independent release gates. This is an implemented research client, **not the completed accurate-detector product**.
