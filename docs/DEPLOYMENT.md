# Deployment Considerations

Accompanies §IX.B sub-paragraph "Deployment Considerations" and addresses
**Reviewer 2, Other Comment 2**.

Beyond the testbed evaluation, real-world deployment introduces latencies
not modeled in our experiments. These are deployment-environmental
factors, **not** limitations of the detection/repair pipeline itself; they
bound the realistic latency floor for production use and motivate
continued work on lightweight verification (§X).

## Quantitative latency budget

| Source of latency                          | Typical magnitude     | Notes                                                |
|--------------------------------------------|-----------------------|------------------------------------------------------|
| Ethereum full-node sync gap                | 12 – 60 s at peak     | Pulling the latest contract state for re-verification adds this to end-to-end production scanning. |
| Hyperledger Fabric endorsement round-trip  | 200 – 800 ms / endorse| Proportional to the endorsement-policy fan-out.      |
| EOS resource-allocation queries            | 50 – 150 ms           | CPU/NET/RAM lookups before symbolic re-execution.    |
| Archive-node query (historical state)      | 200 ms – 2 s          | Archive nodes are scarcer and slower than full nodes; bounds time-travel debugging at scale. |
| Public RPC rate-limiting                   | depends on tier       | Infura/Alchemy per-key limits constrain batch scanning; production deployment requires dedicated infra. |
| Privacy-preserving extensions (encrypted)  | +7 – 10%              | Acceptable for consortium / enterprise blockchains.  |

## Mitigation patterns

1. **Pinned-block analysis.** Run BELMA against a specific block height
   rather than head; eliminates the sync gap at the cost of staleness.
2. **State caching.** `belma/infrastructure/cache.py` already provides an
   LRU cache; in production, extend it with per-block storage snapshots.
3. **Self-hosted nodes.** Avoids RPC rate limits and gives deterministic
   archive-query latency.
4. **Distributed scheduling.** The DHT load balancer in
   `belma/infrastructure/dht_balancer.py` distributes contract analysis
   tasks across a cluster — useful when the queue depth grows under load.

## What this section is NOT

These are deployment factors, not limitations of BELMA's detection or
repair logic. The capability metrics (VDR, RSR, P, R, F1, MCC, CPE,
Coverage) are independent of the deployment infrastructure — see the
single-node ablation in `experiments/single_node_ablation.py` (R1-C2).
