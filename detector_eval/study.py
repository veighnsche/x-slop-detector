"""Offline contributor-study pack: estimates/slots only, no recruitment or payment."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import random

from .adequacy import POLICY
from .data import PARTITIONS, digest, validate_split, write_json

PRICING_SOURCE = "https://researcher-help.prolific.com/en/articles/445239-what-is-your-pricing"
PILOT_FAMILY_SENTINEL = "not-applicable-collection-pilot"
DEFAULT = {
    "schema_version": "1",
    "id": "short-post-study-proposal-v1",
    "status": "draft_not_authorized_for_launch",
    "currency": "USD",
    "pilot_participants": 30,
    "session_minutes": 20,
    "participant_hourly": "15.00",
    "reviewers_per_block": 2,
    "review_minutes_per_block_per_reviewer": 10,
    "reviewer_hourly": "25.00",
    "reviewer_training_total_hours": 4,
    "platform_fee_fraction": "0.42857",
    "contingency_fraction": "0.20",
    "illustrative_vat_fraction_on_fee": "0.20",
    "proposed_pilot_cap": "1000.00",
    "main_slots": {"development": 75, "calibration": 75, "operating": 750, "holdout": 750, "challenge": 75},
    "allocation_seed": 20261102,
    "controller_name": None,
    "controller_contact": None,
    "controller_jurisdiction_and_legal_basis": None,
    "recruitment_account_and_actual_quote": None,
    "public_collection_url": None,
    "consent_and_retention_approval": None,
    "spend_approval_reference": None,
    "reserved_generator_family": None,
    "pricing_source": PRICING_SOURCE,
    "pricing_checked": "2026-11-01",
}


def money(value):
    return format(value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP), ".2f")


def budget(plan, participants):
    """Conservative fees on writing + review + training, even if review is internal."""
    if type(participants) is not int or participants < 1:
        raise ValueError("invalid_participant_budget")
    for field in ("session_minutes", "reviewers_per_block", "review_minutes_per_block_per_reviewer",
                  "reviewer_training_total_hours"):
        if type(plan[field]) is not int or plan[field] < 1:
            raise ValueError("invalid_duration_or_review_budget")
    rate, review_rate = Decimal(plan["participant_hourly"]), Decimal(plan["reviewer_hourly"])
    fee, contingency, vat = (Decimal(plan[k]) for k in (
        "platform_fee_fraction", "contingency_fraction", "illustrative_vat_fraction_on_fee",
    ))
    if not all(v.is_finite() for v in (rate, review_rate, fee, contingency, vat)):
        raise ValueError("nonfinite_study_budget")
    if rate < 12 or review_rate <= 0 or not all(0 <= v < 1 for v in (fee, contingency, vat)):
        raise ValueError("invalid_study_rates")
    per_person = (rate * plan["session_minutes"] / 60).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    writing = per_person * participants
    hours = Decimal(participants * plan["reviewers_per_block"] *
                    plan["review_minutes_per_block_per_reviewer"]) / 60
    review = hours * review_rate
    training = Decimal(plan["reviewer_training_total_hours"]) * review_rate
    rewards = writing + review + training
    platform = rewards * fee
    before_vat = rewards + platform
    with_vat = before_vat + platform * vat
    return {
        "participants": participants, "participant_reward_each": money(per_person),
        "writing_rewards": money(writing), "review_hours": format(hours.normalize(), "f"),
        "review_rewards": money(review), "reviewer_training_rewards": money(training),
        "platform_fee_on_all_rewards": money(platform),
        "before_vat_and_contingency": money(before_vat),
        "with_contingency_before_vat": money(before_vat * (1 + contingency)),
        "illustrative_vat_on_platform_fee_only": money(platform * vat),
        "with_contingency_and_illustrative_vat": money(with_vat * (1 + contingency)),
        "warning": "Estimate, not a quote or permission to spend. Review duration/pay and tax are unmeasured assumptions; hosting, generation, extra screening and vendor taxes may cost more.",
    }


def allocations(plan, phase):
    if phase not in {"pilot", "main"}:
        raise ValueError("unknown_collection_phase")
    counts = {"development": plan["pilot_participants"]} if phase == "pilot" else plan["main_slots"]
    if phase == "main":
        if set(counts) != set(PARTITIONS):
            raise ValueError("missing_collection_partition")
        for part in PARTITIONS:
            floor = max(POLICY["minimum_groups_per_class"][part].values())
            if type(counts[part]) is not int or counts[part] < floor:
                raise ValueError("collection_slots_below_adequacy_floor")
    if any(type(n) is not int or n < 1 for n in counts.values()):
        raise ValueError("invalid_collection_slots")
    slots = []
    for part, count in counts.items():
        for n in range(count):
            slots.append({"id": f"{phase}-{part}-{n + 1:04}", "partition": part})
    random.Random(plan["allocation_seed"]).shuffle(slots)
    return {
        "schema_version": "1", "plan_sha256": digest(plan), "phase": phase,
        "slots": slots, "reserved_family": (
            PILOT_FAMILY_SENTINEL if phase == "pilot" else plan["reserved_generator_family"]
        ),
        "warning": "Unassigned collection slots, not participants, independent groups, labels or a completed study.",
    }


def preassigned_split(corpus, allocation, author_slots, reserved_family):
    """Bind actual pseudonyms after consent; never rearrange to improve scores."""
    from .data import connected_groups
    if allocation.get("schema_version") != "1" or allocation.get("phase") not in {"pilot", "main"}:
        raise ValueError("invalid_collection_allocation")
    if allocation.get("reserved_family") != reserved_family:
        raise ValueError("collection_reserved_family_mismatch")
    if not isinstance(reserved_family, str) or not reserved_family:
        raise ValueError("collection_reserved_family_not_selected")
    slots = {s["id"]: s["partition"] for s in allocation["slots"]}
    if len(slots) != len(allocation["slots"]) or any(p not in PARTITIONS for p in slots.values()):
        raise ValueError("invalid_duplicate_collection_slot")
    authors = {e.author_id for e in corpus.examples}
    if set(author_slots) != authors or len(set(author_slots.values())) != len(author_slots):
        raise ValueError("missing_extra_or_reused_author_slot")
    if any(slot not in slots for slot in author_slots.values()):
        raise ValueError("unknown_author_collection_slot")
    if allocation["phase"] == "pilot" and any(p != "development" for p in slots.values()):
        raise ValueError("pilot_must_not_populate_final_test")
    groups = connected_groups(corpus.examples)
    split = {
        "schema_version": "1", "corpus_sha256": digest(corpus.model_dump(mode="json")),
        "reserved_family": reserved_family, "allocation_sha256": digest(allocation),
        "author_slots_sha256": digest(author_slots),
        "rows": [
            {"id": e.id, "group": group, "partition": slots[author_slots[e.author_id]]}
            for e, group in zip(corpus.examples, groups)
        ],
    }
    validate_split(corpus, split)
    return split


def prepare(output):
    plan = DEFAULT.copy()
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    estimates = {
        "schema_version": "1", "plan_sha256": digest(plan),
        "pilot": budget(plan, plan["pilot_participants"]),
        "main": budget(plan, sum(plan["main_slots"].values())),
        "proposed_pilot_cap": plan["proposed_pilot_cap"],
        "main_is_not_authorized": True,
    }
    blockers = [key for key, value in plan.items() if value is None]
    blockers.extend([
        "participant_collection_interface_not_implemented_or_deployed",
        "completion_withdrawal_storage_and_deletion_flows_not_validated",
        "pilot_duration_and_review_costs_not_measured",
        "platform_study_not_created_published_or_funded",
    ])
    for name, value in (
        ("plan.json", plan), ("budget.json", estimates),
        ("pilot-allocation.json", allocations(plan, "pilot")),
        ("main-allocation.json", allocations(plan, "main")),
        ("launch-blockers.json", {"may_launch": False, "blockers": blockers}),
    ):
        write_json(target / name, value)
    return estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="NEW private preparation directory")
    args = parser.parse_args()
    result = prepare(args.output)
    print({"pack": args.output, "pilot_estimate_with_illustrative_vat":
           result["pilot"]["with_contingency_and_illustrative_vat"], "may_launch": False})


if __name__ == "__main__":
    main()
