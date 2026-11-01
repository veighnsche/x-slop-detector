"""Bounded operational probe, NOT a production adapter or accuracy benchmark.

Run only in an isolated test directory on the intended RTX 3060. Uses synthetic
text, pinned public artifacts, one GPU, four CPU threads, and no hosted detector.
The reference statistical function is extracted from reviewed, pinned MIT source.
No fusion score or model-selection decision is produced.
"""

import argparse
import ast
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time
import urllib.request

ARTIFACTS = {
    "tabularis": ("tabularisai/ai-text-detection", "4bf4a146a66df346e5b54e4b5ebda3fee1a19a86"),
    "e5": ("MayZhou/e5-small-lora-ai-generated-detector", "483fc4969592dc20e00e5130e7187b5dd25dbcc7"),
    "fakespot": ("fakespot-ai/roberta-base-ai-text-detection-v1", "f9cdb14d1f8b105f597d80fa7b56f20c6ea0e9db"),
    "tmr": ("Oxidane/tmr-ai-text-detector", "0ceddea903015ef99cbaa040a4d8a216aed9c683"),
    "neo": ("EleutherAI/gpt-neo-2.7B", "e24fa291132763e59f4a5422741b424fb5d59056"),
}
REFERENCE_REVISION = "971b05202bac2bb504d60c0ac0812fea7a8f7c82"
SAMPLES = [
    "Yes.",
    "The train is late again. Anyone know what happened?",
    "lol that meeting could have been an email 😂",
    "今日は駅まで歩きました。雨が降っていました。",
    "Use `print('hello')` to test the script. Notes: https://example.com/test",
    "I walked to the market this morning, bought some bread, and forgot the apples. "
    "On the way home I stopped to watch a dog trying to carry a stick through a gate. "
    "The owner eventually turned the stick sideways. Nothing remarkable, just a nice morning.",
]


def validate(texts, lengths, limit=512, statistical=False):
    """Probe guards, not evidence that production adapters implement them."""
    if not texts or any(not text.strip() for text in texts):
        raise ValueError("blank_input")
    if any(length > limit for length in lengths):
        raise ValueError("overlength_input")
    if statistical and any(length < 2 for length in lengths):
        raise ValueError("insufficient_next_token_observations")


def timed(function, repeats=5):
    values = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = function()
        values.append(round(1000 * (time.perf_counter() - start), 3))
    return {"median_ms": statistics.median(values), "samples_ms": values}, result


def release(torch):
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()


def memory(torch):
    rss = next(
        line.split()[1] for line in Path("/proc/self/status").read_text().splitlines()
        if line.startswith("VmRSS:")
    )
    output = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory",
         "--format=csv,noheader,nounits"], text=True,
    )
    process_mib = 0
    for row in output.splitlines():
        pid, gpu_uuid, used = [value.strip() for value in row.split(",")]
        if pid == str(os.getpid()):
            if gpu_uuid != os.environ["CUDA_VISIBLE_DEVICES"]:
                raise RuntimeError("Probe allocated on unexpected GPU")
            process_mib = int(used)
    return {
        "process_vram_mib": process_mib,
        "allocated_mib": round(torch.cuda.memory_allocated() / 2**20, 2),
        "reserved_mib": round(torch.cuda.memory_reserved() / 2**20, 2),
        "peak_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20, 2),
        "peak_reserved_mib": round(torch.cuda.max_memory_reserved() / 2**20, 2),
        "host_rss_mib": round(int(rss) / 1024, 2),
    }


def load(name, device, torch, transformers):
    model_id, revision = ARTIFACTS[name]
    start = time.perf_counter()
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_id, revision=revision, trust_remote_code=False,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_class = (
        transformers.AutoModelForCausalLM if name == "neo"
        else transformers.AutoModelForSequenceClassification
    )
    model, loading_info = model_class.from_pretrained(
        model_id, revision=revision, trust_remote_code=False, use_safetensors=True,
        dtype=torch.float16 if name == "neo" else torch.float32,
        attn_implementation="eager", output_loading_info=True,
    )
    diagnostics = {
        key: [str(value) for value in loading_info.get(key, [])]
        for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")
    }
    if any(diagnostics[key] for key in ("missing_keys", "mismatched_keys", "error_msgs")):
        raise RuntimeError(f"Unresolved checkpoint loading diagnostics: {diagnostics}")
    if any(
        name != "neo" or not re.fullmatch(
            r"transformer\.h\.\d+\.attn\.attention\.(masked_bias|bias)", key
        )
        for key in diagnostics["unexpected_keys"]
    ):
        raise RuntimeError(f"Unexpected checkpoint tensors: {diagnostics}")
    model._probe_loading_info = diagnostics
    model = model.to(device).eval()
    if device == "cuda:0":
        torch.cuda.synchronize()
    return tokenizer, model, round(time.perf_counter() - start, 3)


def classifier(texts, tokenizer, model, torch, device):
    encoded = tokenizer(texts, truncation=False)
    validate(texts, [len(ids) for ids in encoded["input_ids"]])
    inputs = tokenizer.pad(encoded, padding=True, return_tensors="pt").to(device)
    with torch.inference_mode():
        logits = model(**inputs).logits
        if logits.shape != (len(texts), 2):
            raise RuntimeError("Unexpected binary classifier shape")
        scores = logits.float().softmax(-1)[:, 1].cpu().tolist()
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in scores):
        raise ValueError("nonfinite_classifier_result")
    return scores


def reference_criterion(torch, directory):
    base = f"https://raw.githubusercontent.com/baoguangsheng/fast-detect-gpt/{REFERENCE_REVISION}/"
    source = urllib.request.urlopen(base + "scripts/fast_detect_gpt.py", timeout=30).read()
    directory.mkdir(exist_ok=True)
    (directory / "fast_detect_gpt.py").write_bytes(source)
    (directory / "LICENSE").write_bytes(
        urllib.request.urlopen(base + "LICENSE", timeout=30).read()
    )
    function = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "get_sampling_discrepancy_analytic"
    )
    namespace = {"torch": torch}
    # Execute only the already-reviewed analytic function, not repository imports
    # or experiment code. Same one-model logits occupy both method roles.
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(directory), "exec"), namespace)
    return namespace[function.name], hashlib.sha256(source).hexdigest()


def statistical(text, tokenizer, model, criterion, torch):
    ids = tokenizer(text, truncation=False, return_tensors="pt", return_token_type_ids=False)
    validate([text], [ids.input_ids.shape[1]], statistical=True)
    ids = ids.to(model.device)
    with torch.inference_mode():
        logits = model(**ids, use_cache=False).logits[:, :-1]
        value = criterion(logits, logits, ids.input_ids[:, 1:])
    if not math.isfinite(value):
        raise ValueError("nonfinite_statistical_result")
    return value


def guard_checks(tokenizer, statistical_mode=False):
    results = {}
    cases = {"blank": "  ", "overlength": "test " * 2200}
    if statistical_mode:
        cases["one_token"] = "a"
    for name, text in cases.items():
        lengths = [len(tokenizer(text, truncation=False)["input_ids"])]
        try:
            validate([text], lengths, statistical=statistical_mode)
        except ValueError as error:
            results[name] = str(error)
        else:
            raise AssertionError(f"Expected rejection: {name}")
    return results


def probe_encoders(torch, transformers):
    records = {}
    for name in ("tabularis", "e5", "fakespot", "tmr"):
        print("PROBE", name, flush=True)
        tokenizer, model, initial = load(name, "cpu", torch, transformers)
        record = {"initial_cpu_load_seconds_including_any_download": initial}
        record["checkpoint_diagnostics"] = model._probe_loading_info
        record["token_counts"] = [len(tokenizer(text)["input_ids"]) for text in SAMPLES]
        record["cpu_batch2"], cpu_scores = timed(
            lambda: classifier(SAMPLES[1:3], tokenizer, model, torch, "cpu"), 3,
        )
        start = time.perf_counter()
        model.to("cuda:0")
        torch.cuda.synchronize()
        record["cpu_to_gpu_ms"] = round(1000 * (time.perf_counter() - start), 3)
        torch.cuda.reset_peak_memory_stats()
        record["gpu_first_batch2"], _ = timed(
            lambda: classifier(SAMPLES[1:3], tokenizer, model, torch, "cuda:0"), 1,
        )
        record["gpu_warm_batch2"], gpu_scores = timed(
            lambda: classifier(SAMPLES[1:3], tokenizer, model, torch, "cuda:0"),
        )
        record["cpu_gpu_max_score_difference"] = max(
            abs(a - b) for a, b in zip(cpu_scores, gpu_scores)
        )
        record["synthetic_scores_not_accuracy_labels"] = classifier(
            SAMPLES, tokenizer, model, torch, "cuda:0"
        )
        record["repeat_max_difference"] = max(
            abs(a - b) for a, b in zip(
                record["synthetic_scores_not_accuracy_labels"],
                classifier(SAMPLES, tokenizer, model, torch, "cuda:0"),
            )
        )
        record["gpu_warm_batch16"], _ = timed(
            lambda: classifier([SAMPLES[1], SAMPLES[2]] * 8, tokenizer, model, torch, "cuda:0"),
        )
        near_limit = tokenizer.decode(tokenizer("The train was late. " * 160)["input_ids"][1:490])
        record["near_limit_tokens"] = len(tokenizer(near_limit)["input_ids"])
        record["near_limit_gpu"], _ = timed(
            lambda: classifier([near_limit], tokenizer, model, torch, "cuda:0"), 3,
        )
        record["probe_guard_checks"] = guard_checks(tokenizer)
        record["after_inference"] = memory(torch)
        del model, tokenizer
        release(torch)
        record["after_unload"] = memory(torch)
        tokenizer, model, record["cached_gpu_load_seconds"] = load(
            name, "cuda:0", torch, transformers
        )
        del model, tokenizer
        release(torch)
        records[name] = record
        print(json.dumps({name: record}), flush=True)
    return records


def probe_suite(torch, transformers, reference_dir):
    criterion, source_sha = reference_criterion(torch, reference_dir)
    models = {}
    records = {"reference_source_sha256": source_sha, "loads": {}}
    try:
        for name in ("tabularis", "e5", "fakespot", "neo"):
            print("COEXIST LOAD", name, flush=True)
            tokenizer, model, seconds = load(name, "cuda:0", torch, transformers)
            models[name] = (tokenizer, model)
            del tokenizer, model
            records["loads"][name] = {
                "seconds_including_any_download": seconds, "memory": memory(torch),
                "checkpoint_diagnostics": models[name][1]._probe_loading_info,
            }
        torch.cuda.reset_peak_memory_stats()
        neo_tokenizer, neo_model = models["neo"]
        records["neo_guards"] = guard_checks(neo_tokenizer, statistical_mode=True)
        records["neo_short_first"], _ = timed(
            lambda: statistical(SAMPLES[1], neo_tokenizer, neo_model, criterion, torch), 1,
        )
        records["neo_short_warm"], score = timed(
            lambda: statistical(SAMPLES[1], neo_tokenizer, neo_model, criterion, torch),
        )
        records["neo_raw_discrepancy_not_probability"] = score
        repeated = statistical(SAMPLES[1], neo_tokenizer, neo_model, criterion, torch)
        records["neo_repeat_difference"] = abs(score - repeated)
        records["neo_synthetic_criteria_not_accuracy_labels"] = [
            statistical(text, neo_tokenizer, neo_model, criterion, torch) for text in SAMPLES
        ]

        def run(texts):
            output = {
                name: classifier(texts, *models[name], torch, "cuda:0")
                for name in ("tabularis", "e5", "fakespot")
            }
            output["neo_discrepancy"] = [
                statistical(text, neo_tokenizer, neo_model, criterion, torch) for text in texts
            ]
            return output

        records["suite_batch2"], output = timed(lambda: run(SAMPLES[1:3]), 3)
        records["suite_outputs_not_accuracy_labels"] = output
        records["suite_batch16"], _ = timed(lambda: run([SAMPLES[1], SAMPLES[2]] * 8), 3)
        near_limit = neo_tokenizer.decode(neo_tokenizer("The train was late. " * 160)["input_ids"][:490])
        records["neo_near_limit_tokens"] = len(neo_tokenizer(near_limit)["input_ids"])
        records["neo_near_limit"], _ = timed(
            lambda: statistical(near_limit, neo_tokenizer, neo_model, criterion, torch), 3,
        )
        records["all_four_after_inference"] = memory(torch)
        tokenizer, model, seconds = load("tmr", "cuda:0", torch, transformers)
        models["tmr"] = (tokenizer, model)
        del tokenizer, model
        classifier(SAMPLES[1:3], *models["tmr"], torch, "cuda:0")
        records["tmr_challenger_load_seconds"] = seconds
        records["all_five_after_tmr_inference"] = memory(torch)
    finally:
        # Also drop local aliases to the statistical model before measuring release.
        neo_model = neo_tokenizer = None
        models.clear()
        release(torch)
        records["after_unload"] = memory(torch)
    tokenizer, model, records["neo_cached_gpu_load_seconds"] = load(
        "neo", "cuda:0", torch, transformers
    )
    model.to("cpu")
    release(torch)
    records["neo_cpu_batch1"], cpu_score = timed(
        lambda: statistical(SAMPLES[1], tokenizer, model, criterion, torch), 3,
    )
    records["neo_cpu_gpu_criterion_difference"] = abs(score - cpu_score)
    del model, tokenizer
    release(torch)
    records["final_after_unload"] = memory(torch)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["encoders", "suite"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").startswith("GPU-"):
        raise SystemExit("Explicitly select the intended GPU by UUID")
    import torch
    import transformers

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    if torch.cuda.device_count() != 1 or "RTX 3060" not in torch.cuda.get_device_name(0):
        raise SystemExit("Probe requires exactly the intended RTX 3060, no fallback")
    report = {
        "purpose": "operational_feasibility_not_accuracy",
        "phase": args.phase, "artifacts": ARTIFACTS,
        "torch": torch.__version__, "transformers": transformers.__version__,
        "device": torch.cuda.get_device_name(0), "pid": os.getpid(),
        "cpu_threads": 4, "classifier_dtype": "float32", "neo_dtype": "float16",
        "input_policy": "raw_text_no_truncation_probe_cap_512_tokens",
    }
    try:
        report["results"] = (
            probe_encoders(torch, transformers) if args.phase == "encoders"
            else probe_suite(torch, transformers, args.output.parent / "reference-fast-detect-gpt")
        )
        report["passed"] = True
    except Exception as error:
        report["passed"] = False
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print("REPORT", args.output, "PASSED", report["passed"], flush=True)


if __name__ == "__main__":
    main()
