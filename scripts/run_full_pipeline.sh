#!/usr/bin/env bash
# Convenience wrapper to run BELMA on a single contract.
#
# Usage:
#   bash scripts/run_full_pipeline.sh examples/Reentrant.sol ethereum
#

set -euo pipefail

CONTRACT="${1:-examples/Reentrant.sol}"
PLATFORM="${2:-ethereum}"
OUTPUT="${3:-results/$(basename "${CONTRACT%.*}").json}"

mkdir -p "$(dirname "$OUTPUT")"

python -m belma.pipeline \
    --contract "$CONTRACT" \
    --platform "$PLATFORM" \
    --output "$OUTPUT" \
    --verbose

echo
echo "Result: $OUTPUT"
