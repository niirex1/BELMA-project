"""RQ3 — Deployment Performance under varying traffic (§VI.C, Fig. 6).

Measures CE, TP, L under three load regimes (low / moderate / high).
"""
from __future__ import annotations

import argparse
import time

from experiments._common import setup_logging, synth_corpus, write_json
from belma.pipeline import BELMA


REGIMES = {
    "low": 16,
    "moderate": 64,
    "high": 256,
}


def run(output: str = "results/rq3.json") -> dict:
    pipeline = BELMA()

    per_regime: dict = {}
    for label, n in REGIMES.items():
        contracts = synth_corpus(n, swc="SWC-107", platform="ethereum")
        t0 = time.perf_counter()
        results = pipeline.analyze_batch(contracts)
        elapsed = time.perf_counter() - t0

        latencies = [
            sum(p.t_gen_ms + p.t_ref_ms + p.t_val_ms for p in r.repair.patches)
            for r in results if r.repair.patches
        ]
        per_regime[label] = {
            "n_contracts": n,
            "elapsed_s": elapsed,
            "TP_per_s": n / elapsed if elapsed else 0,
            "L_mean_ms": sum(latencies) / len(latencies) if latencies else 0,
            "L_p95_ms": sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0,
        }

    payload = {
        "experiment": "rq3_throughput",
        "per_regime": per_regime,
    }
    write_json(payload, output)
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/rq3.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    out = run(args.output)
    print(f"Wrote {args.output}")
    for label, m in out["per_regime"].items():
        print(f"  {label:10s}  TP={m['TP_per_s']:.1f}/s  L={m['L_mean_ms']:.1f}ms")
