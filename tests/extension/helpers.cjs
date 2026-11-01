const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {parseHTML} = require("linkedom");
const root = path.resolve(__dirname, "../..");
const TOKEN = "public-synthetic-test-token-only";
const copy = value => JSON.parse(JSON.stringify(value));
function load(window = {}) {
  const context = vm.createContext(window);
  Object.assign(context, {URL, TextDecoder, TextEncoder, AbortSignal, Response,
    fetch, setTimeout, clearTimeout, console});
  for (const file of ["shared.js", "background-core.js", "extraction.js"]) {
    vm.runInContext(fs.readFileSync(path.join(root, "extension", file), "utf8"), context);
  }
  return context;
}
const kinds = ["classifier", "statistical", "watermark"];
const specs = kinds.map((kind, index) => ({
  checker: {id: `checker${index}`, configuration_id: `config${index}`, artifact_revision: "fixture-revision"},
  kind, artifact_id: "fixture-not-model", precision: "float32", max_tokens: 512,
  preprocessing: "raw_text"
}));
function status() {
  return {schema_version: "2", calibration_status: "not_configured", diagnostics_ready: true,
    probability_ready: false, blockers: ["no_validated_profile"], suite: {
      configuration_id: "fixture-suite-v1", integrated: true, paused: false, pause_persisted: true,
      busy: false, operation: "idle", pending_control: null, last_error: null,
      configured_device: "cpu", verified_gpu_uuid: null, device_memory: null,
      idle_timeout_seconds: 600, unload_in_seconds: 590,
      components: specs.map(s => ({checker_id: s.checker.id, required: s.kind !== "watermark", state: "ready"})),
      local_watermark_routes: [], provider_routes: [
        {id: "openai", access: "pending", state: "access_pending", support: "unconfirmed",
          application_submitted: false, configured: false, approved: false, terms_approved: false,
          free_unlimited_verified: false, enabled: false, connected: false, adapter_implemented: false,
          blockers: ["adapter_not_integrated", "access_pending"]}
      ]
    }};
}
const capabilities = () => ({schema_version: "2", supported_schema_versions: ["2"], checkers: copy(specs),
  limits: {hosted_requests_enabled: false, max_posts: 16, max_body_bytes: 128000, max_text_characters: 10000}});
function analysis(text) {
  return {schema_version: "2", configuration_id: "fixture-suite-v1", extraction_version: "own-post-text-v1",
    calibration_status: "not_configured", results: [{
      id: "post", aggregate: {kind: "no_estimate", target_id: "substantive_llm_wording_v1", reason: "no_validated_profile"},
      checks: specs.map((s, i) => ({
        checker: copy(s.checker), coverage: {characters: [...text].length, input_tokens: 3,
          scored_tokens: null, token_limit: 512, truncated: false}, status: "completed", reason: null,
        output: i === 0 ? {kind: "classifier_ai_score", value: 0.8, ai_label_index: 1} :
          i === 1 ? {kind: "token_probability_discrepancy", value: -3.1} :
            {kind: "watermark_detection", decision: "not_detected", verification_scope: "known_configuration",
              z_score: -0.3, p_value: null, tests_performed: 1, configuration_purpose: "research_fixture"}
      }))
    }]};
}
const ui = {id: "fixture-extension", url: "chrome-extension://fixture-extension/popup.html"};
const content = {id: "fixture-extension", url: "https://x.com/home", frameId: 0, tab: {id: 42}};
function browser(connection = {server: "http://127.0.0.1:8123", token: TOKEN, scan: true}) {
  const data = {connection: copy(connection)}, writes = [];
  let grant = true, access;
  return {
    data, writes, set grant(v) { grant = v; }, get access() { return access; },
    runtime: {id: "fixture-extension", getURL: p => `chrome-extension://fixture-extension/${p}`},
    permissions: {contains: async () => grant},
    storage: {local: {
      setAccessLevel: async v => { access = v; },
      get: async () => copy(data),
      set: async v => { writes.push(copy(v)); Object.assign(data, copy(v)); }
    }}
  };
}
function transport() {
  const calls = [];
  let state = status(), catalog = capabilities(), responder;
  const fetcher = async (url, options) => {
    calls.push({url, options});
    if (responder) { const response = await responder(url, options); if (response) return response; }
    const p = new URL(url).pathname;
    return Response.json(p.endsWith("capabilities") ? catalog : p.endsWith("status") ? state :
      p.endsWith("control") ? {schema_version: "2", action: JSON.parse(options.body).action,
        disposition: "completed", status: state} : analysis(JSON.parse(options.body).posts[0].text));
  };
  return {calls, fetcher, get state() { return state; }, set state(v) { state = v; },
    get catalog() { return catalog; }, set responder(v) { responder = v; }};
}
function dom(html) {
  const {window} = parseHTML(`<html><body>${html}</body></html>`);
  // Do not contextify linkedom's Window proxy: its global fallbacks can mutate
  // Node's own timers when a fixture replaces window.setTimeout.
  return load({
    document: window.document, HTMLElement: window.HTMLElement,
    MutationObserver: window.MutationObserver, Event: window.Event,
    addEventListener: window.addEventListener.bind(window),
    removeEventListener: window.removeEventListener.bind(window),
    dispatchEvent: window.dispatchEvent.bind(window)
  });
}
function tweet(text, extra = "") {
  return `<article data-testid="tweet"><div><div data-testid="tweetText">${text}</div></div>
    ${extra}<div class="controls"><button data-testid="grok" aria-label="Ask Grok">G</button><button data-testid="caret">…</button></div></article>`;
}
module.exports = {root, TOKEN, copy, load, status, capabilities, analysis, ui, content, browser, transport, dom, tweet};
