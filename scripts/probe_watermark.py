"""CPU-only known-key watermark feasibility check, not provider verification.

Generates synthetic controls using GPT-2 and Transformers' public KGW-style
watermark configuration. The demonstration key is public, never a provider key.
No original X posts, hosted verifiers, or production server adapters are used.
"""

import argparse
import gc
import json
import os
from pathlib import Path
import statistics
import time
import weakref

MODEL = "openai-community/gpt2"
REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
DEMO_KEY = 15485863


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures-output", type=Path)
    args = parser.parse_args()
    # Set before importing torch: this process must not create a CUDA context.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, WatermarkDetector, WatermarkingConfig

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, trust_remote_code=False, use_safetensors=True,
        dtype=torch.float32, attn_implementation="eager",
    ).eval()
    load_seconds = time.perf_counter() - start
    config = WatermarkingConfig(
        hashing_key=DEMO_KEY, greenlist_ratio=0.25, bias=2.0,
        seeding_scheme="lefthash", context_width=1,
    )
    inputs = tokenizer("A quiet walk through the town on a rainy morning", return_tensors="pt")
    generated = {}
    fixture_texts = {}
    generation_seconds = {}
    for label, watermark in (("marked", config), ("unmarked", None)):
        torch.manual_seed(42)
        start = time.perf_counter()
        with torch.inference_mode():
            ids = model.generate(
                **inputs, min_new_tokens=128, max_new_tokens=128, do_sample=True,
                temperature=0.8, pad_token_id=tokenizer.eos_token_id,
                watermarking_config=watermark,
            )[:, inputs.input_ids.shape[1]:]
        generation_seconds[label] = time.perf_counter() - start
        # Verify the copied text, not just token IDs taken directly from generation.
        text = tokenizer.decode(ids[0], skip_special_tokens=True)
        fixture_texts[label] = text
        generated[label] = tokenizer(text, return_tensors="pt").input_ids
    model_config = model.config
    model_reference = weakref.ref(model)
    del model
    gc.collect()
    if model_reference() is not None:
        raise RuntimeError("Generator unexpectedly retained during detection-only test")
    detector = WatermarkDetector(
        model_config, device="cpu", watermarking_config=config,
        ignore_repeated_ngrams=True,
    )

    def check(ids, verifier=detector):
        result = verifier(ids, z_threshold=4.0, return_dict=True)
        return {
            name: getattr(result, name).tolist()
            for name in ("num_tokens_scored", "z_score", "p_value", "prediction")
        }

    start = time.perf_counter()
    report = {
        "purpose": "known_configuration_feasibility_not_provider_verification_or_accuracy",
        "model": MODEL, "revision": REVISION, "device": "cpu",
        "generator_released_before_verification": model_reference() is None,
        "cpu_threads": 4, "torch": torch.__version__,
        "demo_key_public_not_secret": DEMO_KEY,
        "load_seconds_including_any_download": round(load_seconds, 3),
        "generation_seconds": generation_seconds,
        "marked_128": check(generated["marked"]),
        "marked_prefix_32": check(generated["marked"][:, :32]),
        "unmarked_128": check(generated["unmarked"]),
    }
    wrong_key_detector = WatermarkDetector(
        model_config, device="cpu",
        watermarking_config=WatermarkingConfig(hashing_key=DEMO_KEY + 1),
        ignore_repeated_ngrams=True,
    )
    report["marked_wrong_key"] = check(generated["marked"], wrong_key_detector)
    times = []
    for _ in range(10):
        tick = time.perf_counter()
        check(generated["marked"])
        times.append(round(1000 * (time.perf_counter() - tick), 3))
    report["cached_verification_ms"] = {
        "median": statistics.median(times), "samples": times,
    }
    report["verification_seconds_all_checks"] = round(time.perf_counter() - start, 3)
    report["cuda_initialized"] = torch.cuda.is_initialized()
    report["passed_fixture_checks"] = (
        report["marked_128"]["prediction"] == [True]
        and report["unmarked_128"]["prediction"] == [False]
        and report["marked_wrong_key"]["prediction"] == [False]
        and not report["cuda_initialized"]
    )
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if args.fixtures_output:
        args.fixtures_output.write_text(json.dumps({
            "purpose": "synthetic_research_only_not_provider_coverage",
            "generator": MODEL, "revision": REVISION, "public_demo_key": DEMO_KEY,
            "texts": fixture_texts,
        }, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed_fixture_checks"]:
        raise SystemExit("Controlled fixture failed; inspect results, not an accuracy estimate")


if __name__ == "__main__":
    main()
