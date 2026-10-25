"""Cliente multi-provedor (NVIDIA NIM, Google Gemini, Anthropic Claude, OpenAI, DeepSeek)
integrado ao cofre criptográfico efêmero e aos Plugins de Economia de Tokens.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from ._vault import dispatch_secure_llm_chat
from .compiler import sanitize_latex_layout
from .config import DEFAULT_MODEL, DEFAULT_PROVIDER, PROVIDERS_CONFIG
from .templates import render_builtin_template, sanitize_awards
from .token_plugins import (
    CavemanPromptPlugin,
    LaTeXPreambleSplitPlugin,
    SHA256DiskCachePlugin,
    ShortKeySchemaPlugin,
    ThinkingSuppressionPlugin,
    TokenMetrics,
    TOONContextPrunerPlugin,
    estimate_tokens,
)


class LLMResumeGenerator:
    """Orquestrador multi-provedor para síntese de currículos com isolamento seguro de chaves e economia de tokens."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        api_key: str | None = None,
        model: str | None = None,
        use_cache: bool = False,
    ) -> None:
        self.provider = (provider or DEFAULT_PROVIDER).strip().lower()
        self._custom_key = api_key.strip() if api_key and api_key.strip() else None

        prov_cfg = PROVIDERS_CONFIG.get(self.provider, PROVIDERS_CONFIG["default"])
        self.model = model or prov_cfg.get("default_model") or DEFAULT_MODEL
        self.use_cache = use_cache
        self.cache = SHA256DiskCachePlugin()

    def _call_llm_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1600,
    ) -> Tuple[str, Dict[str, Any], str, bool]:
        """Executa chamada segura ao provedor selecionado via TLS 1.3 e cofre em memória volátil."""
        cache_key = self.cache.make_key(f"{self.provider}:{self.model}", messages)
        is_latex_call = any(
            "\\begin{document}" in m.get("content", "") or "CAVEMAN_LATEX" in m.get("content", "")
            for m in messages
        )
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                if not is_latex_call or r"\end{document}" in cached:
                    return cached, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, self.model, True

        prov_cfg = PROVIDERS_CONFIG.get(self.provider, PROVIDERS_CONFIG["default"])
        models_to_try = [self.model] + [
            m["id"] for m in prov_cfg.get("models", []) if m["id"] != self.model
        ]

        last_err = None
        for candidate_model in models_to_try:
            status_code, parsed_data, err_str, usage = dispatch_secure_llm_chat(
                provider=self.provider,
                model=candidate_model,
                messages=messages,
                custom_key=self._custom_key,
                max_tokens=max_tokens,
                timeout=40,
            )
            if status_code != 200:
                last_err = err_str
                continue

            content = (parsed_data.get("content") or "").strip()
            if not content:
                last_err = f"Modelo {candidate_model} retornou conteúdo vazio"
                continue

            if is_latex_call and r"\end{document}" not in content:
                last_err = f"Modelo {candidate_model} retornou resposta LaTeX truncada (sem \\end{{document}})"
                continue

            if self.use_cache and content:
                self.cache.set(cache_key, content, candidate_model)
            return content, usage, candidate_model, False

        raise RuntimeError(
            f"Falha ao chamar modelos do provedor '{self.provider}'. Último status: {last_err}"
        )

    def generate_latex_resume(
        self,
        raw_profile_data: Dict[str, Any],
        resume_type: str = "profissional",
        template_id: str = "ai_ats_max",
        custom_latex_template: str | None = None,
        photo_filename: str | None = None,
        lang: str = "pt-br",
    ) -> Tuple[str, Dict[str, Any], TokenMetrics]:
        """Gera o código LaTeX final, o dicionário estruturado do CV e as métricas de tokens."""
        metrics = TokenMetrics(
            active_plugins=[
                CavemanPromptPlugin.name,
                ThinkingSuppressionPlugin.name,
                TOONContextPrunerPlugin.name,
            ]
        )

        # 1. Plugin TOON: comprime os dados de entrada (GitHub, ORCID, Lattes, LinkedIn, Portfólio)
        toon_context, raw_in_tok, comp_in_tok = TOONContextPrunerPlugin.compress_profile_data(raw_profile_data)
        metrics.raw_input_tokens_est = raw_in_tok
        metrics.compressed_input_tokens_est = comp_in_tok

        links = raw_profile_data.get("links") or {}

        # 2. Modo Template Customizado (.tex fornecido pelo usuário)
        if custom_latex_template and custom_latex_template.strip():
            metrics.active_plugins.append(LaTeXPreambleSplitPlugin.name)
            if self.use_cache:
                metrics.active_plugins.append(SHA256DiskCachePlugin.name)

            preamble, body_template, custom_cmds = LaTeXPreambleSplitPlugin.split_template(
                custom_latex_template
            )
            preamble_tokens_saved = estimate_tokens(preamble) * 2

            sys_prompt = CavemanPromptPlugin.build_system_prompt(resume_type, output_mode="latex", lang=lang)
            photo_instr = (
                f"Foto disponível no arquivo '{photo_filename}' (use \\includegraphics se o template suportar)."
                if photo_filename
                else "Sem foto enviada (remova/comente comandos de foto se houver no template)."
            )
            cmd_hint = f"Macros do preâmbulo: {', '.join(custom_cmds[:15])}\n" if custom_cmds else ""
            user_prompt = (
                f"LANG:{lang.upper()}|TIPO:{resume_type.upper()}\n"
                f"LINKS:LI={links.get('linkedin','')}|GH={links.get('github','')}|"
                f"ORCID={links.get('orcid','')}|LATTES={links.get('lattes','')}\n"
                f"{photo_instr}\n"
                f"{cmd_hint}"
                f"DADOS_PERFIL_TOON:\n{toon_context}\n\n"
                f"CORPO_TEMPLATE_LATEX:\n{body_template}\n\n"
                "Preencha o CORPO_TEMPLATE_LATEX com os DADOS_PERFIL_TOON reais. "
                "Retorne SOMENTE de \\begin{document} até \\end{document}."
            )

            content, usage, used_model, is_cached = self._call_llm_chat(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
            )
            clean_body = sanitize_latex_layout(CavemanPromptPlugin.strip_code_fences(content))
            if not clean_body or len(clean_body.strip()) < 30 or r"\end{document}" not in clean_body:
                raise ValueError("Resposta do modelo insuficiente ou incompleta (sem \\end{document}).")
            final_latex = sanitize_latex_layout(LaTeXPreambleSplitPlugin.reassemble(preamble, clean_body))
            if r"\end{document}" not in final_latex:
                final_latex = final_latex.rstrip() + "\n\\end{document}\n"
            self._populate_metrics(
                metrics,
                usage,
                used_model,
                is_cached,
                extra_saved=max(0, raw_in_tok - comp_in_tok) + preamble_tokens_saved + 600,
            )
            return final_latex, {"custom_template": True, "lang": lang}, metrics

        # 3. Modo Templates Integrados: Usa ShortKeySchemaPlugin + Renderização Local LaTeX
        metrics.active_plugins.extend(
            [
                ShortKeySchemaPlugin.name,
                "LaTeXLocalSkeletonPlugin (0-token LaTeX Preamble)",
            ]
        )
        if self.use_cache:
            metrics.active_plugins.append(SHA256DiskCachePlugin.name)

        sys_prompt = CavemanPromptPlugin.build_system_prompt(resume_type, output_mode="json", lang=lang)
        user_prompt = (
            f"LANG:{lang.upper()}|TIPO:{resume_type.upper()}\n"
            f"DADOS_TOON:\n{toon_context}\n\n"
            f"{ShortKeySchemaPlugin.PROMPT_SCHEMA_INSTRUCTION}"
        )

        content, usage, used_model, is_cached = self._call_llm_chat(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
        )

        short_dict = self._parse_json_safely(content, raw_profile_data, resume_type)
        structured_cv = ShortKeySchemaPlugin.expand(short_dict)
        self._apply_fallbacks(structured_cv, raw_profile_data, resume_type, lang)

        final_latex = render_builtin_template(
            template_id=template_id,
            cv=structured_cv,
            links=links,
            resume_type=resume_type,
            photo_filename=photo_filename,
            lang=lang,
        )

        extra_saved = max(0, raw_in_tok - comp_in_tok) + 1150
        self._populate_metrics(metrics, usage, used_model, is_cached, extra_saved=extra_saved)
        return final_latex, structured_cv, metrics

    def repair_latex_error(self, broken_latex: str, error_excerpt: str) -> str:
        """Reparo cirúrgico de LaTeX auditando sintaxe, caracteres de escape, ambientes e layout."""
        preamble, body, _ = LaTeXPreambleSplitPlugin.split_template(broken_latex)
        target = body if preamble else broken_latex
        messages = [
            {
                "role": "system",
                "content": (
                    "MODE:CAVEMAN_LATEX_REPAIR. Zero prose, zero fences. "
                    "Role: Senior LaTeX Debugger and Code Architect. "
                    "Analyze pdflatex compiler errors and fix broken LaTeX code. "
                    "1. SYNTAX AUDIT: Fix unclosed braces {}, unclosed environments (itemize, tabular, minipage), and broken macros. "
                    "2. ESCAPING AUDIT: Ensure %, &, $, #, _ in regular text are escaped (e.g. C\\#, R\\&D, 100\\%, PL/SQL). "
                    "3. ENTRY ISOLATION: Ensure every entry (education, experience, project) is cleanly isolated with \\par\\vspace{3pt} or blank lines so items never collide on the same line. "
                    "Output ONLY valid compilable LaTeX code."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"COMPILER_ERROR:\n{error_excerpt[:600]}\n\n"
                    f"BROKEN_LATEX:\n{target}\n\n"
                    "Fix all syntax, escaping, and formatting errors. Return valid compilable LaTeX code."
                ),
            },
        ]
        fixed, _, _, _ = self._call_llm_chat(messages=messages, max_tokens=4096)
        cleaned = sanitize_latex_layout(CavemanPromptPlugin.strip_code_fences(fixed))
        if not cleaned or len(cleaned.strip()) < 30 or r"\end{document}" not in cleaned:
            return broken_latex
        reassembled = LaTeXPreambleSplitPlugin.reassemble(preamble, cleaned) if preamble else cleaned
        if r"\end{document}" not in reassembled:
            reassembled = reassembled.rstrip() + "\n\\end{document}\n"
        return sanitize_latex_layout(reassembled)

    def review_and_enhance_latex(
        self,
        base_latex: str,
        resume_type: str = "profissional",
        instructions: str = "",
        lang: str = "pt-br",
    ) -> Tuple[str, TokenMetrics]:
        """Revisa e aprimora cirurgicamente o código LaTeX existente sem reconstruir do zero.

        Realiza revisão dupla: auditoria completa do código LaTeX (sintaxe, escape, espaçamento)
        e aprimoramento textual (verbos de ação, impacto, síntese de resumo).
        Economiza até ~75% dos tokens comparado com síntese direta a partir de páginas web brutas.
        Envia apenas o corpo do documento (\\begin{document} .. \\end{document}) com split de preâmbulo.
        """
        metrics = TokenMetrics(
            active_plugins=[
                "LaTeXReviewEngine",
                CavemanPromptPlugin.name,
                ThinkingSuppressionPlugin.name,
                LaTeXPreambleSplitPlugin.name,
            ]
        )
        preamble, body, _ = LaTeXPreambleSplitPlugin.split_template(base_latex)
        target = body if preamble else base_latex
        preamble_tokens_saved = estimate_tokens(preamble) * 2 if preamble else 0

        instruction_line = f"CUSTOM INSTRUCTION: {instructions.strip()}\n" if instructions.strip() else ""

        sys_prompt = (
            f"MODE:CAVEMAN_LATEX_CODE_AND_CONTENT_REVIEW. LANG:{lang.upper()}.\n"
            "Role: Senior LaTeX Architect & Executive Technical Resume Editor.\n"
            "Task: Perform a comprehensive dual review of the provided LaTeX resume body (LaTeX code audit + text content optimization).\n\n"
            "PART 1: LATEX CODE & TYPESETTING AUDIT\n"
            "1. SYNTAX & ENVIRONMENTS: Check and ensure all braces {} are balanced. Ensure all environments (\\begin{itemize} ... \\end{itemize}, minipage, tabular) are properly opened and closed.\n"
            r"2. SPECIAL CHARACTER ESCAPING: Audit all user text, company names, skills, URLs, and descriptions for unescaped reserved LaTeX characters. Ensure '%', '&', '$', '#', and '_' are properly escaped (e.g. C\#, C\texttt{++}, R\&D, PL/SQL, 100\%, \$1M, tech\_stack) while preserving LaTeX commands and math symbols (\cdot, \textbf, \hfill)." "\n"
            "3. ENTRY ISOLATION (ZERO COLLISION): Each education degree, job experience, or project entry MUST be an isolated paragraph block. Conclude each entry with \\par\\vspace{3pt} or a clean blank line. NEVER allow an institution, location, or details line to merge onto the same line as the next entry title or \\hfill.\n"
            "4. LINE BREAK & SPACING DISCIPLINE: Avoid awkward line breaks, overlapping text, or overfull boxes. Ensure clean vertical rhythm and correct use of \\par and \\vspace.\n"
            "5. MACRO PRESERVATION: Preserve existing template structure, commands, and styling macros (e.g. \\cventry, \\cvsection, \\cvskill, \\textbf, \\textit, \\href, \\color).\n\n"
            "PART 2: TEXT & CONTENT ENHANCEMENT\n"
            "1. ACTION VERBS & METRICS: Polish bullet points with high-impact, punchy action verbs and clear accomplishments in the target language.\n"
            "2. EXECUTIVE SUMMARY: If the summary/resumo section is sparse, missing, or contains generic website metadata (e.g. starting with 'Portfólio profissional de...'), synthesize a concise 2-3 sentence executive technical overview highlighting candidate's core expertise, academic background, and technical focus based strictly on their actual data.\n"
            "3. STRICT TRUTHFULNESS: Keep all institutions, degrees, dates, metrics, and names 100% truthful to source facts. Never invent experiences or credentials.\n\n"
            "PART 3: OUTPUT FORMAT\n"
            "Return ONLY the audited, polished LaTeX body from \\begin{document} to \\end{document}. "
            "Zero prose commentary, zero markdown code fences."
        )

        user_prompt = (
            f"{instruction_line}"
            "DUAL REVIEW MANDATE: Review both the LaTeX code (syntax, balanced braces, special character escaping %, &, $, #, _, entry isolation) "
            "and the text content (punchy action verbs, high-impact phrasing, strict truthfulness).\n"
            "Ensure every education, experience, and project entry is isolated with \\par\\vspace{3pt} or blank lines.\n\n"
            f"LATEX_BODY_TO_REVIEW:\n{target}\n\n"
            "Return the audited and improved LaTeX body from \\begin{document} to \\end{document}."
        )

        try:
            fixed, usage, used_model, is_cached = self._call_llm_chat(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
            )
            cleaned = sanitize_latex_layout(CavemanPromptPlugin.strip_code_fences(fixed))
            is_severely_truncated = (len(target) > 600 and len(cleaned.strip()) < int(len(target) * 0.2))
            has_end_doc = r"\end{document}" in cleaned
            if not cleaned or len(cleaned.strip()) < 30 or is_severely_truncated or not has_end_doc:
                final_latex = base_latex
            else:
                final_latex = sanitize_latex_layout(LaTeXPreambleSplitPlugin.reassemble(preamble, cleaned) if preamble else cleaned)
                if r"\end{document}" not in final_latex:
                    final_latex = final_latex.rstrip() + "\n\\end{document}\n"

            self._populate_metrics(
                metrics,
                usage,
                used_model,
                is_cached,
                extra_saved=preamble_tokens_saved + 1500,
            )
            return final_latex, metrics
        except Exception as exc:
            metrics.model_used = f"direct_fallback ({type(exc).__name__})"
            # Em caso de indisponibilidade de API ou falha, preserva o LaTeX determinístico com segurança
            return base_latex, metrics

    @staticmethod
    def _populate_metrics(
        metrics: TokenMetrics,
        usage: Dict[str, Any],
        used_model: str,
        is_cached: bool,
        extra_saved: int,
    ) -> None:
        metrics.model_used = used_model
        metrics.cache_hit = is_cached
        metrics.prompt_tokens_actual = int(usage.get("prompt_tokens") or 0)
        metrics.completion_tokens_actual = int(usage.get("completion_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        metrics.reasoning_tokens_actual = int(details.get("reasoning_tokens") or 0)
        metrics.total_tokens_actual = int(usage.get("total_tokens") or 0)
        metrics.estimated_tokens_saved = extra_saved + (900 if is_cached else 0)

    @staticmethod
    def _parse_json_safely(
        raw_content: str,
        raw_profile_data: Dict[str, Any],
        resume_type: str,
    ) -> Dict[str, Any]:
        cleaned = CavemanPromptPlugin.strip_code_fences(raw_content)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                try:
                    return json.loads(fixed)
                except Exception:
                    pass
        return {}

    @staticmethod
    def _apply_fallbacks(
        cv: Dict[str, Any],
        raw_profile_data: Dict[str, Any],
        resume_type: str,
        lang: str = "pt-br",
    ) -> None:
        """Garante que nenhum dado essencial extraído das APIs fique ausente caso o JSON venha parcial."""
        is_en = str(lang).lower().startswith("en")
        meta = raw_profile_data.get("user_meta") or {}
        gh = raw_profile_data.get("github") or {}
        orcid = raw_profile_data.get("orcid") or {}
        lattes = raw_profile_data.get("lattes") or {}

        if not cv.get("name"):
            cv["name"] = (
                meta.get("name")
                or lattes.get("name")
                or orcid.get("name")
                or gh.get("name")
                or gh.get("username")
                or ("Candidate Name" if is_en else "Nome do Candidato")
            )
        if not cv.get("email"):
            cv["email"] = meta.get("email") or gh.get("email") or ""
        if not cv.get("phone"):
            cv["phone"] = meta.get("phone") or ""
        if not cv.get("location"):
            cv["location"] = meta.get("location") or gh.get("location") or ""
        if not cv.get("title"):
            if is_en:
                default_role = "Academic Researcher & Scientist" if resume_type == "academico" else "Technology & Software Specialist"
            else:
                default_role = "Pesquisador Acadêmico & Cientista" if resume_type == "academico" else "Especialista em Tecnologia & Desenvolvimento"
            cv["title"] = meta.get("role") or default_role
        if not cv.get("summary"):
            cv["summary"] = (
                lattes.get("summary")
                or orcid.get("bio")
                or gh.get("bio")
                or (
                    "Professional with a strong technical and analytical background."
                    if is_en
                    else "Profissional com sólida trajetória técnica e analítica."
                )
            )
        # Remove entradas vazias retornadas pelo modelo antes da renderização LaTeX
        cv["education"] = [
            e for e in (cv.get("education") or [])
            if (e.get("degree") or "").strip() or (e.get("institution") or "").strip()
        ]
        cv["experience"] = [
            x for x in (cv.get("experience") or [])
            if (x.get("role") or "").strip() or (x.get("organization") or "").strip()
        ]
        cv["projects"] = [
            p for p in (cv.get("projects") or [])
            if (p.get("name") or "").strip() or (p.get("description") or "").strip()
        ]
        cv["publications"] = [
            pb for pb in (cv.get("publications") or [])
            if (pb.get("title") or "").strip()
        ]
        cv["skills"] = [
            s for s in (cv.get("skills") or [])
            if isinstance(s.get("items"), list) and s.get("items") or str(s.get("items") or "").strip()
        ]
        for s in cv["skills"]:
            if isinstance(s.get("items"), list):
                s["items"] = ", ".join(str(i) for i in s["items"] if str(i).strip())
        cv["languages"] = [str(l).strip() for l in (cv.get("languages") or []) if str(l).strip()]
        if not cv["languages"]:
            raw_langs = (
                lattes.get("languages")
                or (raw_profile_data.get("linkedin") or {}).get("languages")
                or raw_profile_data.get("languages")
                or meta.get("languages")
                or []
            )
            cv["languages"] = [str(l).strip() for l in raw_langs if str(l).strip()][:5]
        cv["awards"] = sanitize_awards(cv.get("awards") or [])
        if not cv["awards"] and lattes.get("awards"):
            cv["awards"] = sanitize_awards(lattes["awards"][:5])

        if not cv.get("education") and lattes.get("educations"):
            cv["education"] = [
                {
                    "degree": f"{e.get('level', '')} - {e.get('course', '')}".strip(" -"),
                    "institution": e.get("institution", ""),
                    "period": f"{e.get('start', '')}-{e.get('end', '')}".strip("-"),
                    "details": e.get("thesis_title", ""),
                }
                for e in lattes["educations"][:5]
            ]
        elif not cv.get("education") and (raw_profile_data.get("orcid") or {}).get("educations"):
            cv["education"] = [
                {
                    "degree": (e.get("degree") or e.get("role") or e.get("course") or "").strip(),
                    "institution": (e.get("institution") or e.get("organization") or e.get("org") or "").strip(),
                    "period": f"{e.get('start', '')}-{e.get('end', '')}".strip("-"),
                    "details": "",
                }
                for e in (raw_profile_data.get("orcid") or {})["educations"][:5]
            ]
        if not cv.get("projects") and gh.get("repos"):
            cv["projects"] = [
                {
                    "name": r.get("name", ""),
                    "tech": r.get("tech") or r.get("language", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                for r in gh["repos"][:5]
            ]
        elif not cv.get("projects") and lattes.get("projects"):
            cv["projects"] = [
                {
                    "name": p.get("title", ""),
                    "tech": "",
                    "url": str(p.get("year") or ""),
                    "description": p.get("description", ""),
                }
                for p in lattes["projects"][:5]
            ]
        if not cv.get("publications"):
            pubs = (
                lattes.get("publications")
                or orcid.get("works")
                or (raw_profile_data.get("scholar") or {}).get("publications")
                or (raw_profile_data.get("portfolio") or {}).get("publications")
                or []
            )
            cv["publications"] = [
                {
                    "title": p.get("title", ""),
                    "venue": p.get("venue") or p.get("journal") or "",
                    "year": str(p.get("year") or ""),
                    "authors": p.get("authors", ""),
                    "doi": p.get("doi", ""),
                }
                for p in pubs[:30]
                if (p.get("title") or "").strip()
            ]
