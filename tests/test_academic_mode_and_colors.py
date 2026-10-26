import pytest
from src.templates import render_builtin_template
from src.ui_theme import apply_custom_colors_and_portfolio_to_latex
from src.llm_client import LLMResumeGenerator


@pytest.fixture
def sample_academic_cv():
    return {
        "name": "João Lucas Mayrinck",
        "title": "Pesquisador Acadêmico & Cientista",
        "email": "lucas.mayrinck@dcc.ufmg.br",
        "phone": "+55 31 99999-9999",
        "location": "Belo Horizonte, MG",
        "summary": "Pesquisador e desenvolvedor com foco em IA, computação educacional e engenharia de software.",
        "education": [
            {
                "degree": "Mestrado em Ciência da Computação",
                "institution": "Universidade Federal de Minas Gerais",
                "period": "2026 - Atual",
                "details": "DCC/UFMG",
            },
            {
                "degree": "Bacharelado em Sistemas de Informação",
                "institution": "Universidade Federal de Viçosa",
                "period": "2019 - 2025",
                "details": "Campus Rio Paranaíba",
            },
        ],
        "experience": [
            {
                "role": "Monitor de Desenvolvimento de Jogos",
                "organization": "Universidade Federal de Viçosa",
                "period": "2025",
                "bullets": ["Orientação prática e acompanhamento de estudantes no desenvolvimento de jogos."],
            },
            {
                "role": "Bolsista de Pesquisa",
                "organization": "FUNARBEN",
                "period": "2023 - 2024",
                "bullets": ["Pesquisa em figuras dinâmicas no GeoGebra aplicadas ao ensino."],
            },
        ],
        "projects": [
            {
                "name": "jluckmay.github.io",
                "tech": "HTML5, Python, LaTeX",
                "url": "https://github.com/Jluckmay/jluckmay.github.io",
                "description": "",  # Empty description to test synthesis
            },
            {
                "name": "minecraft-map-convertion",
                "tech": "",  # Empty tech to test no ()
                "url": "https://github.com/Jluckmay/minecraft-map-convertion",
                "description": "Utilitário automatizado de conversão e ponte estrutural.",
            },
        ],
        "publications": [
            {
                "title": "Math-O-Ween: Jogo Educacional-Resumo Estendido",
                "venue": "Revista Brasileira de Informática na Educação",
                "year": "2026",
                "authors": "R. Coêlho, F. Bastos, J. L. Mayrinck",
                "doi": "10.5753/rbie.2026.6599",
            },
            {
                "title": "PDI Interativo: Uma Ferramenta Espacial",
                "venue": "Anais do XVI WSIS",
                "year": "2025",
                "authors": "PDI Interativo",  # Bogus author identical to title
                "doi": "10.5753/wsis.2025.15098",
            },
        ],
        "skills": [
            {"category": "Linguagens & Tecnologias", "items": "Python, C++, LaTeX, JavaScript"},
        ],
        "languages": ["Português (Fluente)", "Inglês (Intermediário)", "Espanhol (Básico)", "Libras (Básico)"],
        "awards": ["Menção Honrosa · Games · SBIE 2024", "Segundo Lugar · Ensino · SIA 2023"],
    }


@pytest.fixture
def sample_links():
    return {
        "github": "https://github.com/jluckmay",
        "linkedin": "https://linkedin.com/in/jluckmay",
        "orcid": "https://orcid.org/0009-0001-0178-4877",
        "scholar": "https://scholar.google.com/citations?user=xyz",
        "lattes": "http://lattes.cnpq.br/7395864900833083",
        "portfolio": "https://jluckmay.github.io",
    }


def test_academic_classic_includes_all_sections_and_custom_colors(sample_academic_cv, sample_links):
    """Garante que o modelo Acadêmico Clássico inclui todas as seções acadêmicas e respeita as cores."""
    raw_tex = render_builtin_template(
        template_id="academic_classic",
        cv=sample_academic_cv,
        links=sample_links,
        resume_type="academico",
        lang="pt-br",
    )
    themed_tex = apply_custom_colors_and_portfolio_to_latex(
        latex_code=raw_tex,
        primary_color="#18181B",
        secondary_color="#3F3F46",
        portfolio_url=sample_links["portfolio"],
        lang="pt-br",
    )

    # 1. Cores aplicadas
    assert r"\definecolor{acadnavy}{HTML}{18181B}" in themed_tex
    assert r"\definecolor{subaccent}{HTML}{3F3F46}" in themed_tex

    # 2. Todas as seções presentes
    assert "Formação Acadêmica" in themed_tex
    assert "Atuação Acadêmica e Profissional" in themed_tex
    assert "Produção Científica e Publicações" in themed_tex
    assert "Projetos de Pesquisa e Desenvolvimento" in themed_tex
    assert "Competências Técnicas e Metodológicas" in themed_tex
    assert "Idiomas" in themed_tex
    assert "Prêmios, Títulos e Certificações" in themed_tex

    # 3. Nenhum () vazio
    assert "()" not in themed_tex
    assert "( )" not in themed_tex


def test_overleaf_russell_ti_in_academic_mode(sample_academic_cv, sample_links):
    """Garante que o Modelo Russell CV em modo Acadêmico renderiza todas as seções e aplica Grafite ATS."""
    raw_tex = render_builtin_template(
        template_id="overleaf_russell_ti",
        cv=sample_academic_cv,
        links=sample_links,
        resume_type="academico",
        lang="pt-br",
    )
    themed_tex = apply_custom_colors_and_portfolio_to_latex(
        latex_code=raw_tex,
        primary_color="#18181B",
        secondary_color="#3F3F46",
        portfolio_url=sample_links["portfolio"],
        lang="pt-br",
    )

    # 1. Cores Grafite ATS
    assert r"\definecolor{accent}{HTML}{18181B}" in themed_tex
    assert r"\definecolor{sidecolor}{HTML}{3F3F46}" in themed_tex

    # 2. Seções presentes
    assert r"\cvsection{Formação Acadêmica}" in themed_tex
    assert r"\cvsection{Atuação Acadêmica e Profissional}" in themed_tex
    assert r"\cvsection{Produção Científica e Publicações}" in themed_tex
    assert r"\cvsection{Projetos de Pesquisa e Desenvolvimento}" in themed_tex
    assert r"\cvsection{Competências Técnicas e Metodológicas}" in themed_tex
    assert r"\cvsection{Idiomas}" in themed_tex
    assert r"\cvsection{Prêmios, Títulos e Certificações}" in themed_tex

    # 3. Idiomas com escala de 6 bullets
    assert r"\faIcon[solid]{circle}" in themed_tex
    assert r"\faIcon[regular]{circle}" in themed_tex

    # 4. Nenhum () vazio
    assert "()" not in themed_tex
    assert "( )" not in themed_tex


def test_projects_synthesis_never_renders_empty_description_or_parens():
    """Valida se projetos sem descrição ou sem tech stack recebem descrição sintetizada e zero ()."""
    cv = {
        "name": "Candidato Teste",
        "projects": [
            {"name": "meu-projeto", "tech": "", "description": "", "url": "https://github.com/user/meu-projeto"},
            {"name": "outro-projeto", "tech": "Python", "description": "", "url": ""},
        ],
    }
    tex_acad = render_builtin_template("academic_classic", cv, {}, resume_type="academico")
    tex_russell = render_builtin_template("overleaf_russell_ti", cv, {}, resume_type="academico")

    for tex in (tex_acad, tex_russell):
        assert "()" not in tex
        assert "( )" not in tex
        # Descrição sintetizada não vazia
        assert "meu-projeto" in tex
        assert "outro-projeto" in tex


def test_publication_author_and_resumo_estendido_cleaning():
    """Valida higienização de autor espúrio (cópia do título) e formatação de Resumo Estendido."""
    cv = {
        "name": "Candidato Teste",
        "publications": [
            {
                "title": "Artigo Um-Resumo Estendido",
                "venue": "SBIE",
                "year": "2024",
                "authors": "Artigo Um",  # Repetição do título
                "doi": "10.1234/test",
            }
        ],
    }
    tex = render_builtin_template("academic_classic", cv, {}, resume_type="academico")
    # Confirma que -Resumo Estendido virou (Resumo Estendido)
    assert "(Resumo Estendido)" in tex
    # Confirma que não duplicou "Artigo Um. Artigo Um"
    assert "Artigo Um. Artigo Um" not in tex


def test_llm_client_fallbacks_preserve_experience_and_skills():
    """Valida se _apply_fallbacks recupera experiência e competências de fontes reais se o LLM omitir."""
    raw_profile = {
        "portfolio": {
            "employments": [
                {"role": "Monitor de Ensino", "organization": "UFV", "period": "2022", "description": "Ensino prático."}
            ]
        },
        "github": {
            "languages": ["Python", "C++", "LaTeX"],
            "repos": [{"name": "repo1", "tech": "Python", "description": "Descrição do repo 1"}],
        },
    }
    sparse_cv = {
        "name": "João",
        "education": [],
        "experience": [],
        "skills": [],
        "projects": [{"name": "repo1", "tech": "", "description": ""}],
    }

    LLMResumeGenerator._apply_fallbacks(sparse_cv, raw_profile, resume_type="academico", lang="pt-br")

    assert len(sparse_cv["experience"]) > 0
    assert sparse_cv["experience"][0]["role"] == "Monitor de Ensino"
    assert len(sparse_cv["skills"]) > 0
    assert "Python" in sparse_cv["skills"][0]["items"]
    # Descrição do projeto recuperada do repositório
    assert sparse_cv["projects"][0]["description"] == "Descrição do repo 1"
    assert sparse_cv["projects"][0]["tech"] == "Python"


def test_review_and_enhance_truncation_detection_protects_missing_sections():
    """Valida se o revisor LLM rejeita respostas truncadas que omitam seções originais."""
    generator = LLMResumeGenerator(provider="none", use_cache=False)
    base_latex = (
        r"\documentclass{article}" "\n"
        r"\begin{document}" "\n"
        r"\cvsection{Perfil}" "\nResumo aqui\n"
        r"\cvsection{Formação Acadêmica}" "\nEducação aqui\n"
        r"\cvsection{Produção Científica e Publicações}" "\nPubs aqui\n"
        r"\cvsection{Projetos de Pesquisa e Desenvolvimento}" "\nProjetos aqui\n"
        r"\cvsection{Atuação Acadêmica e Profissional}" "\nExperiência aqui\n"
        r"\cvsection{Idiomas}" "\nIdiomas aqui\n"
        r"\end{document}"
    )

    # Simula resposta truncada do modelo (que parou em Projetos)
    truncated_llm_output = (
        r"\cvsection{Perfil}" "\nResumo melhorado\n"
        r"\cvsection{Formação Acadêmica}" "\nEducação melhorada\n"
        r"\cvsection{Produção Científica e Publicações}" "\nPubs\n"
        r"\cvsection{Projetos de Pesquisa e Desenvolvimento}" "\nProjetos\n"
        r"\end{document}"
    )

    generator._call_llm_chat = lambda messages, max_tokens: (truncated_llm_output, {}, "mock_model", False)
    final_latex, metrics = generator.review_and_enhance_latex(
        base_latex=base_latex,
        resume_type="academico",
        lang="pt-br",
    )

    # Deve rejeitar a resposta truncada e preservar o base_latex completo com todas as seções
    assert r"\cvsection{Atuação Acadêmica e Profissional}" in final_latex
    assert r"\cvsection{Idiomas}" in final_latex


def test_index_html_no_template_hijacking_and_6_bullets():
    """Verifica que index.html preserva a seleção de template e usa 6 bullets no preview do Russell CV."""
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Não deve forçar selectTemplate("academic_classic") ao mudar resumeType
    assert 'selectTemplate("academic_classic")' not in html
    # Preview de idiomas no Russell CV deve ter 6 bullets
    assert "● ● ● ● ● ●" in html

