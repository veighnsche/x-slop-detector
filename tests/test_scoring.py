"""Synthetic unit fixtures only. None of these labels/scores are accuracy evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from detector_eval.aitdna import import_rows
from detector_eval.data import (
    Corpus, Evidence, EvidenceSet, Example, Source, bind_evidence, connected_groups,
    digest, feature_values, split_corpus, text_hash, write_json,
)
from detector_eval.profile import Profile, load_profile
from detector_server.catalog import INITIAL_ROSTER
from detector_server.contracts import (
    CheckEvidence, ClassifierScore, Coverage, Discrepancy, WatermarkFinding, CheckerRef,
)

HAS_EVALUATION = importlib.util.find_spec("sklearn") is not None
SPECS = list(INITIAL_ROSTER)
CONFIG = "synthetic-unit-fixture-suite"


def fixture_corpus(groups=40):
    """Random-looking text avoids incidental near-duplicate links across roots."""
    examples, rows = [], []
    for group in range(groups):
        for label in (0, 1, None):
            id = f"fixture-{group}-{label}"
            text = "Synthetic test fixture " + text_hash(id) + "."
            e = Example(
                id=id, text=text, text_sha256=text_hash(text), source_id="unit-fixture",
                source_locator=id, acquired_at="unit-test-not-an-acquisition",
                author_id=f"author-{group}", root_id=f"root-{group}", language="en",
                generator_family="gemini" if label == 1 and group % 10 == 0 else "fixture" if label == 1 else None,
                cohort="synthetic_unit_fixture", derivation="synthetic_unit_fixture", label=label,
                label_basis="Artificial unit-test label, NOT human/AI provenance evidence.",
            )
            examples.append(e)
            noise = group % 7 * .001
            v = [.08 + noise, .12 + noise, .3 + noise, -1 + noise] if label != 1 else [
                .85 + noise, .75 + noise, .4 + noise, 1 + noise,
            ]
            checks = [
                CheckEvidence(
                    checker=s.checker, status="completed",
                    coverage=Coverage(characters=len(text), input_tokens=20, token_limit=512),
                    output=Discrepancy(value=v[i]) if s.kind == "statistical" else ClassifierScore(value=v[i]),
                ) for i, s in enumerate(SPECS)
            ]
            rows.append(Evidence(
                example_id=id, text_sha256=e.text_sha256, configuration_id=CONFIG,
                extraction_version="own-post-text-v1", checks=checks,
            ))
    corpus = Corpus(
        population="Artificial unit-test fixture, not a benchmark",
        sources=[Source(
            id="unit-fixture", url="https://example.invalid/unit-fixture", revision="synthetic",
            content_sha256="a" * 64, license="unit-fixture", permission_record="Own synthetic fixture",
            private_evaluation_allowed=True, redistribution_allowed=False, limitations=["Not real provenance"],
        )], examples=examples, limitations=["Synthetic unit fixtures are not validation data."],
    )
    evidence = EvidenceSet(
        corpus_sha256=digest(corpus.model_dump(mode="json")), configuration_id=CONFIG,
        runtime={"kind": "synthetic unit fixture"},
        extraction_version="own-post-text-v1", specs=SPECS, rows=rows,
    )
    return corpus, evidence


def fixture_profile():
    return Profile(
        profile_id="fixture-profile", configuration_id=CONFIG, extraction_version="own-post-text-v1",
        runtime_sha256="e" * 64,
        specs=SPECS, feature_indices=[0, 1, 2, 3],
        means=[.5, .5, .5, 0.], scales=[1., 1., 1., 2.],
        coefficients=[1., 2., 3., 4.], intercept=-1.,
        calibration_slope=.7, calibration_intercept=.2, calibration_positive_fraction=.5,
        corpus_sha256="a" * 64, split_sha256="b" * 64, fit_sha256="c" * 64,
        calibration_sha256="d" * 64, population="synthetic unit test", limitations=["Not real data."],
    )


class ScoringContractTests(unittest.TestCase):
    def test_labels_text_and_source_records_are_explicit(self):
        corpus, _ = fixture_corpus(1)
        raw = corpus.examples[0].model_dump()
        raw["text"] = "changed text"
        with self.assertRaises(ValidationError):
            Example.model_validate(raw)
        raw = corpus.examples[0].model_dump()
        raw["label"] = False
        with self.assertRaises(ValidationError):
            Example.model_validate(raw)
        raw = corpus.model_dump()
        raw["examples"].append(raw["examples"][0])
        with self.assertRaises(ValidationError):
            Corpus.model_validate(raw)

    def test_native_features_are_not_averages_and_ignore_watermarks(self):
        corpus, evidence = fixture_corpus(1)
        e, row = corpus.examples[0], evidence.rows[0]
        expected = feature_values(e, row, SPECS)
        self.assertEqual(expected[-1], -1)
        wm = CheckEvidence(
            checker=CheckerRef(id="kgw", configuration_id="fixture", artifact_revision="fixture"),
            coverage=Coverage(characters=len(e.text), token_limit=512), status="completed",
            output=WatermarkFinding(decision="detected", verification_scope="known_configuration",
                                    z_score=99, p_value=0, configuration_purpose="research_fixture"),
        )
        self.assertEqual(expected, feature_values(e, row.model_copy(update={"checks": [*row.checks, wm]}), SPECS))

    def test_unavailable_check_is_no_feature_vector_not_zero(self):
        corpus, evidence = fixture_corpus(1)
        e, row = corpus.examples[0], evidence.rows[0]
        absent = row.checks[0].model_copy(update={"status": "unavailable", "reason": "model_not_loaded", "output": None})
        modified = row.model_copy(update={"checks": [absent, *row.checks[1:]]})
        self.assertIsNone(feature_values(e, modified, SPECS))
        wrong = row.checks[1].model_copy(update={
            "checker": row.checks[1].checker.model_copy(update={"artifact_revision": "wrong"}),
        })
        with self.assertRaisesRegex(ValueError, "invalid_evidence_configuration"):
            feature_values(e, modified.model_copy(update={"checks": [absent, wrong, *row.checks[2:]]}), SPECS)

    def test_wrong_hash_revision_duplicate_and_corpus_change_reject(self):
        corpus, evidence = fixture_corpus(1)
        with self.assertRaisesRegex(ValueError, "not_bound"):
            feature_values(corpus.examples[0], evidence.rows[0].model_copy(update={"text_sha256": "bad"}), SPECS)
        row = evidence.rows[0].model_copy(update={"checks": [*evidence.rows[0].checks, evidence.rows[0].checks[0]]})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            feature_values(corpus.examples[0], row, SPECS)
        with self.assertRaisesRegex(ValueError, "corpus_changed"):
            bind_evidence(corpus.model_copy(update={"population": "changed"}), evidence)

    def test_author_root_prompt_and_duplicate_constraints_are_transitive(self):
        corpus, _ = fixture_corpus(3)
        a = corpus.examples[0].model_copy(update={"extra_groups": ["prompt:shared"]})
        b = corpus.examples[3].model_copy(update={"extra_groups": ["prompt:shared"]})
        c = corpus.examples[4]  # Same author/root as b.
        d = corpus.examples[6].model_copy(update={"text": a.text, "text_sha256": a.text_sha256})
        groups = connected_groups([a, b, c, d])
        self.assertEqual(len(set(groups)), 1)

    def test_near_duplicate_normalization_is_not_scored_text_normalization(self):
        corpus, _ = fixture_corpus(2)
        a = corpus.examples[0]
        text = a.text.replace("Synthetic", "SYNTHETIC").replace(" ", "  ")
        b = corpus.examples[3].model_copy(update={"text": text, "text_sha256": text_hash(text)})
        self.assertEqual(len(set(connected_groups([a, b]))), 1)
        self.assertNotEqual(a.text, b.text)

    def test_importer_never_converts_ambiguous_polish_to_a_binary_label(self):
        rows = [
            {"metadata": {"author": "anon", "human_only": True, "model": ""},
             "data": [{"author": "User", "text": "Human source 😀.\nA second sentence.", "queries": []}]},
            {"metadata": {"author": "anon", "human_only": False, "model": "gpt-test"},
             "data": [{"author": "Bot", "text": "Polished source.", "queries": ["Polish this text"]}]},
        ]
        corpus = import_rows(rows, "unit-test")
        self.assertTrue(any("😀" in e.text for e in corpus.examples))
        self.assertEqual([e.label for e in corpus.examples if e.root_id.endswith("-1")], [None])
        rows[0]["data"][0]["author"] = "Bot"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            import_rows(rows, "unit-test")

    def test_profile_integrity_dimensions_native_scope_and_no_deployment(self):
        p = fixture_profile()
        corpus, evidence = fixture_corpus(1)
        with self.assertRaisesRegex(ValueError, "not_approved"):
            p.score_evidence(corpus.examples[0], evidence.rows[0])
        self.assertTrue(0 < p.score_evidence(corpus.examples[0], evidence.rows[0], benchmark=True) < 1)
        self.assertIsNone(p.score_evidence(
            corpus.examples[0].model_copy(update={"language": "fr"}), evidence.rows[0], benchmark=True,
        ))
        for vector in ([.1], [False, .2, .3, 4.], [.1, .2, .3, float("nan")]):
            with self.assertRaises(ValueError):
                p.predict(vector)
        for patch in ({"scales": [0., 1., 1., 1.]}, {"coefficients": [1.]}, {"deployment_approved": True}):
            with self.assertRaises(ValidationError):
                Profile.model_validate({**p.model_dump(), **patch})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            write_json(path, p.envelope())
            self.assertEqual(p, load_profile(path))
            raw = json.loads(path.read_text()); raw["profile"]["intercept"] += 1
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "integrity"):
                load_profile(path)

    def test_profile_import_has_no_heavy_dependencies(self):
        subprocess.run([sys.executable, "-c", (
            "import sys; import detector_eval.profile; "
            "assert all(n not in sys.modules for n in ('torch','transformers','numpy','sklearn'))"
        )], check=True)


@unittest.skipUnless(HAS_EVALUATION, "optional evaluation dependencies not installed")
class ScoringEvaluationTests(unittest.TestCase):
    def setUp(self):
        # Only in-process synthetic unit fixtures use reduced budgets. There is
        # no CLI switch to weaken the real study's acquisition floors.
        from detector_eval.adequacy import POLICY
        budget = patch.dict(POLICY, {
            "id": "synthetic-unit-fixture-not-a-benchmark",
            "required_origin": None,
            "minimum_groups_per_class": {
                p: {"0": 2, "1": 2}
                for p in ("development", "calibration", "operating", "holdout", "challenge")
            },
            "minimum_cv_groups_per_class": {"train": 2, "validation": 1},
        })
        budget.start()
        self.addCleanup(budget.stop)

    def test_group_split_and_reserved_generator(self):
        corpus, _ = fixture_corpus(40)
        split = split_corpus(corpus, 42, "gemini")
        seen = {}
        for e, row in zip(corpus.examples, split["rows"]):
            seen.setdefault(e.author_id, set()).add(row["partition"])
            if e.generator_family == "gemini":
                self.assertEqual(row["partition"], "challenge")
        self.assertTrue(all(len(p) == 1 for p in seen.values()))

    def test_cluster_rates_and_zero_error_bound_do_not_count_variants_as_authors(self):
        from detector_eval.metrics import point_metrics, bootstrap_rates
        y = [0] * 600
        p = [.1] * 600
        independent = point_metrics(y, p, list(map(str, range(600))), .9)
        correlated = point_metrics(y, p, [str(i % 3) for i in range(600)], .9)
        self.assertLess(independent["any_false_flag_per_negative_group_one_sided_95_upper"], .005)
        self.assertGreater(correlated["any_false_flag_per_negative_group_one_sided_95_upper"], .6)
        rates = point_metrics([0, 0, 0, 1], [.1, .1, .9, .8], ["a", "a", "b", "a"], .5)
        self.assertEqual(rates["fpr_group_weighted"], .5)
        self.assertIn("Zero observed errors", bootstrap_rates(y, p, [str(i % 3) for i in range(600)], .9)["warning"])

    def test_fit_freeze_evaluate_reproduce_and_block_holdout_reselection(self):
        from detector_eval.train import fit, evaluate
        corpus, evidence = fixture_corpus(40)
        split = split_corpus(corpus, 42, "gemini")
        with tempfile.TemporaryDirectory() as directory:
            study = Path(directory)
            write_json(study / "corpus.json", corpus.model_dump(mode="json"))
            write_json(study / "evidence.json", evidence.model_dump(mode="json"))
            write_json(study / "splits.json", split)
            run = study / "run"
            fit(study, run)
            self.assertFalse((run / "report.json").exists())
            self.assertFalse((study / "holdout-use.json").exists())
            p = load_profile(run / "full_suite.json")
            self.assertEqual(p.validation_state, "benchmark_only")
            evaluate(study, run)
            report = json.loads((run / "report.json").read_text())
            self.assertFalse(report["release"]["approved"])
            self.assertIn("primary_false_positive_target_not_established", report["release"]["blockers"])
            self.assertIn("unknown", report["coverage"]["class"])
            self.assertIsNone(report["partitions"]["holdout"]["models"]["raw_tabularis_score_reference"]["fpr_group_weighted"])
            evaluate(study, run)  # Exact frozen reproduction, not fitting again.
            frozen = json.loads((run / "frozen.json").read_text())
            frozen["candidates"]["full_suite"]["thresholds"]["0.005"] = .123
            (run / "frozen.json").write_text(json.dumps(frozen))
            with self.assertRaisesRegex(ValueError, "holdout_already_consumed"):
                evaluate(study, run)

    def test_split_tampering_cannot_leak_derivatives(self):
        from detector_eval.train import load_study
        corpus, evidence = fixture_corpus(40)
        split = split_corpus(corpus, 42, "gemini")
        with tempfile.TemporaryDirectory() as directory:
            study = Path(directory)
            write_json(study / "corpus.json", corpus.model_dump(mode="json"))
            write_json(study / "evidence.json", evidence.model_dump(mode="json"))
            split["rows"][0]["partition"] = "development"
            write_json(study / "splits.json", split)
            with self.assertRaisesRegex(ValueError, "leaks_connected"):
                load_study(study)

    def test_final_feature_values_do_not_affect_fit_or_calibration(self):
        from detector_eval.train import fit
        corpus, evidence = fixture_corpus(40)
        split = split_corpus(corpus, 42, "gemini")
        with tempfile.TemporaryDirectory() as directory:
            study = Path(directory)
            write_json(study / "corpus.json", corpus.model_dump(mode="json"))
            write_json(study / "splits.json", split)
            path = study / "evidence.json"
            write_json(path, evidence.model_dump(mode="json"))
            fit(study, study / "first")
            changed = evidence.model_dump(mode="json")
            for record, partition in zip(changed["rows"], split["rows"]):
                if partition["partition"] in ("holdout", "challenge"):
                    for check in record["checks"]:
                        if check["output"]["kind"] == "classifier_ai_score":
                            check["output"]["value"] = 1 - check["output"]["value"]
                        else:
                            check["output"]["value"] *= -1
            path.write_text(json.dumps(changed))
            fit(study, study / "second")
            a = load_profile(study / "first/full_suite.json")
            b = load_profile(study / "second/full_suite.json")
            for name in ("means", "scales", "coefficients", "intercept",
                         "calibration_slope", "calibration_intercept", "fit_sha256", "calibration_sha256"):
                self.assertEqual(getattr(a, name), getattr(b, name))
