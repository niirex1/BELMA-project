# BELMA — Blockchain-Enhanced Language Model Approach

Reference implementation accompanying the paper:

> **BELMA: Integrating Formal Verification and Large Language Models for Enhanced
> Smart Contract Security**
> Sosu, Chen, Boahen, Cai, Wang, Babu — IEEE TDSC, 2025.

BELMA is a dual-layer framework for smart contract vulnerability detection and
automated repair. The first layer applies bounded symbolic verification; the
second employs a fine-tuned LLM to generate candidate patches that are
re-validated against SWC-derived assertions inside a closed refinement loop.

```
                    ┌─────────────────────────────┐
                    │     Smart Contract (S)      │
                    └──────────────┬──────────────┘
                                   │
                  ┌────────────────▼─────────────────┐
                  │   Layer 1: Vulnerability         │
                  │   Detection                      │
                  │   (Word2Vec + Symbolic + Rules)  │
                  └────────────────┬─────────────────┘
                       Structured Context (AST + meta)
                                   │
                  ┌────────────────▼─────────────────┐
                  │   Layer 2: Automated Repair      │
                  │   (LLM patch + Bias/Error guide) │
                  │   ┌─── refine while B>τ_B ──┐    │
                  │   │   or E>τ_E (k_max=5)    │    │
                  │   └─────────────────────────┘    │
                  └────────────────┬─────────────────┘
                       Bounded re-verification (k=16)
                                   │
                  ┌────────────────▼─────────────────┐
                  │   Cost–Benefit (Pareto) +        │
                  │   DHT Load Balancing             │
                  └────────────────┬─────────────────┘
                                   │
                          Patched Contract (S')
```

## Repository layout

| Path                     | Contents                                                            |
|--------------------------|---------------------------------------------------------------------|
| `belma/detection/`       | Symbolic execution, static rules, Word2Vec, IR translator           |
| `belma/repair/`          | LLM patcher, BiasScore, ErrorScore, refinement loop, validator      |
| `belma/beyond_swc/`      | Anomaly screen + LLM-guided hypothesis pipeline (advisory only)     |
| `belma/optimization/`    | Pareto-based cost–benefit optimizer                                 |
| `belma/infrastructure/`  | DHT load balancer, cache, batch processor                           |
| `belma/platforms/`       | Per-platform adapters (Ethereum / Fabric / EOS)                     |
| `belma/metrics/`         | Capability vs. infrastructure metric separation                     |
| `experiments/`           | Scripts to reproduce RQ1–RQ4 + every revision-round experiment      |
| `configs/belma_config.yaml` | All loop / threshold / k-bound constants (R1-C4 reproducibility)|
| `docs/`                  | Architecture, revision response, worked example                     |

## Quick start

```bash
git clone https://github.com/niirex1/BELMA-project.git
cd BELMA-project
pip install -e .
python -m belma.pipeline --contract examples/Reentrant.sol --platform ethereum
```

## Reproducing the paper

```bash
bash scripts/reproduce_paper_results.sh           # RQ1–RQ4 baseline numbers
python experiments/k_bound_sensitivity.py         # §VI.H, addresses R2-W1
python experiments/bias_error_sensitivity.py      # Table N, addresses R1-C4
python experiments/complexity_stratification.py   # Table Q, addresses R2-W3
python experiments/beyond_swc_evaluation.py       # §VI.G, addresses R2-W2
python experiments/single_node_ablation.py        # §V.E, addresses R1-C2
python experiments/echidna_comparison.py          # §VII.A, addresses R2-Other-1
```

## Revision-round changes (manuscript revision Sept 2025 → resubmission)

A complete walk-through is in [`docs/REVISION_RESPONSE.md`](docs/REVISION_RESPONSE.md);
the short version is below.

| #  | Reviewer item                                | What changed in this repo                                            |
|----|----------------------------------------------|----------------------------------------------------------------------|
| 1  | R1-C4: BiasScore / ErrorScore                | `belma/repair/{bias_score,error_score}.py`, `configs/belma_config.yaml`, `experiments/bias_error_sensitivity.py` |
| 2  | R2-W2: Beyond-SWC / zero-day                 | `belma/beyond_swc/`, `data/beyond_swc_manifest.json`, `experiments/beyond_swc_evaluation.py` |
| 3  | R2-W1: k-bound sensitivity                   | `experiments/k_bound_sensitivity.py`, FN attribution in `belma/detection/symbolic_executor.py` |
| 4  | R2-W3: Complexity × obfuscation degradation  | `experiments/complexity_stratification.py`, `belma/metrics/complexity.py` |
| 5  | R1-C2: Capability vs. infrastructure split   | `belma/metrics/{capability,infrastructure}.py`, `experiments/single_node_ablation.py` |
| 6  | R1-C3: Latency decomposition                 | `belma/metrics/latency_decomposition.py`, instrumented in `belma/repair/refinement_loop.py` |
| 7  | R2-W4: Li et al. 2025 reference              | Added to `docs/REVISION_RESPONSE.md` and bibliography snippet         |
| 8  | R2-Other-1: Echidna / sFuzz / ConFuzzius     | `experiments/echidna_comparison.py`, property templates in `data/`    |
| 9  | R2-Other-2: Deployment considerations        | `docs/DEPLOYMENT.md`                                                  |
| 10 | R2-Other-3: Failure mode taxonomy            | `docs/FAILURE_TAXONOMY.md`, classes in `belma/metrics/failures.py`    |
| 11 | R1-C1: Worked obfuscation example            | `docs/WORKED_EXAMPLE.md`, regression test in `tests/test_obfuscation.py` |

## Citation

```bibtex
@article{sosu2025belma,
  author  = {Sosu, Rexford Nii Ayitey and Chen, Jinfu and Boahen, Edward Kwadwo and
             Cai, Saihua and Wang, Shengran and Babu, C. Narendra},
  title   = {{BELMA}: Integrating Formal Verification and Large Language Models
             for Enhanced Smart Contract Security},
  journal = {IEEE Transactions on Dependable and Secure Computing},
  year    = {2025}
}
```

## License

Apache 2.0. See `LICENSE`.
