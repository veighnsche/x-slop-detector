# Historical single-detector server prototype

**Historical record, not current launch/lifecycle instructions.** The [multi-detector runtime](suite-runtime.md) is now implemented and tested through the v2 API. V1 projects legacy Tabularis diagnostics from that same suite. The older single-model behavior/timings below are retained as evidence of the initial prototype; do not substitute them for whole-suite measurements or current shared controls.

The [v2 contract](v2-api.md) documents the current wire format, including [conditional CPU watermark verification](watermark-routes.md), now used by the [Chrome research client](extension.md) through the separately authorized [private HTTPS service](private-deployment.md). Hosted provider verification, calibrated probability, and completed-product release remain unimplemented. Historical no-deployment statements below describe only the original prototype tests.

## Percentage contract

This section describes the existing **single-model prototype**. The [proposed product score](score-definition.md) targets substantive generated/rewritten wording with validated evidence combination; it is not implemented and cannot be obtained by renaming this field.

The pinned Tabularis binary classifier returns logits for human (index 0) and AI (index 1). The initial percentage is:

$$
s_{\mathrm{AI}} = \frac{\exp(z_{\mathrm{AI}})}{\exp(z_{\mathrm{human}})+\exp(z_{\mathrm{AI}})}, \qquad
\text{displayed estimate} = \operatorname{round}(100s_{\mathrm{AI}}, 1)
$$

Implementation uses numerically stable softmax. This is an **uncalibrated AI-class model estimate**, not the fraction of words AI wrote, a watermark result, or independently established P(AI authorship). Do not describe “72%” as “72% of the words are AI-generated.” The API returns both the raw `ai_score` and rounded `ai_percentage`, alongside `score_kind: uncalibrated_ai_class_probability` and `calibrated_for_x: false`.

Every successful result carries `not_validated_for_short_x_posts`. Short text is not padded with other posts. Blank text and posts above the model's 512-token evaluation limit are rejected, not scored as human; long inputs are not silently truncated. Requests are atomic batches: an overlength post rejects its batch. Errors never produce a percentage.

There is no invented probability correction, ensemble, or certainty threshold. A production probability claim requires the [length-bucketed holdout/calibration evaluation](evaluation.md), including relevant prevalence, mixed-writing definitions, and unseen generators. These scores can support an explicitly experimental client, not a claim of validated authorship confidence.

## Model residency and buttons

- Startup allocates no detector weights and does not import PyTorch.
- The first detection request loads the model; subsequent requests reuse it.
- Default idle timeout is **600 seconds**, measured from the end of inference or a manual Load request. Polling status does not keep the model warm.
- Idle expiry frees model/tokenizer references, runs garbage collection, and releases unused CUDA allocator blocks. Downloaded weights remain cached on disk. The CUDA context can retain some VRAM until process exit: “unloaded” does not promise zero process VRAM.
- **Load** calls `POST /v1/model/load`: load/prewarm, or reset the idle timer if already loaded; also resume after a manual unload.
- **Unload** calls `POST /v1/model/unload`: unload and **pause automatic detection** until Load is pressed. Otherwise background scans would immediately undo the unload. Idle unload does not pause automatic loading.
- `GET /v1/model` exposes `state` (`unloaded`, `loading`, `ready`, `unloading`, `error`), `busy`, `paused`, timeout, and idle countdown. A future client can show the two buttons and a loading spinner from this endpoint.
- One operation owns the model at a time. Concurrent work, including unload during inference, gets **409** with `Retry-After: 2`; it cannot interrupt inference. The client should disable busy controls, batch visible posts, and retry with bounded backoff. There is no unbounded inference queue.

Manual pause is server-wide, not per browser. That is intentional for a personal server. Independent users would need a separate scheduling/ownership design.

## Installation on Linux

Python **3.11+**, compatible NVIDIA drivers, and enough free VRAM are required. **Use the otherwise idle RTX 3060 for this detector**, preserving the active RTX 3090 for other workloads. The real test used under 1 GiB on the 3060 with no material short-batch latency disadvantage observed. No multi-GPU splitting or system service is installed automatically.

From the repository:

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[inference,test]'
```

The inference extra installs PyTorch/Transformers. Select the appropriate PyTorch CUDA wheel for the machine if the default package does not match its driver/runtime. Dependency versions are bounded but not locked; record the working GPU environment before production deployment.

**Select the GPU by UUID for this host.** CUDA's ordinal order differed from `nvidia-smi` during testing; `CUDA_VISIBLE_DEVICES=1` selected the 3060, not the 3090. Run `nvidia-smi --query-gpu=name,uuid --format=csv`, set `CUDA_VISIBLE_DEVICES` to the desired GPU UUID, and use `DETECTOR_DEVICE=cuda:0` for that now-single visible GPU. Verify with `torch.cuda.get_device_name(0)` before allocating weights.

Set these variables in your shell or a protected deployment environment, **not in a committed file**:

| Variable | Meaning |
| --- | --- |
| `DETECTOR_API_TOKEN` | Required random secret, at least 24 non-whitespace ASCII characters. Supply it privately; don't paste it into this repository or chat. |
| `DETECTOR_DEVICE` | Default `cuda:0`; use `cpu` for a CPU test. CUDA unavailability fails explicitly rather than silently using CPU. |
| `DETECTOR_IDLE_SECONDS` | Default `600`; use `3` for the lifecycle smoke test. Minimum 1 second. |
| `HF_HOME` | Optional persistent model-cache directory. Keep this outside the source tree or in ignored `models/`. |
| `CUDA_VISIBLE_DEVICES` | Optional PyTorch GPU selection; device indices are remapped after applying this variable. |

Start a **single worker**:

```sh
CUDA_VISIBLE_DEVICES=GPU-744c1cf5-9578-6aad-95c1-7a6f1c9d11db DETECTOR_DEVICE=cuda:0 \
.venv/bin/uvicorn detector_server.app:create_app --factory \
  --host 127.0.0.1 --port 8765 --workers 1 --no-access-log \
  --limit-concurrency 32 --timeout-keep-alive 5
```

The UUID above explicitly selects the **3060 on `linux.dimensionlab.net`**, not the 3090. Substitute the correct UUID on other machines. Port 8765 was already occupied on this host during testing; choose a free loopback port rather than stopping the existing listener.

Do not use multiple workers: each worker has its own residency state and can allocate another model copy. First load downloads approximately 600 MB of weights plus tokenizer/config files from Hugging Face. The adapter pins revision `4bf4a146a66df346e5b54e4b5ebda3fee1a19a86`, uses safetensors, disables remote code execution, and uses FP32/eager attention initially. Raw author text is scored without normalization. This is not byte-for-byte reproduction of the model card's normalized BF16 CUDA example.

The model is fixed intentionally: replacing a checkpoint requires reviewing its label mapping, preprocessing, limits, and licensing in a detector adapter, not merely changing a model name.

## API

All endpoints, including health/status, require `Authorization: Bearer <your token>`.

| Method/path | Behavior |
| --- | --- |
| `GET /health` | Process liveness; does not load a model. |
| `GET /ready` | 200 only when loaded and not busy; 503 otherwise. Do not use this as a process restart probe, since idle unload is normal. |
| `GET /v1/model` | Residency/control state and pinned model/device information. |
| `POST /v1/model/load` | Explicit prewarm/resume. |
| `POST /v1/model/unload` | Explicit unload/pause. |
| `POST /v1/detect` | Score 1–16 independently tokenized posts. |

Detection body:

```json
{
  "posts": [
    {"id": "post-123", "text": "The author's own post text"}
  ]
}
```

Results preserve input IDs/order and include `ai_score`, `ai_percentage`, token count, and warnings. IDs must be unique per batch. Maximum body is 128,000 bytes; each text is capped at 10,000 characters before tokenization. Status codes: 401 invalid/missing token, 409 busy/manually paused, 413 body too large, 422 invalid fields/overlength tokens, 503 detector failure.

No application post-text persistence, telemetry, or result cache is implemented. Validation errors do not echo submitted text. Uvicorn access logging is disabled in the recommended command; reverse-proxy logs must also avoid tokens/bodies. HTTPS is required outside loopback, via a deliberately configured proxy/private network. Set connection/body timeouts and external rate limits there. Bearer authentication and bounded work are not a substitute for internet-facing abuse controls.

Do not expose port 8765 publicly for the first test. An SSH tunnel or private network is sufficient. A future Chrome extension should make authenticated requests from its background worker with host permissions only for the configured server; no permissive CORS policy is enabled here.

## Validation and remote test

Local deterministic tests (fake backend; no weights/GPU required):

```sh
.venv/bin/python -m unittest discover -s tests -v
```

For a real GPU smoke test, start an **isolated fresh server** with `DETECTOR_IDLE_SECONDS=3`, privately supplied token, and the inference extra installed. In a second shell with the same token:

```sh
DETECTOR_URL=http://127.0.0.1:8765 .venv/bin/python scripts/smoke_server.py
```

The smoke test performs real batch inference, verifies score arithmetic, manual unload/pause/resume, idle expiry, and automatic reload. It leaves the test instance unloaded/paused. It is **not an accuracy benchmark**. Compare `nvidia-smi` before load, while ready, and after unload to check actual VRAM release. Stop only the isolated test process when done.

### Verified GPU run

The earlier SSH reachability failure cleared. The server was subsequently staged and tested through `ssh gpu` on `linux.dimensionlab.net`, as user `vince`, without root or changes to existing services. The first run used the **RTX 3090**; a follow-up repeated the real-model lifecycle checks on the **RTX 3060**, which is now the recommended deployment GPU. Both were selected explicitly by UUID.

Environment: Python **3.12.15**, NVIDIA driver **615.71.10**, PyTorch **2.15.0+cu132** / CUDA **13.2**, Transformers **5.22.1**, FastAPI **0.162.0**. The pinned checkpoint loaded successfully with the existing FP32/eager adapter; no adapter fix was needed.

Checks passed:

- All **12 deterministic API/lifecycle tests** on the Linux host.
- The exact real-model command `.venv/bin/python scripts/smoke_server.py`, with a fresh isolated server, private ephemeral token, and a 3-second idle timeout.
- Real batch inference and score arithmetic; manual unload/pause/resume; idle expiry; automatic reload.
- An additional real 512-token overflow rejection (422).
- The same short post scored alone and in a padded two-post batch returned identical AI scores in this check.

Measured over loopback HTTP, while unrelated GPU applications remained running:

| Measurement | Observed |
| --- | --- |
| Cached-weight reload into an already initialized process | **499.61 ms** |
| Batch of 1 short post, median of 5 requests | **18.52 ms** |
| Batch of 2 short posts, median of 5 requests | **21.11 ms** |
| Batch of 16 short posts, median of 5 requests | **21.58 ms** |
| Manual unload | **160.94 ms** |
| Detector process VRAM before first load | **0 MiB** |
| Detector process VRAM loaded / after inference | **920 / 926 MiB** |
| Detector process VRAM after manual unload | **310 MiB** |
| Detector process VRAM after exit | **0 MiB** |

These latency samples alternate just two short texts; they are not a load test, full-length input benchmark, accuracy evaluation, or remote-client network measurement. One initial batch-of-one request took 73.83 ms; the median must not be interpreted as a worst case. The 21.96-second full lifecycle smoke run included initial download/loading and several lifecycle transitions; first-download latency was not separately timed.

The remaining 310 MiB after unload is process/CUDA overhead, not retained model weights. If releasing **all** process VRAM without stopping the API becomes a requirement, move inference into a disposable worker process; that is not implemented yet.

The isolated test instance used loopback port **42631** and was **stopped after testing**. The pre-existing listener on 8765 and both existing ComfyUI processes remained in place, with aggregate GPU memory returning to its initial readings. No public port, TLS proxy, system service, persistent token, or production deployment was created.

Remote staging artifacts remain at `/home/vince/x-slop-test.Tsn5iXQm` for reuse: source snapshot, isolated `.venv`, model cache, `gpu-test-server.log`, `gpu-test-results.json`, and `gpu-test-requirements.txt` with resolved dependency versions. The venv occupies about 5.4 GiB and the model cache 575 MiB as reported by `du -sh` (some dependency files can share cache storage). The test token existed only in process memory/environment and was not written into these artifacts. This folder is a test snapshot, not a Git checkout or a deployed service.

### RTX 3060 follow-up

Using the same environment, checkpoint, samples, and measurement approach, the RTX 3060 passed `.venv/bin/python scripts/smoke_server.py`, overlength rejection, and the singleton-versus-padded-batch score check.

| Measurement | RTX 3060 | Earlier RTX 3090 run |
| --- | --- | --- |
| Cached-weight reload | **656.12 ms** | 499.61 ms |
| Batch of 1, median of 5 | **18.22 ms** | 18.52 ms |
| Batch of 2, median of 5 | **20.84 ms** | 21.11 ms |
| Batch of 16, median of 5 | **21.55 ms** | 21.58 ms |
| Manual unload | **155.56 ms** | 160.94 ms |
| Process VRAM after inference | **748 MiB** | 926 MiB |
| Process VRAM after unload | **132 MiB** | 310 MiB |
| Process VRAM after exit | **0 MiB** | 0 MiB |

These small sequential measurements do not establish that one GPU is faster; they show no practical reason to occupy the active 3090 for this tested workload. The earlier caveats about accuracy, short samples, load testing, and warm-up still apply.

The 3060 test used loopback port **57521** and was stopped afterward. Additional artifacts are `gpu-test-3060-server.log` and `gpu-test-3060-results.json` in the same staging directory. No production service or persistent GPU reservation was created.
