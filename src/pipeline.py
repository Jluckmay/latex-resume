"""Pipeline completo de ponta a ponta: Extração (GitHub/ORCID/Lattes/LinkedIn/Portfólio) -> TOON/Caveman -> NVIDIA NIM -> Cores & PDF LaTeX."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .compiler import compile_latex_to_pdf, prepare_photo_for_latex, sanitize_custom_latex
from .config import DEFAULT_MODEL, DEFAULT_PROVIDER, OUTPUT_DIR
from .direct_builder import generate_direct_latex_resume
from .extractors import (
    extract_github,
    extract_lattes,
    extract_linkedin,
    extract_orcid,
    extract_portfolio,
    parse_github_input,
    parse_lattes_input,
    parse_linkedin_input,
    parse_orcid_input,
)
from .llm_client import LLMResumeGenerator
from .token_plugins import TokenMetrics
from .ui_theme import apply_custom_colors_and_portfolio_to_latex


@dataclass
class ResumeGenerationResult:
    """Resultado consolidado da geração de currículo."""

    success: bool
    pdf_path: Path | None
    tex_path: Path
    latex_code: str
    structured_cv: Dict[str, Any]
    extracted_sources: Dict[str, Any]
    token_metrics: Dict[str, Any]
    compiler_message: str


def _is_pdf_blank_or_corrupted(pdf_path: Path | None) -> bool:
    """Verifica se o PDF gerado existe em disco mas está vazio ou contém página em branco (menos de 25 caracteres)."""
    if not pdf_path or not pdf_path.exists():
        return False
    try:
        if pdf_path.stat().st_size < 500:
            return True
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) == 0:
            return True
        total_text = ""
        for page in reader.pages:
            total_text += (page.extract_text() or "").strip()
        if len(total_text) < 25:
            return True
        return False
    except Exception:
        return False


def build_resume_pipeline(
    resume_type: str = "profissional",
    linkedin_url: str = "",
    linkedin_pdf_bytes: bytes | None = None,
    linkedin_text: str = "",
    github_input: str = "",
    orcid_input: str = "",
    lattes_url: str = "",
    lattes_file_bytes: bytes | None = None,
    lattes_filename: str = "",
    lattes_text: str = "",
    portfolio_url: str = "",
    photo_bytes: bytes | None = None,
    photo_path: str | None = None,
    template_id: str = "ai_ats_max",
    custom_latex_template: str | None = None,
    primary_color: str = "#18181B",
    secondary_color: str = "#3F3F46",
    user_name: str = "",
    user_role: str = "",
    user_email: str = "",
    user_phone: str = "",
    user_location: str = "",
    extra_notes: str = "",
    provider: str = DEFAULT_PROVIDER,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    use_cache: bool = False,
    output_stem: str = "curriculo_gerado",
    build_dir: Path | None = None,
    lang: str = "pt-br",
    use_ai: bool = True,
    ai_mode: str = "auto",
    data_source_mode: str = "import",
    manual_data: Dict[str, Any] | None = None,
) -> ResumeGenerationResult:
    """Executa todo o fluxo de coleta, síntese IA com economia de tokens, customização de cores e compilação LaTeX."""
    if custom_latex_template:
        sanitize_custom_latex(custom_latex_template)

    target_dir = build_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extração automática das fontes informadas (incluindo normalização de URLs, IDs e nicks)
    gh_url_norm, gh_nick = parse_github_input(github_input)
    orcid_url_norm, orcid_id = parse_orcid_input(orcid_input)
    lattes_url_norm, lattes_id = parse_lattes_input(lattes_url)
    li_url_norm, li_nick = parse_linkedin_input(linkedin_url)

    gh_data = extract_github(gh_url_norm or github_input, target_lang=lang) if github_input else {}
    orcid_data = extract_orcid(orcid_url_norm or orcid_input) if orcid_input else {}
    lattes_data = (
        extract_lattes(
            lattes_url=lattes_url_norm or lattes_url,
            file_bytes=lattes_file_bytes,
            filename=lattes_filename,
            pasted_text=lattes_text,
        )
        if (lattes_url or lattes_file_bytes or lattes_text)
        else {}
    )
    li_data = (
        extract_linkedin(
            linkedin_url=li_url_norm or linkedin_url,
            file_bytes=linkedin_pdf_bytes,
            pasted_text=linkedin_text,
        )
        if (linkedin_url or linkedin_pdf_bytes or linkedin_text)
        else {}
    )
    portfolio_data = extract_portfolio(portfolio_url) if portfolio_url else {}

    links = {
        "linkedin": li_data.get("url") or li_url_norm or (linkedin_url.strip() if linkedin_url else ""),
        "github": gh_data.get("url") or gh_url_norm or (github_input.strip() if github_input else ""),
        "orcid": orcid_data.get("url") or orcid_url_norm or (orcid_input.strip() if orcid_input else ""),
        "lattes": lattes_data.get("url") or lattes_url_norm or (lattes_url.strip() if lattes_url else ""),
        "portfolio": portfolio_data.get("url") or (portfolio_url.strip() if portfolio_url else ""),
        "github_nick": gh_data.get("username") or gh_nick,
        "linkedin_nick": li_data.get("linkedin_nick") or li_nick,
        "orcid_id": orcid_data.get("orcid_id") or orcid_id,
        "lattes_id": lattes_data.get("lattes_id") or lattes_id,
    }

    combined_extra = extra_notes.strip()
    if portfolio_data and not portfolio_data.get("error"):
        port_summary_parts = [
            f"PORTFOLIO_URL: {portfolio_data.get('url', '')}",
            f"TITLE: {portfolio_data.get('title', '')}",
            f"DESC: {portfolio_data.get('description', '')}",
            f"SECTIONS: {', '.join(portfolio_data.get('headings') or [])}",
            f"CONTENT: {portfolio_data.get('raw_text', '')[:1200]}",
        ]
        port_block = " | ".join(p for p in port_summary_parts if not p.endswith(": "))
        combined_extra = f"{combined_extra}\n{port_block}".strip()

    raw_profile_data: Dict[str, Any] = {
        "user_meta": {
            "name": user_name.strip(),
            "role": user_role.strip(),
            "email": user_email.strip(),
            "phone": user_phone.strip(),
            "location": user_location.strip(),
        },
        "links": links,
        "github": gh_data,
        "orcid": orcid_data,
        "lattes": lattes_data,
        "linkedin": li_data,
        "portfolio": portfolio_data,
        "extra_notes": combined_extra,
        "data_source_mode": data_source_mode,
        "manual_data": manual_data or {},
    }

    # 2. Preparação de foto (se enviada)
    photo_filename = prepare_photo_for_latex(
        build_dir=target_dir,
        photo_bytes=photo_bytes,
        photo_path=photo_path,
        target_stem=f"{output_stem}_photo",
    )

    # 3. Geração do LaTeX (Direta / Determinística 0-token ou via IA com economia de tokens)
    chosen_provider = (provider or DEFAULT_PROVIDER).strip().lower()
    is_offline = (chosen_provider == "none") or (not use_ai) or (ai_mode == "disabled")
    generator = None

    if is_offline:
        latex_code, structured_cv = generate_direct_latex_resume(
            raw_profile_data=raw_profile_data,
            resume_type=resume_type,
            template_id=template_id,
            custom_latex_template=custom_latex_template,
            photo_filename=photo_filename,
            lang=lang,
        )
        metrics = TokenMetrics(
            model_used="direct_extractor_engine",
            cache_hit=False,
            prompt_tokens_actual=0,
            completion_tokens_actual=0,
            reasoning_tokens_actual=0,
            total_tokens_actual=0,
            raw_input_tokens_est=0,
            compressed_input_tokens_est=0,
            estimated_tokens_saved=3800,
            active_plugins=["DirectExtractorEngine (0-token offline)"],
        )
    elif ai_mode == "review_only":
        base_latex, structured_cv = generate_direct_latex_resume(
            raw_profile_data=raw_profile_data,
            resume_type=resume_type,
            template_id=template_id,
            custom_latex_template=custom_latex_template,
            photo_filename=photo_filename,
            lang=lang,
        )
        generator = LLMResumeGenerator(provider=chosen_provider, api_key=api_key, model=model, use_cache=use_cache)
        try:
            latex_code, metrics = generator.review_and_enhance_latex(
                base_latex=base_latex,
                resume_type=resume_type,
                instructions=combined_extra,
                lang=lang,
            )
        except Exception as exc:
            latex_code = base_latex
            metrics = TokenMetrics(
                model_used=f"review_fallback ({type(exc).__name__})",
                cache_hit=False,
                prompt_tokens_actual=0,
                completion_tokens_actual=0,
                total_tokens_actual=0,
                raw_input_tokens_est=0,
                compressed_input_tokens_est=0,
                estimated_tokens_saved=3800,
                active_plugins=["ResilientReviewFallback (0-token deterministic fallback)"],
            )
    else:
        generator = LLMResumeGenerator(provider=chosen_provider, api_key=api_key, model=model, use_cache=use_cache)
        try:
            latex_code, structured_cv, metrics = generator.generate_latex_resume(
                raw_profile_data=raw_profile_data,
                resume_type=resume_type,
                template_id=template_id,
                custom_latex_template=custom_latex_template,
                photo_filename=photo_filename,
                lang=lang,
            )
        except Exception as exc:
            # Se for falta de chave própria para provedores que exigem chave (Google, Claude, OpenAI, DeepSeek), propaga o erro explicativo
            if chosen_provider in ("google", "claude", "openai", "deepseek") and not api_key:
                raise
            # Caso contrário (limite de taxa da API, instabilidade de rede ou falha transitória do modelo),
            # realiza fallback resiliente imediato para o gerador direto determinístico.
            # Garante que o usuário receba seu currículo compilado sem erros HTTP 500 mesmo em chamadas repetidas.
            latex_code, structured_cv = generate_direct_latex_resume(
                raw_profile_data=raw_profile_data,
                resume_type=resume_type,
                template_id=template_id,
                custom_latex_template=custom_latex_template,
                photo_filename=photo_filename,
                lang=lang,
            )
            metrics = TokenMetrics(
                model_used=f"resilient_fallback ({type(exc).__name__})",
                cache_hit=False,
                prompt_tokens_actual=0,
                completion_tokens_actual=0,
                reasoning_tokens_actual=0,
                total_tokens_actual=0,
                raw_input_tokens_est=0,
                compressed_input_tokens_est=0,
                estimated_tokens_saved=3800,
                active_plugins=["ResilientFallbackEngine (0-token deterministic fallback)"],
            )

    # 4. Aplica customização de cores do usuário e link clicável de Portfólio ao LaTeX
    latex_code = apply_custom_colors_and_portfolio_to_latex(
        latex_code=latex_code,
        primary_color=primary_color,
        secondary_color=secondary_color,
        portfolio_url=links.get("portfolio", ""),
        lang=lang,
    )

    # 5. Compilação em PDF via pdflatex
    ok, pdf_path, tex_path, comp_msg = compile_latex_to_pdf(
        latex_code=latex_code,
        output_stem=output_stem,
        build_dir=target_dir,
    )

    # 6. Auto-reparo cirúrgico (1 tentativa) caso ocorra erro de compilação em qualquer template
    if not ok and generator is not None:
        try:
            repaired_latex = generator.repair_latex_error(latex_code, comp_msg)
            repaired_latex = apply_custom_colors_and_portfolio_to_latex(
                latex_code=repaired_latex,
                primary_color=primary_color,
                secondary_color=secondary_color,
                portfolio_url=links.get("portfolio", ""),
                lang=lang,
            )
            ok2, pdf_path2, tex_path2, comp_msg2 = compile_latex_to_pdf(
                latex_code=repaired_latex,
                output_stem=output_stem,
                build_dir=target_dir,
            )
            if ok2:
                latex_code = repaired_latex
                ok, pdf_path, tex_path, comp_msg = ok2, pdf_path2, tex_path2, comp_msg2
        except Exception:
            pass

    # 7. Fallback resiliente absoluto contra paginas em branco ou falhas de compilacao:
    # Se a compilacao falhou ou se o PDF gerado e uma pagina em branco (<25 caracteres extraidos), compila o LaTeX deterministico
    is_blank_or_failed = (not ok) or (pdf_path and pdf_path.exists() and _is_pdf_blank_or_corrupted(pdf_path))
    if is_blank_or_failed:
        fallback_base, fb_cv = generate_direct_latex_resume(
            raw_profile_data=raw_profile_data,
            resume_type=resume_type,
            template_id=template_id,
            custom_latex_template=custom_latex_template,
            photo_filename=photo_filename,
            lang=lang,
        )
        safe_fallback_tex = apply_custom_colors_and_portfolio_to_latex(
            latex_code=fallback_base,
            primary_color=primary_color,
            secondary_color=secondary_color,
            portfolio_url=links.get("portfolio", ""),
            lang=lang,
        )
        fb_ok, fb_pdf_path, fb_tex_path, fb_comp_msg = compile_latex_to_pdf(
            latex_code=safe_fallback_tex,
            output_stem=output_stem,
            build_dir=target_dir,
        )
        if fb_ok and fb_pdf_path and fb_pdf_path.exists() and not _is_pdf_blank_or_corrupted(fb_pdf_path):
            latex_code = safe_fallback_tex
            structured_cv = fb_cv
            ok, pdf_path, tex_path, comp_msg = fb_ok, fb_pdf_path, fb_tex_path, "Compilado com sucesso via fallback deterministico resiliente."

    return ResumeGenerationResult(
        success=ok,
        pdf_path=pdf_path,
        tex_path=tex_path,
        latex_code=latex_code,
        structured_cv=structured_cv,
        extracted_sources=raw_profile_data,
        token_metrics=metrics.to_dict() if isinstance(metrics, TokenMetrics) else {},
        compiler_message=comp_msg,
    )
