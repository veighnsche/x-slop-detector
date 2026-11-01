(() => {
  "use strict";
  const X = globalThis.XSD;
  const records = new Map(); // Visible/current DOM only; hard bounded below.
  const LIMIT = 24, QUEUE = 12;
  let running = false, timer, epoch = 0, configuration = null;
  let preferences = {scan: false, reason: "scanning_off"};
  let disposed = false;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function message(payload) {
    let reply;
    try { reply = await chrome.runtime.sendMessage(payload); }
    catch { throw new X.ClientError("offline"); }
    if (!reply?.ok) throw new X.ClientError(reply?.error?.code || "offline", reply?.error?.retryable === true);
    return reply.data;
  }
  const visible = article => {
    const r = article.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
  };
  function display(record, reason) {
    if (!record.badge.isConnected) record.anchor.before(record.badge);
    const explanation = X.explain(reason);
    record.badge.textContent = "—";
    record.badge.title = `X Slop Detector: ${explanation}`;
    record.badge.setAttribute("aria-label", `AI wording estimate unavailable. ${explanation}`);
  }
  function remove(article) {
    records.get(article)?.badge.remove(); records.delete(article);
  }
  function reconcile() {
    for (const [article, record] of records) {
      if (!article.isConnected || !visible(article) || !X.dom.stillMatches(article, record)) remove(article);
    }
    const articles = Array.from(document.querySelectorAll(X.dom.TWEET)).filter(visible).slice(0, LIMIT);
    for (const article of articles) {
      const data = X.dom.extract(article);
      if (!data) { remove(article); continue; }
      if (!records.has(article)) {
        if (records.size >= LIMIT) break;
        const badge = document.createElement("span");
        badge.className = "xsd-result";
        badge.setAttribute("data-xsd-result", "");
        badge.setAttribute("role", "note");
        const record = {...data, badge, done: false};
        records.set(article, record);
        display(record, !X.textOK(data.text) ? "text_too_long" :
          preferences.scan ? "no_validated_profile" : preferences.reason);
      }
    }
  }
  function schedule() {
    if (disposed || timer) return;
    timer = setTimeout(() => { timer = null; void run(); }, 300);
  }
  async function run() {
    if (disposed || running || document.hidden) return;
    running = true;
    try {
      try {
        const next = await message({type: "preferences"});
        if (configuration !== next.configuration || preferences.scan !== next.scan) {
          epoch++;
          for (const [article] of records) remove(article);
        }
        configuration = next.configuration; preferences = next;
      } catch (error) {
        preferences = {scan: false, reason: error.code};
        epoch++;
        for (const record of records.values()) { record.done = false; display(record, error.code); }
      }
      reconcile();
      if (!preferences.scan) {
        for (const record of records.values()) display(record, preferences.reason);
        return;
      }
      const generation = epoch;
      const queue = Array.from(records).filter(([, r]) => !r.done &&
        X.textOK(r.text)).slice(0, QUEUE);
      for (const [article, record] of queue) {
        if (generation !== epoch || document.hidden || !article.isConnected ||
            !visible(article) || !X.dom.stillMatches(article, record)) continue;
        for (let attempt = 0; attempt <= 3; attempt++) {
          if (disposed || generation !== epoch || records.get(article) !== record ||
              !article.isConnected || !visible(article) || !X.dom.stillMatches(article, record)) break;
          try {
            const response = await message({type: "scan", text: record.text});
            // Async responses must never attach to an edited/recycled or unmounted post.
            if (generation !== epoch || !article.isConnected || !visible(article) ||
                records.get(article) !== record || !X.dom.stillMatches(article, record)) break;
            if (response.configuration !== configuration || response.result?.aggregate?.kind !== "no_estimate") {
              throw new X.ClientError("incompatible_response");
            }
            record.done = true;
            display(record, response.result.aggregate.reason);
            break;
          } catch (error) {
            if (generation !== epoch || records.get(article) !== record ||
                !X.dom.stillMatches(article, record)) break;
            if (error.retryable && attempt < 3) {
              await sleep(2000 * 2 ** attempt);
              if (document.hidden || !visible(article)) break;
              continue;
            }
            display(record, error.code);
            // No automatic retry loop after exhaustion. New text/config or explicit
            // off/on scanning permits retry; scrolling an unmounted post may too.
            record.done = true;
            if (["manually_paused", "scanning_off", "settings_changed"].includes(error.code)) {
              preferences = {scan: false, reason: error.code};
              epoch++; schedule(); return;
            }
            break;
          }
        }
      }
      if (Array.from(records.values()).some(r => !r.done && X.textOK(r.text))) schedule();
    } finally { running = false; }
  }
  const observer = new MutationObserver(mutations => {
    // Ignore our own readout updates so there is no observer/request feedback loop.
    if (mutations.some(m => !m.target.closest?.("[data-xsd-result]") &&
        !(m.type === "childList" && [...m.addedNodes, ...m.removedNodes].every(n =>
          n.nodeType === 1 && n.matches?.("[data-xsd-result]"))))) schedule();
  });
  observer.observe(document.documentElement, {childList: true, subtree: true, characterData: true,
    attributes: true, attributeFilter: ["data-testid", "role", "aria-label"]});
  addEventListener("scroll", schedule, {passive: true});
  addEventListener("popstate", () => { epoch++; for (const [a] of records) remove(a); schedule(); });
  document.addEventListener("visibilitychange", schedule);
  // Polling metadata does not refresh server residency. No polls in hidden tabs.
  const interval = setInterval(schedule, 5000);
  addEventListener("pagehide", () => {
    disposed = true; observer.disconnect(); clearInterval(interval); clearTimeout(timer);
    for (const [article] of records) remove(article);
  }, {once: true});
  schedule();
})();
