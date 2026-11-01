"""Portable JSON scoring artifact. No pickle, sklearn, numpy, torch or API wiring."""
import math
from typing import Literal

from pydantic import FiniteFloat, Field, model_validator

from detector_server.contracts import Contract, CheckerSpec, Identifier
from .data import ROSTER, digest, feature_values, read_json


def sigmoid(x):
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


class Profile(Contract):
    schema_version: Literal["1"] = "1"
    profile_id: Identifier
    target_id: Literal["substantive_llm_wording_v1"] = "substantive_llm_wording_v1"
    validation_state: Literal["benchmark_only"] = "benchmark_only"
    deployment_approved: Literal[False] = False
    configuration_id: Identifier
    extraction_version: Identifier
    runtime_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    specs: list[CheckerSpec]
    feature_indices: list[int]
    means: list[FiniteFloat]
    scales: list[FiniteFloat]
    coefficients: list[FiniteFloat]
    intercept: FiniteFloat
    calibration_slope: FiniteFloat
    calibration_intercept: FiniteFloat
    calibration_positive_fraction: FiniteFloat = Field(gt=0, lt=1)
    corpus_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    split_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fit_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    calibration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    population: str
    limitations: list[str]

    @model_validator(mode="after")
    def shape(self):
        n = len(self.feature_indices)
        if tuple(s.checker.id for s in self.specs) != ROSTER:
            raise ValueError("unsupported_roster")
        if (not n or len(set(self.feature_indices)) != n or
                any(type(i) is not int or not 0 <= i < len(ROSTER) for i in self.feature_indices)):
            raise ValueError("invalid_feature_indices")
        if any(len(x) != n for x in (self.means, self.scales, self.coefficients)):
            raise ValueError("invalid_profile_dimensions")
        if any(s <= 0 for s in self.scales):
            raise ValueError("invalid_scaling")
        return self

    def logit(self, values):
        if len(values) != len(ROSTER) or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("invalid_feature_vector")
        result = self.intercept + math.fsum(
            coefficient * (values[i] - mean) / scale
            for i, mean, scale, coefficient in zip(
                self.feature_indices, self.means, self.scales, self.coefficients,
            )
        )
        if not math.isfinite(result):
            raise ValueError("non_finite_model_margin")
        return result

    def predict(self, values):
        margin = self.calibration_slope * self.logit(values) + self.calibration_intercept
        if not math.isfinite(margin):
            raise ValueError("non_finite_calibration_margin")
        return sigmoid(margin)

    def score_evidence(self, example, evidence, *, benchmark=False):
        if not benchmark:
            raise ValueError("profile_not_approved_for_deployment")
        if (evidence.configuration_id != self.configuration_id or
                evidence.extraction_version != self.extraction_version):
            raise ValueError("profile_configuration_mismatch")
        if example.language != "en" or len(example.text) > 10000:
            return None
        values = feature_values(example, evidence, self.specs)
        return None if values is None else self.predict(values)

    def envelope(self):
        payload = self.model_dump(mode="json")
        return {"sha256": digest(payload), "profile": payload}


def load_profile(path):
    raw = read_json(path)
    if set(raw) != {"sha256", "profile"} or digest(raw["profile"]) != raw["sha256"]:
        raise ValueError("profile_integrity_failure")
    profile = Profile.model_validate(raw["profile"])
    # Reject unknown/coerced fields before accepting a supposedly exact artifact.
    if profile.envelope()["sha256"] != raw["sha256"]:
        raise ValueError("noncanonical_profile")
    return profile
