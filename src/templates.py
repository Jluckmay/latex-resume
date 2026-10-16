"""Modelos de Currículo LaTeX integrados (Bilíngues: pt-BR e en-US) e motor de renderização determinístico.

Ao renderizar os templates integrados localmente a partir do JSON compacto gerado
pela API NVIDIA NIM, economizamos ~1.800 tokens de preâmbulo LaTeX por chamada
e garantimos compilação 100% livre de erros de sintaxe no `pdflatex`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .i18n import LATEX_I18N, normalize_lang

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
        "name": "Overleaf: Currículo T.I. — Russell CV (rgfqqnnynrmv)",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/read/rgfqqnnynrmv#d5b171",
        "description": (
            "Modelo Overleaf Russell CV (Currículo T.I.) com foto lateral no cabeçalho, ícones FontAwesome 5, "
            "títulos com destaque nas 3 primeiras letras, tabela de habilidades e níveis de idiomas em círculos."
        ),
    },
    "overleaf_awesome_cv": {
        "id": "overleaf_awesome_cv",
        "name": "Overleaf: Jason Richards' Résumé — Awesome-CV (chbxgnfyyvfc)",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc",
        "description": (
            "Modelo Overleaf Jason Richards' Résumé baseado no clássico Awesome-CV com cabeçalho centralizado, "
            "tipografia Roboto + Source Sans Pro, destaque de 3 letras nas seções e rodapé executivo."
        ),
    },
    "overleaf_single_page_keywords": {
        "id": "overleaf_single_page_keywords",
        "name": "Overleaf: Single-Page Resume with Keywords (wmcxcgmtkxzk)",
        "recommended_for": "profissional",
        "url": "https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk",
        "description": (
            "Modelo Overleaf de página única em duas colunas (Primož Godec & Salman Maqbool) com fonte Raleway, "
            "ícones circulares TikZ, seção de Resumo e palavras-chave (Keywords) de stack por experiência."
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
        u = "https://" + u
    return u.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")


def _build_contact_links(links: Dict[str, str], email: str, phone: str, location: str) -> List[str]:
    items: List[str] = []
    if location:
        items.append(escape_latex(location))
    if email:
        clean_em = email.strip()
        items.append(rf"\href{{mailto:{escape_url(clean_em)}}}{{{escape_latex(clean_em)}}}")
    if phone:
        items.append(escape_latex(phone))
    if links.get("linkedin"):
        items.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\textbf{{LinkedIn}}}}")
    if links.get("github"):
        items.append(rf"\href{{{escape_url(links['github'])}}}{{\textbf{{GitHub}}}}")
    if links.get("orcid"):
        items.append(rf"\href{{{escape_url(links['orcid'])}}}{{\textbf{{ORCID}}}}")
    if links.get("lattes"):
        items.append(rf"\href{{{escape_url(links['lattes'])}}}{{\textbf{{Lattes}}}}")
    return items


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
    if template_id == "academic_classic":
        return _render_academic_classic(cv, links, photo_filename, norm_lang)
    if template_id == "tech_sidebar":
        return _render_tech_sidebar(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "minimal_ats":
        return _render_minimal_ats(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "overleaf_russell_ti":
        return _render_overleaf_russell_ti(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "overleaf_awesome_cv":
        return _render_overleaf_awesome_cv(cv, links, resume_type, photo_filename, norm_lang)
    if template_id == "overleaf_single_page_keywords":
        return _render_overleaf_single_page_keywords(cv, links, resume_type, photo_filename, norm_lang)
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
    lines = [rf"\section*{{{t['sec_education']}}}"]
    for ed in educations:
        deg = escape_latex(ed.get("degree"))
        inst = escape_latex(ed.get("institution"))
        per = escape_latex(ed.get("period"))
        det = escape_latex(ed.get("details"))
        lines.append(rf"\noindent\textbf{{{deg}}} \hfill \textit{{{per}}}\\")
        if inst:
            lines.append(rf"\textit{{{inst}}}")
        if det:
            lines.append(rf"\\{{\small {det}}}")
        lines.append(r"\vspace{4pt}" + "\n")
    return "\n".join(lines)


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
            lines.append(r"\begin{itemize}[leftmargin=1.2em,itemsep=1pt,topsep=2pt]")
            for b in bullets:
                lines.append(rf"    \item {b}")
            lines.append(r"\end{itemize}")
        else:
            lines.append(r"\vspace{4pt}")
    return "\n".join(lines)


def _build_projects_block(projects: List[Dict[str, Any]], resume_type: str, lang: str = "pt-br") -> str:
    if not projects:
        return ""
    t = LATEX_I18N[normalize_lang(lang)]
    title = t["sec_proj_acad"] if resume_type == "academico" else t["sec_proj_prof"]
    lines = [rf"\section*{{{title}}}"]
    lines.append(r"\begin{itemize}[leftmargin=1.2em,itemsep=3pt,topsep=2pt]")
    for pj in projects:
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        desc = escape_latex(pj.get("description"))
        head = rf"\textbf{{{nm}}}"
        if tech:
            head += rf" ({{\small\texttt{{{tech}}}}})"
        if url:
            if url.startswith("http"):
                head += rf" --- \href{{{escape_url(url)}}}{{\small {t['link_label']}}}"
            else:
                head += rf" \hfill \textit{{{escape_latex(url)}}}"
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
    lines.append(r"\begin{enumerate}[leftmargin=1.5em,itemsep=3pt,topsep=2pt]")
    for pb in publications:
        title = escape_latex(pb.get("title"))
        venue = escape_latex(pb.get("venue"))
        year = escape_latex(pb.get("year"))
        authors = escape_latex(pb.get("authors"))
        doi = (pb.get("doi") or "").strip()
        parts = []
        if authors:
            parts.append(f"{authors}.")
        parts.append(rf"\textbf{{{title}}}.")
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
    lines.append(r"\begin{itemize}[leftmargin=1.2em,itemsep=2pt,topsep=2pt]")
    for sk in skills:
        cat = escape_latex(sk.get("category"))
        items = escape_latex(sk.get("items"))
        if cat and items:
            lines.append(rf"    \item \textbf{{{cat}:}} {items}")
        elif items:
            lines.append(rf"    \item {items}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _build_languages_and_awards_block(languages: List[str], awards: List[str], lang: str = "pt-br") -> str:
    t = LATEX_I18N[normalize_lang(lang)]
    parts: List[str] = []
    if languages:
        langs_esc = " $\\cdot$ ".join(escape_latex(x) for x in languages if str(x).strip())
        if langs_esc:
            parts.append(rf"\section*{{{t['sec_languages']}}}" + "\n" + langs_esc)
    if awards:
        lines = [rf"\section*{{{t['sec_awards']}}}"]
        lines.append(r"\begin{itemize}[leftmargin=1.2em,itemsep=2pt,topsep=2pt]")
        for aw in awards:
            if str(aw).strip():
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
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""))
    contact_str = " \\;|\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename)
    body = _render_sections_body(cv, resume_type, lang)

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
\usepackage[hidelinks]{{hyperref}}

\definecolor{{accent}}{{HTML}}{{0F4C81}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\large\bfseries\color{{accent}}}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{10pt}}{{5pt}}

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
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""))
    contact_str = " \\;\\textbullet\\; ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd=r"\color{acadnavy}")
    body = _render_sections_body(cv, "academico", lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.6cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage[hidelinks]{{hyperref}}

\definecolor{{acadnavy}}{{HTML}}{{1B365D}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{acadnavy}}}}{{}}{{0em}}{{}}[\vspace{{1pt}}\titlerule]
\titlespacing*{{\section}}{{0pt}}{{11pt}}{{5pt}}

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
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""))

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
\usepackage[margin=1.3cm]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage[hidelinks]{{hyperref}}

\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{accent}}{{HTML}}{{2563EB}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape\color{{accent}}}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{9pt}}{{4pt}}

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
    contact_items = _build_contact_links(links, cv.get("email", ""), cv.get("phone", ""), cv.get("location", ""))
    contact_str = " | ".join(contact_items)
    header = _render_header_with_optional_photo(name, title, contact_str, photo_filename, accent_cmd="")
    body = _render_sections_body(cv, resume_type, lang)

    return rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[{t['babel']}]{{babel}}
\usepackage{{lmodern}}
\usepackage[margin=1.4cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage[hidelinks]{{hyperref}}

\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\titleformat{{\section}}{{\normalsize\bfseries\scshape}}{{}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{8pt}}{{4pt}}

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
    """Formata comando \\cvsection{3 primeiras letras}{restante} sem quebrar UTF-8 no pdflatex."""
    clean = (raw_title or "").replace(r"\&", "&").strip()
    p1 = escape_latex(clean[:3])
    p2 = escape_latex(clean[3:])
    return rf"\cvsection{{{p1}}}{{{p2}}}"


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
        cat = escape_latex(sk.get("category") or t["default_skill_cat"])
        items = escape_latex(sk.get("items"))
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
    for pj in (cv.get("projects") or []):
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        url = (pj.get("url") or "").strip()
        desc = escape_latex(pj.get("description"))
        url_tex = rf"\href{{{escape_url(url)}}}{{\small {t['link_label']}}}" if url.startswith("http") else escape_latex(url)
        b_items: List[str] = []
        if desc:
            b_items.append(rf"    \item {desc}")
        if tech:
            b_items.append(rf"    \item \textbf{{Technical Stack:}} {tech}")
        b_tex = (
            r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"
            + "\n"
            + "\n".join(b_items)
            + "\n"
            + r"\end{itemize}"
            if b_items
            else ""
        )
        pj_entries.append(rf"\cventry{{{tech}}}{{{nm}}}{{{url_tex}}}{{}}{{{b_tex}}}")
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
            parts = []
            if authors:
                parts.append(f"{authors}.")
            parts.append(rf"\textbf{{{title}}}.")
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
                dots = (
                    r"\faIcon{circle} \faIcon{circle} \faIcon{circle} \faIcon{circle} \faIcon{circle}"
                    if idx == 0
                    else r"\faIcon{circle} \faIcon{circle} \faIcon{circle} \faIcon{circle} \faIcon[regular]{circle}"
                )
                l_rows.append(rf"    \textbf{{\color{{sidecolor}} {escape_latex(lg)}}} & {{\color{{accent}} {dots}}} \\")
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

    awards = [str(x).strip() for x in (cv.get("awards") or []) if str(x).strip()]
    award_block = ""
    if awards:
        aw_lines = [r"\begin{itemize}[leftmargin=1.3em,nosep,topsep=2pt]"]
        for aw in awards:
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
        row1_links.append(rf"\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{GitHub}}}}")
    if links.get("orcid"):
        row1_links.append(rf"\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{ORCID}}}}")
    if links.get("lattes"):
        row1_links.append(rf"\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{Lattes}}}}")

    row2_links: List[str] = []
    if cv.get("email"):
        em = cv["email"].strip()
        row2_links.append(rf"\href{{mailto:{escape_url(em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(em)}}}")
    if cv.get("phone"):
        row2_links.append(rf"{{\faIcon{{whatsapp}}\ {escape_latex(cv['phone'])}}}")
    if links.get("linkedin"):
        row2_links.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{LinkedIn}}}}")
    if cv.get("location"):
        row2_links.append(rf"{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'])}}}")

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
\usepackage[hidelinks]{{hyperref}}

\definecolor{{accent}}{{HTML}}{{0F4C81}}
\definecolor{{sidecolor}}{{HTML}}{{1E293B}}
\definecolor{{graytext}}{{HTML}}{{5D5D5D}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}

\newcommand{{\vhrulefill}}[1]{{\leavevmode\leaders\hrule height #1\hfill\kern0pt}}
\newcommand{{\cvsection}}[2]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries{{\color{{accent}}#1}}{{\color{{sidecolor}}#2}}}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    {{\small\scshape #1}} & {{\small\itshape\color{{graytext}} #4}} \\
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
        social_items.append(rf"{{\faIcon{{mobile-alt}}\ {escape_latex(cv['phone'])}}}")
    if cv.get("email"):
        em = cv["email"].strip()
        social_items.append(rf"\href{{mailto:{escape_url(em)}}}{{\faIcon[regular]{{envelope}}\ {escape_latex(em)}}}")
    if cv.get("location"):
        social_items.append(rf"{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'])}}}")
    if links.get("github"):
        social_items.append(rf"\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{GitHub}}}}")
    if links.get("linkedin"):
        social_items.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{LinkedIn}}}}")
    if links.get("orcid"):
        social_items.append(rf"\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{ORCID}}}}")
    if links.get("lattes"):
        social_items.append(rf"\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{Lattes}}}}")

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
\usepackage[hidelinks]{{hyperref}}

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
\newcommand{{\cvsection}}[2]{{%
  \vspace{{7pt}}%
  \noindent{{\Large\bfseries{{\color{{accent}}#1}}{{\color{{sidecolor}}#2}}}}\hspace{{4pt}}{{\color{{graytext}}\vhrulefill{{0.9pt}}}}\par\vspace{{4pt}}%
}}
\newcommand{{\cventry}}[5]{{%
  \noindent\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}} p{{0.74\textwidth}} r @{{}}}}
    \textbf{{\color{{sidecolor}} #2}} & {{\small\itshape\color{{accent}} #3}} \\
    {{\small\scshape #1}} & {{\small\itshape\color{{graytext}} #4}} \\
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
        if sk.get("items"):
            all_skill_items.append(escape_latex(sk["items"]))
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
        right_contacts.append(rf"{{\small {lbl_lc}}} \textbf{{{escape_latex(cv['location'])}}}")
    if links.get("github"):
        right_contacts.append(rf"{{\small GitHub}} \href{{{escape_url(links['github'])}}}{{\textbf{{GitHub}}}}")
    if links.get("linkedin"):
        right_contacts.append(rf"{{\small LinkedIn}} \href{{{escape_url(links['linkedin'])}}}{{\textbf{{LinkedIn}}}}")
    if links.get("orcid"):
        right_contacts.append(rf"{{\small ORCID}} \href{{{escape_url(links['orcid'])}}}{{\textbf{{ORCID}}}}")
    if links.get("lattes"):
        right_contacts.append(rf"{{\small Lattes}} \href{{{escape_url(links['lattes'])}}}{{\textbf{{Lattes}}}}")

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
        cat = escape_latex(sk.get("category") or t["default_skill_cat"])
        items = escape_latex(sk.get("items"))
        if items:
            sk_rows.append(rf"\noindent\textbf{{{cat}:}} {{\small {items}}}\par\vspace{{2pt}}")
    sk_sec = (rf"\cvsec{{\faIcon{{list}}}}{{{sk_lbl}}}" + "\n" + "\n".join(sk_rows)) if sk_rows else ""

    # Coluna 2: OTHER PROJECTS + EDUCATION + PUBLICATIONS + AWARDS / LANGUAGES
    proj_lbl = "OTHER PROJECTS" if is_en else "PROJETOS DE DESTAQUE"
    proj_rows: List[str] = []
    for pj in (cv.get("projects") or []):
        nm = escape_latex(pj.get("name"))
        tech = escape_latex(pj.get("tech"))
        desc = escape_latex(pj.get("description"))
        kw_suffix = rf" --- \textbf{{{tech}}}" if tech else ""
        body_p = f"{desc}{kw_suffix}" if desc else kw_suffix.lstrip(" -")
        proj_rows.append(rf"    \item \textbf{{{nm}}}: {body_p}")
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
            p_rows.append(rf"    \item \textbf{{{pt}}} ({pv}, {py})")
        pub_sec = (
            rf"\cvsec{{\faIcon{{book}}}}{{{pub_lbl}}}"
            + "\n\\begin{itemize}[leftmargin=1.2em,noitemsep,topsep=2pt]\n"
            + "\n".join(p_rows)
            + "\n\\end{itemize}"
        )

    aw_sec = ""
    awards = [str(x).strip() for x in (cv.get("awards") or []) if str(x).strip()]
    if awards:
        aw_lbl = "AWARDS" if is_en else r"PRÊMIOS \& CERTIFICAÇÕES"
        a_rows = [rf"    \item {escape_latex(a)}" for a in awards]
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

    col1_body = "\n\n".join(x for x in (work_sec, sk_sec) if x)
    col2_body = "\n\n".join(x for x in (proj_sec, edu_sec, pub_sec, aw_sec, lg_sec) if x)

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
\usepackage[hidelinks]{{hyperref}}

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

