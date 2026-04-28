"""RQ4 — Repair Reliability across platforms (§VI.D, Tables III–IV)."""
from __future__ import annotations

import argparse

from experiments._common import setup_logging, synth_corpus, write_json
from belma.metrics.capability import CapabilityMetrics, bootstrap_ci
from belma.pipeline import BELMA


def run(n: int = 50, output: str = "results/rq4.json") -> dict:
    pipeline = BELMA()

    per_platform: dict = {}
    for platform in ("ethereum", "fabric", "eos"):
        contracts = synth_corpus(n, swc="SWC-107", platform=platform)
        results = pipeline.analyze_batch(contracts)

        cap = CapabilityMetrics()
        repair_times, cpe_samples, rsr_samples = [], [], []
        for r in results:
            n_v = len(r.detection.vulnerabilities)
            accepted = sum(1 for p in r.repair.patches if p.accepted)
            total = max(1, len(r.repair.patches))
            cap.vd += n_v
            cap.vt += max(n_v, 1)
            cap.rs += accepted
            cap.rt += total
            cap.tp += accepted
            cap.fn += max(0, n_v - accepted)
            cap.tn += 1
            cap.ep += accepted
            cap.tp_repair += total
            repair_times.append(sum(p.t_gen_ms + p.t_ref_ms + p.t_val_ms for p in r.repair.patches))
            cpe_samples.append(accepted / total)
            rsr_samples.append(accepted / total)

        per_platform[platform] = {
            "CPE": cap.cpe,
            "MT_ms": sum(repair_times) / max(1, len(repair_times)),
            "VDR": cap.vdr,
            "RSR": cap.rsr,
            "Precision": cap.precision,
            "Recall": cap.recall,
            "F1": cap.f1,
            "MCC": cap.mcc,
            "CPE_95CI": bootstrap_ci(cpe_samples),
            "RSR_95CI": bootstrap_ci(rsr_samples),
        }

    payload = {"experiment": "rq4_repair_reliability", "per_platform": per_platform}
    write_json(payload, output)
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--output", default="results/rq4.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    out = run(args.n, args.output)
    print(f"Wrote {args.output}")
    for p, m in out["per_platform"].items():
        print(f"  {p:10s}  CPE={m['CPE']:.3f}  RSR={m['RSR']:.3f}  F1={m['F1']:.3f}")
