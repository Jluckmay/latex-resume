"""Testes de normalização e exibição de nicks e IDs para LinkedIn, Lattes, GitHub e ORCID."""

from src.extractors import (
    parse_github_input,
    parse_lattes_input,
    parse_linkedin_input,
    parse_orcid_input,
)
from src.templates import (
    BUILTIN_TEMPLATES,
    render_builtin_template,
    _get_platform_display,
    simplify_url_display,
)


def test_parse_linkedin_input():
    url, nick = parse_linkedin_input("https://www.linkedin.com/in/lucassilva/")
    assert url == "https://www.linkedin.com/in/lucassilva"
    assert nick == "lucassilva"

    url, nick = parse_linkedin_input("in/lucassilva")
    assert url == "https://www.linkedin.com/in/lucassilva"
    assert nick == "lucassilva"

    url, nick = parse_linkedin_input("@lucassilva")
    assert url == "https://www.linkedin.com/in/lucassilva"
    assert nick == "lucassilva"

    url, nick = parse_linkedin_input("lucassilva")
    assert url == "https://www.linkedin.com/in/lucassilva"
    assert nick == "lucassilva"


def test_parse_lattes_input():
    url, lid = parse_lattes_input("http://lattes.cnpq.br/1234567890123456")
    assert url == "http://lattes.cnpq.br/1234567890123456"
    assert lid == "1234567890123456"

    url, lid = parse_lattes_input("1234567890123456")
    assert url == "http://lattes.cnpq.br/1234567890123456"
    assert lid == "1234567890123456"

    url, lid = parse_lattes_input("http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K4791234T5")
    assert "buscatextual" in url
    assert lid == "K4791234T5"


def test_parse_github_input():
    url, nick = parse_github_input("https://github.com/torvalds")
    assert url == "https://github.com/torvalds"
    assert nick == "torvalds"

    url, nick = parse_github_input("torvalds")
    assert url == "https://github.com/torvalds"
    assert nick == "torvalds"


def test_parse_orcid_input():
    url, oid = parse_orcid_input("https://orcid.org/0000-0002-1825-0097")
    assert url == "https://orcid.org/0000-0002-1825-0097"
    assert oid == "0000-0002-1825-0097"

    url, oid = parse_orcid_input("0000-0002-1825-0097")
    assert url == "https://orcid.org/0000-0002-1825-0097"
    assert oid == "0000-0002-1825-0097"


def test_get_platform_display():
    links = {
        "github": "https://github.com/octocat",
        "github_nick": "octocat",
        "linkedin": "https://www.linkedin.com/in/my-profile",
        "linkedin_nick": "my-profile",
        "orcid": "https://orcid.org/0000-0002-1825-0097",
        "orcid_id": "0000-0002-1825-0097",
        "lattes": "http://lattes.cnpq.br/1234567890123456",
        "lattes_id": "1234567890123456",
    }
    assert _get_platform_display(links, "github") == "octocat"
    assert _get_platform_display(links, "linkedin") == "my-profile"
    assert _get_platform_display(links, "orcid") == "0000-0002-1825-0097"
    assert _get_platform_display(links, "lattes") == "1234567890123456"


def test_all_templates_render_nicks_and_ids():
    cv = {
        "name": "Maria Silva",
        "title": "Engenheira de Software & Pesquisadora",
        "summary": "Resumo profissional de teste para validação de templates.",
        "email": "maria@teste.com",
        "phone": "+55 11 99999-9999",
        "location": "São Paulo, SP",
        "experiences": [
            {
                "role": "Engenheira Sênior",
                "company": "Tech Corp",
                "period": "2022 - Atual",
                "description": "Desenvolvimento de sistemas distribuídos e modelos de ML.",
            }
        ],
        "education": [
            {
                "degree": "Mestrado em Computação",
                "institution": "USP",
                "year": "2020 - 2022",
            }
        ],
        "skills": ["Python", "LaTeX", "Docker", "Machine Learning"],
        "languages": ["Português (Nativo)", "Inglês (Fluente)"],
        "publications": [
            {
                "title": "Artigo Científico de Teste",
                "venue": "Revista Brasileira de Computação",
                "year": "2023",
                "doi": "10.1000/182",
            }
        ],
        "awards": ["Prêmio Melhor Artigo 2023"],
    }
    links = {
        "github": "https://github.com/mariadev",
        "github_nick": "mariadev",
        "linkedin": "https://www.linkedin.com/in/mariasilva",
        "linkedin_nick": "mariasilva",
        "orcid": "https://orcid.org/0000-0002-1825-0097",
        "orcid_id": "0000-0002-1825-0097",
        "lattes": "http://lattes.cnpq.br/1234567890123456",
        "lattes_id": "1234567890123456",
    }

    for tpl_id in BUILTIN_TEMPLATES:
        tex = render_builtin_template(
            template_id=tpl_id,
            cv=cv,
            links=links,
            resume_type="profissional",
            lang="pt-br",
        )
        assert isinstance(tex, str) and len(tex) > 200, f"Template {tpl_id} produced empty or short output"
        # Check nicks and IDs are present in the output
        assert "mariadev" in tex, f"mariadev nick not found in template {tpl_id}"
        assert "mariasilva" in tex, f"mariasilva nick not found in template {tpl_id}"
        assert "0000-0002-1825-0097" in tex, f"ORCID ID not found in template {tpl_id}"
        assert "1234567890123456" in tex, f"Lattes ID not found in template {tpl_id}"
        # Ensure fontawesome5 package is included in the preamble
        assert "\\usepackage{fontawesome5}" in tex, f"\\usepackage{{fontawesome5}} missing in template {tpl_id}"


def test_simplify_url_display():
    assert simplify_url_display("https://portfolio.dev") == "portfolio.dev"
    assert simplify_url_display("http://www.meusite.com.br/cv/") == "meusite.com.br/cv"
    assert simplify_url_display("https://jluck.github.io/") == "jluck.github.io"
    assert simplify_url_display("portfolio.dev") == "portfolio.dev"
    assert simplify_url_display("") == ""
    assert simplify_url_display(None) == ""


def test_location_maps_and_portfolio_between_location_and_linkedin():
    cv = {
        "name": "Carlos Dev",
        "title": "Arquiteto de Software",
        "summary": "Resumo de teste.",
        "email": "carlos@teste.com",
        "phone": "+55 31 99999-9999",
        "location": "Belo Horizonte, MG",
        "projects": [
            {
                "name": "Sistema Open Source",
                "description": "Plataforma de alta performance.",
                "url": "https://github.com/carlosdev/sistema",
            }
        ],
        "publications": [
            {
                "title": "Paper em IA",
                "venue": "IEEE",
                "year": "2024",
                "doi": "10.1109/TEST.2024.12345",
            }
        ],
    }
    links = {
        "portfolio": "https://www.carlosdev.io/portfolio/",
        "linkedin": "https://www.linkedin.com/in/carlosdev",
        "linkedin_nick": "carlosdev",
        "github": "https://github.com/carlosdev",
        "github_nick": "carlosdev",
        "orcid": "https://orcid.org/0000-0002-1825-0097",
        "orcid_id": "0000-0002-1825-0097",
        "lattes": "http://lattes.cnpq.br/1234567890123456",
        "lattes_id": "1234567890123456",
    }

    for tpl_id in BUILTIN_TEMPLATES:
        tex = render_builtin_template(
            template_id=tpl_id,
            cv=cv,
            links=links,
            resume_type="profissional",
            lang="pt-br",
        )
        # 1. Location must link to Google Maps
        assert "maps/search/?api=1" in tex or "maps.google.com" in tex, f"Google Maps link missing in {tpl_id}"
        assert "Belo+Horizonte" in tex or "Belo" in tex, f"Location query parameter missing in {tpl_id}"

        # 2. Portfolio must show simplified URL 'carlosdev.io/portfolio' and NOT generic 'Portfolio'
        assert "carlosdev.io/portfolio" in tex, f"Simplified portfolio URL missing in {tpl_id}"

        # 3. Portfolio must be positioned between location and linkedin
        loc_pos = tex.find("maps.search")
        if loc_pos == -1:
            loc_pos = tex.find("maps/search")
        port_pos = tex.find("carlosdev.io/portfolio")

        assert loc_pos != -1, f"Location link not found in {tpl_id}"
        assert port_pos != -1, f"Portfolio display not found in {tpl_id}"
        # Conforme especificação: o local deve ser o último item a ser exibido no cabeçalho
        assert port_pos < loc_pos, f"Portfolio should appear before location in {tpl_id} (port: {port_pos}, loc: {loc_pos})"

        # 4. Project and publication links must be clickable \href
        assert "\\href{https://github.com/carlosdev/sistema}" in tex, f"Clickable project link missing in {tpl_id}"
        # For publication, check DOI href
        assert "\\href{https://doi.org/10.1109/TEST.2024.12345}" in tex or "\\href{http://dx.doi.org/10.1109/TEST.2024.12345}" in tex, (
            f"Clickable publication DOI missing in {tpl_id}"
        )


