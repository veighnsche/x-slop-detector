const test = require("node:test");
const assert = require("node:assert/strict");
const {load, status, capabilities, analysis, copy} = require("./helpers.cjs");
const X = load().XSD;
test("connection accepts HTTPS origins and loopback HTTP only", () => {
  for (const input of ["http://remote.example", "https://user:pass@example.org", "https://x.org/path",
    "https://x.org/?query", "javascript:alert(1)", "https://x.org/#fragment"]) {
    assert.throws(() => X.serverURL(input), /invalid_server/);
  }
  assert.equal(X.serverURL("https://example.org:8443/"), "https://example.org:8443");
  assert.equal(X.permission("http://[::1]:8123"), "http://[::1]/*");
  assert.equal(X.serverURL("http://127.0.0.1:8123"), "http://127.0.0.1:8123");
});
test("input preserves Unicode and bounds code points, not JS UTF-16 length", () => {
  assert.equal(X.textOK("😀".repeat(10000)), true);
  assert.equal(X.textOK("😀".repeat(10001)), false);
  assert.equal(X.textOK(" \n "), false);
});
test("v2 negotiation and status reject unvalidated numbers or connected providers", () => {
  X.capabilities(capabilities()); X.status(status());
  const bad = [copy(status()), copy(status()), copy(status()), copy(status())];
  bad[0].schema_version = 2;
  bad[1].probability_ready = true;
  bad[2].suite.provider_routes[0].enabled = true;
  bad[3].suite.components.push(bad[3].suite.components[0]);
  for (const s of bad) assert.throws(() => X.status(s), /incompatible_response/);
  const c = capabilities(); c.supported_schema_versions = ["1"];
  assert.throws(() => X.capabilities(c), /incompatible_response/);
});
test("native evidence stays native; aggregate numbers never admitted in phase 4", () => {
  const good = analysis("Emoji 😀\ntext");
  const validate = a => X.analysis(a, "Emoji 😀\ntext", status(), capabilities());
  assert.equal(validate(good).checks[1].output.value, -3.1);
  for (const mutate of [
    a => a.configuration_id = "other",
    a => a.extraction_version = "normalized",
    a => a.results[0].id = "other",
    a => a.results[0].aggregate = {kind: "probability", probability: .99},
    a => a.results[0].checks[0].coverage.characters++,
    a => a.results[0].checks[0].checker.artifact_revision = "other",
    a => a.results[0].checks[0].output.value = Infinity,
    a => a.results[0].checks[0].coverage.truncated = true,
    a => a.results[0].checks[0].output.value = 1.01,
    a => a.results[0].checks[0].status = "unsupported",
    a => a.results[0].checks[1] = a.results[0].checks[0],
    a => a.results[0].checks[2].output.p_value = -1
  ]) {
    const bad = copy(good); mutate(bad);
    assert.throws(() => validate(bad), /incompatible_response/);
  }
});
test("unsuccessful check has no output, never zero", () => {
  const a = analysis("some text");
  Object.assign(a.results[0].checks[0], {status: "unsupported", output: null, reason: "token_limit_exceeded"});
  X.analysis(a, "some text", status(), capabilities());
  a.results[0].checks[0].output = {kind: "classifier_ai_score", value: 0, ai_label_index: 1};
  assert.throws(() => X.analysis(a, "some text", status(), capabilities()), /incompatible_response/);
});
test("bounded LRU cache expires and configuration/extraction keys remain separate", () => {
  let time = 0;
  const c = new X.Cache(2, 10, () => time);
  c.set("text:configA:extractA", 1); c.set("text:configB:extractA", 2);
  c.get("text:configA:extractA"); c.set("text:configB:extractB", 3);
  assert.equal(c.get("text:configB:extractA"), undefined);
  time = 10; assert.equal(c.get("text:configA:extractA"), undefined);
  c.clear(); assert.equal(c.items.size, 0);
});
