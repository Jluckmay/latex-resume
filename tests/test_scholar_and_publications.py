"""Testes para integração do Google Scholar, extração de publicações, idiomas e premiações."""

from pathlib import Path
from unittest.mock import patch
import pytest

from src.extractors import (
    parse_scholar_input,
    extract_scholar,
    extract_portfolio,
    extract_orcid,
)
from src.direct_builder import (
    build_structured_cv_deterministically,
    generate_direct_latex_resume,
)
from src.templates import (
    BUILTIN_TEMPLATES,
    render_builtin_template,
    _get_platform_display,
)
from src.compiler import compile_latex_to_pdf
from src.pipeline import build_resume_pipeline

MOCK_SCHOLAR_HTML = """
<!DOCTYPE html>
<html>
<head><title>Google Scholar</title></head>
<body>
<div id="gsc_prf_in">Ada Lovelace</div>
<div class="gsc_prf_il">Pioneer of Computer Science, University of London</div>
<div id="gsc_prf_int">
    <a href="#">Computing</a>
    <a href="#">Algorithms</a>
</div>
<table id="gsc_rsb_st">
    <tr><th></th><th>All</th><th>Since 2019</th></tr>
    <tr><td><a href="#">Citations</a></td><td>15420</td><td>3200</td></tr>
    <tr><td><a href="#">h-index</a></td><td>42</td><td>28</td></tr>
    <tr><td><a href="#">i10-index</a></td><td>65</td><td>40</td></tr>
</table>
<table id="gsc_a_t">
    <tr class="gsc_a_tr">
        <td class="gsc_a_t">
            <a class="gsc_a_at" href="/citations?view_op=view_citation&user=TESTUSER&citation_for_view=TESTUSER:1">Sketch of the Analytical Engine invented by Charles Babbage</a>
            <div class="gs_gray">A Lovelace, LF Menabrea</div>
            <div class="gs_gray">Scientific Memoirs 3, 666-731, 1843</div>
        </td>
        <td class="gsc_a_c"><a class="gsc_a_ac" href="#">8500</a></td>
        <td class="gsc_a_y"><span class="gsc_a_h">1843</span></td>
    </tr>
    <tr class="gsc_a_tr">
        <td class="gsc_a_t">
            <a class="gsc_a_at" href="/citations?view_op=view_citation&user=TESTUSER&citation_for_view=TESTUSER:2">Notes on the Bernoulli Number Algorithm</a>
            <div class="gs_gray">A Lovelace</div>
            <div class="gs_gray">Journal of Early Computation, 1844</div>
        </td>
        <td class="gsc_a_c"><a class="gsc_a_ac" href="#">1200</a></td>
        <td class="gsc_a_y"><span class="gsc_a_h">1844</span></td>
    </tr>
</table>
</body>
</html>
"""

MOCK_PORTFOLIO_HTML = """
<!DOCTYPE html>
<html>
<head><title>João Lucas Mayrinck</title></head>
<body>
<header>
    <h1>Mayrinck, J. L.</h1>
</header>
<article class="research-item">
    <h3>Idiomas</h3>
    <div class="language-list">
        <div>
            <div class="language-label">
                <span>Português</span>
                <strong>Fluente</strong>
            </div>
        </div>
        <div>
            <div class="language-label">
                <span>Inglês</span>
                <strong>Intermediário</strong>
            </div>
        </div>
        <div>
            <div class="language-label">
                <span>Espanhol</span>
                <strong>Iniciante</strong>
            </div>
        </div>
        <div>
            <div class="language-label">
                <span>Libras</span>
                <strong>Iniciante</strong>
            </div>
        </div>
    </div>
</article>

<section>
    <h3>Premiações & Reconhecimentos</h3>
    <div class="award-card">
        Menção Honrosa · Games · SBIE 2024 Palavras ao Ar ficou entre três melhores artigos da trilha.
    </div>
    <div class="award-card">
        Menção Honrosa · Pôster · WSIS 2025 Explorando a Grécia Antiga foi selecionado entre os melhores trabalhos.
    </div>
</section>

<section>
    <h3>Publicações</h3>
    <article class="pub-card">
        <h4>Math-0-Ween: Um Jogo Digital Educacional para Explorar Operações Matemáticas de Forma Divertida e Assustadora</h4>
        <p>Revista Brasileira de Informática na Educação · 2026</p>
        <a href="https://doi.org/10.5753/rbie.2026.6599">DOI ↗</a>
    </article>
    <article class="pub-card">
        <h4>PDI Interativo: Uma Ferramenta para Estudo e Experimentação com Abordagem Espacial e Frequencial</h4>
        <p>Anais do XVI Workshop de Sistemas de Informação · 2025</p>
        <a href="https://doi.org/10.5753/wsis.2025.15098">DOI ↗</a>
    </article>
</section>
</body>
</html>
"""


def test_parse_scholar_input():
    # URL completa
    u, sid = parse_scholar_input("https://scholar.google.com/citations?user=JicYPdAAAAAJ&hl=en")
    assert u == "https://scholar.google.com/citations?user=JicYPdAAAAAJ"
    assert sid == "JicYPdAAAAAJ"

    # URL scholar.google.com.br
    u2, sid2 = parse_scholar_input("https://scholar.google.com.br/citations?user=AbCdEfGhIjKl")
    assert u2 == "https://scholar.google.com/citations?user=AbCdEfGhIjKl"
    assert sid2 == "AbCdEfGhIjKl"

    # Apenas o ID
    u3, sid3 = parse_scholar_input("JicYPdAAAAAJ")
    assert u3 == "https://scholar.google.com/citations?user=JicYPdAAAAAJ"
    assert sid3 == "JicYPdAAAAAJ"

    # Input vazio
    assert parse_scholar_input("") == ("", "")
    assert parse_scholar_input(None) == ("", "")


def test_extract_scholar_mocked():
    with patch("src.extractors._safe_http_get", return_value=(200, MOCK_SCHOLAR_HTML, "")):
        data = extract_scholar("TESTUSER")
        assert data["name"] == "Ada Lovelace"
        assert "University of London" in data["affiliation"]
        assert data["metrics"].get("Citations") == "15420"
        assert data["metrics"].get("h-index") == "42"
        assert len(data["publications"]) == 2
        p1 = data["publications"][0]
        assert "Analytical Engine" in p1["title"]
        assert p1["year"] == "1843"
        assert p1["citations"] == "8500"
        assert "Lovelace" in p1["authors"]


def test_extract_portfolio_languages_awards_and_publications():
    with patch("src.extractors._safe_http_get", return_value=(200, MOCK_PORTFOLIO_HTML, "")):
        data = extract_portfolio("https://jluckmay.github.io")
        assert len(data["languages"]) == 4
        assert "Português (Fluente)" in data["languages"]
        assert "Inglês (Intermediário)" in data["languages"]
        assert "Espanhol (Iniciante)" in data["languages"]
        assert "Libras (Iniciante)" in data["languages"]

        assert len(data["awards"]) >= 2
        assert any("SBIE 2024" in a for a in data["awards"])
        assert any("WSIS 2025" in a for a in data["awards"])

        assert len(data["publications"]) == 2
        p1 = data["publications"][0]
        assert "Math-0-Ween" in p1["title"]
        assert p1["doi"] == "10.5753/rbie.2026.6599"


def test_platform_display_scholar():
    links = {"scholar": "https://scholar.google.com/citations?user=JicYPdAAAAAJ", "scholar_name": "João Lucas Mayrinck"}
    assert _get_platform_display(links, "scholar") == "J. L. Mayrinck"

    links_cand = {"scholar": "https://scholar.google.com/citations?user=JicYPdAAAAAJ", "candidate_name": "Ada Lovelace"}
    assert _get_platform_display(links_cand, "scholar") == "A. Lovelace"

    links_empty = {"scholar": "https://scholar.google.com/citations?user=JicYPdAAAAAJ"}
    assert _get_platform_display(links_empty, "scholar") == "Google Scholar"


@pytest.mark.parametrize("template_id", list(BUILTIN_TEMPLATES.keys()))
def test_all_templates_render_scholar_link_and_icon(template_id):
    cv = {
        "name": "Ada Lovelace",
        "title": "Computer Scientist",
        "email": "ada@computing.org",
        "location": "London, UK",
        "languages": ["English (Native)", "French (Fluent)"],
        "awards": ["Royal Scientific Distinction (1845)"],
        "publications": [
            {
                "title": "Sketch of the Analytical Engine",
                "venue": "Scientific Memoirs",
                "year": "1843",
                "authors": "A. Lovelace, L. F. Menabrea",
                "doi": "10.1000/1843.engine",
            }
        ],
    }
    links = {
        "scholar": "https://scholar.google.com/citations?user=JicYPdAAAAAJ",
        "scholar_id": "JicYPdAAAAAJ",
        "github": "https://github.com/adalovelace",
        "orcid": "https://orcid.org/0000-0002-1825-0097",
    }
    tex = render_builtin_template(template_id, cv, links, resume_type="academico")
    assert r"\faIcon{google}" in tex or r"\faIcon[regular]{google}" in tex
    assert "scholar.google.com" in tex


def test_smart_publication_merging_and_deduplication():
    raw_profile = {
        "user_meta": {"name": "João Lucas"},
        "links": {},
        "lattes": {
            "publications": [
                {
                    "title": "Math-0-Ween: Um Jogo Digital",
                    "year": "2026",
                    "venue": "",
                    "doi": "",
                    "authors": "Mayrinck, J. L.",
                },
                {
                    "title": "Palavras ao Ar",
                    "year": "2024",
                    "venue": "SBIE",
                    "doi": "",
                },
                {
                    "title": "Palavras ao Ar",
                    "year": "2025",
                    "venue": "WSIS",
                    "doi": "",
                },
            ]
        },
        "orcid": {
            "works": [
                {
                    "title": "Math-0-Ween: Um Jogo Digital Educacional para Explorar",
                    "year": "2026",
                    "journal": "Revista Brasileira de Informática na Educação",
                    "doi": "10.5753/rbie.2026.6599",
                }
            ]
        },
        "scholar": {
            "publications": [
                {
                    "title": "Math-0-Ween: Um Jogo Digital",
                    "year": "2026",
                    "authors": "J. L. Mayrinck, R. Silva",
                    "venue": "RBIE",
                    "citations": "12",
                }
            ]
        },
        "portfolio": {},
    }

    cv = build_structured_cv_deterministically(raw_profile, resume_type="academico")
    pubs = cv["publications"]

    # 1. Math-0-Ween deve ser fundido em uma única entrada rica com DOI, autores e venue
    math_pubs = [p for p in pubs if "math-0-ween" in p["title"].lower()]
    assert len(math_pubs) == 1
    m = math_pubs[0]
    assert m["doi"] == "10.5753/rbie.2026.6599"
    assert "Revista Brasileira" in m["venue"] or "RBIE" in m["venue"]
    assert m["citations"] == "12"

    # 2. Palavras ao Ar 2024 e 2025 têm anos diferentes e devem ser PRESERVADOS ambos
    palavras = [p for p in pubs if "palavras ao ar" in p["title"].lower()]
    assert len(palavras) == 2
    years = {p["year"] for p in palavras}
    assert "2024" in years and "2025" in years


def test_languages_and_awards_populated_from_portfolio_when_lattes_empty():
    raw_profile = {
        "user_meta": {"name": "Pesquisador Teste"},
        "links": {"portfolio": "https://jluckmay.github.io"},
        "lattes": {},
        "orcid": {},
        "portfolio": {
            "languages": ["Português (Fluente)", "Inglês (Intermediário)", "Libras (Iniciante)"],
            "awards": ["Menção Honrosa - SBIE 2024", "Menção Honrosa - WSIS 2025"],
            "publications": [
                {"title": "Artigo A", "venue": "SBIE", "year": "2024", "doi": "10.1234/a"}
            ],
        },
    }

    cv = build_structured_cv_deterministically(raw_profile, resume_type="academico")
    assert len(cv["languages"]) == 3
    assert "Português (Fluente)" in cv["languages"]
    assert len(cv["awards"]) == 2
    assert "Menção Honrosa - SBIE 2024" in cv["awards"]
    assert len(cv["publications"]) == 1


def test_pipeline_with_scholar_and_supplementary_data(tmp_path):
    result = build_resume_pipeline(
        resume_type="academico",
        scholar_input="https://scholar.google.com/citations?user=JicYPdAAAAAJ",
        portfolio_url="https://jluckmay.github.io",
        template_id="overleaf_russell_ti",
        provider="none",
        data_source_mode="import",
        manual_data={"languages": "Português (Fluente), Francês (Básico)", "awards": "Prêmio Jovem Pesquisador 2024"},
        build_dir=tmp_path,
        output_stem="test_scholar_supplementary",
    )

    assert result.success is True
    assert "scholar.google.com" in result.latex_code
    assert r"\faIcon{google}" in result.latex_code
    assert "Português" in result.latex_code
    assert "Prêmio Jovem Pesquisador" in result.latex_code


def test_abbreviate_researcher_name():
    from src.templates import abbreviate_researcher_name

    assert abbreviate_researcher_name("") == ""
    assert abbreviate_researcher_name("Mayrinck") == "Mayrinck"
    assert abbreviate_researcher_name("Ada Lovelace") == "A. Lovelace"
    assert abbreviate_researcher_name("João Lucas Mayrinck") == "J. L. Mayrinck"
    assert abbreviate_researcher_name("João Lucas de Oliveira Mayrinck") == "J. L. O. Mayrinck"
    assert abbreviate_researcher_name("João Lucas Mayrinck D'Oliveira") == "J. L. M. D'Oliveira"
    assert abbreviate_researcher_name("Marie Sklodowska Curie") == "M. S. Curie"


def test_ai_ats_max_header_formatting_and_mbox():
    from src.templates import render_builtin_template

    cv = {
        "name": "João Lucas Mayrinck D'Oliveira",
        "title": "Cientista da Computação",
        "email": "teste@exemplo.com",
        "phone": "+55 31 99999-9999",
        "location": "Belo Horizonte, MG",
        "summary": "Resumo do perfil",
        "experience": [],
        "education": [],
        "projects": [],
        "publications": [],
        "skills": ["Python", "LaTeX"],
    }
    links = {
        "scholar": "https://scholar.google.com/citations?user=TULpQMIAAAAJ",
        "scholar_id": "TULpQMIAAAAJ",
        "candidate_name": "João Lucas Mayrinck D'Oliveira",
        "portfolio": "https://jluckmay.github.io",
        "github": "https://github.com/jluckmay",
        "github_nick": "jluckmay",
        "linkedin": "https://linkedin.com/in/jluckmay",
        "linkedin_nick": "jluckmay",
    }

    latex = render_builtin_template(
        template_id="ai_ats_max",
        cv=cv,
        links=links,
        resume_type="academico",
        lang="pt-br",
    )

    # 1. Não deve haver prefixos de texto inconsistentes como "Local:" ou "Portfólio:"
    assert "Local:" not in latex
    assert "Portfólio:" not in latex

    # 2. Itens de contato devem estar protegidos com \mbox para evitar quebra de ícone/texto
    assert r"\mbox{\href{https://scholar.google.com/citations?user=TULpQMIAAAAJ}{\faIcon{google}\ \textbf{J. L. M. D'Oliveira}}}" in latex
    assert r"\mbox{\href{mailto:teste@exemplo.com}{\faIcon{envelope}\ teste@exemplo.com}}" in latex
    assert r"\mbox{\faIcon{phone}\ +55 31 99999-9999}" in latex
    assert r"\mbox{\href{https://github.com/jluckmay}{\faIcon{github}\ \textbf{jluckmay}}}" in latex

    # 3. Não deve usar o ID alfanumérico TULpQMIAAAAJ no rótulo de exibição do Scholar
    assert r"\textbf{TULpQMIAAAAJ}" not in latex


def test_index_html_no_fake_cards():
    import pathlib

    html_path = pathlib.Path(__file__).parent.parent / "index.html"
    content = html_path.read_text(encoding="utf-8")

    # Garante que initStructuredManualInputs não injeta cards preenchidos fictícios por padrão
    assert "addStructuredExperience({" not in content
    assert "addStructuredEducation({" not in content
    assert "addStructuredProject({" not in content
    assert "addStructuredPublication({" not in content
    assert "addStructuredAward({" not in content

