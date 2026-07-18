# BELMA — Blockchain-Enhanced Language Model Approach

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![PyTorch 1.13](https://img.shields.io/badge/PyTorch-1.13-ee4c2c.svg)](https://pytorch.org/)

Reference implementation accompanying the paper:

> **BELMA: Integrating Formal Verification and Large Language Models for Enhanced
> Smart Contract Security**
> Sosu, Chen, Boahen, Cai, Wang, Babu — IEEE TDSC (Manuscript ID TDSC-2025-09-1422,
> revision under review, 2026).

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

## Trained components

BELMA trains **two separate models**; they follow separate procedures and must not
be conflated (manuscript §V.C, Table III):

| Component | Model | Where trained | Role |
|---|---|---|---|
| Patch generator | `gpt-3.5-turbo-0125` (pinned snapshot) | Hosted, OpenAI fine-tuning API | Patch generation; Beyond-SWC hypotheses |
| Embedding model | `bert-base-uncased` | Local, NVIDIA A100 40 GB | φ(·), µ_secure centroid, Mahalanobis anomaly screen |

The AdamW / A100 / checkpointing configuration in the paper refers to the local
embedding model only. No optimizer, GPU, or gradient settings are user-visible
for the hosted component; its complete controllable hyperparameter set lives in
`configs/belma_config.yaml → fine_tuning`.

**Hosted fine-tune** (`fine_tuning` in the config): pilot jobs at `n_epochs=10`
showed held-out validation loss plateauing by epoch 5, so production jobs use
`n_epochs=5`, batch size 16, learning-rate multiplier 2, job seed 42; the epoch
checkpoint with the lowest validation loss among those exposed by the API is
retained. Inference runs at temperature 0, top-p 1.

**Local embedding fine-tune** (`embedding_training` in the config): contrastive
objective separating audited secure patches from vulnerable counterparts; AdamW,
LR 2e-5, batch 32, weight decay 0.01, dropout 0.1, gradient-clip norm 1.0,
early stopping (patience 2), ≤10 epochs, per-epoch checkpointing, seed 42,
PyTorch 1.13 / CUDA 11.6, ~12 h per run.

**Perplexity reference** (`perplexity_reference` in the config): the *base*,
non-fine-tuned `gpt-3.5-turbo-0125` logprob API at temperature 0 — held out of
fine-tuning so the generator never scores its own outputs as low-perplexity.

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
| `training/`              | `train_embedding.py` (local BERT fine-tune), `launch_finetune_job.py` (hosted job) |
| `prompts/`               | `repair_prompt.txt`, `beyond_swc_8shot.txt` — released verbatim     |
| `data/`                  | `finetune_train_12000.jsonl`, `finetune_val_1200.jsonl`, manifests, property templates |
| `configs/belma_config.yaml` | All loop / threshold / k-bound / training constants (R1-C4; round-3 AE/R2) |
| `docs/`                  | Architecture, revision responses, worked example                    |

## Requirements

- Python 3.8, PyTorch 1.13, CUDA 11.6 (embedding training targets A100 40 GB;
  any ≥16 GB CUDA GPU works with a smaller batch)
- `solc`, `protoc`, `eosio-cpp` on `PATH` for the platform validators
- An OpenAI API key exported as `OPENAI_API_KEY` (patch generation, hosted
  fine-tuning, and the logprob-based perplexity reference)

## Quick start

```bash
git clone https://github.com/niirex1/BELMA-project.git
cd BELMA-project
pip install -e .
export OPENAI_API_KEY=sk-...
python -m belma.pipeline --contract examples/Reentrant.sol --platform ethereum
```

## Training from scratch

```bash
# 1. Local embedding model (BERT, contrastive; seed 42; ~12 h on one A100)
python training/train_embedding.py --config configs/belma_config.yaml

# 2. Hosted patch-generator fine-tune (reads the fine_tuning section of the config,
#    uploads the JSONL files, launches the job, polls checkpoints, records the job id)
python training/launch_finetune_job.py --config configs/belma_config.yaml
```

Both scripts read every hyperparameter and seed from
`configs/belma_config.yaml`; nothing is hard-coded.

## Reproducing the paper

```bash
bash scripts/reproduce_paper_results.sh           # RQ1–RQ4 baseline numbers
python experiments/k_bound_sensitivity.py         # §VI.H, addresses R2-W1
python experiments/bias_error_sensitivity.py      # Table I, addresses R1-C4
python experiments/complexity_stratification.py   # Table V, addresses R2-W3
python experiments/beyond_swc_evaluation.py       # §VI.G, addresses R2-W2
python experiments/single_node_ablation.py        # §V.E, addresses R1-C2
python experiments/echidna_comparison.py          # §VII.A, addresses R2-Other-1
```

## Revision-round changes

A complete walk-through is in [`docs/REVISION_RESPONSE.md`](docs/REVISION_RESPONSE.md);
the short version is below.

### Round 2 (Major Revision, Sept 2025 → June 2026)

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

### Round 3 (Minor Revision, July 2026)

| #  | Reviewer item                                        | What changed in this repo                                            |
|----|------------------------------------------------------|----------------------------------------------------------------------|
| 12 | AE-C1 / R2-C2: LLM training setup — exact model, hosted vs. local procedure, hyperparameters, prompts, seeds, artifacts | Pinned `gpt-3.5-turbo-0125`; new `fine_tuning`, `embedding_training`, and `perplexity_reference` sections in `configs/belma_config.yaml`; `training/train_embedding.py`, `training/launch_finetune_job.py`; `prompts/repair_prompt.txt`, `prompts/beyond_swc_8shot.txt`; `data/finetune_{train_12000,val_1200}.jsonl`; this README section "Trained components" |

## Citation

```bibtex
@article{sosu2026belma,
  author  = {Sosu, Rexford Nii Ayitey and Chen, Jinfu and Boahen, Edward Kwadwo and
             Cai, Saihua and Wang, Shengran and Babu, C. Narendra},
  title   = {{BELMA}: Integrating Formal Verification and Large Language Models
             for Enhanced Smart Contract Security},
  journal = {IEEE Transactions on Dependable and Secure Computing},
  year    = {2026},
  note    = {Manuscript ID TDSC-2025-09-1422, revision under review}
}
```

## License

Apache 2.0. See `LICENSE`.
