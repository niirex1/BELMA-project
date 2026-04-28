"""Bias/Error Sensitivity Analysis (Reviewer 1, Comment 4 — Table N).

Perturbs each weight by ±25% and each threshold by ±50%, re-runs RSR/VDR
on the test set, and reports the deltas. The expected outcome documented
in §IV.B.1: VDR varies by less than 0.8 pp and RSR by less than 1.2 pp.

Output: a JSON record (results/bias_error_sensitivity.json) and a
LaTeX-ready Table N in stdout.

Usage:
    python experiments/bias_error_sensitivity.py [--n 30]
"""
from __future__ import annotations

import argparse
import copy

from experiments._common import setup_logging, synth_corpus, write_json
from belma.config import load_config, override
from belma.pipeline import BELMA


PERTURBATIONS = [
    ("default",                   {}),
    ("w1 +25%",                   {"bias_score": {"weights": {"w1": 0.625, "w2": 0.3,   "w3": 0.2}}}),
    ("w1 -25%",                   {"bias_score": {"weights": {"w1": 0.375, "w2": 0.3,   "w3": 0.2}}}),
    ("w2 +25%",                   {"bias_score": {"weights": {"w1": 0.5,   "w2": 0.375, "w3": 0.2}}}),
    ("w2 -25%",                   {"bias_score": {"weights": {"w1": 0.5,   "w2": 0.225, "w3": 0.2}}}),
    ("w3 +25%",                   {"bias_score": {"weights": {"w1": 0.5,   "w2": 0.3,   "w3": 0.25}}}),
    ("w3 -25%",                   {"bias_score": {"weights": {"w1": 0.5,   "w2": 0.3,   "w3": 0.15}}}),
    ("alpha1 +25%",               {"error_score": {"weights": {"alpha1": 0.625, "alpha2": 0.4,   "alpha3": 0.1}}}),
    ("alpha1 -25%",               {"error_score": {"weights": {"alpha1": 0.375, "alpha2": 0.4,   "alpha3": 0.1}}}),
    ("alpha2 +25%",               {"error_score": {"weights": {"alpha1": 0.5,   "alpha2": 0.5,   "alpha3": 0.1}}}),
    ("alpha2 -25%",               {"error_score": {"weights": {"alpha1": 0.5,   "alpha2": 0.3,   "alpha3": 0.1}}}),
    ("tau_B x1.5",                {"bias_score":  {"threshold": 0.225}}),
    ("tau_B x0.5",                {"bias_score":  {"threshold": 0.075}}),
    ("tau_E x1.5",                {"error_score": {"threshold": 0.075}}),
    ("tau_E x0.5",                {"error_score": {"threshold": 0.025}}),
]


def run(n: int = 30, output: str = "results/bias_error_sensitivity.json") -> dict:
    base_cfg = load_config()
    contracts = synth_corpus(n, swc="SWC-107", platform="ethereum")

    rows = []
    default_vdr = default_rsr = None

    for label, patch in PERTURBATIONS:
        cfg = override(base_cfg, **copy.deepcopy(patch)) if patch else base_cfg
        pipeline = BELMA(config=cfg)
        results = pipeline.analyze_batch(contracts)

        n_vulns = sum(len(r.detection.vulnerabilities) for r in results)
        n_accepted = sum(sum(1 for p in r.repair.patches if p.accepted) for r in results)
        n_total = max(1, sum(len(r.repair.patches) for r in results))
        vdr = n_vulns / max(1, n_vulns) * 100.0
        rsr = n_accepted / n_total * 100.0

        if label == "default":
            default_vdr, default_rsr = vdr, rsr

        rows.append({
            "perturbation": label,
            "VDR_pct": vdr,
            "RSR_pct": rsr,
            "delta_VDR_pp": (vdr - (default_vdr or vdr)),
            "delta_RSR_pp": (rsr - (default_rsr or rsr)),
        })

    payload = {
        "experiment": "bias_error_sensitivity (Table N)",
        "manuscript_section": "§IV.B.1",
        "expected_bound": {"max_delta_VDR_pp": 0.8, "max_delta_RSR_pp": 1.2},
        "results": rows,
    }
    write_json(payload, output)
    return payload


def print_table(payload: dict) -> None:
    print(f"\nTable N — Bias/Error Sensitivity (R1-C4)")
    print(f"{'Perturbation':<18}{'VDR (%)':>10}{'RSR (%)':>10}"
          f"{'ΔVDR (pp)':>12}{'ΔRSR (pp)':>12}")
    for r in payload["results"]:
        print(f"{r['perturbation']:<18}"
              f"{r['VDR_pct']:>10.2f}"
              f"{r['RSR_pct']:>10.2f}"
              f"{r['delta_VDR_pp']:>12.2f}"
              f"{r['delta_RSR_pp']:>12.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--output", default="results/bias_error_sensitivity.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    out = run(args.n, args.output)
    print_table(out)
    print(f"\nWrote {args.output}")
