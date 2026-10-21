"""Testes automatizados do Construtor Direto Determinístico (Zero-Token / Sem IA) e Modo Revisão."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.direct_builder import (
    build_structured_cv_deterministically,
    generate_direct_latex_resume,
)
from src.extractors import extract_lattes
from src.llm_client import LLMResumeGenerator
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES


def test_build_structured_cv_deterministically_from_lattes():
    """Valida se os dados do XML do Lattes são mapeados perfeitamente para o structured_cv sem IA."""
    lattes_path = ROOT / "examples" / "sample_lattes.xml"
    raw_lattes = extract_lattes(file_bytes=lattes_path.read_bytes(), filename="sample_lattes.xml")

    raw_profile = {
        "user_meta": {},
        "links": {"lattes": raw_lattes.get("url", "")},
        "github": {},
        "orcid": {},
        "lattes": raw_lattes,
        "linkedin": {},
        "portfolio": {},
        "extra_notes": "",
    }

    cv = build_structured_cv_deterministically(raw_profile, resume_type="academico", lang="pt-br")

    assert cv["name"] == "Dra. Helena Costa"
    assert "Pesquisadora" in cv["title"]
    assert "Inteligência Artificial" in cv["summary"]

    # Validação de Formação Acadêmica
    assert len(cv["education"]) >= 2
    doutorado = cv["education"][0]
    assert "Doutorado" in doutorado["degree"]
    assert "USP" in doutorado["institution"] or "São Paulo" in doutorado["institution"]
    assert "2020" in doutorado["period"]

    # Validação de Publicações
    assert len(cv["publications"]) >= 1
    artigo = cv["publications"][0]
    assert "Token-Efficient Reasoning" in artigo["title"]
    assert "10.1000/jair.2025.001" in artigo["doi"]

    # Validação de Prêmios e Ausência de ORCID na Seção de Prêmios
    assert len(cv["awards"]) >= 1
    assert "Melhor Tese de Doutorado em IA" in cv["awards"][0]
    for award in cv["awards"]:
        assert "orcid" not in award.lower()


def test_generate_direct_latex_resume_all_templates():
    """Valida se todos os 9 templates integrados renderizam perfeitamente em modo determinístico direto."""
    mock_profile = {
        "user_meta": {
            "name": "Lucas Silva",
            "role": "Engenheiro de Software Sênior",
            "email": "lucas.silva@email.com",
            "phone": "+55 11 99999-8888",
            "location": "São Paulo, SP",
        },
        "links": {
            "github": "https://github.com/lucassilva",
            "linkedin": "https://linkedin.com/in/lucassilva",
        },
        "github": {
            "languages": ["Python", "Go", "TypeScript"],
            "repos": [
                {
                    "name": "microservices-platform",
                    "language": "Go",
                    "description": "Plataforma escalável de mensageria.",
                    "url": "https://github.com/lucassilva/microservices-platform",
                }
            ],
        },
        "orcid": {},
        "lattes": {},
        "linkedin": {
            "experiences": [
                {
                    "role": "Tech Lead",
                    "company": "Tech Corp",
                    "period": "2021 - Atual",
                    "description": "Liderança de equipe de engenharia distribuída.",
                }
            ],
            "skills": ["Docker", "Kubernetes", "AWS", "FastAPI"],
        },
        "portfolio": {},
        "extra_notes": "",
    }

    for tpl_id in BUILTIN_TEMPLATES:
        latex_code, cv = generate_direct_latex_resume(
            raw_profile_data=mock_profile,
            resume_type="profissional",
            template_id=tpl_id,
            lang="pt-br",
        )
        assert r"\begin{document}" in latex_code
        assert r"\end{document}" in latex_code
        assert "Lucas" in latex_code and "Silva" in latex_code
        assert cv["name"] == "Lucas Silva"
        assert len(cv["projects"]) >= 1


def test_pipeline_zero_token_direct_execution(tmp_path):
    """Garante que a pipeline executa com 0 tokens e modelo direct_extractor_engine quando provider='none'."""
    lattes_path = ROOT / "examples" / "sample_lattes.xml"

    result = build_resume_pipeline(
        resume_type="academico",
        lattes_file_bytes=lattes_path.read_bytes(),
        lattes_filename="sample_lattes.xml",
        template_id="academic_classic",
        provider="none",
        output_stem="test_direct_zero_token",
        build_dir=tmp_path,
        lang="pt-br",
    )

    assert result.success is True
    assert result.tex_path.exists()
    assert result.pdf_path is not None and result.pdf_path.exists()

    tm = result.token_metrics
    assert tm["model_used"] == "direct_extractor_engine"
    assert tm["total_tokens_actual"] == 0
    assert tm["prompt_tokens_actual"] == 0
    assert tm["completion_tokens_actual"] == 0
    assert tm["estimated_tokens_saved"] > 0
    assert "DirectExtractorEngine (0-token offline)" in tm["active_plugins"]


def test_pipeline_use_ai_false_flag(tmp_path):
    """Garante que a flag use_ai=False desabilita qualquer chamada de modelo independente do provedor configurado."""
    result = build_resume_pipeline(
        resume_type="profissional",
        user_name="Lucas Silva",
        user_role="Software Engineer",
        user_email="lucas@example.com",
        template_id="modern_pro",
        provider="nvidia",
        use_ai=False,
        output_stem="test_use_ai_false",
        build_dir=tmp_path,
        lang="en-us",
    )

    assert result.success is True
    assert result.token_metrics["total_tokens_actual"] == 0
    assert result.token_metrics["model_used"] == "direct_extractor_engine"


def test_review_and_enhance_latex_method():
    """Valida o método review_and_enhance_latex com mock de resposta do modelo."""
    generator = LLMResumeGenerator(provider="default")

    fake_reviewed_body = r"""\begin{document}
\section*{Summary}
Polished professional summary with powerful action verbs.
\end{document}"""

    with patch.object(
        generator,
        "_call_llm_chat",
        return_value=(
            fake_reviewed_body,
            {"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
            "nvidia/nemotron-3.5-super-vl-120b-a12b",
            False,
        ),
    ):
        base_latex = r"""\documentclass{article}
\begin{document}
\section*{Summary}
Original summary.
\end{document}"""

        reviewed_latex, metrics = generator.review_and_enhance_latex(
            base_latex=base_latex,
            resume_type="profissional",
            instructions="Enfatizar liderança técnica",
            lang="en-us",
        )

        assert "Polished professional summary" in reviewed_latex
        assert r"\documentclass{article}" in reviewed_latex
        assert metrics.total_tokens_actual == 450
        assert "LaTeXReviewEngine" in metrics.active_plugins


def test_server_offline_mode_zero_token_api(client):
    """Valida se o endpoint /api/generate executa com sucesso em modo offline determinístico (0 tokens)."""
    from server import encrypt_payload_envelope, decrypt_payload_envelope

    payload = {
        "name": "Mariana Souza",
        "role": "Engenheira de Dados",
        "email": "mariana@dados.dev",
        "location": "Rio de Janeiro, RJ",
        "provider": "none",
        "resume_type": "profissional",
        "template_id": "minimal_ats",
        "lang": "pt-br",
    }
    enc_req = encrypt_payload_envelope(payload, direction="req")

    res = client.post(
        "/api/generate",
        headers={
            "Origin": "https://jluckmay.github.io",
            "Referer": "https://jluckmay.github.io/latex-resume",
            "Content-Type": "application/json",
        },
        json=enc_req,
    )

    assert res.status_code == 200
    decrypted = decrypt_payload_envelope(res.get_json(), direction="resp")
    assert decrypted["success"] is True
    assert decrypted["token_metrics"]["total_tokens_actual"] == 0
    assert decrypted["token_metrics"]["model_used"] == "direct_extractor_engine"
    assert "Mariana Souza" in decrypted["latex_code"]


def test_extract_languages_from_cnpq_lattes_xml():
    """Valida se XML oficial do CNPq (usando atributo IDIOMA sem DESCRICAO-DO-IDIOMA) extrai idiomas corretamente."""
    from src.extractors import extract_lattes

    cnpq_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <CURRICULO-VITAE NUMERO-IDENTIFICADOR="1122334455667788">
        <DADOS-GERAIS NOME-COMPLETO="Dr. Carlos Drummond">
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO NOME-CURSO="Letras" NOME-INSTITUICAO="UFMG" ANO-DE-INICIO="2010" ANO-DE-CONCLUSAO="2014" />
            </FORMACAO-ACADEMICA-TITULACAO>
            <IDIOMAS>
                <IDIOMA IDIOMA="Ingles" PROFICIENCIA-DE-LEITURA="BOM" PROFICIENCIA-DE-FALA="BOM" PROFICIENCIA-DE-ESCRITA="BOM" PROFICIENCIA-DE-COMPREENSAO="BOM"/>
                <IDIOMA IDIOMA="Espanhol" PROFICIENCIA-DE-LEITURA="RAZOAVEL" PROFICIENCIA-DE-FALA="POUCO"/>
                <IDIOMA IDIOMA="Outro" DESCRICAO-DO-IDIOMA="Mandarim" PROFICIENCIA-DE-LEITURA="BOM"/>
                <IDIOMA IDIOMA="Alemao"/>
            </IDIOMAS>
        </DADOS-GERAIS>
    </CURRICULO-VITAE>
    """
    res = extract_lattes(file_bytes=cnpq_xml, filename="lattes.xml")
    langs = res.get("languages") or []

    assert any("Inglês" in l and "Avançado" in l for l in langs)
    assert any("Espanhol" in l for l in langs)
    assert any("Mandarim" in l for l in langs)
    assert any("Alemão" in l for l in langs)


def test_extract_languages_from_text_sources():
    """Valida extração de idiomas a partir de texto bruto do LinkedIn e anotações livres."""
    from src.extractors import extract_languages_from_text, extract_linkedin

    linkedin_text = """
    Experiência Profissional
    Desenvolvedor Sênior na GlobalTech
    Idiomas
    Inglês (Fluente ou nativo)
    Francês (Intermediário)
    Competências
    Python, Docker, AWS
    """
    res_li = extract_linkedin(pasted_text=linkedin_text)
    assert any("Inglês" in l for l in res_li["languages"])
    assert any("Francês" in l for l in res_li["languages"])

    notes = "Candidato com 6 anos de mercado. Idiomas: Italiano (Fluente), Alemão (Básico)."
    langs_notes = extract_languages_from_text(notes)
    assert any("Italiano" in l for l in langs_notes)
    assert any("Alemão" in l for l in langs_notes)


def test_build_structured_cv_languages_translation_en():
    """Valida se idiomas em português são automaticamente traduzidos para o currículo em inglês."""
    raw_profile = {
        "user_meta": {"name": "Lucas Silva", "role": "Software Architect"},
        "lattes": {"languages": ["Inglês (Avançado)", "Português (Nativo)", "Espanhol (Intermediário)"]},
        "linkedin": {},
        "github": {},
        "orcid": {},
        "extra_notes": "",
    }
    cv_en = build_structured_cv_deterministically(raw_profile, resume_type="profissional", lang="en-us")
    langs = cv_en["languages"]

    assert any("English" in l and "Advanced" in l for l in langs)
    assert any("Portuguese" in l and "Native" in l for l in langs)
    assert any("Spanish" in l and "Intermediate" in l for l in langs)


def test_llm_apply_fallbacks_preserves_languages():
    """Valida se o fallback do LLM recupera os idiomas coletados caso o modelo os omita no JSON."""
    raw_profile = {
        "user_meta": {"name": "Julia Roberts"},
        "lattes": {"languages": ["Inglês (Fluente)", "Espanhol (Básico)"]},
        "linkedin": {},
        "github": {},
        "orcid": {},
    }
    generator = LLMResumeGenerator()
    cv_empty_langs = {"name": "Julia Roberts", "languages": []}
    generator._apply_fallbacks(cv_empty_langs, raw_profile, resume_type="profissional", lang="pt-br")

    assert len(cv_empty_langs["languages"]) == 2
    assert "Inglês (Fluente)" in cv_empty_langs["languages"]


def test_pipeline_resilient_fallback_on_api_limit(tmp_path):
    """Valida se o pipeline cai graciosamente para o gerador direto em caso de falha de API (evitando 500 em cliques repetidos)."""
    with patch.object(
        LLMResumeGenerator,
        "generate_latex_resume",
        side_effect=RuntimeError("HTTP 429 Too Many Requests (NVIDIA NIM Rate Limit)"),
    ):
        result = build_resume_pipeline(
            resume_type="profissional",
            user_name="Roberto Firmino",
            user_role="Tech Lead",
            provider="default",
            use_ai=True,
            ai_mode="auto",
            build_dir=tmp_path,
        )

        assert result.success is True
        assert "Roberto Firmino" in result.latex_code
        assert result.token_metrics["model_used"].startswith("resilient_fallback")
        assert "ResilientFallbackEngine" in result.token_metrics["active_plugins"][0]


def test_server_multiple_consecutive_generations_succeed(client):
    """Garante que requisições consecutivas a /api/generate funcionem perfeitamente sem erro 500."""
    from server import encrypt_payload_envelope, decrypt_payload_envelope

    payload1 = {
        "name": "Primeira Chamada",
        "role": "Engenheiro de Software",
        "provider": "none",
        "resume_type": "profissional",
        "template_id": "modern_pro",
        "lang": "pt-br",
    }
    enc1 = encrypt_payload_envelope(payload1, direction="req")
    res1 = client.post(
        "/api/generate",
        headers={
            "Origin": "https://jluckmay.github.io",
            "Referer": "https://jluckmay.github.io/latex-resume",
            "Content-Type": "application/json",
        },
        json=enc1,
    )
    assert res1.status_code == 200
    dec1 = decrypt_payload_envelope(res1.get_json(), direction="resp")
    assert dec1["success"] is True
    assert "Primeira Chamada" in dec1["latex_code"]

    payload2 = {
        "name": "Segunda Chamada Consecutiva",
        "role": "Tech Lead",
        "provider": "none",
        "resume_type": "profissional",
        "template_id": "minimal_ats",
        "lang": "pt-br",
    }
    enc2 = encrypt_payload_envelope(payload2, direction="req")
    res2 = client.post(
        "/api/generate",
        headers={
            "Origin": "https://jluckmay.github.io",
            "Referer": "https://jluckmay.github.io/latex-resume",
            "Content-Type": "application/json",
        },
        json=enc2,
    )
    assert res2.status_code == 200
    dec2 = decrypt_payload_envelope(res2.get_json(), direction="resp")
    assert dec2["success"] is True
    assert "Segunda Chamada Consecutiva" in dec2["latex_code"]


def test_orcid_education_and_experience_extraction_and_translation():
    """Valida se dados de educação e atuação do ORCID são extraídos com graus, instituições e tradução corretos."""
    from src.direct_builder import build_structured_cv_deterministically

    mock_orcid = {
        "name": "Mayrinck, J. L.",
        "educations": [
            {
                "role": "Master's Degree in Computer Science",
                "org": "Universidade Federal de Minas Gerais",
                "start": "2026",
                "end": "Atual",
            },
            {
                "role": "Bachelor's Degree in Information Systems",
                "org": "Universidade Federal de Viçosa",
                "start": "2019",
                "end": "2025",
            },
        ],
        "employments": [
            {
                "role": "Introduction to Game Development Teaching Assistant",
                "org": "Federal University of Viçosa",
                "start": "2025",
                "end": "2025",
            },
            {
                "role": "Extension Project Fellow",
                "org": "Federal University of Viçosa",
                "start": "2023",
                "end": "2024",
            },
        ],
    }

    # Teste em Português
    cv_pt = build_structured_cv_deterministically({"orcid": mock_orcid}, lang="pt-br")
    edus_pt = cv_pt.get("education", [])
    assert len(edus_pt) == 2
    assert edus_pt[0]["degree"] == "Mestrado em Ciência da Computação"
    assert edus_pt[0]["institution"] == "Universidade Federal de Minas Gerais"
    assert edus_pt[0]["period"] == "2026 - Atual"
    assert edus_pt[1]["degree"] == "Bacharelado em Sistemas de Informação"
    assert edus_pt[1]["institution"] == "Universidade Federal de Viçosa"

    exps_pt = cv_pt.get("experience", [])
    assert len(exps_pt) == 2
    assert exps_pt[0]["role"] == "Monitor de Introdução ao Desenvolvimento de Jogos"
    assert exps_pt[0]["organization"] == "Universidade Federal de Viçosa"
    assert exps_pt[1]["role"] == "Bolsista de Projeto de Extensão"
    assert exps_pt[1]["organization"] == "Universidade Federal de Viçosa"

    # Teste em Inglês
    cv_en = build_structured_cv_deterministically({"orcid": mock_orcid}, lang="en-us")
    edus_en = cv_en.get("education", [])
    assert len(edus_en) == 2
    assert "Computer Science" in edus_en[0]["degree"]
    assert edus_en[0]["institution"] == "Universidade Federal de Minas Gerais"
