# BELMA: Dual-Layer Framework for Smart Contract Vulnerability Detection and Repair

## Introduction

Smart contract security is a critical challenge in blockchain ecosystems. Existing approaches rely either on **formal verification** or **machine learning**, often with trade-offs in accuracy, scalability, or repair reliability.

**BELMA** introduces a **dual-layer architecture** that integrates symbolic/formal verification with **large language model (LLM)-driven repair** to provide reproducible, efficient, and scalable vulnerability detection and automated patching.

---

## About BELMA

### Formal Verification Layer

* Performs **symbolic execution** and **model checking**.
* Ensures detection coverage for reentrancy, integer overflow/underflow, unchecked call return, and access control flaws.

### LLM-Based Repair Layer

* Uses **GPT-3.5-turbo** (fine-tuned on curated vulnerability–fix pairs) for patch generation.
* Employs iterative validation:

  * Candidate patch generation
  * Re-verification with symbolic checks
  * Rollback if violations remain
* Training settings: max 10 epochs, learning rate `2e-5`, batch size 16, Adam optimizer with gradient clipping (1.0). Early stopping at \~5 epochs to prevent overfitting.
* Datasets include both **synthetic contracts** and **real-world vulnerabilities**, balanced to mitigate bias.

---

## Evaluation & Reproducibility

BELMA has been tested on **Ethereum, Hyperledger Fabric, and EOS**. Evaluation included:

* Cross-platform experiments (RQ1–RQ4 in the paper)
* Ablation studies isolating symbolic execution, static analysis, and LLM-only repair
* Statistical significance checks (paired t-test, Wilcoxon)

To support reproducibility:

* **Dockerfile** and `requirements.txt` are provided.
* Random seeds are fixed for training and inference (`torch.manual_seed(42)` etc.).
* Example notebooks reproduce vulnerability detection and repair on demo contracts.

---

## 🔍 Reproducibility Checklist

This section follows best practices (inspired by NeurIPS and ACM reproducibility guidelines) to help reviewers and researchers independently replicate BELMA’s results.

### 1. Dataset

* [x] Training datasets are described in the paper (synthetic + real-world contracts).
* [x] Scripts to preprocess contracts into BELMA’s pipeline format are included (`/datasets`).
* [x] Dataset splits (train/val/test) are fixed and reproducible.
* [x] Curated vulnerability-fix pairs are documented with contract types.

### 2. Code

* [x] Core source code for detection + repair pipeline is provided.
* [x] Ablation study configurations (symbolic-only, static-only, LLM-only) are included.
* [x] Example notebook (`example_usage.ipynb`) demonstrates end-to-end pipeline on demo contracts.

### 3. Models

* [x] BELMA’s repair module is fine-tuned on **GPT-3.5-turbo** with hyperparameters specified in the paper.
* [x] Pre-trained checkpoints are versioned and stored for rollback.
* [x] Scripts for inference and validation are provided.
* [ ] Future extension to GPT-4/newer LLMs can reuse the same training pipeline.

### 4. Training Details

* [x] Hyperparameters (learning rate = 2e-5, batch size = 16, max epochs = 10, Adam optimizer, gradient clipping = 1.0) are documented.
* [x] Early stopping criteria and convergence details are included.
* [x] Random seeds are fixed (`torch.manual_seed(42)` etc.) for reproducibility.
* [x] GPU/compute environment specified: **NVIDIA A100, 40GB VRAM, CUDA 11.8, Ubuntu 20.04**.

### 5. Evaluation

* [x] Metrics used: VDR, RSR, Coverage, Time, Precision, Recall, F1, MCC (defined in the paper).
* [x] Cross-platform results included for Ethereum, Hyperledger Fabric, EOS.
* [x] Ablation results isolate each module’s contribution.
* [x] Boxplots include confidence intervals + statistical significance tests (paired t-test, Wilcoxon).

### 6. Limitations & Risks

* [x] BELMA provides **bounded guarantees** via symbolic re-verification but not full correctness.
* [x] Zero-day vulnerabilities not in training data may evade detection; future directions include anomaly detection & unsupervised learning.
* [x] Risk of incorrect patch deployment in production noted; human-in-the-loop validation is recommended.
* [x] Dataset bias mitigated by balanced sampling, adversarial fine-tuning, and human curation.

---

## Getting Started

### Prerequisites

* Python >= 3.8
* CUDA-enabled GPU (tested on NVIDIA A100, 40GB VRAM)
* Linux (Ubuntu 20.04/22.04 recommended)
* OpenAI API key (for GPT-3.5-turbo inference/fine-tuning)

### Installation

```bash
git clone https://github.com/YourUsername/BELMA-project.git
cd BELMA-project
pip install -r requirements.txt
```

Optional:

```bash
pip install openai
```

### Running BELMA

See `example_usage.ipynb` for:

* loading sample contracts
* running detection + automated repair
* validating patches with symbolic checks

---

## Dataset Preparation

1. **Synthetic Vulnerabilities** (generated using templates for RA, IOU, TXO, etc.)
2. **Curated Real-World Contracts** (Ethereum + Hyperledger Fabric)
3. **Training Data for LLM Fine-Tuning**

   * Balanced sampling of \~3,500 contracts
   * Annotated with fixes for reentrancy, integer overflows, unchecked call returns
   * Human-curated validation set

Scripts are provided in `/datasets` to preprocess contracts into BELMA’s pipeline format.

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
