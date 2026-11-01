/* Opt-in: actual Chrome -> private HTTPS -> real 3060, synthetic page/text only.
 * Requires a quiet paused deployment. Credential stays in memory and a private
 * disposable Chrome profile under DELTA_SCRATCH_DIR, never the normal profile.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {execFileSync} = require("node:child_process");
const puppeteer = require("puppeteer-core");
const origin = "https://slop-detection.dimensionlab.net";
const root = path.resolve(__dirname, "..");
const scratch = process.env.DELTA_SCRATCH_DIR;
if (!scratch) throw Error("DELTA_SCRATCH_DIR is required for the private disposable profile");
const profile = fs.mkdtempSync(path.join(scratch, "chrome-deployed-"));
fs.chmodSync(profile, 0o700);
const token = execFileSync("ssh", ["-o", "BatchMode=yes", "gpu", "sudo", "-n", "cat",
  "/etc/x-slop-detector/api-token"], {encoding: "utf8", stdio: ["ignore", "pipe", "pipe"]}).trim();
let browser, worker, extensionId, ownsLoad = false;
async function api(pathname, body) {
  const r = await fetch(origin + pathname, {
    method: body ? "POST" : "GET", redirect: "error",
    headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
    ...(body ? {body: JSON.stringify(body)} : {}), signal: AbortSignal.timeout(120000)
  });
  assert.equal(r.ok, true, `private API HTTP ${r.status}`);
  return r.json();
}
async function until(fn, message) {
  const end = Date.now() + 120000;
  while (Date.now() < end) {
    if (await fn()) return;
    await new Promise(r => setTimeout(r, 100));
  }
  throw Error(message);
}
async function popup() {
  for (const t of browser.targets().filter(t => t.url() === `chrome-extension://${extensionId}/popup.html`)) {
    const page = await t.asPage(); if (!page.isClosed()) await page.close();
  }
  const previous = new Set(browser.targets());
  await worker.evaluate(() => chrome.action.openPopup());
  const target = await browser.waitForTarget(t => !previous.has(t) && t.url() === `chrome-extension://${extensionId}/popup.html`);
  const page = await target.asPage();
  await page.waitForSelector("#configure");
  return page;
}
async function main() {
  const initial = await api("/v2/status");
  assert.equal(initial.suite.paused, true, "refuse a service that is not manually paused");
  assert.equal(initial.suite.busy, false, "refuse a busy service");
  const executablePath = process.env.CHROME_PATH || (process.platform === "darwin" ?
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "/usr/bin/google-chrome");
  browser = await puppeteer.launch({executablePath, headless: true, pipe: true,
    enableExtensions: true, userDataDir: profile});
  extensionId = await browser.installExtension(path.join(root, "extension"));
  const bootstrap = await browser.newPage();
  await bootstrap.goto(`chrome-extension://${extensionId}/popup.html`);
  worker = await (await browser.waitForTarget(t => t.type() === "service_worker" &&
    t.url() === `chrome-extension://${extensionId}/background.js`)).worker();
  await bootstrap.close();
  const grant = await browser.newPage();
  await grant.goto("chrome://extensions");
  await grant.evaluate(id => chrome.developerPrivate.addHostPermission(id,
    "https://slop-detection.dimensionlab.net/*"), extensionId);
  await grant.close();
  let panel = await popup();
  await panel.click("#configure");
  await panel.$eval("#server", (n, value) => { n.value = value; }, origin);
  await panel.$eval("#token", (n, value) => { n.value = value; }, token);
  await panel.click("#test");
  await until(() => panel.$eval("#draft-result", n => n.textContent.includes("Draft verified")), "HTTPS draft test failed");
  await panel.click("#save");
  await panel.waitForFunction(() => document.getElementById("connection").textContent === "Connected · v2");
  assert.equal(await panel.$eval("#token", n => n.value), "");
  await panel.waitForFunction(() => !document.getElementById("load").disabled);
  ownsLoad = true;
  await panel.click("#load");
  await panel.waitForFunction(() => document.getElementById("residency").textContent === "Models ready · diagnostics only",
    {timeout: 120000});
  await panel.click("#scanning");
  const fixture = await browser.newPage();
  await fixture.setRequestInterception(true);
  fixture.on("request", request => {
    if (request.isNavigationRequest() && request.url() === "https://x.com/__xsd_deployed_fixture__") {
      void request.respond({status: 200, contentType: "text/html; charset=utf-8",
        body: `<!doctype html><html><head><meta charset="utf-8"></head><body>
          <article data-testid="tweet" style="width:600px;min-height:150px">
            <div data-testid="tweetText">Public synthetic Chrome deployment check 😀<br>This tests operation, not accuracy.</div>
            <div role="link"><div data-testid="tweetText">Excluded synthetic quote.</div></div>
            <div><button data-testid="grok" aria-label="Ask Grok">G</button><button data-testid="caret">Menu</button></div>
          </article></body></html>`});
    } else void request.abort();
  });
  await fixture.goto("https://x.com/__xsd_deployed_fixture__");
  await fixture.waitForSelector("[data-xsd-result]");
  await until(() => worker.evaluate(() => !!broker.latest), "No accepted real detector evidence");
  const evidence = await worker.evaluate(() => ({
    gpu: broker.snapshot.suite.verified_gpu_uuid,
    aggregate: broker.latest.result.aggregate.kind,
    checks: broker.latest.result.checks.map(c => ({id: c.checker.id, status: c.status, kind: c.output?.kind}))
  }));
  assert.equal(evidence.gpu, "GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db");
  assert.equal(evidence.aggregate, "no_estimate");
  assert.equal(evidence.checks.length, 5);
  assert.ok(evidence.checks.slice(0, 4).every(c => c.status === "completed"));
  assert.equal(evidence.checks[4].status, "unsupported");
  assert.equal(await fixture.$eval("[data-xsd-result]", n => n.textContent), "—");
  panel = await popup();
  await panel.waitForFunction(() => !document.getElementById("unload").disabled);
  await panel.click("#unload");
  await until(async () => {
    const s = await api("/v2/status");
    return s.suite.paused && !s.suite.busy && s.suite.device_memory.allocated_bytes === 0 &&
      s.suite.device_memory.reserved_bytes === 0;
  }, "Shared Unload failed");
  console.log(JSON.stringify({
    browser: await browser.version(), origin, actualGpuInference: true, syntheticPageOnly: true,
    evidence, finalState: "paused/unloaded", nativePermissionPromptManuallyTested: false
  }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  try {
    if (ownsLoad) await api("/v2/control", {schema_version: "2", action: "unload"});
  } finally { if (browser) await browser.close(); }
});
