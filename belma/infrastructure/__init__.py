"""Engineering layer: DHT load balancing, caching, batching.

These modules are *infrastructure* in the sense of Reviewer 1 Comment 2: they
affect deployment-efficiency metrics (TP, L, BOR, ETO) but should NOT change
capability metrics (VDR, RSR, Precision, Recall, F1, MCC, CPE, Coverage).

The single-node ablation in `experiments/single_node_ablation.py` confirms
this empirically: VDR/RSR shift by < 0.4 pp when DHT/cache/batch are all
disabled, while TP and L shift by 60% +.
"""
from belma.infrastructure.dht_balancer import DHTLoadBalancer
from belma.infrastructure.cache import AnalysisCache
from belma.infrastructure.batch_processor import BatchProcessor

__all__ = ["DHTLoadBalancer", "AnalysisCache", "BatchProcessor"]
