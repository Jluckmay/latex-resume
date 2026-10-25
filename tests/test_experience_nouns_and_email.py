"""Testes para conversão de verbos em substantivos na experiência e importação de email das fontes."""

from unittest.mock import patch, MagicMock

from src.extractors import (
    sanitize_experience_description,
    extract_portfolio,
    _parse_lattes_xml,
    extract_github,
)
from src.compiler import clean_latex_experience_verbs
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES, render_builtin_template


def test_sanitize_experience_description_pt_verbs_to_nouns():
    """Valida conversão de verbos no passado para substantivos em português conforme solicitado pelo usuário."""
    # 1. Participou -> Participação
    d1 = "Participou do processo de eleição da representação discente do Centro Acadêmico."
    r1 = sanitize_experience_description(d1, lang="pt-br")
    assert r1.startswith("Participação no processo")
    assert not r1.startswith("Participou")

    d1b = "Participou da organização da semana acadêmica."
    r1b = sanitize_experience_description(d1b, lang="pt-br")
    assert r1b.startswith("Participação na organização")

    d1c = "Participou de projetos de iniciação científica."
    r1c = sanitize_experience_description(d1c, lang="pt-br")
    assert r1c.startswith("Participação em projetos")

    # 2. Orientou -> Orientação
    d2 = "Orientou estudantes e apoiou no desenvolvimento e revisão de materiais de desenvolvimento de jogos."
    r2 = sanitize_experience_description(d2, lang="pt-br")
    assert r2.startswith("Orientação a estudantes")
    assert "e apoio no desenvolvimento" in r2
    assert not r2.startswith("Orientou")

    # 3. Acompanhou -> Acompanhamento
    d3 = "Acompanhou estudantes e apoiou o aprendizado de fundamentos de programação."
    r3 = sanitize_experience_description(d3, lang="pt-br")
    assert r3.startswith("Acompanhamento de estudantes")
    assert "e apoio ao aprendizado" in r3
    assert not r3.startswith("Acompanhou")

    # 4. Desenvolveu -> Desenvolvimento
    d4 = "Desenvolveu figuras dinâmicas no GeoGebra aplicadas ao ensino de matemática."
    r4 = sanitize_experience_description(d4, lang="pt-br")
    assert r4.startswith("Desenvolvimento de figuras dinâmicas")
    assert not r4.startswith("Desenvolveu")

    # 5. Ensinou -> Ensino
    d5 = "Ensinou conceitos de história da computação, noções de informática e pacote Office."
    r5 = sanitize_experience_description(d5, lang="pt-br")
    assert r5.startswith("Ensino de conceitos")
    assert not r5.startswith("Ensinou")

    # 6. Realizou -> Realização
    d6 = "Realizou trabalho voluntário em Ciência e Tecnologia (dez. de 2021 a mar. de 2023)."
    r6 = sanitize_experience_description(d6, lang="pt-br")
    assert r6.startswith("Realização de trabalho voluntário")
    assert not r6.startswith("Realizou")


def test_sanitize_experience_description_en():
    """Valida conversão em inglês para estilo substantivo/nominal."""
    assert sanitize_experience_description("Led engineering team", lang="en-us").startswith("Leadership of engineering team")
    assert sanitize_experience_description("Developed microservices", lang="en-us").startswith("Development of microservices")
    assert sanitize_experience_description("Taught introductory programming", lang="en-us").startswith("Instruction in introductory programming")
    assert sanitize_experience_description("Participated in agile ceremonies", lang="en-us").startswith("Participation in agile ceremonies")


def test_clean_latex_experience_verbs_in_compiler():
    """Valida se o compilador LaTeX converte verbos no bloco de experiência para substantivos."""
    tex_input = r"""
\section*{EXPERIÊNCIA PROFISSIONAL}
\begin{itemize}
    \item Participou do processo de eleição da representação discente.
    \item Orientou estudantes e apoiou no desenvolvimento de jogos.
    \item Desenvolveu figuras dinâmicas no GeoGebra.
    \item Ensinou conceitos de história da computação.
    \item Acompanhou estudantes e apoiou o aprendizado.
\end{itemize}

\section*{Projetos de Destaque}
\begin{itemize}
    \item Utilitário automatizado de conversão.
\end{itemize}
"""
    cleaned = clean_latex_experience_verbs(tex_input)
    assert r"\item Participação no processo de eleição" in cleaned
    assert r"\item Orientação a estudantes e apoio no desenvolvimento" in cleaned
    assert r"\item Desenvolvimento de figuras dinâmicas" in cleaned
    assert r"\item Ensino de conceitos de história" in cleaned
    assert r"\item Acompanhamento de estudantes e apoio ao aprendizado" in cleaned
    assert "Participou do" not in cleaned
    assert "Orientou estudantes" not in cleaned


def test_extract_portfolio_extracts_email():
    """Valida extração de email a partir de mailto: ou texto da página de portfólio."""
    html_with_mailto = """
    <html>
        <head><title>João Lucas Mayrinck</title></head>
        <body>
            <h1>João Lucas Mayrinck</h1>
            <p>Contato: <a href="mailto:lucas.mayrinck@dcc.ufmg.br?subject=Ola">Enviar email</a></p>
        </body>
    </html>
    """
    with patch("src.extractors._safe_http_get", return_value=(200, html_with_mailto, "")):
        data = extract_portfolio("https://jluckmay.github.io")
        assert data.get("email") == "lucas.mayrinck@dcc.ufmg.br"


def test_extract_lattes_xml_extracts_email():
    """Valida extração de email do XML da plataforma Lattes."""
    xml_content = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
    <CURRICULO-VITAE NUMERO-IDENTIFICADOR="7395864900833083">
        <DADOS-GERAIS NOME-COMPLETO="Lucas Silva">
            <ENDERECO>
                <ENDERECO-PROFISSIONAL E-MAIL="lucas.silva@ufv.br" />
            </ENDERECO>
        </DADOS-GERAIS>
    </CURRICULO-VITAE>
    """
    out = {}
    _parse_lattes_xml(xml_content, out)
    assert out.get("email") == "lucas.silva@ufv.br"


def test_extract_github_extracts_email_from_bio():
    """Valida extração de email do bio do GitHub se campo email estiver nulo na API."""
    mock_resp_user = MagicMock()
    mock_resp_user.status_code = 200
    mock_resp_user.json.return_value = {
        "name": "Lucas",
        "bio": "Pesquisador em IA. Contato: lucas@dcc.ufmg.br",
        "email": None,
    }
    mock_resp_repos = MagicMock()
    mock_resp_repos.status_code = 200
    mock_resp_repos.json.return_value = []

    with patch("requests.get", side_effect=[mock_resp_user, mock_resp_repos]):
        data = extract_github("jluckmay")
        assert data.get("email") == "lucas@dcc.ufmg.br"


def test_header_renders_imported_email_across_all_templates():
    """Valida se o email importado é incluído na lista de contatos do cabeçalho em todos os templates."""
    cv = {
        "name": "João Lucas Mayrinck",
        "title": "Especialista em Tecnologia & Desenvolvimento",
        "location": "Belo Horizonte, MG",
        "email": "lucas.mayrinck@dcc.ufmg.br",
        "phone": "+55 31 99999-9999",
        "summary": "Resumo profissional de teste.",
        "education": [{"degree": "Ciência da Computação", "institution": "UFMG", "period": "2026 - Atual"}],
        "experience": [{"role": "Monitor", "organization": "UFV", "period": "2025", "bullets": ["Orientou estudantes no laboratório."]}],
        "projects": [{"name": "MineMan", "tech": "Python", "description": "Jogo de exploração"}],
        "skills": [{"category": "Linguagens", "skills": ["Python"]}],
        "languages": ["Português (Nativo)"],
        "awards": ["Menção Honrosa - SBIE 2024"],
        "publications": [],
    }
    links = {
        "portfolio": "https://jluckmay.github.io",
        "github": "https://github.com/jluckmay",
        "email": "lucas.mayrinck@dcc.ufmg.br",
    }

    for template_id in BUILTIN_TEMPLATES.keys():
        tex = render_builtin_template(template_id, cv, links, resume_type="profissional", lang="pt-br")
        assert "lucas.mayrinck@dcc.ufmg.br" in tex, f"Template {template_id} deve renderizar o email no cabeçalho"
        assert "mailto:lucas.mayrinck@dcc.ufmg.br" in tex, f"Template {template_id} deve incluir link mailto"


def test_pipeline_populates_email_from_portfolio_without_manual_step4(tmp_path):
    """Valida se build_resume_pipeline importa o email da página de portfólio mesmo quando user_email não é fornecido."""
    mock_port = {
        "url": "https://jluckmay.github.io",
        "email": "lucas.mayrinck@dcc.ufmg.br",
        "educations": [],
        "employments": [
            {
                "role": "Monitor de Jogos",
                "organization": "Universidade Federal de Viçosa",
                "period": "2025",
                "description": "Orientou estudantes e apoiou no desenvolvimento de jogos.",
            }
        ],
        "languages": [],
        "awards": [],
        "publications": [],
    }
    with patch("src.pipeline.extract_portfolio", return_value=mock_port), \
         patch("src.pipeline.extract_lattes", return_value={}), \
         patch("src.pipeline.extract_github", return_value={}), \
         patch("src.pipeline.extract_linkedin", return_value={}), \
         patch("src.pipeline.extract_scholar", return_value={}), \
         patch("src.pipeline.extract_orcid", return_value={}):

        res = build_resume_pipeline(
            portfolio_url="https://jluckmay.github.io",
            user_name="João Lucas Mayrinck",
            user_email="",  # Vazio no passo 4 manual!
            build_dir=tmp_path,
            use_ai=False,
        )

        assert "lucas.mayrinck@dcc.ufmg.br" in res.latex_code
        assert "mailto:lucas.mayrinck@dcc.ufmg.br" in res.latex_code
        # Experiência deve conter Orientação a estudantes
        assert "Orientação a estudantes" in res.latex_code
        assert "Orientou estudantes" not in res.latex_code
