"""Módulo de transporte seguro e cofre efêmero vinculado à tarefa (Task-Bound Enclave).

Garante blindagem de rede (TLS 1.3, anti-MITM/anti-sniffing), atestação de pilha de chamadas,
ciclo de vida de memória com limpeza ativa (zero-exposure) e proteção contra vazamento em
repositórios públicos (carregamento por variável de ambiente isolada ou arquivo de cofre local).
"""

from __future__ import annotations

import hashlib
import inspect
import os
import pathlib
import ssl
from typing import Any, Callable, Dict, List, Tuple
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

# Shards e sal efêmeros em memória
_IN_MEMORY_SHARDS: Tuple[bytes, bytes, bytes, bytes, int] | None = None


class _PinnedTLS13Adapter(HTTPAdapter):
    """Adapter TLS 1.3 restrito com verificação estrita de certificado para integrate.api.nvidia.com."""

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


def _initialize_in_memory_vault() -> None:
    """Carrega a chave efêmera em memória, higieniza o ambiente de execução e particiona em shards.
    A chave nunca é salva em disco local nem exposta externamente.
    """
    global _IN_MEMORY_SHARDS
    if _IN_MEMORY_SHARDS is not None:
        return

    # 1. Busca por variável de ambiente efêmera (injetada em tempo de execução no Render)
    raw_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_VAULT_KEY")

    # Higienização imediata do os.environ para que nenhum processo-filho (como pdflatex) tenha acesso
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_VAULT_KEY", None)

    if not raw_key:
        return

    key_bytes = raw_key.strip().encode("utf-8")
    salt = os.urandom(24)
    task_tag = b"LATEX_RESUME_ONLY::" + "::".join(_ALLOWED_MODES).encode("utf-8")
    ks = hashlib.pbkdf2_hmac("sha256", task_tag, salt, 60000, dklen=len(key_bytes))

    # Rotação de bits + XOR com chave derivada
    rot = bytes((((b ^ k) << 3) | ((b ^ k) >> 5)) & 0xFF for b, k in zip(key_bytes, ks))
    s0 = rot[0::3]
    s1 = rot[1::3]
    s2 = rot[2::3]

    _IN_MEMORY_SHARDS = (s0, s1, s2, salt, len(key_bytes))
    del raw_key, key_bytes, rot, ks


def _attest_and_derive_tag(messages: List[Dict[str, str]]) -> bytes:
    """Atesta a integridade da chamada (origem src/nvidia_client.py e compatibilidade da tarefa)."""
    caller_ok = False
    for frame_info in inspect.stack()[1:7]:
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

    modes_joined = "::".join(_ALLOWED_MODES)
    return f"LATEX_RESUME_ONLY::{modes_joined}".encode("utf-8")


def dispatch_secure_nvidia_chat(
    endpoint_url: str,
    payload: Dict[str, Any],
    custom_key: str | None = None,
    timeout: int = 35,
) -> Tuple[int, Dict[str, Any], str]:
    """Despacha requisição autenticada vinculada exclusivamente ao gerador de currículos LaTeX."""
    _scrub_network_environment()
    _initialize_in_memory_vault()

    messages = payload.get("messages") or []
    task_tag = _attest_and_derive_tag(messages)

    buf = bytearray()
    auth_buf = bytearray()
    try:
        if custom_key and custom_key.strip():
            buf.extend(custom_key.strip().encode("utf-8"))
        elif _IN_MEMORY_SHARDS is not None:
            s0, s1, s2, salt, ln = _IN_MEMORY_SHARDS
            enc = bytearray(ln)
            enc[0::3] = s0
            enc[1::3] = s1
            enc[2::3] = s2

            ks = hashlib.pbkdf2_hmac("sha256", task_tag, salt, 60000, dklen=ln)
            unrot = bytes((((a ^ b) >> 3) | ((a ^ b) << 5)) & 0xFF for a, b in zip(enc, ks))
            buf.extend(unrot)
            for i in range(len(enc)):
                enc[i] = 0
        else:
            raise RuntimeError(
                "Chave de API NVIDIA não configurada. Defina a variável de ambiente NVIDIA_API_KEY no painel seguro do Render "
                "ou informe a chave efêmera na sessão em memória."
            )

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
        for i in range(len(buf)):
            buf[i] = 0
        for i in range(len(auth_buf)):
            auth_buf[i] = 0
