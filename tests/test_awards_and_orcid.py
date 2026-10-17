"""Testes de conformidade e blindagem para Prêmios, Títulos e Certificações.

Garante que:
1. Quando não forem encontrados prêmios, títulos ou certificações, a seção NÃO deve ser criada
   em nenhum dos 9 templates suportados.
2. O identificador ORCID NUNCA é exibido ou interpretado como prêmio/certificação.
3. Se o candidato possuir ORCID cadastrado nos links/contatos, ele é renderizado apenas no cabeçalho.
4. Prêmios legítimos reais continuam sendo renderizados com precisão.
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from src.templates import (
    BUILTIN_TEMPLATES,
    render_builtin_template,
    sanitize_awards,
)
from src.token_plugins import ShortKeySchemaPlugin
from src.llm_client import LLMResumeGenerator


SAMPLE_BASE_CV: Dict[str, Any] = {
    "name": "Lucas Silva",
    "title": "Engenheiro de Software & Pesquisador",
    "email": "lucas.silva@example.com",
    "phone": "+55 11 98888-7777",
    "location": "São Paulo, SP",
    "summary": "Profissional e pesquisador com experiência em sistemas de alta performance.",
    "education": [
        {
            "degree": "Bacharelado em Ciência da Computação",
            "institution": "Universidade de São Paulo",
            "period": "2018 - 2022",
            "details": "Foco em inteligência artificial e compiladores.",
        }
    ],
    "experience": [
        {
            "role": "Engenheiro de Software Sênior",
            "organization": "Tech Corp",
            "period": "2022 - Presente",
            "bullets": ["Desenvolvimento de arquiteturas distribuídas com alta disponibilidade."],
        }
    ],
    "projects": [
        {
            "name": "Open-Source Engine",
            "tech": "Python, Rust",
            "url": "https://github.com/example/engine",
            "description": "Motor de processamento de alto rendimento.",
        }
    ],
    "publications": [
        {
            "title": "Deep Learning Optimization in Edge Devices",
            "venue": "IEEE Transactions",
            "year": "2023",
            "authors": "Silva, L.; Santos, A.",
            "doi": "10.1109/EXAMPLE.2023.12345",
        }
    ],
    "skills": [
        {
            "category": "Linguagens",
            "items": "Python, C++, Rust, Go",
        }
    ],
    "languages": ["Português (Nativo)", "Inglês (Fluente)"],
    "awards": [],
}

SAMPLE_LINKS: Dict[str, str] = {
    "github": "https://github.com/lucassilva",
    "linkedin": "https://linkedin.com/in/lucassilva",
    "orcid": "https://orcid.org/0009-0002-7600-9784",
    "lattes": "http://lattes.cnpq.br/1234567890123456",
}

ALL_TEMPLATE_IDS = list(BUILTIN_TEMPLATES.keys())


def test_sanitize_awards_scrubs_orcid_and_profile_links():
    """Valida se a função sanitize_awards remove estritamente qualquer menção a ORCID, Lattes, links e placeholders."""
    # ORCID variações
    assert sanitize_awards(["ORCID: 0009-0002-7600-9784"]) == []
    assert sanitize_awards(["0009-0002-7600-9784"]) == []
    assert sanitize_awards(["https://orcid.org/0009-0002-7600-9784"]) == []
    assert sanitize_awards(["orcid: 0000-0001-2345-6789"]) == []
    assert sanitize_awards(["ORCID 0009-0002-7600-9784"]) == []

    # Links e IDs de perfil
    assert sanitize_awards(["http://lattes.cnpq.br/1234567890123456"]) == []
    assert sanitize_awards(["ID Lattes: 1234567890123456"]) == []
    assert sanitize_awards(["Lattes: http://lattes.cnpq.br/12345"]) == []
    assert sanitize_awards(["https://github.com/lucassilva"]) == []
    assert sanitize_awards(["https://linkedin.com/in/lucassilva"]) == []

    # Placeholders e valores vazios
    assert sanitize_awards(["None", "N/A", "nenhum", "sem prêmios", "sem certificações", "-", ""]) == []
    assert sanitize_awards(None) == []
    assert sanitize_awards([]) == []

    # Prêmios reais legítimos
    legitimate = [
        "1º Lugar no Hackathon Nacional de IA (2024)",
        "AWS Certified Solutions Architect Associate (2023)",
        "Prêmio Mérito Acadêmico - USP (2022)",
    ]
    assert sanitize_awards(legitimate) == legitimate

    # Lista mista com ORCID e prêmio real
    mixed = ["ORCID: 0009-0002-7600-9784", "1º Lugar no Hackathon Nacional de IA (2024)"]
    assert sanitize_awards(mixed) == ["1º Lugar no Hackathon Nacional de IA (2024)"]


@pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
def test_no_awards_section_created_when_awards_empty(template_id: str):
    """Quando não forem encontrados prêmios, a seção de prêmios/certificações não deve ser criada no template."""
    cv = dict(SAMPLE_BASE_CV)
    cv["awards"] = []

    latex = render_builtin_template(
        template_id=template_id,
        cv=cv,
        links=SAMPLE_LINKS,
        resume_type="academico",
        lang="pt-br",
    )

    # Nenhuma variação de cabeçalho de prêmios/certificações deve existir
    assert "Prêmios" not in latex
    assert "Certificações" not in latex
    assert "PRÊMIOS" not in latex
    assert "CERTIFICAÇÕES" not in latex
    assert "sec_awards" not in latex


@pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
def test_orcid_never_in_awards_section_even_if_passed_in_awards(template_id: str):
    """Se por alucinação ou input imperfeito o ORCID for passado em awards, ele deve ser expurgado e a seção omitida."""
    cv = dict(SAMPLE_BASE_CV)
    cv["awards"] = ["ORCID: 0009-0002-7600-9784"]

    latex = render_builtin_template(
        template_id=template_id,
        cv=cv,
        links=SAMPLE_LINKS,
        resume_type="academico",
        lang="pt-br",
    )

    # Não deve criar a seção de prêmios
    assert "Prêmios" not in latex
    assert "Certificações" not in latex
    assert "PRÊMIOS" not in latex
    assert "CERTIFICAÇÕES" not in latex

    # O texto "ORCID: 0009-0002-7600-9784" como item de lista \item NÃO deve constar no LaTeX
    assert r"\item ORCID" not in latex
    assert r"\item {ORCID" not in latex
    assert r"\item {\small ORCID" not in latex


@pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
def test_orcid_properly_rendered_in_header_contacts(template_id: str):
    """O ORCID deve aparecer normalmente como link de contato no cabeçalho quando fornecido em links."""
    cv = dict(SAMPLE_BASE_CV)
    cv["awards"] = []

    latex = render_builtin_template(
        template_id=template_id,
        cv=cv,
        links=SAMPLE_LINKS,
        resume_type="academico",
        lang="pt-br",
    )

    # O ORCID deve ser referenciado como link no cabeçalho
    has_orcid_header = (
        "orcid.org/0009-0002-7600-9784" in latex
        or "ORCID" in latex
        or "0009-0002-7600-9784" in latex
    )
    assert has_orcid_header, f"Template {template_id} não incluiu link ORCID no cabeçalho"


@pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
def test_genuine_awards_are_rendered_when_present(template_id: str):
    """Quando existirem prêmios legítimos reais, a seção correspondente deve ser criada com o item."""
    cv = dict(SAMPLE_BASE_CV)
    cv["awards"] = ["1º Lugar Hackathon Nacional 2024"]

    latex = render_builtin_template(
        template_id=template_id,
        cv=cv,
        links=SAMPLE_LINKS,
        resume_type="academico",
        lang="pt-br",
    )

    # Deve conter o prêmio legítimo
    assert "1º Lugar Hackathon Nacional 2024" in latex

    # E deve conter algum identificador de seção de prêmios
    has_award_header = (
        "Prêmios" in latex
        or "PRÊMIOS" in latex
        or "CERTIFICAÇÕES" in latex
        or "Certificações" in latex
        or "Awards" in latex
        or "AWARDS" in latex
    )
    assert has_award_header, f"Template {template_id} não renderizou seção de prêmios com item legítimo"


def test_short_key_schema_expand_scrubs_orcid():
    """Valida se o ShortKeySchemaPlugin.expand elimina ORCID de 'aw' automaticamente."""
    short_data = {
        "nm": "Lucas Silva",
        "aw": ["ORCID: 0009-0002-7600-9784"],
    }
    expanded = ShortKeySchemaPlugin.expand(short_data)
    assert expanded["awards"] == []

    short_data_legit = {
        "nm": "Lucas Silva",
        "aw": ["Prêmio Inovação 2024", "ORCID: 0009-0002-7600-9784"],
    }
    expanded_legit = ShortKeySchemaPlugin.expand(short_data_legit)
    assert expanded_legit["awards"] == ["Prêmio Inovação 2024"]


def test_apply_fallbacks_scrubs_orcid_from_awards():
    """Valida se _apply_fallbacks higieniza o campo awards contra ORCID e placeholders."""
    cv = {
        "awards": ["ORCID: 0009-0002-7600-9784", "None"],
    }
    raw_data: Dict[str, Any] = {
        "lattes": {"awards": []},
        "orcid": {"orcid_id": "0009-0002-7600-9784"},
    }
    LLMResumeGenerator._apply_fallbacks(cv, raw_data, "academico", "pt-br")
    assert cv["awards"] == []
