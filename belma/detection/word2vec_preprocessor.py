"""Word2Vec preprocessor for semantic alignment.

Per Section IV (Methodology) and Fig. 1 of the paper, the detection layer
applies Word2Vec preprocessing to map source/bytecode tokens into a dense
embedding space before classification. The ablation in Section VIII (w/o
Word2Vec, Table VII) confirms the module contributes ~3 pp Precision and
~4.5 pp Recall.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

import numpy as np

log = logging.getLogger(__name__)

# Solidity / Vyper / chaincode reserved tokens (small subset; production uses
# a tokenizer derived from the language grammar).
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0x[0-9a-fA-F]+|[+\-*/%=<>!&|^~()\[\]{};,.]")


def tokenize(source: str) -> List[str]:
    """Lightweight lexical tokenizer for smart-contract source code."""
    return _TOKEN_RE.findall(source)


class Word2VecPreprocessor:
    """Wraps a (pre-trained or freshly trained) Word2Vec model.

    In production this is loaded from disk; for the ablation we expose a tiny
    online trainer so the module is self-contained for unit tests.
    """

    def __init__(self, vector_size: int = 128, window: int = 5, min_count: int = 1):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self._model = None  # lazy: gensim.models.Word2Vec when fit() is called

    def fit(self, corpus: Iterable[str]) -> "Word2VecPreprocessor":
        from gensim.models import Word2Vec

        sentences = [tokenize(text) for text in corpus]
        self._model = Word2Vec(
            sentences=sentences,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            workers=4,
            seed=20250901,
        )
        log.info("Trained Word2Vec on %d sentences", len(sentences))
        return self

    def embed(self, source: str) -> np.ndarray:
        """Return a single mean-pooled vector for the input source."""
        toks = tokenize(source)
        if self._model is None or not toks:
            return np.zeros(self.vector_size, dtype=np.float32)
        vecs = [self._model.wv[t] for t in toks if t in self._model.wv]
        if not vecs:
            return np.zeros(self.vector_size, dtype=np.float32)
        return np.mean(np.stack(vecs), axis=0).astype(np.float32)

    def embed_batch(self, sources: Iterable[str]) -> np.ndarray:
        return np.stack([self.embed(s) for s in sources])

    def save(self, path: str) -> None:
        if self._model is None:
            raise RuntimeError("Cannot save: model not fitted.")
        self._model.save(path)

    @classmethod
    def load(cls, path: str) -> "Word2VecPreprocessor":
        from gensim.models import Word2Vec

        m = cls()
        m._model = Word2Vec.load(path)
        m.vector_size = m._model.vector_size
        return m
