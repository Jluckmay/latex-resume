"""Testes de normalização e exibição de nicks e IDs para LinkedIn, Lattes, GitHub e ORCID."""

import pytest
from src.extractors import (
    parse_github_input,
    parse_lattes_input,
    parse_linkedin_input,
    parse_orcid_input,
)
from src.templates import BUILTIN_TEMPLATES, render_builtin_template, _get_platform_display


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

