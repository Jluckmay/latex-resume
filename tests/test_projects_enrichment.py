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
    assert desc == "Descrição padrão de fallback."
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



def test_sanitize_project_description_replaces_verbs_with_nouns():
    """Valida se descrições de projetos iniciam estritamente com substantivos (Gerador, Utilitário, etc.) e nunca verbos (Desenvolveu, Implementou)."""
    from src.extractors import sanitize_project_description

    # Caso do usuário: Minecraft
    desc_mc = "Implementou utilitário automatizado de conversão e ponte para suprir lacunas estruturais entre Minecraft Java Edition e Minecraft Bedrock."
    res_mc = sanitize_project_description(desc_mc, lang="pt-br")
    assert res_mc.startswith("Utilitário automatizado de conversão")
    assert not res_mc.startswith("Implementou")

    # Caso: latex-resume
    desc_lr = "Desenvolveu gerador automático de currículos acadêmicos e profissionais em LaTeX + PDF."
    res_lr = sanitize_project_description(desc_lr, lang="pt-br")
    assert res_lr.startswith("Gerador automático de currículos")
    assert not res_lr.startswith("Desenvolveu")

    # Caso: jluckmay.github.io
    desc_io = "Criou portfólio pessoal e acadêmico como página estática otimizada."
    res_io = sanitize_project_description(desc_io, lang="pt-br")
    assert res_io.startswith("Portfólio pessoal e acadêmico")
    assert not res_io.startswith("Criou")

    # Caso: C-Codes
    desc_cc = "Reuniu implementações manuais de funções matemáticas e manipuladores de string."
    res_cc = sanitize_project_description(desc_cc, lang="pt-br")
    assert res_cc.startswith("Implementações manuais de funções")
    assert not res_cc.startswith("Reuniu")

    # Caso: Quadro-Branco
    desc_qb = "Desenvolveu aplicação web multiusuária para criação e edição de conteúdo."
    res_qb = sanitize_project_description(desc_qb, lang="pt-br")
    assert res_qb.startswith("Aplicação web multiusuária")
    assert not res_qb.startswith("Desenvolveu")

    # Caso: MineMan
    desc_mm = "Criou jogo de exploração de labirintos inspirado no universo de Minecraft."
    res_mm = sanitize_project_description(desc_mm, lang="pt-br")
    assert res_mm.startswith("Jogo de exploração de labirintos")
    assert not res_mm.startswith("Criou")

    # Caso: Desenvolvido em Python para...
    desc_py = "Desenvolvido em Python para automação de tarefas acadêmicas."
    res_py = sanitize_project_description(desc_py, lang="pt-br")
    assert res_py.startswith("Ferramenta para automação de tarefas acadêmicas")

    # Caso: Inglês
    desc_en = "Implemented automated conversion utility and bridge between Minecraft Java Edition and Bedrock."
    res_en = sanitize_project_description(desc_en, lang="en-us")
    assert res_en.startswith("Automated conversion utility")
    assert not res_en.startswith("Implemented")


def test_clean_latex_project_verbs_preserves_experience_verbs():
    """Valida se clean_latex_project_verbs remove verbos apenas na seção de projetos, preservando a de experiência."""
    from src.compiler import clean_latex_project_verbs

    sample_latex = """
\\section*{Experiência Profissional}
\\begin{itemize}
    \\item Desenvolveu sistemas distribuídos de alta disponibilidade.
    \\item Implementou pipelines de CI/CD automatizados.
\\end{itemize}

\\section*{Projetos de Destaque e Open Source}
\\begin{itemize}
    \\item Desenvolveu gerador automático de currículos acadêmicos.
    \\item Implementou utilitário automatizado de conversão de mapas.
    \\item Criou jogo de exploração em Python.
\\end{itemize}
"""
    cleaned = clean_latex_project_verbs(sample_latex)

    # Experiência deve PRESERVAR verbos de ação
    assert "\\item Desenvolveu sistemas distribuídos de alta disponibilidade." in cleaned
    assert "\\item Implementou pipelines de CI/CD automatizados." in cleaned

    # Projetos deve CONVERTER para substantivos
    assert "\\item Gerador automático de currículos acadêmicos." in cleaned
    assert "\\item Utilitário automatizado de conversão de mapas." in cleaned
    assert "\\item Jogo de exploração em Python." in cleaned
    assert "Desenvolveu gerador" not in cleaned
    assert "Implementou utilitário" not in cleaned
    assert "Criou jogo" not in cleaned
