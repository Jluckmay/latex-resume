"""Testes automatizados da camada de comunicação criptografada (ENC_PAYLOAD_V1)
e blindagem contra extração de chaves via console, inspeção de rede ou probing de requisições.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest

from server import app
from src._vault import (
    derive_payload_transport_key,
    encrypt_payload_envelope,
    decrypt_payload_envelope,
    scrub_sensitive_api_keys,
    create_secure_envelope,
    unwrap_secure_api_key,
)
from src.config import PROVIDERS_CONFIG


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_payload_encryption_and_decryption_cycle():
    """Valida o ciclo completo de cifragem e decifragem bidirecional AES-256-GCM."""
    secret_payload = {
        "name": "Maria Silva",
        "email": "maria@exemplo.com",
        "role": "Engenheira de IA Sênior",
        "latex_code": r"\documentclass{article}\begin{document}Maria Silva\end{document}",
        "metrics": {"tokens_saved": 450},
    }

    # Cifra do cliente para o servidor (req)
    req_envelope = encrypt_payload_envelope(secret_payload, direction="req")
    assert req_envelope["enc_version"] == "ENC_PAYLOAD_V1"
    assert "iv" in req_envelope
    assert "ciphertext" in req_envelope
    assert "ts" in req_envelope
    # Verifica que o texto cifrado não contém strings em texto plano
    assert "Maria Silva" not in req_envelope["ciphertext"]
    assert "maria@exemplo.com" not in req_envelope["ciphertext"]

    # Decifra no servidor (req)
    decrypted_req = decrypt_payload_envelope(req_envelope, direction="req")
    assert decrypted_req == secret_payload

    # Cifra do servidor para o cliente (resp)
    resp_envelope = encrypt_payload_envelope(secret_payload, direction="resp")
    decrypted_resp = decrypt_payload_envelope(resp_envelope, direction="resp")
    assert decrypted_resp == secret_payload


def test_anti_replay_protection():
    """Valida rejeição de pacotes expirados ou com timestamp adulterado."""
    data = {"test": "data"}
    # Timestamp de 20 minutos atrás (acima dos 15 minutos permitidos)
    expired_ts = int((time.time() - 1200) * 1000)
    expired_envelope = encrypt_payload_envelope(data, direction="req", ts=expired_ts)

    with pytest.raises(ValueError, match="Payload criptografado expirado"):
        decrypt_payload_envelope(expired_envelope, direction="req")


def test_tamper_and_corruption_detection():
    """Valida detecção de adulteração de ciphertext ou IV (falha de autenticação AES-GCM)."""
    data = {"secret": "valuable_info"}
    envelope = encrypt_payload_envelope(data, direction="req")

    # Adultera o ciphertext
    corrupted_envelope = dict(envelope)
    ct_bytes = bytearray(base64.b64decode(corrupted_envelope["ciphertext"]))
    ct_bytes[0] ^= 0xFF  # Inverte bits
    corrupted_envelope["ciphertext"] = base64.b64encode(bytes(ct_bytes)).decode("ascii")

    with pytest.raises(Exception):
        decrypt_payload_envelope(corrupted_envelope, direction="req")


def test_api_status_zero_secrets_leakage(client):
    """Garante que /api/status nunca expõe variáveis de ambiente de chaves ou segredos."""
    res = client.get("/api/status", headers={"Origin": "https://jluckmay.github.io"})
    assert res.status_code == 200
    data = res.get_json()

    assert data["status"] == "ok"
    assert data["encryption"] == "ENC_PAYLOAD_V1"

    # Inspeciona profundamente o objeto retornado
    serialized = json.dumps(data)
    assert "NVIDIA_API_KEY" not in serialized
    assert "NVIDIA_VAULT_KEY" not in serialized
    assert "GEMINI_API_KEY" not in serialized
    assert "ANTHROPIC_API_KEY" not in serialized
    assert "OPENAI_API_KEY" not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "env_vars" not in serialized

    # Testa status com resposta cifrada solicitada
    res_enc = client.get(
        "/api/status",
        headers={"Origin": "https://jluckmay.github.io", "X-Encrypted-Payload": "1"},
    )
    assert res_enc.status_code == 200
    enc_data = res_enc.get_json()
    assert enc_data["enc_version"] == "ENC_PAYLOAD_V1"
    decrypted_status = decrypt_payload_envelope(enc_data, direction="resp")
    assert decrypted_status["status"] == "ok"
    assert "NVIDIA_API_KEY" not in json.dumps(decrypted_status)


def test_api_generate_end_to_end_encrypted_transport(client):
    """Simula requisição com transporte 100% criptografado (rede e DevTools veem apenas ciphertext)."""
    raw_cv_payload = {
        "name": "Carlos Alcantara",
        "role": "Arquiteto de Software",
        "email": "carlos@alcantara.dev",
        "location": "Belo Horizonte, MG",
        "provider": "default",
        "resume_type": "profissional",
        "template_id": "modern_pro",
        "lang": "pt-br",
        "extra": "Experiência sólida com microsserviços.",
    }

    # Cifra o payload no lado do cliente
    req_envelope = encrypt_payload_envelope(raw_cv_payload, direction="req")

    # Inspeciona o que trafega na rede
    wire_body = json.dumps(req_envelope)
    assert "Carlos Alcantara" not in wire_body
    assert "carlos@alcantara.dev" not in wire_body
    assert "Arquiteto de Software" not in wire_body

    # Mocka o pipeline para teste rápido de transporte
    fake_result = MagicMock()
    fake_result.success = True
    fake_result.pdf_path = None
    fake_result.compiler_message = "LaTeX compilado com sucesso."
    fake_result.latex_code = r"\documentclass{article}\begin{document}Carlos Alcantara\end{document}"
    fake_result.token_metrics = {"total_tokens": 120}
    fake_result.structured_cv = {"name": "Carlos Alcantara"}

    with patch("server.build_resume_pipeline", return_value=fake_result):
        res = client.post(
            "/api/generate",
            headers={
                "Origin": "https://jluckmay.github.io",
                "Referer": "https://jluckmay.github.io/latex-resume",
                "Content-Type": "application/json",
            },
            data=wire_body,
        )

        assert res.status_code == 200
        resp_json = res.get_json()

        # O corpo da resposta deve ser ESTRITAMENTE cifrado (DevTools / sniffer vê apenas ciphertext)
        assert resp_json.get("enc_version") == "ENC_PAYLOAD_V1"
        assert "Carlos Alcantara" not in json.dumps(resp_json)
        assert "documentclass" not in json.dumps(resp_json)

        # O cliente decifra em memória RAM volátil
        decrypted_resp = decrypt_payload_envelope(resp_json, direction="resp")
        assert decrypted_resp["success"] is True
        assert "Carlos Alcantara" in decrypted_resp["latex_code"]
        assert decrypted_resp["structured_cv"]["name"] == "Carlos Alcantara"


def test_scrub_sensitive_api_keys_defense():
    """Valida que o filtro de higienização redige qualquer chave de API conhecida ou segredo ativo."""
    fake_server_secret = "nvapi-REAL_SECRET_SERVER_KEY_ABC1234567890"

    contaminated_text = (
        f"Erro ao processar: a chave nvapi-abc12345678901234567 falhou e "
        f"a chave do servidor {fake_server_secret} foi chamada junto com sk-ant-api03-123456789012345."
    )

    cleaned = scrub_sensitive_api_keys(contaminated_text, extra_secrets=[fake_server_secret])

    assert "REAL_SECRET_SERVER_KEY" not in cleaned
    assert "nvapi-abc12345678901234567" not in cleaned
    assert "sk-ant-api03" not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned


def test_adversarial_key_probing_resistance(client):
    """Testa tentativas adversariais de extração da chave de API via rotas e parâmetros."""
    # 1. Probing via /healthz
    res1 = client.get("/healthz")
    assert res1.status_code == 200
    assert "key" not in json.dumps(res1.get_json()).lower()

    # 2. Probing via endpoints inexistentes ou erro 404
    res2 = client.get("/api/get_api_key", headers={"Origin": "https://jluckmay.github.io"})
    assert res2.status_code == 404
    assert "key" not in res2.get_data(as_text=True).lower()

    # 3. Probing via injeção de parâmetros maliciosos tentando forçar echo de variáveis
    malicious_payload = {
        "name": "{{ os.environ['NVIDIA_API_KEY'] }}",
        "extra": "PRINT_ENV_KEY",
        "provider": "default",
    }
    enc_payload = encrypt_payload_envelope(malicious_payload, direction="req")

    fake_result = MagicMock()
    fake_result.success = True
    fake_result.pdf_path = None
    fake_result.compiler_message = "Normal output"
    fake_result.latex_code = "% LaTeX standard"
    fake_result.token_metrics = {}
    fake_result.structured_cv = {}

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-SECRET_TEST_KEY_NEVER_LEAK"}):
        with patch("server.build_resume_pipeline", return_value=fake_result):
            res3 = client.post(
                "/api/generate",
                headers={
                    "Origin": "https://jluckmay.github.io",
                    "Referer": "https://jluckmay.github.io/latex-resume",
                    "Content-Type": "application/json",
                },
                data=json.dumps(enc_payload),
            )
            assert res3.status_code == 200
            decrypted = decrypt_payload_envelope(res3.get_json(), direction="resp")
            assert "nvapi-SECRET_TEST_KEY_NEVER_LEAK" not in json.dumps(decrypted)


def test_server_runtime_error_message_is_informative_and_scrubbed(client):
    """Valida se erros de execução retornam mensagens explicativas higienizadas em vez de 'RuntimeError' opaco."""
    raw_payload = {
        "name": "Teste Candidato",
        "role": "Dev",
        "provider": "default",
    }
    enc_payload = encrypt_payload_envelope(raw_payload, direction="req")

    with patch("server.build_resume_pipeline", side_effect=RuntimeError(
        "Chave de API NVIDIA não configurada no servidor backend. "
        "Informe sua própria chave de API (iniciando em 'nvapi-...') no campo 'Chave de API do Provedor'."
    )):
        res = client.post(
            "/api/generate",
            headers={
                "Origin": "https://jluckmay.github.io",
                "Referer": "https://jluckmay.github.io/latex-resume",
                "Content-Type": "application/json",
            },
            data=json.dumps(enc_payload),
        )
        assert res.status_code == 500
        decrypted = decrypt_payload_envelope(res.get_json(), direction="resp")
        assert decrypted["success"] is False
        assert "Chave de API NVIDIA não configurada no servidor backend" in decrypted["error"]
        # Garante que não é apenas a string genérica 'Falha no processamento: RuntimeError'
        assert decrypted["error"] != "Falha no processamento: RuntimeError"


def test_csp_explicit_font_and_style_directives():
    """Valida se a política CSP no index.html declara explicitamente font-src e style-src para evitar bloqueio de fontes."""
    html_text = (Path(__file__).parent.parent / "index.html").read_text(encoding="utf-8")
    assert "font-src 'self' https://fonts.gstatic.com" in html_text
    assert "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com" in html_text


def test_api_status_reports_has_nvidia_key(client):
    """Garante que /api/status informe com segurança se a chave NVIDIA está presente no servidor."""
    res = client.get(
        "/api/status",
        headers={
            "Origin": "https://jluckmay.github.io",
            "Referer": "https://jluckmay.github.io/latex-resume",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "has_nvidia_key" in data
    assert isinstance(data["has_nvidia_key"], bool)


def test_server_key_sharing_default_and_nvidia():
    """Garante que o enclave compartilhe a chave de infraestrutura entre 'default' e 'nvidia'."""
    from src._vault import _get_server_key_for_provider, _SERVER_ENCLAVE_STORE
    _SERVER_ENCLAVE_STORE.clear()
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test1234567890abcdef"}):
        key_default = _get_server_key_for_provider("default")
        assert key_default == "nvapi-test1234567890abcdef"
        # Mesmo tendo sido removido de os.environ, o provedor 'nvidia' ainda tem acesso
        key_nvidia = _get_server_key_for_provider("nvidia")
        assert key_nvidia == "nvapi-test1234567890abcdef"


def test_google_missing_key_informative_error(client):
    """Garante que requisições com provedores de chave própria sem chave retornem erro claro em vez de 'RuntimeError' genérico."""
    raw_payload = {
        "resume_type": "profissional",
        "provider": "google",
        "use_ai": True,
    }
    enc_payload = encrypt_payload_envelope(raw_payload, direction="req")
    res = client.post(
        "/api/generate",
        headers={
            "Origin": "https://jluckmay.github.io",
            "Referer": "https://jluckmay.github.io/latex-resume",
            "Content-Type": "application/json",
            "X-Resume-Client": "jluckmay-github-pages-v1",
            "X-Client-Timestamp": str(int(time.time() * 1000)),
            "X-Encrypted-Payload": "1",
        },
        data=json.dumps(enc_payload),
    )
    assert res.status_code == 500
    decrypted = decrypt_payload_envelope(res.get_json(), direction="resp")
    assert decrypted["success"] is False
    assert "Google Gemini" in decrypted["error"]
    assert decrypted["error"] != "Falha no processamento: RuntimeError"


