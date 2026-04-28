# Failure Mode Taxonomy

Accompanies §IX.B.1 of the manuscript ("Failure Mode Taxonomy") and
addresses **Reviewer 2, Other Comment 3**.

The mapping below is the single source of truth, kept in sync with
`belma/metrics/failures.py`. Update both together.

| Failure cause                              | Category    | Mitigation path                                            |
|--------------------------------------------|-------------|------------------------------------------------------------|
| Path explosion exceeding *k*-bound         | Fundamental | Larger *k*, summary abstractions, modular verification     |
| Inter-contract call-chain depth exceeded   | Fundamental | Compositional verification, summary inference              |
| Non-linear arithmetic / SMT timeout        | Fundamental | Solver portfolio, abstraction refinement                   |
| Delegate-call summary limit                | Fundamental | Deeper modeling of upgradable proxy patterns               |
| Property not in SWC vocabulary             | Fundamental | Property inference, human-in-loop review                   |
| Aggressive obfuscation defeats AST sim     | Fundamental | Semantic-only embeddings, adversarial training             |
| Memory exhaustion on > 10 k LOC contracts  | Local       | Distributed verification, larger-memory machines           |
| LLM context-window truncation              | Local       | Long-context models, hierarchical prompting                |
| Network sync gap during re-verification    | Local       | Pinned-block analysis, cached state                        |
| RPC rate-limit on public endpoints         | Local       | Self-hosted node, dedicated infrastructure                 |

## Categorization principle

- **Fundamental** failures are intrinsic to the symbolic-execution engine,
  the SMT solver, or the specification language. Mitigation requires
  methodological advances.
- **Local** failures are intrinsic to the testbed environment (RAM, model
  choice, RPC quotas). Mitigation requires engineering work.

## Empirical breakdown

Of the 152 failure cases observed across the evaluation:
- 64% fundamental (predominantly path-explosion and SMT timeouts in the
  high-complexity stratum, §VI.A Table Q)
- 36% local (predominantly LLM context-window truncation on contracts >10k LOC)

The fundamental cases motivate the future-work directions in §X. The
local cases are addressable through engineering improvements rather than
methodological advances.

## Programmatic access

```python
from belma.metrics.failures import FailureLog, FailureRecord

log = FailureLog()
log.add(FailureRecord.from_cause("Vault.sol", "smt_timeout"))
print(log.summary())  # {'by_category': {'fundamental': 1}, 'by_cause': ...}
```
