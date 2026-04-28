#!/usr/bin/env bash
# Reproduce the headline numbers and revision-round tables from the paper.
#
# Per the §V.D "Computational Resources" paragraph, full reproduction of
# the production numbers requires the high-performance cluster (Intel Xeon
# 64-core, 128 GB RAM, NVIDIA A100). This script drives the same code paths
# at smaller scale (50 contracts/platform) so reviewers can spot-check the
# pipeline quickly on a workstation.

set -euo pipefail

mkdir -p results

echo "=== RQ1: detection and repair quality (§VI.A) ==="
python experiments/rq1_detection_repair.py        --n 30  --output results/rq1.json

echo "=== RQ2: dual-layer overhead (§VI.B) ==="
python experiments/rq2_dual_layer.py               --n 30  --output results/rq2.json

echo "=== RQ3: throughput / latency (§VI.C) ==="
python experiments/rq3_throughput.py                       --output results/rq3.json

echo "=== RQ4: repair reliability per platform (§VI.D) ==="
python experiments/rq4_repair_reliability.py       --n 30  --output results/rq4.json

echo "=== R1-C4: BiasScore/ErrorScore sensitivity (Table N) ==="
python experiments/bias_error_sensitivity.py       --n 20  --output results/bias_error_sensitivity.json

echo "=== R2-W1: k-bound sensitivity (Table P, §VI.H) ==="
python experiments/k_bound_sensitivity.py          --n 40  --output results/k_bound_sensitivity.json

echo "=== R2-W3: complexity x obfuscation stratification (Table Q) ==="
python experiments/complexity_stratification.py   --per_cell 8  --output results/complexity_stratification.json

echo "=== R2-W2: Beyond-SWC evaluation (§VI.G, Table M) ==="
python experiments/beyond_swc_evaluation.py                --output results/beyond_swc_evaluation.json

echo "=== R1-C2: single-node ablation (§V.E validation) ==="
python experiments/single_node_ablation.py         --n 30  --output results/single_node_ablation.json

echo "=== R2-Other-1: Echidna comparison (§VII.A) ==="
python experiments/echidna_comparison.py           --n 20  --output results/echidna_comparison.json

echo
echo "All experiments complete. Results in ./results/"
