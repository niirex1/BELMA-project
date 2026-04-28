"""BELMA — dual-layer smart-contract vulnerability detection and repair.

The framework is structured as two cooperating layers:

    Layer 1 (`belma.detection`)  : Word2Vec preprocessing -> symbolic execution
                                   + rule-based detectors -> structured context.
    Layer 2 (`belma.repair`)     : LLM-driven patch generation guided by a
                                   BiasScore / ErrorScore loop, followed by
                                   bounded symbolic re-verification.

Supporting modules:
    `belma.beyond_swc`     : advisory pipeline for non-SWC vulnerabilities (R2-W2).
    `belma.optimization`   : Pareto-based cost-benefit optimizer.
    `belma.infrastructure` : DHT load balancer, cache, batch processor.
    `belma.platforms`      : per-platform IR adapters (Ethereum / Fabric / EOS).
    `belma.metrics`        : capability vs. infrastructure metric separation.

See `docs/ARCHITECTURE.md` for the full design walkthrough.
"""
from belma._version import __version__

__all__ = ["__version__"]
