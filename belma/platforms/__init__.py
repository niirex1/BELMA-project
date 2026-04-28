"""Per-platform adapters (Section IV.F of the paper).

Each adapter:
  (a) parses platform-specific source/bytecode into the common IR;
  (b) attaches platform-specific constraints (gas / endorsement / CPU-NET-RAM);
  (c) re-validates a candidate patch under those constraints.

The unified IR is what enables BELMA to address Reviewer 2 Other-3's failure
taxonomy: "fundamental" (engine-level) failures are platform-independent, and
"local" (testbed) failures are easy to attribute via the per-platform adapter.
"""
from belma.platforms.ethereum import EthereumAdapter
from belma.platforms.fabric import FabricAdapter
from belma.platforms.eos import EOSAdapter

__all__ = ["EthereumAdapter", "FabricAdapter", "EOSAdapter"]


def adapter_for(platform_str: str):
    """Return the adapter instance for a platform string."""
    p = platform_str.lower()
    if p == "ethereum":
        return EthereumAdapter()
    if p in ("fabric", "hyperledger", "hyperledger_fabric"):
        return FabricAdapter()
    if p == "eos":
        return EOSAdapter()
    raise ValueError(f"Unsupported platform: {platform_str}")
