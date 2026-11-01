import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec("torch"), "optional inference dependencies not installed")
class StatisticalTests(unittest.TestCase):
    def test_guarded_criterion_matches_reference_equation(self):
        import torch
        from detector_server._vendor.fast_detect_gpt import get_sampling_discrepancy_analytic

        for dtype in (torch.float32, torch.float16):
            torch.manual_seed(42)
            logits = torch.randn(1, 20, 100, dtype=dtype)
            labels = torch.randint(0, 100, (1, 20))
            log_probs = torch.log_softmax(logits, -1)
            probs = torch.softmax(logits, -1)
            likelihood = log_probs.gather(-1, labels.unsqueeze(-1)).squeeze(-1)
            mean = (probs * log_probs).sum(-1)
            variance = (probs * log_probs.square()).sum(-1) - mean.square()
            expected = ((likelihood.sum(-1) - mean.sum(-1)) / variance.sum(-1).sqrt()).mean().item()
            self.assertEqual(get_sampling_discrepancy_analytic(logits, logits, labels), expected)

    def test_zero_variance_produces_no_finite_evidence(self):
        import math
        import torch
        from detector_server._vendor.fast_detect_gpt import get_sampling_discrepancy_analytic

        logits = torch.zeros(1, 5, 2)
        labels = torch.zeros(1, 5, dtype=torch.long)
        self.assertFalse(math.isfinite(get_sampling_discrepancy_analytic(logits, logits, labels)))
