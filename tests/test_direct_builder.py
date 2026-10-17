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
