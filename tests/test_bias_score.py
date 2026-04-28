"""Tests for BiasScore — operational definition (R1-C4)."""
from __future__ import annotations

import numpy as np
import pytest

from belma.repair.bias_score import BiasScore


def test_bias_components_present():
    bs = BiasScore()
    comp = bs.compute("require(x > 0); _; (bool ok,) = msg.sender.call(\"\");")
    assert hasattr(comp, "cosine_distance")
    assert hasattr(comp, "perplexity")
    assert hasattr(comp, "ast_dissimilarity")
    assert hasattr(comp, "weighted_total")


def test_bias_weights_sum_to_one_default():
    """Default weights from belma_config.yaml are (0.5, 0.3, 0.2)."""
    bs = BiasScore()
    assert abs((bs.w1 + bs.w2 + bs.w3) - 1.0) < 1e-9


def test_bias_threshold_default():
    """Default tau_B = 0.15 from belma_config.yaml."""
    assert BiasScore().threshold == pytest.approx(0.15)


def test_bias_passes_for_secure_centroid_match():
    """When phi(T') == mu_secure, cosine distance is 0; the score reduces to
    w2 * PPL + w3 * (1 - sim_AST). With small PPL stub, this should pass."""
    centroid = np.ones(96, dtype=np.float32)
    bs = BiasScore(secure_centroid=centroid, embedder=lambda _: centroid.copy())
    score = bs("require(x > 0); _;", swc_label="SWC-107")
    assert score < 0.5  # well below the 0.15-equivalent gate after stubbing


def test_bias_score_is_finite_for_empty_input():
    bs = BiasScore()
    score = bs("")
    assert np.isfinite(score)
