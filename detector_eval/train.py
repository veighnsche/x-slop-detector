"""Separate fit/freeze and final evaluation commands. No production activation."""
import argparse
from collections import Counter
from importlib.metadata import version
from pathlib import Path
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from .data import (
    Corpus, EvidenceSet, ROSTER, bind_evidence, digest, read_json,
    validate_split, write_json,
)
from .adequacy import POLICY, require, require_cv
from .metrics import (
    bootstrap_rates, char_bucket, operating_threshold, paired_cluster_interval,
    point_metrics, probability_losses, weights, word_bucket,
)
from .profile import Profile, load_profile, sigmoid

PLAN = {
    "adequacy_policy": POLICY,
    "method": "development-only weighted StandardScaler + L2 logistic stack; separate L2 sigmoid calibration",
    "C": 1.0, "calibration_C": 1.0, "solver": "lbfgs", "max_iter": 2000, "tol": 1e-10,
    "weighting": "one unit of training mass per connected group; equal mass within group",
    "baseline_selection": "development grouped CV log loss, before calibration/operating/final evaluation",
    "threshold_targets": [0.005, 0.01], "seed": 20261101,
    "bootstrap_resamples": 1000, "reliability_bins": 10,
    "hypothetical_prior_sensitivity": [0.01, 0.1, 0.5],
    "scope": "English; all four native checks complete; benchmark population only",
    "release": "never enabled by this offline command",
}
CANDIDATES = {
    "full_suite": [0, 1, 2, 3],
    **{f"single_{id}": [i] for i, id in enumerate(ROSTER)},
    **{f"without_{id}": [j for j in range(4) if j != i] for i, id in enumerate(ROSTER)},
}


def load_study(directory):
    study = Path(directory)
    corpus = Corpus.model_validate(read_json(study / "corpus.json"))
    evidence = EvidenceSet.model_validate(read_json(study / "evidence.json"))
    features = bind_evidence(corpus, evidence)
    split = read_json(study / "splits.json")
    validate_split(corpus, split)
    eligible = [v is not None and e.language == "en" and len(e.text) <= 10000
                for e, v in zip(corpus.examples, features)]
    labeled = [ok and e.label is not None for e, ok in zip(corpus.examples, eligible)]
    return study, corpus, evidence, features, split, eligible, labeled


def arrays(corpus, features, rows, indices):
    return (
        np.asarray([features[i] for i in indices], dtype=float),
        np.asarray([corpus.examples[i].label for i in indices], dtype=int),
        np.asarray([rows[i]["group"] for i in indices]),
    )


def fit_base(x, y, groups, indices):
    if len(set(y)) != 2:
        raise ValueError("fitting_requires_both_provenance_classes")
    w = weights(groups)
    scale = StandardScaler().fit(x[:, indices], sample_weight=w)
    model = LogisticRegression(
        C=PLAN["C"], solver=PLAN["solver"], max_iter=PLAN["max_iter"], tol=PLAN["tol"],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(scale.transform(x[:, indices]), y, sample_weight=w)
    return scale, model


def select_baseline(x, y, groups, budget_eligible):
    positive_groups = len(set(groups[y == 1]))
    negative_groups = len(set(groups[y == 0]))
    folds = min(3, positive_groups, negative_groups)
    if folds < 2:
        raise ValueError("not_enough_groups_for_development_baseline_selection")
    cv = list(StratifiedGroupKFold(
        n_splits=folds, shuffle=True, random_state=PLAN["seed"],
    ).split(x, y, groups))
    for train, test in cv:
        require_cv(y, groups, train, test, budget_eligible)
    scores = {}
    for name, indices in CANDIDATES.items():
        if not name.startswith("single_"):
            continue
        predictions = np.empty(len(y))
        for train, test in cv:
            scaler, model = fit_base(x[train], y[train], groups[train], indices)
            p = model.predict_proba(scaler.transform(x[test][:, indices]))[:, 1]
            predictions[test] = p
        _, logloss = probability_losses(y, predictions)
        scores[name] = float(np.average(logloss, weights=weights(groups)))
    return min(scores, key=lambda name: (scores[name], name)), scores


def fit(directory, output):
    study, corpus, evidence, values, split, eligible, labeled = load_study(directory)
    adequacy = require(corpus, split, eligible)
    rows = split["rows"]
    dev = [i for i, r in enumerate(rows) if labeled[i] and r["partition"] == "development"]
    cal = [i for i, r in enumerate(rows) if labeled[i] and r["partition"] == "calibration"]
    op = [i for i, r in enumerate(rows) if labeled[i] and r["partition"] == "operating"]
    xd, yd, gd = arrays(corpus, values, rows, dev)
    xc, yc, gc = arrays(corpus, values, rows, cal)
    xo, yo, go = arrays(corpus, values, rows, op)
    if len(set(yc)) != 2:
        raise ValueError("calibration_requires_both_provenance_classes")
    best, cv = select_baseline(xd, yd, gd, [
        POLICY["required_origin"] is None or corpus.examples[i].derivation == POLICY["required_origin"]
        for i in dev
    ])
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    corpus_sha = digest(corpus.model_dump(mode="json"))
    split_sha = digest(split)

    def subset_hash(indices):
        return digest([{"id": corpus.examples[i].id, "features": values[i], "label": corpus.examples[i].label}
                       for i in indices])

    frozen = {
        "schema_version": "1", "plan": PLAN,
        "adequacy": adequacy,
        "versions": {n: version(n) for n in ("numpy", "scipy", "scikit-learn", "pydantic")},
        "corpus_sha256": corpus_sha, "split_sha256": split_sha,
        "evidence_sha256": digest(evidence.model_dump(mode="json")),
        "selected_individual_baseline": best, "development_cv_log_loss": cv,
        "candidates": {},
    }
    for name, indices in CANDIDATES.items():
        scale, model = fit_base(xd, yd, gd, indices)
        margins = model.decision_function(scale.transform(xc[:, indices]))
        calibrator = LogisticRegression(
            C=PLAN["calibration_C"], solver=PLAN["solver"],
            max_iter=PLAN["max_iter"], tol=PLAN["tol"],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            calibrator.fit(margins.reshape(-1, 1), yc, sample_weight=weights(gc))
        profile = Profile(
            profile_id=f"pilot-{name.replace('_', '-')}-v1",
            configuration_id=evidence.configuration_id, extraction_version=evidence.extraction_version,
            runtime_sha256=digest(evidence.runtime),
            specs=evidence.specs, feature_indices=indices,
            means=scale.mean_.tolist(), scales=scale.scale_.tolist(),
            coefficients=model.coef_[0].tolist(), intercept=float(model.intercept_[0]),
            calibration_slope=float(calibrator.coef_[0, 0]),
            calibration_intercept=float(calibrator.intercept_[0]),
            calibration_positive_fraction=float(np.average(yc, weights=weights(gc))),
            corpus_sha256=corpus_sha, split_sha256=split_sha,
            fit_sha256=subset_hash(dev), calibration_sha256=subset_hash(cal),
            population=corpus.population, limitations=corpus.limitations,
        )
        # Verify portable inference is numerically the fitted estimator, not a
        # hand-coded approximation with different transformations.
        expected = calibrator.predict_proba(model.decision_function(
            scale.transform(xo[:, indices]),
        ).reshape(-1, 1))[:, 1]
        actual = np.asarray([profile.predict(v) for v in xo])
        if not np.allclose(expected, actual, rtol=1e-12, atol=1e-12):
            raise ValueError("portable_profile_disagrees_with_estimator")
        path = out / f"{name}.json"
        write_json(path, profile.envelope())
        thresholds = {
            str(target): operating_threshold(yo, actual, go, target)
            for target in PLAN["threshold_targets"]
        }
        frozen["candidates"][name] = {
            "file": path.name, "sha256": profile.envelope()["sha256"], "thresholds": thresholds,
            "calibration_orientation_reversed": profile.calibration_slope <= 0,
        }
    # Written BEFORE any final/challenge metrics are computed. evaluate never fits.
    write_json(out / "frozen.json", frozen)
    print({"frozen": str(out), "baseline": best, "final_holdout_evaluated": False})


def coverage(corpus, rows, eligible):
    out = {}
    axes = {
        "partition": lambda i, e: rows[i]["partition"],
        "cohort": lambda i, e: e.cohort,
        "language": lambda i, e: e.language,
        "characters": lambda i, e: char_bucket(e.text),
        "words_whitespace_english": lambda i, e: word_bucket(e.text),
        "generator": lambda i, e: e.generator_family or "human",
        "class": lambda i, e: "unknown" if e.label is None else str(e.label),
    }
    for axis, key in axes.items():
        buckets = {}
        for i, e in enumerate(corpus.examples):
            b = buckets.setdefault(key(i, e), {"total": 0, "evidence_complete_supported": 0, "known_labels": 0})
            b["total"] += 1
            b["evidence_complete_supported"] += int(eligible[i])
            b["known_labels"] += int(e.label is not None)
        for b in buckets.values():
            b["coverage"] = b["evidence_complete_supported"] / b["total"]
        out[axis] = buckets
    return out


def evaluate(directory, run):
    study, corpus, evidence, values, split, eligible, labeled = load_study(directory)
    adequacy = require(corpus, split, eligible)
    out = Path(run)
    frozen = read_json(out / "frozen.json")
    if frozen.get("adequacy") != adequacy:
        raise ValueError("frozen_adequacy_changed")
    if frozen["plan"] != PLAN:
        raise ValueError("frozen_plan_changed")
    if frozen["versions"] != {n: version(n) for n in ("numpy", "scipy", "scikit-learn", "pydantic")}:
        raise ValueError("evaluation_environment_changed")
    if (frozen["corpus_sha256"] != digest(corpus.model_dump(mode="json")) or
            frozen["split_sha256"] != digest(split) or
            frozen["evidence_sha256"] != digest(evidence.model_dump(mode="json"))):
        raise ValueError("frozen_study_changed")
    if set(frozen["candidates"]) != set(CANDIDATES):
        raise ValueError("frozen_candidate_set_changed")
    profiles = {}
    for name, record in frozen["candidates"].items():
        if record["file"] != f"{name}.json":
            raise ValueError("invalid_profile_file")
        profile = load_profile(out / record["file"])
        if (profile.envelope()["sha256"] != record["sha256"] or
                profile.corpus_sha256 != frozen["corpus_sha256"] or
                profile.split_sha256 != frozen["split_sha256"] or
                profile.configuration_id != evidence.configuration_id or
                profile.extraction_version != evidence.extraction_version or
                profile.runtime_sha256 != digest(evidence.runtime) or
                profile.specs != evidence.specs or
                profile.feature_indices != CANDIDATES[name]):
            raise ValueError("frozen_profile_changed")
        profiles[name] = profile
    receipt = {"frozen_sha256": digest(frozen), "split_sha256": digest(split)}
    ledger = study / "holdout-use.json"
    if ledger.exists():
        if read_json(ledger) != receipt:
            raise ValueError("holdout_already_consumed_for_different_frozen_model")
    else:
        write_json(ledger, receipt)
    rows = split["rows"]
    report = {
        "schema_version": "1", "study": "process-provenance pilot, not validated X probability",
        "receipt": receipt, "population": corpus.population, "limitations": corpus.limitations,
        "configuration_id": evidence.configuration_id, "runtime": evidence.runtime,
        "full_suite_artifact_sha256": frozen["candidates"]["full_suite"]["sha256"],
        "selected_individual_baseline": frozen["selected_individual_baseline"],
        "development_cv_log_loss": frozen["development_cv_log_loss"],
        "adequacy": adequacy,
        "coverage": coverage(corpus, rows, eligible),
        "partitions": {}, "paired_comparisons": {},
        "release": {"approved": False, "blockers": []},
    }
    report["native_check_availability"] = {
        id: dict(Counter(
            f"{c.status}:{c.reason or 'native_output'}"
            for row in evidence.rows for c in row.checks if c.checker.id == id
        )) for id in ROSTER
    }
    report["collection_failures"] = dict(Counter(
        r.collection_reason for r in evidence.rows if r.collection_reason is not None
    ))
    partitions = [("holdout", lambda e: True), ("challenge", lambda e: True),
                  ("reserved_family_challenge", lambda e: e.label == 0 or e.generator_family == split["reserved_family"])]
    for part, include in partitions:
        base = "challenge" if part == "reserved_family_challenge" else part
        all_indices = [i for i, r in enumerate(rows) if r["partition"] == base and include(corpus.examples[i])]
        indices = [i for i in all_indices if labeled[i]]
        x, y, groups = arrays(corpus, values, rows, indices)
        section = {
            "total_examples": len(all_indices), "known_label_examples": sum(corpus.examples[i].label is not None for i in all_indices),
            "scored_known_label_examples": len(indices), "models": {}, "strata": {},
            "class_coverage": {
                str(label): {
                    "all_examples": sum(corpus.examples[i].label == label for i in all_indices),
                    "scored_examples": sum(corpus.examples[i].label == label for i in indices),
                    "all_groups": len({rows[i]["group"] for i in all_indices if corpus.examples[i].label == label}),
                } for label in (0, 1, None)
            },
        }
        for name, profile in profiles.items():
            p = np.asarray([profile.predict(v) for v in x])
            threshold = frozen["candidates"][name]["thresholds"]["0.005"]
            metrics = point_metrics(y, p, groups, threshold)
            metrics["threshold_frozen_on_operating_data"] = threshold
            metrics["rate_uncertainty"] = bootstrap_rates(y, p, groups, threshold)
            metrics["before_sigmoid_calibration"] = point_metrics(
                y, [sigmoid(profile.logit(v)) for v in x], groups, threshold=None,
            )
            metrics["secondary_1_percent_operating_point"] = point_metrics(
                y, p, groups, frozen["candidates"][name]["thresholds"]["0.01"],
            )
            section["models"][name] = metrics
        # Raw classifier outputs are diagnostic score references, not approved
        # probabilities; no raw discrepancy is forced into a probability domain.
        for j, id in enumerate(ROSTER[:3]):
            section["models"][f"raw_{id}_score_reference"] = point_metrics(
                y, x[:, j] if len(x) else [], groups, threshold=None,
            )
        full = np.asarray([profiles["full_suite"].predict(v) for v in x])
        baseline = np.asarray([profiles[frozen["selected_individual_baseline"]].predict(v) for v in x])
        report["paired_comparisons"][part] = paired_cluster_interval(y, full, baseline, groups)
        axes = {
            "characters": lambda e: char_bucket(e.text), "cohort": lambda e: e.cohort,
            "language": lambda e: e.language, "generator": lambda e: e.generator_family or "human",
        }
        threshold = frozen["candidates"]["full_suite"]["thresholds"]["0.005"]
        flags = {i: bool(p > threshold) for i, p in zip(indices, full)}
        effective = {}
        for label, name in ((0, "false_flags_per_all_known_negatives"), (1, "effective_recall_per_all_known_positives")):
            all_class = [i for i in all_indices if corpus.examples[i].label == label]
            if all_class:
                group_ids = [rows[i]["group"] for i in all_class]
                effective[name] = float(np.average([flags.get(i, False) for i in all_class], weights=weights(group_ids)))
            else:
                effective[name] = None
        effective["interpretation"] = "Unsupported examples remain in denominators; no probability/human label is imputed to them. Uniform connected-group class-conditional weighting."
        section["full_suite_effective_rates_including_abstentions"] = effective
        prior = profiles["full_suite"].calibration_positive_fraction
        section["hypothetical_prior_sensitivity"] = {
            "calibration_positive_fraction": prior,
            "assumption": "Unverified label-shift-only transport; hypothetical scenarios, not estimates of X prevalence or authorization to apply a prior.",
            "same_holdout_mean_predictions": {
                str(hypothesis): (float(np.average([
                    sigmoid(
                        profiles["full_suite"].calibration_slope * profiles["full_suite"].logit(v) +
                        profiles["full_suite"].calibration_intercept +
                        np.log(hypothesis / (1 - hypothesis)) - np.log(prior / (1 - prior))
                    ) for v in x
                ], weights=weights(groups))) if len(x) else None)
                for hypothesis in PLAN["hypothetical_prior_sensitivity"]
            },
        }
        for axis, key in axes.items():
            section["strata"][axis] = {}
            for value in sorted({key(corpus.examples[i]) for i in indices}):
                sub = [n for n, i in enumerate(indices) if key(corpus.examples[i]) == value]
                section["strata"][axis][value] = point_metrics(y[sub], full[sub], groups[sub], threshold)
        report["partitions"][part] = section
    blockers = report["release"]["blockers"]
    blockers.extend([
        "deployment_population_and_prevalence_unvalidated",
        "short_social_distribution_unvalidated",
        "minimum_useful_recall_and_coverage_not_agreed",
        "human_edited_translation_mechanical_ideas_only_cohorts_unvalidated",
        "profile_release_requires_separate_review_and_api_ui_implementation",
    ])
    if any(not s.redistribution_allowed for s in corpus.sources):
        blockers.append("source_release_rights_unresolved")
    if any(e.unverified_group_axes for e in corpus.examples):
        blockers.append("prompt_topic_event_independence_unverified")
    primary = report["partitions"]["holdout"]["models"]["full_suite"]
    upper = primary.get("any_false_flag_per_negative_group_one_sided_95_upper")
    if upper is None or upper > .005:
        blockers.append("primary_false_positive_target_not_established")
    improvement = report["paired_comparisons"]["holdout"]
    if (not improvement["assessable"] or
            any(improvement[k]["two_sided_95_cluster_bootstrap"][1] >= 0 for k in ("brier", "log_loss"))):
        blockers.append("incremental_suite_probability_quality_not_established")
    if frozen["candidates"]["full_suite"]["calibration_orientation_reversed"]:
        blockers.append("calibration_reversed_development_score_orientation")
    target = out / "report.json"
    if target.exists():
        if read_json(target) != report:
            raise ValueError("non_reproducible_evaluation_report")
    else:
        write_json(target, report)
    print({"report": str(target), "release_approved": False, "blockers": blockers})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fit_parser = commands.add_parser("fit")
    fit_parser.add_argument("--study", required=True)
    fit_parser.add_argument("--output", required=True)
    eval_parser = commands.add_parser("evaluate")
    eval_parser.add_argument("--study", required=True)
    eval_parser.add_argument("--run", required=True)
    args = parser.parse_args()
    if args.command == "fit":
        fit(args.study, args.output)
    else:
        evaluate(args.study, args.run)


if __name__ == "__main__":
    main()
