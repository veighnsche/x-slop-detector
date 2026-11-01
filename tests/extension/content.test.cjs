const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {root, dom, tweet, analysis} = require("./helpers.cjs");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn) {
  for (let i = 0; i < 300; i++) { if (fn()) return; await delay(5); }
  throw Error("Content fixture did not settle");
}
function controller(markup, handler) {
  const c = dom(markup), sent = [];
  c.innerHeight = 800;
  Object.defineProperty(c.document, "hidden", {value: false, configurable: true});
  c.HTMLElement.prototype.getBoundingClientRect = () => ({width: 600, height: 150, top: 0, bottom: 150});
  c.setTimeout = (fn, ms) => setTimeout(fn, ms >= 2000 ? 0 : 5);
  c.clearTimeout = clearTimeout;
  c.setInterval = () => 0; c.clearInterval = () => {};
  c.chrome = {runtime: {sendMessage: async m => {
    if (m.type === "preferences") return {ok: true, data: {scan: true, reason: null, configuration: "fixture-suite-v1"}};
    sent.push(m);
    return handler(m, sent);
  }}};
  vm.runInContext(fs.readFileSync(path.join(root, "extension/content.js"), "utf8"), c);
  return {c, sent, stop: () => c.dispatchEvent(new c.Event("pagehide"))};
}
const success = text => ({ok: true, data: {configuration: "fixture-suite-v1", result: analysis(text).results[0]}});
test("content retry budget is four attempts, then stops without a request feedback loop", async () => {
  const t = controller(tweet("public synthetic text"), async () => ({
    ok: false, error: {code: "busy", retryable: true}
  }));
  try {
    await until(() => t.sent.length === 4);
    await delay(60);
    assert.equal(t.sent.length, 4);
    assert.match(t.c.document.querySelector("[data-xsd-result]").title, /Bounded retries/);
  } finally { t.stop(); }
});
test("edited/recycled node rejects an old in-flight result and rescans exact new text", async () => {
  let release;
  const gate = new Promise(r => { release = r; });
  const t = controller(tweet("old own text", '<div role="link"><div data-testid="tweetText">excluded quote</div></div>'),
    async (m, sent) => {
      if (sent.length === 1) await gate;
      const response = success(m.text);
      if (m.text === "new own text") response.data.result.aggregate.reason = "required_evidence_missing";
      return response;
    });
  try {
    await until(() => t.sent.length === 1);
    t.c.document.querySelector('[data-testid="tweetText"]').textContent = "new own text";
    release();
    await until(() => t.sent.length === 2 &&
      t.c.document.querySelector("[data-xsd-result]")?.title.includes("Required evidence"));
    assert.deepEqual(t.sent.map(m => m.text), ["old own text", "new own text"]);
    assert.equal(t.c.document.querySelectorAll("[data-xsd-result]").length, 1);
    assert.equal(t.c.document.querySelector("[data-xsd-result]").textContent, "—");
  } finally { release(); t.stop(); }
});
test("visible work is bounded to 24 records and processed sequentially", async () => {
  let active = 0, peak = 0;
  const t = controller(Array.from({length: 30}, (_, i) => tweet(`public post ${i}`)).join(""),
    async m => { peak = Math.max(peak, ++active); await delay(1); active--; return success(m.text); });
  try {
    await until(() => t.sent.length === 24 && active === 0);
    assert.equal(peak, 1);
    assert.equal(t.c.document.querySelectorAll("[data-xsd-result]").length, 24);
    await delay(30); assert.equal(t.sent.length, 24);
  } finally { t.stop(); }
});
test("media-only/missing-header posts produce no submissions or misplaced readouts", async () => {
  const t = controller(tweet("") +
    '<article data-testid="tweet"><div data-testid="tweetText">no header anchor</div></article>',
  async m => success(m.text));
  try {
    await delay(40);
    assert.equal(t.sent.length, 0);
    assert.equal(t.c.document.querySelectorAll("[data-xsd-result]").length, 0);
  } finally { t.stop(); }
});
