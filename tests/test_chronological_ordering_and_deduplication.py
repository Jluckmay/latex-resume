"""Testes de ordenação cronológica reversa, padronização de datas/descrições e desduplicação rigorosa.

Valida:
1. Experiências ordenadas da mais recente à mais antiga (2026 - Atual, 2025, 2023 - 2024, etc.).
2. Normalização de datas (ex: '2025 - 2025' padronizado para '2025').
3. Desduplicação e mesclagem de experiências (ex: 'Monitor de Introdução ao Desenvolvimento de Jogos' e 'Monitor de Desenvolvimento de Jogos').
4. Padronização e enriquecimento de descrições e bullets.
5. Publicações ordenadas da mais recente à mais antiga (2026, 2025, 2024...), desduplicadas por DOI e título normalizado.
6. Premiações ordenadas da mais recente à mais antiga, desduplicadas e com exclusão de cards não-premiações.
"""

from src.direct_builder import build_structured_cv_deterministically
from src.templates import (
    deduplicate_and_sort_awards,
    deduplicate_and_sort_publications,
    normalize_period,
    render_builtin_template,
)


def test_normalize_period():
    assert normalize_period("2025 - 2025") == "2025"
    assert normalize_period("2025 – 2025") == "2025"
    assert normalize_period("2023 - 2024") == "2023 - 2024"
    assert normalize_period("2026 - Present", "pt-br") == "2026 - Atual"
    assert normalize_period("2026 - Atual", "en-us") == "2026 - Present"
    assert normalize_period("2025") == "2025"


def test_experiences_deduplicated_standardized_and_reverse_chronological():
    raw_profile = {
        "user_meta": {"name": "João Lucas Mayrinck"},
        "links": {},
        "orcid": {
            "employments": [
                {
                    "role": "Introduction to Game Development Teaching Assistant",
                    "start": "2025",
                    "end": "2025",
                    "organization": "Federal University of Viçosa",
                },
                {
                    "role": "Extension Project Fellow",
                    "start": "2023",
                    "end": "2024",
                    "organization": "Federal University of Viçosa",
                },
                {
                    "role": "Programming Teaching Assistant",
                    "start": "2021",
                    "end": "2022",
                    "organization": "Federal University of Viçosa",
                },
                {
                    "role": "Programming Tutor",
                    "start": "2019",
                    "end": "2020",
                    "organization": "Federal University of Viçosa",
                },
            ]
        },
        "portfolio": {
            "employments": [
                {
                    "role": "Monitor de Desenvolvimento de Jogos",
                    "organization": "Universidade Federal de Viçosa",
                    "period": "2025",
                    "description": "Orientou estudantes no desenvolvimento de jogos, revisou materiais didáticos e acompanhou o progresso acadêmico dos participantes.",
                },
                {
                    "role": "Bolsista de pesquisa",
                    "organization": "FUNARBEN",
                    "period": "2023 - 2024",
                    "description": "Desenvolveu figuras dinâmicas no GeoGebra para aprimorar o ensino de matemática em ambientes virtuais.",
                },
                {
                    "role": "Monitor de Programação",
                    "organization": "Universidade Federal de Viçosa",
                    "period": "2021 - 2022",
                    "description": "Acompanhamento de estudantes e apoio ao aprendizado de fundamentos de programação.",
                },
                {
                    "role": "Tutor de Programação",
                    "organization": "Universidade Federal de Viçosa",
                    "period": "2019 - 2020",
                    "description": "Atendimento, orientação prática e reforço de conceitos introdutórios.",
                },
                {
                    "role": "Comissão eleitoral",
                    "organization": "CAPosComp/UFMG",
                    "period": "2026",
                    "description": "Participação no processo de eleição da representação discente do Centro Acadêmico da Pós-Graduação em Ciência da Computação.",
                },
            ]
        },
    }

    cv = build_structured_cv_deterministically(raw_profile, resume_type="profissional")
    exps = cv["experience"]

    # 1. Total deve ser exatamente 5 experiências distintas (sem repetição de monitorias de jogos ou bolsas)
    assert len(exps) == 5

    # 2. Ordenadas da mais recente à mais antiga
    assert exps[0]["period"] == "2026"
    assert exps[0]["role"] == "Comissão eleitoral"

    assert exps[1]["period"] == "2025"  # Padronizado (não "2025 - 2025")
    assert "Jogos" in exps[1]["role"]
    assert len(exps[1]["bullets"]) >= 1
    assert "Orientou estudantes" in exps[1]["bullets"][0]

    assert exps[2]["period"] == "2023 - 2024"
    assert "Bolsista" in exps[2]["role"]
    assert len(exps[2]["bullets"]) >= 1
    assert "GeoGebra" in exps[2]["bullets"][0]

    assert exps[3]["period"] == "2021 - 2022"
    assert "Monitor de Programação" in exps[3]["role"]
    assert len(exps[3]["bullets"]) >= 1

    assert exps[4]["period"] == "2019 - 2020"
    assert "Tutor de Programação" in exps[4]["role"]
    assert len(exps[4]["bullets"]) >= 1


def test_publications_deduplication_and_reverse_chronological():
    pubs = [
        # Gamificação 1 (Lattes / DOI)
        {
            "title": "Gamificação no Ensino de Física: Projeto e Teste de Usabilidade de um Jogo de Física para Ensino Médio",
            "venue": "XVI Workshop de Sistemas de Informação – UFV Rio Paranaíba Campus",
            "year": "2025",
            "authors": "JL Mayrinck, F Bastos",
            "doi": "10.5753/wsis.2025.15027",
        },
        # Gamificação 2 (Google Scholar com hífen no título e autores completos)
        {
            "title": "Gamificação no Ensino de Física-Projeto e Teste de Usabilidade de um Jogo de Física para Ensino Médio",
            "venue": "Workshop de Sistemas de Informação (WSIS), 214-219, 2025",
            "year": "2025",
            "authors": "JVN Silva, F Bastos, JL Mayrinck, PM de Sousa",
            "doi": "",
        },
        # Gamificação 3 (Portfólio com mesmo DOI)
        {
            "title": "Gamificação no Ensino de Física: Projeto e Teste de Usabilidade de um Jogo de Física para Ensino Médio",
            "venue": "Usabilidade de um Jogo de Física para Ensino Médio XVI Workshop de Sistemas de Informação",
            "year": "2025",
            "authors": "",
            "doi": "10.5753/wsis.2025.15027",
        },
        # Artigo de 2026
        {
            "title": "Math-0-Ween: Um Jogo Digital Educacional para Explorar Operações Matemáticas de Forma Divertida e Assustadora",
            "venue": "Revista Brasileira de Informática na Educação",
            "year": "2026",
            "authors": "JL Mayrinck",
            "doi": "10.5753/rbie.2026.6599",
        },
        # Artigo de 2024
        {
            "title": "Palavras ao Ar: um jogo digital de descoberta de novas palavras e seus significados para auxiliar na alfabetização",
            "venue": "XXXV Simpósio Brasileiro de Informática na Educação",
            "year": "2024",
            "authors": "JL Mayrinck",
            "doi": "10.5753/sbie.2024.241887",
        },
    ]

    dedup = deduplicate_and_sort_publications(pubs)

    # 1. Deve haver apenas 3 artigos (as 3 versões de Gamificação fundiram-se em 1)
    assert len(dedup) == 3

    # 2. Ordem cronológica reversa estrita: 2026 -> 2025 -> 2024
    assert dedup[0]["year"] == "2026"
    assert "Math-0-Ween" in dedup[0]["title"]

    assert dedup[1]["year"] == "2025"
    assert "Gamificação" in dedup[1]["title"]
    # Retém tanto o DOI quanto a lista completa de autores
    assert dedup[1]["doi"] == "10.5753/wsis.2025.15027"
    assert "JVN Silva" in dedup[1]["authors"]

    assert dedup[2]["year"] == "2024"
    assert "Palavras ao Ar" in dedup[2]["title"]


def test_awards_deduplication_and_reverse_chronological():
    raw_awards = [
        "Menção Honrosa · Games · SBIE 2024: Palavras ao Ar ficou entre três melhores artigos da trilha de gamificação, jogos digitais, robótica e tecnologias imersivas.",
        "Menção Honrosa · Pôster · WSIS 2025: Explorando a Grécia Antiga: Um Jogo Digital Educativo foi selecionado entre os melhores trabalhos apresentados na categoria pôster do XVI Workshop de Sistemas de Informação.",
        "Segundo Lugar · Ensino · SIA 2023: Palavras ao Ar ganhou segundo lugar dentre os trabalhos apresentados na categoria ensino durante o XIV Simpósio de Integração Acadêmica da Universidade Federal de Viçosa — campus Rio Paranaíba.",
        "01 / DESTAQUE Palavras ao Ar Jogo digital educacional para descoberta de palavras e apoio à alfabetização. Menção honrosa no SBIE 2024. Ver publicação +",
        "Menção Honrosa · Games · SBIE 2024 Palavras ao Ar ficou entre três melhores artigos da trilha de gamificação, jogos digitais, robótica e tecnologias imersivas.",
        "Menção Honrosa · Pôster · WSIS 2025 Explorando a Grécia Antiga: Um Jogo Digital Educativo foi selecionado entre os melhores trabalhos apresentados na categoria pôster do XVI Workshop de Sistemas de Informação.",
        "Bolsa / Grant: Metodologia de ensino-aprendizagem baseada no uso interativo de figuras dinâmicas no ambiente virtual GeoGebra aplicada a estudantes da UFV - Campus Rio Paranaíba - Federal University of Viçosa (2023 - 2024).",
    ]

    dedup = deduplicate_and_sort_awards(raw_awards)

    # 1. Exatamente 4 prêmios válidos (excluídos cards de destaque e duplicatas pontuadas)
    assert len(dedup) == 4

    # 2. Ordem cronológica reversa: 2025 -> 2024 -> 2023
    assert "WSIS 2025" in dedup[0]
    assert "SBIE 2024" in dedup[1] or "2023 - 2024" in dedup[1]
    assert "SIA 2023" in dedup[3]


def test_template_rendering_respects_clean_ordering():
    cv = {
        "name": "João Lucas Mayrinck",
        "title": "Cientista da Computação",
        "experience": [
            {"role": "Monitor de Introdução ao Desenvolvimento de Jogos", "organization": "UFV", "period": "2025 - 2025", "bullets": []},
            {"role": "Monitor de Desenvolvimento de Jogos", "organization": "UFV", "period": "2025", "bullets": ["Apoio prático a alunos."]},
            {"role": "Tutor de Programação", "organization": "UFV", "period": "2019 - 2020", "bullets": ["Tutor introdutório."]},
        ],
        "education": [
            {"degree": "Mestrado", "institution": "UFMG", "period": "2026 - Atual"},
            {"degree": "Bacharelado", "institution": "UFV", "period": "2019 - 2025"},
        ],
        "publications": [
            {"title": "Artigo 2024", "year": "2024", "doi": "10.1111/2024"},
            {"title": "Artigo 2026", "year": "2026", "doi": "10.1111/2026"},
        ],
        "awards": [
            "Menção Honrosa 2023",
            "Menção Honrosa 2025",
        ],
    }

    links = {"linkedin": "https://linkedin.com/in/jluckmay"}
    latex = render_builtin_template("overleaf_russell_ti", cv, links, "profissional")

    # 1. Período "2025 - 2025" não deve estar presente no LaTeX gerado (padronizado para 2025)
    assert "2025 - 2025" not in latex
    assert "2025" in latex

    # 2. Experiência de 2025 deve aparecer antes da de 2019 - 2020
    pos_2025 = latex.find("2025")
    pos_2019 = latex.find("2019 - 2020")
    assert pos_2025 < pos_2019

    # 3. Publicação de 2026 deve aparecer antes da de 2024
    pos_pub_2026 = latex.find("Artigo 2026")
    pos_pub_2024 = latex.find("Artigo 2024")
    assert pos_pub_2026 < pos_pub_2024

    # 4. Premiação de 2025 deve aparecer antes da de 2023
    pos_aw_2025 = latex.find("Menção Honrosa 2025")
    pos_aw_2023 = latex.find("Menção Honrosa 2023")
    assert pos_aw_2025 < pos_aw_2023
