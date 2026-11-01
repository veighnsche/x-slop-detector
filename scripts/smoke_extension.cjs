/* Actual Google Chrome + unpacked MV3 + real FastAPI with synthetic adapters.
 * No real X navigation, collected posts, provider calls, or GPU allocations.
 * Launches an isolated Chrome profile; never attaches to the user's browser.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {spawn} = require("node:child_process");
const {once} = require("node:events");
const {createInterface} = require("node:readline");
const {randomBytes} = require("node:crypto");
const puppeteer = require("puppeteer-core");
const root = path.resolve(__dirname, "..");
const executablePath = process.env.CHROME_PATH || (process.platform === "darwin" ?
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "/usr/bin/google-chrome");
const scratch = process.env.DELTA_SCRATCH_DIR || path.join(root, ".cache");
fs.mkdirSync(scratch, {recursive: true});
const profile = fs.mkdtempSync(path.join(scratch, "chrome-extension-"));
const token = `synthetic-loopback-only-${randomBytes(24).toString("hex")}`;
const server = spawn(process.env.PYTHON || path.join(root, ".venv/bin/python"),
  ["scripts/extension_fixture_server.py"], {cwd: root,
    env: {...process.env, XSD_FIXTURE_TOKEN: token}, stdio: ["ignore", "pipe", "inherit"]});
let browser, fixturePage, api, worker, extensionId;
const failures = [];
async function waitFor(fn, message, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await fn()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw Error(message);
}
async function openPopup() {
  for (const target of browser.targets().filter(t => t.url() === `chrome-extension://${extensionId}/popup.html`)) {
    const previousPopup = await target.asPage();
    if (!previousPopup.isClosed()) await previousPopup.close();
  }
  const previous = new Set(browser.targets());
  await worker.evaluate(() => chrome.action.openPopup());
  const target = await browser.waitForTarget(t => !previous.has(t) &&
    t.url() === `chrome-extension://${extensionId}/popup.html`);
  const popup = await target.asPage();
  popup.on("pageerror", error => failures.push(error.message));
  await popup.waitForSelector("#configure");
  return popup;
}
async function read(page, selector) {
  return page.$eval(selector, node => node.textContent);
}
async function fill(page, selector, value) {
  await page.$eval(selector, (node, text) => {
    node.value = text; node.dispatchEvent(new Event("input", {bubbles: true}));
  }, value);
}
async function main() {
  const lines = createInterface({input: server.stdout});
  const [line] = await once(lines, "line");
  const origin = `http://127.0.0.1:${JSON.parse(line).port}`;
  const auth = {Authorization: `Bearer ${token}`};
  await waitFor(async () => {
    try { return (await fetch(`${origin}/health`, {headers: auth})).ok; } catch { return false; }
  }, "Fixture API did not start");
  browser = await puppeteer.launch({executablePath, headless: true, pipe: true,
    enableExtensions: true, userDataDir: profile});
  extensionId = await browser.installExtension(path.join(root, "extension"));
  // Opening the resource once starts the worker. It is NOT used as the popup:
  // extension tabs are deliberately denied privileged UI messages.
  const bootstrap = await browser.newPage();
  await bootstrap.goto(`chrome-extension://${extensionId}/popup.html`);
  const workerTarget = await browser.waitForTarget(t => t.type() === "service_worker" &&
    t.url() === `chrome-extension://${extensionId}/background.js`);
  worker = await workerTarget.worker();
  const network = await workerTarget.createCDPSession();
  await network.send("Network.enable");
  const submissions = [];
  const networkFailures = [];
  network.on("Network.loadingFailed", e => networkFailures.push({
    error: e.errorText, blockedReason: e.blockedReason, cors: e.corsErrorStatus
  }));
  network.on("Network.requestWillBeSent", ({request}) => {
    if (request.url.endsWith("/v2/analyze")) submissions.push(JSON.parse(request.postData));
  });
  await bootstrap.close();
  // Chrome's native optional-host prompt is outside CDP's page DOM. Pregrant
  // ONLY this loopback host through Chrome's own extension settings, in this
  // disposable profile. popup.js still executes the real permissions.request;
  // accepting/denying the native prompt remains an interactive manual check.
  const chromeSettings = await browser.newPage();
  await chromeSettings.goto("chrome://extensions");
  await chromeSettings.evaluate(id => chrome.developerPrivate.addHostPermission(id, "http://127.0.0.1/*"), extensionId);
  await chromeSettings.close();
  let popup = await openPopup();
  await popup.click("#configure");
  await popup.waitForFunction(() => document.activeElement.id === "server");
  await fill(popup, "#server", origin);
  await fill(popup, "#token", token);
  // Real user gesture/API, with the loopback grant preconfigured above.
  await popup.click("#test");
  await waitFor(async () => (await read(popup, "#draft-result")).includes("Draft verified"),
    "Draft connection/Chrome optional-host permission was not verified").catch(async error => {
      throw Error(`${error.message}; UI: ${await read(popup, "#feedback")}; test disabled: ${
        await popup.$eval("#test", n => n.disabled)}; host grant: ${
        await worker.evaluate(o => chrome.permissions.contains({origins: [o]}), "http://127.0.0.1/*")}; network: ${
        JSON.stringify(networkFailures)}`);
    });
  assert.equal(await worker.evaluate(() => broker.settings.server), "");
  await popup.click("#save");
  await popup.waitForFunction(() => document.getElementById("config").hidden &&
    document.getElementById("connection").textContent === "Connected · v2");
  assert.equal(await popup.$eval("#token", node => node.value), "");
  await popup.click("#scanning");
  // Intercept a synthetic X URL before network; no live X text is fetched.
  fixturePage = await browser.newPage();
  fixturePage.on("pageerror", error => failures.push(error.message));
  await fixturePage.setRequestInterception(true);
  fixturePage.on("request", request => {
    if (request.isNavigationRequest() && request.url() === "https://x.com/__xsd_fixture__") {
      void request.respond({status: 200, contentType: "text/html; charset=utf-8", body: `<!doctype html><html><head><meta charset="utf-8"></head><body>
        <article data-testid="tweet" style="width:600px;min-height:150px">
          <div data-testid="tweetText">Own synthetic 😀<br>second line</div>
          <div role="link"><div data-testid="tweetText">Excluded quoted synthetic text</div></div>
          <div class="controls"><button data-testid="grok" aria-label="Ask Grok">G</button>
          <button data-testid="caret">Menu</button></div>
        </article></body></html>`});
    } else void request.abort();
  });
  await fixturePage.goto("https://x.com/__xsd_fixture__");
  await fixturePage.waitForSelector("[data-xsd-result]");
  await waitFor(() => submissions.length === 1, "No synthetic own-post request");
  assert.equal(submissions[0].posts[0].text, "Own synthetic 😀\nsecond line");
  await waitFor(async () => !!(await worker.evaluate(() => broker.latest)), "No accepted native diagnostics");
  assert.equal(await fixturePage.$eval("[data-xsd-result]", n => n.textContent), "—");
  assert.equal(await fixturePage.$eval("[data-xsd-result]", n => n.nextElementSibling.className), "controls");
  // Content-script storage cannot read the saved token.
  const frame = await fixturePage.target().createCDPSession();
  const contexts = [];
  frame.on("Runtime.executionContextCreated", ({context}) => contexts.push(context));
  await frame.send("Runtime.enable");
  const isolated = contexts.find(c => c.origin === `chrome-extension://${extensionId}`);
  assert.ok(isolated, "Missing extension isolated world");
  const denied = await frame.send("Runtime.evaluate", {contextId: isolated.id, awaitPromise: true,
    expression: "chrome.storage.local.get('connection').then(()=>false,()=>true)", returnByValue: true});
  assert.equal(denied.result.value, true, "Content world could read privileged local storage");
  const forbidden = await frame.send("Runtime.evaluate", {contextId: isolated.id, awaitPromise: true,
    expression: "chrome.runtime.sendMessage({type:'control',action:'unload'})", returnByValue: true});
  assert.equal(forbidden.result.value.error.code, "forbidden");
  // Edit a reused node: old results cannot be attached to new text.
  await fixturePage.$eval('[data-testid="tweetText"]', n => { n.textContent = "Edited synthetic own wording"; });
  await waitFor(() => submissions.some(s => s.posts[0].text === "Edited synthetic own wording"), "Edited post not rescanned");
  popup = await openPopup();
  await popup.waitForFunction(() => document.getElementById("connection").textContent === "Connected · v2");
  await popup.screenshot({path: path.join(scratch, "extension-panel.png")});
  await popup.click("#diagnostics > summary");
  await popup.waitForFunction(() => document.getElementById("native").textContent.includes("tabularis"));
  assert.equal((await read(popup, "#native")).includes("classifier_ai_score"), true);
  // Actual client #2 uses the same authenticated API and pause intent.
  api = (action) => fetch(`${origin}/v2/control`, {method: "POST", headers: {...auth, "Content-Type": "application/json"},
    body: JSON.stringify({schema_version: "2", action})});
  await api("unload");
  await popup.click("#refresh");
  await popup.waitForFunction(() => document.getElementById("residency").textContent === "Server manually paused");
  await popup.waitForFunction(() => !document.getElementById("load").disabled);
  await popup.click("#load");
  await popup.waitForFunction(() => document.getElementById("residency").textContent === "Models ready · diagnostics only");
  await popup.click("#unload");
  await popup.waitForFunction(() => document.getElementById("residency").textContent === "Server manually paused");
  await popup.click("#configure");
  await popup.screenshot({path: path.join(scratch, "extension-configuration.png")});
  await popup.click("details:has(#provider-info) > summary");
  assert.equal((await read(popup, "#provider-info")).includes("connected: false"), true);
  await popup.keyboard.press("Escape");
  assert.equal(await popup.$eval("#config", n => n.hidden), true);
  assert.equal(await popup.evaluate(() => document.activeElement.id), "configure");
  // Auth failure shown truthfully, then restore and exercise permission revocation.
  await popup.click("#configure");
  await fill(popup, "#token", "deliberately-invalid-synthetic-token");
  await popup.click("#save");
  await popup.waitForFunction(() => document.getElementById("connection").textContent === "Authentication failed");
  await popup.click("#configure"); await fill(popup, "#token", token); await popup.click("#save");
  await popup.waitForFunction(() => document.getElementById("connection").textContent === "Connected · v2");
  await popup.click("#configure");
  await popup.click("details:has(#revoke) > summary");
  await popup.click("#revoke");
  await popup.waitForFunction(() => document.getElementById("residency").textContent.includes("Grant access"));
  assert.equal(await worker.evaluate(() => broker.settings.token.length > 24), true);
  // Restore a grant in the disposable profile, stop the fixture, and verify
  // offline state rather than treating the last ready snapshot as current.
  const grantPage = await browser.newPage();
  await grantPage.goto("chrome://extensions");
  await grantPage.evaluate(id => chrome.developerPrivate.addHostPermission(id, "http://127.0.0.1/*"), extensionId);
  await grantPage.close();
  popup = await openPopup();
  await popup.click("#configure");
  await popup.click("#test");
  await waitFor(async () => (await read(popup, "#draft-result")).includes("Draft verified"),
    "Loopback permission was not reacquired after revocation");
  server.kill("SIGTERM");
  await once(server, "exit");
  popup = await openPopup();
  await popup.waitForFunction(() => document.getElementById("residency").textContent.includes("Cannot reach"));
  assert.deepEqual(failures, []);
  console.log(JSON.stringify({
    browser: await browser.version(), extension: "unpacked MV3",
    server: "real FastAPI/LocalSuite with synthetic adapters (not GPU inference)",
    checks: ["actual action popup", "cogwheel/focus/Escape", "draft test without save",
      "pregranted loopback permission/revocation", "background-only storage", "content message rejection",
      "own-text/quote separation", "edit rescan", "native diagnostics/no-number",
      "shared second-client pause", "Load/Unload", "authentication failure", "offline failure"],
    syntheticSubmissions: submissions.length, pageErrors: failures.length,
    liveX: false, nativePermissionPromptManuallyTested: false, accuracyClaim: false, profileDirectory: profile
  }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  server.kill("SIGTERM");
  if (server.exitCode === null) await once(server, "exit");
});
