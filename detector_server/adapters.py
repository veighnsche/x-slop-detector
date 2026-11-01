"""Bounded real inference adapters. Construction/status import no model runtime."""

import gc
import math
import os
import re
import sys

from .contracts import CheckEvidence, ClassifierScore, Coverage, Discrepancy


class ResourceExhausted(Exception):
    pass


class DeviceConfigurationError(Exception):
    pass


def initialized_cuda():
    """Observe an already initialized runtime, never a worker's partial import."""
    torch = sys.modules.get("torch")
    if torch is None or getattr(getattr(torch, "__spec__", None), "_initializing", False):
        return None
    cuda = getattr(torch, "cuda", None)
    is_initialized = getattr(cuda, "is_initialized", None)
    return cuda if callable(is_initialized) and is_initialized() else None


def verify_device(device, gpu_uuid):
    if device == "cpu":
        return None
    # Check before importing torch or touching CUDA. No automatic GPU selection,
    # multi-GPU spread, offload, quantization, or CPU fallback.
    if (
        device != "cuda:0" or not gpu_uuid
        or not re.fullmatch(r"GPU-[a-fA-F0-9-]{36}", gpu_uuid)
        or os.environ.get("CUDA_VISIBLE_DEVICES") != gpu_uuid
    ):
        raise DeviceConfigurationError()
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise DeviceConfigurationError()
    actual = str(getattr(torch.cuda.get_device_properties(0), "uuid", ""))
    actual = actual.removeprefix("GPU-")
    if actual.lower() != gpu_uuid.removeprefix("GPU-").lower():
        raise DeviceConfigurationError()
    return gpu_uuid


class TransformerAdapter:
    def __init__(self, spec, device):
        self.spec = spec
        self.device = device
        self.model = None
        self.tokenizer = None

    def load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.spec.artifact_id, revision=self.spec.checker.artifact_revision,
            trust_remote_code=False,
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        model_class = (
            AutoModelForCausalLM if self.spec.kind == "statistical"
            else AutoModelForSequenceClassification
        )
        self.model, diagnostics = model_class.from_pretrained(
            self.spec.artifact_id, revision=self.spec.checker.artifact_revision,
            trust_remote_code=False, use_safetensors=True, attn_implementation="eager",
            dtype=torch.float16 if self.spec.precision == "float16" else torch.float32,
            output_loading_info=True,
        )
        if any(diagnostics.get(key) for key in ("missing_keys", "mismatched_keys", "error_msgs")):
            raise RuntimeError("invalid_checkpoint")
        for key in diagnostics.get("unexpected_keys", []):
            if self.spec.kind != "statistical" or not re.fullmatch(
                r"transformer\.h\.\d+\.attn\.attention\.(masked_bias|bias)", key,
            ):
                raise RuntimeError("unexpected_checkpoint_tensor")
        self.model = self.model.to(self.device).eval()

    def predict(self, post):
        import torch

        count = len(self.tokenizer(post.text, truncation=False)["input_ids"])
        coverage = Coverage(
            characters=len(post.text), input_tokens=count, token_limit=self.spec.max_tokens,
        )
        common = {"checker": self.spec.checker, "coverage": coverage}
        if count > self.spec.max_tokens:
            return CheckEvidence(**common, status="unsupported", reason="token_limit_exceeded")
        if self.spec.kind == "statistical" and count < 2:
            return CheckEvidence(
                **common, status="insufficient_evidence", reason="no_next_token_observations",
            )
        exhausted = False
        try:
            inputs = self.tokenizer(
                post.text, truncation=False, return_tensors="pt", return_token_type_ids=False,
            ).to(self.device)
            with torch.inference_mode():
                if self.spec.kind == "statistical":
                    from ._vendor.fast_detect_gpt import get_sampling_discrepancy_analytic

                    logits = self.model(**inputs, use_cache=False).logits[:, :-1]
                    value = get_sampling_discrepancy_analytic(
                        logits, logits, inputs.input_ids[:, 1:],
                    )
                    if not math.isfinite(value):
                        return CheckEvidence(
                            **common, status="insufficient_evidence", reason="too_little_signal",
                        )
                    common["coverage"] = coverage.model_copy(update={"scored_tokens": count - 1})
                    output = Discrepancy(value=value)
                else:
                    logits = self.model(**inputs).logits
                    if logits.shape != (1, 2):
                        raise ValueError("unexpected_classifier_shape")
                    output = ClassifierScore(
                        value=logits.float().softmax(-1)[0, self.spec.ai_label_index].item(),
                    )
            return CheckEvidence(**common, status="completed", output=output)
        except torch.OutOfMemoryError:
            exhausted = True
        # Drop exception tracebacks/tensor locals before the owner attempts
        # whole-suite release. Do not retain a CUDA OOM as an exception cause.
        if exhausted:
            raise ResourceExhausted() from None

    def unload(self):
        self.model = None
        self.tokenizer = None
        gc.collect()
        # Do not import torch merely to unload an adapter that never loaded.
        cuda = initialized_cuda() if self.device.startswith("cuda") else None
        if cuda is not None:
            with cuda.device(self.device):
                cuda.empty_cache()
