"""Modelos de Currículo LaTeX integrados (Bilíngues: pt-BR e en-US) e motor de renderização determinístico.

Ao renderizar os templates integrados localmente a partir do JSON compacto gerado
pela API NVIDIA NIM, economizamos ~1.800 tokens de preâmbulo LaTeX por chamada
e garantimos compilação 100% livre de erros de sintaxe no `pdflatex`.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List

from .i18n import LATEX_I18N, normalize_lang
from .extractors import (
    parse_github_input,
    parse_lattes_input,
    parse_linkedin_input,
    parse_orcid_input,
    parse_scholar_input,
)

BUILTIN_TEMPLATES: Dict[str, Dict[str, str]] = {
    "modern_pro": {
        "id": "modern_pro",
        "name": "Moderno Executivo (Profissional & Tech) / Executive Modern",
        "recommended_for": "profissional",
        "description": (
            "Layout executivo moderno em coluna única com destaques em azul-petróleo, "
            "cabeçalho com foto opcional e links clicáveis (LinkedIn, GitHub, ORCID, Lattes)."
        ),
    },
    "academic_classic": {
        "id": "academic_classic",
        "name": "Acadêmico Clássico (Pesquisador / Pós-Graduação) / Academic Classic",
        "recommended_for": "academico",
        "description": (
            "Estrutura acadêmica formal com foco em Formação, Produção Bibliográfica (DOI), "
            "Projetos de Pesquisa, Docência, Prêmios, Lattes e ORCID."
        ),
    },
    "tech_sidebar": {
        "id": "tech_sidebar",
        "name": "Tech & Engenharia Duas Colunas (Barra Lateral) / Tech Sidebar",
        "recommended_for": "profissional",
        "description": (
            "Design assimétrico de duas colunas com foto, contatos, stack técnica e idiomas "
            "na coluna lateral e experiências/projetos na coluna principal."
        ),
    },
    "minimal_ats": {
        "id": "minimal_ats",
        "name": "Minimalista ATS-Friendly (Alta Densidade) / Minimalist ATS",
        "recommended_for": "profissional",
        "description": (
            "Tipografia clássica de alto contraste otimizada para sistemas corporativos ATS "
            "e leitura rápida por recrutadores."
        ),
    },
    "overleaf_russell_ti": {
        "id": "overleaf_russell_ti",
        "name": "Modelo Russell (Currículo T.I.) / Russell Model",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/read/rgfqqnnynrmv#d5b171",
        "description": (
            "Modelo Overleaf Russell CV (Currículo T.I.) com foto lateral no cabeçalho, ícones FontAwesome 5, "
            "títulos com destaque nas 3 primeiras letras, tabela de habilidades e níveis de idiomas em círculos."
        ),
    },
    "overleaf_awesome_cv": {
        "id": "overleaf_awesome_cv",
        "name": "Awesome CV (Jason Richards) / Awesome CV",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc",
        "description": (
            "Modelo Overleaf Jason Richards' Résumé baseado no clássico Awesome-CV com cabeçalho centralizado, "
            "tipografia Roboto + Source Sans Pro, destaque de 3 letras nas seções e rodapé executivo."
        ),
    },
    "overleaf_single_page_keywords": {
        "id": "overleaf_single_page_keywords",
        "name": "Single Page + Keywords / Single Page + Keywords",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk",
        "description": (
            "Modelo Overleaf de página única em duas colunas (Primož Godec & Salman Maqbool) com fonte Raleway, "
            "ícones circulares TikZ, seção de Resumo e palavras-chave (Keywords) de stack por experiência."
        ),
    },
    "nico_krieger": {
        "id": "nico_krieger",
        "name": "Modelo Nico Krieger (Duas Colunas & Header Escuro) / Nico Krieger",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny",
        "description": (
            "Modelo baseado no my-resume de Nico Krieger com cabeçalho escuro de largura total, "
            "barra lateral destacada para contatos, habilidades avaliadas em 5 pontos e idiomas, e coluna principal para realizações."
        ),
    },
    "google_standard": {
        "id": "google_standard",
        "name": "Padrão Google (Big Tech / SWE) / Google Standard",
        "recommended_for": "profissional",
        "description": (
            "Modelo padrão de recrutamento Big Tech (Google SWE / Gayle Laakmann McDowell). "
            "Página única densa, margens de 0.5 polegadas, estrutura XYZ de realizações e formatação clean."
        ),
    },
    "ai_ats_max": {
        "id": "ai_ats_max",
        "name": "Otimizado para IA & ATS (Máxima Legibilidade) / AI & ATS Max-Readability",
        "recommended_for": "profissional",
        "description": (
            "Desenvolvido especificamente para triagem automatizada por LLMs (Gemini, Claude, GPT) e sistemas ATS. "
            "Fluxo textual 100% linear, metadados semânticos, matriz de competências e compatibilidade Unicode nativa."
        ),
    },
}


def escape_latex(text: Any) -> str:
    """Escapa caracteres especiais do LaTeX preservando acentuação UTF-8."""
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    s = (
        s.replace("\u2013", "--")
        .replace("\u2014", "---")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", "``")
        .replace("\u201d", "''")
        .replace("\u2026", "...")
        .replace("\u00a0", " ")
    )
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))
    return pattern.sub(lambda m: replacements[m.group(0)], s)


def escape_url(url: str) -> str:
    """Prepara uma URL para uso seguro dentro de \\href{url}{label}."""
    if not url:
        return ""
    u = url.strip()
    if not u.startswith(("http://", "https://", "mailto:")):
        if "@" in u and "/" not in u:
            return u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
        u = "https://" + u
    return u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")



def abbreviate_researcher_name(name: str) -> str:
    """Abrevia o nome do pesquisador no formato acadêmico padrão (ex: 'João Lucas Mayrinck' -> 'J. L. Mayrinck')."""
    if not name or not str(name).strip():
        return ""
    parts = str(name).strip().split()
    if len(parts) <= 1:
        return parts[0]

    preps = {"de", "da", "do", "das", "dos", "e", "van", "von", "del", "di"}
    last = parts[-1]
    first_parts = parts[:-1]

    initials: List[str] = []
    for p in first_parts:
        clean = p.strip()
        if clean.lower() in preps:
            continue
        if clean.endswith("."):
            initials.append(clean)
        else:
            initials.append(f"{clean[0].upper()}.")

    if initials:
        return f"{' '.join(initials)} {last}"
    return last


def _get_platform_display(links: Dict[str, str], platform: str, candidate_name: str = "") -> str:
    """Retorna o nick (GitHub/LinkedIn), ID (Lattes/ORCID) ou nome abreviado (Scholar) para exibição ao lado do ícone."""
    if platform == "github":
        if links.get("github_nick"):
            return str(links["github_nick"]).strip()
        val = str(links.get("github") or "").strip()
        if val:
            _, nick = parse_github_input(val)
            return nick or val
        return "GitHub"

    if platform == "linkedin":
        if links.get("linkedin_nick"):
            return str(links["linkedin_nick"]).strip()
        val = str(links.get("linkedin") or "").strip()
        if val:
            _, nick = parse_linkedin_input(val)
            return nick or val
        return "LinkedIn"

    if platform == "orcid":
        if links.get("orcid_id"):
            return str(links["orcid_id"]).strip()
        val = str(links.get("orcid") or "").strip()
        if val:
            _, oid = parse_orcid_input(val)
            return oid or val
        return "ORCID"

    if platform == "lattes":
        if links.get("lattes_id"):
            return str(links["lattes_id"]).strip()
        val = str(links.get("lattes") or "").strip()
        if val:
            _, lid = parse_lattes_input(val)
            return lid or val
        return "Lattes"

    if platform == "scholar":
        # Utiliza o nome abreviado do pesquisador (ex: 'J. L. Mayrinck') ao invés do ID enigmático do Google Scholar
        sc_name = str(links.get("scholar_name") or links.get("scholar_author") or candidate_name or links.get("candidate_name") or "").strip()
        if sc_name:
            abbr = abbreviate_researcher_name(sc_name)
            if abbr:
                return abbr
        return "Google Scholar"

    return ""

def simplify_url_display(url: str) -> str:
    """Retorna uma versão amigável e simplificada da URL (remove protocolo http/https, www e barra final)."""
    if not url:
        return ""
    u = str(url).strip()
    u = re.sub(r"^https?://", "", u, flags=re.IGNORECASE)
    u = re.sub(r"^www\.", "", u, flags=re.IGNORECASE)
    u = u.rstrip("/")
    return u or url.strip()


def _build_contact_links(links: Dict[str, str], email: str, phone: str, location: str, candidate_name: str = "") -> List[str]:
    items: List[str] = []
    if email:
        clean_em = email.strip()
        items.append(rf"\mbox{{\href{{mailto:{escape_url(clean_em)}}}{{\faIcon{{envelope}}\ {escape_latex(clean_em)}}}}}")
    if phone:
        items.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(phone.strip())}}}")
    if location:
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(location.strip())
        items.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(location.strip())}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        items.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        scholar_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{scholar_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=candidate_name))
        items.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")
    return items


ORCID_PATTERN = re.compile(
    r"\borcid\b|\b000[0-9]-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9Xx]\b|\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b",
    re.IGNORECASE,
)
PROFILE_LINK_PATTERN = re.compile(
    r"\b(?:lattes|orcid|github|linkedin)\.com\b|\blattes\.cnpq\.br\b|^\s*(?:id\s+)?lattes[:\s]|^\s*orcid[:\s]",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(
    r"^(?:none|n/a|na|nil|null|nenhum|nenhuma|sem prêmios|sem certificações|no awards|empty|-)$",
    re.IGNORECASE,
)


def sanitize_awards(awards: Any) -> List[str]:
    """Higieniza a lista de prêmios/títulos/certificações:
    - Normaliza dicionários estruturados para texto limpo
    - Remove entradas nulas, vazias ou puramente de espaços
    - Remove rigorosamente identificadores e links de ORCID, Lattes, GitHub e LinkedIn
    - Remove placeholders como N/A, None, Nenhum, Sem Prêmios
    Retorna apenas títulos, prêmios ou certificações legítimos.
    """
    if not awards or not isinstance(awards, (list, tuple)):
        return []
    clean: List[str] = []
    for raw in awards:
        if raw is None:
            continue
        if isinstance(raw, dict):
            title = str(raw.get("title") or raw.get("name") or "").strip()
            yr = str(raw.get("year") or raw.get("date") or "").strip()
            det = str(raw.get("details") or raw.get("institution") or "").strip()
            parts: List[str] = []
            if title:
                parts.append(title)
            if yr:
                parts.append(f"({yr})")
            if det:
                parts.append(f"- {det}")
            val = " ".join(parts).strip()
        else:
            val = str(raw).strip()
        if not val:
            continue
        if ORCID_PATTERN.search(val):
            continue
        if PROFILE_LINK_PATTERN.search(val):
            continue
        if PLACEHOLDER_PATTERN.match(val):
            continue
        clean.append(val)
    return clean


def render_builtin_template(
    template_id: str,
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str = "profissional",
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o currículo completo em LaTeX usando o template e idioma escolhidos."""
    norm_lang = normalize_lang(lang)
    cv_clean = dict(cv)
    if "awards" in cv_clean:
        cv_clean["awards"] = sanitize_awards(cv_clean.get("awards"))
    cv = cv_clean
    if template_id == "academic_classic":
        return _render_academic_classic(cv, links, photo_filename, norm_lang)
    if template_id == "tech_sidebar":
        return _render_tech_sidebar(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "minimal_ats":
        return _render_minimal_ats(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_russell_ti", "russell_ti", "modelo_russell", "russell"):
        return _render_overleaf_russell_ti(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_awesome_cv", "awesome_cv", "awesome"):
        return _render_overleaf_awesome_cv(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("overleaf_single_page_keywords", "single_page_keywords", "keywords"):
        return _render_overleaf_single_page_keywords(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("nico_krieger", "modelo_nico_krieger", "krieger"):
        return _render_nico_krieger(cv, links, resume_type, photo_filename, norm_lang)
    if template_id in ("google_standard", "google"):
        return _render_google_standard(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "ai_ats_max":
        return _render_ai_ats_max(cv, links, resume_type, photo_filename, norm_lang)
    return _render_modern_pro(cv, links, resume_type, photo_filename, norm_lang)


def _render_header_with_optional_photo(
    name: str,
    title: str,
    contact_str: str,
    photo_filename: str | None,
    accent_cmd: str = r"\color{accent}",
) -> str:
    if photo_filename:
        return rf"""
\noindent
\begin{{minipage}}[c]{{0.78\textwidth}}
    {{\LARGE\bfseries {accent_cmd} {name}}}\\[4pt]
    {{\large\itshape {title}}}\\[6pt]
    {{\small {contact_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.19\textwidth}}
    \raggedleft
    \includegraphics[width=2.6cm,height=2.6cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{6pt}}
\hrule height 0.8pt
\vspace{{6pt}}
"""
    return rf"""
\begin{{center}}
    {{\LARGE\bfseries {accent_cmd} {name}}}\\[4pt]
    {{\large\itshape {title}}}\\[6pt]
    {{\small {contact_str}}}
\end{{center}}
\vspace{{2pt}}
\hrule height 0.8pt
\vspace{{6pt}}
"""


def _render_sections_body(cv: Dict[str, Any], resume_type: str, lang: str = "pt-br") -> str:
    """Constrói as seções do corpo na ordem e idioma ideais para currículo Acadêmico ou Profissional."""
    t = LATEX_I18N[normalize_lang(lang)]
    blocks: List[str] = []

    if cv.get("summary"):
        sec_title = t["sec_summary_acad"] if resume_type == "academico" else t["sec_summary_prof"]
        blocks.append(rf"\section*{{{sec_title}}}" + "\n" + escape_latex(cv["summary"]))

    edu_block = _build_education_block(cv.get("education") or [], lang)
    exp_block = _build_experience_block(cv.get("experience") or [], resume_type, lang)
    pub_block = _build_publications_block(cv.get("publications") or [], lang)
    proj_block = _build_projects_block(cv.get("projects") or [], resume_type, lang)
    skill_block = _build_skills_block(cv.get("skills") or [], lang)
    lang_award_block = _build_languages_and_awards_block(
        cv.get("languages") or [], cv.get("awards") or [], lang
    )

    if resume_type == "academico":
        ordered = [edu_block, pub_block, proj_block, exp_block, skill_block, lang_award_block]
    else:
        ordered = [exp_block, proj_block, edu_block, skill_block, pub_block, lang_award_block]

    for b in ordered:
        if b:
            blocks.append(b)

    return "\n\n".join(blocks)


def _build_education_block(educations: List[Dict[str, Any]], lang: str = "pt-br") -> str:
    if not educations:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    entries: List[str] = []
    for ed in educations:
        deg = escape_latex(ed.get("degree"))
        inst = escape_latex(ed.get("institution"))
        per = escape_latex(ed.get("period"))
        det = escape_latex(ed.get("details"))
        entry_lines = [rf"\noindent\textbf{{{deg}}} \hfill \textbf{{{per}}}"]
        if inst and det:
            entry_lines.append(rf"\textit{{{inst}}} \\ {{\small {det}}}")
        elif inst:
            entry_lines.append(rf"\textit{{{inst}}}")
        elif det:
            entry_lines.append(rf"{{\small {det}}}")
        entries.append(r" \\ ".join(entry_lines) + r"\par\vspace{4pt}")
    return rf"\section*{{{t['sec_education']}}}" + "\n\n" + "\n\n".join(entries)


def _build_experience_block(experiences: List[Dict[str, Any]], resume_type: str, lang: str = "pt-br") -> str:
    if not experiences:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    title = t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"]
    lines = [rf"\section*{{{title}}}"]
    for xp in experiences:
        role = escape_latex(xp.get("role"))
        org = escape_latex(xp.get("organization"))
        per = escape_latex(xp.get("period"))
        bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
        header_left = f"{role} --- \\textit{{{org}}}" if org else role
        lines.append(rf"\noindent\textbf{{{header_left}}} \hfill \textit{{{per}}}")
        if bullets:
            lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
            for b in bullets:
                lines.append(rf"    \item {b}")
            lines.append(r"\end{itemize}")
            lines.append(r"\vspace{2pt}")
        else:
            lines.append(r"\par\vspace{3pt}")
    return "\n".join(lines)


def _build_projects_block(projects: List[Dict[str, Any]], resume_type: str, lang: str = "pt-br") -> str:
    if not projects:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    title = t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"]
    lines = [rf"\section*{{{title}}}"]
    lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    for pj in projects:
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        desc = escape_latex(pj.get("description"))
        if url and url.startswith("http"):
            head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            head = rf"\textbf{{{nm}}}"
        if tech:
            head += rf" ({{\small\texttt{{{tech}}}}})"
        item_line = f"    \\item {head}"
        if desc:
            item_line += f": {desc}"
        lines.append(item_line)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _build_publications_block(publications: List[Dict[str, Any]], lang: str = "pt-br") -> str:
    if not publications:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    lines = [rf"\section*{{{t['sec_publications']}}}"]
    lines.append(r"\begin{enumerate}[leftmargin=1.5em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    for pb in publications:
        title = escape_latex(pb.get("title"))
        venue = escape_latex(pb.get("venue"))
        year = escape_latex(pb.get("year"))
        authors = escape_latex(pb.get("authors"))
        doi = (pb.get("doi") or "").strip()
        pub_url = (pb.get("url") or "").strip()
        if not pub_url and doi:
            pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        title_head = rf"\textbf{{{title}}}"
        if pub_url and pub_url.startswith("http"):
            title_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{title}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        parts = []
        if authors:
            parts.append(f"{authors}.")
        parts.append(f"{title_head}.")
        if venue:
            parts.append(rf"\textit{{{venue}}},")
        if year:
            parts.append(f"{year}.")
        if doi:
            doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            parts.append(rf"\href{{{escape_url(doi_url)}}}{{DOI: {escape_latex(doi)}}}")
        lines.append("    \\item " + " ".join(parts))
    lines.append(r"\end{enumerate}")
    return "\n".join(lines)


def _build_skills_block(skills: List[Dict[str, Any]], lang: str = "pt-br") -> str:
    if not skills:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    lines = [rf"\section*{{{t['sec_skills']}}}"]
    lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
    for sk in skills:
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category"))
            items = escape_latex(sk.get("items"))
        else:
            s = str(sk).strip()
            if ":" in s:
                p = s.split(":", 1)
                cat, items = escape_latex(p[0].strip()), escape_latex(p[1].strip())
            else:
                cat, items = "", escape_latex(s)
        if cat and items:
            lines.append(rf"    \item \textbf{{{cat}:}} {items}")
        elif items:
            lines.append(rf"    \item {items}")
        elif cat:
            lines.append(rf"    \item {cat}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _build_languages_and_awards_block(languages: List[str], awards: List[str], lang: str = "pt-br") -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    parts: List[str] = []
    clean_langs = [str(x).strip() for x in (languages or []) if str(x).strip()]
    if clean_langs:
        langs_esc = " $\\cdot$ ".join(escape_latex(x) for x in clean_langs)
        if langs_esc:
            parts.append(rf"\section*{{{t['sec_languages']}}}" + "\n" + langs_esc)
    clean_awards = sanitize_awards(awards)
    if clean_awards:
        lines = [rf"\section*{{{t['sec_awards']}}}"]
        lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
        for aw in clean_awards:
            lines.append(rf"    \item {escape_latex(aw)}")
        lines.append(r"\end{itemize}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _render_modern_pro(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    title = escape_latex(cv.get("title") or default_tl)
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " \\;|\\; ".join(contact_items[:mid])
        r2 = " \\;|\\; ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " \\;|\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename)
    body = _render_sections_body(cv, resume_type, lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.4cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0F4C81}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\large\bfseries\color{{accent}}}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{4pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""


def _render_academic_classic(
    cv: Dict[str, Any],
    links: Dict[str, str],
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_researcher"])
    title = escape_latex(cv.get("title") or t["default_acad_title"])
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " \\;\\textbullet\\; ".join(contact_items[:mid])
        r2 = " \\;\\textbullet\\; ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " \\;\\textbullet\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd=r"\color{acadnavy}")
    body = _render_sections_body(cv, "academico", lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{acadnavy}}{{HTML}}{{1B365D}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{acadnavy}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{9pt}}{{4pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""


def _render_tech_sidebar(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    title = escape_latex(cv.get("title") or t["default_tech_title"])
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)

    photo_tex = ""
    if photo_filename:
        photo_tex = rf"""
\begin{{center}}
    \includegraphics[width=3.2cm,height=3.2cm,keepaspectratio]{{{photo_filename}}}
\end{{center}}
\vspace{{4pt}}
"""

    sidebar_contacts = "\n\n".join(rf"\noindent{{\small {c}}}" for c in contact_items)
    sidebar_skills = _build_skills_block(cv.get("skills") or [], lang)
    sidebar_langs = _build_languages_and_awards_block(cv.get("languages") or [], cv.get("awards") or [], lang)

    main_blocks: List[str] = []
    if cv.get("summary"):
        main_blocks.append(rf"\section*{{{t['sec_profile']}}}" + "\n" + escape_latex(cv["summary"]))
    if resume_type == "academico":
        for b in (
            _build_education_block(cv.get("education") or [], lang),
            _build_publications_block(cv.get("publications") or [], lang),
            _build_projects_block(cv.get("projects") or [], resume_type, lang),
            _build_experience_block(cv.get("experience") or [], resume_type, lang),
        ):
            if b:
                main_blocks.append(b)
    else:
        for b in (
            _build_experience_block(cv.get("experience") or [], resume_type, lang),
            _build_projects_block(cv.get("projects") or [], resume_type, lang),
            _build_education_block(cv.get("education") or [], lang),
            _build_publications_block(cv.get("publications") or [], lang),
        ):
            if b:
                main_blocks.append(b)

    main_body = "\n\n".join(main_blocks)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.2cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{accent}}{{HTML}}{{2563EB}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{accent}}}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{3pt}}

\begin{{document}}
\noindent
\begin{{minipage}}[t]{{0.31\textwidth}}
\vspace{{0pt}}
{photo_tex}
{{\Large\bfseries\color{{sidecolor}} {name}}}\\[3pt]
{{\normalsize\itshape\color{{accent}} {title}}}\\[8pt]
\section*{{{t['sec_contact']}}}
{sidebar_contacts}

{sidebar_skills}

{sidebar_langs}
\end{{minipage}}%
\hfill
\vrule width 0.5pt
\hfill
\begin{{minipage}}[t]{{0.65\textwidth}}
\vspace{{0pt}}
{main_body}
\end{{minipage}}
\end{{document}}
"""


def _render_minimal_ats(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    name = escape_latex(cv.get("name") or t["default_candidate"])
    title = escape_latex(cv.get("title") or t["default_cv_title"])
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""), candidate_name=name)
    if len(contact_items) > 4:
        mid = (len(contact_items) + 1) // 2
        r1 = " | ".join(contact_items[:mid])
        r2 = " | ".join(contact_items[mid:])
        contact_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contact_str = " | ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd="")
    body = _render_sections_body(cv, resume_type, lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.3cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{3pt}}

\begin{{document}}
{header}
{body}
\end{{document}}
"""


def _split_first_last_name(raw_name: str) -> tuple[str, str]:
    """Divide o nome completo em (Primeiro(s) Nome(s), Sobrenome(s)) no estilo Russell / Awesome-CV / my_cv."""
    cleaned = (raw_name or "").strip()
    parts = cleaned.split()
    if not parts:
        return ("Candidato", "")
    if len(parts) == 1:
        return (escape_latex(parts[0]), "")
    if len(parts) == 2:
        return (escape_latex(parts[0]), escape_latex(parts[1]))
    # Para 3+ palavras, usa as duas primeiras no primeiro bloco e o restante no segundo
    return (escape_latex(" ".join(parts[:2])), escape_latex(" ".join(parts[2:])))


def _acv_sec_cmd(raw_title: str) -> str:
    """Formata comando \\cvsection{título} garantindo que nenhuma linha horizontal engula o parágrafo seguinte."""
    clean = escape_latex((raw_title or "").replace(r"\&", "&").strip())
    return rf"\cvsection{{{clean}}}"


def _build_acv_sections(
    cv: Dict[str, Any],
    resume_type: str,
    lang: str = "pt-br",
    skills_first: bool = False,
    with_lang_circles: bool = True,
) -> str:
    """Constrói seções no estilo Russell CV / Awesome-CV (\\cvsection, \\cventries, \\cvskills, \\cvhonors)."""
    t = LATEX_I18N[normalize_lang(lang)]
    blocks: List[str] = []

    if cv.get("summary"):
        sec_title = t["sec_profile"] if with_lang_circles else (
            t["sec_summary_acad"] if resume_type == "academico" else t["sec_summary_prof"]
        )
        blocks.append(
            _acv_sec_title_with_body(
                sec_title,
                rf"{{\small\color{{sidecolor}} {escape_latex(cv['summary'])}}}\par\vspace{{4pt}}",
            )
        )

    # Skills block (tabular style \cvskills)
    sk_lines: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category") or t["default_skill_cat"])
            items = escape_latex(sk.get("items"))
        else:
            s = str(sk).strip()
            cat = escape_latex(t["default_skill_cat"])
            items = escape_latex(s)
        if items:
            sk_lines.append(rf"    \textbf{{\color{{sidecolor}} {cat}}} & {{\small {items}}} \\")
    skill_block = ""
    if sk_lines:
        skill_body = (
            r"\noindent\begin{tabular}{@{} r p{0.78\textwidth} @{}}"
            + "\n"
            + "\n".join(sk_lines)
            + "\n"
            + r"\end{tabular}\par\vspace{4pt}"
        )
        skill_block = _acv_sec_title_with_body(t["sec_skills"], skill_body)

    # Experience block (\cventries)
    xp_entries: List[str] = []
    for xp in (cv.get("experience") or []):
        role = escape_latex(xp.get("role"))
        org = escape_latex(xp.get("organization"))
        per = escape_latex(xp.get("period"))
        bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
        b_tex = ""
        if bullets:
            items_str = "\n".join(rf"    \item {b}" for b in bullets)
            b_tex = (
                r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"
                + "\n"
                + items_str
                + "\n"
                + r"\end{itemize}"
            )
        xp_entries.append(rf"\cventry{{{role}}}{{{org}}}{{}}{{{per}}}{{{b_tex}}}")
    exp_title = t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"]
    exp_block = _acv_sec_title_with_body(exp_title, "\n\n".join(xp_entries)) if xp_entries else ""

    # Education block (\cventries)
    ed_entries: List[str] = []
    for ed in (cv.get("education") or []):
        deg = escape_latex(ed.get("degree"))
        inst = escape_latex(ed.get("institution"))
        per = escape_latex(ed.get("period"))
        det = escape_latex(ed.get("details"))
        det_tex = rf"{{\small {det}}}" if det else ""
        ed_entries.append(rf"\cventry{{{deg}}}{{{inst}}}{{}}{{{per}}}{{{det_tex}}}")
    edu_block = _acv_sec_title_with_body(t["sec_education"], "\n\n".join(ed_entries)) if ed_entries else ""

    # Projects block (\cventries)
    pj_entries: List[str] = []
    lbl_tech = t.get("lbl_tech_stack", "Ferramentas & Tecnologias")
    for pj in (cv.get("projects") or []):
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        desc = escape_latex(pj.get("description"))
        if url and url.startswith("http"):
            nm_tex = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            nm_tex = rf"\textbf{{{nm}}}"
        b_items: List[str] = []
        if desc:
            b_items.append(rf"    \item {desc}")
        if tech:
            b_items.append(rf"    \item \textbf{{{lbl_tech}:}} {tech}")
        b_tex = (
            r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"
            + "\n"
            + "\n".join(b_items)
            + "\n"
            + r"\end{itemize}"
            if b_items
            else ""
        )
        pj_entries.append(rf"\cventry{{}}{{{nm_tex}}}{{}}{{}}{{{b_tex}}}")
    proj_title = t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"]
    proj_block = _acv_sec_title_with_body(proj_title, "\n\n".join(pj_entries)) if pj_entries else ""

    # Publications block
    pub_block = ""
    pubs = cv.get("publications") or []
    if pubs:
        pb_lines = [r"\begin{enumerate}[leftmargin=1.5em,itemsep=2pt,topsep=2pt]"]
        for pb in pubs:
            title = escape_latex(pb.get("title"))
            venue = escape_latex(pb.get("venue"))
            year = escape_latex(pb.get("year"))
            authors = escape_latex(pb.get("authors"))
            doi = (pb.get("doi") or "").strip()
            pub_url = (pb.get("url") or "").strip()
            if not pub_url and doi:
                pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            title_head = rf"\textbf{{{title}}}"
            if pub_url and pub_url.startswith("http"):
                title_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{title}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            parts = []
            if authors:
                parts.append(f"{authors}.")
            parts.append(f"{title_head}.")
            if venue:
                parts.append(rf"\textit{{{venue}}},")
            if year:
                parts.append(f"{year}.")
            if doi:
                doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                parts.append(rf"\href{{{escape_url(doi_url)}}}{{\color{{accent}}DOI: {escape_latex(doi)}}}")
            pb_lines.append("    \\item {\\small " + " ".join(parts) + "}")
        pb_lines.append(r"\end{enumerate}")
        pub_block = _acv_sec_title_with_body(t["sec_publications"], "\n".join(pb_lines))

    # Languages & Awards block
    langs = [str(x).strip() for x in (cv.get("languages") or []) if str(x).strip()]
    lang_block = ""
    if langs:
        if with_lang_circles:
            l_rows: List[str] = []
            for idx, lg in enumerate(langs):
                low_lg = lg.lower()
                m = re.match(r"^([^\(]+)(?:\s*\((.*?)\))?$", lg)
                clean_name = m.group(1).strip() if m else lg
                prof_note = m.group(2).strip().lower() if m and m.group(2) else ""

                if any(k in prof_note or k in low_lg for k in ("fluente", "fluent", "nativo", "native")):
                    filled = 5
                elif any(k in prof_note or k in low_lg for k in ("avançado", "avancado", "advanced")):
                    filled = 4
                elif any(k in prof_note or k in low_lg for k in ("intermediário", "intermediario", "intermediate")):
                    filled = 3
                elif any(k in prof_note or k in low_lg for k in ("iniciante", "básico", "basico", "beginner", "basic", "pouco")):
                    filled = 2
                else:
                    if "portugu" in low_lg:
                        filled = 5
                    elif "ingl" in low_lg or "engl" in low_lg:
                        filled = 3
                    elif any(k in low_lg for k in ("espanh", "span", "libra")):
                        filled = 2
                    elif idx == 0:
                        filled = 5
                    else:
                        filled = 3

                full_circle = r"\faIcon{circle}"
                empty_circle = r"\faIcon[regular]{circle}"
                dots = " ".join([full_circle] * filled + [empty_circle] * (5 - filled))
                l_rows.append(rf"    \textbf{{\color{{sidecolor}} {escape_latex(clean_name)}}} & {{\color{{accent}} {dots}}} \\")
            l_body = (
                r"\noindent\begin{tabular}{@{} p{0.55\textwidth} >{\raggedleft\arraybackslash}p{0.40\textwidth} @{}}"
                + "\n"
                + "\n".join(l_rows)
                + "\n"
                + r"\end{tabular}\par\vspace{3pt}"
            )
            lang_block = _acv_sec_title_with_body(t["sec_languages"], l_body)
        else:
            langs_esc = " $\\cdot$ ".join(escape_latex(x) for x in langs)
            lang_block = _acv_sec_title_with_body(t["sec_languages"], rf"{{\small {langs_esc}}}\par\vspace{{3pt}}")

    clean_awards = sanitize_awards(cv.get("awards"))
    award_block = ""
    if clean_awards:
        aw_lines = [r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"]
        for aw in clean_awards:
            aw_lines.append(rf"    \item {{\small {escape_latex(aw)}}}")
        aw_lines.append(r"\end{itemize}")
        award_block = _acv_sec_title_with_body(t["sec_awards"], "\n".join(aw_lines))

    if resume_type == "academico":
        ordered = [edu_block, pub_block, proj_block, exp_block, skill_block, award_block, lang_block]
    elif skills_first:
        # Ordem do Jason Richards' Résumé (Awesome-CV): Skills -> Education -> Experience -> Projects -> Pubs -> Languages
        ordered = [skill_block, edu_block, exp_block, proj_block, pub_block, award_block, lang_block]
    else:
        # Ordem do Currículo T.I. (Russell CV): Skills -> Experience -> Education -> Projects -> Pubs -> Languages
        ordered = [skill_block, exp_block, edu_block, proj_block, pub_block, award_block, lang_block]

    for b in ordered:
        if b:
            blocks.append(b)

    return "\n\n".join(blocks)


def _acv_sec_title_with_body(title: str, body: str) -> str:
    return _acv_sec_cmd(title) + "\n" + body


def _render_overleaf_russell_ti(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Currículo - T.I.' (Russell CV — https://www.overleaf.com/read/rgfqqnnynrmv#d5b171)."""
    t = LATEX_I18N[normalize_lang(lang)]
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    role = escape_latex(cv.get("title") or default_tl)

    row1_links: List[str] = []
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        row1_links.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")

    row2_links: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        row2_links.append(rf"\mbox{{\href{{mailto:{escape_url(em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(em)}}}}}")
    if cv.get("phone"):
        row2_links.append(rf"\mbox{{\faIcon{{whatsapp}}\ {escape_latex(cv['phone'])}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        row2_links.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        row2_links.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        row2_links.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")

    r1_str = " \\quad | \\quad ".join(row1_links)
    r2_str = " \\quad | \\quad ".join(row2_links)
    contacts_combined = "\\\\[3pt]\n    ".join(x for x in (r1_str, r2_str) if x)

    if photo_filename:
        header_tex = rf"""\begin{{center}}
\begin{{tabular}}{{@{{}} c l @{{}}}}
  \adjustbox{{valign=c}}{{\includegraphics[width=2.3cm,height=2.3cm,keepaspectratio]{{{photo_filename}}}}} &
  \hspace{{2mm}}\begin{{minipage}}[c]{{0.82\linewidth}}
    \centering
    {{\fontsize{{22pt}}{{26pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{22pt}}{{26pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[3pt]
    {{\large\itshape\color{{accent}} {role}}}\\[4pt]
    {{\small {contacts_combined}}}
  \end{{minipage}}
\end{{tabular}}
\end{{center}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{24pt}}{{28pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{24pt}}{{28pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[3pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\small {contacts_combined}}}
\end{{center}}"""

    body = _build_acv_sections(cv, resume_type, lang, skills_first=False, with_lang_circles=True)

    return rf"""% Template Overleaf: Currículo - T.I. (Russell CV) — https://www.overleaf.com/read/rgfqqnnynrmv#d5b171
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{roboto}}
\usepackage[default]{{sourcesanspro}}
\usepackage{{fontawesome5}}
\usepackage{{adjustbox}}
\usepackage{{array}}
\usepackage[left=1.4cm,top=0.9cm,right=1.4cm,bottom=1.5cm,footskip=0.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0F4C81}}
\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{graytext}}{{HTML}}{{5D5D5D}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\vhrulefill}}[1]{{\leavevmode\leaders\hrule height #1\hfill\kern0pt}}
\newcommand{{\cvsection}}[1]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries\color{{accent}}#1}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    \ifstrempty{{#1#4}}{{}}{{\small\scshape #1 & \small\itshape\color{{graytext}} #4 \\}}%
  \end{{tabular*}}\par
  #5\vspace{{4pt}}\par
}}

\begin{{document}}
{header_tex}
{body}
\end{{document}}
"""


def _render_overleaf_awesome_cv(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Jason Richards' Résumé' (Awesome-CV — https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc)."""
    t = LATEX_I18N[normalize_lang(lang)]
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    full_nm_esc = escape_latex(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    role = escape_latex(cv.get("title") or default_tl)

    social_items: List[str] = []
    if cv.get("phone"):
        social_items.append(rf"\mbox{{\faIcon{{mobile-alt}}\ {escape_latex(cv['phone'])}}}")
    if cv.get("email"):
        em = cv["email"].strip()
        social_items.append(rf"\mbox{{\href{{mailto:{escape_url(em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(em)}}}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        social_items.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        social_items.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")

    if len(social_items) > 4:
        mid = (len(social_items) + 1) // 2
        r1 = " \\quad\\textbar\\quad ".join(social_items[:mid])
        r2 = " \\quad\\textbar\\quad ".join(social_items[mid:])
        social_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        social_str = " \\quad\\textbar\\quad ".join(social_items)

    if photo_filename:
        header_tex = rf"""\noindent
\begin{{minipage}}[c]{{0.80\textwidth}}
    {{\fontsize{{26pt}}{{30pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{26pt}}{{30pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[4pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\footnotesize\color{{graytext}} {social_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.18\textwidth}}
    \raggedleft
    \includegraphics[width=2.4cm,height=2.4cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{4pt}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{28pt}}{{32pt}}\selectfont\color{{graytext}} {first_nm}}} {{\fontsize{{28pt}}{{32pt}}\selectfont\bfseries\color{{sidecolor}} {last_nm}}}\\[4pt]
    {{\large\itshape\color{{accent}} {role}}}\\[5pt]
    {{\footnotesize\color{{graytext}} {social_str}}}
\end{{center}}
\vspace{{2pt}}"""

    body = _build_acv_sections(cv, resume_type, lang, skills_first=True, with_lang_circles=False)
    footer_lbl = "Résumé" if normalize_lang(lang) == "en-us" else "Currículo"

    return rf"""% Template Overleaf: Jason Richards' Résumé (Awesome-CV) — https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{roboto}}
\usepackage[default]{{sourcesanspro}}
\usepackage{{fontawesome5}}
\usepackage{{fancyhdr}}
\usepackage{{array}}
\usepackage[left=1.4cm,top=1.1cm,right=1.4cm,bottom=1.8cm,footskip=0.5cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0395DE}}
\definecolor{{sidecolor}}{{HTML}}{{333333}}
\definecolor{{graytext}}{{HTML}}{{5D5D5D}}

\pagestyle{{fancy}}
\fancyhf{{}}
\renewcommand{{\headrulewidth}}{{0pt}}
\fancyfoot[L]{{\footnotesize\color{{graytext}}\today}}
\fancyfoot[C]{{\footnotesize\color{{graytext}}{full_nm_esc}\ ~~~\textperiodcentered~~~\ {footer_lbl}}}
\fancyfoot[R]{{\footnotesize\color{{graytext}}\thepage}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\vhrulefill}}[1]{{\leavevmode\leaders\hrule height #1\hfill\kern0pt}}
\newcommand{{\cvsection}}[1]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries\color{{accent}}#1}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    \ifstrempty{{#1#4}}{{}}{{\small\scshape #1 & \small\itshape\color{{graytext}} #4 \\}}%
  \end{{tabular*}}\par
  #5\vspace{{4pt}}\par
}}

\begin{{document}}
{header_tex}
{body}
\end{{document}}
"""


def _render_overleaf_single_page_keywords(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Overleaf 'Sample single page resume with keywords' (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk)."""
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    raw_name = cv.get("name") or t["default_candidate"]
    first_nm, last_nm = _split_first_last_name(raw_name)
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    role = escape_latex(cv.get("title") or default_tl)

    # Coleta keywords de skills para destacar nas experiências caso necessário
    all_skill_items: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict) and sk.get("items"):
            all_skill_items.append(escape_latex(sk["items"]))
        elif isinstance(sk, str) and sk.strip():
            all_skill_items.append(escape_latex(sk.strip()))
    fallback_kw = ", ".join(all_skill_items)[:95]

    right_contacts: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        right_contacts.append(rf"{{\small Email}} \href{{mailto:{escape_url(em)}}}{{\textbf{{{escape_latex(em)}}}}}")
    if cv.get("phone"):
        lbl_ph = "Phone" if is_en else "Tel"
        right_contacts.append(rf"{{\small {lbl_ph}}} \textbf{{{escape_latex(cv['phone'])}}}")
    if cv.get("location"):
        lbl_lc = "Location" if is_en else "Local"
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        right_contacts.append(rf"{{\small {lbl_lc}}} \href{{{escape_url(maps_url)}}}{{\textbf{{{escape_latex(cv['location'].strip())}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        right_contacts.append(rf"{{\small Web}} \href{{{escape_url(links['portfolio'])}}}{{\textbf{{{port_disp}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        right_contacts.append(rf"{{\small\faIcon{{linkedin}}}} \href{{{escape_url(links['linkedin'])}}}{{\textbf{{{li_disp}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        right_contacts.append(rf"{{\small\faIcon{{github}}}} \href{{{escape_url(links['github'])}}}{{\textbf{{{gh_disp}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        right_contacts.append(rf"{{\small\faIcon{{orcid}}}} \href{{{escape_url(links['orcid'])}}}{{\textbf{{{orcid_disp}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        right_contacts.append(rf"{{\small\faIcon{{google}}}} \href{{{escape_url(links['scholar'])}}}{{\textbf{{{sc_disp}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        right_contacts.append(rf"{{\small\faIcon{{graduation-cap}}}} \href{{{escape_url(links['lattes'])}}}{{\textbf{{{lattes_disp}}}}}")

    right_contact_tex = "\\\\\n    ".join(right_contacts)
    photo_inline = (
        rf"\includegraphics[width=1.9cm,height=1.9cm,keepaspectratio]{{{photo_filename}}}\hspace{{6pt}}"
        if photo_filename
        else ""
    )

    summary_tex = ""
    if cv.get("summary"):
        sum_lbl = "SUMMARY" if is_en else "RESUMO"
        summary_tex = rf"""\cvsec{{\faIcon{{file-alt}}}}{{{sum_lbl}}}
{{\small {escape_latex(cv['summary'])}}}
\vspace{{4pt}}"""

    # Coluna 1: WORK + SKILLS
    work_lbl = "WORK" if is_en else "EXPERIÊNCIA"
    work_items: List[str] = []
    for xp in (cv.get("experience") or []):
        r_txt = escape_latex(xp.get("role"))
        p_txt = escape_latex(xp.get("period"))
        o_txt = escape_latex(xp.get("organization"))
        bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
        desc_txt = " ".join(bullets)
        head_rp = f"{r_txt} / {p_txt}" if p_txt else r_txt
        work_items.append(rf"\work{{{head_rp}}}{{{o_txt}}}{{{desc_txt}}}{{{fallback_kw}}}")
    work_sec = (rf"\cvsec{{\faIcon{{pencil-alt}}}}{{{work_lbl}}}" + "\n" + "\n\n".join(work_items)) if work_items else ""

    sk_lbl = "SKILLS" if is_en else "COMPETÊNCIAS"
    sk_rows: List[str] = []
    for sk in (cv.get("skills") or []):
        if isinstance(sk, dict):
            cat = escape_latex(sk.get("category") or t["default_skill_cat"])
            items = escape_latex(sk.get("items"))
        else:
            cat = escape_latex(t["default_skill_cat"])
            items = escape_latex(str(sk).strip())
        if items:
            sk_rows.append(rf"\noindent\textbf{{{cat}:}} {{\small {items}}}\par\vspace{{2pt}}")
    sk_sec = (rf"\cvsec{{\faIcon{{list}}}}{{{sk_lbl}}}" + "\n" + "\n".join(sk_rows)) if sk_rows else ""

    # Coluna 2: OTHER PROJECTS + EDUCATION + PUBLICATIONS + AWARDS / LANGUAGES
    proj_lbl = "OTHER PROJECTS" if is_en else "PROJETOS DE DESTAQUE"
    proj_rows: List[str] = []
    for pj in (cv.get("projects") or []):
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        desc = escape_latex(pj.get("description"))
        if url and url.startswith("http"):
            nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
        else:
            nm_head = rf"\textbf{{{nm}}}"
        kw_suffix = rf" --- \textbf{{{tech}}}" if tech else ""
        body_p = f"{desc}{kw_suffix}" if desc else kw_suffix.lstrip(" -")
        proj_rows.append(rf"    \item {nm_head}: {body_p}")
    proj_sec = ""
    if proj_rows:
        proj_sec = (
            rf"\cvsec{{\faIcon{{paint-brush}}}}{{{proj_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=2pt]\n"
            + "\n".join(proj_rows)
            + "\n\\end{itemize}"
        )

    edu_lbl = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
    edu_rows: List[str] = []
    for ed in (cv.get("education") or []):
        deg = escape_latex(ed.get("degree"))
        per = escape_latex(ed.get("period"))
        inst = escape_latex(ed.get("institution"))
        det = escape_latex(ed.get("details"))
        head_ed = f"{deg} - {per}" if per else deg
        edu_rows.append(rf"\school{{{head_ed}}}{{{inst}}}{{{det}}}")
    edu_sec = (rf"\cvsec{{\faIcon{{graduation-cap}}}}{{{edu_lbl}}}" + "\n" + "\n\n".join(edu_rows)) if edu_rows else ""

    pub_sec = ""
    pubs = cv.get("publications") or []
    if pubs:
        pub_lbl = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        p_rows: List[str] = []
        for pb in pubs:
            pt = escape_latex(pb.get("title"))
            pv = escape_latex(pb.get("venue"))
            py = escape_latex(pb.get("year"))
            pub_url = (pb.get("url") or "").strip()
            doi = (pb.get("doi") or "").strip()
            if not pub_url and doi:
                pub_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            if pub_url and pub_url.startswith("http"):
                pt_head = rf"\href{{{escape_url(pub_url)}}}{{\textbf{{{pt}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                pt_head = rf"\textbf{{{pt}}}"
            p_rows.append(rf"    \item {pt_head} ({pv}, {py})")
        pub_sec = (
            rf"\cvsec{{\faIcon{{book}}}}{{{pub_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=2pt]\n"
            + "\n".join(p_rows)
            + "\n\\end{itemize}"
        )

    aw_sec = ""
    clean_awards = sanitize_awards(cv.get("awards"))
    if clean_awards:
        aw_lbl = "AWARDS" if is_en else r"PRÊMIOS \& CERTIFICAÇÕES"
        a_rows = [rf"    \item {escape_latex(a)}" for a in clean_awards]
        aw_sec = (
            rf"\cvsec{{\faIcon{{star}}}}{{{aw_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=2pt]\n"
            + "\n".join(a_rows)
            + "\n\\end{itemize}"
        )

    lg_sec = ""
    langs = [str(x).strip() for x in (cv.get("languages") or []) if str(x).strip()]
    if langs:
        lg_lbl = "LANGUAGES / INTERESTS" if is_en else "IDIOMAS"
        lg_sec = rf"\cvsec{{\faIcon{{globe}}}}{{{lg_lbl}}}" + "\n{\\small " + " $\\cdot$ ".join(escape_latex(x) for x in langs) + "}"

    col1_body = "\n\n".join(x for x in (work_sec, edu_sec, aw_sec) if x)
    col2_body = "\n\n".join(x for x in (proj_sec, sk_sec, pub_sec, lg_sec) if x)

    return rf"""% Template Overleaf: Sample single page resume with keywords — https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage[default]{{raleway}}
\usepackage{{fontawesome5}}
\usepackage{{tikz}}
\usepackage{{multicol}}
\usepackage[skins]{{tcolorbox}}
\usepackage[margin=1.0cm,footskip=0.25in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{52ADE3}}
\definecolor{{sidecolor}}{{HTML}}{{111827}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\columnsep}}{{1.1cm}}

\newcommand*{{\circled}}[1]{{%
  \tikz[baseline=(char.base)]{{%
    \node[shape=circle,fill=sidecolor,inner sep=1.8pt,minimum size=18pt] (char) {{\textcolor{{white}}{{\footnotesize #1}}}};%
  }}%
}}
\newcommand*{{\cvsec}}[2]{{%
  \vspace{{6pt}}\noindent\circled{{#1}}\hspace{{5pt}}{{\large\bfseries\color{{accent}} #2}}\par\vspace{{3pt}}%
}}
\newcommand*{{\work}}[4]{{%
  \noindent{{\normalsize\bfseries\color{{sidecolor}} #1}}\par
  \ifx&#2&\else\noindent{{\small\bfseries\color{{accent}} #2}}\par\fi
  \ifx&#3&\else\noindent{{\small #3}}\par\fi
  \ifx&#4&\else\noindent{{\footnotesize\textbf{{Keywords:}} \textit{{#4}}}}\par\fi
  \vspace{{5pt}}
}}
\newcommand*{{\school}}[3]{{%
  \noindent{{\normalsize\bfseries\color{{sidecolor}} #1}}\par
  \ifx&#2&\else\noindent{{\small\bfseries\color{{accent}} #2}}\par\fi
  \ifx&#3&\else\noindent{{\footnotesize\textit{{#3}}}}\par\fi
  \vspace{{4pt}}
}}

\begin{{document}}
\noindent
\begin{{minipage}}[c]{{0.58\textwidth}}
    {photo_inline}\begin{{minipage}}[c]{{0.78\linewidth}}
        {{\fontsize{{26}}{{28}}\selectfont\bfseries\color{{sidecolor}} {first_nm}}}\\[2pt]
        {{\fontsize{{28}}{{30}}\selectfont\mdseries\color{{accent}} {last_nm}}}\\[4pt]
        {{\large\itshape\color{{sidecolor}} {role}}}
    \end{{minipage}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.40\textwidth}}
    \begin{{flushright}}
    {right_contact_tex}
    \end{{flushright}}
\end{{minipage}}
\vspace{{4pt}}
\hrule height 0.6pt
\vspace{{4pt}}

{summary_tex}

\begin{{multicols}}{{2}}
{col1_body}
\columnbreak
{col2_body}
\end{{multicols}}
\end{{document}}
"""


def _render_google_standard(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Padrão Google (Big Tech / Software Engineer) — baseado em Gayle Laakmann McDowell.

    Layout em página única densa, margens de 0.5 polegadas, estrutura XYZ de realizações,
    divisórias horizontais limpas e total conformidade com triagem humana e automatizada.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    title = escape_latex(cv.get("title") or default_tl)

    contact_parts: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        contact_parts.append(rf"\mbox{{\href{{mailto:{escape_url(em)}}}{{\faIcon{{envelope}}\ {escape_latex(em)}}}}}")
    if cv.get("phone"):
        contact_parts.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(cv['phone'].strip())}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        contact_parts.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")

    if len(contact_parts) > 4:
        mid = (len(contact_parts) + 1) // 2
        r1 = " \\quad | \\quad ".join(contact_parts[:mid])
        r2 = " \\quad | \\quad ".join(contact_parts[mid:])
        contacts_str = f"{r1}\\\\[3pt]\n    {r2}"
    else:
        contacts_str = " \\quad | \\quad ".join(contact_parts)

    if photo_filename:
        header_tex = rf"""\noindent
\begin{{minipage}}[c]{{0.78\textwidth}}
    {{\fontsize{{24pt}}{{28pt}}\selectfont\bfseries\color{{sidecolor}} {name}}}\\[3pt]
    {{\large\color{{accent}} {title}}}\\[4pt]
    {{\small {contacts_str}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.20\textwidth}}
    \raggedleft
    \includegraphics[width=2.5cm,height=2.5cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\vspace{{3pt}}
\hrule height 0.8pt
\vspace{{4pt}}"""
    else:
        header_tex = rf"""\begin{{center}}
    {{\fontsize{{26pt}}{{30pt}}\selectfont\bfseries\color{{sidecolor}} {name}}}\\[3pt]
    {{\large\color{{accent}} {title}}}\\[4pt]
    {{\small {contacts_str}}}
\end{{center}}
\vspace{{2pt}}
\hrule height 0.8pt
\vspace{{4pt}}"""

    # Summary
    sum_block = ""
    if cv.get("summary"):
        sec_sum = "SUMMARY" if is_en else "RESUMO PROFISSIONAL"
        sum_block = rf"\section*{{{sec_sum}}}" + "\n" + rf"{{\small {escape_latex(cv['summary'])}}}"

    # Experience
    xp_block = ""
    xp_list = cv.get("experience") or []
    if xp_list:
        sec_xp = "WORK EXPERIENCE" if is_en else (t["sec_exp_acad"] if resume_type == "academico" else t["sec_exp_prof"])
        xp_lines = [rf"\section*{{{sec_xp}}}"]
        for xp in xp_list:
            role = escape_latex(xp.get("role"))
            org = escape_latex(xp.get("organization"))
            per = escape_latex(xp.get("period"))
            bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
            head_l = f"\\textbf{{{org}}}" if org else f"\\textbf{{{role}}}"
            sub_l = f"\\textit{{{role}}}" if org else ""
            item_lines = [rf"\noindent{head_l} \hfill \textbf{{{per}}}"]
            if sub_l:
                item_lines.append(rf"\\ {sub_l}")
            if bullets:
                item_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                for b in bullets:
                    item_lines.append(rf"    \item {b}")
                item_lines.append(r"\end{itemize}")
                item_lines.append(r"\vspace{3pt}")
            else:
                item_lines.append(r"\par\vspace{3pt}")
            xp_lines.append("\n".join(item_lines))
        xp_block = "\n".join(xp_lines)

    # Education
    edu_block = ""
    edu_list = cv.get("education") or []
    if edu_list:
        sec_edu = "EDUCATION" if is_en else t["sec_education"]
        ed_lines = [rf"\section*{{{sec_edu}}}"]
        for ed in edu_list:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            head_i = f"\\textbf{{{inst}}}" if inst else f"\\textbf{{{deg}}}"
            sub_d = f"\\textit{{{deg}}}" if inst else ""
            item_lines = [rf"\noindent{head_i} \hfill \textbf{{{per}}}"]
            if sub_d and det:
                item_lines.append(rf"\\ {sub_d} \hfill {{\small {det}}}\par\vspace{{4pt}}")
            elif sub_d:
                item_lines.append(rf"\\ {sub_d}\par\vspace{{4pt}}")
            elif det:
                item_lines.append(rf"\\ {{\small {det}}}\par\vspace{{4pt}}")
            else:
                item_lines.append(r"\par\vspace{4pt}")
            ed_lines.append("\n".join(item_lines))
        edu_block = "\n".join(ed_lines)

    # Projects
    pj_block = ""
    pj_list = cv.get("projects") or []
    if pj_list:
        sec_pj = "KEY PROJECTS" if is_en else (t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"])
        pj_lines = [rf"\section*{{{sec_pj}}}"]
        for pj in pj_list:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(pj.get("description"))
            if url and url.startswith("http"):
                nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
                link_tex = rf"\href{{{escape_url(url)}}}{{\textit{{{t['link_label']}}}}}"
            else:
                nm_head = rf"\textbf{{{nm}}}"
                link_tex = escape_latex(url)
            tech_str = rf" \textbar{{}} \textit{{{tech}}}" if tech else ""
            pj_lines.append(rf"\noindent{nm_head}{tech_str}")
            if desc:
                pj_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                pj_lines.append(rf"    \item {desc}")
                pj_lines.append(r"\end{itemize}")
                pj_lines.append(r"\vspace{2pt}")
            else:
                pj_lines.append(r"\par\vspace{2pt}")
        pj_block = "\n".join(pj_lines)

    # Skills
    sk_block = ""
    sk_list = cv.get("skills") or []
    if sk_list:
        sec_sk = "TECHNICAL SKILLS" if is_en else t["sec_skills"]
        sk_lines = [rf"\section*{{{sec_sk}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for sk in sk_list:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category") or t["default_skill_cat"])
                items = escape_latex(sk.get("items"))
            else:
                s = str(sk).strip()
                if ":" in s:
                    p = s.split(":", 1)
                    cat, items = escape_latex(p[0].strip()), escape_latex(p[1].strip())
                else:
                    cat, items = escape_latex(t["default_skill_cat"]), escape_latex(s)
            if items:
                sk_lines.append(rf"    \item \textbf{{{cat}:}} {items}")
        sk_lines.append(r"\end{itemize}")
        sk_block = "\n".join(sk_lines)

    # Publications & Awards & Languages
    pub_block = _build_publications_block(cv.get("publications") or [], lang)
    lg_aw_block = _build_languages_and_awards_block(cv.get("languages") or [], cv.get("awards") or [], lang)

    if resume_type == "academico":
        ordered = [sum_block, edu_block, pub_block, pj_block, xp_block, sk_block, lg_aw_block]
    else:
        ordered = [sum_block, xp_block, pj_block, edu_block, sk_block, pub_block, lg_aw_block]

    body_tex = "\n\n".join(b for b in ordered if b)

    return rf"""% Template Google Standard (Big Tech / Software Engineer) — Gayle Laakmann McDowell Standard
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=0.5in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{0B57D0}}
\definecolor{{sidecolor}}{{HTML}}{{1F1F1F}}
\definecolor{{graytext}}{{HTML}}{{444746}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\large\bfseries\scshape\color{{sidecolor}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{7pt}}{{3pt}}

\begin{{document}}
{header_tex}
{body_tex}
\end{{document}}
"""


def _render_ai_ats_max(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo Otimizado para IA & ATS (Máxima Legibilidade por LLMs e Parsers Neurais).

    Características arquiteturais essenciais:
    - Fluxo textual 100% linear em coluna única (sem colunas paralelas que quebram o fluxo de leitura de parsers de PDF).
    - Metadados semânticos explícitos (TAGS textuais ASCII: LOCATION, EMAIL, PHONE, GITHUB, LINKEDIN).
    - Mapeamento nativo Unicode (glyphtounicode e pdfgentounicode=1).
    - Matriz de Competências e Palavras-Chave (Core Competencies & Keywords) dedicada para match semântico em embeddings.
    - Seções padrão em caixa alta universalmente indexadas por ATS (Workday, Greenhouse, Lever, Taleo) e LLMs.
    """
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    name = escape_latex(cv.get("name") or t["default_candidate"])
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_professional"]
    title = escape_latex(cv.get("title") or default_tl)

    contact_parts: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        contact_parts.append(rf"\mbox{{\href{{mailto:{escape_url(em)}}}{{\faIcon{{envelope}}\ {escape_latex(em)}}}}}")
    if cv.get("phone"):
        contact_parts.append(rf"\mbox{{\faIcon{{phone}}\ {escape_latex(cv['phone'].strip())}}}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        contact_parts.append(rf"\mbox{{\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=name))
        contact_parts.append(rf"\mbox{{\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}}}")

    if len(contact_parts) > 4:
        mid = (len(contact_parts) + 1) // 2
        row1 = " \\quad | \\quad ".join(contact_parts[:mid])
        row2 = " \\quad | \\quad ".join(contact_parts[mid:])
        contact_str = f"{row1}\\\\[3pt]\n    {row2}"
    else:
        contact_str = " \\quad | \\quad ".join(contact_parts)

    header_tex = rf"""\begin{{center}}
    {{\LARGE\bfseries\color{{sidecolor}} {name}}}\\[3pt]
    {{\large\bfseries\color{{accent}} {title}}}\\[5pt]
    {{\footnotesize {contact_str}}}
\end{{center}}
\vspace{{2pt}}
\hrule height 0.75pt
\vspace{{5pt}}"""

    blocks: List[str] = []

    # 1. Summary
    if cv.get("summary"):
        sum_title = "PROFESSIONAL SUMMARY" if is_en else "RESUMO PROFISSIONAL"
        blocks.append(
            rf"\section*{{{sum_title}}}"
            + "\n"
            + rf"{{\normalsize {escape_latex(cv['summary'])}}}"
        )

    # 2. Dedicated Core Competencies & Keywords (Crucial for AI screening / ATS matching)
    skills = cv.get("skills") or []
    if skills:
        kw_title = r"CORE COMPETENCIES \& KEYWORDS" if is_en else r"COMPETÊNCIAS PRINCIPAIS \& PALAVRAS-CHAVE"
        kw_lines = [rf"\section*{{{kw_title}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for sk in skills:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category") or t["default_skill_cat"])
                items = escape_latex(sk.get("items"))
            else:
                cat = escape_latex(t["default_skill_cat"])
                items = escape_latex(str(sk).strip())
            if items:
                kw_lines.append(rf"    \item \textbf{{{cat}:}} {items}")
        kw_lines.append(r"\end{itemize}")
        blocks.append("\n".join(kw_lines))

    # 3. Experience
    exps = cv.get("experience") or []
    if exps:
        exp_title = "PROFESSIONAL EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
        xp_lines = [rf"\section*{{{exp_title}}}"]
        for xp in exps:
            role = escape_latex(xp.get("role"))
            org = escape_latex(xp.get("organization"))
            per = escape_latex(xp.get("period"))
            bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
            head_txt = f"{role} | {org}" if org else role
            xp_lines.append(rf"\noindent\textbf{{{head_txt}}} \hfill \textbf{{{per}}}")
            if bullets:
                xp_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                for b in bullets:
                    xp_lines.append(rf"    \item {b}")
                xp_lines.append(r"\end{itemize}")
                xp_lines.append(r"\vspace{3pt}")
            else:
                xp_lines.append(r"\par\vspace{3pt}")
        blocks.append("\n".join(xp_lines))

    # 4. Education
    edus = cv.get("education") or []
    if edus:
        edu_title = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
        ed_lines = [rf"\section*{{{edu_title}}}"]
        for ed in edus:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            inst_txt = f" --- {inst}" if inst else ""
            ed_lines.append(rf"\noindent\textbf{{{deg}}}{inst_txt} \hfill \textbf{{{per}}}")
            if det:
                ed_lines.append(rf"\par{{\small {det}}}\par\vspace{{4pt}}")
            else:
                ed_lines.append(r"\par\vspace{4pt}")
        blocks.append("\n\n".join(ed_lines))

    # 5. Projects
    projs = cv.get("projects") or []
    if projs:
        proj_title = "TECHNICAL PROJECTS" if is_en else "PROJETOS TÉCNICOS"
        pj_lines = [rf"\section*{{{proj_title}}}"]
        for pj in projs:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(pj.get("description"))
            if url and url.startswith("http"):
                nm_head = rf"\href{{{escape_url(url)}}}{{\textbf{{{nm}}}\ \footnotesize\faIcon{{external-link-alt}}}}"
            else:
                nm_head = rf"\textbf{{{nm}}}"
            tech_txt = f" [Stack: {tech}]" if tech else ""
            pj_lines.append(rf"\noindent{nm_head}{tech_txt}")
            if desc:
                pj_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]")
                pj_lines.append(rf"    \item {desc}")
                pj_lines.append(r"\end{itemize}")
                pj_lines.append(r"\vspace{2pt}")
            else:
                pj_lines.append(r"\par\vspace{2pt}")
        blocks.append("\n".join(pj_lines))

    # 6. Publications
    pubs = cv.get("publications") or []
    if pubs:
        pub_title = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        blocks.append(rf"\section*{{{pub_title}}}" + "\n" + _build_publications_block(pubs, lang).replace(rf"\section*{{{t['sec_publications']}}}", "").strip())

    # 7. Certifications & Awards
    clean_awards = sanitize_awards(cv.get("awards"))
    if clean_awards:
        aw_title = r"CERTIFICATIONS \& AWARDS" if is_en else r"CERTIFICAÇÕES \& PRÊMIOS"
        aw_lines = [rf"\section*{{{aw_title}}}", r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt,partopsep=0pt,parsep=0pt]"]
        for aw in clean_awards:
            aw_lines.append(rf"    \item {escape_latex(aw)}")
        aw_lines.append(r"\end{itemize}")
        blocks.append("\n".join(aw_lines))

    # 8. Languages
    langs = cv.get("languages") or []
    if langs:
        lg_title = "LANGUAGES" if is_en else "IDIOMAS"
        lg_str = " $\\cdot$ ".join(escape_latex(x) for x in langs if str(x).strip())
        blocks.append(rf"\section*{{{lg_title}}}" + "\n" + lg_str)

    body_tex = "\n\n".join(b for b in blocks if b)

    return rf"""% Template AI & ATS Max-Readability (LLM & Neural ATS Evaluators)
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=0.6in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fontawesome5}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{etoolbox}}

\input{{glyphtounicode}}
\pdfgentounicode=1

\raggedbottom
\setlist{{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt}}
\definecolor{{accent}}{{HTML}}{{1E293B}}
\definecolor{{sidecolor}}{{HTML}}{{0F172A}}
\definecolor{{graytext}}{{HTML}}{{334155}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{sidecolor}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{3pt}}

\begin{{document}}
{header_tex}
{body_tex}
\end{{document}}
"""


def _render_nico_krieger(
    cv: Dict[str, Any],
    links: Dict[str, str],
    resume_type: str,
    photo_filename: str | None,
    lang: str = "pt-br",
) -> str:
    """Renderiza o modelo 'Modelo Nico Krieger' (https://www.overleaf.com/latex/templates/my-resume/rqzfybxqvpny)."""
    t = LATEX_I18N[normalize_lang(lang)]
    is_en = normalize_lang(lang) == "en-us"
    raw_name = cv.get("name") or t["default_candidate"]
    default_tl = t["default_researcher"] if resume_type == "academico" else t["default_tech_title"]
    role = escape_latex(cv.get("title") or default_tl)

    # 1. Header (Name, Title, Tagline, optional Photo)
    tagline_raw = cv.get("summary") or ""
    tagline_short = escape_latex(tagline_raw[:180] + ("..." if len(tagline_raw) > 180 else "")) if tagline_raw else ""

    if photo_filename:
        header_tex = rf"""\begin{{tcolorbox}}[
    enhanced,
    colback=headerbg,
    colframe=headerbg,
    arc=0mm,
    left=12mm,
    right=12mm,
    top=8mm,
    bottom=8mm,
    boxrule=0mm,
    width=\paperwidth
]
\begin{{minipage}}[c]{{0.78\linewidth}}
    {{\Huge\bfseries\color{{white}} {escape_latex(raw_name)}}}\\[3pt]
    {{\large\color{{white!90}} {role}}}\\[3pt]
    {{\small\color{{white!75}} {tagline_short}}}
\end{{minipage}}%
\hfill
\begin{{minipage}}[c]{{0.18\linewidth}}
    \raggedleft
    \includegraphics[width=2.4cm,height=2.4cm,keepaspectratio]{{{photo_filename}}}
\end{{minipage}}
\end{{tcolorbox}}"""
    else:
        header_tex = rf"""\begin{{tcolorbox}}[
    enhanced,
    colback=headerbg,
    colframe=headerbg,
    arc=0mm,
    left=12mm,
    right=12mm,
    top=8mm,
    bottom=8mm,
    boxrule=0mm,
    width=\paperwidth
]
\begin{{minipage}}[c]{{\linewidth}}
    {{\Huge\bfseries\color{{white}} {escape_latex(raw_name)}}}\\[3pt]
    {{\large\color{{white!90}} {role}}}\\[3pt]
    {{\small\color{{white!75}} {tagline_short}}}
\end{{minipage}}
\end{{tcolorbox}}"""

    # 2. Contacts (Strictly: email -> phone -> location -> portfolio -> linkedin -> github -> orcid -> lattes)
    sidebar_contacts: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        sidebar_contacts.append(rf"\faIcon{{envelope}}\ \href{{{escape_url('mailto:' + em)}}}{{{escape_latex(em)}}}")
    if cv.get("phone"):
        sidebar_contacts.append(rf"\faIcon{{phone}}\ {escape_latex(cv['phone'])}")
    if cv.get("location"):
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())
        sidebar_contacts.append(rf"\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'].strip())}}}")
    if links.get("portfolio"):
        port_disp = escape_latex(simplify_url_display(links["portfolio"]))
        sidebar_contacts.append(rf"\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}")
    if links.get("linkedin"):
        li_disp = escape_latex(_get_platform_display(links, "linkedin", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}")
    if links.get("github"):
        gh_disp = escape_latex(_get_platform_display(links, "github", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}")
    if links.get("orcid"):
        orcid_disp = escape_latex(_get_platform_display(links, "orcid", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}")
    if links.get("scholar"):
        sc_disp = escape_latex(_get_platform_display(links, "scholar", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['scholar'])}}}{{\faIcon{{google}}\ \textbf{{{sc_disp}}}}}")
    if links.get("lattes"):
        lattes_disp = escape_latex(_get_platform_display(links, "lattes", candidate_name=raw_name))
        sidebar_contacts.append(rf"\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}")

    contact_lbl = "CONTACT" if is_en else "CONTATO"
    contact_body = r"\\[4pt]" + "\n    ".join(sidebar_contacts) if sidebar_contacts else ""
    contact_block = rf"""{{\large\bfseries\color{{accent}} {contact_lbl}}}\\[-2pt]
\rule{{\linewidth}}{{0.8pt}}\\[5pt]
\small
{contact_body}"""

    # 3. Skills with 5-dot rating
    skill_lbl = "SKILLS" if is_en else "HABILIDADES"
    skill_lines: List[str] = [rf"{{\large\bfseries\color{{accent}} {skill_lbl}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[5pt]"]
    skills = cv.get("skills") or []
    if skills:
        for sk in skills:
            if isinstance(sk, dict):
                cat = escape_latex(sk.get("category") or t["default_skill_cat"])
                raw_items = str(sk.get("items") or "")
                parts = [p.strip() for p in raw_items.split(",") if p.strip()]
                if parts:
                    skill_lines.append(rf"{{\small\bfseries\color{{darktext}} {cat}}}\\[2pt]")
                    for idx, p in enumerate(parts[:5]):
                        rating = 5 if idx == 0 else (4 if idx < 3 else 3)
                        skill_lines.append(rf"{{\small {escape_latex(p)}}} \hfill \skilldots{{{rating}}}\\[3pt]")
                    skill_lines.append(r"\vspace{3pt}")
            elif isinstance(sk, str) and sk.strip():
                parts = [p.strip() for p in sk.split(",") if p.strip()]
                for idx, p in enumerate(parts[:6]):
                    rating = 5 if idx == 0 else (4 if idx < 3 else 3)
                    skill_lines.append(rf"{{\small\textbf{{{escape_latex(p)}}}}} \hfill \skilldots{{{rating}}}\\[3pt]")
        skill_block = "\n".join(skill_lines)
    else:
        skill_block = ""

    # 4. Languages with 5-dot rating
    lang_lbl = "LANGUAGES" if is_en else "IDIOMAS"
    lang_lines: List[str] = [rf"{{\large\bfseries\color{{accent}} {lang_lbl}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[5pt]"]
    languages = cv.get("languages") or []
    if languages:
        for lg in languages:
            lg_str = str(lg).strip()
            if not lg_str:
                continue
            lower_lg = lg_str.lower()
            if any(k in lower_lg for k in ("nativo", "native", "fluente", "fluent", "avançado", "advanced", "5")):
                rating = 5
            elif any(k in lower_lg for k in ("intermediário", "intermediate", "pleno", "4")):
                rating = 4
            else:
                rating = 3
            clean_name = re.sub(r"\s*[\(\[].*?[\)\]]", "", lg_str).strip() or lg_str
            lang_lines.append(rf"{{\small\textbf{{{escape_latex(clean_name)}}}}} \hfill \skilldots{{{rating}}}\\[3pt]")
        lang_block = "\n".join(lang_lines)
    else:
        lang_block = ""

    # 5. Certifications & Awards in Sidebar
    clean_awards = sanitize_awards(cv.get("awards"))
    aw_lbl = r"CERTIFICATIONS \& AWARDS" if is_en else r"CERTIFICAÇÕES \& PRÊMIOS"
    if clean_awards:
        aw_lines = [rf"{{\large\bfseries\color{{accent}} {aw_lbl}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[5pt]"]
        for aw in clean_awards[:4]:
            aw_lines.append(rf"{{\small $\cdot$ {escape_latex(aw)}}}\\[3pt]")
        awards_block = "\n".join(aw_lines)
    else:
        awards_block = ""

    sidebar_sections = [s for s in (contact_block, skill_block, lang_block, awards_block) if s]
    sidebar_content = "\n\n\\vspace{10pt}\n\n".join(sidebar_sections)

    # 6. Main Column: Experience, Education, Projects, Publications
    main_sections: List[str] = []

    # Experience
    exps = cv.get("experience") or []
    if exps:
        exp_title = "PROFESSIONAL EXPERIENCE" if is_en else "EXPERIÊNCIA PROFISSIONAL"
        xp_lines = [rf"{{\large\bfseries\color{{accent}} {exp_title}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[6pt]"]
        for xp in exps:
            role_xp = escape_latex(xp.get("role"))
            org_xp = escape_latex(xp.get("organization"))
            per_xp = escape_latex(xp.get("period"))
            bullets = [escape_latex(b) for b in (xp.get("bullets") or []) if str(b).strip()]
            date_tex = rf"{{\small\color{{graytext}}\faIcon{{calendar-alt}}\ {per_xp}}}" if per_xp else ""
            xp_lines.append(rf"\textbf{{\large {role_xp}}} \hfill {date_tex}\\[1pt]")
            if org_xp:
                xp_lines.append(rf"{{\color{{accent}}\textbf{{{org_xp}}}}}\\[3pt]")
            if bullets:
                xp_lines.append(r"\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=1pt]")
                for b in bullets:
                    xp_lines.append(rf"    \item {b}")
                xp_lines.append(r"\end{itemize}")
            xp_lines.append(r"\vspace{6pt}")
        main_sections.append("\n".join(xp_lines))

    # Education
    edus = cv.get("education") or []
    if edus:
        edu_title = "EDUCATION" if is_en else "FORMAÇÃO ACADÊMICA"
        ed_lines = [rf"{{\large\bfseries\color{{accent}} {edu_title}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[6pt]"]
        for ed in edus:
            deg = escape_latex(ed.get("degree"))
            inst = escape_latex(ed.get("institution"))
            per_ed = escape_latex(ed.get("period"))
            det = escape_latex(ed.get("details"))
            date_tex = rf"{{\small\color{{graytext}}\faIcon{{calendar-alt}}\ {per_ed}}}" if per_ed else ""
            ed_lines.append(rf"\textbf{{\large {deg}}} \hfill {date_tex}\\[1pt]")
            if inst:
                ed_lines.append(rf"{{\color{{accent}}\textbf{{{inst}}}}}\\[2pt]")
            if det:
                ed_lines.append(rf"{{\small {det}}}\\[4pt]")
            else:
                ed_lines.append(r"\vspace{4pt}")
        main_sections.append("\n".join(ed_lines))

    # Projects
    projs = cv.get("projects") or []
    if projs:
        proj_title = "TECHNICAL PROJECTS" if is_en else "PROJETOS TÉCNICOS"
        pj_lines = [rf"{{\large\bfseries\color{{accent}} {proj_title}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[6pt]"]
        for pj in projs:
            nm = escape_latex(pj.get("name"))
            tech = escape_latex(pj.get("tech"))
            url = (pj.get("url") or "").strip()
            desc = escape_latex(pj.get("description"))
            if url and url.startswith("http"):
                nm_head = rf"\textbf{{\large \href{{{escape_url(url)}}}{{{nm}\ \small\faIcon{{external-link-alt}}}}}}"
            else:
                nm_head = rf"\textbf{{\large {nm}}}"
            pj_lines.append(rf"{nm_head}\\[1pt]")
            if tech:
                pj_lines.append(rf"{{\small\color{{graytext}}\textbf{{Stack:}} {tech}}}\\[2pt]")
            if desc:
                pj_lines.append(rf"{{\small {desc}}}\\[4pt]")
            else:
                pj_lines.append(r"\vspace{4pt}")
        main_sections.append("\n".join(pj_lines))

    # Publications
    pubs = cv.get("publications") or []
    if pubs:
        pub_title = "PUBLICATIONS" if is_en else "PUBLICAÇÕES"
        pb_lines = [rf"{{\large\bfseries\color{{accent}} {pub_title}}}\\[-2pt]", r"\rule{\linewidth}{0.8pt}\\[6pt]"]
        for pb in pubs:
            title_pb = escape_latex(pb.get("title"))
            auth_pb = escape_latex(pb.get("authors"))
            venue_pb = escape_latex(pb.get("venue"))
            yr_pb = escape_latex(pb.get("year"))
            doi_pb = (pb.get("doi") or "").strip()
            pb_lines.append(rf"\textbf{{{title_pb}}}\\[1pt]")
            meta_parts = [p for p in (auth_pb, f"{venue_pb} ({yr_pb})" if (venue_pb and yr_pb) else (venue_pb or yr_pb)) if p]
            if meta_parts:
                pb_lines.append(rf"{{\small {', '.join(meta_parts)}}}\\[1pt]")
            if doi_pb:
                clean_doi = doi_pb.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
                doi_url = f"https://doi.org/{clean_doi}"
                pb_lines.append(rf"{{\small \href{{{escape_url(doi_url)}}}{{\faIcon{{link}}\ DOI: {escape_latex(clean_doi)}}}}}\\[4pt]")
            else:
                pb_lines.append(r"\vspace{4pt}")
        main_sections.append("\n".join(pb_lines))

    main_content = "\n\n\\vspace{8pt}\n\n".join(main_sections)

    return rf"""% Template Nico Krieger (my-resume) - Full-Width Dark Header & Two-Column Highlight Sidebar
\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage[margin=0cm,noheadfoot]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{tikz}}
\usepackage[skins]{{tcolorbox}}
\usepackage{{fontawesome5}}
\usepackage{{enumitem}}
\usepackage{{parskip}}
\usepackage[hidelinks]{{hyperref}}

\definecolor{{headerbg}}{{HTML}}{{212529}}
\definecolor{{sidebg}}{{HTML}}{{F8F9FA}}
\definecolor{{accent}}{{HTML}}{{DC3545}}
\definecolor{{darktext}}{{HTML}}{{212529}}
\definecolor{{graytext}}{{HTML}}{{6C757D}}
\definecolor{{lightgray}}{{HTML}}{{DEE2E6}}

\renewcommand{{\familydefault}}{{\sfdefault}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\skilldots}}[1]{{%
  \begin{{tikzpicture}}[baseline=-0.35ex]%
    \foreach \x in {{1,...,5}}{{%
      \ifnum\x>#1\relax%
        \fill[lightgray] (\x*0.28cm,0) circle (2.2pt);%
      \else%
        \fill[accent] (\x*0.28cm,0) circle (2.2pt);%
      \fi%
    }}%
  \end{{tikzpicture}}%
}}

\begin{{document}}

{header_tex}

\vspace{{-1.5mm}}
\noindent
\begin{{minipage}}[t]{{0.33\paperwidth}}
\begin{{tcolorbox}}[
    enhanced,
    colback=sidebg,
    colframe=sidebg,
    arc=0mm,
    boxrule=0mm,
    left=8mm,
    right=8mm,
    top=6mm,
    bottom=8mm
]
{sidebar_content}
\end{{tcolorbox}}
\end{{minipage}}%
\hspace{{0.02\paperwidth}}%
\begin{{minipage}}[t]{{0.61\paperwidth}}
\vspace{{6mm}}
\begin{{minipage}}{{0.96\linewidth}}
{main_content}
\end{{minipage}}
\end{{minipage}}

\end{{document}}
"""
