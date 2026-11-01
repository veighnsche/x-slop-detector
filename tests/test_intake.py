"""Synthetic intake files exercise provenance plumbing, not genuine consent/data."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pydantic import ValidationError

from detector_eval.intake import Bundle, convert


def fixture_bundle(root, workflow="unaided", origin="native_short"):
    artifacts = []

    def add(id, kind, text):
        path = root / f"{id}.txt"
        path.write_bytes(text.encode())
        artifacts.append({"id": id, "kind": kind, "path": path.name,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return id

    add("permission", "permission", "SYNTHETIC TEST ONLY. No participant, consent or grant exists.")
    add("final", "final_text", "Synthetic test record 😀.\nNot human/AI benchmark data.")
    process = [add("declaration", "assistance_declaration", "Synthetic tool-use declaration")]
    if workflow != "generated":
        process.append(add("writing", "writing_log", '{"kind":"synthetic unit-test events"}'))
    if workflow in {"human_edited_ai", "mixed", "mechanical_only", "ideas_only"}:
        process.append(add("edits", "edit_log", '{"kind":"synthetic unit-test edit events"}'))
    generation = None
    if workflow in {"generated", "rewritten", "translated", "human_edited_ai", "mixed", "ideas_only"}:
        generation = {
            "model_id": "synthetic-model", "model_revision": "not-a-model", "family": "unit-fixture",
            "prompt_artifact_id": add("prompt", "generation_prompt", "Synthetic prompt, not generated"),
            "output_artifact_id": add("output", "generation_output", (root / "final.txt").read_text()),
            "config_artifact_id": add("config", "generation_config", '{"kind":"synthetic test configuration"}'),
        }
    ids = [a["id"] for a in artifacts]
    reviews = [{"reviewer_id": f"fixture-reviewer-{i}", "method": "human_process_review",
                "decision": "negative" if workflow in {"unaided", "mechanical_only", "ideas_only"} else "positive",
                "evidence_artifact_ids": ids, "rationale": "Synthetic test review, not a real person or judgment."}
               for i in range(2)]
    return {
        "schema_version": "1", "population": "Synthetic unit tests, never an accuracy corpus",
        "sources": [{
            "id": "unit-source", "url": "https://example.invalid/synthetic-test",
            "revision": "unit-test", "license": "Synthetic fixture only",
            "permission_artifact_id": "permission", "private_evaluation_allowed": True,
            "redistribution_allowed": False, "limitations": ["No genuine writing-process evidence."],
        }],
        "artifacts": artifacts,
        "records": [{
            "id": "record", "source_id": "unit-source", "author_id": "pseudonymous-fixture",
            "root_id": "fixture-root", "prompt_group": "fixture-prompt", "topic_group": "fixture-topic",
            "event_group": "fixture-event", "acquired_at": "2026-11-01T00:00:00Z",
            "language": "en", "workflow": workflow, "origin": origin, "final_artifact_id": "final",
            "process_artifact_ids": process, "generation": generation, "reviews": reviews,
            "content_tags": ["reply", "emoji"],
        }],
    }


class IntakeTests(unittest.TestCase):
    def test_exact_bytes_provenance_permissions_and_groups_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); raw = fixture_bundle(root)
            corpus, summary = convert(Bundle.model_validate(raw), root)
            e = corpus.examples[0]
            self.assertEqual(e.text.encode(), (root / "final.txt").read_bytes())
            self.assertEqual(e.label, 0)
            self.assertEqual(e.derivation, "native_short")
            self.assertEqual(e.extra_groups[:3], ["prompt:fixture-prompt", "topic:fixture-topic", "event:fixture-event"])
            self.assertIn("process-artifact:writing", e.extra_groups)
            self.assertFalse(corpus.sources[0].redistribution_allowed)
            self.assertEqual(summary["labels"], {"0": 1})
            self.assertEqual(summary["content_tags"]["emoji"], 1)

    def test_all_workflows_have_process_not_style_labels(self):
        for workflow, label in [
            ("unaided", 0), ("generated", 1), ("rewritten", 1), ("translated", 1),
            ("human_edited_ai", 1), ("mixed", 1), ("mechanical_only", 0), ("ideas_only", 0),
        ]:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as directory:
                root = Path(directory);raw = fixture_bundle(root, workflow)
                corpus, _ = convert(Bundle.model_validate(raw), root)
                self.assertEqual(corpus.examples[0].label, label)

    def test_disagreement_unknown_or_missing_review_never_becomes_human(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);raw = fixture_bundle(root, "generated")
            for reviews in [
                [], raw["records"][0]["reviews"][:1],
                [{**r, "decision": "unknown"} for r in raw["records"][0]["reviews"]],
                [raw["records"][0]["reviews"][0], {**raw["records"][0]["reviews"][1], "decision": "negative"}],
            ]:
                changed = deepcopy(raw);changed["records"][0]["reviews"] = reviews
                corpus, _ = convert(Bundle.model_validate(changed), root)
                self.assertIsNone(corpus.examples[0].label)

    def test_llm_mechanical_assistance_is_not_automatically_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);raw = fixture_bundle(root, "ideas_only")
            raw["records"][0]["workflow"] = "mechanical_only"
            corpus, _ = convert(Bundle.model_validate(raw), root)
            self.assertEqual(corpus.examples[0].label, 0)
            self.assertEqual(corpus.examples[0].generator_family, "unit-fixture")

    def test_invalid_permissions_hash_paths_and_foreign_review_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);raw = fixture_bundle(root)
            raw["sources"][0]["private_evaluation_allowed"] = False
            with self.assertRaises(ValidationError):
                Bundle.model_validate(raw)
            raw["sources"][0]["private_evaluation_allowed"] = True
            for change, error in [
                (lambda v: v["artifacts"][0].update(sha256="0" * 64), "hash_or_size"),
                (lambda v: v["artifacts"][0].update(path="../outside-workspace.txt"), "escapes"),
                (lambda v: v["records"][0]["reviews"][0].update(evidence_artifact_ids=["foreign"]), "foreign"),
                (lambda v: v["records"][0]["reviews"][0].update(evidence_artifact_ids=["final"]), "cover_required"),
            ]:
                changed = deepcopy(raw);change(changed)
                with self.assertRaisesRegex(ValueError, error):
                    convert(Bundle.model_validate(changed), root)

    def test_duplicate_reviewers_missing_logs_and_workflow_conflicts_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);raw = fixture_bundle(root)
            changed = deepcopy(raw);changed["records"][0]["reviews"][1]["reviewer_id"] = "fixture-reviewer-0"
            with self.assertRaises(ValidationError):
                Bundle.model_validate(changed)
            changed = deepcopy(raw);changed["records"][0]["process_artifact_ids"] = ["declaration"]
            with self.assertRaisesRegex(ValueError, "missing_required"):
                convert(Bundle.model_validate(changed), root)
            changed = deepcopy(raw)
            for review in changed["records"][0]["reviews"]:
                review["decision"] = "positive"
            with self.assertRaisesRegex(ValueError, "conflict_with_workflow"):
                convert(Bundle.model_validate(changed), root)

    def test_generation_output_and_short_origin_are_not_silently_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);raw = fixture_bundle(root, "generated")
            (root / "output.txt").write_text("Different generated output")
            for a in raw["artifacts"]:
                if a["id"] == "output":
                    a["sha256"] = hashlib.sha256((root / "output.txt").read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "verbatim_generation_differs"):
                convert(Bundle.model_validate(raw), root)
            raw = fixture_bundle(root)
            (root / "final.txt").write_text("😀" * 281)
            for a in raw["artifacts"]:
                if a["id"] == "final":
                    a["sha256"] = hashlib.sha256((root / "final.txt").read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "native_short_exceeds"):
                convert(Bundle.model_validate(raw), root)

    def test_schema_cli_writes_no_fake_records_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            command = [sys.executable, "-m", "detector_eval.intake", "schema", "--output", str(path)]
            subprocess.run(command, check=True, capture_output=True)
            self.assertIn("records", json.loads(path.read_text())["properties"])
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "optional evaluation dependencies not installed")
    def test_import_cli_prepares_real_files_but_refuses_insufficient_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            combined = {"schema_version": "1", "population": "Synthetic CLI test only",
                        "sources": [], "artifacts": [], "records": []}
            for i in range(12):
                prefix = f"g{i}-";sub = root / prefix;sub.mkdir()
                raw = fixture_bundle(sub, "generated" if i % 2 else "unaided")
                text = "Synthetic CLI fixture " + hashlib.sha256(prefix.encode()).hexdigest()
                for a in raw["artifacts"]:
                    if a["kind"] in {"final_text", "generation_output"}:
                        (sub / a["path"]).write_text(text)
                        a["sha256"] = hashlib.sha256(text.encode()).hexdigest()
                    a["id"] = prefix + a["id"]
                    a["path"] = prefix + "/" + a["path"]
                source = raw["sources"][0]
                source["id"] = prefix + source["id"]
                source["permission_artifact_id"] = prefix + source["permission_artifact_id"]
                r = raw["records"][0]
                for name in ["id", "source_id", "author_id", "root_id", "prompt_group",
                             "topic_group", "event_group", "final_artifact_id"]:
                    r[name] = prefix + r[name]
                r["process_artifact_ids"] = [prefix + id for id in r["process_artifact_ids"]]
                for review in r["reviews"]:
                    review["evidence_artifact_ids"] = [prefix + id for id in review["evidence_artifact_ids"]]
                if r["generation"]:
                    for name in ["prompt_artifact_id", "output_artifact_id", "config_artifact_id"]:
                        r["generation"][name] = prefix + r["generation"][name]
                    r["generation"]["family"] = "reserved-fixture" if i == 1 else "other-fixture"
                for key in ["sources", "artifacts", "records"]:
                    combined[key].extend(raw[key])
            bundle = root / "bundle.json";bundle.write_text(json.dumps(combined))
            output = root / "study"
            result = subprocess.run([
                sys.executable, "-m", "detector_eval.intake", "import",
                "--bundle", str(bundle), "--artifacts", str(root), "--output", str(output),
                "--reserved-family", "reserved-fixture",
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(len(json.loads((output / "corpus.json").read_text())["examples"]), 12)
            self.assertFalse(json.loads((output / "adequacy-precollection.json").read_text())["passed"])
            self.assertFalse((output / "evidence.json").exists())
            self.assertFalse(output.stat().st_mode & 0o077)
            from detector_eval.study import DEFAULT, PILOT_FAMILY_SENTINEL, allocations
            allocation = allocations(DEFAULT, "pilot")
            allocation_path = root / "allocation.json"
            allocation_path.write_text(json.dumps(allocation))
            author_slots = {r["author_id"]: allocation["slots"][i]["id"]
                            for i, r in enumerate(combined["records"])}
            mapping_path = root / "author-slots.json"
            mapping_path.write_text(json.dumps(author_slots))
            pilot_output = root / "pilot-study"
            result = subprocess.run([
                sys.executable, "-m", "detector_eval.intake", "import",
                "--bundle", str(bundle), "--artifacts", str(root), "--output", str(pilot_output),
                "--reserved-family", PILOT_FAMILY_SENTINEL,
                "--allocation", str(allocation_path), "--author-slots", str(mapping_path),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            pilot_split = json.loads((pilot_output / "splits.json").read_text())
            self.assertEqual({r["partition"] for r in pilot_split["rows"]}, {"development"})
            self.assertIn("allocation_sha256", pilot_split)
            self.assertFalse((pilot_output / "holdout-use.json").exists())
