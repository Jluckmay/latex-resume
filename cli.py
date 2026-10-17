"""Interface de Linha de Comando (CLI) Bilíngue (pt-BR / en-US) para o Gerador de Currículos LaTeX."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.compiler import check_latex_compiler
from src.config import DEFAULT_MODEL, DEFAULT_PROVIDER, PROVIDERS_CONFIG
from src.i18n import MODELS_I18N, TEMPLATES_I18N, normalize_lang
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gerador Automático de Currículos LaTeX (NVIDIA NIM / Gemini / Claude / OpenAI / DeepSeek) / "
            "Automatic LaTeX Resume Generator."
        )
    )
    parser.add_argument(
        "--lang",
        choices=["pt-br", "en-us"],
        default="pt-br",
        help="Idioma da interface e do currículo gerado / Output & CLI language: 'pt-br' or 'en-us' (default: pt-br).",
    )
    parser.add_argument(
        "--type",
        choices=["profissional", "academico", "professional", "academic"],
        default="profissional",
        help="Modalidade / Mode: 'profissional'/'professional' or 'academico'/'academic'.",
    )
    parser.add_argument("--linkedin", default="", help="URL do perfil LinkedIn / LinkedIn profile URL.")
    parser.add_argument("--linkedin-pdf", default="", help="Caminho para PDF do LinkedIn / Path to LinkedIn PDF.")
    parser.add_argument("--github", default="", help="Username ou URL do GitHub / GitHub username or URL.")
    parser.add_argument("--orcid", default="", help="ID ou URL do ORCID / ORCID ID or URL (e.g. 0000-0002-1825-0097).")
    parser.add_argument("--lattes", default="", help="URL do Currículo Lattes / Lattes CV URL.")
    parser.add_argument("--lattes-file", default="", help="Caminho para XML/ZIP/PDF do Lattes / Path to Lattes XML/ZIP/PDF.")
    parser.add_argument("--portfolio", default="", help="URL da página de portfólio pessoal / Personal portfolio website URL.")
    parser.add_argument("--photo", default="", help="Caminho para foto de perfil (PNG/JPG) / Path to profile photo.")
    parser.add_argument(
        "--template",
        choices=list(BUILTIN_TEMPLATES.keys()),
        default="modern_pro",
        help="Modelo LaTeX integrado / Built-in LaTeX template.",
    )
    parser.add_argument(
        "--custom-tex",
        default="",
        help="Caminho para arquivo .tex customizado / Path to custom .tex template file.",
    )
    parser.add_argument("--primary-color", default="#0F4C81", help="Cor principal HEX / Primary HEX color (e.g. #047857).")
    parser.add_argument("--secondary-color", default="#1E293B", help="Cor secundária HEX / Secondary HEX color (e.g. #064E3B).")
    parser.add_argument("--name", default="", help="Nome completo / Full name.")
    parser.add_argument("--role", default="", help="Cargo ou título principal / Primary role or headline.")
    parser.add_argument("--email", default="", help="E-mail de contato / Contact e-mail.")
    parser.add_argument("--phone", default="", help="Telefone / Phone number.")
    parser.add_argument("--location", default="", help="Cidade/UF/País / City, State, Country.")
    parser.add_argument("--extra", default="", help="Informações complementares / Additional notes.")
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS_CONFIG.keys()),
        default=DEFAULT_PROVIDER,
        help="Provedor de IA / AI Provider: default (NVIDIA NIM padrão), nvidia, google (Gemini), claude, openai, deepseek.",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Modelo de IA (opcional — usa o padrão do provedor escolhido se omitido) / AI model name.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Chave de API do provedor (opcional — criptografada em memória, nunca armazenada em disco).",
    )
    parser.add_argument("--no-cache", action="store_true", help="Desativa o cache local / Disable local token cache.")
    parser.add_argument("--output", default="curriculo_gerado", help="Nome-base de saída / Output filename stem.")
    parser.add_argument("--list-providers", action="store_true", help="Lista provedores suportados / List supported AI providers.")
    parser.add_argument("--list-models", action="store_true", help="Lista modelos recomendados / List recommended models.")
    parser.add_argument("--list-templates", action="store_true", help="Lista templates integrados / List built-in templates.")
    parser.add_argument("--check-deps", action="store_true", help="Verifica compilador LaTeX (pdflatex) / Check LaTeX compiler requirement.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lang = normalize_lang(args.lang)
    is_en = lang == "en-us"

    if args.check_deps:
        ok, info = check_latex_compiler()
        if ok:
            print(f"[OK] LaTeX compiler (pdflatex): {info}" if is_en else f"[OK] Compilador LaTeX (pdflatex): {info}")
            return 0
        print(f"[ERROR] {info}", file=sys.stderr)
        return 1

    norm_type = "academico" if args.type in ("academico", "academic") else "profissional"

    if args.list_providers:
        header = "Supported AI Providers & Models:" if is_en else "Provedores de IA & Modelos Suportados:"
        print(header)
        for pid, pdata in PROVIDERS_CONFIG.items():
            p_name = pdata["name_en"] if is_en else pdata["name"]
            req_txt = ("Requires API Key" if is_en else "Requer chave de API própria") if pdata["requires_key"] else ("Server Default" if is_en else "Padrão do Servidor")
            print(f"\n  [{pid}] {p_name} ({req_txt}):")
            for m in pdata.get("models", []):
                print(f"    - {m['id']} ({m['name']})")
        return 0

    if args.list_models:
        header = f"Recommended Models for Provider '{args.provider}':" if is_en else f"Modelos recomendados para o provedor '{args.provider}':"
        print(header)
        prov_cfg = PROVIDERS_CONFIG.get(args.provider, PROVIDERS_CONFIG["default"])
        for m in prov_cfg.get("models", []):
            print(f"  - {m['id']} ({m['name']}): {m['description']}")
        return 0

    if args.list_templates:
        header = "Built-in LaTeX Resume Templates:" if is_en else "Modelos de currículo LaTeX integrados:"
        print(header)
        for tid, tdata in TEMPLATES_I18N[lang].items():
            rec = BUILTIN_TEMPLATES[tid]["recommended_for"]
            print(f"  - {tid}: {tdata['name']} [{rec}]")
        return 0

    custom_tex_content: str | None = None
    if args.custom_tex:
        custom_path = Path(args.custom_tex)
        if not custom_path.exists():
            msg = (
                f"Error: custom template file not found: {custom_path}"
                if is_en
                else f"Erro: arquivo de template customizado não encontrado: {custom_path}"
            )
            print(msg, file=sys.stderr)
            return 1
        custom_tex_content = custom_path.read_text(encoding="utf-8", errors="ignore")

    lattes_bytes: bytes | None = None
    lattes_fname = ""
    if args.lattes_file:
        lp = Path(args.lattes_file)
        if lp.exists():
            lattes_bytes = lp.read_bytes()
            lattes_fname = lp.name

    li_bytes: bytes | None = None
    if args.linkedin_pdf:
        lip = Path(args.linkedin_pdf)
        if lip.exists():
            li_bytes = lip.read_bytes()

    chosen_prov = args.provider.strip().lower()
    prov_data = PROVIDERS_CONFIG.get(chosen_prov, PROVIDERS_CONFIG["default"])
    chosen_model = args.model.strip() or prov_data.get("default_model") or DEFAULT_MODEL

    result = build_resume_pipeline(
        resume_type=norm_type,
        linkedin_url=args.linkedin,
        linkedin_pdf_bytes=li_bytes,
        github_input=args.github,
        orcid_input=args.orcid,
        lattes_url=args.lattes,
        lattes_file_bytes=lattes_bytes,
        lattes_filename=lattes_fname,
        portfolio_url=args.portfolio,
        photo_path=args.photo if args.photo else None,
        template_id=args.template,
        custom_latex_template=custom_tex_content,
        primary_color=args.primary_color,
        secondary_color=args.secondary_color,
        user_name=args.name,
        user_role=args.role,
        user_email=args.email,
        user_phone=args.phone,
        user_location=args.location,
        extra_notes=args.extra,
        provider=chosen_prov,
        api_key=args.api_key.strip() or None,
        model=chosen_model,
        use_cache=not args.no_cache,
        output_stem=args.output,
        lang=lang,
    )

    banner = (
        "=== Token Economy Report (NVIDIA NIM) ==="
        if is_en
        else "=== Relatório de Economia de Tokens (NVIDIA NIM) ==="
    )
    print(banner)
    print(json.dumps(result.token_metrics, ensure_ascii=False, indent=2))

    tex_msg = (
        f"\nLaTeX file saved to: {result.tex_path}"
        if is_en
        else f"\nArquivo LaTeX salvo em: {result.tex_path}"
    )
    print(tex_msg)

    if result.success and result.pdf_path:
        pdf_msg = (
            f"PDF file successfully compiled at: {result.pdf_path}"
            if is_en
            else f"Arquivo PDF compilado com sucesso em: {result.pdf_path}"
        )
        print(pdf_msg)
        return 0

    err_msg = (
        f"Failed to compile PDF: {result.compiler_message}"
        if is_en
        else f"Falha ao compilar PDF: {result.compiler_message}"
    )
    print(err_msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
