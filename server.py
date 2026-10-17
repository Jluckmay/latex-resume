"""Servidor Web (Flask / Gunicorn) para compilação remota de currículos LaTeX.

Implementa bloqueio estrito de conexões (aceitando exclusivamente solicitações
vindas de https://github.com/Jluckmay/latex-resume e https://jluckmay.github.io/),
verificação de Referer e cabeçalhos de atestação mútua, proteção contra DoS/Rate
Limiting e compilação em diretórios isolados.
"""

from __future__ import annotations

import base64
import os
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

from src.compiler import check_latex_compiler
from src.config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    PROJECT_ROOT,
    PROVIDERS_CONFIG,
    RECOMMENDED_MODELS,
)
from src.pipeline import build_resume_pipeline

app = Flask(__name__, static_folder=str(PROJECT_ROOT))
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # Limite máximo de 12 MB por requisição

# Origens e páginas autorizadas exclusivamente em produção:
# 1. GitHub Pages oficial do usuário: https://jluckmay.github.io/
# 2. Repositório oficial do GitHub: https://github.com/Jluckmay/latex-resume
PAGES_ORIGIN = "https://jluckmay.github.io"
PAGES_REFERER_PREFIX = "https://jluckmay.github.io"

GITHUB_ORIGIN = "https://github.com"
GITHUB_REPO_URL_LOWER = "https://github.com/jluckmay/latex-resume"

LOCAL_ORIGINS = {
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "null",  # Navegadores abrindo file:// localmente
}

ALLOW_LOCAL_DEV = os.environ.get("ALLOW_LOCAL_DEV", "0") == "1"

CLIENT_HEADER_NAME = "X-Resume-Client"
ALLOWED_CLIENT_HEADERS = {
    "jluckmay-github-pages-v1",
    "jluckmay-github-repo-v1",
    "jluckmay-latex-resume-v1",
}
BACKEND_ATTESTATION = "latex-resume-render-v1"

# Rate Limiter em memória por IP (máximo 15 gerações a cada 10 minutos)
_IP_REQUEST_TIMES: defaultdict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 600.0  # 10 minutos
_MAX_REQUESTS_PER_WINDOW = 15


def _is_rate_limited(ip: str) -> bool:
    """Verifica se o IP cliente ultrapassou a taxa máxima de requisições."""
    now = time.time()
    times = [t for t in _IP_REQUEST_TIMES[ip] if now - t < _RATE_LIMIT_WINDOW]
    if len(times) >= _MAX_REQUESTS_PER_WINDOW:
        _IP_REQUEST_TIMES[ip] = times
        return True
    times.append(now)
    _IP_REQUEST_TIMES[ip] = times
    return False


def _validate_origin_and_referer() -> tuple[bool, str]:
    """Valida se a solicitação vem exclusivamente das páginas autorizadas:
    - https://jluckmay.github.io/
    - https://github.com/Jluckmay/latex-resume
    (ou ambiente local quando em desenvolvimento / loopback).
    
    Retorna (True, origin_para_cors) se válida, ou (False, mensagem_de_erro) se rejeitada.
    """
    origin = request.headers.get("Origin", "").strip()
    referer = request.headers.get("Referer", "").strip()
    referer_lower = referer.lower()
    is_options = request.method == "OPTIONS"

    # Verificação de loopback / desenvolvimento local
    is_loopback = request.remote_addr in ("127.0.0.1", "::1", "localhost")
    if (ALLOW_LOCAL_DEV or is_loopback) and (origin in LOCAL_ORIGINS or not origin):
        return True, origin or "http://127.0.0.1:5000"

    # 1. Validação de solicitações vindas de https://jluckmay.github.io/
    if origin == PAGES_ORIGIN:
        if referer and not referer_lower.startswith(PAGES_REFERER_PREFIX.lower()):
            return False, "Referer não autorizado para a origem jluckmay.github.io"
        return True, PAGES_ORIGIN

    # 2. Validação de solicitações vindas de https://github.com/Jluckmay/latex-resume
    # Navegadores em páginas do GitHub utilizam Origin: https://github.com
    # e Referer iniciando com https://github.com/Jluckmay/latex-resume (ou jluckmay/latex-resume)
    if origin == GITHUB_ORIGIN:
        if is_options:
            if not referer or referer_lower.startswith(GITHUB_REPO_URL_LOWER) or referer_lower.startswith("https://github.com"):
                return True, GITHUB_ORIGIN
        if not referer_lower.startswith(GITHUB_REPO_URL_LOWER):
            return False, "Referer não autorizado: permitido exclusivamente https://github.com/Jluckmay/latex-resume"
        return True, GITHUB_ORIGIN

    # Caso a Origin seja diretamente a URL completa do repositório
    if origin.lower().startswith(GITHUB_REPO_URL_LOWER):
        return True, origin

    # 3. Solicitações diretas sem cabeçalho Origin (validando exclusivamente via Referer)
    if not origin:
        if referer_lower.startswith(PAGES_REFERER_PREFIX.lower()):
            return True, PAGES_ORIGIN
        if referer_lower.startswith(GITHUB_REPO_URL_LOWER):
            return True, GITHUB_ORIGIN

    return False, "Origem não autorizada: o backend aceita exclusivamente requisições de https://github.com/Jluckmay/latex-resume e https://jluckmay.github.io/"


@app.after_request
def add_security_and_cors_headers(response: Response) -> Response:
    """Aplica cabeçalhos estritos de segurança e CORS restrito exclusivamente à origem autorizada."""
    is_valid, origin = _validate_origin_and_referer()
    if is_valid:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Resume-Client, X-Client-Timestamp"
        response.headers["Access-Control-Expose-Headers"] = "X-Backend-Attestation"
        response.headers["Access-Control-Max-Age"] = "86400"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Backend-Attestation"] = BACKEND_ATTESTATION
    return response


@app.route("/healthz", methods=["GET"])
def health_check() -> Response:
    """Endpoint de health check do Render para monitorar a saúde do container Docker."""
    return jsonify({"status": "ok", "service": "latex-resume-backend"})


@app.route("/")
def serve_index() -> Response:
    """Serve a interface index.html se acessada localmente ou redireciona."""
    if not ALLOW_LOCAL_DEV and not (request.remote_addr in ("127.0.0.1", "::1")):
        return jsonify({
            "message": "LaTeX Resume Compiler API. Interfaces oficiais: https://github.com/Jluckmay/latex-resume e https://jluckmay.github.io/"
        })
    return send_file(PROJECT_ROOT / "index.html")


@app.route("/api/status", methods=["GET", "OPTIONS"])
def api_status() -> Response | tuple[Response, int]:
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    is_valid, err_msg = _validate_origin_and_referer()
    if not is_valid:
        return jsonify({"error": err_msg}), 403

    latex_ok, latex_ver = check_latex_compiler()
    return jsonify(
        {
            "status": "ok",
            "latex_ok": latex_ok,
            "latex_version": latex_ver,
            "providers": PROVIDERS_CONFIG,
            "models": RECOMMENDED_MODELS,
            "service": "latex-resume-backend",
        }
    )


@app.route("/api/generate", methods=["POST", "OPTIONS"])
def api_generate() -> Response | tuple[Response, int]:
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # Validação estrita de origem e referer (aceita exclusivamente https://github.com/Jluckmay/latex-resume e https://jluckmay.github.io/)
    is_valid, err_msg = _validate_origin_and_referer()
    if not is_valid:
        return jsonify({"error": f"Acesso negado: {err_msg}"}), 403

    # Proteção de taxa de requisições (Rate Limiting)
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if _is_rate_limited(client_ip):
        return jsonify({"error": "Limite de requisições excedido. Aguarde alguns minutos antes de tentar novamente."}), 429

    try:
        form = request.form
        files = request.files

        provider = form.get("provider", DEFAULT_PROVIDER).strip().lower()
        resume_type = form.get("resume_type", "profissional")
        template_id = form.get("template_id", "modern_pro")
        lang = form.get("lang", "pt-br")
        primary_color = form.get("primary_color", "#0F4C81")
        secondary_color = form.get("secondary_color", "#1E293B")

        prov_info = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["default"])
        model = form.get("model") or prov_info.get("default_model") or DEFAULT_MODEL

        custom_tex: str | None = None
        if "custom_tex_file" in files and files["custom_tex_file"].filename:
            custom_tex = files["custom_tex_file"].read().decode("utf-8", errors="ignore")
        elif form.get("custom_tex_code", "").strip():
            custom_tex = form.get("custom_tex_code", "").strip()

        photo_bytes = files["photo"].read() if ("photo" in files and files["photo"].filename) else None
        lattes_bytes = (
            files["lattes_file"].read()
            if ("lattes_file" in files and files["lattes_file"].filename)
            else None
        )
        lattes_fname = files["lattes_file"].filename if ("lattes_file" in files and files["lattes_file"].filename) else ""
        li_pdf_bytes = (
            files["linkedin_pdf"].read()
            if ("linkedin_pdf" in files and files["linkedin_pdf"].filename)
            else None
        )

        # Compilação em diretório temporário isolado por requisição (previne colisões concorrentes e vazamento em disco)
        with tempfile.TemporaryDirectory(prefix="cv_build_") as tmp_build_dir:
            build_path = Path(tmp_build_dir)
            result = build_resume_pipeline(
                resume_type=resume_type,
                linkedin_url=form.get("linkedin", ""),
                linkedin_pdf_bytes=li_pdf_bytes,
                github_input=form.get("github", ""),
                orcid_input=form.get("orcid", ""),
                lattes_url=form.get("lattes", ""),
                lattes_file_bytes=lattes_bytes,
                lattes_filename=lattes_fname,
                portfolio_url=form.get("portfolio", ""),
                photo_bytes=photo_bytes,
                template_id=template_id,
                custom_latex_template=custom_tex,
                primary_color=primary_color,
                secondary_color=secondary_color,
                user_name=form.get("name", ""),
                user_role=form.get("role", ""),
                user_email=form.get("email", ""),
                user_phone=form.get("phone", ""),
                user_location=form.get("location", ""),
                extra_notes=form.get("extra", ""),
                provider=provider,
                api_key=form.get("api_key", "").strip() or None,
                model=model,
                use_cache=True,
                output_stem=f"web_{lang}_{resume_type}_{template_id}",
                build_dir=build_path,
                lang=lang,
            )

            pdf_b64 = ""
            if result.success and result.pdf_path and result.pdf_path.exists():
                pdf_b64 = base64.b64encode(result.pdf_path.read_bytes()).decode("ascii")

            return jsonify(
                {
                    "success": result.success,
                    "compiler_message": result.compiler_message,
                    "latex_code": result.latex_code,
                    "pdf_base64": pdf_b64,
                    "token_metrics": result.token_metrics,
                    "structured_cv": result.structured_cv,
                }
            )
    except Exception as exc:
        return jsonify({"error": f"Falha no processamento: {type(exc).__name__}"}), 500


if __name__ == "__main__":
    # Permite desenvolvimento local quando executado diretamente
    os.environ["ALLOW_LOCAL_DEV"] = "1"
    ALLOW_LOCAL_DEV = True
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor Web iniciado em http://127.0.0.1:{port} (ALLOW_LOCAL_DEV=True)")
    app.run(host="0.0.0.0", port=port, debug=False)
