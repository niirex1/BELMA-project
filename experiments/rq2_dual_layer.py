"""RQ2 — Dual-Layer Overhead (§VI.B).

Compares dual-layer BELMA against a single-layer (LLM-only) baseline.
Measures BOR, ETO, RSR, VDR.
"""
from __future__ import annotations

import argparse

from experiments._common import setup_logging, synth_corpus, write_json
from belma.config import load_config, override
from belma.pipeline import BELMA


def run(n: int = 50, output: str = "results/rq2.json") -> dict:
    cfg = load_config()

    # ---- single-layer: refinement loop with k_max=1, no bounded re-validation ----
    cfg_single = override(
        cfg,
        refinement_loop={"k_max": 1, "on_non_convergence": "auto_accept",
                         "log_per_iteration": True},
    )

    contracts = synth_corpus(n, swc="SWC-107", platform="ethereum")

    pipeline_single = BELMA(config=cfg_single)
    pipeline_dual = BELMA(config=cfg)

    res_single = pipeline_single.analyze_batch(contracts)
    res_dual = pipeline_dual.analyze_batch(contracts)

    def agg(results, label):
        accepted = sum(sum(1 for p in r.repair.patches if p.accepted) for r in results)
        total = max(1, sum(len(r.repair.patches) for r in results))
        runtime_ms = sum(r.detection.runtime_ms + r.repair.runtime_ms for r in results)
        return {
            "label": label,
            "RSR": accepted / total,
            "VDR": sum(len(r.detection.vulnerabilities) for r in results) / max(1, total),
            "runtime_ms_total": runtime_ms,
            "n_patches": total,
        }

    single = agg(res_single, "single-layer (LLM only)")
    dual = agg(res_dual, "dual-layer (BELMA)")

    payload = {
        "experiment": "rq2_dual_layer_overhead",
        "single_layer": single,
        "dual_layer": dual,
        "ETO_ms": dual["runtime_ms_total"] - single["runtime_ms_total"],
        "BOR": dual["runtime_ms_total"] / max(1.0, single["runtime_ms_total"]) - 1.0,
    }
    write_json(payload, output)
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--output", default="results/rq2.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    out = run(args.n, args.output)
    print(f"Wrote {args.output}")
    print(f"  Dual VDR/RSR = {out['dual_layer']['VDR']:.3f} / {out['dual_layer']['RSR']:.3f}")
    print(f"  Single VDR/RSR = {out['single_layer']['VDR']:.3f} / {out['single_layer']['RSR']:.3f}")
    print(f"  ETO = {out['ETO_ms']:.1f} ms,  BOR = {out['BOR']*100:.1f}%")
