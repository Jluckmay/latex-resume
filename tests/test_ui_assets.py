"""Testes de integridade dos ícones oficiais, favicon de navegador e responsividade das interfaces gráficas."""

import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from server import app
from src.config import PROJECT_ROOT
from src.ui_theme import get_theme_css


def test_icon_assets_exist():
    """Valida se todos os formatos essenciais de ícones foram gerados com sucesso."""
    expected_files = [
        "favicon.svg",
        "favicon.png",
        "favicon.ico",
        "apple-touch-icon.png",
        "favicon-192.png",
        "favicon-32.png",
        "favicon-16.png",
    ]
    for fname in expected_files:
        root_path = PROJECT_ROOT / fname
        assets_path = PROJECT_ROOT / "assets" / fname
        assert root_path.exists(), f"Arquivo {fname} não encontrado na raiz"
        assert assets_path.exists(), f"Arquivo {fname} não encontrado em assets/"
        assert root_path.stat().st_size > 0, f"Arquivo {fname} está vazio"


def test_icon_image_dimensions():
    """Valida as dimensões e formatos das imagens PNG e ICO geradas."""
    img_512 = Image.open(PROJECT_ROOT / "favicon.png")
    assert img_512.size == (512, 512)
    assert img_512.format == "PNG"

    img_180 = Image.open(PROJECT_ROOT / "apple-touch-icon.png")
    assert img_180.size == (180, 180)
    assert img_180.format == "PNG"

    img_32 = Image.open(PROJECT_ROOT / "favicon-32.png")
    assert img_32.size == (32, 32)
    assert img_32.format == "PNG"

    ico = Image.open(PROJECT_ROOT / "favicon.ico")
    assert ico.format == "ICO"


def test_svg_content_validity():
    """Valida se o SVG contém os elementos da identidade visual do projeto."""
    svg_text = (PROJECT_ROOT / "favicon.svg").read_text(encoding="utf-8")
    assert "<svg" in svg_text
    assert 'viewBox="0 0 512 512"' in svg_text
    assert "LaTeX" in svg_text or ("L" in svg_text and "T" in svg_text and "E" in svg_text and "X" in svg_text)
    assert "starGrad" in svg_text or "starGlow" in svg_text


def test_server_favicon_endpoints():
    """Valida se o servidor Flask responde com sucesso aos endpoints de favicon."""
    client = app.test_client()

    r_ico = client.get("/favicon.ico")
    assert r_ico.status_code == 200
    assert "image/x-icon" in r_ico.content_type

    r_svg = client.get("/favicon.svg")
    assert r_svg.status_code == 200
    assert "image/svg+xml" in r_svg.content_type

    r_png = client.get("/favicon.png")
    assert r_png.status_code == 200
    assert "image/png" in r_png.content_type

    r_apple = client.get("/apple-touch-icon.png")
    assert r_apple.status_code == 200
    assert "image/png" in r_apple.content_type


def test_index_html_favicon_and_responsiveness():
    """Valida a presença de tags favicon e regras de responsividade no index.html."""
    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

    # Links de favicon na guia do navegador
    assert 'rel="icon" type="image/svg+xml" href="favicon.svg"' in html_text
    assert 'rel="shortcut icon" href="favicon.ico"' in html_text
    assert 'rel="apple-touch-icon"' in html_text

    # Logotipo na barra de navegação
    assert 'class="brand-logo"' in html_text
    assert 'src="favicon.svg"' in html_text

    # Regras responsivas de viewport e media queries
    assert "@media (max-width: 820px)" in html_text
    assert "@media (max-width: 600px)" in html_text
    assert "@media (max-width: 440px)" in html_text
    assert "clamp(" in html_text


def test_ui_theme_responsive_css():
    """Valida se o gerador de CSS da interface Streamlit inclui regras de responsividade."""
    css = get_theme_css("light", "#0F4C81")
    assert "@media (max-width: 820px)" in css
    assert ".st-brand-logo" in css
    assert "min-height: 44px" in css


def test_index_html_encrypted_transport_and_devtools_defense():
    """Valida a presença de rotinas de criptografia de ponta a ponta e blindagem do Console no index.html."""
    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

    # Funções de transporte cifrado AES-256-GCM
    assert "encryptTransportPayload" in html_text
    assert "decryptTransportPayload" in html_text
    assert "ENC_PAYLOAD_V1" in html_text
    assert "X-Encrypted-Payload" in html_text

    # Defesas de Console / DevTools
    assert "Object.defineProperty(window, \"apiKey\"" in html_text
    assert "Object.defineProperty(window, \"NVIDIA_API_KEY\"" in html_text
    assert "LaTeX Resume Enclave" in html_text

    # Nenhuma chave hardcoded
    assert "nvapi-" not in html_text or "placeholder" in html_text
    assert "sk-" not in html_text or "placeholder" in html_text
    assert "AIza" not in html_text or "placeholder" in html_text
