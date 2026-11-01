"""Conditional CPU verification and non-callable hosted-route policy.

No provider URL, credential, HTTP client, or generation model is implemented here.
The only executable scheme is the pinned, operator-scoped KGW configuration.
"""

import gc
import hashlib
import json
import logging
import math
import os
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import (
    CheckEvidence, CheckerRef, CheckerSpec, Contract, Coverage, Identifier,
    LocalWatermarkRoute, ProviderRoute, WatermarkFinding,
    validate_check,
)

logger = logging.getLogger(__name__)
TOKENIZER_ID = "openai-community/gpt2"
TOKENIZER_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
TRANSFORMERS_VERSION = "5.22.1"
TORCH_VERSION = "2.15.0"
PUBLIC_FIXTURE_KEY = 15485863
MAX_TOKENS = 512


class KgwConfiguration(Contract):
    enabled: bool = False
    applicability: Literal["unconfigured", "operator_scoped"] = "unconfigured"
    purpose: Literal["research_fixture", "known_configuration"] = "research_fixture"
    scope_description: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    key_id: Identifier = "public-fixture-key"
    key_source: Literal["public_fixture", "environment"] = "public_fixture"
    key_env: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,99}$")] | None = None
    matching_generation_device: Literal["cpu"] = "cpu"

    @model_validator(mode="after")
    def explicit_scope_and_key(self):
        if self.enabled and (self.applicability != "operator_scoped" or not self.scope_description):
            raise ValueError("explicit_operator_scope_required")
        if self.key_source == "environment" and not self.key_env:
            raise ValueError("key_environment_required")
        if self.key_source == "public_fixture":
            if self.purpose != "research_fixture" or self.key_env is not None:
                raise ValueError("demo_key_is_research_only")
        if self.purpose == "known_configuration" and self.key_id == "public-fixture-key":
            raise ValueError("explicit_non_demo_key_identity_required")
        return self

    def public_identity(self):
        # Neither the key nor its environment-variable name crosses the API.
        return self.model_dump(exclude={"key_env"})


class ProviderPolicy(Contract):
    id: Literal["anthropic", "openai", "google", "xai"]
    access: Literal["pending", "unconfirmed", "granted"] = "unconfirmed"
    application_submitted: bool = False
    configured: bool = False
    approved: bool = False
    enabled: Literal[False] = False
    support: Literal["unconfirmed", "supported", "unsupported"] = "unconfirmed"
    terms_approved: bool = False
    free_unlimited_verified: bool = False
    failure: Literal["configuration_invalid", "contract_unverified"] | None = None


class WatermarkConfiguration(Contract):
    schema_version: Literal["1"] = "1"
    kgw: KgwConfiguration | None = None
    providers: Annotated[list[ProviderPolicy], Field(max_length=4)] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_providers(self):
        if len({policy.id for policy in self.providers}) != len(self.providers):
            raise ValueError("duplicate_provider_policy")
        return self


def read_configuration(path):
    if path is None:
        return WatermarkConfiguration()
    try:
        with Path(path).open("rb") as file:
            data = file.read(65_537)
        if len(data) > 65_536:
            raise ValueError("configuration_too_large")
        return WatermarkConfiguration.model_validate_json(data)
    except Exception:
        # Pydantic/file exceptions can contain operator data. Fail startup
        # without dumping supplied values, secrets, or the configuration text.
        raise ValueError("invalid_watermark_route_configuration") from None


class KgwVerifier:
    def __init__(self, configuration=None):
        self.configuration = configuration
        identity = {
            "operator": configuration.public_identity() if configuration is not None else None,
            "transformers": TRANSFORMERS_VERSION, "torch": TORCH_VERSION,
            "tokenizer": TOKENIZER_ID, "tokenizer_revision": TOKENIZER_REVISION,
            "seeding_scheme": "lefthash", "context_width": 1, "greenlist_ratio": 0.25,
            "bias": 2.0, "z_threshold": 4.0, "minimum_unique_bigrams": 32,
            "ignore_repeated_ngrams": True, "max_tokens": MAX_TOKENS,
            "generation_rng_device": "cpu",
        }
        suffix = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
        self.spec = CheckerSpec(
            checker=CheckerRef(
                id="kgw", configuration_id=f"kgw-gpt2-cpu-v1-{suffix}",
                artifact_revision=TOKENIZER_REVISION,
            ),
            kind="watermark",
            role="research_fixture" if configuration is None else (
                "research_fixture" if configuration.purpose == "research_fixture" else "conditional_verifier"
            ),
            artifact_id=TOKENIZER_ID, license="Apache-2.0 AND MIT",
            method_revision=f"transformers-{TRANSFORMERS_VERSION}-torch-{TORCH_VERSION}-kgw-cpu-v1",
            precision="not_applicable", max_tokens=MAX_TOKENS, preprocessing="raw_text",
        )
        self.state = "unavailable" if self.blocker() else "unloaded"
        self.failure = None
        self.tokenizer = None
        self.detector = None

    def blocker(self):
        config = self.configuration
        if config is None or config.applicability == "unconfigured":
            return "no_matching_configuration"
        if not config.enabled:
            return "route_disabled"
        return getattr(self, "failure", None)

    def status(self):
        config = self.configuration
        return LocalWatermarkRoute(
            configuration_id=self.spec.checker.configuration_id,
            configured=config is not None, enabled=config.enabled if config else False,
            applicability=config.applicability if config else "unconfigured",
            purpose=config.purpose if config else "research_fixture",
            key_id=config.key_id if config else None,
            scope_description=config.scope_description if config else None,
            state=self.state, blocker=self.blocker(),
        )

    def load(self):
        if self.blocker() in ("no_matching_configuration", "route_disabled"):
            return
        if self.state == "ready":
            return
        failed = None
        try:
            import torch
            import transformers
            from transformers import AutoConfig, AutoTokenizer, WatermarkDetector, WatermarkingConfig

            if transformers.__version__ != TRANSFORMERS_VERSION or torch.__version__.split("+")[0] != TORCH_VERSION:
                failed = "implementation_unavailable"
            else:
                config = self.configuration
                key = PUBLIC_FIXTURE_KEY if config.key_source == "public_fixture" else int(os.environ[config.key_env])
                if not 0 <= key < 2**63:
                    raise ValueError("invalid_key")
                if config.purpose == "known_configuration" and key == PUBLIC_FIXTURE_KEY:
                    raise ValueError("demo_key_is_research_only")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    TOKENIZER_ID, revision=TOKENIZER_REVISION, trust_remote_code=False,
                )
                model_config = AutoConfig.from_pretrained(
                    TOKENIZER_ID, revision=TOKENIZER_REVISION, trust_remote_code=False,
                )
                if self.tokenizer.vocab_size != 50257 or model_config.vocab_size != 50257:
                    raise ValueError("incompatible_vocabulary")
                self.detector = WatermarkDetector(
                    model_config, device="cpu",
                    watermarking_config=WatermarkingConfig(
                        hashing_key=key, greenlist_ratio=0.25, bias=2.0,
                        seeding_scheme="lefthash", context_width=1,
                    ),
                    ignore_repeated_ngrams=True, max_cache_size=0,
                )
        except ImportError:
            failed = "implementation_unavailable"
        except Exception as error:
            logger.error("Watermark load failed (%s)", type(error).__name__)
            failed = "configuration_invalid"
        if failed is not None:
            self.unload()
            self.failure = failed
            self.state = "error"
        else:
            self.failure = None
            self.state = "ready"

    def predict(self, post):
        blocker = self.blocker()
        common = {
            "checker": self.spec.checker,
            "coverage": Coverage(characters=len(post.text), token_limit=MAX_TOKENS),
        }
        if blocker is not None:
            return CheckEvidence(
                **common, status="unsupported" if blocker == "no_matching_configuration" else "unavailable",
                reason=blocker,
            )
        self.load()
        if self.failure:
            return CheckEvidence(**common, status="unavailable", reason=self.failure)
        tokens = self.tokenizer(post.text, return_tensors="pt", truncation=False).input_ids
        count = tokens.shape[1]
        common["coverage"] = Coverage(
            characters=len(post.text), input_tokens=count, token_limit=MAX_TOKENS,
        )
        if count > MAX_TOKENS:
            return CheckEvidence(**common, status="unsupported", reason="token_limit_exceeded")
        ids = tokens[0].tolist()
        if ids and ids[0] == self.detector.bos_token_id:
            ids = ids[1:]
        # Exactly one whole-passage test, one key/config, repeated bigrams
        # ignored. Match the detector's count and guard sparse/repeated input.
        unique = len(set(zip(ids, ids[1:])))
        common["coverage"] = common["coverage"].model_copy(update={"scored_tokens": unique})
        if unique < 32:
            return CheckEvidence(**common, status="insufficient_evidence", reason="too_little_signal")
        native = self.detector(tokens, z_threshold=4.0, return_dict=True)
        z = float(native.z_score[0])
        if int(native.num_tokens_scored[0]) != unique or not math.isfinite(z):
            raise ValueError("invalid_watermark_output")
        return CheckEvidence(
            **common, status="completed",
            output=WatermarkFinding(
                decision="detected" if z > 4.0 else "not_detected",
                verification_scope="known_configuration", z_score=z,
                # The library p-value approximation is not validated. Do not
                # expose its "confidence" or turn it into authorship probability.
                p_value=None, tests_performed=1,
                configuration_purpose=self.configuration.purpose,
            ),
        )

    def unload(self):
        self.tokenizer = None
        self.detector = None
        # The library's LRU wrapper retains a bound method/self cycle even with
        # max_cache_size=0; release its CPU processor/table during explicit unload.
        gc.collect()
        self.failure = None
        self.state = "unavailable" if self.blocker() else "unloaded"


class WatermarkRoutes:
    def __init__(self, configuration=None, *, verifier_factory=KgwVerifier):
        self.configuration = configuration or WatermarkConfiguration()
        self.verifier = verifier_factory(self.configuration.kgw)
        self.specs = (self.verifier.spec,)
        policies = {policy.id: policy for policy in self.configuration.providers}
        self.providers = tuple(ProviderRoute(
            **(policies[id].model_dump() if id in policies else {
                "id": id, "access": "unconfirmed" if id == "google" else "pending",
            }),
        ) for id in ("anthropic", "openai", "google", "xai"))

    def public_identity(self):
        return {
            "kgw": self.verifier.spec.model_dump(),
            "providers": [route.model_dump() for route in self.providers],
        }

    @property
    def resident(self):
        return self.verifier.state == "ready"

    @property
    def ready_or_inactive(self):
        config = self.configuration.kgw
        return not (
            config and config.enabled and config.applicability == "operator_scoped"
        ) or self.resident

    def load(self):
        failed = False
        try:
            self.verifier.load()
        except Exception as error:
            logger.error("Watermark prewarm failed (%s)", type(error).__name__)
            failed = True
        if failed:
            self.verifier.unload()
            self.verifier.failure = "configuration_invalid"
            self.verifier.state = "error"

    def unload(self):
        self.verifier.unload()

    def predict(self, post):
        reason = "checker_error"
        try:
            result = self.verifier.predict(post)
            checked = CheckEvidence.model_validate(result.model_dump())
            validate_check(checked, self.verifier.spec, len(post.text))
            return checked
        except ValueError:
            reason = "invalid_checker_output"
        except Exception as error:
            logger.error("Watermark verification failed (%s)", type(error).__name__)
        # Drop error tracebacks before releasing any tokenizer/detector caches.
        self.verifier.unload()
        self.verifier.failure = "configuration_invalid"
        self.verifier.state = "error"
        return CheckEvidence(
            checker=self.verifier.spec.checker, status="failed", reason=reason,
            coverage=Coverage(characters=len(post.text), token_limit=self.verifier.spec.max_tokens),
        )
