# `data/` — datasets and configuration files

## Contents

| Path                            | Purpose                                                              |
|---------------------------------|----------------------------------------------------------------------|
| `beyond_swc_manifest.json`      | 50-contract corpus of post-2023 DeFi exploits used in §VI.G (R2-W2). |
| `echidna_properties/`           | Echidna config + property files used in §VII.A (R2-Other-1).         |
| `synthetic_seeds/`              | (created on first run) seeds for the synthetic injection corpus.     |

## Beyond-SWC manifest

The manifest enumerates 50 contracts spanning eight attack classes outside
the SWC catalog. **Source bodies are not bundled** — each entry includes
`postmortem_url` and (where applicable) `local_path`. Run

```bash
python scripts/fetch_beyond_swc_corpus.py
```

to download verified Etherscan source code where available; entries without
verified source remain text stand-ins so the pipeline can still be exercised.

Per the manuscript: BELMA does NOT auto-patch any contract in this corpus.
The Beyond-SWC pipeline is advisory only.

## Echidna properties

`echidna.yaml` matches the test budget (50,000 tests/contract) and
deterministic seed (20250901) used in the comparison reported in
`experiments/echidna_comparison.py`.

## Reproducibility note

All numeric thresholds and weights used by the rest of the pipeline live in
`configs/belma_config.yaml`. This file contains the dataset/manifest layer
only. Keeping the two separate addresses Reviewer 1, Comment 4 (operational
reproducibility) without conflating data identity with model parameters.
