/* The only context allowed to hold credentials or contact the analysis server. */
(() => {
  "use strict";
  const X = globalThis.XSD;
  class Broker {
    constructor(browser, fetcher = fetch, now = Date.now) {
      // Native browser fetch is a WebIDL method: never invoke it with Broker
      // as its receiver (Node's fetch does not expose that browser-only failure).
      this.browser = browser; this.fetcher = (...args) => fetcher(...args); this.now = now;
      this.settings = {server: "", token: "", scan: false};
      this.epoch = 0; this.cache = new X.Cache(128, 300000, now);
      this.snapshot = null; this.catalog = null; this.checkedAt = 0;
      this.active = null; this.latest = null; this.controlPending = false;
      this.settingsTail = Promise.resolve();
    }
    async init() {
      // Not sync storage. Deny content-script access before reading the credential.
      await this.browser.storage.local.setAccessLevel({accessLevel: "TRUSTED_CONTEXTS"});
      const {connection} = await this.browser.storage.local.get("connection");
      if (connection) {
        try {
          this.settings = {server: X.serverURL(connection.server), token: connection.token,
            scan: connection.scan === true};
          if (!X.tokenOK(connection.token)) throw Error();
        } catch { this.settings = {server: "", token: "", scan: false}; }
      }
    }
    role(sender) {
      if (sender.id !== this.browser.runtime.id) return null;
      if (!sender.tab && sender.url === this.browser.runtime.getURL("popup.html")) return "ui";
      let url;
      try { url = new URL(sender.url); } catch { return null; }
      return Number.isInteger(sender.tab?.id) && sender.frameId === 0 &&
        url.protocol === "https:" && ["x.com", "twitter.com"].includes(url.hostname) ? "content" : null;
    }
    async permitted(settings = this.settings) {
      return !!settings.server && this.browser.permissions.contains({origins: [X.permission(settings.server)]});
    }
    publicSettings() {
      return {server: this.settings.server, hasToken: !!this.settings.token, scan: this.settings.scan};
    }
    draft(message) {
      const server = X.serverURL(message.server);
      const token = message.token || (server === this.settings.server ? this.settings.token : "");
      if (!X.tokenOK(token)) throw new X.ClientError("invalid_token");
      return {server, token, scan: this.settings.scan};
    }
    async request(path, body, settings = this.settings) {
      if (!settings.server) throw new X.ClientError("not_configured");
      if (!await this.permitted(settings)) throw new X.ClientError("permission_missing");
      let response, data;
      try {
        response = await this.fetcher(`${settings.server}/v2/${path}`, {
          method: body ? "POST" : "GET", redirect: "error", credentials: "omit",
          cache: "no-store", referrerPolicy: "no-referrer",
          headers: {Authorization: `Bearer ${settings.token}`, ...(body ? {"Content-Type": "application/json"} : {})},
          ...(body ? {body: JSON.stringify(body)} : {}),
          signal: AbortSignal.timeout(path === "analyze" ? 120000 : 15000)
        });
        const reader = response.body.getReader();
        let size = 0;
        const chunks = [];
        try {
          for (;;) {
            const {done, value} = await reader.read();
            if (done) break;
            size += value.byteLength;
            if (size > 1048576) throw new X.ClientError("incompatible_response");
            chunks.push(value);
          }
        } finally { await reader.cancel().catch(() => {}); }
        const bytes = new Uint8Array(size);
        let offset = 0;
        for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
        data = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
      } catch (error) {
        if (error instanceof X.ClientError) throw error;
        if (error.name === "TimeoutError" || error.name === "AbortError") throw new X.ClientError("timeout");
        if (response) throw new X.ClientError("incompatible_response");
        throw new X.ClientError("offline");
      }
      if (!response.ok) {
        if (data?.schema_version !== "2" || typeof data.error?.code !== "string" ||
            typeof data.error?.retryable !== "boolean") throw new X.ClientError("incompatible_response");
        const allowed = ["unauthorized", "body_too_large", "invalid_request", "busy", "manually_paused",
          "resource_exhausted", "suite_not_integrated", "operation_failed", "not_found", "method_not_allowed"];
        if (!allowed.includes(data.error.code)) throw new X.ClientError("incompatible_response");
        // Only explicit busy/rate-limit responses may be retried; never timeouts/auth/OOM.
        throw new X.ClientError(data.error.code, data.error.retryable &&
          (data.error.code === "busy" || response.status === 429));
      }
      return data;
    }
    async probe(settings = this.settings) {
      const [catalog, snapshot] = await Promise.all([
        this.request("capabilities", null, settings), this.request("status", null, settings)
      ]);
      X.capabilities(catalog); X.status(snapshot);
      for (const c of snapshot.suite.components) {
        X.require(catalog.checkers.some(s => s.checker.id === c.checker_id));
      }
      return {catalog, snapshot};
    }
    accept(probe) {
      if (this.snapshot?.suite.configuration_id !== probe.snapshot.suite.configuration_id) {
        this.cache.clear(); this.latest = null;
      }
      this.catalog = probe.catalog; this.snapshot = probe.snapshot; this.checkedAt = this.now();
      if (this.snapshot.suite.paused) this.cache.clear();
    }
    async refresh() {
      const epoch = this.epoch;
      this.cache.prune();
      try {
        const probe = await this.probe();
        if (epoch !== this.epoch) throw new X.ClientError("settings_changed");
        this.accept(probe);
        return this.snapshot;
      } catch (error) {
        if (epoch === this.epoch) {
          this.snapshot = null; this.checkedAt = 0; this.cache.clear(); this.latest = null;
        }
        throw error;
      }
    }
    async preferences(force = false) {
      this.cache.prune();
      if (!this.settings.scan) return {scan: false, reason: "scanning_off", configuration: null};
      if (!this.settings.server) return {scan: false, reason: "not_configured", configuration: null};
      if (force || !this.snapshot || !this.catalog || this.now() - this.checkedAt >= 10000) await this.refresh();
      return {scan: !this.snapshot.suite.paused,
        reason: this.snapshot.suite.paused ? "manually_paused" : null,
        configuration: this.snapshot.suite.configuration_id};
    }
    async scan(text) {
      if (!X.textOK(text)) throw new X.ClientError("text_too_long");
      if (this.settings.server && !await this.permitted()) throw new X.ClientError("permission_missing");
      const prefs = await this.preferences();
      if (!prefs.scan) throw new X.ClientError(prefs.reason);
      const epoch = this.epoch, snapshot = this.snapshot, catalog = this.catalog;
      const key = JSON.stringify([this.settings.server, snapshot.suite.configuration_id, X.EXTRACTION, X.TARGET, text]);
      const cached = this.cache.get(key);
      if (cached) return {result: cached, configuration: snapshot.suite.configuration_id};
      if (this.controlPending || this.snapshot.suite.busy) throw new X.ClientError("busy", true);
      if (this.active) {
        if (this.active.key === key) return this.active.promise;
        throw new X.ClientError("busy", true);
      }
      const promise = (async () => {
        const raw = await this.request("analyze", {
          schema_version: "2", extraction_version: X.EXTRACTION, posts: [{id: "post", text}]
        });
        if (epoch !== this.epoch || !this.settings.scan) throw new X.ClientError("settings_changed");
        const result = X.analysis(raw, text, snapshot, catalog);
        // Do not return an old config/pause result if another status poll has changed it.
        if (!this.snapshot || this.snapshot.suite.paused ||
            this.snapshot.suite.configuration_id !== snapshot.suite.configuration_id) {
          throw new X.ClientError("settings_changed");
        }
        this.cache.set(key, result);
        this.latest = {configuration: snapshot.suite.configuration_id, result};
        return this.latest;
      })();
      this.active = {key, promise};
      try { return await promise; } finally { this.active = null; }
    }
    async dispatch(message, sender, serialized = false) {
      const role = this.role(sender);
      const contentActions = ["preferences", "scan"];
      const uiActions = ["settings", "status", "test", "save", "scanPreference", "control", "diagnostics"];
      if (!message || !role || !(role === "ui" ? uiActions : contentActions).includes(message.type)) {
        throw new X.ClientError("forbidden");
      }
      const keys = {
        preferences: ["type"], scan: ["type", "text"], settings: ["type"], status: ["type"],
        test: ["type", "server", "token"], save: ["type", "server", "token"],
        scanPreference: ["type", "enabled"], control: ["type", "action"], diagnostics: ["type"]
      };
      if (Object.keys(message).some(k => !keys[message.type].includes(k))) throw new X.ClientError("forbidden");
      if (!serialized && ["save", "scanPreference"].includes(message.type)) {
        const operation = this.settingsTail.then(() => this.dispatch(message, sender, true));
        this.settingsTail = operation.catch(() => {});
        return operation;
      }
      switch (message.type) {
        case "settings": return this.publicSettings();
        case "preferences": return this.preferences();
        case "scan": return this.scan(message.text);
        case "status": return this.refresh();
        case "diagnostics": return this.latest;
        case "test": return (await this.probe(this.draft(message))).snapshot;
        case "save": {
          const next = this.draft(message);
          if (!await this.permitted(next)) throw new X.ClientError("permission_missing");
          await this.browser.storage.local.set({connection: next});
          this.epoch++; this.settings = next; this.snapshot = this.catalog = this.latest = null;
          this.checkedAt = 0; this.cache.clear();
          return this.publicSettings();
        }
        case "scanPreference": {
          if (typeof message.enabled !== "boolean") throw new X.ClientError("forbidden");
          const next = {...this.settings, scan: message.enabled};
          await this.browser.storage.local.set({connection: next});
          this.settings = next;
          this.epoch++; this.cache.clear(); this.latest = null;
          return this.publicSettings();
        }
        case "control": {
          if (!["load", "unload"].includes(message.action)) throw new X.ClientError("forbidden");
          if (this.controlPending) throw new X.ClientError("busy", true);
          this.controlPending = true;
          this.epoch++; // Discard already-owned results, especially during Unload.
          this.cache.clear();
          this.latest = null;
          try {
            const epoch = this.epoch;
            const r = await this.request("control", {schema_version: "2", action: message.action});
            X.require(r.schema_version === "2" && r.action === message.action &&
              ["completed", "pending"].includes(r.disposition));
            X.status(r.status);
            if (epoch !== this.epoch) throw new X.ClientError("settings_changed");
            this.snapshot = r.status; this.checkedAt = this.now();
            return r;
          } finally { this.controlPending = false; }
        }
      }
    }
  }
  X.Broker = Broker;
})();
