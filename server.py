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

from src.compiler import check_latex_compiler, secure_wipe_and_remove_dir
from src.config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    PROJECT_ROOT,
    PROVIDERS_CONFIG,
    RECOMMENDED_MODELS,
)
from src.pipeline import build_resume_pipeline
from src._vault import (
    decrypt_payload_envelope,
    encrypt_payload_envelope,
    scrub_sensitive_api_keys,
)

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


def _is_local_origin(origin: str) -> bool:
    """Verifica se a origem é um host local/loopback em qualquer porta (Live Server, Vite, etc.)."""
    if not origin or origin == "null":
        return True
    return (
        origin.startswith("http://127.0.0.1:")
        or origin.startswith("http://localhost:")
        or origin in LOCAL_ORIGINS
    )

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
    if (ALLOW_LOCAL_DEV or is_loopback) and _is_local_origin(origin):
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
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, X-Resume-Client, X-Client-Timestamp, X-Encrypted-Payload"
        )
        response.headers["Access-Control-Expose-Headers"] = "X-Backend-Attestation, X-Encrypted-Payload"
        response.headers["Access-Control-Max-Age"] = "86400"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Backend-Attestation"] = BACKEND_ATTESTATION
    return response


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def handle_api_errors(e):
    """Garante que endpoints de API sempre retornem JSON estruturado e higienizado, sem vazar segredos."""
    if request.path.startswith("/api/"):
        code = getattr(e, "code", 500)
        raw_desc = getattr(e, "description", str(e))
        clean_desc = scrub_sensitive_api_keys(raw_desc)
        if code == 500:
            clean_desc = "Erro interno no servidor de compilação segura."
        return jsonify({"error": clean_desc, "status": code}), code
    return e


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


@app.route("/favicon.ico")
def serve_favicon_ico() -> Response:
    """Serve o favicon.ico oficial do projeto para a guia do navegador."""
    ico_path = PROJECT_ROOT / "favicon.ico"
    if ico_path.exists():
        return send_file(ico_path, mimetype="image/x-icon", max_age=86400)
    return "", 404


@app.route("/favicon.svg")
def serve_favicon_svg() -> Response:
    """Serve o ícone vetorial SVG de alta definição."""
    svg_path = PROJECT_ROOT / "favicon.svg"
    if svg_path.exists():
        return send_file(svg_path, mimetype="image/svg+xml", max_age=86400)
    return "", 404


@app.route("/favicon.png")
@app.route("/favicon-32.png")
@app.route("/favicon-192.png")
@app.route("/apple-touch-icon.png")
def serve_favicon_png_variants() -> Response:
    """Serve as variantes de ícone PNG para dispositivos móveis e navegadores."""
    filename = Path(request.path).name
    img_path = PROJECT_ROOT / filename
    if img_path.exists():
        return send_file(img_path, mimetype="image/png", max_age=86400)
    return "", 404


@app.route("/assets/<path:filename>")
def serve_assets(filename: str) -> Response:
    """Serve arquivos da pasta de assets."""
    target = (PROJECT_ROOT / "assets" / filename).resolve()
    if target.exists() and str(target).startswith(str((PROJECT_ROOT / "assets").resolve())):
        return send_file(target, max_age=86400)
    return "", 404


@app.route("/api/status", methods=["GET", "POST", "OPTIONS"])
def api_status() -> Response | tuple[Response, int]:
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    is_valid, err_msg = _validate_origin_and_referer()
    if not is_valid:
        return jsonify({"error": err_msg}), 403

    latex_ok, latex_ver = check_latex_compiler()

    # Sanitização estrita: garante que nenhuma informação de ambiente ou chave conste em providers
    safe_providers: dict[str, Any] = {}
    for prov_id, prov_val in PROVIDERS_CONFIG.items():
        prov_dict = dict(prov_val)
        prov_dict.pop("env_vars", None)
        safe_providers[prov_id] = prov_dict

    status_data = {
        "status": "ok",
        "latex_ok": latex_ok,
        "latex_version": latex_ver,
        "providers": safe_providers,
        "models": RECOMMENDED_MODELS,
        "service": "latex-resume-backend",
        "encryption": "ENC_PAYLOAD_V1",
    }

    # Verifica se o cliente solicitou transporte criptografado no status
    wants_encrypted = (
        request.headers.get("X-Encrypted-Payload") == "1"
        or (request.is_json and (request.get_json(silent=True) or {}).get("enc_version") == "ENC_PAYLOAD_V1")
    )
    if wants_encrypted:
        enc_envelope = encrypt_payload_envelope(status_data, direction="resp")
        resp = jsonify(enc_envelope)
        resp.headers["X-Encrypted-Payload"] = "1"
        return resp

    return jsonify(status_data)


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

    is_encrypted_transport = False
    try:
        # Detecta se a requisição possui payload criptografado (ENC_PAYLOAD_V1)
        if request.is_json:
            req_json = request.get_json(silent=True) or {}
            if req_json.get("enc_version") == "ENC_PAYLOAD_V1":
                is_encrypted_transport = True
                payload_data = decrypt_payload_envelope(req_json, direction="req")
            else:
                payload_data = req_json
        else:
            payload_data = {}

        if is_encrypted_transport:
            provider = (payload_data.get("provider") or DEFAULT_PROVIDER).strip().lower()
            resume_type = payload_data.get("resume_type", "profissional")
            template_id = payload_data.get("template_id", "modern_pro")
            lang = payload_data.get("lang", "pt-br")
            primary_color = payload_data.get("primary_color", "#18181B")
            secondary_color = payload_data.get("secondary_color", "#3F3F46")

            prov_info = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["default"])
            model = payload_data.get("model") or prov_info.get("default_model") or DEFAULT_MODEL
            ai_mode = payload_data.get("ai_mode", "auto").strip().lower()
            use_ai_param = payload_data.get("use_ai")
            use_ai = (str(use_ai_param).lower() not in ("0", "false", "no")) if use_ai_param is not None else (provider != "none")

            # Arquivos decodificados do payload cifrado em memória RAM
            custom_tex: str | None = None
            if payload_data.get("custom_tex_file") and isinstance(payload_data["custom_tex_file"], dict):
                file_info = payload_data["custom_tex_file"]
                if file_info.get("data"):
                    custom_tex = base64.b64decode(file_info["data"]).decode("utf-8", errors="ignore")
            elif payload_data.get("custom_tex_code", "").strip():
                custom_tex = payload_data.get("custom_tex_code", "").strip()

            photo_bytes: bytes | None = None
            if payload_data.get("photo"):
                p_item = payload_data["photo"]
                raw_b64 = p_item.get("data") if isinstance(p_item, dict) else str(p_item)
                if raw_b64:
                    photo_bytes = base64.b64decode(raw_b64)

            lattes_bytes: bytes | None = None
            lattes_fname = ""
            if payload_data.get("lattes_file"):
                l_item = payload_data["lattes_file"]
                if isinstance(l_item, dict):
                    lattes_fname = l_item.get("filename", "")
                    if l_item.get("data"):
                        lattes_bytes = base64.b64decode(l_item["data"])
                elif isinstance(l_item, str) and l_item:
                    lattes_bytes = base64.b64decode(l_item)

            li_pdf_bytes: bytes | None = None
            if payload_data.get("linkedin_pdf"):
                lp_item = payload_data["linkedin_pdf"]
                lp_b64 = lp_item.get("data") if isinstance(lp_item, dict) else str(lp_item)
                if lp_b64:
                    li_pdf_bytes = base64.b64decode(lp_b64)

            req_linkedin = payload_data.get("linkedin", "")
            req_github = payload_data.get("github", "")
            req_orcid = payload_data.get("orcid", "")
            req_lattes = payload_data.get("lattes", "")
            req_portfolio = payload_data.get("portfolio", "")
            req_name = payload_data.get("name", "")
            req_role = payload_data.get("role", "")
            req_email = payload_data.get("email", "")
            req_phone = payload_data.get("phone", "")
            req_location = payload_data.get("location", "")
            req_extra = payload_data.get("extra", "")
            req_api_key = payload_data.get("api_key", "").strip() or None
        else:
            # Fallback para multipart/form-data legada (compatibilidade com CLI e testes)
            form = request.form
            files = request.files

            provider = form.get("provider", DEFAULT_PROVIDER).strip().lower()
            resume_type = form.get("resume_type", "profissional")
            template_id = form.get("template_id", "modern_pro")
            lang = form.get("lang", "pt-br")
            primary_color = form.get("primary_color", "#18181B")
            secondary_color = form.get("secondary_color", "#3F3F46")

            prov_info = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["default"])
            model = form.get("model") or prov_info.get("default_model") or DEFAULT_MODEL
            ai_mode = form.get("ai_mode", "auto").strip().lower()
            use_ai_param = form.get("use_ai")
            use_ai = (str(use_ai_param).lower() not in ("0", "false", "no")) if use_ai_param is not None else (provider != "none")

            custom_tex = None
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

            req_linkedin = form.get("linkedin", "")
            req_github = form.get("github", "")
            req_orcid = form.get("orcid", "")
            req_lattes = form.get("lattes", "")
            req_portfolio = form.get("portfolio", "")
            req_name = form.get("name", "")
            req_role = form.get("role", "")
            req_email = form.get("email", "")
            req_phone = form.get("phone", "")
            req_location = form.get("location", "")
            req_extra = form.get("extra", "")
            req_api_key = form.get("api_key", "").strip() or None

        # Compilação em diretório efêmero isolado por requisição com política estrita de Zero-Storage
        tmp_build_dir = tempfile.mkdtemp(prefix="cv_session_ephemeral_")
        build_path = Path(tmp_build_dir)
        try:
            result = build_resume_pipeline(
                resume_type=resume_type,
                linkedin_url=req_linkedin,
                linkedin_pdf_bytes=li_pdf_bytes,
                github_input=req_github,
                orcid_input=req_orcid,
                lattes_url=req_lattes,
                lattes_file_bytes=lattes_bytes,
                lattes_filename=lattes_fname,
                portfolio_url=req_portfolio,
                photo_bytes=photo_bytes,
                template_id=template_id,
                custom_latex_template=custom_tex,
                primary_color=primary_color,
                secondary_color=secondary_color,
                user_name=req_name,
                user_role=req_role,
                user_email=req_email,
                user_phone=req_phone,
                user_location=req_location,
                extra_notes=req_extra,
                provider=provider,
                api_key=req_api_key,
                model=model,
                use_cache=False,  # Zero-storage: documentos nunca gravados em disco de cache
                output_stem=f"web_{lang}_{resume_type}_{template_id}",
                build_dir=build_path,
                lang=lang,
                use_ai=use_ai,
                ai_mode=ai_mode,
            )

            pdf_b64 = ""
            if result.success and result.pdf_path and result.pdf_path.exists():
                pdf_bytes = result.pdf_path.read_bytes()
                pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

            resp_data = {
                "success": result.success,
                "compiler_message": result.compiler_message,
                "latex_code": result.latex_code,
                "pdf_base64": pdf_b64,
                "token_metrics": result.token_metrics,
                "structured_cv": result.structured_cv,
            }

            # Higienização de segurança zero-leak: redige qualquer padrão de chave ou segredo ativo em RAM
            active_secrets = [
                os.environ.get(k, "") for k in ("NVIDIA_API_KEY", "NVIDIA_VAULT_KEY") if os.environ.get(k)
            ]
            if req_api_key:
                active_secrets.append(req_api_key)
            cleaned_data = scrub_sensitive_api_keys(resp_data, extra_secrets=active_secrets)

            if is_encrypted_transport:
                enc_response = encrypt_payload_envelope(cleaned_data, direction="resp")
                resp = jsonify(enc_response)
                resp.headers["X-Encrypted-Payload"] = "1"
                return resp

            return jsonify(cleaned_data)
        finally:
            # Destruição segura e imediata: sobrescreve com zeros e remove todos os arquivos efêmeros
            secure_wipe_and_remove_dir(build_path)
    except Exception as exc:
        raw_msg = str(exc).strip()
        exc_msg = raw_msg if raw_msg else type(exc).__name__
        err_msg = scrub_sensitive_api_keys(f"Falha no processamento: {exc_msg}")
        if is_encrypted_transport:
            enc_err = encrypt_payload_envelope({"error": err_msg, "success": False}, direction="resp")
            return jsonify(enc_err), 500
        return jsonify({"error": err_msg}), 500


def main() -> None:
    """Ponto de entrada para execução local do servidor Flask backend."""
    global ALLOW_LOCAL_DEV
    os.environ["ALLOW_LOCAL_DEV"] = "1"
    ALLOW_LOCAL_DEV = True
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor Web iniciado em http://127.0.0.1:{port} (ALLOW_LOCAL_DEV=True)")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
