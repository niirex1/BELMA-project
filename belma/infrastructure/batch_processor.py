"""Batch processor — Eq. (9) of the paper.

    Batch(T) = ⋃_{b in Batches} Execute(b)

Groups contracts into batches that are executed in parallel. Capability
metrics are unaffected; only TP/L change.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchProcessor:
    max_batch_size: int = 32
    max_workers: int = 8
    enabled: bool = True

    def process(
        self,
        items: Iterable[T],
        worker: Callable[[T], R],
        on_error: Optional[Callable[[T, Exception], None]] = None,
    ) -> List[R]:
        items = list(items)
        if not self.enabled or self.max_workers <= 1:
            # sequential fallback used by the single-node ablation (R1-C2)
            return [worker(it) for it in items]

        results: List[R] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(worker, it): it for it in items}
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as e:    # pragma: no cover
                    if on_error:
                        on_error(futures[fut], e)
        return results

    def chunk(self, items: List[T]) -> List[List[T]]:
        return [
            items[i:i + self.max_batch_size]
            for i in range(0, len(items), self.max_batch_size)
        ]
