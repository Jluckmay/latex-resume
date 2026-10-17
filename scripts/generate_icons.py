"""Script para geração automatizada dos ícones oficiais do projeto LaTeX Resume Generator.

Gera:
- favicon.svg (Vetor SVG escalável de alta definição)
- favicon.png (512x512)
- favicon-192.png (192x192 PWA)
- favicon-32.png (32x32)
- favicon-16.png (16x16)
- apple-touch-icon.png (180x180)
- favicon.ico (multi-frame: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256)

Salva tanto na raiz quanto em assets/ para compatibilidade total com GitHub Pages,
Flask (server.py) e Streamlit (app.py).
"""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B192C"/>
      <stop offset="45%" stop-color="#0F4C81"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>

    <!-- Squircle Border Gradient -->
    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#818CF8" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#2563EB" stop-opacity="0.2"/>
    </linearGradient>

    <!-- Document Page Gradient -->
    <linearGradient id="pageGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#F1F5F9"/>
    </linearGradient>

    <!-- Fold Flap Gradient -->
    <linearGradient id="foldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#CBD5E1"/>
      <stop offset="100%" stop-color="#94A3B8"/>
    </linearGradient>

    <!-- AI Sparkle Gradient -->
    <linearGradient id="starGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="50%" stop-color="#60A5FA"/>
      <stop offset="100%" stop-color="#FBBF24"/>
    </linearGradient>

    <!-- Soft Drop Shadows -->
    <filter id="cardShadow" x="-10%" y="-10%" width="125%" height="125%">
      <feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#000000" flood-opacity="0.45"/>
    </filter>
    <filter id="starGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Outer Rounded Container (Squircle) -->
  <rect x="18" y="18" width="476" height="476" rx="108" ry="108" fill="url(#bgGrad)" stroke="url(#borderGrad)" stroke-width="4"/>

  <!-- Subtle Inner Ambient Mesh -->
  <circle cx="120" cy="110" r="140" fill="#2563EB" opacity="0.18" filter="blur(40px)"/>
  <circle cx="400" cy="400" r="130" fill="#38BDF8" opacity="0.15" filter="blur(40px)"/>

  <!-- Document Page with Folded Corner -->
  <g filter="url(#cardShadow)">
    <!-- Document Base Sheet: cut at top right (330, 78) to (400, 148) -->
    <path d="M 136 78
             L 330 78
             L 404 152
             L 404 410
             A 22 22 0 0 1 382 432
             L 136 432
             A 22 22 0 0 1 114 410
             L 114 100
             A 22 22 0 0 1 136 78 Z"
          fill="url(#pageGrad)"/>

    <!-- Document Corner Fold Flap -->
    <path d="M 330 78
             L 330 136
             A 16 16 0 0 0 346 152
             L 404 152 Z"
          fill="url(#foldGrad)"/>
    <path d="M 330 78
             L 330 136
             A 16 16 0 0 0 346 152
             L 404 152 Z"
          fill="none" stroke="#E2E8F0" stroke-width="1.5"/>
  </g>

  <!-- Document Header Bar -->
  <rect x="146" y="116" width="158" height="18" rx="9" fill="#0F4C81"/>
  <rect x="146" y="144" width="105" height="10" rx="5" fill="#94A3B8"/>

  <!-- LaTeX Typography Feature Box -->
  <rect x="144" y="174" width="230" height="92" rx="14" fill="#0F172A" opacity="0.04"/>
  <rect x="144" y="174" width="230" height="92" rx="14" fill="none" stroke="#E2E8F0" stroke-width="1.5"/>

  <!-- Stylized LaTeX Logo: L - A (raised) - T - E (lowered) - X -->
  <g fill="#0F4C81" font-family="'Times New Roman', 'Latin Modern Roman', 'Computer Modern', Georgia, serif" font-weight="bold">
    <text x="168" y="235" font-size="42">L</text>
    <text x="198" y="222" font-size="30">A</text>
    <text x="224" y="235" font-size="42">T</text>
    <text x="254" y="247" font-size="30">E</text>
    <text x="278" y="235" font-size="42">X</text>
  </g>

  <!-- Document Section 1: Experience Lines -->
  <rect x="146" y="292" width="76" height="11" rx="5.5" fill="#0F4C81"/>
  <rect x="146" y="315" width="226" height="7" rx="3.5" fill="#CBD5E1"/>
  <rect x="146" y="331" width="186" height="7" rx="3.5" fill="#E2E8F0"/>

  <!-- Document Section 2: Education & Skills Lines -->
  <rect x="146" y="356" width="94" height="11" rx="5.5" fill="#0F4C81"/>
  <rect x="146" y="379" width="226" height="7" rx="3.5" fill="#CBD5E1"/>
  <rect x="146" y="395" width="160" height="7" rx="3.5" fill="#E2E8F0"/>

  <!-- AI Sparks / Intelligence Star (Top Right Corner Accent) -->
  <g filter="url(#starGlow)">
    <!-- Primary 4-point Star -->
    <path d="M 412 60
             Q 412 94 446 94
             Q 412 94 412 128
             Q 412 94 378 94
             Q 412 94 412 60 Z"
          fill="url(#starGrad)"/>
    <!-- Center white core for sparkle -->
    <circle cx="412" cy="94" r="5" fill="#FFFFFF"/>
    <!-- Secondary Mini Sparkle -->
    <path d="M 452 126
             Q 452 142 468 142
             Q 452 142 452 158
             Q 452 142 436 142
             Q 452 142 452 126 Z"
          fill="#38BDF8"/>
  </g>
</svg>
"""


def render_raster_icon(size: int = 1024) -> Image.Image:
    """Renderiza a imagem rasterizada em alta resolução (1024x1024) para posterior downsampling."""
    scale = size / 512.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def s(val: float) -> int:
        return int(round(val * scale))

    # 1. Background Squircle
    margin = s(18)
    sq_size = size - 2 * margin
    radius = s(108)

    # Cria máscara para squircle e aplica gradiente
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([margin, margin, margin + sq_size, margin + sq_size], radius=radius, fill=255)

    # Gradiente de fundo: Navy (#0B192C) -> Indigo/Blue (#0F4C81 -> #1E3A8A)
    for y in range(size):
        ratio = y / float(size)
        r = int(11 * (1 - ratio) + 30 * ratio)
        g = int(25 * (1 - ratio) + 58 * ratio)
        b = int(44 * (1 - ratio) + 138 * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Aplica máscara do squircle
    img.putalpha(mask)
    draw = ImageDraw.Draw(img)

    # 2. Borda do squircle (#38BDF8 suave)
    draw.rounded_rectangle(
        [margin, margin, margin + sq_size, margin + sq_size],
        radius=radius,
        outline=(56, 189, 248, 160),
        width=max(2, s(4)),
    )

    # 3. Document Page Sheet
    # Coordenadas: L 136 78 -> L 330 78 -> L 404 152 -> L 404 410 -> L 136 432
    doc_left = s(114)
    doc_top = s(78)
    doc_right = s(404)
    doc_bottom = s(432)
    fold_x = s(330)
    fold_y = s(152)
    doc_corner = s(20)

    # Sombra do documento
    shadow_offset = s(12)
    shadow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.rounded_rectangle(
        [doc_left, doc_top + shadow_offset, doc_right, doc_bottom + shadow_offset],
        radius=doc_corner,
        fill=(0, 0, 0, 110),
    )
    img = Image.alpha_composite(img, shadow_layer)
    draw = ImageDraw.Draw(img)

    # Folha do documento (fundo branco / gelo)
    doc_points = [
        (s(136), s(78)),
        (fold_x, s(78)),
        (doc_right, fold_y),
        (doc_right, s(410)),
        (s(382), doc_bottom),
        (s(136), doc_bottom),
        (doc_left, s(410)),
        (doc_left, s(100)),
    ]
    draw.polygon(doc_points, fill=(248, 250, 252, 255))

    # Flap da dobra (triângulo de dobra no canto superior direito)
    fold_points = [(fold_x, s(78)), (fold_x, fold_y), (doc_right, fold_y)]
    draw.polygon(fold_points, fill=(203, 213, 225, 255))
    draw.line([(fold_x, s(78)), (fold_x, fold_y), (doc_right, fold_y)], fill=(148, 163, 184, 255), width=s(2))

    # 4. Linhas decorativas do topo do currículo
    # Barra de cabeçalho
    draw.rounded_rectangle([s(146), s(116), s(304), s(134)], radius=s(9), fill=(15, 76, 129, 255))
    # Subtítulo
    draw.rounded_rectangle([s(146), s(144), s(251), s(154)], radius=s(5), fill=(148, 163, 184, 255))

    # 5. Caixa de Destaque LaTeX
    draw.rounded_rectangle(
        [s(144), s(174), s(374), s(266)],
        radius=s(14),
        fill=(241, 245, 249, 255),
        outline=(226, 232, 240, 255),
        width=max(1, s(2)),
    )

    # Tenta carregar fonte serifada para a sigla LaTeX
    font_large = None
    font_small = None
    for font_name in ["timesbd.ttf", "georgiab.ttf", "times.ttf", "arialbd.ttf", "calibrib.ttf"]:
        try:
            font_large = ImageFont.truetype(font_name, s(42))
            font_small = ImageFont.truetype(font_name, s(30))
            break
        except Exception:
            continue

    primary_color = (15, 76, 129, 255)

    if font_large and font_small:
        draw.text((s(166), s(195)), "L", fill=primary_color, font=font_large)
        draw.text((s(196), s(185)), "A", fill=primary_color, font=font_small)
        draw.text((s(222), s(195)), "T", fill=primary_color, font=font_large)
        draw.text((s(254), s(207)), "E", fill=primary_color, font=font_small)
        draw.text((s(280), s(195)), "X", fill=primary_color, font=font_large)
    else:
        # Fallback se nenhuma fonte TTF estiver disponível no sistema
        draw.rectangle([s(166), s(200), s(350), s(240)], fill=primary_color)

    # 6. Seções e Linhas de Texto do Currículo
    # Seção 1: Experiência
    draw.rounded_rectangle([s(146), s(292), s(222), s(303)], radius=s(5), fill=(15, 76, 129, 255))
    draw.rounded_rectangle([s(146), s(315), s(372), s(322)], radius=s(3), fill=(203, 213, 225, 255))
    draw.rounded_rectangle([s(146), s(331), s(332), s(338)], radius=s(3), fill=(226, 232, 240, 255))

    # Seção 2: Formação & Competências
    draw.rounded_rectangle([s(146), s(356), s(240), s(367)], radius=s(5), fill=(15, 76, 129, 255))
    draw.rounded_rectangle([s(146), s(379), s(372), s(386)], radius=s(3), fill=(203, 213, 225, 255))
    draw.rounded_rectangle([s(146), s(395), s(306), s(402)], radius=s(3), fill=(226, 232, 240, 255))

    # 7. AI Sparkle Star (Estrela de 4 pontas da IA no canto superior direito)
    cx, cy = s(412), s(94)
    r_outer = s(36)
    r_inner = s(9)
    star_points = []
    for i in range(8):
        angle = i * (math.pi / 4.0)
        curr_r = r_outer if i % 2 == 0 else r_inner
        px = cx + curr_r * math.cos(angle)
        py = cy + curr_r * math.sin(angle)
        star_points.append((px, py))

    # Glow da estrela
    draw.polygon(star_points, fill=(56, 189, 248, 255))
    # Núcleo brilhante
    draw.ellipse([cx - s(6), cy - s(6), cx + s(6), cy + s(6)], fill=(255, 255, 255, 255))

    # Mini estrela secundária
    cx2, cy2 = s(452), s(142)
    r2_outer = s(16)
    r2_inner = s(4)
    star2_points = []
    for i in range(8):
        angle = i * (math.pi / 4.0)
        curr_r = r2_outer if i % 2 == 0 else r2_inner
        px = cx2 + curr_r * math.cos(angle)
        py = cy2 + curr_r * math.sin(angle)
        star2_points.append((px, py))
    draw.polygon(star2_points, fill=(96, 165, 250, 230))

    return img


def main() -> None:
    print("Gerando arquivos de ícone oficiais do projeto LaTeX Resume Generator...")

    # 1. Salva favicon.svg na raiz e em assets/
    (ROOT / "favicon.svg").write_text(SVG_CONTENT, encoding="utf-8")
    (ASSETS_DIR / "favicon.svg").write_text(SVG_CONTENT, encoding="utf-8")
    print("[OK] favicon.svg gerado na raiz e em assets/")

    # 2. Renderiza imagem base de alta fidelidade
    base_img = render_raster_icon(size=1024)

    # 3. Exporta diferentes resoluções com reamostragem Lanczos
    sizes = {
        "favicon.png": 512,
        "apple-touch-icon.png": 180,
        "favicon-192.png": 192,
        "favicon-32.png": 32,
        "favicon-16.png": 16,
    }

    generated_images: dict[int, Image.Image] = {}

    for fname, sz in sizes.items():
        res_img = base_img.resize((sz, sz), Image.Resampling.LANCZOS)
        generated_images[sz] = res_img
        res_img.save(ROOT / fname, "PNG", optimize=True)
        res_img.save(ASSETS_DIR / fname, "PNG", optimize=True)
        print(f"[OK] {fname} ({sz}x{sz}) gerado")

    # 4. Gera favicon.ico multi-frame (16, 24, 32, 48, 64, 128, 256)
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_frames = [base_img.resize((s, s), Image.Resampling.LANCZOS) for s in ico_sizes]

    # Salva ICO contendo todos os tamanhos na raiz e em assets/
    ico_frames[0].save(
        ROOT / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_frames[1:],
    )
    ico_frames[0].save(
        ASSETS_DIR / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_frames[1:],
    )
    print("[OK] favicon.ico multi-resolucao gerado na raiz e em assets/")
    print("Todos os icones foram gerados com sucesso!")


if __name__ == "__main__":
    main()
