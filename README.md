# BELMA: Dual-Layer Framework for Smart Contract Vulnerability Detection and Repair

## Introduction

Smart contract security is a critical challenge in blockchain ecosystems. Existing approaches rely either on **formal verification** or **machine learning**, often with trade-offs in accuracy, scalability, or repair reliability.

**BELMA** introduces a **dual-layer architecture** that integrates symbolic/formal verification with **large language model (LLM)-driven repair** to provide reproducible, efficient, and scalable vulnerability detection and automated patching.  

This repository includes **code, datasets, configurations, and notebooks** to reproduce the main experiments reported in the manuscript.

---

## About BELMA

### Formal Verification Layer
* Performs **symbolic execution** and **model checking**.  
* Ensures detection coverage for reentrancy, integer overflow/underflow, unchecked call returns, access control flaws, and transaction-order dependence.  

### LLM-Based Repair Layer
* Uses **GPT-3.5-turbo** (fine-tuned on curated vulnerability–fix pairs) for patch generation.  
* Employs iterative validation:  
  - Candidate patch generation  
  - Re-verification with symbolic checks  
  - Rollback if violations remain  
* Training settings: max 10 epochs, learning rate `2e-5`, batch size 16, AdamW optimizer with gradient clipping (1.0). Early stopping at ~5 epochs to prevent overfitting.  
* Datasets include both **synthetic contracts** and **real-world vulnerabilities**, balanced to mitigate bias.  

> **Note:** GPT-3.5 is used in this work. For forward-compatibility, the training pipeline supports GPT-4 or future LLMs with minimal adjustment.

---

## Evaluation & Reproducibility

BELMA has been evaluated on **Ethereum, Hyperledger Fabric, and EOS**. Evaluation included:  
* Cross-platform experiments (RQ1–RQ4 in the paper)  
* Ablation studies isolating symbolic execution, static analysis, and LLM-only repair  
* Statistical significance checks (paired t-test, Wilcoxon)  

Reproducibility support includes:  
* `requirements.txt` and `environment.yml` with pinned versions  
* Example notebook (`example_usage.ipynb`) showing detection → repair → validation on toy contracts  
* Fixed random seeds (`torch.manual_seed(42)`, NumPy, Python)  
* Config files under `/experiments/configs/` for controlled ablation runs  
* A symbolic **`validate_patch.py`** script to re-verify generated patches  

---

## Reproducibility Checklist

- [x] **Environment files**: `requirements.txt` and `environment.yml` provided  
- [x] **Deterministic seeds**: all training and inference runs use fixed random seeds  
- [x] **Toy dataset + demo run**: included in `/datasets/demo` for <1 min end-to-end test  
- [x] **Full datasets**: synthetic + curated real-world (Ethereum, Fabric, EOS) with preprocessing scripts  
- [x] **Configs**: ablation and experiment configs under `/experiments/configs/*.yaml`  
- [x] **Figures/tables**: reproduction scripts for selected tables and plots (`/experiments/reproduce_figures.ipynb`)  
- [x] **LLM usage**: `.env.example` for API keys, plus cached outputs (offline mode)  
- [x] **Repair validation**: `validate_patch.py` ensures symbolic re-verification before deployment  

---

## 🔑 Demo Quickstart (Runs in <1 Minute)

To verify reproducibility, BELMA ships with **four small sample contracts** illustrating common vulnerabilities (Reentrancy, Unchecked Call, Integer Overflow, Access Control).  
The demo runs the full pipeline — **detection → repair → symbolic re-verification** — entirely offline by default (no API key required).

```bash
# 1. Clone and install
git clone https://github.com/niirex1/BELMA-project.git
cd BELMA-project
pip install -r requirements.txt

# 2. Run the demo (offline mode, finishes in <1 min)
python run_belma_demo.py

# 3. Inspect results
# - Original & patched contracts: outputs/demo/*.sol
# - JSON reports: outputs/demo/*.report.json
# - Aggregate summary: outputs/demo/aggregate_report.json

---
export BELMA_OFFLINE_MODE=0
export OPENAI_API_KEY=sk-...   # your key here
python run_belma_demo.py

---

## Contributing

We welcome contributions from the community:

* Extend BELMA to other platforms (e.g., Solana, Avalanche)
* Improve dataset diversity (zero-day coverage, adversarial contracts)
* Enhance repair validation pipelines

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

BELMA is released under the **MIT License**.
See [LICENSE](LICENSE.md) for full terms.

---

## Contact & Support

* **Rexford Sosu**

  * 📧 [rexfordsosu@outlook.com](mailto:rexfordsosu@outlook.com)
  * GitHub: [@niirex1](https://github.com/niirex1)
  * LinkedIn: [Rexford Sosu](https://www.linkedin.com/in/rexford-sosu-b4593b57/)
