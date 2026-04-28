"""Stage 1 of the Beyond-SWC pipeline — Mahalanobis anomaly screen.

Manuscript §IV.B.1, "Beyond-SWC Detection":

    flag if  d_M( phi(C), mu_secure )  >  delta

where phi(.) is the BERT embedding of the contract, mu_secure is the centroid
over the 12,000-pair fine-tuning corpus, and delta is the 95th percentile of
in-distribution Mahalanobis distances on the validation split (target FPR
~5% on benign contracts).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class AnomalyVerdict:
    is_anomalous: bool
    distance: float
    threshold: float
    confidence: float


class MahalanobisAnomalyScreen:
    """Stage 1: out-of-distribution screen on contract embeddings."""

    def __init__(
        self,
        secure_embeddings: Optional[np.ndarray] = None,
        embedder: Optional[Callable[[str], np.ndarray]] = None,
        percentile: float = 95.0,
    ):
        self.percentile = percentile
        self._embed = embedder or _hash_embedder
        self.mu: Optional[np.ndarray] = None
        self.cov_inv: Optional[np.ndarray] = None
        self.threshold: float = float("inf")
        if secure_embeddings is not None:
            self.fit(secure_embeddings)

    # ---- fit on the 12,000-pair corpus ----
    def fit(self, secure_embeddings: np.ndarray) -> "MahalanobisAnomalyScreen":
        if secure_embeddings.ndim != 2:
            raise ValueError("secure_embeddings must be a 2-D array")
        self.mu = secure_embeddings.mean(axis=0)
        cov = np.cov(secure_embeddings, rowvar=False)
        # numerical regularization so the inverse is well-conditioned
        cov += 1e-3 * np.eye(cov.shape[0])
        self.cov_inv = np.linalg.pinv(cov)

        # calibrate threshold to in-distribution percentile
        in_dist = np.array([
            self._mahalanobis(e) for e in secure_embeddings
        ])
        self.threshold = float(np.percentile(in_dist, self.percentile))
        log.info("AnomalyScreen calibrated: threshold=%.3f at p=%.0f",
                 self.threshold, self.percentile)
        return self

    # ---- inference ----
    def screen(self, source: str) -> AnomalyVerdict:
        if self.mu is None or self.cov_inv is None:
            raise RuntimeError("AnomalyScreen has not been fit; call .fit() first.")
        phi = self._embed(source)
        d = self._mahalanobis(phi)
        return AnomalyVerdict(
            is_anomalous=d > self.threshold,
            distance=float(d),
            threshold=self.threshold,
            confidence=float(min(1.0, d / max(self.threshold, 1e-9))),
        )

    def _mahalanobis(self, x: np.ndarray) -> float:
        diff = x - self.mu
        return float(np.sqrt(diff @ self.cov_inv @ diff))


# fallback embedder for unit tests / CI
def _hash_embedder(text: str) -> np.ndarray:
    import hashlib
    h = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
    return np.tile(arr, 3)[:96]   # 96-dim for testability
