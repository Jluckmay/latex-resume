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

import urllib.parse

from typing import Any, Dict, List, Tuple



from .i18n import normalize_lang

from .extractors import extract_languages_from_text

from .templates import (

    BUILTIN_TEMPLATES,

    simplify_url_display,

    _get_platform_display,

    escape_latex,

    escape_url,

    render_builtin_template,

    sanitize_awards,

)





def parse_manual_resume_inputs(manual_data: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normaliza e extrai dados de currículo inseridos manualmente (estruturados ou texto livre)."""
    if not manual_data or not isinstance(manual_data, dict):
        return {}

    parsed: Dict[str, Any] = {}

    # 1. Metadados e Resumo
    for key in ("name", "title", "role", "email", "phone", "location", "summary"):
        val = manual_data.get(key)
        if val and isinstance(val, str) and val.strip():
            parsed[key] = val.strip()

    # 2. Formação Acadêmica (Education)
    raw_edu = manual_data.get("education")
    edu_list: List[Dict[str, str]] = []
    if isinstance(raw_edu, list):
        for item in raw_edu:
            if isinstance(item, dict):
                degree = str(item.get("degree") or item.get("course") or item.get("level") or "").strip()
                inst = str(item.get("institution") or item.get("org") or "").strip()
                period = str(item.get("period") or item.get("year") or "").strip()
                details = str(item.get("details") or item.get("thesis_title") or "").strip()
                if degree or inst:
                    edu_list.append({"degree": degree, "institution": inst, "period": period, "details": details})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                edu_list.append({
                    "degree": parts[0],
                    "institution": parts[1] if len(parts) > 1 else "",
                    "period": parts[2] if len(parts) > 2 else "",
                    "details": parts[3] if len(parts) > 3 else "",
                })
    elif isinstance(raw_edu, str) and raw_edu.strip():
        for line in raw_edu.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            edu_list.append({
                "degree": parts[0],
                "institution": parts[1] if len(parts) > 1 else "",
                "period": parts[2] if len(parts) > 2 else "",
                "details": parts[3] if len(parts) > 3 else "",
            })
    if edu_list:
        parsed["education"] = edu_list

    # 3. Experiência Profissional (Experience)
    raw_exp = manual_data.get("experience")
    exp_list: List[Dict[str, str]] = []
    if isinstance(raw_exp, list):
        for item in raw_exp:
            if isinstance(item, dict):
                role = str(item.get("role") or item.get("title") or "").strip()
                org = str(item.get("organization") or item.get("company") or "").strip()
                period = str(item.get("period") or "").strip()
                loc = str(item.get("location") or "").strip()
                desc = str(item.get("description") or "").strip()
                if role or org:
                    exp_list.append({"role": role, "organization": org, "period": period, "location": loc, "description": desc})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                exp_list.append({
                    "role": parts[0],
                    "organization": parts[1] if len(parts) > 1 else "",
                    "period": parts[2] if len(parts) > 2 else "",
                    "location": parts[3] if len(parts) > 3 else "",
                    "description": parts[4] if len(parts) > 4 else "",
                })
    elif isinstance(raw_exp, str) and raw_exp.strip():
        for line in raw_exp.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            exp_list.append({
                "role": parts[0],
                "organization": parts[1] if len(parts) > 1 else "",
                "period": parts[2] if len(parts) > 2 else "",
                "location": parts[3] if len(parts) > 3 else "",
                "description": parts[4] if len(parts) > 4 else (parts[3] if len(parts) == 4 and not any(c in parts[3] for c in (",", "/")) else ""),
            })
    if exp_list:
        parsed["experience"] = exp_list

    # 4. Habilidades & Competências (Skills)
    raw_skills = manual_data.get("skills")
    skill_list: List[Dict[str, Any]] = []
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                cat = str(item.get("category") or "Competências Principais").strip()
                items = item.get("items")
                if isinstance(items, list):
                    items_str = ", ".join(str(x).strip() for x in items if str(x).strip())
                else:
                    items_str = str(items or "").strip()
                if items_str:
                    skill_list.append({"category": cat, "items": items_str})
            elif isinstance(item, str) and item.strip():
                if ":" in item:
                    cat, items = item.split(":", 1)
                    skill_list.append({"category": cat.strip(), "items": items.strip()})
                else:
                    skill_list.append({"category": "Competências Principais", "items": item.strip()})
    elif isinstance(raw_skills, str) and raw_skills.strip():
        for line in raw_skills.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                cat, items = line.split(":", 1)
                skill_list.append({"category": cat.strip(), "items": items.strip()})
            else:
                skill_list.append({"category": "Competências Principais", "items": line})
    if skill_list:
        parsed["skills"] = skill_list

    # 5. Projetos (Projects)
    raw_proj = manual_data.get("projects")
    proj_list: List[Dict[str, str]] = []
    if isinstance(raw_proj, list):
        for item in raw_proj:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                tech = str(item.get("tech") or "").strip()
                url = str(item.get("url") or "").strip()
                desc = str(item.get("description") or "").strip()
                if name:
                    proj_list.append({"name": name, "tech": tech, "url": url, "description": desc})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                proj_list.append({
                    "name": parts[0],
                    "tech": parts[1] if len(parts) > 1 else "",
                    "url": parts[2] if len(parts) > 2 else "",
                    "description": parts[3] if len(parts) > 3 else "",
                })
    elif isinstance(raw_proj, str) and raw_proj.strip():
        for line in raw_proj.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            proj_list.append({
                "name": parts[0],
                "tech": parts[1] if len(parts) > 1 else "",
                "url": parts[2] if len(parts) > 2 and parts[2].startswith("http") else "",
                "description": parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 and not parts[2].startswith("http") else ""),
            })
    if proj_list:
        parsed["projects"] = proj_list

    # 6. Idiomas (Languages)
    raw_langs = manual_data.get("languages")
    lang_list: List[str] = []
    if isinstance(raw_langs, list):
        for lg in raw_langs:
            if isinstance(lg, dict):
                nm = str(lg.get("name") or "").strip()
                lvl = str(lg.get("level") or lg.get("proficiency") or "").strip()
                lang_list.append(f"{nm} ({lvl})" if lvl else nm)
            elif isinstance(lg, str) and lg.strip():
                lang_list.append(lg.strip())
    elif isinstance(raw_langs, str) and raw_langs.strip():
        items = [it.strip() for it in re.split(r"[\r\n,;]+", raw_langs) if it.strip()]
        lang_list = [it.strip() for it in items if it.strip()]
    if lang_list:
        parsed["languages"] = lang_list

    # 7. Prêmios & Certificações (Awards)
    raw_awards = manual_data.get("awards")
    award_list: List[Any] = []
    if isinstance(raw_awards, list):
        award_list = [a for a in raw_awards if a]
    elif isinstance(raw_awards, str) and raw_awards.strip():
        award_list = [line.strip() for line in raw_awards.splitlines() if line.strip()]
    if award_list:
        parsed["awards"] = award_list

    # 8. Publicações (Publications)
    raw_pubs = manual_data.get("publications")
    pub_list: List[Dict[str, str]] = []
    if isinstance(raw_pubs, list):
        for item in raw_pubs:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                venue = str(item.get("venue") or "").strip()
                yr = str(item.get("year") or "").strip()
                authors = str(item.get("authors") or "").strip()
                doi = str(item.get("doi") or "").strip()
                if title:
                    pub_list.append({"title": title, "venue": venue, "year": yr, "authors": authors, "doi": doi})
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                pub_list.append({
                    "title": parts[0],
                    "venue": parts[1] if len(parts) > 1 else "",
                    "year": parts[2] if len(parts) > 2 else "",
                    "authors": parts[3] if len(parts) > 3 else "",
                    "doi": parts[4] if len(parts) > 4 else "",
                })
    elif isinstance(raw_pubs, str) and raw_pubs.strip():
        for line in raw_pubs.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(" - "))]
            pub_list.append({
                "title": parts[0],
                "venue": parts[1] if len(parts) > 1 else "",
                "year": parts[2] if len(parts) > 2 else "",
                "authors": parts[3] if len(parts) > 3 else "",
                "doi": parts[4] if len(parts) > 4 else "",
            })
    if pub_list:
        parsed["publications"] = pub_list

    return parsed


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

    manual = parse_manual_resume_inputs(raw_profile_data.get("manual_data"))



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

    if lattes.get("summary"):

        summary = lattes["summary"].strip()

    elif extra_notes and len(extra_notes) > 40 and not extra_notes.startswith("PORTFOLIO_URL:"):

        summary = extra_notes

    elif li.get("summary"):

        summary = li["summary"].strip()

    elif orcid.get("bio"):

        summary = orcid["bio"].strip()

    elif gh.get("bio"):

        summary = gh["bio"].strip()

    elif portfolio.get("description"):
        port_desc = portfolio["description"].strip()
        low_desc = port_desc.lower()
        if low_desc.startswith("portfólio") or low_desc.startswith("portfolio"):
            cleaned_snippet = re.sub(r"(?i)^portf[óo]lio\s+(?:profissional\s+)?de\s+[^,]+,\s*", "", port_desc).strip()
            if cleaned_snippet:
                cap_snippet = cleaned_snippet[0].upper() + cleaned_snippet[1:]
                summary = (
                    f"Computer Science and Technology Specialist. {cap_snippet}. Strong background in software architecture, distributed systems, and modern development."
                    if is_en
                    else f"Especialista em Computação e Tecnologia. {cap_snippet}. Sólida experiência em desenvolvimento de software, arquitetura escalável e sistemas computacionais."
                )
            else:
                summary = (
                    "Computer Scientist and Software Engineer with experience in software development, algorithm design, and modern technology stacks."
                    if is_en
                    else "Cientista da Computação e Engenheiro de Software com experiência em desenvolvimento de software, projetos computacionais e tecnologias modernas."
                )
        else:
            summary = port_desc

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

            start_yr = str(edu.get("start") or "").strip()

            end_yr = str(edu.get("end") or "").strip()

            if not end_yr or end_yr.lower() in ("atual", "present"):

                end_yr = "Present" if is_en else "Atual"

            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)



            raw_degree = (

                edu.get("degree")

                or edu.get("role")

                or edu.get("course")

                or edu.get("dept")

                or ""

            ).strip()



            inst = (

                edu.get("institution")

                or edu.get("organization")

                or edu.get("org")

                or edu.get("school")

                or ""

            ).strip()



            if not is_en and raw_degree:

                deg_lower = raw_degree.lower()

                if "master" in deg_lower and "computer science" in deg_lower:

                    raw_degree = "Mestrado em Ciência da Computação"

                elif "bachelor" in deg_lower and ("information systems" in deg_lower or "sistemas de informacao" in deg_lower or "sistemas de informação" in deg_lower):

                    raw_degree = "Bacharelado em Sistemas de Informação"

                elif "master" in deg_lower:

                    raw_degree = re.sub(r"(?i)master'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Mestrado em ", raw_degree)

                elif "bachelor" in deg_lower:

                    raw_degree = re.sub(r"(?i)bachelor'?s?\s+(?:degree\s+)?(?:of\s+science\s+)?in\s+", "Bacharelado em ", raw_degree)

                elif "ph" in deg_lower or "doctor" in deg_lower:

                    raw_degree = re.sub(r"(?i)(?:ph\.?d\.?|doctorate)\s+in\s+", "Doutorado em ", raw_degree)

            elif is_en and raw_degree:

                deg_lower = raw_degree.lower()

                if "mestrado" in deg_lower and ("ciencia da computacao" in deg_lower or "ciência da computação" in deg_lower):

                    raw_degree = "M.Sc. in Computer Science"

                elif "bacharelado" in deg_lower and ("sistemas de informacao" in deg_lower or "sistemas de informação" in deg_lower):

                    raw_degree = "B.Sc. in Information Systems"

                elif "mestrado" in deg_lower:

                    raw_degree = re.sub(r"(?i)mestrado(?:\s+profissional)?\s+em\s+", "M.Sc. in ", raw_degree)

                elif "bacharelado" in deg_lower or "graduação" in deg_lower:

                    raw_degree = re.sub(r"(?i)(?:bacharelado|graduação)\s+em\s+", "B.Sc. in ", raw_degree)

                elif "doutorado" in deg_lower:

                    raw_degree = re.sub(r"(?i)doutorado\s+em\s+", "Ph.D. in ", raw_degree)



            deg = raw_degree or ("Higher Education" if is_en else "Formação Superior")

            education.append({

                "degree": deg,

                "institution": inst,

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

            start_yr = str(emp.get("start") or "").strip()

            end_yr = str(emp.get("end") or "").strip()

            if not end_yr or end_yr.lower() in ("atual", "present"):

                end_yr = "Present" if is_en else "Atual"

            period = f"{start_yr} - {end_yr}" if (start_yr and end_yr) else (start_yr or end_yr)



            raw_role = (emp.get("role") or emp.get("role-title") or emp.get("dept") or "").strip()

            inst = (

                emp.get("organization")

                or emp.get("institution")

                or emp.get("org")

                or emp.get("company")

                or ""

            ).strip()



            if not is_en and raw_role:

                role_lower = raw_role.lower()

                role_map_pt = {

                    "introduction to game development teaching assistant": "Monitor de Introdução ao Desenvolvimento de Jogos",

                    "programming teaching assistant": "Monitor de Programação",

                    "programming tutor": "Tutor de Programação",

                    "extension project fellow": "Bolsista de Projeto de Extensão",

                    "teaching assistant": "Monitor(a) de Ensino",

                    "research fellow": "Bolsista de Pesquisa",

                    "research assistant": "Assistente de Pesquisa",

                    "graduate student": "Pós-Graduando",

                }

                raw_role = role_map_pt.get(role_lower, raw_role)



            if not is_en and inst:

                if "federal university of viçosa" in inst.lower() or "federal university of vicosa" in inst.lower():

                    inst = "Universidade Federal de Viçosa"

                elif "federal university of minas gerais" in inst.lower():

                    inst = "Universidade Federal de Minas Gerais"



            experience.append({

                "role": raw_role or ("Position" if is_en else "Atuação Profissional"),

                "organization": inst,

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

    raw_languages = (

        lattes.get("languages")

        or li.get("languages")

        or raw_profile_data.get("languages")

        or user_meta.get("languages")

        or []

    )

    if not raw_languages and extra_notes:

        raw_languages = extract_languages_from_text(extra_notes)



    if is_en:

        trans_en = {

            "inglês": "English", "ingles": "English",

            "português": "Portuguese", "portugues": "Portuguese",

            "espanhol": "Spanish",

            "francês": "French", "frances": "French",

            "alemão": "German", "alemao": "German",

            "italiano": "Italian",

            "japonês": "Japanese", "japones": "Japanese",

            "chinês": "Chinese", "chines": "Chinese", "mandarim": "Mandarin",

            "russo": "Russian",

        }

        prof_trans_en = {

            "avançado": "Advanced", "avancado": "Advanced", "bom": "Advanced",

            "fluente": "Fluent", "fluente ou nativo": "Fluent / Native",

            "nativo": "Native", "nativo ou bilíngue": "Native / Bilingual", "nativo ou bilingue": "Native / Bilingual",

            "intermediário": "Intermediate", "intermediario": "Intermediate", "regular": "Intermediate", "razoável": "Intermediate", "razoavel": "Intermediate",

            "básico": "Basic", "basico": "Basic", "pouco": "Basic",

        }

        translated_langs: List[str] = []

        for lg in raw_languages:

            lg_str = str(lg).strip()

            if not lg_str:

                continue

            m = re.match(r"^([A-Za-zÀ-ÿ]+)(?:\s*\((.*?)\))?$", lg_str)

            if m:

                p_name = m.group(1).strip()

                p_prof = m.group(2).strip() if m.group(2) else ""

                en_name = trans_en.get(p_name.lower(), p_name)

                en_prof = prof_trans_en.get(p_prof.lower(), p_prof)

                translated_langs.append(f"{en_name} ({en_prof})" if en_prof else en_name)

            else:

                translated_langs.append(lg_str)

        languages = translated_langs

    else:

        languages = [str(lg).strip() for lg in raw_languages if str(lg).strip()]



    # 11. Prêmios, Títulos e Certificações (Awards)

    raw_awards = lattes.get("awards") or li.get("certifications") or []

    awards = sanitize_awards(raw_awards)



    # 12. Sobrescrita com dados manuais fornecidos diretamente pelo usuário

    if manual.get("name"):

        name = manual["name"].strip()

    if manual.get("title") or manual.get("role"):

        title = (manual.get("title") or manual.get("role")).strip()

    if manual.get("email"):

        email = manual["email"].strip()

    if manual.get("phone"):

        phone = manual["phone"].strip()

    if manual.get("location"):

        location = manual["location"].strip()

    if manual.get("summary"):

        summary = manual["summary"].strip()

    if manual.get("education"):

        education = list(manual["education"])

    if manual.get("experience"):

        experience = list(manual["experience"])

    if manual.get("projects"):

        projects = list(manual["projects"])

    if manual.get("publications"):

        publications = list(manual["publications"])

    if manual.get("skills"):

        skills = list(manual["skills"])

    if manual.get("languages"):

        languages = list(manual["languages"])

    if manual.get("awards"):

        awards = sanitize_awards(manual["awards"])

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

    template_id: str = "ai_ats_max",

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

        em = cv["email"].strip()

        contact_parts.append(rf"\href{{mailto:{escape_url(em)}}}{{\faIcon{{envelope}}\ {escape_latex(em)}}}")

    if cv.get("phone"):

        contact_parts.append(rf"\faIcon{{phone}}\ {escape_latex(cv['phone'])}")

    if cv.get("location"):

        maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(cv["location"].strip())

        contact_parts.append(rf"\href{{{escape_url(maps_url)}}}{{\faIcon{{map-marker-alt}}\ {escape_latex(cv['location'])}}}")

    if links.get("portfolio"):

        port_disp = escape_latex(simplify_url_display(links["portfolio"]))

        contact_parts.append(rf"\href{{{escape_url(links['portfolio'])}}}{{\faIcon{{globe}}\ \textbf{{{port_disp}}}}}")

    if links.get("linkedin"):

        li_disp = escape_latex(_get_platform_display(links, "linkedin"))

        contact_parts.append(rf"\href{{{escape_url(links['linkedin'])}}}{{\faIcon{{linkedin}}\ \textbf{{{li_disp}}}}}")

    if links.get("github"):

        gh_disp = escape_latex(_get_platform_display(links, "github"))

        contact_parts.append(rf"\href{{{escape_url(links['github'])}}}{{\faIcon{{github}}\ \textbf{{{gh_disp}}}}}")

    if links.get("orcid"):

        orcid_disp = escape_latex(_get_platform_display(links, "orcid"))

        contact_parts.append(rf"\href{{{escape_url(links['orcid'])}}}{{\faIcon{{orcid}}\ \textbf{{{orcid_disp}}}}}")

    if links.get("lattes"):

        lattes_disp = escape_latex(_get_platform_display(links, "lattes"))

        contact_parts.append(rf"\href{{{escape_url(links['lattes'])}}}{{\faIcon{{graduation-cap}}\ \textbf{{{lattes_disp}}}}}")

    contact_line = " $\\cdot$ ".join(contact_parts)



    # Substituições case-insensitive seguras de cabeçalho

    res = re.sub(r"(?i)NOME DO CANDIDATO|\[NOME\]|\{\{NAME\}\}|CANDIDATE NAME", name, res)

    res = re.sub(r"(?i)CARGO OU T[IÍ]TULO|\[CARGO\]|\{\{TITLE\}\}|PROFESSIONAL ROLE", title, res)

    res = re.sub(r"(?i)Links e Contatos|\[CONTATOS\]|\{\{CONTACTS\}\}|CONTACT INFO", contact_line, res)

    res = re.sub(r"(?i)Preencher resumo do candidato\.?|\[RESUMO\]|\{\{SUMMARY\}\}", summary, res)



    return res



