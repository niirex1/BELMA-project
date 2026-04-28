# BELMA Architecture

This document walks through the dual-layer pipeline of the paper and points
at the modules that implement each piece.

## Top-level flow (Algorithm 3, Section IV.C)

```
                  ┌────────────────────────────────────┐
                  │         Smart Contract S           │
                  └──────────────────┬─────────────────┘
                                     │
                  ┌──────────────────▼─────────────────┐
                  │  Layer 1 — Detection                │
                  │  belma/detection/                   │
                  │                                     │
                  │   1. Word2Vec preprocessing         │
                  │      → word2vec_preprocessor.py     │
                  │   2. Bounded symbolic execution     │
                  │      → symbolic_executor.py (Alg 1) │
                  │   3. Rule-based detectors           │
                  │      → static_analyzer.py           │
                  │   4. Vulnerability classifier       │
                  │      → vulnerability_classifier.py  │
                  └──────────────────┬─────────────────┘
                                     │
                       Vulnerability  Context  VC
                       (StructuredContext per vuln)
                                     │
                  ┌──────────────────▼─────────────────┐
                  │  Layer 2 — Repair                   │
                  │  belma/repair/                      │
                  │                                     │
                  │   1. LLM patch generation           │
                  │      → llm_patcher.py               │
                  │   2. Refinement loop (Alg 2)        │
                  │      while B>τ_B or E>τ_E:          │
                  │          refine via LLM             │
                  │      → refinement_loop.py           │
                  │   3. Bounded symbolic re-validation │
                  │      → patch_validator.py           │
                  └──────────────────┬─────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
       ┌──────▼──────┐      ┌────────▼────────┐    ┌────────▼────────┐
       │ Beyond-SWC  │      │ Cost-Benefit    │    │ Infrastructure  │
       │ pipeline    │      │ (Pareto, Alg 4) │    │ (DHT/cache/batch)│
       │ (advisory)  │      │ optimization    │    │                 │
       └─────────────┘      └─────────────────┘    └─────────────────┘
       belma/beyond_swc/     belma/optimization/    belma/infrastructure/
```

## Capability vs. Infrastructure separation (R1-C2)

Per Reviewer 1, Comment 2 we explicitly separate the two metric families:

```
belma/metrics/capability.py      # VDR, RSR, P, R, F1, MCC, CPE, Cov
belma/metrics/infrastructure.py  # TP, L, BOR, ETO
```

The `experiments/single_node_ablation.py` script empirically validates the
separation: disabling DHT/cache/batch shifts capability metrics by < 0.4 pp
while infrastructure metrics shift by 60 % +.

## BiasScore / ErrorScore (R1-C4)

Closed-form definitions live in:

```
belma/repair/bias_score.py   # B(T') = w1 d_cos + w2 PPL + w3 (1 - sim_AST)
belma/repair/error_score.py  # E(T') = a1 e_compile + a2 e_assert + a3 e_regress
```

All weights and thresholds are loaded from `configs/belma_config.yaml`.
The sensitivity analysis lives in `experiments/bias_error_sensitivity.py`
(produces Table N).

## Latency decomposition (R1-C3)

`belma/repair/refinement_loop.py` records `t_gen_ms`, `t_ref_ms`, `t_val_ms`
on every Patch. Aggregation into the per-stage mean / 95 % CI table is
done by `belma/metrics/latency_decomposition.py`.

## Beyond-SWC pipeline (R2-W2)

Two-stage advisory pipeline in `belma/beyond_swc/`:

```
anomaly_screen.py           # Stage 1: Mahalanobis OOD detection
hypothesis_generator.py     # Stage 2: 8-shot LLM hypothesis generation
beyond_swc_pipeline.py      # Orchestrator
```

This pipeline NEVER auto-patches. All flagged contracts surface for human
review.

## k-bound sensitivity (R2-W1)

`belma/detection/symbolic_executor.py` records `truncations_by_cause` per
run, so the FN-attribution numbers in §VI.H reproduce from the same logs.
The sweep is in `experiments/k_bound_sensitivity.py`.

## Per-platform adapters (Section IV.F)

```
belma/platforms/ethereum.py  # gas + storage constraints
belma/platforms/fabric.py    # endorsement-policy preservation
belma/platforms/eos.py       # CPU/NET/RAM resource budgets
```

All three normalize into the IR defined in
`belma/detection/ir_translator.py`, so the rest of the pipeline operates
uniformly across heterogeneous platforms.
