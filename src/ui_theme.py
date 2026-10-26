"""Detecção automática de tema/idioma, temas visuais (Claro/Escuro), customização de cores e Previews de Templates LaTeX."""

from __future__ import annotations

import locale
import os
import re
from typing import Dict

COLOR_PRESETS: Dict[str, Dict[str, str]] = {
    "charcoal_minimal": {
        "pt-br": "🖤 Grafite ATS (#18181B)",
        "en-us": "🖤 Minimalist Charcoal (ATS)",
        "primary": "#18181B",
        "secondary": "#3F3F46",
    },
    "ocean_blue": {
        "pt-br": "🌊 Azul Oceano (Padrão Executivo)",
        "en-us": "🌊 Ocean Blue (Executive Default)",
        "primary": "#0F4C81",
        "secondary": "#1E293B",
    },
    "academic_navy": {
        "pt-br": "🎓 Azul Marinho Acadêmico",
        "en-us": "🎓 Academic Navy",
        "primary": "#1B365D",
        "secondary": "#0F172A",
    },
    "emerald_tech": {
        "pt-br": "🌲 Verde Esmeralda Tech",
        "en-us": "🌲 Emerald Tech",
        "primary": "#047857",
        "secondary": "#064E3B",
    },
    "royal_indigo": {
        "pt-br": "🔮 Índigo Real",
        "en-us": "🔮 Royal Indigo",
        "primary": "#4338CA",
        "secondary": "#1E1B4B",
    },
    "burgundy_classic": {
        "pt-br": "🍷 Bordô Clássico / Burgundy",
        "en-us": "🍷 Classic Burgundy",
        "primary": "#881337",
        "secondary": "#27272A",
    },
}


def detect_default_language(st_context_headers: Dict[str, str] | None = None) -> str:
    """Detecta automaticamente o idioma padrão do navegador (`Accept-Language`) ou do sistema operacional."""
    if st_context_headers:
        accept_lang = st_context_headers.get("Accept-Language") or st_context_headers.get("accept-language") or ""
        if accept_lang:
            first_tag = accept_lang.split(",")[0].strip().lower()
            if first_tag.startswith("en"):
                return "en-us"
            if first_tag.startswith("pt"):
                return "pt-br"

    # Fallback: sistema operacional (Windows / POSIX)
    try:
        if os.name == "nt":
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # 0x0416 = pt-BR (1046), 0x0816 = pt-PT (2070); 0x09 primary = English
            if (lang_id & 0x3FF) == 0x09:
                return "en-us"
            if (lang_id & 0x3FF) == 0x16:
                return "pt-br"
    except Exception:
        pass

    try:
        loc, _ = locale.getdefaultlocale()
        if loc and loc.lower().startswith("en"):
            return "en-us"
    except Exception:
        pass

    return "pt-br"


def detect_default_theme(st_context_headers: Dict[str, str] | None = None) -> str:
    """Detecta automaticamente o tema padrão (Claro 'light' vs Escuro 'dark') do navegador ou SO."""
    if st_context_headers:
        pref = (
            st_context_headers.get("Sec-CH-Prefers-Color-Scheme")
            or st_context_headers.get("sec-ch-prefers-color-scheme")
            or ""
        ).lower()
        if pref in ("light", "dark"):
            return pref

    # Fallback Windows Registry: AppsUseLightTheme (1 = light, 0 = dark)
    if os.name == "nt":
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if int(val) == 1 else "dark"
        except Exception:
            pass

    return "light"


def sanitize_hex_color(color: str, default: str = "18181B") -> str:
    """Retorna código HEX de 6 dígitos maiúsculo sem '#' para uso no pacote xcolor do LaTeX."""
    if not color:
        return default
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", color.strip())
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    return cleaned[:6].upper() if len(cleaned) >= 6 else default


def apply_custom_colors_and_portfolio_to_latex(
    latex_code: str,
    primary_color: str = "#18181B",
    secondary_color: str = "#3F3F46",
    portfolio_url: str = "",
    lang: str = "pt-br",
) -> str:
    """Aplica as cores customizadas pelo usuário e o link de Portfólio ao código LaTeX."""
    p_hex = sanitize_hex_color(primary_color, "18181B")
    s_hex = sanitize_hex_color(secondary_color, "3F3F46")

    out = latex_code
    # Substitui definições de cores primárias e secundárias nos modelos integrados
    out = re.sub(r"\\definecolor\{(accent|acadnavy|primary)\}\{(?:HTML|RGB|rgb)\}\{[^}]+\}", rf"\\definecolor{{\1}}{{HTML}}{{{p_hex}}}", out)
    out = re.sub(r"\\definecolor\{(sidecolor|secondary|subaccent)\}\{(?:HTML|RGB|rgb)\}\{[^}]+\}", rf"\\definecolor{{\1}}{{HTML}}{{{s_hex}}}", out)

    # Garante que acadnavy e subaccent/sidecolor estejam definidos e sincronizados
    if "\\definecolor{acadnavy}" in out and "\\definecolor{subaccent}" not in out:
        out = re.sub(
            r"(\\definecolor\{acadnavy\}\{HTML\}\{[0-9A-Fa-f]{6}\})",
            rf"\1\n\\definecolor{{subaccent}}{{HTML}}{{{s_hex}}}\n\\definecolor{{sidecolor}}{{HTML}}{{{s_hex}}}",
            out,
        )
        out = re.sub(
            r"\\titleformat\{\\section\}\{\\normalsize\\bfseries\\scshape\\color\{acadnavy\}\}\{\}\{0em\}\{\}\[\\vspace\{1pt\}\\titlerule\]",
            rf"\\titleformat{{\\section}}{{\\normalsize\\bfseries\\scshape\\color{{acadnavy}}}}{{}}{{0em}}{{}}[\\vspace{{1pt}}{{\\color{{subaccent}}\\titlerule[0.8pt]}}]",
            out,
        )
        out = out.replace(r"{\large\itshape ", r"{\large\itshape\color{subaccent} ")

    # No modelo minimal_ats (que não tinha cor nos títulos), adiciona a cor escolhida pelo usuário
    if "\\definecolor{accent}" not in out and "\\definecolor{acadnavy}" not in out and "\\usepackage{xcolor}" not in out:
        out = out.replace(
            "\\usepackage{graphicx}",
            f"\\usepackage{{xcolor}}\n\\definecolor{{accent}}{{HTML}}{{{p_hex}}}\n\\definecolor{{subaccent}}{{HTML}}{{{s_hex}}}\n\\usepackage{{graphicx}}",
        )
        out = out.replace(
            r"\titleformat{\section}{\normalsize\bfseries\scshape}",
            r"\titleformat{\section}{\normalsize\bfseries\scshape\color{accent}}",
        )
    else:
        # Aplica cor secundária ao nome no cabeçalho quando disponível
        if "\\definecolor{subaccent}" not in out and "\\usepackage{xcolor}" in out:
            out = out.replace(
                "\\pagestyle{empty}",
                f"\\definecolor{{subaccent}}{{HTML}}{{{s_hex}}}\n\\pagestyle{{empty}}",
            )
            out = out.replace(r"{\large\itshape ", r"{\large\itshape\color{subaccent} ")

    # Injeta link clicável para a página de Portfólio no cabeçalho se fornecido e ainda não presente
    if portfolio_url and portfolio_url.strip():
        u = portfolio_url.strip()
        if not u.startswith(("http://", "https://")):
            u = "https://" + u
        u_safe = u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
        # Se a URL já estiver presente no documento (ex.: renderizada nativamente no cabeçalho), não duplica
        if u in out or u_safe in out:
            return out

        clean_disp = re.sub(r"^https?://(www\.)?", "", u, flags=re.IGNORECASE).rstrip("/") or "portfolio"
        port_link = rf"\href{{{u_safe}}}{{\faIcon{{globe}}\ \textbf{{{clean_disp}}}}}"

        # Tenta inserir antes do LinkedIn (entre Localização e LinkedIn)
        inserted = False
        m_li = re.search(r"(\\href\{[^{}]+\}\{\\faIcon\{linkedin\}[^{}]*\})", out)
        if m_li:
            target = m_li.group(1)
            sep = " \\;|\\; " if "\\;|\\;" in out else (" \\;\\textbullet\\; " if "\\textbullet" in out else " | ")
            out = out.replace(target, f"{port_link}{sep}{target}", 1)
            inserted = True
        if not inserted:
            for anchor in (r"{\textbf{LinkedIn}}", r"{\textbf{GitHub}}", r"{\textbf{ORCID}}"):
                if anchor in out:
                    sep = " \\;|\\; " if "\\;|\\;" in out else (" \\;\\textbullet\\; " if "\\textbullet" in out else " | ")
                    out = out.replace(anchor, f"{port_link}{sep}{anchor}", 1)
                    inserted = True
                    break
        if not inserted:
            m = list(re.finditer(r"\\href\{[^{}]+\}\{\\faIcon\{(?:github|linkedin|orcid|graduation-cap)\}[^{}]*\}", out))
            if m:
                last_match = m[-1].group(0)
                sep = " \\;|\\; " if "\\;|\\;" in out else (" \\;\\textbullet\\; " if "\\textbullet" in out else " | ")
                out = out.replace(last_match, f"{last_match}{sep}{port_link}", 1)
                inserted = True
        if not inserted and r"\end{center}" in out:
            out = out.replace(r"\end{center}", f"\\\\[2pt] {{\\small {port_link}}}\n\\end{{center}}", 1)

    return out


def render_template_preview_html(
    template_id: str,
    primary_color: str = "#18181B",
    secondary_color: str = "#3F3F46",
    lang: str = "pt-br",
    has_photo: bool = True,
) -> str:
    """Gera um preview visual interativo em HTML/SVG de alta fidelidade do modelo LaTeX e cores selecionadas."""
    is_en = str(lang).lower().startswith("en")
    p_col = primary_color if primary_color.startswith("#") else f"#{primary_color}"
    s_col = secondary_color if secondary_color.startswith("#") else f"#{secondary_color}"

    lbl_exp = "PROFESSIONAL EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
    lbl_edu = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
    lbl_pub = "SCIENTIFIC PUBLICATIONS" if is_en else "PRODUÇÃO CIENTÍFICA"
    lbl_sk = "SKILLS & STACK" if is_en else "COMPETÊNCIAS"
    lbl_cnt = "CONTACT & LINKS" if is_en else "CONTATO & PERFIS"
    role_txt = "Senior AI & Software Architect" if is_en else "Arquiteto de Software & IA Sênior"

    photo_circle = (
        f'<div style="width:42px;height:42px;border-radius:8px;background:linear-gradient(135deg,{p_col},{s_col});'
        f'display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:15px;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.15);flex-shrink:0;">👤</div>'
        if has_photo
        else ""
    )

    if template_id == "tech_sidebar":
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:14px;font-family:'Segoe UI',system-ui,sans-serif;
                    font-size:11px;line-height:1.35;min-height:255px;display:flex;gap:12px;">
            <div style="width:33%;border-right:1.5px solid #e2e8f0;padding-right:10px;">
                <div style="display:flex;justify-content:center;margin-bottom:8px;">{photo_circle}</div>
                <div style="font-weight:800;font-size:13px;color:{s_col};">Lucas Silva</div>
                <div style="font-style:italic;font-size:10px;color:{p_col};margin-bottom:8px;">{role_txt}</div>
                <div style="font-weight:700;font-size:9px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:4px;">{lbl_cnt}</div>
                <div style="font-size:9px;color:#475569;">• 📍 São Paulo, BR • 🌐 portfolio.dev<br>• 🔗 in/lucassilva • 🐙 lucassilva</div>
                <div style="font-weight:700;font-size:9px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin:8px 0 4px 0;">{lbl_sk}</div>
                <div style="font-size:9px;color:#475569;">Python, LaTeX, PyTorch, Cloud, Docker</div>
            </div>
            <div style="width:67%;">
                <div style="font-weight:700;font-size:10px;color:{p_col};border-bottom:1.5px solid {p_col};padding-bottom:2px;margin-bottom:6px;">{lbl_exp}</div>
                <div style="display:flex;justify-content:space-between;font-weight:700;font-size:10px;color:{s_col};">
                    <span>Lead AI Engineer — Tech Corp</span><span style="color:#64748b;font-weight:400;">2023–Present</span>
                </div>
                <div style="font-size:9.5px;color:#334155;margin:3px 0 8px 8px;">• Token-efficient LLM pipelines (-78% cost)<br>• High-throughput LaTeX automation</div>
                <div style="font-weight:700;font-size:10px;color:{p_col};border-bottom:1.5px solid {p_col};padding-bottom:2px;margin-bottom:6px;">{lbl_edu}</div>
                <div style="display:flex;justify-content:space-between;font-weight:700;font-size:10px;color:{s_col};">
                    <span>M.Sc. Computer Science</span><span style="color:#64748b;font-weight:400;">2021–2023</span>
                </div>
                <div style="font-size:9.5px;color:#475569;margin-top:2px;">Universidade de São Paulo (USP)</div>
            </div>
        </div>
        """

    if template_id == "academic_classic":
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:15px;font-family:'Georgia',serif;
                    font-size:11px;line-height:1.35;min-height:255px;">
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1.5px solid {p_col};padding-bottom:8px;margin-bottom:8px;">
                <div>
                    <div style="font-weight:700;font-size:15px;color:{p_col};">Lucas Silva</div>
                    <div style="font-style:italic;font-size:10.5px;color:{s_col};">Postdoctoral Researcher in Artificial Intelligence</div>
                    <div style="font-size:9px;color:#475569;margin-top:3px;">📍 São Paulo, BR • 🌐 portfolio.dev • 🔗 in/lucassilva • 🐙 lucassilva • 🆔 0000-0002-1825-0097</div>
                </div>
                {photo_circle}
            </div>
            <div style="font-weight:700;font-size:10px;letter-spacing:0.6px;color:{p_col};border-bottom:1px solid #cbd5e1;padding-bottom:2px;margin-bottom:5px;">{lbl_edu}</div>
            <div style="display:flex;justify-content:space-between;font-size:10px;">
                <b>Ph.D. in Computer Science — USP</b><i>2020–2024</i>
            </div>
            <div style="font-weight:700;font-size:10px;letter-spacing:0.6px;color:{p_col};border-bottom:1px solid #cbd5e1;padding-bottom:2px;margin:8px 0 5px 0;">{lbl_pub}</div>
            <div style="font-size:9.5px;color:#334155;">
                1. SILVA, L.; COSTA, H. <b>Token-Efficient Reasoning in LLMs</b>. <i>JAIR</i>, 2025. <span style="color:{p_col};">DOI:10.1000/jair</span><br>
                2. SILVA, L. <b>Graph Neural Networks in Bioinformatics</b>. <i>Nature Mach. Intell.</i>, 2024.
            </div>
        </div>
        """

    if template_id == "minimal_ats":
        return f"""
        <div style="background:#ffffff;color:#18181b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:15px;font-family:'Arial',sans-serif;
                    font-size:11px;line-height:1.35;min-height:255px;">
            <div style="text-align:center;border-bottom:1.5px solid {p_col};padding-bottom:7px;margin-bottom:8px;">
                <div style="font-weight:800;font-size:15px;color:{p_col};">LUCAS SILVA</div>
                <div style="font-size:10px;color:{s_col};">{role_txt}</div>
                <div style="font-size:9px;color:#52525b;margin-top:2px;">São Paulo, BR | 🌐 portfolio.dev | 🔗 in/lucassilva | 🐙 lucassilva | 🆔 0000-0002-1825-0097</div>
            </div>
            <div style="font-weight:800;font-size:9.5px;color:{p_col};border-bottom:1px solid {p_col};margin-bottom:5px;">{lbl_exp}</div>
            <div style="display:flex;justify-content:space-between;font-size:10px;font-weight:700;">
                <span>Senior Software Engineer — Global Systems</span><span>2022–Present</span>
            </div>
            <div style="font-size:9.5px;color:#27272a;margin:2px 0 8px 10px;">• Architected distributed microservices handling 50k req/s<br>• Automated CI/CD & LaTeX document pipelines</div>
            <div style="font-weight:800;font-size:9.5px;color:{p_col};border-bottom:1px solid {p_col};margin-bottom:5px;">{lbl_sk}</div>
            <div style="font-size:9.5px;color:#27272a;"><b>Languages & Tools:</b> Python, Go, TypeScript, PostgreSQL, Kubernetes, AWS</div>
        </div>
        """

    if template_id == "overleaf_russell_ti":
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:15px;font-family:'Roboto','Segoe UI',sans-serif;
                    font-size:11px;line-height:1.35;min-height:255px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                {photo_circle}
                <div style="flex:1;text-align:center;">
                    <div><span style="font-size:15px;color:#64748b;font-weight:300;">Lucas</span> <span style="font-size:15px;color:{s_col};font-weight:800;">Silva</span></div>
                    <div style="font-size:9px;color:#475569;margin-top:2px;">🐙 lucassilva | 🆔 0000-0002-1825-0097 | 🎓 1234567890123456</div>
                    <div style="font-size:9px;color:#475569;">✉️ lucas@email.com | 📱 WhatsApp | 📍 São Paulo, BR | 🌐 portfolio.dev | 🔗 in/lucassilva</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                <span style="font-weight:800;font-size:11px;"><span style="color:{p_col};">Per</span><span style="color:{s_col};">fil</span></span>
                <div style="flex:1;height:1px;background:#94a3b8;"></div>
            </div>
            <div style="font-size:9.5px;color:#334155;margin-bottom:6px;">Engenheiro de Software & IA com foco em UX Design, Segurança e LLMOps.</div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                <span style="font-weight:800;font-size:11px;"><span style="color:{p_col};">Hab</span><span style="color:{s_col};">ilidades</span></span>
                <div style="flex:1;height:1px;background:#94a3b8;"></div>
            </div>
            <div style="font-size:9.5px;color:#334155;margin-bottom:6px;"><b>Programação:</b> Python, C/C++, JS, SQL &nbsp;•&nbsp; <b>Ferramentas:</b> Linux, LaTeX, Git</div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                <span style="font-weight:800;font-size:11px;"><span style="color:{p_col};">Idi</span><span style="color:{s_col};">omas</span></span>
                <div style="flex:1;height:1px;background:#94a3b8;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:9.5px;">
                <span><b>Português</b> (Nativo)</span><span style="color:{p_col};">● ● ● ● ● ●</span>
            </div>
        </div>
        """

    if template_id == "overleaf_awesome_cv":
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:15px;font-family:'Roboto','Segoe UI',sans-serif;
                    font-size:11px;line-height:1.35;min-height:255px;display:flex;flex-direction:column;justify-content:space-between;">
            <div>
                <div style="text-align:center;margin-bottom:8px;">
                    <div><span style="font-size:16px;color:#64748b;font-weight:300;">Lucas</span> <span style="font-size:16px;color:{s_col};font-weight:800;">Silva</span></div>
                    <div style="font-size:9.5px;font-variant:small-caps;color:{p_col};font-weight:700;">{role_txt}</div>
                    <div style="font-size:8.5px;color:#64748b;margin-top:2px;">📱 Phone &nbsp;|&nbsp; ✉️ Email &nbsp;|&nbsp; 📍 São Paulo, BR &nbsp;|&nbsp; 🌐 portfolio.dev &nbsp;|&nbsp; 🔗 in/lucassilva &nbsp;|&nbsp; 🐙 lucassilva</div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-weight:800;font-size:11px;"><span style="color:{p_col};">Ski</span><span style="color:{s_col};">lls</span></span>
                    <div style="flex:1;height:1px;background:#94a3b8;"></div>
                </div>
                <div style="font-size:9.5px;color:#334155;margin-bottom:6px;"><b>Backend & AI:</b> Python, LaTeX, FastAPI, NVIDIA NIM, Docker</div>
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-weight:800;font-size:11px;"><span style="color:{p_col};">Exp</span><span style="color:{s_col};">erience</span></span>
                    <div style="flex:1;height:1px;background:#94a3b8;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:9.5px;font-weight:700;color:{s_col};">
                    <span>Senior Software Engineer</span><span style="color:{p_col};font-style:italic;">2023–Present</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:8px;color:#94a3b8;border-top:1px solid #f1f5f9;padding-top:4px;margin-top:6px;">
                <span>2026</span><span>Lucas Silva · Résumé</span><span>1</span>
            </div>
        </div>
        """

    if template_id == "overleaf_single_page_keywords":
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:14px;font-family:'Raleway','Segoe UI',sans-serif;
                    font-size:10.5px;line-height:1.3;min-height:255px;">
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #cbd5e1;padding-bottom:6px;margin-bottom:6px;">
                <div>
                    <div style="font-size:14px;font-weight:900;color:{s_col};line-height:1;">LUCAS <span style="font-weight:300;color:{p_col};">SILVA</span></div>
                    <div style="font-size:9px;color:{s_col};margin-top:2px;">{role_txt}</div>
                </div>
                <div style="text-align:right;font-size:8.5px;color:#475569;">
                    Location <b>São Paulo, BR</b><br>Web <b>portfolio.dev</b><br>LinkedIn <b>in/lucassilva</b><br>GitHub <b>lucassilva</b>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:5px;margin-bottom:4px;">
                <span style="background:{s_col};color:#fff;border-radius:50%;width:15px;height:15px;display:inline-flex;align-items:center;justify-content:center;font-size:8px;">📄</span>
                <span style="font-weight:800;font-size:10px;color:{p_col};">SUMMARY</span>
            </div>
            <div style="font-size:9px;color:#334155;margin-bottom:6px;">Generalist software engineer & AI researcher specialized in Python and deep learning.</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div>
                    <div style="display:flex;align-items:center;gap:4px;margin-bottom:3px;">
                        <span style="background:{s_col};color:#fff;border-radius:50%;width:14px;height:14px;display:inline-flex;align-items:center;justify-content:center;font-size:7px;">✏️</span>
                        <span style="font-weight:800;font-size:9.5px;color:{p_col};">WORK</span>
                    </div>
                    <div style="font-size:8.5px;"><b>ML Engineer / 2023–Now</b><br><i>Keywords: Python, PyTorch, LaTeX</i></div>
                </div>
                <div>
                    <div style="display:flex;align-items:center;gap:4px;margin-bottom:3px;">
                        <span style="background:{s_col};color:#fff;border-radius:50%;width:14px;height:14px;display:inline-flex;align-items:center;justify-content:center;font-size:7px;">🎓</span>
                        <span style="font-weight:800;font-size:9.5px;color:{p_col};">EDUCATION</span>
                    </div>
                    <div style="font-size:8.5px;"><b>M.Sc. Robotics & AI</b><br>Thesis on Deep Neural Networks</div>
                </div>
            </div>
        </div>
        """

    if template_id in ("nico_krieger", "modelo_nico_krieger"):
        return f"""
        <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);overflow:hidden;font-family:'Segoe UI',sans-serif;
                    font-size:10.5px;line-height:1.3;min-height:255px;">
            <div style="background:#212529;color:#ffffff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:15px;font-weight:900;letter-spacing:0.5px;">LUCAS SILVA</div>
                    <div style="font-size:9.5px;color:#e2e8f0;margin-top:2px;">{role_txt}</div>
                    <div style="font-size:8px;color:#94a3b8;margin-top:2px;">Especialista em microsserviços e sistemas distribuídos de alta disponibilidade.</div>
                </div>
                {photo_circle}
            </div>
            <div style="display:flex;min-height:180px;">
                <div style="width:34%;background:#f8f9fa;border-right:1px solid #e2e8f0;padding:10px 10px;font-size:8.5px;color:#334155;">
                    <div style="font-weight:800;font-size:9px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:4px;">CONTATO</div>
                    <div style="line-height:1.45;margin-bottom:8px;">
                        ✉️ lucas@email.com<br>
                        📱 +55 11 99999-8888<br>
                        📍 São Paulo, SP<br>
                        🌐 portfolio.dev<br>
                        🔗 in/lucassilva<br>
                        🐙 lucassilva
                    </div>
                    <div style="font-weight:800;font-size:9px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:4px;">HABILIDADES</div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Python</span><span style="color:{p_col};">● ● ● ● ●</span></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Docker</span><span style="color:{p_col};">● ● ● ● ○</span></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span>AWS</span><span style="color:{p_col};">● ● ● ○ ○</span></div>
                    <div style="font-weight:800;font-size:9px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:4px;">IDIOMAS</div>
                    <div style="display:flex;justify-content:space-between;"><span>Português</span><span style="color:{p_col};">● ● ● ● ● ●</span></div>
                    <div style="display:flex;justify-content:space-between;"><span>Inglês</span><span style="color:{p_col};">● ● ● ● ○ ○</span></div>
                </div>
                <div style="width:66%;padding:10px 12px;font-size:9px;">
                    <div style="font-weight:800;font-size:9.5px;color:{p_col};border-bottom:1px solid #cbd5e1;padding-bottom:2px;margin-bottom:4px;">EXPERIÊNCIA PROFISSIONAL</div>
                    <div style="display:flex;justify-content:space-between;font-weight:700;color:#0f172a;">
                        <span>Lead Software Architect</span><span style="color:#64748b;font-size:8px;">2021–Presente</span>
                    </div>
                    <div style="color:{p_col};font-weight:600;font-size:8.5px;margin-bottom:2px;">Tech Innovations Inc.</div>
                    <div style="color:#334155;font-size:8.5px;margin-bottom:6px;">
                        • Liderança técnica de microsserviços atendendo 5M de requisições diárias.<br>
                        • Redução de latência em 40% com cache Redis e mensageria distribuída.
                    </div>
                    <div style="font-weight:800;font-size:9.5px;color:{p_col};border-bottom:1px solid #cbd5e1;padding-bottom:2px;margin-bottom:4px;">FORMAÇÃO ACADÊMICA</div>
                    <div style="font-weight:700;color:#0f172a;">Bacharelado em Ciência da Computação</div>
                    <div style="color:#64748b;font-size:8px;">Universidade de São Paulo (USP) · 2017–2021</div>
                </div>
            </div>
        </div>
        """

    if template_id == "google_standard":
        return f"""
        <div style="background:#ffffff;color:#1f1f1f;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:14px;font-family:'Segoe UI',system-ui,sans-serif;
                    font-size:10.5px;line-height:1.3;min-height:255px;">
            <div style="text-align:center;border-bottom:1.5px solid {p_col};padding-bottom:5px;margin-bottom:6px;">
                <div style="font-weight:800;font-size:15px;color:{s_col};letter-spacing:-0.2px;">LUCAS SILVA</div>
                <div style="font-size:9.5px;color:{p_col};font-weight:600;">{role_txt}</div>
                <div style="font-size:8.5px;color:#444746;margin-top:2px;">📍 São Paulo, Brazil &nbsp;|&nbsp; 🌐 portfolio.dev &nbsp;|&nbsp; 🔗 in/lucassilva &nbsp;|&nbsp; 🐙 lucassilva</div>
            </div>
            <div style="font-weight:800;font-size:9.5px;color:{s_col};border-bottom:1px solid {p_col};margin-bottom:4px;letter-spacing:0.5px;">EXPERIENCE</div>
            <div style="display:flex;justify-content:space-between;font-size:9.5px;font-weight:700;color:{s_col};">
                <span>Google &nbsp;—&nbsp; Senior Software Engineer</span><span style="color:#444746;">2022–Present</span>
            </div>
            <div style="font-size:9px;color:#334155;margin:2px 0 6px 8px;">
                • Designed distributed caching architecture reducing P99 latency by 42% across 10M daily active users.<br>
                • Built deterministic resume synthesis pipeline saving 78% tokens via NVIDIA NIM.
            </div>
            <div style="font-weight:800;font-size:9.5px;color:{s_col};border-bottom:1px solid {p_col};margin-bottom:4px;letter-spacing:0.5px;">EDUCATION</div>
            <div style="display:flex;justify-content:space-between;font-size:9.5px;font-weight:700;color:{s_col};">
                <span>Universidade de São Paulo (USP)</span><span style="color:#444746;">2018–2022</span>
            </div>
            <div style="font-size:9px;color:#475569;font-style:italic;">B.S. in Computer Science — GPA: 3.9/4.0</div>
            <div style="font-weight:800;font-size:9.5px;color:{s_col};border-bottom:1px solid {p_col};margin:6px 0 4px 0;letter-spacing:0.5px;">TECHNICAL SKILLS</div>
            <div style="font-size:9px;color:#334155;"><b>Languages & Cloud:</b> Python, Go, C++, SQL, TypeScript, GCP, Docker, Kubernetes</div>
        </div>
        """

    if template_id == "ai_ats_max":
        return f"""
        <div style="background:#ffffff;color:#0f172a;border-radius:10px;border:1px solid #cbd5e1;
                    box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:14px;font-family:'Segoe UI',sans-serif;
                    font-size:10.5px;line-height:1.3;min-height:255px;">
            <div style="text-align:center;border-bottom:1.5px solid {s_col};padding-bottom:5px;margin-bottom:6px;">
                <div style="font-weight:900;font-size:15px;color:{s_col};">LUCAS SILVA</div>
                <div style="font-size:9.5px;font-weight:700;color:{p_col};">{role_txt.upper()}</div>
                <div style="font-size:8px;color:#334155;margin-top:2px;">LOCATION: São Paulo, BR &nbsp;|&nbsp; PORTFOLIO: portfolio.dev &nbsp;|&nbsp; LINKEDIN: in/lucassilva &nbsp;|&nbsp; GITHUB: lucassilva</div>
            </div>
            <div style="font-weight:800;font-size:9px;color:{s_col};border-bottom:1px solid #cbd5e1;margin-bottom:3px;">CORE COMPETENCIES & KEYWORDS</div>
            <div style="font-size:8.5px;color:#1e293b;margin-bottom:5px;">
                • <b>AI & LLMs:</b> RAG, Fine-Tuning, NVIDIA NIM, PyTorch, Embeddings, Prompt Engineering<br>
                • <b>Backend & Cloud:</b> Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS/GCP, CI/CD
            </div>
            <div style="font-weight:800;font-size:9px;color:{s_col};border-bottom:1px solid #cbd5e1;margin-bottom:3px;">PROFESSIONAL EXPERIENCE</div>
            <div style="display:flex;justify-content:space-between;font-size:9px;font-weight:700;">
                <span>Lead AI Architect | Enterprise Systems</span><span>2023–Present</span>
            </div>
            <div style="font-size:8.5px;color:#334155;margin:1px 0 5px 6px;">
                • Architected neural parsing pipelines processing 2M docs/day with 99.9% uptime.<br>
                • Engineered zero-leakage TLS 1.3 token vault for enterprise LLM infrastructure.
            </div>
            <div style="font-weight:800;font-size:9px;color:{s_col};border-bottom:1px solid #cbd5e1;margin-bottom:3px;">EDUCATION</div>
            <div style="font-size:8.5px;"><b>B.S. in Computer Science</b> — Universidade Federal (2018–2022)</div>
        </div>
        """

    # Default: modern_pro
    return f"""
    <div style="background:#ffffff;color:#1e293b;border-radius:10px;border:1px solid #cbd5e1;
                box-shadow:0 6px 18px rgba(15,23,42,0.08);padding:15px;font-family:'Segoe UI',system-ui,sans-serif;
                font-size:11px;line-height:1.35;min-height:255px;">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {p_col};padding-bottom:8px;margin-bottom:8px;">
            <div>
                <div style="font-weight:800;font-size:15px;color:{p_col};">Lucas Silva</div>
                <div style="font-style:italic;font-size:10.5px;color:{s_col};">{role_txt}</div>
                <div style="font-size:9px;color:#475569;margin-top:3px;">📍 São Paulo • 🌐 portfolio.dev • 🔗 in/lucassilva • 🐙 lucassilva • 🆔 0000-0002-1825-0097 • 🎓 1234567890123456</div>
            </div>
            {photo_circle}
        </div>
        <div style="font-weight:700;font-size:10.5px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:5px;">{lbl_exp}</div>
        <div style="display:flex;justify-content:space-between;font-size:10px;font-weight:700;color:{s_col};">
            <span>Senior AI Engineer — NVIDIA NIM Partner</span><span style="color:#64748b;">2023–Present</span>
        </div>
        <div style="font-size:9.5px;color:#334155;margin:3px 0 8px 10px;">
            • Reduced LLM token consumption by 78% using TOON & Caveman plugins<br>
            • Built automated multi-source LaTeX resume synthesis engine
        </div>
        <div style="font-weight:700;font-size:10.5px;color:{p_col};border-bottom:1px solid {p_col};padding-bottom:2px;margin-bottom:5px;">{lbl_sk}</div>
        <div style="font-size:9.5px;color:#334155;"><b>Core Stack:</b> Python, LaTeX, FastAPI, Streamlit, LLMOps, Docker</div>
    </div>
    """


def get_theme_css(theme_mode: str = "light", primary_color: str = "#18181B") -> str:
    """Gera folha de estilos CSS moderna e responsiva para Modo Claro (Light) ou Modo Escuro (Dark)."""
    is_light = theme_mode == "light"
    bg_main = "#F8FAFC" if is_light else "#0B0F19"
    bg_sidebar = "#FFFFFF" if is_light else "#111827"
    bg_card = "#FFFFFF" if is_light else "#1E293B"
    text_main = "#0F172A" if is_light else "#F8FAFC"
    text_muted = "#475569" if is_light else "#94A3B8"
    border_col = "#E2E8F0" if is_light else "#334155"
    input_bg = "#FFFFFF" if is_light else "#0F172A"
    shadow = "0 4px 14px rgba(15, 23, 42, 0.05)" if is_light else "0 4px 18px rgba(0, 0, 0, 0.35)"

    return f"""
    <style>
        .stApp {{
            background-color: {bg_main} !important;
            color: {text_main} !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: {bg_sidebar} !important;
            border-right: 1px solid {border_col} !important;
        }}
        section[data-testid="stSidebar"] * {{
            color: {text_main};
        }}
        .stMarkdown, .stText, h1, h2, h3, h4, p, label, .stCaption {{
            color: {text_main} !important;
        }}
        div[data-testid="stMetric"] {{
            background-color: {bg_card} !important;
            border: 1px solid {border_col} !important;
            border-left: 4px solid {primary_color} !important;
            border-radius: 10px !important;
            padding: 12px 14px !important;
            box-shadow: {shadow} !important;
        }}
        div[data-testid="stExpander"] {{
            background-color: {bg_card} !important;
            border: 1px solid {border_col} !important;
            border-radius: 10px !important;
            box-shadow: {shadow} !important;
        }}
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            border-color: {border_col} !important;
            color: {text_main} !important;
            border-radius: 8px !important;
        }}
        input, textarea {{
            color: {text_main} !important;
        }}
        .ui-card {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: {shadow};
        }}
        .ui-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            background-color: {primary_color}20;
            color: {primary_color};
            border: 1px solid {primary_color}50;
            margin-right: 6px;
        }}
        .ui-subtitle {{
            color: {text_muted} !important;
            font-size: 0.92rem;
        }}
        button[kind="primary"] {{
            background: linear-gradient(135deg, {primary_color}, #2563EB) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            padding: 0.65rem 1.2rem !important;
            box-shadow: 0 4px 12px {primary_color}45 !important;
            min-height: 44px !important;
        }}
        .st-brand-logo {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(15, 76, 129, 0.25);
            object-fit: cover;
        }}

        /* Mobile & Tablet Responsiveness */
        @media (max-width: 820px) {{
            .block-container {{
                padding: 1.25rem 0.85rem 3rem 0.85rem !important;
            }}
            .ui-card {{
                padding: 12px !important;
                margin-bottom: 12px !important;
            }}
            div[data-testid="column"] {{
                min-width: 100% !important;
                margin-bottom: 0.75rem !important;
            }}
            button[kind="primary"], button[kind="secondary"] {{
                min-height: 44px !important;
                width: 100% !important;
            }}
            div[data-testid="stMetric"] {{
                padding: 10px 12px !important;
            }}
        }}
    </style>
    """
