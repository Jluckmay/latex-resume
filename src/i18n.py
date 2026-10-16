"""Internacionalização (i18n) bilíngue (pt-BR e en-US) para Interface Web, CLI e Templates LaTeX."""

from __future__ import annotations

from typing import Any, Dict

SUPPORTED_LANGS = ("pt-br", "en-us")


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "pt-br"
    cleaned = lang.strip().lower().replace("_", "-")
    if cleaned.startswith("en"):
        return "en-us"
    return "pt-br"


LATEX_I18N: Dict[str, Dict[str, str]] = {
    "pt-br": {
        "babel": "brazil",
        "present": "Atual",
        "default_candidate": "Candidato",
        "default_researcher": "Pesquisador Acadêmico",
        "default_professional": "Profissional",
        "default_acad_title": "Currículo Acadêmico & Científico",
        "default_tech_title": "Engenharia & Tecnologia",
        "default_cv_title": "Currículo",
        "sec_summary_acad": "Síntese Acadêmica e Linha de Pesquisa",
        "sec_summary_prof": "Resumo Profissional",
        "sec_profile": "Perfil",
        "sec_contact": r"Contato \& Perfis",
        "sec_education": "Formação Acadêmica",
        "sec_exp_acad": "Atuação Acadêmica e Profissional",
        "sec_exp_prof": "Experiência Profissional",
        "sec_proj_acad": "Projetos de Pesquisa e Desenvolvimento",
        "sec_proj_prof": "Projetos de Destaque e Open Source",
        "sec_publications": "Produção Científica e Publicações",
        "sec_skills": "Competências Técnicas e Metodológicas",
        "sec_languages": "Idiomas",
        "sec_awards": "Prêmios, Títulos e Certificações",
        "default_skill_cat": "Habilidades",
        "link_label": "Link",
    },
    "en-us": {
        "babel": "english",
        "present": "Present",
        "default_candidate": "Candidate",
        "default_researcher": "Academic Researcher",
        "default_professional": "Professional",
        "default_acad_title": "Academic & Scientific Curriculum Vitae",
        "default_tech_title": "Engineering & Technology",
        "default_cv_title": "Curriculum Vitae",
        "sec_summary_acad": r"Academic Summary \& Research Focus",
        "sec_summary_prof": "Professional Summary",
        "sec_profile": "Profile",
        "sec_contact": r"Contact \& Profiles",
        "sec_education": "Education",
        "sec_exp_acad": r"Academic \& Professional Appointments",
        "sec_exp_prof": "Professional Experience",
        "sec_proj_acad": r"Research \& Development Projects",
        "sec_proj_prof": r"Featured \& Open Source Projects",
        "sec_publications": "Scientific Publications",
        "sec_skills": r"Technical \& Methodological Skills",
        "sec_languages": "Languages",
        "sec_awards": r"Awards, Honors \& Certifications",
        "default_skill_cat": "Skills",
        "link_label": "Link",
    },
}


TEMPLATES_I18N: Dict[str, Dict[str, Dict[str, str]]] = {
    "pt-br": {
        "modern_pro": {
            "name": "Moderno Executivo (Profissional & Tech)",
            "description": (
                "Layout executivo moderno em coluna única com destaques em azul-petróleo, "
                "cabeçalho com foto opcional e links clicáveis (LinkedIn, GitHub, ORCID, Lattes)."
            ),
        },
        "academic_classic": {
            "name": "Acadêmico Clássico (Pesquisador / CNPq / Pós-Graduação)",
            "description": (
                "Estrutura acadêmica formal com foco em Formação, Produção Bibliográfica (DOI), "
                "Projetos de Pesquisa, Docência, Prêmios, Lattes e ORCID."
            ),
        },
        "tech_sidebar": {
            "name": "Tech & Engenharia Duas Colunas (Barra Lateral)",
            "description": (
                "Design assimétrico de duas colunas com foto, contatos, stack técnica e idiomas "
                "na coluna lateral e experiências/projetos na coluna principal."
            ),
        },
        "minimal_ats": {
            "name": "Minimalista ATS-Friendly (Alta Densidade)",
            "description": (
                "Tipografia clássica de alto contraste otimizada para sistemas corporativos ATS "
                "e leitura rápida por recrutadores."
            ),
        },
        "overleaf_russell_ti": {
            "name": "Overleaf: Currículo T.I. — Russell CV (rgfqqnnynrmv)",
            "description": (
                "Modelo Overleaf Russell CV (https://www.overleaf.com/read/rgfqqnnynrmv#d5b171) com foto lateral "
                "no cabeçalho, ícones FontAwesome 5, títulos com destaque nas 3 primeiras letras e níveis de idiomas em círculos."
            ),
        },
        "overleaf_awesome_cv": {
            "name": "Overleaf: Jason Richards' Résumé — Awesome-CV (chbxgnfyyvfc)",
            "description": (
                "Modelo Overleaf Jason Richards' Résumé (https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc) "
                "baseado no clássico Awesome-CV com cabeçalho centralizado, destaque de 3 letras nas seções e rodapé executivo."
            ),
        },
        "overleaf_single_page_keywords": {
            "name": "Overleaf: Currículo Página Única com Keywords (wmcxcgmtkxzk)",
            "description": (
                "Modelo Overleaf de página única em duas colunas (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk) "
                "com fonte Raleway, ícones circulares TikZ, Resumo e Keywords de stack por experiência."
            ),
        },
    },
    "en-us": {
        "modern_pro": {
            "name": "Executive Modern (Professional & Tech)",
            "description": (
                "Single-column modern executive layout with teal-blue accents, "
                "optional header photo, and clickable links (LinkedIn, GitHub, ORCID, Lattes)."
            ),
        },
        "academic_classic": {
            "name": "Academic Classic (Researcher / Post-Grad / Faculty)",
            "description": (
                "Formal academic CV structure highlighting Education, Peer-Reviewed Publications (DOI), "
                "Research Projects, Teaching, Awards, Lattes, and ORCID."
            ),
        },
        "tech_sidebar": {
            "name": "Tech & Engineering Two-Column (Sidebar)",
            "description": (
                "Asymmetric two-column layout with photo, contacts, tech stack, and languages "
                "in the sidebar and experience/projects in the main column."
            ),
        },
        "minimal_ats": {
            "name": "Minimalist ATS-Friendly (High Density)",
            "description": (
                "High-contrast classic typography optimized for corporate ATS parsers "
                "and rapid recruiter scanning."
            ),
        },
        "overleaf_russell_ti": {
            "name": "Overleaf: IT & Academic CV — Russell CV (rgfqqnnynrmv)",
            "description": (
                "Overleaf Russell CV template (https://www.overleaf.com/read/rgfqqnnynrmv#d5b171) featuring left header photo, "
                "FontAwesome 5 icons, 3-letter colored section titles, skill tables, and 5-dot language proficiency bars."
            ),
        },
        "overleaf_awesome_cv": {
            "name": "Overleaf: Jason Richards' Résumé — Awesome-CV (chbxgnfyyvfc)",
            "description": (
                "Overleaf Jason Richards' Résumé template (https://www.overleaf.com/articles/jason-richards-resume/chbxgnfyyvfc) "
                "built on Awesome-CV with centered header, Roboto + Source Sans Pro typography, and 3-column executive footer."
            ),
        },
        "overleaf_single_page_keywords": {
            "name": "Overleaf: Single-Page Resume with Keywords (wmcxcgmtkxzk)",
            "description": (
                "Overleaf two-column single-page template (https://www.overleaf.com/latex/templates/sample-single-page-resume-with-keywords/wmcxcgmtkxzk) "
                "by Primož Godec & Salman Maqbool with Raleway font, TikZ circled icons, Summary, and per-job stack Keywords."
            ),
        },
    },
}


MODELS_I18N: Dict[str, Dict[str, Dict[str, str]]] = {
    "pt-br": {
        "nvidia/nemotron-3.5-super-vl-120b-a12b": {
            "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recomendado",
            "description": "Melhor equilíbrio entre inteligência (120B), velocidade (<1s) e economia (0 reasoning tokens).",
        },
        "stepfun-ai/step-5-preview": {
            "name": "StepFun Step-5 Preview — Alta Velocidade",
            "description": "Baixa latência (~1s) e excelente formatação LaTeX/JSON sem desperdício de tokens.",
        },
        "google/gemma-4-31b-it": {
            "name": "Google Gemma 4 31B Instruct — Econômico",
            "description": "Modelo 31B direto sem tokens de raciocínio ocultos.",
        },
        "z-ai/glm-5.3": {
            "name": "Z-AI GLM 5.3 — Raciocínio Avançado",
            "description": "Alta capacidade analítica para templates LaTeX customizados complexos.",
        },
    },
    "en-us": {
        "nvidia/nemotron-3.5-super-vl-120b-a12b": {
            "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recommended",
            "description": "Best balance of intelligence (120B), speed (<1s), and token economy (0 reasoning tokens).",
        },
        "stepfun-ai/step-5-preview": {
            "name": "StepFun Step-5 Preview — High Speed",
            "description": "Low latency (~1s) and accurate LaTeX/JSON formatting without token waste.",
        },
        "google/gemma-4-31b-it": {
            "name": "Google Gemma 4 31B Instruct — Economical",
            "description": "Direct 31B model with zero hidden reasoning token overhead.",
        },
        "z-ai/glm-5.3": {
            "name": "Z-AI GLM 5.3 — Advanced Reasoning",
            "description": "High analytical capacity for complex custom LaTeX templates.",
        },
    },
}


UI_TEXT: Dict[str, Dict[str, Any]] = {
    "pt-br": {
        "page_title": "Gerador de Currículos LaTeX — NVIDIA AI",
        "app_title": "📄 Gerador Automático de Currículos LaTeX (NVIDIA NIM AI)",
        "app_caption": (
            "Extração automática de GitHub, ORCID, Lattes e LinkedIn • Compilação PDF via LaTeX • "
            "Otimizado com Plugins de Economia de Tokens (Caveman + TOON + 0-Reasoning)"
        ),
        "lang_selector_label": "🌐 Idioma da Interface e do Currículo / Language",
        "sidebar_header": "⚙️ Motor NVIDIA NIM & Economia de Tokens",
        "model_select_label": "Modelo da API NVIDIA",
        "model_select_help": (
            "O modelo padrão (Nemotron 3.5 Super 120B) foi selecionado por apresentar a melhor precisão estrutural, "
            "baixa latência (<1s) e 0 tokens ocultos de raciocínio."
        ),
        "custom_key_label": "Credencial Customizada (opcional — cofre criptográfico integrado ativo por padrão)",
        "custom_key_placeholder": "Usando cofre interno vinculado à tarefa",
        "cache_checkbox": "Ativar Cache Local SHA-256 (0 tokens em reuso)",
        "plugins_header": "🔌 Plugins de Economia Ativos",
        "plugins_md": (
            "- **CavemanPromptPlugin**: diretivas ultra-concisas sem preâmbulo (~65% menos tokens)\n"
            "- **ThinkingSuppressionPlugin**: `enable_thinking=False` (0 tokens gastos em CoT oculto)\n"
            "- **TOONContextPrunerPlugin**: minificação tabular e deduplicação local ORCID/Lattes\n"
            "- **ShortKeySchemaPlugin**: chaves JSON de 1–2 letras na geração\n"
            "- **LaTeXPreambleSplitPlugin**: separa preâmbulo fixo de templates `.tex`"
        ),
        "sec1_title": "1. Perfil, Modalidade e Modelo LaTeX",
        "resume_type_label": "Finalidade do Currículo",
        "resume_type_prof": "Profissional (Mercado / Indústria / Tech)",
        "resume_type_acad": "Acadêmico (Pesquisa / Pós-Graduação / Docência)",
        "tpl_mode_label": "Origem do Modelo LaTeX",
        "tpl_mode_builtin": "Escolher modelo integrado",
        "tpl_mode_custom": "Fornecer meu próprio modelo LaTeX (.tex)",
        "tpl_select_label": "Selecione o Modelo de Currículo",
        "upload_tex_label": "Envie seu arquivo de template `.tex`",
        "paste_tex_label": "Ou cole o código LaTeX do seu modelo abaixo",
        "sec2_title": "2. Perfis Online e Foto",
        "github_label": "GitHub (usuário ou URL)",
        "github_ph": "ex: torvalds ou https://github.com/usuario",
        "orcid_label": "ORCID (ID ou URL)",
        "orcid_ph": "ex: 0000-0002-1825-0097",
        "linkedin_label": "LinkedIn (URL do perfil)",
        "linkedin_ph": "https://www.linkedin.com/in/seu-perfil/",
        "lattes_label": "Currículo Lattes (URL)",
        "lattes_ph": "http://lattes.cnpq.br/0000000000000000",
        "photo_label": "Foto de Perfil (opcional — PNG/JPG)",
        "expander_extra": "📎 Complementar LinkedIn / Lattes (Upload XML/ZIP/PDF ou Texto)",
        "expander_caption": (
            "Como o LinkedIn exige login e o Lattes possui CAPTCHA para acesso externo, "
            "você pode anexar o XML/ZIP exportado do Lattes ou o PDF salvo do LinkedIn para extração 100% completa."
        ),
        "lattes_file_label": "Arquivo do Lattes (XML, ZIP ou PDF exportado do CNPq)",
        "linkedin_pdf_label": "PDF do LinkedIn ('Salvar como PDF' no perfil do LinkedIn)",
        "extra_text_label": "Experiências / Publicações / Resumo complementar (opcional)",
        "extra_text_ph": "Cole aqui informações extras do LinkedIn/Lattes, certificações ou descrição da vaga/edital...",
        "sec3_title": "3. Dados Pessoais de Cabeçalho (Opcional — sobrescreve extração)",
        "name_label": "Nome Completo",
        "name_ph": "Detectado automaticamente se vazio",
        "role_label": "Cargo / Título Principal",
        "role_ph": "Ex: Engenheiro de Software Sênior / Doutorando em IA",
        "email_label": "E-mail",
        "email_ph": "seu.email@dominio.com",
        "phone_label": "Telefone / WhatsApp",
        "phone_ph": "+55 (11) 99999-9999",
        "loc_label": "Cidade / Estado / País",
        "loc_ph": "São Paulo, SP, Brasil",
        "gen_btn": "🚀 Gerar Currículo LaTeX + PDF",
        "res_header": "📑 Resultado, Preview PDF e Métricas de Tokens",
        "spinner_msg": "Extraindo perfis, otimizando tokens (Caveman + TOON) e compilando PDF via pdflatex...",
        "metric_total": "Tokens Totais API",
        "metric_reasoning": "Reasoning Tokens",
        "metric_saved": "Tokens Economizados",
        "metric_pct": "Economia Estimada",
        "model_used_lbl": "Modelo utilizado",
        "cache_hit_lbl": "Cache Hit",
        "yes_zero_tokens": "Sim (0 tokens gastos)",
        "no_lbl": "Não",
        "pdf_ok_msg": "Currículo PDF compilado com sucesso",
        "dl_pdf_btn": "⬇️ Baixar Currículo (.PDF)",
        "dl_tex_btn": "⬇️ Baixar Código LaTeX (.TEX)",
        "pdf_warn_msg": "O código LaTeX foi gerado, mas houve um alerta na compilação PDF",
        "view_tex_exp": "🔍 Ver Código-Fonte LaTeX Gerado",
        "view_audit_exp": "📊 Ver Auditoria dos Plugins de Economia de Tokens e Dados Extraídos",
        "err_msg": "Erro ao gerar currículo",
        "latex_ok_lbl": "✅ Compilador LaTeX ativo",
        "latex_missing_lbl": "⚠️ Compilador LaTeX (`pdflatex`) não encontrado — instale TeX Live ou MiKTeX",
        "theme_label": "🎨 Tema da Interface",
        "theme_light": "☀️ Modo Claro",
        "theme_dark": "🌙 Modo Escuro",
        "auto_detected_badge": "Detectado automaticamente do seu sistema/navegador",
        "portfolio_label": "Página de Portfólio / Website Pessoal (URL)",
        "portfolio_ph": "https://meuportfolio.dev ou https://seusite.com.br",
        "color_sec_title": "🎨 Cores do Currículo & Preview ao Vivo do Modelo",
        "color_preset_label": "Paleta de Cores Predefinida",
        "color_custom_opt": "✨ Personalizado (Escolher cores manualmente)",
        "primary_color_label": "Cor Principal (Títulos, Linhas & Destaques)",
        "secondary_color_label": "Cor Secundária (Subtítulos & Barra Lateral)",
        "preview_card_title": "👁️ Preview Visual do Modelo LaTeX (Atualiza em Tempo Real)",
        "preview_card_caption": "Representação visual fiel da estrutura tipográfica e das cores selecionadas.",
        "idle_info": (
            "Configure seu perfil, escolha o modelo e as cores à esquerda e clique em "
            "**Gerar Currículo LaTeX + PDF** para compilar o documento final."
        ),
    },
    "en-us": {
        "page_title": "LaTeX Resume Generator — NVIDIA AI",
        "app_title": "📄 Automatic LaTeX Resume Generator (NVIDIA NIM AI)",
        "app_caption": (
            "Automatic extraction from GitHub, ORCID, Lattes, LinkedIn & Portfolio • PDF compilation via LaTeX • "
            "Optimized with Token-Saving Plugins (Caveman + TOON + 0-Reasoning)"
        ),
        "lang_selector_label": "🌐 Interface & Resume Language / Idioma",
        "sidebar_header": "⚙️ NVIDIA NIM Engine & Token Economy",
        "model_select_label": "NVIDIA API Model",
        "model_select_help": (
            "The default model (Nemotron 3.5 Super 120B) was selected for its top structural accuracy, "
            "low latency (<1s), and 0 hidden reasoning tokens."
        ),
        "custom_key_label": "Custom Credential (optional — built-in task-bound cryptographic vault active by default)",
        "custom_key_placeholder": "Using built-in task-bound enclave vault",
        "cache_checkbox": "Enable Local SHA-256 Cache (0 tokens on reuse)",
        "plugins_header": "🔌 Active Token-Saving Plugins",
        "plugins_md": (
            "- **CavemanPromptPlugin**: ultra-terse directives with zero preamble (~65% fewer tokens)\n"
            "- **ThinkingSuppressionPlugin**: `enable_thinking=False` (0 tokens spent on hidden CoT)\n"
            "- **TOONContextPrunerPlugin**: tabular minification & local ORCID/Lattes deduplication\n"
            "- **ShortKeySchemaPlugin**: 1–2 char JSON keys during generation\n"
            "- **LaTeXPreambleSplitPlugin**: splits static preamble from `.tex` templates"
        ),
        "sec1_title": "1. Profile, Mode & LaTeX Template",
        "resume_type_label": "Resume Purpose",
        "resume_type_prof": "Professional (Industry / Corporate / Tech)",
        "resume_type_acad": "Academic (Research / Post-Grad / Faculty)",
        "tpl_mode_label": "LaTeX Template Source",
        "tpl_mode_builtin": "Choose built-in template",
        "tpl_mode_custom": "Provide my own custom LaTeX template (.tex)",
        "tpl_select_label": "Select Resume Template",
        "upload_tex_label": "Upload your `.tex` template file",
        "paste_tex_label": "Or paste your custom LaTeX template code below",
        "sec2_title": "2. Online Profiles, Portfolio & Photo",
        "github_label": "GitHub (username or URL)",
        "github_ph": "e.g. torvalds or https://github.com/username",
        "orcid_label": "ORCID (ID or URL)",
        "orcid_ph": "e.g. 0000-0002-1825-0097",
        "linkedin_label": "LinkedIn (Profile URL)",
        "linkedin_ph": "https://www.linkedin.com/in/your-profile/",
        "lattes_label": "Lattes CV (URL)",
        "lattes_ph": "http://lattes.cnpq.br/0000000000000000",
        "photo_label": "Profile Photo (optional — PNG/JPG)",
        "expander_extra": "📎 Supplement LinkedIn / Lattes (Upload XML/ZIP/PDF or Text)",
        "expander_caption": (
            "Since LinkedIn requires login and Lattes uses CAPTCHA for external access, "
            "you can attach your exported Lattes XML/ZIP or saved LinkedIn PDF for 100% complete extraction."
        ),
        "lattes_file_label": "Lattes File (XML, ZIP, or PDF exported from CNPq)",
        "linkedin_pdf_label": "LinkedIn PDF ('Save to PDF' from your LinkedIn profile)",
        "extra_text_label": "Additional Experience / Publications / Summary (optional)",
        "extra_text_ph": "Paste extra LinkedIn/Lattes details, certifications, or target job/grant description here...",
        "sec3_title": "3. Personal Header Details (Optional — overrides auto-extraction)",
        "name_label": "Full Name",
        "name_ph": "Auto-detected if left blank",
        "role_label": "Primary Role / Headline",
        "role_ph": "e.g. Senior Software Engineer / Ph.D. Researcher in AI",
        "email_label": "E-mail",
        "email_ph": "your.email@domain.com",
        "phone_label": "Phone / Mobile",
        "phone_ph": "+1 (555) 000-0000",
        "loc_label": "City / State / Country",
        "loc_ph": "San Francisco, CA, USA",
        "gen_btn": "🚀 Generate LaTeX + PDF Resume",
        "res_header": "📑 Result, PDF Preview & Token Metrics",
        "spinner_msg": "Extracting profiles & portfolio, optimizing tokens (Caveman + TOON), and compiling PDF via pdflatex...",
        "metric_total": "Total API Tokens",
        "metric_reasoning": "Reasoning Tokens",
        "metric_saved": "Tokens Saved",
        "metric_pct": "Estimated Savings",
        "model_used_lbl": "Model used",
        "cache_hit_lbl": "Cache Hit",
        "yes_zero_tokens": "Yes (0 tokens spent)",
        "no_lbl": "No",
        "pdf_ok_msg": "PDF Resume successfully compiled",
        "dl_pdf_btn": "⬇️ Download Resume (.PDF)",
        "dl_tex_btn": "⬇️ Download LaTeX Source (.TEX)",
        "pdf_warn_msg": "LaTeX code was generated, but PDF compilation reported a warning",
        "view_tex_exp": "🔍 View Generated LaTeX Source Code",
        "view_audit_exp": "📊 View Token-Saving Plugin Audit & Extracted Data",
        "err_msg": "Error generating resume",
        "latex_ok_lbl": "✅ LaTeX Compiler active",
        "latex_missing_lbl": "⚠️ LaTeX Compiler (`pdflatex`) not found — install TeX Live or MiKTeX",
        "theme_label": "🎨 Interface Theme",
        "theme_light": "☀️ Light Mode",
        "theme_dark": "🌙 Dark Mode",
        "auto_detected_badge": "Auto-detected from your OS/Browser",
        "portfolio_label": "Portfolio Page / Personal Website (URL)",
        "portfolio_ph": "https://myportfolio.dev or https://yourwebsite.com",
        "color_sec_title": "🎨 Resume Color Customization & Live Template Preview",
        "color_preset_label": "Color Palette Preset",
        "color_custom_opt": "✨ Custom (Pick colors manually)",
        "primary_color_label": "Primary Color (Headings, Rules & Accents)",
        "secondary_color_label": "Secondary Color (Subtitles & Sidebar)",
        "preview_card_title": "👁️ Live Visual Preview of LaTeX Template",
        "preview_card_caption": "Real-time visual representation of the layout structure and selected colors.",
        "idle_info": (
            "Configure your profile, choose your template and colors on the left, and click "
            "**Generate LaTeX + PDF Resume** to compile the final document."
        ),
    },
}
