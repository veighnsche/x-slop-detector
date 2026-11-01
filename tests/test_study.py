"""Offline proposal/assignment checks; no recruitment, people or payments."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from detector_eval.data import PARTITIONS
from detector_eval.study import DEFAULT, PILOT_FAMILY_SENTINEL, allocations, budget, prepare, preassigned_split
from test_scoring import fixture_corpus


class StudyTests(unittest.TestCase):
    def test_costs_include_both_reviewers_training_fees_and_contingency(self):
        result = budget(DEFAULT, 30)
        self.assertEqual(result["participant_reward_each"], "5.00")
        self.assertEqual(result["writing_rewards"], "150.00")
        self.assertEqual(result["review_hours"], "10")
        self.assertEqual(result["review_rewards"], "250.00")
        self.assertEqual(result["reviewer_training_rewards"], "100.00")
        self.assertEqual(result["platform_fee_on_all_rewards"], "214.29")
        self.assertEqual(result["with_contingency_before_vat"], "857.14")
        self.assertEqual(result["with_contingency_and_illustrative_vat"], "908.57")

    def test_invalid_or_underpaid_budget_rejects(self):
        for field, value in [
            ("participant_hourly", "7.00"), ("reviewers_per_block", -1),
            ("reviewer_hourly", "NaN"), ("contingency_fraction", "1.0"),
        ]:
            plan = deepcopy(DEFAULT);plan[field] = value
            with self.assertRaises(ValueError):
                budget(plan, 30)

    def test_allocations_match_unequal_quotas_not_equal_folds(self):
        result = allocations(DEFAULT, "main")
        self.assertEqual(Counter(s["partition"] for s in result["slots"]), DEFAULT["main_slots"])
        self.assertEqual(len(result["slots"]), 1725)
        self.assertEqual(result, allocations(DEFAULT, "main"))
        self.assertEqual(len({s["id"] for s in result["slots"]}), 1725)
        bad = deepcopy(DEFAULT);bad["main_slots"]["holdout"] = 599
        with self.assertRaisesRegex(ValueError, "below_adequacy"):
            allocations(bad, "main")

    def test_pilot_never_populates_calibration_operating_or_final_test(self):
        result = allocations(DEFAULT, "pilot")
        self.assertEqual(len(result["slots"]), 30)
        self.assertEqual({s["partition"] for s in result["slots"]}, {"development"})
        self.assertEqual(result["reserved_family"], PILOT_FAMILY_SENTINEL)
        corpus, _ = fixture_corpus(8)
        author_slots = {f"author-{i}": result["slots"][i]["id"] for i in range(8)}
        split = preassigned_split(corpus, result, author_slots, PILOT_FAMILY_SENTINEL)
        self.assertEqual({r["partition"] for r in split["rows"]}, {"development"})

    def test_main_assignments_preserve_authors_and_reserved_family(self):
        corpus, _ = fixture_corpus(10)
        plan = deepcopy(DEFAULT);plan["reserved_generator_family"] = "gemini"
        allocation = allocations(plan, "main")
        slots = {part: [s["id"] for s in allocation["slots"] if s["partition"] == part] for part in PARTITIONS}
        mapping = {}
        for i in range(10):
            part = "challenge" if i == 0 else PARTITIONS[i % 4]
            mapping[f"author-{i}"] = slots[part].pop()
        split = preassigned_split(corpus, allocation, mapping, "gemini")
        for e, row in zip(corpus.examples, split["rows"]):
            if e.generator_family == "gemini":
                self.assertEqual(row["partition"], "challenge")
        wrong = dict(mapping);wrong["author-0"] = slots["development"].pop()
        with self.assertRaisesRegex(ValueError, "reserved_family_leakage"):
            preassigned_split(corpus, allocation, wrong, "gemini")

    def test_linked_sources_cannot_be_reassigned_to_meet_quotas(self):
        corpus, _ = fixture_corpus(2)
        # Two declared authors share a real prompt/source: they are one component.
        examples = [e.model_copy(update={"extra_groups": ["prompt:shared"]}) for e in corpus.examples]
        corpus = corpus.model_copy(update={"examples": examples})
        plan = deepcopy(DEFAULT);plan["reserved_generator_family"] = "not-in-unit-corpus"
        allocation = allocations(plan, "main")
        slots = {part: next(s["id"] for s in allocation["slots"] if s["partition"] == part) for part in PARTITIONS}
        with self.assertRaisesRegex(ValueError, "leaks_connected"):
            preassigned_split(corpus, allocation,
                              {"author-0": slots["development"], "author-1": slots["holdout"]},
                              "not-in-unit-corpus")
        with self.assertRaisesRegex(ValueError, "reused_author_slot"):
            preassigned_split(corpus, allocation,
                              {"author-0": slots["development"], "author-1": slots["development"]},
                              "not-in-unit-corpus")

    def test_preparation_is_private_draft_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pack"
            result = prepare(path)
            self.assertTrue(result["main_is_not_authorized"])
            self.assertFalse(json.loads((path / "launch-blockers.json").read_text())["may_launch"])
            self.assertFalse(path.stat().st_mode & 0o077)
            self.assertIsNone(json.loads((path / "plan.json").read_text())["spend_approval_reference"])
            with self.assertRaises(FileExistsError):
                prepare(path)

    def test_cli_only_prepares_a_local_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cli-pack"
            result = subprocess.run(
                [sys.executable, "-m", "detector_eval.study", "--output", str(path)],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("'may_launch': False", result.stdout)
            self.assertEqual(set(p.name for p in path.iterdir()),
                             {"plan.json", "budget.json", "pilot-allocation.json",
                              "main-allocation.json", "launch-blockers.json"})
