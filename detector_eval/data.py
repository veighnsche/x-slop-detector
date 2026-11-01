"""Strict provenance and native-evidence records. Never infer labels from scores."""
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from detector_server.contracts import (
    Contract, CheckerSpec, CheckEvidence, Identifier, validate_check,
)

PARTITIONS = ("development", "calibration", "operating", "holdout", "challenge")
ROSTER = ("tabularis", "e5", "fakespot", "fast_detect_gpt")


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Source(Contract):
    id: Identifier
    url: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    license: str = Field(min_length=1)
    permission_record: str = Field(min_length=1)
    private_evaluation_allowed: Literal[True]
    redistribution_allowed: bool
    limitations: list[str]


class Example(Contract):
    id: Identifier
    text: str = Field(min_length=1, max_length=100_000)
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_id: Identifier
    source_locator: str = Field(min_length=1)
    acquired_at: str = Field(min_length=1)
    author_id: Identifier
    root_id: Identifier
    # Supply actual prompt/event/lineage groups where known, not generic genre.
    extra_groups: list[str] = Field(default_factory=list)
    unverified_group_axes: list[str] = Field(default_factory=list)
    language: str = Field(min_length=1)
    generator_family: str | None
    cohort: str = Field(min_length=1)
    derivation: str = Field(min_length=1)
    label: Literal[0, 1] | None
    label_basis: str = Field(min_length=1)

    @field_validator("label", mode="before")
    @classmethod
    def integer_label(cls, value):
        if value is not None and type(value) is not int:
            raise ValueError("binary_label_must_be_integer_not_boolean")
        return value

    @model_validator(mode="after")
    def exact_text(self):
        if not self.text.strip() or self.text_sha256 != text_hash(self.text):
            raise ValueError("invalid_example_text_hash")
        if not self.label_basis:
            raise ValueError("missing_process_label_evidence")
        return self


class Corpus(Contract):
    schema_version: Literal["1"] = "1"
    target_id: Literal["substantive_llm_wording_v1"] = "substantive_llm_wording_v1"
    population: str
    deployment_population_validated: Literal[False] = False
    sources: list[Source]
    examples: list[Example]
    limitations: list[str]

    @model_validator(mode="after")
    def identities(self):
        sources = {s.id for s in self.sources}
        if len(sources) != len(self.sources) or not sources:
            raise ValueError("duplicate_or_missing_sources")
        ids = [e.id for e in self.examples]
        if len(ids) != len(set(ids)) or not ids:
            raise ValueError("duplicate_or_missing_examples")
        if any(e.source_id not in sources for e in self.examples):
            raise ValueError("unknown_source")
        return self


class Evidence(Contract):
    example_id: Identifier
    text_sha256: str
    configuration_id: Identifier
    extraction_version: Identifier
    checks: list[CheckEvidence]
    collection_reason: Literal["input_character_limit"] | None = None


class EvidenceSet(Contract):
    schema_version: Literal["1"] = "1"
    corpus_sha256: str
    configuration_id: Identifier
    extraction_version: Identifier
    runtime: dict[str, str]
    specs: list[CheckerSpec]
    rows: list[Evidence]


def feature_values(example, evidence, specs):
    """None means unavailable evidence, not four zero-valued observations."""
    if evidence.example_id != example.id or evidence.text_sha256 != example.text_sha256:
        raise ValueError("evidence_not_bound_to_example")
    checks = {c.checker.id: c for c in evidence.checks}
    if len(checks) != len(evidence.checks):
        raise ValueError("duplicate_evidence")
    if tuple(s.checker.id for s in specs) != ROSTER:
        raise ValueError("unsupported_roster")
    values = []
    complete = True
    for spec in specs:
        check = checks.get(spec.checker.id)
        if check is None:
            complete = False
            continue
        validate_check(check, spec, len(example.text))
        if check.status != "completed":
            complete = False
            continue
        value = check.output.value
        if not math.isfinite(value):
            raise ValueError("non_finite_feature")
        values.append(value)
    return values if complete else None


def bind_evidence(corpus, evidence):
    if evidence.corpus_sha256 != digest(corpus.model_dump(mode="json")):
        raise ValueError("corpus_changed_after_collection")
    by_id = {r.example_id: r for r in evidence.rows}
    if len(by_id) != len(evidence.rows) or set(by_id) != {e.id for e in corpus.examples}:
        raise ValueError("missing_duplicate_or_extra_evidence_rows")
    for row in evidence.rows:
        if (row.configuration_id != evidence.configuration_id or
                row.extraction_version != evidence.extraction_version):
            raise ValueError("mixed_evidence_configuration")
    return [feature_values(e, by_id[e.id], evidence.specs) for e in corpus.examples]


def normalized(text):
    # Duplicate discovery only. These bytes are never fed to a detector.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def connected_groups(examples):
    """Union authors/roots/declared groups, exact and near-duplicate passages."""
    parent = list(range(len(examples)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    known = {}
    signatures = []
    for i, e in enumerate(examples):
        text = normalized(e.text)
        tags = [f"author:{e.author_id}", f"root:{e.root_id}", f"exact:{text}", *e.extra_groups]
        for tag in tags:
            if tag in known:
                union(i, known[tag])
            else:
                known[tag] = i
        # Character shingles cover spacing/punctuation edits without translating text.
        signatures.append({text[j:j + 12] for j in range(max(0, len(text) - 11))})
    for i, left in enumerate(signatures):
        if not left:
            continue
        for j in range(i):
            right = signatures[j]
            if find(i) == find(j) or not right:
                continue
            if min(len(left), len(right)) / max(len(left), len(right)) < 0.9:
                continue
            if len(left & right) / len(left | right) >= 0.9:
                union(i, j)
    return [f"group-{find(i)}" for i in range(len(examples))]


def split_corpus(corpus, seed, reserved_family):
    """Stratify connected groups before fitting; hold an entire family out."""
    import numpy as np
    from sklearn.model_selection import StratifiedGroupKFold

    groups = connected_groups(corpus.examples)
    reserved = {
        group for e, group in zip(corpus.examples, groups)
        if e.generator_family == reserved_family
    }
    indices = [i for i, g in enumerate(groups) if g not in reserved]
    if len({groups[i] for i in indices}) < 5:
        raise ValueError("not_enough_independent_groups")
    # Unknown labels influence split balance as a distinct stratum, never fitting.
    labels = [2 if corpus.examples[i].label is None else corpus.examples[i].label for i in indices]
    split = ["challenge" if g in reserved else None for g in groups]
    names = ["holdout", "operating", "calibration", "development", "development"]
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    for fold, (_, test) in enumerate(folds.split(np.zeros(len(indices)), labels, [groups[i] for i in indices])):
        for n in test:
            split[indices[int(n)]] = names[fold]
    if any(p is None for p in split):
        raise ValueError("unassigned_example")
    for group in set(groups):
        if len({split[i] for i, g in enumerate(groups) if g == group}) != 1:
            raise ValueError("group_leakage")
    return {
        "schema_version": "1", "corpus_sha256": digest(corpus.model_dump(mode="json")),
        "seed": seed, "reserved_family": reserved_family,
        "rows": [{"id": e.id, "group": g, "partition": p}
                 for e, g, p in zip(corpus.examples, groups, split)],
    }


def validate_split(corpus, split):
    """Shared precollection/post-evidence split checks; never trust group names."""
    if split["corpus_sha256"] != digest(corpus.model_dump(mode="json")):
        raise ValueError("split_corpus_mismatch")
    rows = split["rows"]
    if split.get("schema_version") != "1":
        raise ValueError("unsupported_split_schema")
    if len(rows) != len(corpus.examples) or [r["id"] for r in rows] != [e.id for e in corpus.examples]:
        raise ValueError("split_identity_mismatch")
    actual_groups = connected_groups(corpus.examples)
    mapped, assignments = {}, {}
    for actual, row in zip(actual_groups, rows):
        assignment = (row["partition"], row["group"])
        if actual in assignments and assignments[actual] != assignment:
            raise ValueError("split_leaks_connected_group")
        assignments[actual] = assignment
        if row["group"] in mapped and mapped[row["group"]] != actual:
            raise ValueError("split_group_identity_collision")
        mapped[row["group"]] = actual
    if any(r["partition"] not in PARTITIONS for r in rows):
        raise ValueError("invalid_partition")
    if any(e.generator_family == split["reserved_family"] and r["partition"] != "challenge"
           for e, r in zip(corpus.examples, rows)):
        raise ValueError("reserved_family_leakage")


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    # Refuse overwriting an existing study/result, including a consumed holdout.
    with Path(path).open("x") as f:
        json.dump(value, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
