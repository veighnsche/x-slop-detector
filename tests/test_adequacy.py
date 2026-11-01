"""Budgets use synthetic records only; no human/AI accuracy claims."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from detector_eval.adequacy import InadequateStudy, POLICY, audit, require, require_cv, zero_error_budget
from detector_eval.data import PARTITIONS, digest, write_json
from test_scoring import fixture_corpus


def manual_split(corpus):
    return {
        "schema_version": "1", "corpus_sha256": digest(corpus.model_dump(mode="json")),
        "seed": 0, "reserved_family": "not-present-in-unit-fixtures",
        "rows": [
            {"id": e.id, "group": f"fixture-group-{i // 3}", "partition": PARTITIONS[(i // 3) % 5]}
            for i, e in enumerate(corpus.examples)
        ],
    }


class AdequacyTests(unittest.TestCase):
    def setUp(self):
        budget = patch.dict(POLICY, {"required_origin": None})
        budget.start()
        self.addCleanup(budget.stop)

    def test_zero_error_sample_size_is_not_rounded_down(self):
        self.assertEqual(zero_error_budget(.005, .95), 598)
        self.assertGreater(1 - .05 ** (1 / 597), .005)
        for target, confidence in [(0, .95), (.005, 1), (-1, .5)]:
            with self.assertRaises(ValueError):
                zero_error_budget(target, confidence)

    def test_rows_and_unknowns_do_not_manufacture_independent_classes(self):
        corpus, _ = fixture_corpus(15)
        # A thousand variants of one source are still just one connected group.
        original = corpus.examples[1]
        extra = [original.model_copy(update={"id": f"variant-{i}"}) for i in range(1000)]
        corpus = corpus.model_copy(update={"examples": [*corpus.examples, *extra]})
        split = manual_split(corpus)
        for r in split["rows"][-1000:]:
            r.update(group="fixture-group-0", partition="development")
        report = audit(corpus, split, [True] * len(corpus.examples), basis="synthetic")
        self.assertFalse(report["passed"])
        self.assertEqual(report["counts"]["development"]["classes"]["1"]["groups"], 3)
        self.assertEqual(report["counts"]["development"]["classes"]["1"]["rows"], 1003)
        self.assertEqual(report["counts"]["development"]["eligible_unknown_rows"], 3)

    def test_post_evidence_exclusions_reduce_group_counts(self):
        corpus, _ = fixture_corpus(15)
        split = manual_split(corpus)
        upper = audit(corpus, split, [True] * len(corpus.examples), basis="upper_bound")
        eligible = [not (r["partition"] == "calibration" and e.label == 1 and r["group"] != "fixture-group-1")
                    for e, r in zip(corpus.examples, split["rows"])]
        actual = audit(corpus, split, eligible, basis="actual")
        self.assertEqual(upper["counts"]["calibration"]["classes"]["1"]["groups"], 3)
        self.assertEqual(actual["counts"]["calibration"]["classes"]["1"]["groups"], 1)
        with self.assertRaises(InadequateStudy):
            require(corpus, split, eligible)

    def test_derived_text_cannot_fill_native_short_budget(self):
        corpus, _ = fixture_corpus(15)
        with patch.dict(POLICY, {"required_origin": "native_short"}):
            report = audit(corpus, manual_split(corpus), [True] * len(corpus.examples), basis="synthetic")
        cell = report["counts"]["development"]["classes"]["1"]
        self.assertEqual(cell["eligible_groups_all_origins"], 3)
        self.assertEqual(cell["groups"], 0)

    def test_each_partition_and_class_is_required(self):
        corpus, _ = fixture_corpus(15)
        split = manual_split(corpus)
        report = audit(corpus, split, [True] * len(corpus.examples), basis="synthetic")
        self.assertEqual({(r["partition"], r["label"]) for r in report["failures"]},
                         {(part, label) for part in PARTITIONS for label in (0, 1)})
        tampered = deepcopy(split)
        tampered["rows"][1]["group"] = "invented-independent-group"
        with self.assertRaisesRegex(ValueError, "leaks_connected"):
            audit(corpus, tampered, [True] * len(corpus.examples), basis="synthetic")

    def test_cv_cannot_have_one_positive_group(self):
        with self.assertRaisesRegex(ValueError, "inadequate_cv_groups"):
            require_cv([0, 1, 0, 1], ["a", "b", "c", "d"], [0, 1], [2, 3])
        with patch.dict(POLICY, {"minimum_cv_groups_per_class": {"train": 1, "validation": 1}}):
            with self.assertRaisesRegex(ValueError, "validation:label=1"):
                require_cv([0, 1, 0, 1], ["a", "b", "c", "d"], [0, 1], [2, 3], [True, True, True, False])

    def test_collection_rejects_before_ssh_credentials_or_network(self):
        from detector_eval.collect import main
        corpus, _ = fixture_corpus(15)
        with tempfile.TemporaryDirectory() as directory:
            study = Path(directory)
            write_json(study / "corpus.json", corpus.model_dump(mode="json"))
            write_json(study / "splits.json", manual_split(corpus))
            with patch("sys.argv", ["collect", "--study", str(study)]), \
                    patch("detector_eval.collect.subprocess.run") as ssh, \
                    patch("detector_eval.collect.httpx.Client") as client:
                with self.assertRaises(InadequateStudy):
                    main()
                ssh.assert_not_called()
                client.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "optional evaluation dependencies not installed")
    def test_fit_and_evaluate_stop_before_output_fitting_or_holdout_consumption(self):
        from detector_eval.train import fit, evaluate
        corpus, evidence = fixture_corpus(15)
        with tempfile.TemporaryDirectory() as directory:
            study = Path(directory)
            write_json(study / "corpus.json", corpus.model_dump(mode="json"))
            write_json(study / "splits.json", manual_split(corpus))
            write_json(study / "evidence.json", evidence.model_dump(mode="json"))
            with patch("detector_eval.train.fit_base", side_effect=AssertionError("must not fit")):
                with self.assertRaises(InadequateStudy):
                    fit(study, study / "run")
            self.assertFalse((study / "run").exists())
            # No frozen file is needed: adequacy is checked before even reading it.
            with self.assertRaises(InadequateStudy):
                evaluate(study, study / "run")
            self.assertFalse((study / "holdout-use.json").exists())
            self.assertEqual(POLICY["id"], "independent-groups-v1")
