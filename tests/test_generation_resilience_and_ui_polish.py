"""Testes de validação para resiliência de geração LaTeX, prevenção de páginas em branco,
responsividade do visualizador de código e balanceamento de templates.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from src.direct_builder import build_structured_cv_deterministically
from src.llm_client import LLMResumeGenerator
from src.pipeline import _is_pdf_blank_or_corrupted, build_resume_pipeline
from src.templates import render_builtin_template


def test_truncated_llm_response_rejected_and_falls_back_to_base_latex():
    """Garante que respostas parciais/truncadas da IA (sem \\end{document}) são rejeitadas sem poluir o cache."""
    generator = LLMResumeGenerator(provider="default")
    base_tex = (
        r"\documentclass{article}"
        r"\begin{document}"
        r"\section{Experiência}"
        r"Engenheiro de Software"
        r"\end{document}"
    )

    # Simula resposta cortada no meio (exatamente como reportado pelo usuário: terminando abruptamente)
    truncated_response = (
        r"\begin{document}"
        r"\section{Perfil}"
        r"Portfólio do candidato"
        r"\section{Experiência}"
        r"\cventry{Quadro-Branco}{Link}{}{}{\begin{itemiz"
    )

    with patch.object(
        generator,
        "_call_llm_chat",
        return_value=(
            truncated_response,
            {"total_tokens": 500},
            "nvidia/test-model",
            False,
        ),
    ):
        enhanced_tex, metrics = generator.review_and_enhance_latex(
            base_latex=base_tex,
            resume_type="profissional",
            lang="pt-br",
        )

        # Deve rejeitar a resposta truncada e preservar o base_latex íntegro
        assert enhanced_tex == base_tex
        assert r"\end{document}" in enhanced_tex
        assert r"\begin{itemiz" not in enhanced_tex


def test_blank_pdf_detection_logic(tmp_path):
    """Garante que PDFs com menos de 25 caracteres ou tamanho ínfimo são detectados como vazios."""
    # 1. Arquivo inexistente
    non_existent = tmp_path / "nao_existe.pdf"
    assert _is_pdf_blank_or_corrupted(non_existent) is False

    # 2. Arquivo < 500 bytes (corrompido/truncado)
    tiny_pdf = tmp_path / "tiny.pdf"
    tiny_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    assert _is_pdf_blank_or_corrupted(tiny_pdf) is True

    # 3. PDF válido compilado com conteúdo real
    real_pdf = tmp_path / "real.pdf"
    from pypdf import PdfWriter
    writer = PdfWriter()
    # Adiciona página sem texto
    writer.add_blank_page(width=200, height=200)
    with open(real_pdf, "wb") as f:
        writer.write(f)
    assert _is_pdf_blank_or_corrupted(real_pdf) is True


def test_code_box_and_container_responsiveness_css():
    """Valida se o pre.code-box e o container possuem regras estritas contra overflow horizontal."""
    html = Path("index.html").read_text(encoding="utf-8")
    assert "minmax(0, 1.08fr)" in html
    assert "minmax(0, 0.92fr)" in html
    assert "white-space: pre-wrap;" in html
    assert "word-break: break-all;" in html
    assert "overflow-wrap: anywhere;" in html


def test_cvsection_single_argument_prevents_paragraph_swallowing():
    """Valida se \\cvsection aceita 1 argumento nos modelos Russell CV e Awesome CV."""
    cv = {
        "name": "Carlos Dev",
        "title": "Engenheiro",
        "summary": "Perfil profissional executivo.",
        "skills": [{"category": "Linguagens", "items": "Python, C"}],
    }
    links = {"linkedin": "https://linkedin.com/in/carlos"}

    for tpl_id in ("overleaf_russell_ti", "overleaf_awesome_cv"):
        tex = render_builtin_template(
            template_id=tpl_id,
            cv=cv,
            links=links,
            resume_type="profissional",
            lang="pt-br",
        )
        assert r"\newcommand{\cvsection}[1]" in tex
        assert r"\cvsection{" in tex
        # Não deve haver \\cvsection com 2 argumentos separados
        assert not any(line.strip().startswith(r"\cvsection{") and line.strip().count("}{") >= 1 for line in tex.splitlines() if not line.strip().startswith(r"\newcommand"))


def test_single_page_keywords_column_balance():
    """Valida o balanceamento simétrico de seções nas duas colunas do template Single Page + Keywords."""
    cv = {
        "name": "Carlos Dev",
        "experience": [{"role": "Engenheiro", "organization": "Tech", "period": "2023"}],
        "education": [{"degree": "B.S.", "institution": "USP", "period": "2020"}],
        "skills": [{"category": "Stack", "items": "Python, Go"}],
        "projects": [{"name": "App", "tech": "React", "description": "Portal"}],
        "languages": ["Português", "Inglês"],
    }
    tex = render_builtin_template(
        template_id="overleaf_single_page_keywords",
        cv=cv,
        links={},
        resume_type="profissional",
        lang="pt-br",
    )
    # Verifica que multicols está presente
    assert r"\begin{multicols}{2}" in tex
    assert r"\columnbreak" in tex
    # Quebra de coluna divide Trabalho/Educação na coluna 1 e Projetos/Skills na coluna 2
    parts = tex.split(r"\columnbreak")
    assert len(parts) == 2
    col1, col2 = parts[0], parts[1]
    assert "WORK" in col1 or "EXPERIÊNCIA" in col1
    assert "EDUCATION" in col1 or "FORMAÇÃO ACADÊMICA" in col1
    assert "SKILLS" in col2 or "COMPETÊNCIAS" in col2
    assert "OTHER PROJECTS" in col2 or "PROJETOS DE DESTAQUE" in col2


def test_portfolio_summary_synthesis_scrubs_raw_meta_description():
    """Valida se o resumo sintetizado limpa meta tags brutas como 'Portfólio profissional de...'."""
    raw_data = {
        "portfolio": {
            "description": "Portfólio profissional de João Lucas Mayrinck D'Oliveira, mestrando em Ciência da Computação na UFMG."
        }
    }
    cv = build_structured_cv_deterministically(raw_data, resume_type="profissional", lang="pt-br")
    assert not cv["summary"].startswith("Portfólio profissional de")
    assert "Mestrando em Ciência da Computação na UFMG" in cv["summary"]
    assert "Especialista em Computação e Tecnologia" in cv["summary"]
