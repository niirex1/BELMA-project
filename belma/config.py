"""Configuration loader.

All BELMA constants are centralized in `configs/belma_config.yaml`. This module
loads them once and exposes a frozen `Config` view. Per Reviewer 1, Comment 4
(operational reproducibility) every threshold and weight in the manuscript must
be retrievable from the YAML — never hard-coded in Python.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "configs" / "belma_config.yaml"
)


@dataclass(frozen=True)
class Config:
    raw: Dict[str, Any] = field(default_factory=dict)

    # ---- common accessors ----
    def bias_weights(self) -> tuple[float, float, float]:
        w = self.raw["bias_score"]["weights"]
        return float(w["w1"]), float(w["w2"]), float(w["w3"])

    def bias_threshold(self) -> float:
        return float(self.raw["bias_score"]["threshold"])

    def error_weights(self) -> tuple[float, float, float]:
        a = self.raw["error_score"]["weights"]
        return float(a["alpha1"]), float(a["alpha2"]), float(a["alpha3"])

    def error_threshold(self) -> float:
        return float(self.raw["error_score"]["threshold"])

    def k_max(self) -> int:
        return int(self.raw["refinement_loop"]["k_max"])

    def symbolic_k(self) -> int:
        return int(self.raw["symbolic_execution"]["k_default"])

    def smt_timeout(self) -> int:
        return int(self.raw["symbolic_execution"]["smt_timeout_seconds"])

    def cost_benefit_weights(self) -> tuple[float, float, float]:
        cb = self.raw["cost_benefit"]
        return float(cb["alpha"]), float(cb["beta"]), float(cb["gamma"])

    def beyond_swc_enabled(self) -> bool:
        return bool(self.raw["beyond_swc"]["enabled"])


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Load YAML config from disk; returns a frozen `Config` view."""
    target = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not target.exists():
        raise FileNotFoundError(f"BELMA config not found at {target!s}")
    with target.open("r") as fh:
        raw = yaml.safe_load(fh)
    log.debug("Loaded BELMA config from %s", target)
    return Config(raw=raw)


def override(cfg: Config, **patch) -> Config:
    """Return a new Config with the given top-level keys deep-merged.

    Used by sensitivity-analysis experiments (R1-C4 Table N, R2-W1 Table P)
    to perturb individual parameters without mutating the on-disk YAML.
    """
    import copy

    new_raw = copy.deepcopy(cfg.raw)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(new_raw.get(key), dict):
            new_raw[key].update(value)
        else:
            new_raw[key] = value
    return Config(raw=new_raw)
