"""Testes para a política de Zero-Storage no servidor:
Garante que documentos recebidos e gerados não sejam armazenados em disco,
sendo processados exclusivamente na memória da sessão do usuário.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from src.compiler import secure_wipe_and_remove_dir
from src.config import CACHE_DIR, PROJECT_ROOT
from src.token_plugins import SHA256DiskCachePlugin


def test_secure_wipe_and_remove_dir():
    """Valida que diretórios efêmeros e arquivos confidenciais são destruídos sem deixar vestígios."""
    tmp = Path(tempfile.mkdtemp(prefix="test_wipe_"))
    try:
        # Cria arquivos simulando documentos recebidos e compilados
        tex_file = tmp / "curriculo.tex"
        pdf_file = tmp / "curriculo.pdf"
        photo_file = tmp / "profile_photo.png"
        aux_file = tmp / "curriculo.aux"

        tex_file.write_text("\\documentclass{article}\n\\begin{document}\nConfidential CV Data\n\\end{document}", encoding="utf-8")
        pdf_file.write_bytes(b"%PDF-1.4 confidential binary data")
        photo_file.write_bytes(b"\x89PNG\r\n\x1a\nphoto bytes")
        aux_file.write_text("\\relax\n", encoding="utf-8")

        assert tex_file.exists()
        assert pdf_file.exists()
        assert photo_file.exists()
        assert aux_file.exists()

        # Executa limpeza segura
        secure_wipe_and_remove_dir(tmp)

        # O diretório e todos os arquivos devem ter sido completamente eliminados
        assert not tmp.exists()
        assert not tex_file.exists()
        assert not pdf_file.exists()
        assert not photo_file.exists()
        assert not aux_file.exists()
    finally:
        if tmp.exists():
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def test_sha256_cache_in_memory_zero_storage():
    """Valida que o cache de tokens opera estritamente em memória RAM por padrão (sem escrita em disco)."""
    # Garante que arquivo de cache em disco não existe antes do teste
    test_cache_dir = PROJECT_ROOT / ".cache_test_zero_storage"
    if test_cache_dir.exists():
        import shutil
        shutil.rmtree(test_cache_dir, ignore_errors=True)

    try:
        cache = SHA256DiskCachePlugin(cache_dir=test_cache_dir, in_memory_only=True)
        key = cache.make_key("test_model", [{"role": "user", "content": "secret resume data"}])

        cache.set(key, "synthesized resume content", "test_model")
        assert cache.get(key) == "synthesized resume content"

        # Nenhum arquivo deve ter sido gravado em disco
        assert not (test_cache_dir / "nvidia_token_cache.json").exists()
        assert not test_cache_dir.exists()
    finally:
        if test_cache_dir.exists():
            import shutil
            shutil.rmtree(test_cache_dir, ignore_errors=True)


def test_server_code_guarantees_zero_storage():
    """Valida que server.py utiliza use_cache=False e secure_wipe_and_remove_dir em bloco finally."""
    server_text = (PROJECT_ROOT / "server.py").read_text(encoding="utf-8")
    assert "use_cache=False" in server_text
    assert "secure_wipe_and_remove_dir(build_path)" in server_text
    assert "finally:" in server_text


def test_app_code_guarantees_zero_storage():
    """Valida que app.py utiliza use_cache=False, compilação efêmera e secure_wipe_and_remove_dir."""
    app_text = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "use_cache=False" in app_text
    assert "secure_wipe_and_remove_dir(build_path)" in app_text
    assert "st.session_state[\"session_pdf_bytes\"]" in app_text


def test_cache_directory_clean():
    """Valida que o cache persistente não contém dados de usuários."""
    if CACHE_DIR.exists():
        cache_files = list(CACHE_DIR.glob("*.json"))
        assert len(cache_files) == 0, f"Encontrados arquivos de cache em disco: {cache_files}"
