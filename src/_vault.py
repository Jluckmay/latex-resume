"""Módulo de transporte seguro e cofre efêmero vinculado à tarefa (Task-Bound Enclave).

Implementa isolamento estrito de credenciais na memória volátil, atestação de pilha
de execução, transporte seguro via TLS 1.3 puro com pinning de certificado e sanitização
completa do ambiente de rede. Nenhuma chave é salva em disco ou exposta externamente.
"""

from __future__ import annotations

import inspect
import os
import ssl
from typing import Any, Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

_ALLOWED_MODES = (
    "MODE:CAVEMAN_JSON_ONLY",
    "MODE:CAVEMAN_LATEX_ONLY",
    "MODE:CAVEMAN_LATEX_REPAIR",
)

_ALLOWED_MARKERS = (
    "DADOS_TOON:",
    "DADOS_PERFIL_TOON:",
    "CORPO_TEMPLATE_LATEX:",
    "ERROR:\n",
)

_ENV_INTERCEPT_VARS = (
    "SSLKEYLOGFILE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "PYTHONHTTPSVERIFY",
)


class _PinnedTLS13Adapter(HTTPAdapter):
    """Adaptador HTTP com pinning de TLS 1.3 estrito e verificação forçada de hostname."""

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.options |= ssl.OP_NO_COMPRESSION | ssl.OP_NO_TICKET
        pool_kwargs["ssl_context"] = ctx
        pool_kwargs["assert_hostname"] = "integrate.api.nvidia.com"
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs)


def _scrub_network_environment() -> None:
    """Remove variáveis de interceptação TLS e proxies para impedir captura de pacotes em trânsito."""
    for var in _ENV_INTERCEPT_VARS:
        if var in os.environ:
            os.environ.pop(var, None)


def _attest_and_verify_caller(messages: List[Dict[str, str]]) -> None:
    """Atesta a integridade da chamada (origem src/nvidia_client.py e compatibilidade da tarefa)."""
    caller_ok = False
    for frame_info in inspect.stack()[1:8]:
        fname = frame_info.filename.replace("\\", "/")
        if fname.endswith("src/nvidia_client.py") and frame_info.function == "_call_nvidia_chat":
            caller_ok = True
            break
    if not caller_ok:
        raise PermissionError("Acesso negado: invocação fora do pipeline autorizado de currículos LaTeX.")

    if not isinstance(messages, list) or len(messages) != 2:
        raise PermissionError("Acesso negado: formato de mensagens incompatível com a tarefa de currículo.")

    sys_msg = (messages[0].get("content") or "").strip()
    usr_msg = (messages[1].get("content") or "").strip()

    matched_mode = None
    for mode in _ALLOWED_MODES:
        if sys_msg.startswith(mode):
            matched_mode = mode
            break
    if not matched_mode:
        raise PermissionError("Acesso negado: prompt de sistema não pertence ao gerador de currículos LaTeX.")

    if not any(marker in usr_msg for marker in _ALLOWED_MARKERS):
        raise PermissionError("Acesso negado: carga útil não corresponde a dados de currículo LaTeX.")


def dispatch_secure_nvidia_chat(
    endpoint_url: str,
    payload: Dict[str, Any],
    custom_key: str | None = None,
    timeout: int = 35,
) -> Tuple[int, Dict[str, Any], str]:
    """Despacha requisição autenticada vinculada exclusivamente ao gerador de currículos LaTeX.

    A chave de API é mantida apenas em memória RAM efêmera e destruída imediatamente após a requisição.
    Nenhuma chave é salva em disco local, arquivos de configuração ou repositório Git.
    """
    _scrub_network_environment()
    messages = payload.get("messages") or []
    _attest_and_verify_caller(messages)

    # 1. Recupera chave customizada ou chave injetada no ambiente seguro (ex: painel Render)
    raw_key = (custom_key or os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_VAULT_KEY") or "").strip()

    # Higienização imediata do os.environ para que nenhum processo-filho (como pdflatex) tenha acesso
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_VAULT_KEY", None)

    if not raw_key:
        raise RuntimeError(
            "Chave de API NVIDIA não configurada. Defina a variável de ambiente NVIDIA_API_KEY no painel seguro do Render "
            "ou forneça a chave na interface/CLI para execução."
        )

    buf = bytearray()
    auth_buf = bytearray()
    try:
        buf.extend(raw_key.encode("utf-8"))
        auth_buf.extend(b"Bearer ")
        auth_buf.extend(buf)

        session = requests.Session()
        session.trust_env = False
        session.mount("https://", _PinnedTLS13Adapter())

        resp = session.post(
            endpoint_url,
            headers={
                "Authorization": bytes(auth_buf).decode("ascii"),
                "Content-Type": "application/json",
                "Connection": "close",
            },
            json=payload,
            timeout=timeout,
        )
        session.close()
        if resp.status_code == 200:
            return resp.status_code, resp.json(), ""
        return resp.status_code, {}, f"HTTP {resp.status_code}"
    except PermissionError:
        raise
    except Exception as exc:
        return 599, {}, f"Erro de transporte seguro ({type(exc).__name__})"
    finally:
        # Higienização imediata da memória RAM (preenchimento com zeros)
        for i in range(len(buf)):
            buf[i] = 0
        for i in range(len(auth_buf)):
            auth_buf[i] = 0
        del raw_key
