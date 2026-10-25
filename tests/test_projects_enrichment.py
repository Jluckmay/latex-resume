"""Testes para enriquecimento de projetos via README, links clicáveis sem opção à direita e lista única de ferramentas."""

from __future__ import annotations

import pytest

from src.extractors import extract_project_info_from_readme, clean_markdown_text
from src.templates import render_builtin_template


def test_clean_markdown_text():
    raw = (
        "# Title\n\n"
        "[![Badge](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)\n"
        "This is **bold** and *italic* with `inline code` and [a link](https://example.com).\n"
        "<p>HTML paragraph</p>"
    )
    cleaned = clean_markdown_text(raw)
    assert "[![Badge]" not in cleaned
    assert "**" not in cleaned
    assert "`" not in cleaned
    assert "<p>" not in cleaned
    assert "This is bold and italic with inline code and a link. HTML paragraph" in cleaned


def test_extract_project_info_from_readme_multilingual():
    readme = """# Gerador Automático de Currículos LaTeX
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)

## 🇧🇷 Português
Gerador automático de currículos Acadêmicos e Profissionais em LaTeX + PDF nos idiomas pt-BR e en-US, alimentado por múltiplos provedores de IA.
Possui arquitetura modular com plugins de economia de tokens e cofre de memória volátil.

### 📋 Requisitos
Requer Python 3.11, Docker, Flask e TeX Live.

## 🇺🇸 English
Automatic Academic and Professional resume generator in LaTeX + PDF powered by multiple AI providers.
Features modular architecture with token economy plugins.

### Requirements
Requires Python 3.11, Docker, Flask and TeX Live.
"""
    # Test pt-br extraction
    desc_pt, tech_pt = extract_project_info_from_readme(
        readme_text=readme,
        repo_lang="Python",
        topics=["latex", "automation"],
        target_lang="pt-br",
    )
    assert "Gerador automático de currículos Acadêmicos" in desc_pt
    assert "Python" in tech_pt
    assert "LaTeX" in tech_pt
    assert "Flask" in tech_pt
    assert "Docker" in tech_pt

    # Test en-us extraction
    desc_en, tech_en = extract_project_info_from_readme(
        readme_text=readme,
        repo_lang="Python",
        topics=["latex", "automation"],
        target_lang="en-us",
    )
    assert "Automatic Academic and Professional resume generator" in desc_en
    assert "Python" in tech_en
    assert "LaTeX" in tech_en


def test_extract_project_info_fallback():
    desc, tech = extract_project_info_from_readme(
        readme_text="",
        repo_lang="C",
        topics=["algorithms"],
        target_lang="pt-br",
        fallback_desc="Descrição padrão de fallback",
    )
    assert desc == "Descrição padrão de fallback"
    assert tech == "C"


SAMPLE_CV_FOR_PROJECTS = {
    "name": "João Lucas Mayrinck D'Oliveira",
    "title": "Especialista em Tecnologia & Desenvolvimento",
    "location": "Belo Horizonte, MG",
    "email": "joao@example.com",
    "phone": "+55 31 99999-9999",
    "summary": "Portfólio profissional e acadêmico.",
    "skills": [
        {"category": "Linguagens", "items": "Python, C, JavaScript, LaTeX"},
    ],
    "experience": [
        {
            "role": "Monitor de Programação",
            "organization": "Universidade Federal de Viçosa",
            "period": "2021 - 2022",
            "description": "Auxílio a discentes em algoritmos."
        }
    ],
    "education": [
        {
            "degree": "Bacharelado em Sistemas de Informação",
            "institution": "Universidade Federal de Viçosa",
            "period": "2019 - 2025",
            "details": "Graduação completa."
        }
    ],
    "projects": [
        {
            "name": "latex-resume",
            "tech": "Python, LaTeX, Flask, Docker, Jinja2",
            "url": "https://github.com/Jluckmay/latex-resume",
            "description": "Gerador automático de currículos Acadêmicos e Profissionais em LaTeX + PDF alimentado por múltiplos provedores de IA."
        },
        {
            "name": "minecraft-map-convertion",
            "tech": "Python, Java, Git, Bash",
            "url": "https://github.com/Jluckmay/minecraft-map-convertion",
            "description": "Utilitário automatizado de conversão projetado para converter mundos entre as edições Minecraft Java e Bedrock."
        }
    ]
}

SAMPLE_LINKS = {
    "github": "https://github.com/Jluckmay",
    "linkedin": "https://linkedin.com/in/jluckmay",
}


@pytest.mark.parametrize(
    "tmpl",
    [
        "overleaf_russell_ti",
        "overleaf_awesome_cv",
        "overleaf_single_page_keywords",
        "nico_krieger",
        "google_standard",
        "modern_pro",
        "ai_ats_max",
    ],
)
def test_projects_never_have_right_hand_link_option(tmpl: str):
    """Garante que links para projetos estejam contidos exclusivamente no nome clicável e sem a opção 'Link' à direita."""
    tex = render_builtin_template(tmpl, SAMPLE_CV_FOR_PROJECTS, SAMPLE_LINKS, lang="pt-br")
    
    # 1. Project name must be clickable with href
    assert r"\href{https://github.com/Jluckmay/latex-resume}" in tex
    assert "latex-resume" in tex

    # 2. Must NOT contain right-hand "Link" text
    assert r"\href{https://github.com/Jluckmay/latex-resume}{\small Link}" not in tex
    assert r"\href{https://github.com/Jluckmay/latex-resume}{\textit{Link}}" not in tex
    assert r"\hfill \textit{Link}" not in tex
    assert r"\hfill \textit{https://github.com/Jluckmay/latex-resume}" not in tex


@pytest.mark.parametrize("tmpl", ["overleaf_russell_ti", "overleaf_awesome_cv"])
def test_russell_and_awesome_cv_single_stack_listing_and_no_duplicate_smallcaps(tmpl: str):
    """Garante que no Modelo Russell e Awesome CV a stack tecnológica seja renderizada exatamente uma vez por projeto."""
    tex = render_builtin_template(tmpl, SAMPLE_CV_FOR_PROJECTS, SAMPLE_LINKS, lang="pt-br")

    # \cventry must have empty #1 and empty #3: \cventry{}{\href...}{}{}{...}
    assert r"\cventry{}{\href{https://github.com/Jluckmay/latex-resume}" in tex

    # Must contain the full tech stack inside itemize
    assert r"\textbf{Ferramentas \& Tecnologias:} Python, LaTeX, Flask, Docker, Jinja2" in tex

    # Must NOT have Python, LaTeX... twice in the same cventry
    occurrences = tex.count("Python, LaTeX, Flask, Docker, Jinja2")
    assert occurrences == 1, f"Expected tech stack to appear exactly once, but found {occurrences} times"
