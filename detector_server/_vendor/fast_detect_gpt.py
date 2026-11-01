# Copyright (c) Guangsheng Bao. MIT; see fast_detect_gpt.LICENSE.
# Source: baoguangsheng/fast-detect-gpt, revision
# 971b05202bac2bb504d60c0ac0812fea7a8f7c82, scripts/fast_detect_gpt.py.
# Only the analytic function is retained. Added a non-finite/near-zero
# variance guard; otherwise the upstream calculation is unchanged.
import torch


def get_sampling_discrepancy_analytic(logits_ref, logits_score, labels):
    assert logits_ref.shape[0] == 1
    assert logits_score.shape[0] == 1
    assert labels.shape[0] == 1
    if logits_ref.size(-1) != logits_score.size(-1):
        vocab_size = min(logits_ref.size(-1), logits_score.size(-1))
        logits_ref = logits_ref[:, :, :vocab_size]
        logits_score = logits_score[:, :, :vocab_size]

    labels = labels.unsqueeze(-1) if labels.ndim == logits_score.ndim - 1 else labels
    lprobs_score = torch.log_softmax(logits_score, dim=-1)
    probs_ref = torch.softmax(logits_ref, dim=-1)
    log_likelihood = lprobs_score.gather(dim=-1, index=labels).squeeze(-1)
    mean_ref = (probs_ref * lprobs_score).sum(dim=-1)
    var_ref = (probs_ref * torch.square(lprobs_score)).sum(dim=-1) - torch.square(mean_ref)
    variance = var_ref.sum(dim=-1)
    if not torch.isfinite(variance).all() or (variance <= torch.finfo(variance.dtype).eps).any():
        return float("nan")
    discrepancy = (log_likelihood.sum(dim=-1) - mean_ref.sum(dim=-1)) / variance.sqrt()
    discrepancy = discrepancy.mean()
    return discrepancy.item()
