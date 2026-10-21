"""Testes de integridade de layout LaTeX e isolamento de entradas (prevenção de colisões)."""

import pytest
from src.compiler import sanitize_latex_layout
from src.templates import _build_education_block
from src.token_plugins import CavemanPromptPlugin


def test_sanitize_latex_layout_fixes_colliding_education_entries():
    """Verifica se o sanitizador corrige exatamente o erro reportado (Mestrado + Bacharelado fundidos)."""
    raw_broken = r"""\section*{Formação Acadêmica}
\textbf{Mestrado em Ciência da Computação} \hfill \textbf{2026 - Atual} \\
DCC/UFMG $\cdot$ Belo Horizonte, MG
\textbf{Bacharelado em Sistemas de Informação} \hfill \textbf{2019 - 2025} \\
UFV $\cdot$ Rio Paranaíba, MG"""

    sanitized = sanitize_latex_layout(raw_broken)
    
    # Deve conter \par\vspace{3pt} ou quebra após a primeira instituição
    assert r"DCC/UFMG $\cdot$ Belo Horizonte, MG\par\vspace{3pt}" in sanitized
    
    # As entradas não devem estar no mesmo parágrafo sem quebra
    lines = sanitized.splitlines()
    bach_idx = -1
    dcc_idx = -1
    for idx, l in enumerate(lines):
        if "DCC/UFMG" in l:
            dcc_idx = idx
        if "Bacharelado" in l:
            bach_idx = idx

    assert dcc_idx != -1 and bach_idx != -1
    assert bach_idx > dcc_idx
    # Deve haver pelo menos uma linha em branco ou espaçamento entre eles
    assert any(not l.strip() for l in lines[dcc_idx+1:bach_idx])


def test_sanitize_latex_layout_fixes_trailing_double_backslash_entries():
    """Verifica se converte '\\' soltos no final de uma entrada em '\\par\\vspace{3pt}'."""
    raw_broken = r"""\section*{Formação Acadêmica}
\noindent\textbf{Mestrado em Ciência da Computação} \hfill \textbf{2026 - Atual} \\
DCC/UFMG $\cdot$ Belo Horizonte, MG \\
\noindent\textbf{Bacharelado em Sistemas de Informação} \hfill \textbf{2019 - 2025} \\
UFV $\cdot$ Rio Paranaíba, MG"""

    sanitized = sanitize_latex_layout(raw_broken)
    assert r"DCC/UFMG $\cdot$ Belo Horizonte, MG\par\vspace{3pt}" in sanitized


def test_build_education_block_has_explicit_blank_lines():
    """Garante que a renderização nativa de educação inclui linhas em branco entre entradas."""
    edus = [
        {
            "degree": "Mestrado em Ciência da Computação",
            "institution": "DCC/UFMG",
            "period": "2026 - Atual",
            "details": "Belo Horizonte, MG",
        },
        {
            "degree": "Bacharelado em Sistemas de Informação",
            "institution": "UFV",
            "period": "2019 - 2025",
            "details": "Rio Paranaíba, MG",
        },
    ]
    block = _build_education_block(edus, lang="pt-br")
    assert r"\section*{Formação Acadêmica}" in block
    assert r"\par\vspace{4pt}" in block
    assert "\n\n" in block


def test_llm_prompts_contain_entry_isolation_rules():
    """Garante que as instruções de isolamento de entradas estão presentes nos prompts do modelo."""
    latex_sys = CavemanPromptPlugin.build_system_prompt("profissional", output_mode="latex", lang="pt-br")
    assert "CRITICAL ENTRY ISOLATION RULE" in latex_sys
    assert "NEVER merge an institution/location line" in latex_sys
    assert r"\par\vspace{3pt}" in latex_sys
