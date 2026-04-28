"""LLM patcher — wraps GPT-3.5-turbo for context-aware patch generation.

Section V.C of the paper. The patcher is fine-tuned on ~12,000 vulnerability /
patch pairs (Table II). At inference time it consumes a `StructuredContext`
(produced by the detection layer) and emits a candidate patched source.

This module is deliberately thin: the heavy lifting is in `RefinementLoop`,
which iterates BiasScore / ErrorScore until acceptance.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from belma.config import Config, load_config
from belma.types import StructuredContext

log = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    patched_source: str
    raw_completion: str
    tokens_used: int
    latency_ms: float


class LLMPatcher:
    """Fine-tuned GPT-3.5-turbo wrapper for context-aware patch generation."""

    SYSTEM_PROMPT = (
        "You are BELMA, a smart-contract repair model fine-tuned on the SWC "
        "catalog. Given a vulnerability context, output a corrected version of "
        "the function body that preserves the original behavior while removing "
        "the vulnerability. Do not introduce gas-prohibitive constructs."
    )

    def __init__(
        self,
        model: Optional[str] = None,
        api_key_env: str = "OPENAI_API_KEY",
        config: Optional[Config] = None,
    ):
        cfg = config or load_config()
        self.model = model or cfg.raw["llm"]["model"]
        self.temperature = float(cfg.raw["llm"]["temperature"])
        self.max_tokens = int(cfg.raw["llm"]["max_tokens"])
        self._api_key = os.environ.get(api_key_env)
        self._client = None
        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                log.warning("openai SDK not installed; LLMPatcher will use stub.")

    # ---- main entry ----
    def generate(
        self,
        context: StructuredContext,
        feedback: Optional[str] = None,
    ) -> LLMResponse:
        prompt = self._build_prompt(context, feedback)
        t0 = time.perf_counter()

        if self._client is None:
            patched = self._stub_patch(context)
            tokens, raw = 0, patched
        else:
            try:
                completion = self._client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = completion.choices[0].message.content or ""
                patched = self._extract_code(raw)
                tokens = completion.usage.total_tokens if completion.usage else 0
            except Exception as e:    # pragma: no cover - production resilience
                log.warning("LLM call failed (%s); falling back to stub.", e)
                patched = self._stub_patch(context)
                tokens, raw = 0, patched

        return LLMResponse(
            patched_source=patched,
            raw_completion=raw,
            tokens_used=tokens,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # ---- prompt construction ----
    def _build_prompt(
        self, context: StructuredContext, feedback: Optional[str]
    ) -> str:
        v = context.vulnerability
        parts = [
            f"Platform: {context.contract.platform.value}",
            f"Function: {context.enclosing_function}",
            f"SWC class: {v.swc.value if v.swc else 'non-SWC (advisory)'}",
            f"Severity: {v.severity}",
            f"Description: {v.description}",
            "",
            "Vulnerable code:",
            "```",
            v.raw_context or context.contract.source[:2000],
            "```",
        ]
        if feedback:
            parts.extend([
                "",
                "The previous candidate failed validation with:",
                feedback,
                "Address the feedback above and produce a new candidate.",
            ])
        parts.extend([
            "",
            "Output the entire corrected function body, no commentary.",
        ])
        return "\n".join(parts)

    # ---- helpers ----
    def _stub_patch(self, context: StructuredContext) -> str:
        """Used when the OpenAI client is not configured (CI / unit tests).

        Returns a minimal, plausibly-correct patch that demonstrates the
        checks-effects-interactions pattern for SWC-107."""
        src = context.contract.source
        if context.vulnerability.swc and context.vulnerability.swc.value == "SWC-107":
            # Simple textual swap of call-then-store into store-then-call
            patched = src.replace(
                "msg.sender.call.value",
                "// state-update before external call (BELMA stub)\n"
                "        balances[msg.sender] -= amount;\n"
                "        msg.sender.call.value",
            )
            return patched
        return src   # other classes return source unchanged in stub mode

    def _extract_code(self, raw: str) -> str:
        if "```" in raw:
            parts = raw.split("```")
            if len(parts) >= 3:
                code = parts[1]
                if code.startswith("solidity\n") or code.startswith("javascript\n"):
                    code = code.split("\n", 1)[1] if "\n" in code else code
                return code.strip()
        return raw.strip()
