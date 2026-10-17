#!/usr/bin/env python3
"""Script de geração direta e determinística de currículos LaTeX sem uso de IA (Zero-Token).

Coleta dados de múltiplas fontes (GitHub, ORCID, Lattes XML/PDF, LinkedIn, Portfólio)
e gera um currículo LaTeX profissional ou acadêmico 100% determinístico e compilável,
com custo zero de tokens e sem necessidade de chaves de API externas.

Opcionalmente, permite acionar uma revisão cirúrgica do código gerado por um modelo LLM
(--review-ai), economizando até 75% dos tokens em relação à síntese de texto não-estruturado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para importação de src
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.compiler import check_latex_compiler
from src.config import DEFAULT_MODEL, DEFAULT_PROVIDER, PROVIDERS_CONFIG
from src.i18n import normalize_lang
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gerador Direto de Currículos LaTeX (Zero-Token / Sem IA) / "
            "Deterministic Direct LaTeX Resume Generator."
        )
    )
    parser.add_argument(
        "--lang",
        choices=["pt-br", "en-us"],
        default="pt-br",
        help="Idioma do currículo / Output language: 'pt-br' or 'en-us' (default: pt-br).",
    )
    parser.add_argument(
        "--type",
        choices=["profissional", "academico", "professional", "academic"],
        default="profissional",
        help="Modalidade: 'profissional' ou 'academico' / Mode: 'professional' or 'academic'.",
    )
    parser.add_argument("--linkedin", default="", help="URL do perfil LinkedIn.")
    parser.add_argument("--linkedin-pdf", default="", help="Caminho para arquivo PDF exportado do LinkedIn.")
    parser.add_argument("--github", default="", help="Username ou URL de perfil do GitHub.")
    parser.add_argument("--orcid", default="", help="ID ou URL do ORCID (ex: 0000-0002-1825-0097).")
    parser.add_argument("--lattes", default="", help="URL do Currículo Lattes.")
    parser.add_argument("--lattes-file", default="", help="Caminho para XML, ZIP ou PDF do Lattes.")
    parser.add_argument("--portfolio", default="", help="URL da página de portfólio pessoal.")
    parser.add_argument("--photo", default="", help="Caminho para foto de perfil (PNG/JPG).")
    parser.add_argument(
        "--template",
        choices=list(BUILTIN_TEMPLATES.keys()),
        default="modern_pro",
        help="Modelo LaTeX integrado (default: modern_pro).",
    )
    parser.add_argument("--custom-tex", default="", help="Caminho para template .tex customizado.")
    parser.add_argument("--primary-color", default="#18181B", help="Cor primária HEX (ex: #18181B).")
    parser.add_argument("--secondary-color", default="#3F3F46", help="Cor secundária HEX (ex: #3F3F46).")
    parser.add_argument("--name", default="", help="Nome completo do candidato.")
    parser.add_argument("--role", default="", help="Cargo ou título profissional.")
    parser.add_argument("--email", default="", help="E-mail de contato.")
    parser.add_argument("--phone", default="", help="Telefone.")
    parser.add_argument("--location", default="", help="Localização (Cidade/UF/País).")
    parser.add_argument("--extra", default="", help="Notas ou objetivos profissionais complementares.")
    parser.add_argument("--output", default="curriculo_direto", help="Nome do arquivo de saída (sem extensão).")
    parser.add_argument(
        "--review-ai",
        action="store_true",
        help="Aciona revisão cirúrgica opcional com modelo LLM para aprimorar o código gerado economizando tokens.",
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS_CONFIG.keys()),
        default="default",
        help="Provedor de IA para revisão (caso --review-ai seja informado).",
    )
    parser.add_argument("--model", default="", help="Modelo de IA para revisão.")
    parser.add_argument("--api-key", default="", help="Chave de API do provedor (opcional).")
    parser.add_argument("--check-deps", action="store_true", help="Verifica a instalação do pdflatex.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lang = normalize_lang(args.lang)
    is_en = lang == "en-us"

    if args.check_deps:
        ok, info = check_latex_compiler()
        if ok:
            print(f"[OK] Compilador LaTeX (pdflatex): {info}")
            return 0
        print(f"[ERROR] {info}", file=sys.stderr)
        return 1

    norm_type = "academico" if args.type in ("academico", "academic") else "profissional"

    # Leitura de arquivos locais se fornecidos
    lattes_bytes = None
    lattes_fname = ""
    if args.lattes_file:
        lp = Path(args.lattes_file)
        if lp.is_file():
            lattes_bytes = lp.read_bytes()
            lattes_fname = lp.name
        else:
            print(f"[AVISO] Arquivo Lattes não encontrado: {args.lattes_file}", file=sys.stderr)

    li_bytes = None
    if args.linkedin_pdf:
        lip = Path(args.linkedin_pdf)
        if lip.is_file():
            li_bytes = lip.read_bytes()
        else:
            print(f"[AVISO] PDF do LinkedIn não encontrado: {args.linkedin_pdf}", file=sys.stderr)

    custom_tex_content = None
    if args.custom_tex:
        ctp = Path(args.custom_tex)
        if ctp.is_file():
            custom_tex_content = ctp.read_text(encoding="utf-8", errors="replace")
        else:
            print(f"[AVISO] Template customizado não encontrado: {args.custom_tex}", file=sys.stderr)

    print(
        "⚡ Iniciando geração de currículo via extratores (Modo Direto / Zero-Token)..."
        if not is_en
        else "⚡ Starting deterministic resume generation from extractors (Direct / Zero-Token mode)..."
    )

    use_ai = bool(args.review_ai)
    ai_mode = "review_only" if args.review_ai else "disabled"

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
        provider=args.provider if use_ai else "none",
        api_key=args.api_key.strip() or None,
        model=args.model,
        output_stem=args.output,
        lang=lang,
        use_ai=use_ai,
        ai_mode=ai_mode,
    )

    print("\n" + ("=== Relatório de Execução ===" if not is_en else "=== Execution Report ==="))
    print(json.dumps(result.token_metrics, ensure_ascii=False, indent=2))
    print(f"\n[OK] Código LaTeX salvo em: {result.tex_path}" if not is_en else f"\n[OK] LaTeX code saved to: {result.tex_path}")

    if result.success and result.pdf_path:
        print(f"[OK] PDF compilado com sucesso em: {result.pdf_path}" if not is_en else f"[OK] PDF compiled successfully at: {result.pdf_path}")
        return 0

    print(
        f"[ERRO] Falha ao compilar PDF: {result.compiler_message}" if not is_en else f"[ERROR] Failed to compile PDF: {result.compiler_message}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

