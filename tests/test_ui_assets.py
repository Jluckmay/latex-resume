"""Testes de integridade dos ícones oficiais, favicon de navegador e responsividade das interfaces gráficas."""

import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from server import app
from src.config import PROJECT_ROOT
from src.ui_theme import get_theme_css


def test_icon_assets_exist():
    """Valida se todos os formatos essenciais de ícones foram organizados em assets/icons/ e a raiz está limpa."""
    expected_files = [
        "favicon.svg",
        "favicon.png",
        "favicon.ico",
        "apple-touch-icon.png",
        "favicon-192.png",
        "favicon-32.png",
        "favicon-16.png",
    ]
    icons_dir = PROJECT_ROOT / "assets" / "icons"
    assert icons_dir.exists(), "Diretório assets/icons/ não encontrado"

    for fname in expected_files:
        icon_path = icons_dir / fname
        root_path = PROJECT_ROOT / fname
        assert icon_path.exists(), f"Arquivo {fname} não encontrado em assets/icons/"
        assert icon_path.stat().st_size > 0, f"Arquivo {fname} está vazio"
        # Invariante de organização: nenhum ícone deve ficar solto na raiz
        assert not root_path.exists(), f"Arquivo {fname} não deve estar solto na raiz do repositório"


def test_icon_image_dimensions():
    """Valida as dimensões e formatos das imagens PNG e ICO geradas em assets/icons/."""
    icons_dir = PROJECT_ROOT / "assets" / "icons"

    img_512 = Image.open(icons_dir / "favicon.png")
    assert img_512.size == (512, 512)
    assert img_512.format == "PNG"

    img_180 = Image.open(icons_dir / "apple-touch-icon.png")
    assert img_180.size == (180, 180)
    assert img_180.format == "PNG"

    img_32 = Image.open(icons_dir / "favicon-32.png")
    assert img_32.size == (32, 32)
    assert img_32.format == "PNG"

    ico = Image.open(icons_dir / "favicon.ico")
    assert ico.format == "ICO"


def test_svg_content_validity():
    """Valida se o SVG em assets/icons/ contém os elementos da identidade visual do projeto."""
    svg_text = (PROJECT_ROOT / "assets" / "icons" / "favicon.svg").read_text(encoding="utf-8")
    assert "<svg" in svg_text
    assert 'viewBox="0 0 512 512"' in svg_text
    assert "LaTeX" in svg_text or ("L" in svg_text and "T" in svg_text and "E" in svg_text and "X" in svg_text)
    assert "starGrad" in svg_text or "starGlow" in svg_text


def test_server_favicon_endpoints():
    """Valida se o servidor Flask responde com sucesso aos endpoints de favicon servidos de assets/icons/."""
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

    # Links de favicon na guia do navegador apontando para assets/icons/
    assert 'rel="icon" type="image/svg+xml" href="assets/icons/favicon.svg"' in html_text
    assert 'rel="shortcut icon" href="assets/icons/favicon.ico"' in html_text
    assert 'rel="apple-touch-icon"' in html_text

    # Logotipo na barra de navegação apontando para assets/icons/
    assert 'class="brand-logo"' in html_text
    assert 'src="assets/icons/favicon.svg"' in html_text

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

    # Blindagem de propriedades de backend no console
    assert 'Object.defineProperty(window, "backendUrl"' in html_text
    assert 'Object.defineProperty(window, "BACKEND_URL"' in html_text
    assert 'Object.defineProperty(window, "renderUrl"' in html_text


def test_all_template_previews_use_lucas_silva():
    """Valida se todos os previews de templates LaTeX utilizam exclusivamente o candidato de exemplo 'Lucas Silva'."""
    from src.ui_theme import render_template_preview_html

    templates = [
        "modern_pro",
        "academic_classic",
        "tech_sidebar",
        "minimal_ats",
        "overleaf_russell_ti",
        "overleaf_awesome_cv",
        "overleaf_single_page_keywords",
        "google_standard",
        "ai_ats_max",
    ]

    for tpl in templates:
        html = render_template_preview_html(tpl)
        has_lucas_silva = (
            "Lucas Silva" in html
            or "LUCAS SILVA" in html
            or ("Lucas" in html and "Silva" in html)
            or ("LUCAS" in html and "SILVA" in html)
        )
        assert has_lucas_silva, f"Template {tpl} não contém 'Lucas Silva' no preview"
        # Nomes legados não devem constar
        assert "Helena Costa" not in html
        assert "Jason Richards" not in html
        assert "Mayrinck" not in html
        assert "John Doe" not in html
        assert "JOHN DOE" not in html


def test_default_palette_is_charcoal_minimal():
    """Valida se a paleta padrão do sistema é a 'charcoal_minimal' (Grafite ATS #18181B / #3F3F46)."""
    from src.ui_theme import COLOR_PRESETS

    first_key = list(COLOR_PRESETS.keys())[0]
    assert first_key == "charcoal_minimal"
    assert COLOR_PRESETS["charcoal_minimal"]["primary"] == "#18181B"
    assert COLOR_PRESETS["charcoal_minimal"]["secondary"] == "#3F3F46"

    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
    assert '<option value="charcoal_minimal" selected>' in html_text
    assert 'value="#18181B"' in html_text
    assert 'value="#3F3F46"' in html_text


def test_backend_enclave_obfuscated_url():
    """Valida se a URL do servidor backend em nuvem é ofuscada e não exposta em texto puro no projeto."""
    import hashlib
    import re

    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

    # O enclave criptográfico deve estar presente no index.html
    assert "const BackendEnclave = (() => {" in html_text
    assert "aliasLabel: \"🔒 Servidor Render Nuvem Padrão\"" in html_text

    # Validação do algoritmo de decifragem do enclave em Python
    c1_match = re.search(r"_C1\s*=\s*\[([0-9,\s]+)\]", html_text)
    c2_match = re.search(r"_C2\s*=\s*\[([0-9,\s]+)\]", html_text)
    assert c1_match and c2_match

    c1 = [int(x.strip()) for x in c1_match.group(1).split(",")]
    c2 = [int(x.strip()) for x in c2_match.group(1).split(",")]
    cipher = c1 + c2
    key = [0x53, 0x79, 0x6E, 0x74, 0x68, 0x65, 0x73, 0x69, 0x73]
    salt = 0xA7

    dec = ""
    for i, b in enumerate(cipher):
        k = key[i % len(key)]
        diff = (b - (i * 7) - salt) % 256
        if diff < 0:
            diff += 256
        dec += chr(diff ^ k)

    # A URL decifrada deve coincidir com o hash criptográfico SHA-256 esperado
    expected_hash = "11f1f1b11b67d29a6c7595c5013db65ed6ed94fecb2f0f150fa06b2bcc2bdd3d"
    assert hashlib.sha256(dec.encode("utf-8")).hexdigest() == expected_hash

    # Garante que a URL decifrada ou seu host privado não estão em texto puro no index.html
    sensitive_subdomain = dec.split("://")[1].split(".")[0]
    assert sensitive_subdomain not in html_text
    assert dec not in html_text


def test_no_plaintext_backend_url_in_project_files():
    """Garante que a URL do backend de produção e seu subdomínio não vazem em texto puro em nenhum arquivo do projeto."""
    import re
    import os

    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
    c1_match = re.search(r"_C1\s*=\s*\[([0-9,\s]+)\]", html_text)
    c2_match = re.search(r"_C2\s*=\s*\[([0-9,\s]+)\]", html_text)
    assert c1_match and c2_match

    c1 = [int(x.strip()) for x in c1_match.group(1).split(",")]
    c2 = [int(x.strip()) for x in c2_match.group(1).split(",")]
    cipher = c1 + c2
    key = [0x53, 0x79, 0x6E, 0x74, 0x68, 0x65, 0x73, 0x69, 0x73]
    salt = 0xA7

    dec = ""
    for i, b in enumerate(cipher):
        k = key[i % len(key)]
        diff = (b - (i * 7) - salt) % 256
        if diff < 0:
            diff += 256
        dec += chr(diff ^ k)

    sensitive_subdomain = dec.split("://")[1].split(".")[0]

    # Verifica todos os arquivos de código e documentação do repositório
    excluded_dirs = {".git", ".pytest_cache", "__pycache__", "venv", ".venv", "node_modules"}
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for f in files:
            file_path = Path(root) / f
            if file_path.suffix.lower() in [".png", ".ico", ".svg", ".pdf", ".pyc"]:
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            assert sensitive_subdomain not in content, f"Subdomínio sensível do backend vazou em {file_path}"
            assert dec not in content, f"URL completa do backend vazou em {file_path}"


def test_index_html_auto_environment_detection():
    """Valida se o index.html detecta automaticamente localhost/file vs nuvem web para o backend."""
    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

    assert "window.location.hostname === \"127.0.0.1\"" in html_text
    assert "window.location.hostname === \"localhost\"" in html_text
    assert "window.location.protocol === \"file:\"" in html_text
    assert "http://127.0.0.1:5000" in html_text
    assert "BackendEnclave.resolve()" in html_text


