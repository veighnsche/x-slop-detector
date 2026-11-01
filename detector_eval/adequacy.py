"""Fail-closed independent-group budgets, not claims of statistical power."""
import argparse
import math
from pathlib import Path

from .data import Corpus, PARTITIONS, digest, read_json, validate_split, write_json

# Conservative collection floors, fixed before acquiring the replacement study.
# Fifty is an engineering floor, NOT a proof of useful recall or calibration.
# Six hundred negatives support a zero-error one-sided 95% illustration at .5%;
# observed errors, subgroup claims and population transport require more evidence.
POLICY = {
    "id": "independent-groups-v1",
    "required_origin": "native_short",
    "minimum_groups_per_class": {
        "development": {"0": 50, "1": 50},
        "calibration": {"0": 50, "1": 50},
        "operating": {"0": 600, "1": 50},
        "holdout": {"0": 600, "1": 50},
        "challenge": {"0": 50, "1": 50},
    },
    "minimum_cv_groups_per_class": {"train": 20, "validation": 10},
    "primary_fpr_target": 0.005,
    "one_sided_confidence": 0.95,
    "interpretation": (
        "Necessary collection floors, not sufficient release criteria. Challenge "
        "floors do not establish .5% FPR. Group IDs do not prove real independence."
    ),
}


class InadequateStudy(ValueError):
    def __init__(self, report):
        self.report = report
        failed = "; ".join(
            f"{r['partition']} label={r['label']}: {r['observed']} < {r['required']} groups"
            for r in report["failures"]
        )
        super().__init__("inadequate_independent_groups: " + failed)


def zero_error_budget(target, confidence):
    """Independent Bernoulli, one-sided zero-error bound; not a power analysis."""
    if not 0 < target < 1 or not 0 < confidence < 1:
        raise ValueError("invalid_zero_error_assumptions")
    return math.ceil(math.log1p(-confidence) / math.log1p(-target))


def audit(corpus, split, eligible, *, basis):
    """Count each connected group once per class, never count unknowns as human."""
    validate_split(corpus, split)
    if len(eligible) != len(corpus.examples) or any(type(v) is not bool for v in eligible):
        raise ValueError("invalid_eligibility_mask")
    counts, failures = {}, []
    for part in PARTITIONS:
        indices = [i for i, r in enumerate(split["rows"]) if r["partition"] == part]
        counts[part] = {
            "total_rows": len(indices),
            "eligible_unknown_rows": sum(eligible[i] and corpus.examples[i].label is None for i in indices),
            "classes": {},
        }
        for label in (0, 1):
            members = [i for i in indices if eligible[i] and corpus.examples[i].label == label]
            budget_members = [i for i in members if POLICY["required_origin"] is None or
                              corpus.examples[i].derivation == POLICY["required_origin"]]
            groups = {split["rows"][i]["group"] for i in budget_members}
            required = POLICY["minimum_groups_per_class"][part][str(label)]
            counts[part]["classes"][str(label)] = {
                "rows": len(members),
                "eligible_groups_all_origins": len({split["rows"][i]["group"] for i in members}),
                "budget_rows": len(budget_members), "groups": len(groups), "required_groups": required,
            }
            if len(groups) < required:
                failures.append({"partition": part, "label": label, "observed": len(groups), "required": required})
    return {
        "schema_version": "1", "policy": POLICY, "policy_sha256": digest(POLICY),
        "basis": basis, "passed": not failures, "counts": counts, "failures": failures,
        "zero_error_independent_negative_budget": zero_error_budget(
            POLICY["primary_fpr_target"], POLICY["one_sided_confidence"],
        ),
        "warning": "Passing counts proves neither provenance, independence, accuracy, representative coverage nor release approval.",
    }


def require(corpus, split, eligible):
    report = audit(corpus, split, eligible, basis="complete_native_evidence_and_supported_input")
    if not report["passed"]:
        raise InadequateStudy(report)
    return report


def require_cv(y, groups, train, test, budget_eligible=None):
    """The fitting partition can pass while a particular CV fold is inadequate."""
    if budget_eligible is None:
        budget_eligible = [True] * len(y)
    if len(budget_eligible) != len(y):
        raise ValueError("invalid_cv_budget_mask")
    for role, indices in (("train", train), ("validation", test)):
        minimum = POLICY["minimum_cv_groups_per_class"][role]
        for label in (0, 1):
            observed = len({str(groups[i]) for i in indices if budget_eligible[i] and y[i] == label})
            if observed < minimum:
                raise ValueError(f"inadequate_cv_groups:{role}:label={label}:{observed}<{minimum}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True)
    parser.add_argument("--output", help="New report file; never overwrite a prior audit")
    args = parser.parse_args()
    study = Path(args.study)
    corpus = Corpus.model_validate(read_json(study / "corpus.json"))
    split = read_json(study / "splits.json")
    evidence_available = (study / "evidence.json").exists()
    if evidence_available:
        from .train import load_study
        _, corpus, _, _, split, eligible, _ = load_study(study)
        basis = "complete_native_evidence_and_supported_input"
    else:
        eligible = [e.language == "en" and len(e.text) <= 10000 for e in corpus.examples]
        basis = "precollection_upper_bound_no_native_evidence"
    report = audit(corpus, split, eligible, basis=basis)
    if args.output:
        write_json(args.output, report)
    import json
    print(json.dumps(report, indent=2))
    # A corpus-only pass is permission to collect, never a post-evidence pass.
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
