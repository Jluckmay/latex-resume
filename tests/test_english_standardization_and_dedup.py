"""Testes de validação da desduplicação cross-lingual e padronização para inglês (en-US).

Garante:
1. Desduplicação de formações acadêmicas (Mestrado / Master's e Bacharelado / Bachelor's)
   mesmo quando importadas em idiomas e formatos distintos (Lattes, ORCID, Portfólio).
2. Remoção de duplicações em experiências profissionais e acadêmicas (Monitoria de Jogos,
   Bolsista GeoGebra FUNARBEN vs UFV, Comissão Eleitoral).
3. Padronização completa para o inglês (en-US) de:
   - Resumo do perfil (summary)
   - Títulos de cargos e formações
   - Bullet points e descrições
   - Premiações (Honorable Mention, Academic Integration Symposium)
4. Renderização de círculos preenchidos sólidos (\\faIcon[solid]{circle}) no Russell CV.
5. Limpeza de repetições de título no campo de veículo (venue) das publicações.
"""

from src.direct_builder import build_structured_cv_deterministically
from src.templates import (
    clean_publication_venue,
    deduplicate_and_sort_educations,
    deduplicate_and_sort_experiences,
    deduplicate_and_sort_publications,
    render_builtin_template,
)


def test_cross_lingual_education_deduplication():
    raw_profile = {
        "user_meta": {"name": "João Lucas Mayrinck"},
        "links": {},
        "lattes": {
            "educations": [
                {
                    "level": "Mestrado",
                    "course": "Ciência da Computação",
                    "institution": "Universidade Federal de Minas Gerais",
                    "start": "2026",
                    "end": "Atual",
                    "thesis_title": "Pesquisa em Redes Sem Fio e Sistemas Distribuídos",
                },
                {
                    "level": "Graduação",
                    "course": "Sistemas de Informação",
                    "institution": "Universidade Federal de Viçosa",
                    "start": "2019",
                    "end": "2025",
                    "thesis_title": "",
                },
            ]
        },
        "portfolio": {
            "educations": [
                {
                    "degree": "Master's Degree in Computer Science",
                    "institution": "Universidade Federal de Minas Gerais · DCC",
                    "period": "2026 - Present",
                    "details": "Universidade Federal de Minas Gerais · DCC",
                },
                {
                    "degree": "Bachelor's Degree in Information Systems",
                    "institution": "Federal University of Viçosa",
                    "period": "2019 - 2025",
                    "details": "Universidade Federal de Viçosa",
                },
            ]
        },
    }

    # Quando gerado em inglês
    cv_en = build_structured_cv_deterministically(raw_profile, lang="en-us")
    edus_en = cv_en["education"]

    # Deve haver exatamente 2 formações, não 4
    assert len(edus_en) == 2
    assert edus_en[0]["degree"] == "M.Sc. in Computer Science"
    assert "Federal University of Minas Gerais" in edus_en[0]["institution"]
    assert edus_en[0]["period"] == "2026 - Present"
    # Detalhes não devem repetir a instituição
    assert "Universidade Federal de Minas Gerais" not in edus_en[0].get("details", "")

    assert edus_en[1]["degree"] == "B.Sc. in Information Systems"
    assert "Federal University of Viçosa" in edus_en[1]["institution"]
    assert edus_en[1]["period"] == "2019 - 2025"
    assert "Universidade Federal de Viçosa" not in edus_en[1].get("details", "")

    # Quando gerado em português
    cv_pt = build_structured_cv_deterministically(raw_profile, lang="pt-br")
    edus_pt = cv_pt["education"]
    assert len(edus_pt) == 2
    assert "Mestrado" in edus_pt[0]["degree"]
    assert "Bacharelado" in edus_pt[1]["degree"]


def test_cross_lingual_experience_deduplication():
    raw_profile = {
        "user_meta": {"name": "João Lucas Mayrinck"},
        "links": {},
        "lattes": {
            "employments": [
                {
                    "institution": "Universidade Federal de Viçosa",
                    "role": "Monitor de Desenvolvimento de Jogos",
                    "start": "2025",
                    "end": "2025",
                    "description": "Orientação prática e acompanhamento técnico de estudantes na disciplina de desenvolvimento de jogos.",
                },
                {
                    "institution": "FUNARBEN",
                    "role": "Bolsista de Pesquisa",
                    "start": "2023",
                    "end": "2024",
                    "description": "Figuras dinâmicas no GeoGebra para o ensino de matemática na educação básica e apoio a atividades de extensão.",
                },
                {
                    "institution": "Universidade Federal de Minas Gerais",
                    "role": "Comissão Eleitoral",
                    "start": "2026",
                    "end": "2026",
                    "description": "Participação no processo eleitoral como membro discente da comissão eleitoral.",
                },
            ]
        },
        "portfolio": {
            "employments": [
                {
                    "role": "Introduction to Game Development Teaching Assistant",
                    "organization": "Federal University of Viçosa",
                    "period": "2025",
                    "description": "Hands-on student mentoring in digital game development and instructional lab sessions.",
                },
                {
                    "role": "Extension Project Fellow",
                    "organization": "Federal University of Viçosa",
                    "period": "2023 - 2024",
                    "description": "Development of interactive GeoGebra figures for basic mathematics instruction.",
                },
            ]
        },
    }

    cv = build_structured_cv_deterministically(raw_profile, lang="en-us")
    exps = cv["experience"]

    # Deve haver exatamente 3 experiências, sem duplicar Game TA nem GeoGebra Fellow
    assert len(exps) == 3

    roles = [e["role"] for e in exps]
    assert any("Electoral" in r for r in roles)
    assert any("Teaching Assistant" in r or "Game" in r for r in roles)
    assert any("Fellow" in r for r in roles)

    # Verifica se os bullets estão em inglês
    for exp in exps:
        for bullet in exp.get("bullets", []):
            assert "Orientação prática" not in bullet
            assert "Figuras dinâmicas" not in bullet
            assert "Participação no processo" not in bullet


def test_english_summary_and_awards_standardization():
    raw_profile = {
        "user_meta": {"name": "João Lucas Mayrinck"},
        "links": {},
        "lattes": {
            "summary": "Ensino de conceitos relacionados a história da computação e jogos digitais. Atuação em projetos de extensão universitária voltados para tecnologias educacionais.",
            "awards": [
                "Menção Honrosa · Pôster · Simpósio de Integração Acadêmica (SIA/UFV) (2024)",
                "Segundo Lugar · Ensino · Simpósio de Integração Acadêmica (SIA/UFV) (2023)",
            ],
        },
    }

    cv_en = build_structured_cv_deterministically(raw_profile, lang="en-us")

    # Resumo em inglês
    assert "Computer Science" in cv_en["summary"]
    assert "Ensino de conceitos" not in cv_en["summary"]

    # Premiações em inglês
    awards_en = cv_en["awards"]
    assert len(awards_en) == 2
    assert "Honorable Mention" in awards_en[0]
    assert "Academic Integration Symposium" in awards_en[0]
    assert "Menção Honrosa" not in awards_en[0]

    assert "Second Place" in awards_en[1]
    assert "Segundo Lugar" not in awards_en[1]


def test_russell_cv_language_circles_solid():
    cv = {
        "name": "João Lucas Mayrinck",
        "title": "Computer Scientist",
        "email": "test@domain.com",
        "phone": "+55 31 99999-9999",
        "location": "Belo Horizonte, MG",
        "summary": "Software engineer and researcher.",
        "education": [],
        "experience": [],
        "projects": [],
        "publications": [],
        "skills": [],
        "languages": ["Português (Nativo)", "Inglês (Intermediário)"],
        "awards": [],
    }
    links = {"github": "https://github.com/jluckmay"}

    tex = render_builtin_template("overleaf_russell_ti", cv, links, lang="en-us")
    assert r"\faIcon[solid]{circle}" in tex
    assert r"\faIcon{circle}" not in tex


def test_clean_publication_venue_removes_title_duplication():
    title = "Math-O-Ween: Uma Abordagem Lúdica para o Ensino de Operações Matemáticas"
    redundant_venue = (
        "Math-O-Ween: Uma Abordagem Lúdica para o Ensino de Operações Matemáticas. "
        "Revista Brasileira de Informática na Educação"
    )
    clean_v = clean_publication_venue(redundant_venue, title)
    assert clean_v == "Revista Brasileira de Informática na Educação"

    # Caso com hífen e ano
    redundant_venue_2 = "Math-O-Ween - Revista Brasileira de Informática na Educação, 2024"
    clean_v_2 = clean_publication_venue(redundant_venue_2, "Math-O-Ween")
    assert clean_v_2 == "Revista Brasileira de Informática na Educação, 2024"

