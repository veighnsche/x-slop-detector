"""Group-weighted probability/coverage metrics; uncertainty is not fake certainty."""
import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score


def weights(groups):
    groups = np.asarray(groups)
    return np.asarray([1 / np.count_nonzero(groups == g) for g in groups])


def probability_losses(y, p):
    y, p = np.asarray(y), np.asarray(p)
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    return (p - y) ** 2, -(y * np.log(clipped) + (1 - y) * np.log1p(-clipped))


def point_metrics(y, p, groups, threshold):
    y, p, groups = np.asarray(y), np.asarray(p), np.asarray(groups)
    n = len(y)
    if not n:
        return {"n": 0, "groups": 0}
    w = weights(groups)
    brier, loss = probability_losses(y, p)
    positive, negative = y == 1, y == 0
    flags = None if threshold is None else p > threshold

    def rate(mask):
        return (float(np.average(flags[mask], weights=weights(groups[mask])))
                if flags is not None and np.any(mask) else None)

    bins = []
    ece = 0.0
    for i in range(10):
        mask = (p >= i / 10) & (p <= 1 if i == 9 else p < (i + 1) / 10)
        if np.any(mask):
            predicted = float(np.average(p[mask], weights=w[mask]))
            observed = float(np.average(y[mask], weights=w[mask]))
            mass = float(w[mask].sum() / w.sum())
            ece += mass * abs(predicted - observed)
            bins.append({"lower": i / 10, "upper": (i + 1) / 10, "n": int(mask.sum()),
                         "groups": len(set(groups[mask])), "predicted": predicted, "observed": observed})
        else:
            bins.append({"lower": i / 10, "upper": (i + 1) / 10, "n": 0})
    # Any false flag within a negative group: conservative cluster event bound.
    negative_groups = set(groups[negative])
    group_errors = (sum(bool(np.any(flags[(groups == g) & negative])) for g in negative_groups)
                    if flags is not None else None)
    k, total = group_errors, len(negative_groups)
    upper = (None if not total or k is None else
             (1.0 if k == total else float(beta.ppf(.95, k + 1, total - k))))
    return {
        "n": n, "groups": len(set(groups)), "negative_n": int(negative.sum()),
        "positive_n": int(positive.sum()), "negative_groups": total,
        "false_positive_count": None if flags is None else int(np.count_nonzero(flags & negative)),
        "true_positive_count": None if flags is None else int(np.count_nonzero(flags & positive)),
        "fpr_group_weighted": rate(negative), "recall_group_weighted": rate(positive),
        "brier": float(np.average(brier, weights=w)), "log_loss": float(np.average(loss, weights=w)),
        "auroc": float(roc_auc_score(y, p, sample_weight=w)) if len(set(y)) == 2 else None,
        "ece_10_equal_width_bins": ece, "reliability": bins,
        "negative_groups_with_any_false_flag": k,
        "any_false_flag_per_negative_group_one_sided_95_upper": upper,
        "bound_assumption": "Independent connected groups sampled uniformly; bounds the mean within-group FPR, not arbitrary row/population weighting.",
    }


def paired_cluster_interval(y, left, right, groups, *, seed=20261101, resamples=1000):
    """Paired group bootstrap for proper-score differences, not iid row bootstrap."""
    y, left, right, groups = map(np.asarray, (y, left, right, groups))
    unique = sorted(set(groups))
    if len(unique) < 2:
        return {"assessable": False, "reason": "fewer_than_two_groups"}
    a = probability_losses(y, left)
    b = probability_losses(y, right)
    diffs = np.asarray([
        [np.mean(a[j][groups == g] - b[j][groups == g]) for j in (0, 1)]
        for g in unique
    ])
    rng = np.random.default_rng(seed)
    draws = diffs[rng.integers(0, len(unique), size=(resamples, len(unique)))].mean(axis=1)
    return {
        "assessable": True, "groups": len(unique), "resamples": resamples,
        "interpretation": "left minus right; negative favors left; exploratory except predeclared full suite vs development-selected individual baseline",
        **{name: {"difference": float(diffs[:, i].mean()),
                  "two_sided_95_cluster_bootstrap": [float(x) for x in np.quantile(draws[:, i], [.025, .975])]}
           for i, name in enumerate(("brier", "log_loss"))},
    }


def bootstrap_rates(y, p, groups, threshold, *, seed=20261101, resamples=1000):
    y, p, groups = map(np.asarray, (y, p, groups))
    unique = sorted(set(groups))
    if len(unique) < 2:
        return {"assessable": False}
    # Per-cluster class-conditional flag rate, then resample the clusters.
    values = {}
    rng = np.random.default_rng(seed)
    for label, name in ((0, "fpr"), (1, "recall")):
        rates = [float(np.mean(p[(groups == g) & (y == label)] > threshold))
                 for g in unique if np.any((groups == g) & (y == label))]
        if len(rates) < 2:
            values[name] = None
            continue
        rates = np.asarray(rates)
        draws = rates[rng.integers(0, len(rates), size=(resamples, len(rates)))].mean(axis=1)
        values[name] = [float(x) for x in np.quantile(draws, [.025, .975])]
    return {
        "assessable": True, "two_sided_95_cluster_bootstrap": values,
        "warning": "Zero observed errors can yield a zero-width bootstrap. Use the separate nonzero exact cluster-event upper bound, never this interval alone, to assess rare FPR.",
    }


def operating_threshold(y, p, groups, target):
    """Choose only on operating data. Strict > makes ties conservative."""
    y, p, groups = map(np.asarray, (y, p, groups))
    negatives = p[y == 0]
    if not len(negatives):
        raise ValueError("operating_partition_has_no_negative_controls")
    for threshold in sorted({0.0, *map(float, negatives), 1.0}):
        mask = y == 0
        w = weights(groups[mask])
        fpr = float(np.average(p[mask] > threshold, weights=w))
        if fpr <= target:
            return threshold
    raise AssertionError("no_conservative_threshold")


def char_bucket(text):
    n = len(text)
    return "1-80" if n <= 80 else "81-160" if n <= 160 else "161-280" if n <= 280 else ">280"


def word_bucket(text):
    n = len(text.split())
    return "1-4" if n <= 4 else "5-15" if n <= 15 else "16-30" if n <= 30 else "31-60" if n <= 60 else ">60"
