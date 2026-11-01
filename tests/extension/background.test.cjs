const test = require("node:test");
const assert = require("node:assert/strict");
const {load, TOKEN, browser, transport, ui, content} = require("./helpers.cjs");
async function setup() {
  let now = 0;
  const X = load().XSD, b = browser(), t = transport(), broker = new X.Broker(b, t.fetcher, () => now);
  await broker.init();
  return {broker, b, t, advance: n => { now += n; }};
}
test("credential is local, restricted and never in content responses", async () => {
  const {broker, b, t} = await setup();
  assert.equal(b.access.accessLevel, "TRUSTED_CONTEXTS");
  const prefs = await broker.dispatch({type: "preferences"}, content);
  const result = await broker.dispatch({type: "scan", text: "public test text"}, content);
  assert.equal(JSON.stringify([prefs, result, broker.publicSettings()]).includes(TOKEN), false);
  assert.equal(t.calls.every(c => c.options.credentials === "omit" && c.options.redirect === "error"), true);
  assert.equal(b.writes.length, 0); // no posts or results persisted
  assert.equal(t.calls.at(-1).options.headers.Authorization, `Bearer ${TOKEN}`);
  assert.deepEqual(Object.keys(JSON.parse(t.calls.at(-1).options.body)).sort(),
    ["extraction_version", "posts", "schema_version"]);
});
test("sender validation rejects pages, iframes, other extensions and privileged content commands", async () => {
  const {broker, t} = await setup();
  for (const sender of [{}, {...content, id: "other"}, {...content, frameId: 1},
    {...content, url: "https://x.com.evil.example"}, {...ui, url: ui.url + "?spoof"},
    {...content, url: "http://x.com/home"}]) {
    await assert.rejects(broker.dispatch({type: "preferences"}, sender), /forbidden/);
  }
  for (const type of ["control", "settings", "save", "test", "scanPreference", "diagnostics"]) {
    await assert.rejects(broker.dispatch({type, action: "unload"}, content), /forbidden/);
  }
  await assert.rejects(broker.dispatch({type: "scan", text: "test", server: "https://evil.example"}, content), /forbidden/);
  assert.equal(t.calls.length, 0);
});
test("missing host permission blocks network, including cached requests", async () => {
  const {broker, b, t} = await setup();
  await broker.scan("cached synthetic text");
  const count = t.calls.length;
  b.grant = false;
  await assert.rejects(broker.refresh(), /permission_missing/);
  await assert.rejects(broker.scan("cached synthetic text"), /permission_missing/);
  assert.equal(t.calls.length, count);
});
test("fetch transport never receives the Broker as its WebIDL receiver", async () => {
  const X = load().XSD, b = browser(), t = transport();
  const broker = new X.Broker(b, function (url, options) {
    "use strict";
    assert.equal(this, undefined);
    return t.fetcher(url, options);
  });
  await broker.init(); await broker.refresh();
});
test("cache deduplication and configuration changes invalidate exact-text results", async () => {
  const {broker, t, advance} = await setup();
  await broker.scan("one public text");
  await broker.scan("one public text");
  await broker.scan("one public text!");
  assert.equal(t.calls.filter(c => c.url.endsWith("/analyze")).length, 2);
  t.state.suite.configuration_id = "fixture-suite-v2";
  advance(10001); await broker.refresh();
  assert.equal(broker.cache.items.size, 0); assert.equal(broker.latest, null);
});
test("one in-flight request deduplicates same text and rejects other text without queueing", async () => {
  const {broker, t} = await setup();
  await broker.refresh();
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  t.responder = async url => { if (url.endsWith("/analyze")) await gate; };
  const first = broker.scan("same text"), second = broker.scan("same text");
  await assert.rejects(broker.scan("other text"), /busy/);
  release();
  assert.deepEqual(await first, await second);
  assert.equal(t.calls.filter(c => c.url.endsWith("/analyze")).length, 1);
});
test("manual pause from another client prevents cached results and new work", async () => {
  const {broker, t, advance} = await setup();
  await broker.scan("public text");
  t.state.suite.paused = true; advance(10001);
  await assert.rejects(broker.scan("public text"), /manually_paused/);
  assert.equal(broker.cache.items.size, 0);
  assert.equal(t.calls.filter(c => c.url.endsWith("/analyze")).length, 1);
});
test("scan off during inference discards response and never logs or persists text", async () => {
  const {broker, t, b} = await setup();
  await broker.refresh();
  let release, entered;
  const gate = new Promise(r => { release = r; });
  const started = new Promise(r => { entered = r; });
  t.responder = async url => { if (url.endsWith("/analyze")) { entered(); await gate; } };
  const result = broker.scan("private-like synthetic post");
  await started;
  await broker.dispatch({type: "scanPreference", enabled: false}, ui);
  release(); await assert.rejects(result, /settings_changed/);
  assert.equal(JSON.stringify(b.writes).includes("private-like"), false);
  assert.equal(broker.latest, null);
});
test("busy alone retries, auth and timeout never become human results", async () => {
  const {broker, t} = await setup();
  await broker.refresh();
  for (const [code, http, retryable] of [["busy", 409, true], ["unauthorized", 401, false]]) {
    t.responder = async () => Response.json({schema_version: "2", error: {code, retryable}}, {status: http});
    await assert.rejects(broker.scan("text"), e => e.code === code && e.retryable === retryable);
  }
  t.responder = async () => { throw new DOMException("synthetic", "TimeoutError"); };
  await assert.rejects(broker.scan("text"), e => e.code === "timeout" && !e.retryable);
  assert.equal(broker.cache.items.size, 0);
});
test("draft testing is non-saving; blank token retains only the same origin", async () => {
  const {broker, b} = await setup();
  await broker.dispatch({type: "test", server: b.data.connection.server, token: ""}, ui);
  assert.equal(b.writes.length, 0);
  await assert.rejects(broker.dispatch({type: "save", server: "https://different.example", token: ""}, ui), /invalid_token/);
  const result = await broker.dispatch({type: "save", server: b.data.connection.server, token: ""}, ui);
  assert.equal(result.hasToken, true); assert.equal("token" in result, false);
});
test("malformed, oversized, redirected or legacy responses are rejected", async () => {
  const {broker, t} = await setup();
  await broker.refresh();
  for (const response of [
    Response.json({ai_percentage: 99}), new Response("not json"),
    new Response(" ".repeat(1048577))
  ]) {
    t.responder = async () => response;
    await assert.rejects(broker.scan("text"), /incompatible_response/);
  }
  t.responder = async () => { throw new TypeError("redirect rejected"); };
  await assert.rejects(broker.scan("text"), /offline/);
});
test("Load and Unload are only v2 controls, status polls do not issue controls", async () => {
  const {broker, t} = await setup();
  await broker.refresh(); await broker.refresh();
  assert.equal(t.calls.some(c => c.url.endsWith("/control")), false);
  await broker.dispatch({type: "control", action: "unload"}, ui);
  const call = t.calls.at(-1);
  assert.equal(new URL(call.url).pathname, "/v2/control");
  assert.deepEqual(JSON.parse(call.options.body), {schema_version: "2", action: "unload"});
});
test("concurrent settings mutations serialize, preserving both new origin and scan preference", async () => {
  const {broker, b} = await setup();
  await Promise.all([
    broker.dispatch({type: "save", server: "https://new.example", token: TOKEN}, ui),
    broker.dispatch({type: "scanPreference", enabled: false}, ui)
  ]);
  assert.equal(broker.settings.server, "https://new.example");
  assert.equal(broker.settings.scan, false);
  assert.equal(b.data.connection.server, "https://new.example");
  assert.equal(b.data.connection.scan, false);
});
test("Unload invalidates already-owned analysis before its control acknowledgement", async () => {
  const {broker, t} = await setup();
  await broker.refresh();
  let release, entered;
  const gate = new Promise(r => { release = r; });
  const started = new Promise(r => { entered = r; });
  t.responder = async url => { if (url.endsWith("/analyze")) { entered(); await gate; } };
  const result = broker.scan("synthetic public post");
  await started;
  await broker.dispatch({type: "control", action: "unload"}, ui);
  release(); await assert.rejects(result, /settings_changed/);
  assert.equal(broker.latest, null);
});
test("failed status invalidates old cache and discards an owned result safely", async () => {
  const {broker, t} = await setup();
  await broker.scan("previous cached text");
  let release, entered;
  const gate = new Promise(r => { release = r; });
  const started = new Promise(r => { entered = r; });
  t.responder = async url => {
    if (url.endsWith("/analyze")) { entered(); await gate; return; }
    throw TypeError("synthetic disconnect");
  };
  const result = broker.scan("new owned text");
  await started;
  await assert.rejects(broker.refresh(), /offline/);
  assert.equal(broker.cache.items.size, 0);
  assert.equal(broker.snapshot, null);
  release(); await assert.rejects(result, /settings_changed/);
});
