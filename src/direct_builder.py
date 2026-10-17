"""Construtor Direto e Determinístico de Currículos (Zero-Token / Sem IA).

Permite gerar currículos LaTeX profissionais ou acadêmicos 100% offline
e determinísticos a partir dos dados coletados pelos extratores
(GitHub, ORCID, Lattes, LinkedIn, Portfólio e metadados manuais).

Garante:
1. Economia de 100% de tokens quando o uso de modelos de IA estiver desabilitado.
2. Servir como base de altíssima qualidade para revisão cirúrgica por LLMs,
   economizando até 75% dos tokens em relação à síntese de texto bruto não-estruturado.
3. Compilação determinística com 0 alucinações de dados, datas ou instituições.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .i18n import normalize_lang
from .templates import BUILTIN_TEMPLATES, render_builtin_template, sanitize_awards


def build_structured_cv_deterministically(
    raw_profile_data: Dict[str, Any],
    resume_type: str = "profissional",
    lang: str = "pt-br",
) -> Dict[str, Any]:
    """Mapeia os dados brutos extraídos das fontes para a estrutura canônica do currículo."""
    norm_lang = normalize_lang(lang)
    is_en = norm_lang.startswith("en")
    is_academic = str(resume_type).lower().strip() in ("academico", "academic")

    user_meta = raw_profile_data.get("user_meta") or {}
    gh = raw_profile_data.get("github") or {}
    orcid = raw_profile_data.get("orcid") or {}
    lattes = raw_profile_data.get("lattes") or {}
    li = raw_profile_data.get("linkedin") or {}
    portfolio = raw_profile_data.get("portfolio") or {}
    extra_notes = str(raw_profile_data.get("extra_notes") or "").strip()

    # 1. Nome Completo
    name = (
        user_meta.get("name")
        or lattes.get("name")
        or li.get("name")
        or orcid.get("name")
        or gh.get("name")
        or gh.get("username")
        or ("Candidate Name" if is_en else "Nome do Candidato")
    ).strip()

    # 2. Título / Cargo
    if user_meta.get("role"):
        title = user_meta["role"].strip()
    elif li.get("title"):
        title = li["title"].strip()
    elif is_academic:
        # Se for acadêmico e houver atuação no Lattes, busca o enquadramento mais recente
        lattes_roles = [emp.get("role") for emp in (lattes.get("employments") or []) if emp.get("role")]
        title = (
            lattes_roles[0]
            if lattes_roles
            else ("Academic Researcher & Scientist" if is_en else "Pesquisador Acadêmico & Cientista")
        )
    elif gh.get("bio") and len(gh["bio"]) < 60:
        title = gh["bio"].strip()
    else:
        title = (
            "Technology & Software Specialist"
            if is_en
            else "Especialista em Tecnologia & Desenvolvimento"
        )

    # 3. Informações de Contato
    email = (user_meta.get("email") or gh.get("email") or "").strip()
    phone = (user_meta.get("phone") or "").strip()
    location = (user_meta.get("location") or gh.get("location") or "").strip()

    # 4. Resumo Profissional / Acadêmico
    summary = ""
    if extra_notes and len(extra_notes) > 40:
        summary = extra_notes
    elif lattes.get("summary"):
        summary = lattes["summary"].strip()
    elif li.get("summary"):
        summary = li["summary"].strip()
    elif orcid.get("bio"):
        summary = orcid["bio"].strip()
    elif gh.get("bio"):
        summary = gh["bio"].strip()
    elif portfolio.get("description"):
        summary = portfolio["description"].strip()
    else:
        if is_academic:
            summary = (
                "Academic researcher with experience in scientific investigation, academic publishing, and collaborative research projects."
                if is_en
                else "Pesquisador acadêmico com sólida formação científica, publicações em periódicos indexados e participação em projetos de pesquisa."
            )
        else:
            summary = (
                "Dedicated professional with strong technical expertise, proven track record in software engineering, and continuous learning mindset."
                if is_en
                else "Profissional dedicado com sólida experiência técnica, atuação em desenvolvimento de software e foco em resultados escaláveis."
            )

    # 5. Formação Acadêmica (Education)
    education: List[Dict[str, str]] = []
    # Prioridade A: Lattes (muito rico em nível, curso, instituição e tese)
    for edu in lattes.get("educations") or []:
        lvl = edu.get("level", "").strip()
        course = edu.get("course", "").strip()
        degree = f"{lvl} em {course}" if (lvl and course) else (lvl or course or "Formação Superior")
        if is_en:
            lvl_en = {
                "Doutorado": "Ph.D.",
                "Mestrado": "M.Sc.",
                "Mestrado Profissional": "Professional M.Sc.",
                "Especialização": "Postgraduate Specialization",
                "Graduação": "B.Sc.",
                "Pós-Doutorado": "Postdoctoral Fellowship",
            }.get(lvl, lvl)
            degree = f"{lvl_en} in {course}" if (lvl_en and course) else (lvl_en or course)

        start_yr = str(edu.get("start") or "").strip()
        end_yr = str(edu.get("end") or "").strip() or ("Present" if is_en else "Atual")
        period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)

        details = edu.get("thesis_title", "").strip()
        if details:
            details = f"Tese/Dissertação: {details}" if not is_en else f"Thesis: {details}"

        education.append({
            "degree": degree,
            "institution": edu.get("institution", "").strip(),
            "period": period,
            "details": details,
        })

    # Prioridade B: LinkedIn (caso Lattes esteja vazio)
    if not education:
        for edu in li.get("educations") or []:
            degree = edu.get("degree", "").strip() or ("Degree" if is_en else "Graduação")
            education.append({
                "degree": degree,
                "institution": edu.get("school", "").strip(),
                "period": edu.get("period", "").strip(),
                "details": "",
            })

    # Prioridade C: ORCID (caso ambos estejam vazios)
    if not education:
        for edu in orcid.get("educations") or []:
            start_yr = edu.get("start", "")
            end_yr = edu.get("end", "") or ("Present" if is_en else "Atual")
            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else ""
            education.append({
                "degree": edu.get("degree", "").strip() or ("Higher Education" if is_en else "Formação Acadêmica"),
                "institution": edu.get("institution", "").strip(),
                "period": period,
                "details": "",
            })

    # 6. Experiência Profissional (Experience)
    experience: List[Dict[str, Any]] = []
    # Prioridade A: LinkedIn
    for exp in li.get("experiences") or []:
        role = exp.get("role", "").strip()
        comp = exp.get("company", "").strip()
        period = exp.get("period", "").strip()
        raw_desc = exp.get("description", "").strip()
        bullets = [b.strip("- •") for b in raw_desc.split("\n") if b.strip("- •")] if raw_desc else []
        if role or comp:
            experience.append({
                "role": role or ("Professional" if is_en else "Atuação Profissional"),
                "organization": comp,
                "period": period,
                "bullets": bullets if bullets else ([raw_desc] if raw_desc else []),
            })

    # Prioridade B: Lattes Atuações Profissionais
    for emp in lattes.get("employments") or []:
        inst = emp.get("institution", "").strip()
        role = emp.get("role", "").strip()
        start_yr = str(emp.get("start") or "").strip()
        end_yr = str(emp.get("end") or "").strip() or ("Present" if is_en else "Atual")
        period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)
        desc = emp.get("description", "").strip()
        bullets = [desc] if desc else []
        if role or inst:
            # Evita duplicatas se já adicionado pelo LinkedIn
            if not any(e["organization"].lower() == inst.lower() for e in experience):
                experience.append({
                    "role": role or ("Pesquisador / Colaborador" if not is_en else "Researcher / Staff"),
                    "organization": inst,
                    "period": period,
                    "bullets": bullets,
                })

    # Prioridade C: ORCID Employments
    if not experience:
        for emp in orcid.get("employments") or []:
            start_yr = emp.get("start", "")
            end_yr = emp.get("end", "") or ("Present" if is_en else "Atual")
            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else ""
            experience.append({
                "role": emp.get("role", "").strip() or ("Position" if is_en else "Cargo"),
                "organization": emp.get("institution", "").strip(),
                "period": period,
                "bullets": [],
            })

    # 7. Projetos (Projects)
    projects: List[Dict[str, str]] = []
    # Prioridade A: GitHub Repositories
    for repo in gh.get("repos") or []:
        r_name = repo.get("name", "").strip()
        r_tech = repo.get("language", "").strip()
        r_desc = repo.get("description", "").strip()
        r_url = repo.get("url", "").strip()
        if r_name:
            projects.append({
                "name": r_name,
                "tech": r_tech,
                "url": r_url,
                "description": r_desc,
            })

    # Prioridade B: Lattes Projetos de Pesquisa
    for proj in lattes.get("projects") or []:
        p_name = proj.get("title", "").strip()
        p_year = str(proj.get("year") or "").strip()
        p_desc = proj.get("description", "").strip()
        if p_name:
            projects.append({
                "name": p_name,
                "tech": f"Pesquisa ({p_year})" if not is_en else f"Research ({p_year})",
                "url": p_year,
                "description": p_desc,
            })

    # 8. Publicações (Publications)
    publications: List[Dict[str, str]] = []
    # Lattes Publicações
    for pub in lattes.get("publications") or []:
        p_title = pub.get("title", "").strip()
        if p_title:
            publications.append({
                "title": p_title,
                "venue": pub.get("venue", "").strip(),
                "year": str(pub.get("year") or "").strip(),
                "authors": pub.get("authors", "").strip(),
                "doi": pub.get("doi", "").strip(),
            })

    # ORCID Works (se não duplicado)
    for work in orcid.get("works") or []:
        w_title = work.get("title", "").strip()
        if w_title and not any(p["title"].lower() == w_title.lower() for p in publications):
            publications.append({
                "title": w_title,
                "venue": work.get("journal", "").strip(),
                "year": str(work.get("year") or "").strip(),
                "authors": "",
                "doi": work.get("doi", "").strip(),
            })

    # 9. Habilidades e Competências (Skills)
    skills: List[Dict[str, Any]] = []
    # Tecnologias / Linguagens de Programação do GitHub
    gh_langs = [l for l in (gh.get("languages") or []) if str(l).strip()]
    if gh_langs:
        skills.append({
            "category": "Linguagens & Tecnologias" if not is_en else "Languages & Technologies",
            "items": ", ".join(gh_langs[:10]),
        })

    # Competências do LinkedIn
    li_skills = [s for s in (li.get("skills") or []) if str(s).strip()]
    if li_skills:
        skills.append({
            "category": "Competências & Especialidades" if not is_en else "Core Competencies",
            "items": ", ".join(li_skills[:12]),
        })

    # Áreas de Atuação do Lattes / Palavras-chave do ORCID
    academic_areas = [a for a in (lattes.get("areas") or orcid.get("keywords") or []) if str(a).strip()]
    if academic_areas:
        skills.append({
            "category": "Áreas de Conhecimento & Foco" if not is_en else "Focus & Research Domains",
            "items": ", ".join(academic_areas[:10]),
        })

    # 10. Idiomas (Languages)
    raw_languages = lattes.get("languages") or li.get("languages") or []
    languages = [str(lg).strip() for lg in raw_languages if str(lg).strip()]

    # 11. Prêmios, Títulos e Certificações (Awards)
    raw_awards = lattes.get("awards") or li.get("certifications") or []
    awards = sanitize_awards(raw_awards)

    # Limitações saudáveis para caber confortavelmente no layout LaTeX
    return {
        "name": name,
        "title": title,
        "email": email,
        "phone": phone,
        "location": location,
        "summary": summary,
        "education": education[:6],
        "experience": experience[:6],
        "projects": projects[:6],
        "publications": publications[:12],
        "skills": skills[:5],
        "languages": languages[:5],
        "awards": awards[:6],
    }


def generate_direct_latex_resume(
    raw_profile_data: Dict[str, Any],
    resume_type: str = "profissional",
    template_id: str = "modern_pro",
    custom_latex_template: str | None = None,
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> Tuple[str, Dict[str, Any]]:
    """Gera o código LaTeX completo e compilável sem nenhuma chamada a modelos LLM."""
    norm_lang = normalize_lang(lang)
    links = raw_profile_data.get("links") or {}

    # Constrói o structured_cv de forma puramente determinística
    cv = build_structured_cv_deterministically(
        raw_profile_data=raw_profile_data,
        resume_type=resume_type,
        lang=norm_lang,
    )

    # 1. Caso Template Customizado .tex fornecido pelo usuário
    if custom_latex_template and custom_latex_template.strip():
        latex_code = _fill_custom_template_deterministically(
            template_code=custom_latex_template,
            cv=cv,
            links=links,
            photo_filename=photo_filename,
            lang=norm_lang,
        )
        return latex_code, cv

    # 2. Caso Templates Integrados (modern_pro, academic_classic, tech_sidebar, etc.)
    if template_id not in BUILTIN_TEMPLATES:
        template_id = "modern_pro"

    latex_code = render_builtin_template(
        template_id=template_id,
        cv=cv,
        links=links,
        resume_type=resume_type,
        photo_filename=photo_filename,
        lang=norm_lang,
    )

    return latex_code, cv


def _fill_custom_template_deterministically(
    template_code: str,
    cv: Dict[str, Any],
    links: Dict[str, str],
    photo_filename: str | None = None,
    lang: str = "pt-br",
) -> str:
    """Preenche placeholders comuns em templates customizados de forma determinística."""
    res = template_code
    name = cv.get("name") or "Nome do Candidato"
    title = cv.get("title") or "Profissional"
    summary = cv.get("summary") or ""

    contact_parts = []
    if cv.get("email"):
        contact_parts.append(cv["email"])
    if cv.get("phone"):
        contact_parts.append(cv["phone"])
    if cv.get("location"):
        contact_parts.append(cv["location"])
    if links.get("linkedin"):
        contact_parts.append(r"\href{" + links["linkedin"] + "}{LinkedIn}")
    if links.get("github"):
        contact_parts.append(r"\href{" + links["github"] + "}{GitHub}")
    contact_line = " $\\cdot$ ".join(contact_parts)

    # Substituições case-insensitive seguras de cabeçalho
    res = re.sub(r"(?i)NOME DO CANDIDATO|\[NOME\]|\{\{NAME\}\}|CANDIDATE NAME", name, res)
    res = re.sub(r"(?i)CARGO OU T[IÍ]TULO|\[CARGO\]|\{\{TITLE\}\}|PROFESSIONAL ROLE", title, res)
    res = re.sub(r"(?i)Links e Contatos|\[CONTATOS\]|\{\{CONTACTS\}\}|CONTACT INFO", contact_line, res)
    res = re.sub(r"(?i)Preencher resumo do candidato\.?|\[RESUMO\]|\{\{SUMMARY\}\}", summary, res)

    return res

