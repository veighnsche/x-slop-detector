/* Shared, dependency-free protocol boundary; usable in MV3 and Node fixtures. */
globalThis.XSD = (() => {
  "use strict";
  const EXTRACTION = "own-post-text-v1";
  const TARGET = "substantive_llm_wording_v1";
  const id = v => typeof v === "string" && /^[a-zA-Z0-9._:-]{1,100}$/.test(v);
  const str = v => typeof v === "string" && v.length <= 1024;
  const bool = v => typeof v === "boolean";
  const finite = v => typeof v === "number" && Number.isFinite(v);
  const count = v => Number.isSafeInteger(v) && v >= 0;
  const one = (v, choices) => choices.includes(v);
  const fail = code => { throw new ClientError(code); };
  class ClientError extends Error {
    constructor(code, retryable = false) { super(code); this.code = code; this.retryable = retryable; }
  }
  function require(value) { if (!value) fail("incompatible_response"); }
  function serverURL(value) {
    let u;
    try { u = new URL(value); } catch { fail("invalid_server"); }
    if (u.username || u.password || u.search || u.hash || u.pathname !== "/" ||
        !(u.protocol === "https:" || (u.protocol === "http:" &&
          ["localhost", "127.0.0.1", "[::1]"].includes(u.hostname)))) fail("invalid_server");
    return u.origin;
  }
  // Chrome host grants cover all ports on a host, not one TCP port.
  const permission = server => {
    const u = new URL(serverURL(server));
    return `${u.protocol}//${u.hostname}/*`;
  };
  function tokenOK(token) {
    return typeof token === "string" && /^[\x21-\x7e]{24,4096}$/.test(token);
  }
  function textOK(text) {
    return typeof text === "string" && text.trim().length > 0 && [...text].length <= 10000;
  }
  function ref(r) { require(r && id(r.id) && id(r.configuration_id) && str(r.artifact_revision)); }
  function capabilities(c) {
    require(c?.schema_version === "2" && Array.isArray(c.supported_schema_versions) &&
      c.supported_schema_versions.includes("2") && Array.isArray(c.checkers) &&
      c.checkers.length > 0 && c.checkers.length <= 32);
    const seen = new Set();
    for (const s of c.checkers) {
      ref(s.checker);
      require(!seen.has(s.checker.id) && one(s.kind, ["classifier", "statistical", "watermark"]) &&
        str(s.artifact_id) && str(s.precision) && s.preprocessing === "raw_text" &&
        (s.max_tokens === null || count(s.max_tokens) && s.max_tokens > 0));
      seen.add(s.checker.id);
    }
    require(c.limits?.hosted_requests_enabled === false && c.limits.max_posts >= 1 &&
      c.limits.max_body_bytes >= 64000 && c.limits.max_text_characters >= 10000);
    return c;
  }
  function status(s) {
    require(s?.schema_version === "2" && s.calibration_status === "not_configured" &&
      s.probability_ready === false && bool(s.diagnostics_ready) && Array.isArray(s.blockers) &&
      s.blockers.every(str));
    const t = s.suite;
    require(t && id(t.configuration_id) && bool(t.integrated) && bool(t.paused) &&
      bool(t.pause_persisted) && bool(t.busy) &&
      one(t.operation, ["idle", "loading", "analyzing", "unloading"]) &&
      one(t.pending_control, [null, "load", "unload"]) &&
      (t.last_error === null || str(t.last_error)) && str(t.configured_device) &&
      (t.verified_gpu_uuid === null || str(t.verified_gpu_uuid)) &&
      finite(t.idle_timeout_seconds) && t.idle_timeout_seconds >= 1 &&
      (t.unload_in_seconds === null || finite(t.unload_in_seconds) && t.unload_in_seconds >= 0) &&
      Array.isArray(t.components) && t.components.length > 0 && t.components.length <= 32);
    const seen = new Set();
    for (const c of t.components) {
      require(id(c.checker_id) && !seen.has(c.checker_id) && bool(c.required) &&
        one(c.state, ["unavailable", "unloaded", "loading", "ready", "unloading", "error"]));
      seen.add(c.checker_id);
    }
    require(t.components.some(c => c.required) && Array.isArray(t.provider_routes) &&
      t.provider_routes.length <= 4 && new Set(t.provider_routes.map(r => r.id)).size === t.provider_routes.length);
    for (const r of t.provider_routes) {
      require(one(r.id, ["anthropic", "openai", "google", "xai"]) &&
        one(r.access, ["pending", "unconfirmed", "granted"]) &&
        one(r.state, ["discovered", "access_pending", "configured", "approved", "unsupported", "failed"]) &&
        one(r.support, ["unconfirmed", "supported", "unsupported"]) &&
        ["application_submitted", "configured", "approved", "terms_approved", "free_unlimited_verified"].every(k => bool(r[k])) &&
        r.enabled === false && r.connected === false && r.adapter_implemented === false &&
        Array.isArray(r.blockers) && r.blockers.length <= 16 && r.blockers.every(str));
    }
    require(Array.isArray(t.local_watermark_routes) && t.local_watermark_routes.length <= 1);
    for (const r of t.local_watermark_routes) {
      require(r.id === "kgw" && id(r.configuration_id) && bool(r.configured) && bool(r.enabled) &&
        one(r.applicability, ["unconfigured", "operator_scoped"]) &&
        one(r.purpose, ["research_fixture", "known_configuration"]) &&
        one(r.state, ["unavailable", "unloaded", "ready", "error"]) &&
        (r.key_id === null || id(r.key_id)) &&
        (r.scope_description === null || str(r.scope_description)) &&
        (r.blocker === null || str(r.blocker)) && r.device === "cpu");
    }
    return s;
  }
  const reasons = {
    unavailable: ["adapter_not_integrated", "access_pending", "route_disabled", "model_not_loaded",
      "manually_paused", "configuration_invalid", "implementation_unavailable"],
    unsupported: ["token_limit_exceeded", "unsupported_language", "no_matching_configuration"],
    insufficient_evidence: ["too_little_signal", "no_next_token_observations"],
    failed: ["checker_error", "invalid_checker_output"], timed_out: ["checker_timeout"]
  };
  function analysis(a, text, snapshot, catalog) {
    require(a?.schema_version === "2" && a.configuration_id === snapshot.suite.configuration_id &&
      a.extraction_version === EXTRACTION && a.calibration_status === "not_configured" &&
      Array.isArray(a.results) && a.results.length === 1);
    const r = a.results[0], expected = snapshot.suite.components;
    require(r?.id === "post" && r.aggregate?.kind === "no_estimate" &&
      r.aggregate.target_id === TARGET &&
      one(r.aggregate.reason, ["no_validated_profile", "required_evidence_missing"]) &&
      Array.isArray(r.checks) && r.checks.length === expected.length &&
      new Set(r.checks.map(c => c.checker?.id)).size === expected.length);
    for (const c of r.checks) {
      ref(c.checker);
      const spec = catalog.checkers.find(s => s.checker.id === c.checker.id &&
        s.checker.configuration_id === c.checker.configuration_id &&
        s.checker.artifact_revision === c.checker.artifact_revision);
      require(spec && expected.some(s => s.checker_id === c.checker.id));
      const v = c.coverage;
      require(v && v.characters === [...text].length && v.truncated === false &&
        v.token_limit === spec.max_tokens &&
        [v.input_tokens, v.scored_tokens].every(n => n === null || count(n)) &&
        (v.input_tokens === null || v.scored_tokens === null || v.scored_tokens <= v.input_tokens));
      if (c.status !== "completed") {
        require(c.output === null && reasons[c.status]?.includes(c.reason));
        continue;
      }
      require(c.reason === null && c.output &&
        (v.input_tokens === null || v.token_limit === null || v.input_tokens <= v.token_limit));
      const o = c.output;
      if (spec.kind === "classifier") require(o.kind === "classifier_ai_score" &&
        finite(o.value) && o.value >= 0 && o.value <= 1 && o.ai_label_index === 1 &&
        count(v.input_tokens) && v.input_tokens > 0);
      if (spec.kind === "statistical") require(o.kind === "token_probability_discrepancy" &&
        finite(o.value) && count(v.input_tokens) && v.input_tokens >= 2);
      if (spec.kind === "watermark") require(o.kind === "watermark_detection" &&
        one(o.decision, ["detected", "not_detected", "inconclusive"]) &&
        one(o.verification_scope, ["known_configuration", "provider"]) &&
        (o.z_score === null || finite(o.z_score)) &&
        (o.p_value === null || finite(o.p_value) && o.p_value >= 0 && o.p_value <= 1) &&
        count(o.tests_performed) && o.tests_performed >= 1 &&
        one(o.configuration_purpose, [null, "research_fixture", "known_configuration"]));
    }
    return r;
  }
  const explanations = {
    no_validated_profile: "No validated combined probability. Native checks are research diagnostics only.",
    required_evidence_missing: "Required evidence is missing or unsupported; no probability is available.",
    manually_paused: "Server manually paused. Press Load in the extension to resume.",
    scanning_off: "Client scanning is off. This does not unload the shared server.",
    busy: "The shared server is busy. Bounded retries were exhausted.",
    not_configured: "Configure a server in the extension.",
    permission_missing: "Grant access to the chosen server in Configuration.",
    unauthorized: "Server rejected the credential. Check Configuration.",
    offline: "Cannot reach the configured server.",
    timeout: "Request timed out. The server may still be finishing owned work.",
    incompatible_response: "Incompatible or invalid v2 response. No result was accepted.",
    text_too_long: "Post exceeds the client's 10,000-character input limit.",
    invalid_server: "Use an HTTPS origin, or HTTP on localhost/127.0.0.1/[::1]. No path or credentials.",
    invalid_token: "A server token of at least 24 printable ASCII characters is required.",
    settings_changed: "Connection changed during the request; the old response was discarded.",
    forbidden: "This extension message is not authorized."
  };
  const explain = code => explanations[code] || `No estimate: ${String(code).replaceAll("_", " ")}.`;
  class Cache {
    constructor(max = 128, ttl = 300000, now = Date.now) {
      this.max = max; this.ttl = ttl; this.now = now; this.items = new Map();
    }
    prune() {
      for (const [key, item] of this.items) if (this.now() >= item.expires) this.items.delete(key);
    }
    get(key) {
      this.prune();
      const item = this.items.get(key);
      if (!item) return;
      if (this.now() >= item.expires) { this.items.delete(key); return; }
      this.items.delete(key); this.items.set(key, item); return item.value;
    }
    set(key, value) {
      this.prune();
      this.items.delete(key);
      this.items.set(key, {value, expires: this.now() + this.ttl});
      while (this.items.size > this.max) this.items.delete(this.items.keys().next().value);
    }
    clear() { this.items.clear(); }
  }
  return {EXTRACTION, TARGET, ClientError, require, serverURL, permission, tokenOK, textOK,
    capabilities, status, analysis, Cache, explain};
})();
