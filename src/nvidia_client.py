"""Cliente da API NVIDIA NIM e adaptador para LLMResumeGenerator (retrocompatibilidade)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import DEFAULT_MODEL
from .llm_client import LLMResumeGenerator


class NvidiaResumeGenerator(LLMResumeGenerator):
    """Adaptador de retrocompatibilidade para geração de currículos usando o provedor NVIDIA NIM."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        use_cache: bool = True,
    ) -> None:
        super().__init__(
            provider="nvidia",
            api_key=api_key,
            model=model,
            use_cache=use_cache,
        )

    def _call_nvidia_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1600,
    ) -> Tuple[str, Dict[str, Any], str, bool]:
        return self._call_llm_chat(messages=messages, max_tokens=max_tokens)
