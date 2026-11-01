# Private HTTPS deployment

**Authorized and deployed 1 November 2026:** after inspecting the hosts, the user explicitly approved a **private LAN/Tailscale HTTPS endpoint**. This is a persistent operational deployment of the **research service**, not approval to release an accurate combined detector, expose a public inference service, enable hosted verifiers, or publish the extension.

## Connect the extension

Set its server origin to:

```text
https://slop-detection.dimensionlab.net
```

Retrieve the server token **privately**, never through a chat message, screenshot, repository file, URL, or command-line argument. On your Mac, this copies it directly from the protected server file to your clipboard without printing it:

```sh
ssh gpu 'sudo -n cat /etc/x-slop-detector/api-token' | pbcopy
```

Paste into the extension's masked token field, Test, then Save. Clear the clipboard after pasting. The extension is **not installed into your normal Chrome profile automatically**; see [installation](extension.md#install-and-connect).

Use your private AdGuard DNS/routing for this name. A browser configured to bypass it with a public-only Secure DNS resolver may see NXDOMAIN even while the LAN service is healthy.

The service was intentionally left **manually paused with all models unloaded**. Press **Load** to resume it, and enable client-local scanning when you want to submit visible own-post text. Unload pauses every client; scanning off alone does not unload the server.

The root URL is not a web dashboard. API paths are authenticated; an unauthenticated `/v2/status` returning **401** means HTTPS/routing reached the API successfully.

## Actual routing and exposure

```text
AdGuard on network-core
  slop-detection.dimensionlab.net → 192.168.2.252
Chrome → trusted HTTPS :443 on GPU host's existing Caddy
  → private-source filter → 127.0.0.1:18767 → non-root API → pinned RTX 3060
```

- Added **one** AdGuard rewrite; the previous 43 rewrites and other YAML settings were preserved.
- Reused the GPU host's existing Caddy and `cloudflare_tls` DNS-01 snippet. No Cloudflare credential was copied into this project, and no second proxy was added on `network-core`.
- The certificate is browser-trusted and hostname-verified, observed expiry **30 January 2027, 18:32:20 UTC**. DNS-01/ACME and public certificate transparency expose the certificate hostname, **not submitted posts**. No public A/AAAA record was created; a public resolver still returned NXDOMAIN.
- Caddy checks the **actual socket peer**, not client-provided forwarding headers. Allowed: exact IPv4/IPv6 loopback, LAN `192.168.2.0/24`, LAN ULA `fd4c:4b32:3031::/64`, and Tailscale ranges `100.64.0.0/10` / `fd7a:115c:a1e0::/48`. Other sources receive **403**, before proxying.
- The API binds **only `127.0.0.1:18767`**, requires its Bearer token on every endpoint, and exposes only `/v2/*`, `/health`, `/ready` through this site. Legacy v1 is not exposed through the proxy.
- Existing 80/443 listeners were reused. **No firewall port was opened, no public DNS address was added, and no global Tailscale DNS/ACL/subnet-route setting was changed.**
- On a remote Tailscale client, the AdGuard LAN address requires the existing LAN subnet route/split-DNS arrangement. HTTPS over the GPU's Tailscale address was tested between `network-core` and `gpu` with the correct hostname. A particular off-LAN phone/laptop's DNS and routing were **not** tested; do not infer that this deployment changes its VPN configuration.
- Proxy access output is discarded; Uvicorn access logging is off. Operational logs contain startup/model metadata and sanitized errors, not default request-body collection. The service has no application text/result persistence enabled.

The [Caddy site](../deploy/slop-detection.caddy#L1), [systemd unit](../deploy/x-slop-detector.service#L1), and [launcher](../deploy/start-server.sh#L1) are reviewed, secret-free templates for this specific host.

## Installed state

| Asset | Location / behavior |
| --- | --- |
| Service | `x-slop-detector.service`, enabled at boot; runs as dedicated non-login user/group `xslop`, not root. |
| Code artifact | `/opt/x-slop-detector/current` → `releases/e07d98fb61bfded3`; installed wheel contents verified against the artifact. |
| Final wheel SHA-256 | `e07d98fb61bfded307fdab99e0a86b4e4aecc18ec6ff38a2f92eeb128d73beb0` |
| Python environment | `/home/xslop/venv`, independent copy of the previously tested Linux dependencies, with the new wheel installed and no editable-source dependency. It is **not** a clean/hash-locked dependency rebuild. |
| Model cache | `/home/xslop/models/hub`, copied public model cache only; no user HF token copied. Environment and models are root-owned/read-only to the runtime. |
| Credential | `/etc/x-slop-detector/api-token`, root-only mode `0400`, generated on the server and supplied via systemd `LoadCredential`; not printed in the deployment output. |
| Pause state | `/var/lib/x-slop-detector/manual-pause.json`, runtime-writable and preserved across restart. |
| Runtime caches | `/var/cache/x-slop-detector`; separate from immutable model artifacts. |
| Caddy site | `/etc/caddy/conf.d/slop-detection.caddy`; existing main config and other site files unchanged. |
| AdGuard backup | `/var/lib/adguardhome/AdGuardHome.yaml.before-slop-20261101T193221Z`, root-only; contains private pre-change configuration, **never copy into the repository**. |
| GPU | UUID `GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db`, sole visible CUDA GPU. Identity verified before allocating weights. |
| Runtime policy | One worker, four CPU threads / 400% CPU quota, 16 GiB memory high / 20 GiB max, bounded execution, ten-minute idle expiry. |

The unit uses protected filesystem/home mounts, no extra capabilities, no-new-privileges, offline model loading, and systemd network policy allowing loopback only. These restrictions deliberately exclude future hosted calls/model downloads; changing them requires operator review, not a browser toggle. GPU device access remains available because the process needs the selected NVIDIA device.

All four native detectors are present. Local KGW remains **unsupported without matching operator configuration**; all hosted routes remain disabled/not connected. There is no calibrated scoring profile, so the extension still shows **`—`**, not percentages.

## Validation and bounded results

### DNS, TLS and isolation

- Private AdGuard A response resolves to `192.168.2.252`; no rewritten AAAA address. Public resolver A response NXDOMAIN.
- Trusted TLS chain and hostname verification succeeded from the Mac and over Tailscale between the two servers.
- No token → **401**; correct token → **200** metadata.
- A non-allowlisted loopback source with a **valid token and spoofed LAN `X-Forwarded-For`** → **403**.
- A real connection from the network host's global IPv6 address to the GPU host's global IPv6 address → **403**.
- Backend socket verified loopback-only. Existing Caddy host inventory preserved: 41 prior host matches retained, only the new hostname added.
- AdGuard backup/edit/check/start transaction measured **0.189 s**. That is transaction duration, **not a measured bound on DNS outage**. Its `reload` command only refreshes runtime-client/TLS data; it was not incorrectly treated as a rewrite reload. Admin API authentication was not bypassed or reset.

### Actual runtime and browser

- **69 Python tests passed on Linux** in the installed dependency environment; locally **65 passed and four optional inference tests skipped**. Includes three deployment guardrails and two cold-import/memory-observation regressions. **30 Node client tests passed.**
- Built/installed wheel contents matched the local runtime sources and deployed artifact. Service unit verification and real Caddy config validation passed.
- The first real prewarm exposed a status observation race: `sys.modules["torch"]` can be present before its CUDA attribute exists. Fixed by the shared [already-initialized CUDA observation guard](../detector_server/adapters.py#L20), used by status and unload; no heavy import is introduced into metadata.
- On the fixed service, [`smoke_private_deployment.py`](../scripts/smoke_private_deployment.py#L1) passed through the actual private DNS/HTTPS endpoint with real models: **94 status polls, zero poll errors**, about **9.231 s** cold prewarm, **0.558 s** one-post HTTPS inference, and **4.138 s** inference including lazy reload after idle release. Synthetic public text only; no accuracy label.
- Idle expiry was bounded with a **temporary three-second systemd runtime override**, then removed. The normal **600-second** policy was restored and verified after restart; a complete ten-minute wall-clock expiry was not separately waited out.
- [`smoke_deployed_extension.cjs`](../scripts/smoke_deployed_extension.cjs#L1) passed in **Google Chrome 156.0.8078.74**, actual unpacked MV3/action popup → private HTTPS → real **3060**, using an intercepted synthetic X page. Four native results completed; KGW unsupported, aggregate no-estimate, header `—`, actual Load/Unload. This is no longer merely the earlier synthetic-adapter browser smoke.
- Native permission-prompt accept/deny and **live X** remain manual checks. Chrome used a private disposable profile, not the user's normal profile; its host grant was set through Chrome's settings for automation. The deployed-browser smoke requires `$DELTA_SCRATCH_DIR` because that temporary profile contains the real operator token; do not archive/share it.
- Manual pause survived an actual service restart. After final restart, service active/enabled, idle 600 s, pause true, all models unloaded, no initialized CUDA context, **3060 15 MiB aggregate**.
- The 3090's existing ComfyUI process PID 3206 increased from 5800 to 17736 MiB during this work; PID 3209 remained 256 MiB. Its final aggregate was **18041 MiB**. The detector process was observed **only on the 3060**; do not incorrectly report the 3090's memory as unchanged.

Temporary service stop/restart windows produced expected brief **502** proxy responses during rollout checks. They are distinct from the cold-import **503** bug, which was fixed and tested with uninterrupted cold-load status polling. The persistent endpoint is healthy after rollout.

### Reproduce deliberately

These are **real inference/control tests**, not passive health checks. They require an otherwise quiet, manually paused service and finish with shared Unload:

```sh
.venv/bin/python scripts/smoke_private_deployment.py
node scripts/smoke_deployed_extension.cjs
```

The second command also requires installed Google Chrome, the pinned npm dev dependencies, and `DELTA_SCRATCH_DIR` set to private temporary storage. Neither script retrieves collected posts or calls a hosted verifier. Do not run them during another client's analysis.

## Operations, credential rotation and rollback

Non-secret checks:

```sh
ssh gpu 'systemctl is-active x-slop-detector; systemctl is-enabled x-slop-detector'
curl -i https://slop-detection.dimensionlab.net/v2/status
ssh gpu 'sudo journalctl -u x-slop-detector -n 50 --no-pager'
```

The `curl` request should return 401 without authentication. Browser clients need private DNS/routing as described above. Restarting this service preserves pause but temporarily interrupts its API; it does not restart Caddy, DNS, or other GPU applications.

To rotate authentication, generate a new token **on the server**, atomically replace the root-only token file with mode `0400`, restart **only** `x-slop-detector`, then privately update clients. Never paste the token into a command argument, repository, issue, or chat. Restart is required to reload systemd's credential copy.

To withdraw this deployment, deliberately:

1. `sudo systemctl disable --now x-slop-detector` on `gpu`.
2. Move **only** `/etc/caddy/conf.d/slop-detection.caddy` to a name that does not end in `.caddy`, validate the remaining Caddy config with its existing environment, then reload Caddy. Keep all unrelated sites untouched.
3. Remove **only** the `slop-detection.dimensionlab.net` rewrite through the authenticated AdGuard UI/operator workflow. Do not blindly restore the full backup if unrelated settings have changed since deployment.
4. Retain the private credential/state, wheel and dependency/cache copies until rollback is verified. Deleting them is a separate destructive cleanup, not necessary to make the API unreachable.

The first wheel is retained as rollout history, but it contains the cold-import bug; it is **not** the recommended rollback target. Stop/remove this new service route rather than reintroducing a known bug.

No machine reboot, certificate-renewal cycle, sustained/hostile load, phone/off-LAN DNS path, live X, hosted-provider access, corpus benchmark or calibrated probability was validated. **Private operational availability is not completion of the accurate-detector product.**
