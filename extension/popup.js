(() => {
  "use strict";
  const X = globalThis.XSD, $ = id => document.getElementById(id);
  let settings, snapshot, command = false, polling = false, editing = false;
  async function call(message) {
    const response = await chrome.runtime.sendMessage(message);
    if (!response?.ok) throw new X.ClientError(response?.error?.code || "operation_failed");
    return response.data;
  }
  const feedback = text => { $("feedback").textContent = text; };
  const entry = (container, title, lines) => {
    const node = document.createElement("div");
    node.className = "entry";
    const strong = document.createElement("strong"); strong.textContent = title;
    const p = document.createElement("p"); p.textContent = lines.join("\n");
    node.append(strong, p); container.append(node);
  };
  function renderStatus(s) {
    snapshot = s;
    const t = s.suite;
    $("connection").textContent = "Connected · v2";
    $("residency").textContent = t.paused ? "Server manually paused" :
      t.busy ? `Server ${t.operation}` : s.diagnostics_ready ? "Models ready · diagnostics only" : "Models unloaded or unavailable";
    $("progress").textContent = [
      t.pending_control ? `${t.pending_control} pending` : null,
      t.unload_in_seconds !== null ? `Idle unload in ${Math.ceil(t.unload_in_seconds)} s` : null,
      !t.pause_persisted ? "Warning: pause intent is not persisted" : null,
      t.last_error ? X.explain(t.last_error) : null
    ].filter(Boolean).join(" · ") || "Lazy loading enabled; status polls do not load models.";
    $("load").disabled = command || !!t.pending_control || t.busy;
    // Unload remains available during analysis/loading so it can latch shared pause.
    $("unload").disabled = command || t.pending_control === "unload";
    for (const id of ["profile-info", "component-info", "watermark-info", "provider-info"]) $(id).replaceChildren();
    entry($("profile-info"), "No validated scoring profile", [
      `Configuration: ${t.configuration_id}`, "Target: substantive LLM-generated/rewritten wording.",
      "No validated language/length scope. Feed percentages are disabled.",
      `Device: ${t.configured_device}`, `Verified GPU: ${t.verified_gpu_uuid || "not yet verified"}`,
      `Server idle policy: ${t.idle_timeout_seconds} s · read-only`,
      `Blockers: ${s.blockers.join(", ")}`
    ]);
    for (const c of t.components) entry($("component-info"), c.checker_id, [
      `${c.required ? "Required" : "Optional"} · ${c.state}`
    ]);
    if (!t.local_watermark_routes.length) $("watermark-info").textContent = "No local route configured.";
    for (const r of t.local_watermark_routes) entry($("watermark-info"), `KGW · ${r.state}`, [
      `Applicability: ${r.applicability} · ${r.purpose}`,
      `Configured: ${r.configured} · enabled: ${r.enabled} · device: ${r.device}`,
      `Scope: ${r.scope_description || "No matching generation configuration"}`,
      `Public key alias: ${r.key_id || "none"}`,
      `Blocker: ${r.blocker || "none"} · minimum ${r.minimum_unique_bigrams} unique bigrams`,
      "One matching-key test; no negative implies human authorship. Research keys are not provider coverage."
    ]);
    if (!t.provider_routes.length) $("provider-info").textContent = "No provider routes.";
    for (const r of t.provider_routes) entry($("provider-info"), `${r.id} · ${r.state}`, [
      `Access: ${r.access} · application submitted: ${r.application_submitted}`,
      `Configured: ${r.configured} · approved: ${r.approved} · enabled: ${r.enabled}`,
      `Support: ${r.support} · terms approved: ${r.terms_approved}`,
      `Free/unlimited verified: ${r.free_unlimited_verified} · connected: ${r.connected}`,
      `Blockers: ${r.blockers.join(", ")}`, "Data destination: none (no callable adapter)."
    ]);
    $("destination").textContent = `Saved analysis destination: ${settings.server || "none"}. Hosted routes are disabled.`;
  }
  function offline(error) {
    snapshot = null;
    $("connection").textContent = error.code === "unauthorized" ? "Authentication failed" : "Not connected";
    $("residency").textContent = X.explain(error.code);
    $("progress").textContent = "No current server state. Previously displayed state is invalid.";
    $("load").disabled = $("unload").disabled = true;
    for (const id of ["profile-info", "component-info", "watermark-info", "provider-info"]) {
      $(id).textContent = "No verified saved connection.";
    }
    $("native").textContent = "No current diagnostics; connection unavailable.";
  }
  async function update() {
    if (polling || command) return;
    polling = true;
    try {
      settings = await call({type: "settings"});
      $("scanning").checked = settings.scan;
      renderStatus(X.status(await call({type: "status"})));
      const latest = await call({type: "diagnostics"});
      $("native").replaceChildren();
      if (!latest) $("native").textContent = "No analysis yet.";
      else {
        entry($("native"), "Not a combined probability", [X.explain(latest.result.aggregate.reason)]);
        for (const c of latest.result.checks) {
          const o = c.output;
          const native = !o ? c.reason : o.kind === "watermark_detection" ?
            `${o.decision}; ${o.verification_scope}; ${o.configuration_purpose}; z=${o.z_score}; p=${o.p_value}` :
            `${o.kind}: ${o.value}`;
          entry($("native"), `${c.checker.id} · ${c.status}`, [
            native, `Tokens: ${c.coverage.input_tokens ?? "unknown"} / ${c.coverage.token_limit ?? "none"}`,
            `Configuration: ${c.checker.configuration_id}`, `Revision: ${c.checker.artifact_revision}`
          ]);
        }
      }
    } catch (error) { offline(error); }
    finally { polling = false; }
  }
  function closeConfig() {
    $("token").value = ""; editing = false;
    $("config").hidden = true; $("panel").hidden = false; $("configure").hidden = false;
    document.querySelector("main").scrollTop = 0;
    $("configure").focus();
  }
  $("configure").addEventListener("click", () => {
    editing = true; $("server").value = settings?.server || ""; $("token").value = "";
    $("draft-result").textContent = "Draft not tested. Server details below refer to the saved connection only.";
    $("credential-note").textContent = settings?.hasToken ?
      "A token is saved in background-only local storage. Blank keeps it only for the same server." :
      "No saved token. Never synced or exposed to X pages.";
    $("panel").hidden = true; $("config").hidden = false; $("configure").hidden = true;
    document.querySelector("main").scrollTop = 0;
    $("server").focus();
  });
  for (const id of ["cancel", "close-config"]) $(id).addEventListener("click", closeConfig);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && editing && !command) { event.preventDefault(); closeConfig(); }
  });
  for (const id of ["server", "token"]) $(id).addEventListener("input", () => {
    $("draft-result").textContent = "Draft not tested. Server details below refer to the saved connection only.";
  });
  async function connectDraft(save) {
    if (command) return;
    command = true; $("save").disabled = $("test").disabled = true;
    try {
      const server = X.serverURL($("server").value), token = $("token").value;
      if (token && !X.tokenOK(token)) throw new X.ClientError("invalid_token");
      if (!token && (!settings?.hasToken || settings.server !== server)) throw new X.ClientError("invalid_token");
      const granted = await chrome.permissions.request({origins: [X.permission(server)]});
      if (!granted) throw new X.ClientError("permission_missing");
      if (save) {
        settings = await call({type: "save", server, token});
        closeConfig(); feedback("Connection saved. Scanning remains a separate, client-local preference.");
      } else {
        const tested = X.status(await call({type: "test", server, token}));
        $("draft-result").textContent = `Draft verified · v2 · ${tested.suite.configuration_id}. Not saved; details below still belong to the saved connection.`;
      }
    } catch (error) { feedback(X.explain(error.code || "operation_failed")); }
    finally { command = false; $("save").disabled = $("test").disabled = false; if (save) void update(); }
  }
  $("test").addEventListener("click", () => void connectDraft(false));
  $("connection-form").addEventListener("submit", event => { event.preventDefault(); void connectDraft(true); });
  $("revoke").addEventListener("click", async () => {
    if (!settings?.server) return;
    await chrome.permissions.remove({origins: [X.permission(settings.server)]});
    feedback("Saved server access revoked. No new requests can be sent without another grant.");
    void update();
  });
  $("scanning").addEventListener("change", async () => {
    try {
      settings = await call({type: "scanPreference", enabled: $("scanning").checked});
      feedback(settings.scan ? "Client scanning on. Shared server pause still applies." :
        "Client scanning off. Already-owned requests can finish; models were not unloaded.");
    } catch (error) { feedback(X.explain(error.code)); }
    void update();
  });
  for (const action of ["load", "unload"]) $(action).addEventListener("click", async () => {
    if (command) return;
    command = true; $("load").disabled = $("unload").disabled = true;
    feedback(`${action === "load" ? "Load" : "Unload"} requested…`);
    try {
      const r = await call({type: "control", action});
      renderStatus(r.status);
      feedback(`${action}: ${r.disposition}. ${action === "load" ?
        "Server resumes; client scanning preference is unchanged." : "Shared pause applies to every client."}`);
    } catch (error) { feedback(X.explain(error.code)); }
    finally { command = false; void update(); }
  });
  $("refresh").addEventListener("click", () => void update());
  setInterval(() => void update(), 2500);
  void update();
})();
