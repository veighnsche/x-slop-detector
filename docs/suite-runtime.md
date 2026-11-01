# Multi-detector server and shared residency

**Implemented and tested:** phase 2 added **Tabularis + E5 + Fakespot + single-Neo Fast-DetectGPT**, with TMR as challenger. Later work added [conditional CPU watermark routes](watermark-routes.md), the [Chrome research client](extension.md), and a separately approved [private HTTPS deployment](private-deployment.md). This remains an evidence service, **not calibrated authorship probability, general provider verification, or a completed-product release**. The measurements below preserve the phase-2 study.

## Execution and evidence

The selected four models are co-resident while active and execute **sequentially**, one post at a time. One process owns one bounded analysis slot; additional requests get 409 rather than joining an unbounded queue. Per-post execution bounds GPU intermediates even for 16 near-limit posts. This deliberately differs from the earlier batched diagnostic timings.

- Encoders: pinned weights, FP32, eager attention, index 1 AI-class score.
- Statistical path: pinned Neo FP16, same model/logits in both method roles, batch size one, raw analytic discrepancy. A vendored MIT function avoids downloading/executing research source at request time; its only mathematical modification is an explicit non-finite/near-zero variance guard. Invalid variance produces `insufficient_evidence`, not an invented probability.
- All inputs remain raw and independently tokenized. Per-check **512-token cap**, no silent truncation or content-removing cleaning. One-token Neo input is insufficient; other checks/posts retain their own outcomes.
- No averaging or calibration is enabled. Every aggregate is `no_estimate`; probability readiness remains false.
- CPU and CUDA configurations have distinct component/configuration identities. CPU Neo FP16 is **not** numerically interchangeable with GPU Neo.
- No hidden GPU/CPU fallback, quantization, offload, multi-GPU splitting, or arbitrary HTTP-selected models.
- Optional KGW is now a fifth evidence slot, unsupported when unconfigured. `/v2/watermarks` uses the same ownership/pause/idle lifecycle without loading the four classifiers. See [scope/configuration](watermark-routes.md).

Ordinary invalid/erroring checker results preserve other native evidence and explicit failed statuses; the suite is then released and the failed component marked error. Partial load failure cleans every adapter, including partially allocated ones. OOM releases the whole suite and returns 503 `resource_exhausted`; it never silently shrinks the roster. Cleanup failures remain visible and must succeed before subsequent loading.

## Shared controls and persistence

`POST /v2/control` accepts `{"schema_version":"2","action":"load"}` or `"unload"`. It returns 200 when already completed or **202 pending** for background work. Poll `/v2/status`; no separate job queue or websocket is required.

- **Load:** persist resumed intent, clear manual pause, and prewarm the selected suite. Repeated Load while that load is pending is idempotent. An authenticated analysis request otherwise lazy-loads on demand.
- **Unload:** immediately latch shared pause and persist it, reject new analysis, wait for already-owned work to finish safely, then release every local model/tokenizer. Repeated Unload is idempotent. Unload can supersede a pending prewarm; Load cannot undo a pending unload and receives 409.
- **Idle expiry:** default 600 seconds after completed analysis/prewarm; release without manual pause, so a later request can reload. Status/health polling does not extend this timer.
- **Cancellation/shutdown:** client cancellation cannot release residency while an uncancellable worker still runs. Shutdown waits for control/inference ownership before cleanup.
- **Restart:** non-secret manual pause is stored atomically in the operator's state directory. Corrupt/unreadable state fails closed (paused). A write failure still allows Unload to release models, but exposes `pause_persisted: false` and `state_persistence_failed`; fix storage before relying on pause across a restart. Load cannot resume when it cannot persist resumed intent.

Status includes required component states, shared `paused`/`busy`, operation, `pending_control`, sanitized `last_error`, verified GPU UUID, idle countdown, and optional live/peak PyTorch memory counters. It never imports/initializes CUDA merely to answer metadata. Zero allocator counters do **not** mean zero process VRAM.

### Legacy compatibility without a second model owner

V1 retains its legacy Tabularis numeric response shape and uncalibrated labeling, but the default factory now projects those diagnostics from the **same suite**, not a second independently loaded Tabularis process. V1 analysis therefore executes the selected suite. V1 Load/Unload wait for the shared control operation; v2 exposes asynchronous progress. Either API's Unload pauses all clients. The old standalone fake-backend tests remain injection-only.

## Configuration and safe local launch

Python 3.11+ and the inference extra are required for real models. Use a compatible PyTorch CUDA wheel and record the environment; `requirements/linux-cu132-observed.txt` is the exact observed Linux package-version snapshot, **not a hash lock or proof of clean installation on every machine**. Do not sync that Linux-specific file into a macOS or unrelated CUDA environment.

| Variable | Meaning |
| --- | --- |
| `DETECTOR_API_TOKEN` | Required private server credential, at least 24 non-whitespace ASCII characters. Never commit it or place it in command logs. |
| `DETECTOR_DEVICE` | `cuda:0` for the sole UUID-selected GPU, or explicit `cpu`. No automatic fallback. |
| `DETECTOR_GPU_UUID` | CUDA target UUID. If omitted, an exact single UUID in `CUDA_VISIBLE_DEVICES` supplies it. |
| `CUDA_VISIBLE_DEVICES` | Must equal that **single GPU UUID** before startup. Numeric ordinals, multiple devices, mismatches, and unverifiable device identity fail before model loading. |
| `DETECTOR_IDLE_SECONDS` | Default 600; use 3 only for the smoke test. |
| `DETECTOR_STATE_DIR` | Stable operator-writable directory for manual pause; default `.cache/detector-state` under the working directory. Keep it across restarts. |
| `DETECTOR_ROBERTA` | Default `fakespot`; explicit `tmr` replaces that slot for challenger experiments and changes the suite identity. No fitted scoring profile exists for either. |
| `DETECTOR_WATERMARK_CONFIG` | Optional bounded server-only JSON policy; default no matching local configuration and all provider routes disabled. See [watermark configuration](watermark-routes.md#server-only-configuration). |
| `HF_HOME` | Model cache. Offline testing can use `HF_HUB_OFFLINE=1` once pinned artifacts are cached. |
| `OMP_NUM_THREADS` | Set deliberately for host/CPU testing; this run used 4. |

After privately supplying the token and choosing a protected state/cache directory, an example **loopback-only** launch for this host is:

```sh
CUDA_VISIBLE_DEVICES=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db \
DETECTOR_GPU_UUID=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db \
DETECTOR_DEVICE=cuda:0 OMP_NUM_THREADS=4 \
.venv/bin/uvicorn detector_server.app:create_app --factory \
  --host 127.0.0.1 --port 18767 --workers 1 --no-access-log \
  --limit-concurrency 32 --timeout-keep-alive 5
```

Choose an unused port; do not stop an existing listener. The UUID is the **3060 on linux.dimensionlab.net**, not portable to other hosts. Verification checks actual CUDA device properties against it before allocation. **Run one worker/process only**; multiple independent server processes are unsupported and would not share the in-memory execution slot. The historical phase-2 test did not install a service/proxy/secret. **The subsequent private deployment now owns port 18767**; do not start a second model-owning test process alongside it without deliberately coordinating GPU use.

The [v2 contract](v2-api.md) specifies request limits, native output meanings, status, and errors. The [private deployment runbook](private-deployment.md) records the separately authorized service, HTTPS/security policy, and operations. Public/product release is not authorized.

## Recorded validation

Executed via `ssh gpu` in a fresh **non-Git isolated directory** `/home/vince/x-slop-v2-test.Gs25Eo`, using the pre-existing test venv/cache without changing its dependencies or existing services. Python 3.12.15, torch 2.15.0+cu132, Transformers 5.22.1, driver 615.71.10; offline artifact loading. Synthetic public inputs only, no accuracy labels or submitted user posts.

### Tests and workflows

- `.venv/bin/python -m unittest discover -s tests -v`: **49 passed on Linux**. Locally, 47 passed and the two optional torch numerical tests were skipped. These include fake-adapter partial loads, inference/unload failures, simulated OOM, corrupt/unwritable pause state, competing controls, cancellation, shared v1/v2 clients, idle expiry, and shutdown.
- Real Uvicorn + HTTP API: lazy loading, all four native outputs, explicit no-estimate, per-check overlength/one-token admission, repeat analysis, competing requests (200/409), Unload during inference, cancelled network client followed by safe unload, manual resume, idle release/reload, v1/v2 shared pause, and persisted pause after actual process restart.
- Real TMR-replacement and explicit CPU suite each returned all four native outputs for a synthetic input. CPU Neo was `−0.10144043` versus GPU `−0.09722900` for that input—configuration identity must remain distinct. These are repeatability observations, not accuracy labels.
- Wheel build passed and inspection confirmed the runtime and vendored MIT license are packaged.

### Bounded measurements from the final default-roster HTTP smoke

| Measurement | Observed |
| --- | --- |
| First lazy load plus two-post response, populated artifact cache | **7.343 s** |
| Three warm two-post loopback requests | **180.89 / 180.14 / 178.87 ms** |
| 16 near-limit posts, all four outputs per post | **3944 ms** |
| Near-limit input counts (Tabularis/E5/Fakespot/Neo) | **493 / 492 / 493 / 491 tokens** |
| Process VRAM after short inference | **6838 MiB** |
| Process VRAM sampled after near-limit batch | **7142 MiB ≈ 6.97 GiB** |
| PyTorch peak allocated / reserved during that process | **6938281984 / 7342129152 bytes** |
| Allocated / reserved after manual and idle release | **0 / 0 bytes** |
| Residual process VRAM after release | **140 MiB**, removed on process exit |

Unlike the earlier probes, these timings include real loopback HTTP/validation/control machinery. They exclude internet latency/Chrome and are bounded samples, **not a throughput, maximum latency, or universal memory guarantee**. Single-post model execution trades some short-batch speed for a straightforward bounded memory rule.

Before and after all test processes, the 3060 was **15 MiB** aggregate and the 3090 **6105 MiB**, with the same existing ComfyUI PIDs 3206/3209. All temporary API processes were stopped. No active-3090 model allocation was observed.

Raw remote artifacts: `api-current.json`, `api-max.json`, `api-final-{1,2}.json`, `api-{tmr,cpu}.json`, `server-*.log`, `smoke-*.log`, and pause-state directories. The table uses `api-current.json` from the final source, including the 16-near-limit check; earlier intermediate runs remain separately. Source snapshot and cached model dependencies remain available there/at the earlier cache location.

Canonical local/remote source inventories matched SHA-256 `b59f529b127dcdb7d503573fb0df1ab84843ae8247361f60099b39a33b28c936`: sorted paths plus bytes for runtime Python, vendored license, tests, the suite smoke script, and `pyproject.toml`. macOS AppleDouble archive metadata on the initial remote copy was excluded from this source inventory; it is not imported Python source.

### Reproduce the HTTP smoke

Against a fresh isolated loopback server with `DETECTOR_IDLE_SECONDS=3`, a separate state directory, populated model cache, and the privately supplied matching token:

```sh
DETECTOR_URL=http://127.0.0.1:18767 \
.venv/bin/python scripts/smoke_suite_server.py --output api-smoke.json
```

The script requires `DETECTOR_GPU_UUID` and uses synthetic text. It deliberately leaves the server **manually paused/unloaded**. Restart that server with the same state directory and run:

```sh
DETECTOR_URL=http://127.0.0.1:18767 \
.venv/bin/python scripts/smoke_suite_server.py --restart-only --output api-restart.json
```

Use authenticated Load to resume after testing. Optionally supply `DETECTOR_SERVER_PID` to record its `nvidia-smi` process usage; status always exposes allocator counters after CUDA initialization.

## Boundaries still open

Conditional local KGW, the Chrome research client, and a private operational HTTPS deployment are now implemented and tested separately; no hosted verification, fusion/calibration, corpus benchmark, or completed-product release exists. Driver failure, actual forced hardware OOM/competing VRAM, prolonged traffic, and an independently rebuilt inference environment were **not** tested. OOM tests used injected failures rather than destabilizing the host. Both launch gates remain intact.
