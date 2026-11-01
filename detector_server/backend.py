"""Dedicated classifier adapter. Heavy imports happen only when loading."""

import gc
from dataclasses import dataclass

from .catalog import TABULARIS

MODEL_ID = TABULARIS.artifact_id
MODEL_REVISION = TABULARIS.checker.artifact_revision
# The publisher's inference example maps index 1 to AI. Keep this mapping tied
# to the pinned checkpoint, rather than assuming it applies to arbitrary models.
AI_LABEL_INDEX = TABULARIS.ai_label_index
MAX_TOKENS = TABULARIS.max_tokens


class InputTooLong(ValueError):
    pass


@dataclass
class Prediction:
    ai_score: float
    tokens: int


class TransformersBackend:
    def __init__(self, device: str):
        self.device = device
        self.model = None
        self.tokenizer = None

    def load(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("Configured CUDA device is unavailable")
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False
        )
        # FP32 avoids silently changing the publisher's inference precision.
        # Eager attention avoids optional FlashAttention dependencies.
        self.model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            trust_remote_code=False,
            use_safetensors=True,
            attn_implementation="eager",
        ).to(self.device).eval()

    def predict(self, texts: list[str]) -> list[Prediction]:
        import torch

        # Do not silently truncate longer posts, pad with unrelated posts, or
        # normalize away parts of the author's text.
        encoded = self.tokenizer(texts, truncation=False)
        lengths = [len(ids) for ids in encoded["input_ids"]]
        if any(length > MAX_TOKENS for length in lengths):
            raise InputTooLong(f"Each post must fit within {MAX_TOKENS} tokens")
        inputs = self.tokenizer.pad(encoded, padding=True, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            logits = self.model(**inputs).logits
            if logits.shape != (len(texts), 2):
                raise RuntimeError("Unexpected classifier output shape")
            scores = logits.float().softmax(dim=-1)[:, AI_LABEL_INDEX].cpu().tolist()
        return [Prediction(score, count) for score, count in zip(scores, lengths)]

    def unload(self):
        self.model = None
        self.tokenizer = None
        gc.collect()
        # This returns unused allocator blocks to CUDA, not the process's CUDA
        # context. Some VRAM can remain reserved until the process exits.
        import torch

        if self.device.startswith("cuda") and torch.cuda.is_available():
            with torch.cuda.device(self.device):
                torch.cuda.empty_cache()
