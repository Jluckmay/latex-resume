"""Pipeline completo de ponta a ponta: Extração (GitHub/ORCID/Lattes/LinkedIn/Portfólio) -> TOON/Caveman -> NVIDIA NIM -> Cores & PDF LaTeX."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .compiler import compile_latex_to_pdf, prepare_photo_for_latex, sanitize_custom_latex
from .config import DEFAULT_MODEL, OUTPUT_DIR
from .extractors import (
    extract_github,
    extract_lattes,
    extract_linkedin,
    extract_orcid,
    extract_portfolio,
)
from .nvidia_client import NvidiaResumeGenerator
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
    template_id: str = "modern_pro",
    custom_latex_template: str | None = None,
    primary_color: str = "#0F4C81",
    secondary_color: str = "#1E293B",
    user_name: str = "",
    user_role: str = "",
    user_email: str = "",
    user_phone: str = "",
    user_location: str = "",
    extra_notes: str = "",
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    use_cache: bool = True,
    output_stem: str = "curriculo_gerado",
    build_dir: Path | None = None,
    lang: str = "pt-br",
) -> ResumeGenerationResult:
    """Executa todo o fluxo de coleta, síntese IA com economia de tokens, customização de cores e compilação LaTeX."""
    if custom_latex_template:
        sanitize_custom_latex(custom_latex_template)

    target_dir = build_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extração automática das fontes informadas (incluindo página de Portfólio)
    gh_data = extract_github(github_input) if github_input else {}
    orcid_data = extract_orcid(orcid_input) if orcid_input else {}
    lattes_data = (
        extract_lattes(
            lattes_url=lattes_url,
            file_bytes=lattes_file_bytes,
            filename=lattes_filename,
            pasted_text=lattes_text,
        )
        if (lattes_url or lattes_file_bytes or lattes_text)
        else {}
    )
    li_data = (
        extract_linkedin(
            linkedin_url=linkedin_url,
            file_bytes=linkedin_pdf_bytes,
            pasted_text=linkedin_text,
        )
        if (linkedin_url or linkedin_pdf_bytes or linkedin_text)
        else {}
    )
    portfolio_data = extract_portfolio(portfolio_url) if portfolio_url else {}

    links = {
        "linkedin": linkedin_url.strip() if linkedin_url else "",
        "github": gh_data.get("url") or (github_input.strip() if github_input else ""),
        "orcid": orcid_data.get("url") or (orcid_input.strip() if orcid_input else ""),
        "lattes": lattes_data.get("url") or (lattes_url.strip() if lattes_url else ""),
        "portfolio": portfolio_data.get("url") or (portfolio_url.strip() if portfolio_url else ""),
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
    }

    # 2. Preparação de foto (se enviada)
    photo_filename = prepare_photo_for_latex(
        build_dir=target_dir,
        photo_bytes=photo_bytes,
        photo_path=photo_path,
        target_stem=f"{output_stem}_photo",
    )

    # 3. Geração do LaTeX via NVIDIA NIM + Plugins de Economia de Tokens
    generator = NvidiaResumeGenerator(api_key=api_key, model=model, use_cache=use_cache)
    latex_code, structured_cv, metrics = generator.generate_latex_resume(
        raw_profile_data=raw_profile_data,
        resume_type=resume_type,
        template_id=template_id,
        custom_latex_template=custom_latex_template,
        photo_filename=photo_filename,
        lang=lang,
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

    # 6. Auto-reparo cirúrgico (1 tentativa) caso template customizado tenha erro de sintaxe
    if not ok and custom_latex_template:
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
