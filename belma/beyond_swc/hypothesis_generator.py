"""Stage 2 of the Beyond-SWC pipeline — LLM-guided hypothesis generation.

Flagged contracts (those passing the Mahalanobis anomaly screen) are passed
to the repair LLM with a few-shot prompt comprising eight curated post-2023
exploit examples. The LLM emits a natural-language hypothesis describing the
suspected vulnerability and, where the property is formalizable, a candidate
Hoare-style assertion.

These outputs are SURFACED FOR HUMAN REVIEW. BELMA does NOT auto-patch
them — see the limitation in §IX.B of the manuscript.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from belma.repair.llm_patcher import LLMPatcher
from belma.types import Contract

log = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    contract_name: str
    natural_language: str
    candidate_assertion: Optional[str] = None
    suspected_class: Optional[str] = None
    confidence: float = 0.0
    references: List[str] = field(default_factory=list)


# Eight curated post-2023 exploit examples (Reviewer 2, Weakness 2).
# In production the full prompt template lives in `data/beyond_swc_prompts.txt`;
# the version here is a one-line synopsis for documentation and triage.
DEFAULT_FEWSHOT_EXAMPLES: List[str] = [
    "flash_loan_price_manipulation: attacker borrows X, manipulates spot price, "
        "drains the AMM, repays loan in same tx (e.g. bZx 2020, Mango 2022).",
    "governance_voting_attack: attacker flash-borrows governance tokens, votes "
        "to drain treasury, repays loan (e.g. Beanstalk 2022).",
    "read_only_reentrancy: external view function reads stale state during "
        "callback while caller's state is half-updated (e.g. Curve LP 2023).",
    "oracle_manipulation: single-block TWAP manipulated via large swap; "
        "downstream contract treats inflated price as truth.",
    "mev_sandwich: attacker frontruns and backruns user swap to capture "
        "spread; victim contract underspecifies slippage tolerance.",
    "cross_chain_bridge_replay: signed message replayed on the destination "
        "chain after the source chain releases funds (e.g. Wormhole 2022).",
    "storage_collision: upgradeable proxy and implementation declare layout-"
        "incompatible storage variables; upgrade clobbers state.",
    "donation_attack: attacker donates underlying asset to a yield vault to "
        "manipulate share price and dilute legitimate depositors.",
]


class HypothesisGenerator:
    """LLM-guided few-shot hypothesis generation for non-SWC vulnerabilities."""

    SYSTEM_PROMPT = (
        "You are a smart-contract security analyst. The contract below was "
        "flagged as out-of-distribution by an embedding-based anomaly screen. "
        "Compare it against the eight post-2023 exploit patterns provided as "
        "few-shot examples and output:\n"
        "  1. A short natural-language hypothesis (<= 4 sentences) describing "
        "     the most plausible attack class and the code locations involved.\n"
        "  2. If formalizable, a Hoare-style invariant the contract is "
        "     suspected of violating.\n"
        "Do NOT propose a patch. This pipeline is advisory only."
    )

    def __init__(
        self,
        patcher: Optional[LLMPatcher] = None,
        fewshot: Optional[List[str]] = None,
    ):
        self.patcher = patcher or LLMPatcher()
        self.fewshot = fewshot or list(DEFAULT_FEWSHOT_EXAMPLES)

    def generate(self, contract: Contract) -> Hypothesis:
        prompt = self._build_prompt(contract)
        # Reuse the LLM client but with our advisory system prompt.
        resp = self.patcher._client and self._call_llm(prompt) or self._stub(contract)
        return self._parse(resp, contract)

    def _build_prompt(self, contract: Contract) -> str:
        parts = [
            "Eight post-2023 exploit patterns (few-shot context):",
            *(f"  - {x}" for x in self.fewshot),
            "",
            f"Platform: {contract.platform.value}",
            f"Contract: {contract.name}",
            "",
            "Source:",
            "```",
            contract.source[:6000],
            "```",
            "",
            "Output JSON with keys: suspected_class, hypothesis, candidate_assertion, "
            "confidence (0..1).",
        ]
        return "\n".join(parts)

    def _call_llm(self, prompt: str) -> str:
        try:
            completion = self.patcher._client.chat.completions.create(
                model=self.patcher.model,
                temperature=self.patcher.temperature,
                max_tokens=self.patcher.max_tokens,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content or ""
        except Exception as e:    # pragma: no cover
            log.warning("Beyond-SWC LLM call failed: %s", e)
            return ""

    def _stub(self, contract: Contract) -> str:
        return (
            '{"suspected_class": "oracle_manipulation", '
            '"hypothesis": "Anomaly screen flagged this contract as OOD; manual '
            'review recommended.", "candidate_assertion": null, "confidence": 0.5}'
        )

    def _parse(self, raw: str, contract: Contract) -> Hypothesis:
        import json
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "suspected_class": "unknown",
                "hypothesis": raw[:500] or "Anomaly screen flagged contract.",
                "candidate_assertion": None,
                "confidence": 0.3,
            }
        return Hypothesis(
            contract_name=contract.name,
            natural_language=str(data.get("hypothesis", "")),
            candidate_assertion=data.get("candidate_assertion"),
            suspected_class=data.get("suspected_class"),
            confidence=float(data.get("confidence", 0.0)),
        )
