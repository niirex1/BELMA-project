#!/usr/bin/env python
"""Fetch verified Etherscan source code for the Beyond-SWC corpus.

Reads `data/beyond_swc_manifest.json` and downloads each contract's source
into `data/beyond_swc_sources/<name>.sol`. Skips entries that lack a
verified contract address.

Requires ETHERSCAN_API_KEY in the environment.

This is a stub — production setups should also fetch transaction traces
of the actual exploits (from the post-mortems' linked tx hashes) so the
ground truth of "vulnerable in this transaction" is fully reproducible.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.request
import urllib.parse


MANIFEST = Path(__file__).parent.parent / "data" / "beyond_swc_manifest.json"
OUT_DIR = Path(__file__).parent.parent / "data" / "beyond_swc_sources"


def fetch(addr: str, api_key: str) -> str | None:
    url = (
        "https://api.etherscan.io/api?module=contract&action=getsourcecode"
        f"&address={urllib.parse.quote(addr)}&apikey={urllib.parse.quote(api_key)}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("status") != "1" or not data.get("result"):
        return None
    return data["result"][0].get("SourceCode")


def main() -> int:
    api_key = os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        print("ETHERSCAN_API_KEY not set; cannot fetch.", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())

    fetched, skipped = 0, 0
    for entry in manifest["contracts"]:
        addr = entry.get("address")
        name = entry["name"]
        if not addr:
            skipped += 1
            continue
        try:
            src = fetch(addr, api_key)
        except Exception as e:
            print(f"  ! {name}: {e}", file=sys.stderr)
            skipped += 1
            continue
        if not src:
            skipped += 1
            continue
        (OUT_DIR / f"{name}.sol").write_text(src, encoding="utf-8")
        fetched += 1
    print(f"Fetched {fetched}, skipped {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
