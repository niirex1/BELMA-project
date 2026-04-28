"""Distributed Hash Table load balancer (Algorithm 5).

Hash-based assignment of analysis tasks across worker nodes:

    TaskAllocation(t) = arg min_{n in N}  || h(t) - h(n) ||

This is engineering, not capability. The ablation in
`experiments/single_node_ablation.py` confirms VDR/RSR move by <0.4 pp when
the DHT layer is disabled; only TP / L change materially.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Node:
    node_id: str
    capacity: int = 100
    load: int = 0


@dataclass
class DHTLoadBalancer:
    nodes: List[Node] = field(default_factory=list)
    enabled: bool = True

    def add_node(self, node_id: str, capacity: int = 100) -> None:
        self.nodes.append(Node(node_id=node_id, capacity=capacity))

    def assign(self, task_key: str) -> Optional[str]:
        """Assign a task to the node whose hash is closest to the task hash.

        When `enabled=False`, all tasks are routed to the first node — this is
        the single-node configuration used in the R1-C2 ablation.
        """
        if not self.nodes:
            return None
        if not self.enabled or len(self.nodes) == 1:
            chosen = self.nodes[0]
        else:
            t_hash = self._hash(task_key)
            chosen = min(
                self.nodes,
                key=lambda n: abs(self._hash(n.node_id) - t_hash),
            )
        chosen.load += 1
        return chosen.node_id

    def assign_batch(self, task_keys: List[str]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = defaultdict(list)
        for tk in task_keys:
            assigned = self.assign(tk)
            if assigned:
                out[assigned].append(tk)
        return dict(out)

    @staticmethod
    def _hash(value: str) -> int:
        return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)
