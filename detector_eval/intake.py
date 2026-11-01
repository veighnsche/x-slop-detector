"""Import private, process-recorded short writing; never label from detector scores."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from detector_server.contracts import Contract, Identifier
from .adequacy import audit
from .data import Corpus, Example, Source, digest, read_json, split_corpus, text_hash, write_json

Workflow = Literal[
    "unaided", "generated", "rewritten", "translated", "human_edited_ai",
    "mixed", "mechanical_only", "ideas_only",
]
POSITIVE = {"generated", "rewritten", "translated", "human_edited_ai", "mixed"}
GENERATIVE = POSITIVE | {"ideas_only"}
ArtifactKind = Literal[
    "permission", "final_text", "writing_log", "assistance_declaration",
    "generation_prompt", "generation_output", "generation_config", "edit_log",
]
CONTENT_TAGS = (
    "reply", "joke", "argument", "technical", "non_native_english",
    "very_short", "emoji", "link", "quotation", "longer_post",
)


class Artifact(Contract):
    id: Identifier
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: ArtifactKind


class PermissionSource(Contract):
    id: Identifier
    url: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    license: str = Field(min_length=1)
    permission_artifact_id: Identifier
    private_evaluation_allowed: Literal[True]
    redistribution_allowed: bool
    limitations: list[str]


class Generation(Contract):
    model_id: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    family: str = Field(min_length=1)
    prompt_artifact_id: Identifier
    output_artifact_id: Identifier
    # Raw record: decoding parameters, seed (or unavailable), tokenizer/template
    # revisions, execution time and route. Not a made-up default configuration.
    config_artifact_id: Identifier


class ProcessReview(Contract):
    reviewer_id: Identifier
    method: Literal["human_process_review"]
    decision: Literal["positive", "negative", "unknown"]
    evidence_artifact_ids: list[Identifier] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class Record(Contract):
    id: Identifier
    source_id: Identifier
    author_id: Identifier
    root_id: Identifier
    prompt_group: Identifier
    topic_group: Identifier
    event_group: Identifier
    acquired_at: str
    language: str = Field(min_length=1)
    workflow: Workflow
    origin: Literal["native_short", "native_long", "derived", "constructed"]
    final_artifact_id: Identifier
    process_artifact_ids: list[Identifier] = Field(min_length=1)
    generation: Generation | None
    reviews: list[ProcessReview] = Field(max_length=2)
    content_tags: list[Literal[
        "reply", "joke", "argument", "technical", "non_native_english",
        "very_short", "emoji", "link", "quotation", "longer_post",
    ]]

    @model_validator(mode="after")
    def process(self):
        if datetime.fromisoformat(self.acquired_at.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("acquisition_timestamp_requires_timezone")
        if len({r.reviewer_id for r in self.reviews}) != len(self.reviews):
            raise ValueError("duplicate_process_reviewer")
        if ((self.workflow in GENERATIVE and self.generation is None) or
                (self.workflow == "unaided" and self.generation is not None)):
            raise ValueError("workflow_generation_record_mismatch")
        return self


class Bundle(Contract):
    schema_version: Literal["1"]
    population: str = Field(min_length=1)
    sources: list[PermissionSource] = Field(min_length=1)
    artifacts: list[Artifact] = Field(min_length=1)
    records: list[Record] = Field(min_length=1)

    @model_validator(mode="after")
    def identities(self):
        for entries in (self.sources, self.artifacts, self.records):
            if len({r.id for r in entries}) != len(entries):
                raise ValueError("duplicate_intake_identity")
        return self


def convert(bundle, artifact_directory):
    """Verify referenced bytes, not the truth of externally supplied attestations."""
    root = Path(artifact_directory).resolve()
    artifacts = {a.id: a for a in bundle.artifacts}
    sources = {s.id: s for s in bundle.sources}
    verified = {}

    def artifact(id, kind=None):
        if id not in artifacts:
            raise ValueError("missing_process_artifact")
        a = artifacts[id]
        if kind is not None and a.kind != kind:
            raise ValueError("wrong_process_artifact_kind")
        if id not in verified:
            relative = Path(a.path)
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root):
                raise ValueError("artifact_path_escapes_private_bundle")
            with path.open("rb") as f:
                data = f.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != a.sha256:
                raise ValueError("process_artifact_hash_or_size")
            verified[id] = data
        return verified[id]

    source_artifacts = {s.id: {s.permission_artifact_id} for s in bundle.sources}
    for s in bundle.sources:
        artifact(s.permission_artifact_id, "permission")
    examples, decisions = [], {}
    for r in bundle.records:
        if r.source_id not in sources:
            raise ValueError("unknown_intake_source")
        final = artifact(r.final_artifact_id, "final_text")
        text = final.decode("utf-8")
        if r.origin == "native_short" and len(text) > 280:
            raise ValueError("native_short_exceeds_280_codepoints")
        if r.origin == "native_long" and len(text) <= 280:
            raise ValueError("native_long_not_long")
        ids = {sources[r.source_id].permission_artifact_id, r.final_artifact_id, *r.process_artifact_ids}
        for id in r.process_artifact_ids:
            artifact(id)
        kinds = {artifacts[id].kind for id in r.process_artifact_ids}
        required = {"assistance_declaration"}
        if r.workflow != "generated":
            required.add("writing_log")
        if r.workflow in {"human_edited_ai", "mixed", "mechanical_only", "ideas_only"}:
            required.add("edit_log")
        if not required <= kinds:
            raise ValueError("missing_required_writing_process_record")
        if r.generation:
            g = r.generation
            artifact(g.prompt_artifact_id, "generation_prompt")
            output = artifact(g.output_artifact_id, "generation_output")
            artifact(g.config_artifact_id, "generation_config")
            ids.update([g.prompt_artifact_id, g.output_artifact_id, g.config_artifact_id])
            if r.workflow in {"generated", "rewritten", "translated"} and final != output:
                raise ValueError("verbatim_generation_differs_from_final_use_edited_workflow")
        for review in r.reviews:
            if not set(review.evidence_artifact_ids) <= ids:
                raise ValueError("review_references_foreign_process_evidence")
            if not ids <= set(review.evidence_artifact_ids):
                raise ValueError("process_review_does_not_cover_required_artifacts")
        # Reviews concern source/process evidence, never style or detector results.
        # Disagreement, unknown and incomplete review remain unknown.
        decisions[r.id] = None
        if len(r.reviews) == 2 and r.reviews[0].decision == r.reviews[1].decision != "unknown":
            expected = "positive" if r.workflow in POSITIVE else "negative"
            if r.reviews[0].decision != expected:
                raise ValueError("process_reviews_conflict_with_workflow")
            decisions[r.id] = int(expected == "positive")
        source_artifacts[r.source_id].update(ids)
        examples.append(Example(
            id=r.id, text=text, text_sha256=text_hash(text), source_id=r.source_id,
            source_locator=f"process-record:{r.id}", acquired_at=r.acquired_at,
            author_id=r.author_id, root_id=r.root_id,
            extra_groups=[
                f"prompt:{r.prompt_group}", f"topic:{r.topic_group}", f"event:{r.event_group}",
                *[f"process-artifact:{id}" for id in sorted(ids) if artifacts[id].kind in {
                    "writing_log", "edit_log", "generation_prompt", "generation_output",
                }],
            ],
            language=r.language, generator_family=r.generation.family if r.generation else None,
            cohort=r.workflow, derivation=r.origin, label=decisions[r.id],
            label_basis=(
                f"process-intake-v1; workflow={r.workflow}; "
                f"independent review IDs={len(r.reviews)}; decision={decisions[r.id]}; "
                f"artifact-manifest-sha256={digest({id: artifacts[id].sha256 for id in sorted(ids)})}"
            ),
        ))
    corpus = Corpus(
        population=bundle.population,
        sources=[Source(
            id=s.id, url=s.url, revision=s.revision,
            content_sha256=digest({id: artifacts[id].sha256 for id in sorted(source_artifacts[s.id])}),
            license=s.license, permission_record=s.permission_artifact_id,
            private_evaluation_allowed=s.private_evaluation_allowed,
            redistribution_allowed=s.redistribution_allowed, limitations=s.limitations,
        ) for s in bundle.sources],
        examples=examples, limitations=[
            "Trusted-operator process records/reviewer IDs, not forensic authentication or proof of independent people.",
            "No claim of X prevalence or representative sampling; subgroup coverage requires separate validation.",
            "Declared prompt/topic/event groups must reflect real shared sources, not invented independent IDs.",
            "Two process reviews are required for known labels; unresolved items remain unknown.",
        ],
    )
    summary = {
        "schema_version": "1", "bundle_sha256": digest(bundle.model_dump(mode="json")),
        "corpus_sha256": digest(corpus.model_dump(mode="json")), "records": len(examples),
        "labels": dict(Counter("unknown" if e.label is None else str(e.label) for e in examples)),
        "origins": dict(Counter(r.origin for r in bundle.records)),
        "workflows": {workflow: sum(r.workflow == workflow for r in bundle.records) for workflow in (
            "unaided", "generated", "rewritten", "translated", "human_edited_ai",
            "mixed", "mechanical_only", "ideas_only",
        )},
        "character_buckets": {
            name: sum(low <= len(e.text) <= high for e in examples)
            for name, low, high in (("1-80", 1, 80), ("81-160", 81, 160),
                                    ("161-280", 161, 280), (">280", 281, 100000))
        },
        "content_tags": {tag: sum(tag in r.content_tags for r in bundle.records) for tag in CONTENT_TAGS},
        "warning": "Completeness/hash checks do not authenticate permission, writing history, reviewer identity or truth.",
    }
    return corpus, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema", help="Write the machine-readable intake schema, not sample labels")
    schema.add_argument("--output", required=True)
    imp = commands.add_parser("import")
    imp.add_argument("--bundle", required=True)
    imp.add_argument("--artifacts", required=True)
    imp.add_argument("--output", required=True, help="NEW private study directory, preferably under .cache/evaluation")
    imp.add_argument("--reserved-family", required=True)
    imp.add_argument("--seed", type=int, default=20261102)
    imp.add_argument("--allocation", help="Preregistered main-study collection slots; use together with --author-slots")
    imp.add_argument("--author-slots", help="Private pseudonymous author -> collection-slot JSON mapping, no Prolific IDs")
    args = parser.parse_args()
    if args.command == "schema":
        write_json(args.output, Bundle.model_json_schema())
        return
    bundle = Bundle.model_validate(read_json(args.bundle))
    corpus, summary = convert(bundle, args.artifacts)
    if bool(args.allocation) != bool(args.author_slots):
        parser.error("--allocation and --author-slots must be supplied together")
    allocation = read_json(args.allocation) if args.allocation else None
    if (not allocation or allocation.get("phase") != "pilot") and \
            args.reserved_family not in {e.generator_family for e in corpus.examples}:
        raise ValueError("reserved_family_absent")
    if args.allocation:
        from .study import preassigned_split
        split = preassigned_split(corpus, allocation,
                                  read_json(args.author_slots), args.reserved_family)
    else:
        split = split_corpus(corpus, args.seed, args.reserved_family)
    preflight = audit(corpus, split, [e.language == "en" and len(e.text) <= 10000 for e in corpus.examples],
                      basis="precollection_upper_bound_no_native_evidence")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in [
        ("corpus.json", corpus.model_dump(mode="json")), ("splits.json", split),
        ("intake-summary.json", summary), ("adequacy-precollection.json", preflight),
    ]:
        write_json(output / name, value)
    print({"records_imported": len(corpus.examples), "adequacy_passed": preflight["passed"],
           "next": "collect only after all acquisition and coverage gates are satisfied"})
    raise SystemExit(0 if preflight["passed"] else 2)


if __name__ == "__main__":
    main()
