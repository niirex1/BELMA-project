"""BiasScore — operational definition (R1-C4).

Manuscript §IV.B.1, Eq. (1):

    B(T') = w1 * d_cos( phi(T'), mu_secure )
          + w2 * PPL_hat(T')
          + w3 * ( 1 - sim_AST(T', N_T(T')) )

where:
    phi(.)        : BERT embedding of the candidate patch (§V.C)
    mu_secure     : centroid of phi over the 12,000-pair fine-tuning corpus
    PPL_hat       : length-normalized perplexity under a held-out reference LM
                    (GPT-3.5-turbo logprob API, temperature 0)
    sim_AST       : normalized tree-edit similarity to the nearest-neighbor
                    SWC patch template

Default weights (from grid search on the 1,200-sample validation split):
    (w1, w2, w3) = (0.5, 0.3, 0.2)
Default acceptance threshold:
    tau_B = 0.15

The sensitivity analysis in `experiments/bias_error_sensitivity.py` perturbs
each weight by ±25% and the threshold by ±50%; VDR varies by less than 0.8 pp
and RSR by less than 1.2 pp (Table N).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from belma.config import Config, load_config

log = logging.getLogger(__name__)


@dataclass
class BiasScoreComponents:
    """Per-call breakdown — useful for sensitivity analysis and debugging."""
    cosine_distance: float       # d_cos(phi(T'), mu_secure)
    perplexity: float            # PPL_hat(T')
    ast_dissimilarity: float     # 1 - sim_AST(T', N_T(T'))
    weighted_total: float


class BiasScore:
    """Compute B(T') for a candidate patch.

    Plug-in interfaces:
        embedder(text) -> np.ndarray              # BERT embedding
        perplexity_fn(text) -> float              # length-normalized PPL
        ast_similarity_fn(text, template) -> float  # tree-edit sim in [0,1]
        nearest_template_fn(swc_label) -> str     # patch template lookup
    """

    def __init__(
        self,
        secure_centroid: Optional[np.ndarray] = None,
        embedder=None,
        perplexity_fn=None,
        ast_similarity_fn=None,
        nearest_template_fn=None,
        config: Optional[Config] = None,
    ):
        cfg = config or load_config()
        self.w1, self.w2, self.w3 = cfg.bias_weights()
        self.threshold = cfg.bias_threshold()

        self.secure_centroid = secure_centroid
        self._embed = embedder or _identity_embedder
        self._ppl = perplexity_fn or _default_perplexity
        self._ast_sim = ast_similarity_fn or _stub_ast_similarity
        self._nearest_template = nearest_template_fn or _stub_template_lookup

    # ---- main API ----
    def compute(self, patch_source: str, swc_label: Optional[str] = None) -> BiasScoreComponents:
        phi = self._embed(patch_source)
        if self.secure_centroid is None:
            self.secure_centroid = np.zeros_like(phi)

        d_cos = float(_cosine_distance(phi, self.secure_centroid))
        ppl = float(self._ppl(patch_source))
        template = self._nearest_template(swc_label)
        ast_sim = float(self._ast_sim(patch_source, template))

        total = (
            self.w1 * d_cos
            + self.w2 * ppl
            + self.w3 * (1.0 - ast_sim)
        )
        return BiasScoreComponents(
            cosine_distance=d_cos,
            perplexity=ppl,
            ast_dissimilarity=1.0 - ast_sim,
            weighted_total=total,
        )

    def __call__(self, patch_source: str, swc_label: Optional[str] = None) -> float:
        return self.compute(patch_source, swc_label).weighted_total

    def passes(self, patch_source: str, swc_label: Optional[str] = None) -> bool:
        return self(patch_source, swc_label) <= self.threshold


# ---- helpers ----
def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - float(np.dot(a, b) / (na * nb))


def _identity_embedder(text: str) -> np.ndarray:
    """Fallback embedder: hash-based pseudo-embedding for unit tests.

    Production setups inject a BERT-base-uncased embedder via the constructor.
    """
    import hashlib
    h = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
    return np.tile(arr, 32)[:768]   # 768-dim, BERT-shaped


def _default_perplexity(text: str) -> float:
    """Stub PPL — production injects an LM logprob API.

    Returns a value in [0,1] under a length-normalized formulation so the
    weighted sum stays comparable across patches of different length.
    """
    if not text:
        return 1.0
    # rough proxy: token-rarity divided by length
    tokens = text.split()
    return min(1.0, max(0.0, len(set(tokens)) / max(1, len(tokens))))


def _stub_ast_similarity(patch: str, template: str) -> float:
    """Stub: returns the fraction of common k-grams. Production uses the
    Zhang–Shasha tree-edit distance over Solidity ASTs."""
    if not patch or not template:
        return 0.0
    set_a = set(patch[i:i + 4] for i in range(len(patch) - 3))
    set_b = set(template[i:i + 4] for i in range(len(template) - 3))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _stub_template_lookup(swc_label: Optional[str]) -> str:
    """Stub: returns a canonical patch template per SWC class."""
    return {
        "SWC-107": "require(state_updated); _; (bool ok,) = msg.sender.call.value(amount)(\"\"); require(ok);",
        "SWC-101": "using SafeMath for uint256;",
        "SWC-104": "(bool success,) = target.call(data); require(success);",
    }.get(swc_label or "", "")
