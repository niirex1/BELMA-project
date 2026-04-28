# BELMA — Reviewer-Comment Response Map

This document maps every reviewer comment from the September 2025 review
round to (a) the manuscript section that addresses it and (b) the code in
this repository that supports it. Use it together with the response letter.

The 11 items follow the dependency order from the itemized revision guide
(`BELMA-revision-itemised.rtf`). Phase 1 items are foundational — start
there if you are reviewing the implementation in dependency order.

---

## Phase 1 — Foundational items

### Item 1 — R1-C4: Operational definition of BiasScore / ErrorScore

**Manuscript:** §IV.B.1, Eq. (1), Table N (sensitivity).

**Code:**
- `belma/repair/bias_score.py`  — closed-form B(T') with three named components.
- `belma/repair/error_score.py` — closed-form E(T') with three named components.
- `configs/belma_config.yaml`   — every weight, threshold, and constant.
- `experiments/bias_error_sensitivity.py` — produces Table N.
- `tests/test_bias_score.py`, `tests/test_error_score.py` — pin defaults
  exactly to the manuscript values (w1=0.5, w2=0.3, w3=0.2; α1=0.5, α2=0.4,
  α3=0.1; τ_B=0.15; τ_E=0.05).

**Verification:**
```bash
python experiments/bias_error_sensitivity.py
```
Should print a 15-row Table N with |ΔVDR| < 0.8 pp and |ΔRSR| < 1.2 pp
across all perturbations.

---

### Item 2 — R2-W2: Zero-day / non-SWC evaluation

**Manuscript:** §IV.B.1 ("Beyond-SWC Detection"), §VI.G ("Beyond-SWC Evaluation"),
§IX.B (auto-repair limitation).

**Code:**
- `belma/beyond_swc/anomaly_screen.py`     — Mahalanobis OOD screen at p=95.
- `belma/beyond_swc/hypothesis_generator.py` — 8-shot LLM advisor.
- `belma/beyond_swc/beyond_swc_pipeline.py`  — two-stage orchestrator.
- `data/beyond_swc_manifest.json`            — 50-contract corpus manifest
  (8 attack classes from post-2023 DeFi exploits).
- `experiments/beyond_swc_evaluation.py`     — produces §VI.G results.

**Hard guarantee in code:** `BeyondSwcPipeline.run()` returns
`flagged_for_human_review=True` but never invokes the auto-repair loop.
This is enforced at the pipeline level in `belma/pipeline.py` via a
branching condition — search for `Beyond-SWC advisory pipeline` in
`pipeline.py:78`.

---

### Item 3 — R2-W1: k-bound sensitivity

**Manuscript:** §VI.H ("Bounded Verification Sensitivity"), §IX.C
(bounded-soundness ≠ completeness).

**Code:**
- `belma/detection/symbolic_executor.py`  — `FailureCause` enum +
  `ExplorationStats.truncations_by_cause` per-run dictionary.
- `experiments/k_bound_sensitivity.py`     — sweeps k ∈ {4, 8, 16, 32};
  produces Table P + the marginal-gain analysis.

**Verification:**
```bash
python experiments/k_bound_sensitivity.py
```
Outputs Table P plus the FN-attribution percentages
(41 / 33 / 18 / 8 across the four root causes).

---

## Phase 2 — Data-derivative items

### Item 4 — R2-W3: Performance degradation in complex / obfuscated code

**Manuscript:** §VI.A (Table Q), §IX.B (failure-regime discussion).

**Code:**
- `belma/metrics/complexity.py`           — cyclomatic complexity computation.
- `experiments/complexity_stratification.py` — produces Table Q (3×3 grid).

The mechanism attribution is decomposed into:
- (i) symbolic re-verification path explosion → `experiments/k_bound_sensitivity.py`
- (ii) AST-similarity signal degradation → `experiments/bias_error_sensitivity.py`

---

### Item 5 — R1-C2: Capability vs. system-engineering separation

**Manuscript:** §V.E (paragraph "Capability vs. infrastructure metrics").

**Code:**
- `belma/metrics/capability.py`        — VDR, RSR, Precision, Recall, F1, MCC, CPE.
- `belma/metrics/infrastructure.py`    — TP, L, BOR, ETO.
- `belma/infrastructure/`              — DHT, cache, batch (toggleable).
- `experiments/single_node_ablation.py` — single-node ablation: VDR/RSR
  shift by < 0.4 pp; TP/L shift by ≥ 60%.

---

### Item 6 — R1-C3: Latency decomposition

**Manuscript:** §V.E paragraph (f), abstract revision.

**Code:**
- `belma/metrics/latency_decomposition.py` — aggregator over per-Patch timings.
- `belma/repair/refinement_loop.py`        — instruments t_gen, t_ref, t_val
  on every patch. See `Patch.t_gen_ms`, `Patch.t_ref_ms`, `Patch.t_val_ms`.

The "8 ms" figure in the abstract specifically refers to T_val (bounded
symbolic re-check). End-to-end T_repair is 180–280 ms (Fig. 4).

---

## Phase 3 — Discussion and reference items

### Item 7 — R2-W4: Add Li et al. 2025 reference

**Manuscript:** §II (transformer/LLM-based detection paragraph),
§VII.B (positioning vs. concurrent work).

**Bibliography snippet (IEEE format):**
```
X. Li, Z. Li, W. Li, Y. Zhang, and X. Wang, "No more hidden pitfalls?
Exposing smart contract bad practices with LLM-powered hybrid analysis,"
ACM Trans. Softw. Eng. Methodol., 2025. doi: 10.1145/3795692
```

This paper is conceptually adjacent to BELMA (LLM + program analysis) but
targets bad-practice detection rather than verified repair. We do not
include it as a quantitative baseline because of the different output
specification (qualitative bad-practice flags vs. machine-checkable
assertions).

---

### Item 8 — R2-Other-1: Additional fuzzing / verification baselines

**Manuscript:** §VII.A (extended).

**Code:**
- `experiments/echidna_comparison.py`   — runs Echidna on a 100-contract
  Ethereum subset; falls back to literature numbers if `echidna-test` is
  not on PATH.
- `data/echidna_properties/echidna.yaml` — matches §VII.A test budget.
- `data/echidna_properties/EchidnaProperties.sol` — generic SWC properties.

sFuzz and ConFuzzius numbers come from the cited publications under
matched experimental settings. The orthogonality argument is in the
script's `orthogonality_note` field.

---

### Item 9 — R2-Other-2: Deployment challenges discussion

**Manuscript:** §IX.B sub-paragraph "Deployment Considerations".

**Code:** see `docs/DEPLOYMENT.md`.

Discusses:
- Node synchronization delay (12–60 s peak)
- Consensus-mechanism heterogeneity (200–800 ms Fabric endorsement)
- Archive-node availability (200 ms – 2 s queries)
- RPC rate-limiting on public endpoints

These are deployment-environmental factors, distinguished in the
manuscript from limitations of the detection/repair pipeline itself.

---

### Item 10 — R2-Other-3: Failure mode taxonomy

**Manuscript:** §IX.B.1 ("Failure Mode Taxonomy").

**Code:**
- `belma/metrics/failures.py`              — enum `FailureCategory`,
  `FailureRecord`, `FailureLog` for persistent attribution.
- `docs/FAILURE_TAXONOMY.md`               — the taxonomy table.

The mapping `CAUSE_CATEGORY` in `failures.py` is the single source of
truth for the local-vs-fundamental classification. Update both the
table and that dict together.

---

### Item 11 — R1-C1: Worked obfuscation example

**Manuscript:** §VI.A sub-paragraph "Worked example: variable renaming on
a reentrancy pattern".

**Code:**
- `docs/WORKED_EXAMPLE.md`                — full prose trace.
- `tests/test_obfuscation.py`             — regression test pinning the
  expected behavior on both the original and the obfuscated variant.

The test exercises the three architectural reasons cited in the
manuscript: (1) bytecode-level analysis is rename-invariant; (2)
structured context canonicalizes statement sequences; (3) bounded
re-verification checks the call-after-store invariant directly.

---

## Quality gate checklist before resubmission

Manuscript:
- [ ] Every reviewer comment is addressed with a section reference in the response letter
- [ ] All new content is highlighted in the manuscript
- [ ] All new tables and figures have captions and are referenced
- [ ] Numbers in response letter match numbers in manuscript exactly
- [ ] Reference [25] (Ibba et al.) updated to published version if available
- [ ] All new references have DOIs

Repository:
- [x] `configs/belma_config.yaml` exposes all R1-C4 constants
- [x] Beyond-SWC corpus included or linked with manifest
- [x] Echidna property files included
- [x] README updated with revision-round changes summary
- [x] Tests cover R1-C1 worked example (`tests/test_obfuscation.py`)
- [x] Tests cover R1-C4 thresholds (`tests/test_bias_score.py`,
      `tests/test_error_score.py`)
