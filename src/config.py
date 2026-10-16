"""Configuração de diretórios e seleção dos modelos otimizados na API NVIDIA NIM."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache"
OUTPUT_DIR = PROJECT_ROOT / "output"

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

RECOMMENDED_MODELS: List[Dict[str, str]] = [
    {
        "id": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recomendado",
        "tier": "primary",
        "description": (
            "Melhor equilíbrio entre inteligência (120B parâmetros), velocidade (<1s) "
            "e economia de tokens (suporta thinking=False com 0 reasoning tokens)."
        ),
    },
    {
        "id": "stepfun-ai/step-5-preview",
        "name": "StepFun Step-5 Preview — Alta Velocidade",
        "tier": "fallback_1",
        "description": "Baixa latência (~1s) e excelente formatação LaTeX/JSON sem desperdício de tokens.",
    },
    {
        "id": "google/gemma-4-31b-it",
        "name": "Google Gemma 4 31B Instruct — Econômico",
        "tier": "fallback_2",
        "description": "Modelo 31B direto sem tokens de raciocínio ocultos.",
    },
    {
        "id": "z-ai/glm-5.3",
        "name": "Z-AI GLM 5.3 — Raciocínio Avançado",
        "tier": "fallback_3",
        "description": "Alta capacidade analítica para templates LaTeX customizados complexos.",
    },
]

DEFAULT_MODEL = RECOMMENDED_MODELS[0]["id"]
