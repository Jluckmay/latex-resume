"""Interface Web Bilíngue (pt-BR / en-US) com Detecção Automática de Tema/Idioma, Preview de Templates LaTeX, Customização de Cores e Portfólio."""

from __future__ import annotations

import base64

import streamlit as st

from src.compiler import check_latex_compiler
from src.config import RECOMMENDED_MODELS
from src.i18n import MODELS_I18N, TEMPLATES_I18N, UI_TEXT, normalize_lang
from src.pipeline import build_resume_pipeline
from src.templates import BUILTIN_TEMPLATES
from src.ui_theme import (
    COLOR_PRESETS,
    detect_default_language,
    detect_default_theme,
    get_theme_css,
    render_template_preview_html,
)

st.set_page_config(
    page_title="LaTeX Resume Generator — NVIDIA AI",
    page_icon="📄",
    layout="wide",
)

# 1. Detecção automática de idioma e tema padrão do usuário (Navegador / Sistema Operacional)
headers_dict = {}
try:
    if hasattr(st, "context") and hasattr(st.context, "headers"):
        headers_dict = dict(st.context.headers)
except Exception:
    pass

if "auto_lang" not in st.session_state:
    st.session_state["auto_lang"] = detect_default_language(headers_dict)
if "auto_theme" not in st.session_state:
    st.session_state["auto_theme"] = detect_default_theme(headers_dict)

default_lang_idx = 1 if st.session_state["auto_lang"] == "en-us" else 0
default_theme_idx = 0 if st.session_state["auto_theme"] == "light" else 1

with st.sidebar:
    lang_choice = st.selectbox(
        "🌐 Idioma / Language",
        options=["🇧🇷 Português (pt-BR)", "🇺🇸 English (en-US)"],
        index=default_lang_idx,
    )
    ui_lang = "en-us" if "en-US" in lang_choice else "pt-br"
    txt = UI_TEXT[ui_lang]

    theme_choice = st.radio(
        txt["theme_label"],
        options=[txt["theme_light"], txt["theme_dark"]],
        index=default_theme_idx,
        horizontal=True,
        help=txt["auto_detected_badge"],
    )
    active_theme = "light" if theme_choice == txt["theme_light"] else "dark"

    resume_lang_choice = st.selectbox(
        "📝 Idioma do Currículo PDF / Resume Output Language",
        options=["🇧🇷 Português (pt-BR)", "🇺🇸 English (en-US)"],
        index=1 if ui_lang == "en-us" else 0,
    )
    resume_lang = normalize_lang("en-us" if "en-US" in resume_lang_choice else "pt-br")

    latex_ok, latex_ver = check_latex_compiler()
    if latex_ok:
        st.caption(f"{txt['latex_ok_lbl']}: `{latex_ver}`")
    else:
        st.error(txt["latex_missing_lbl"])

    st.divider()
    st.header(txt["sidebar_header"])

    models_loc = MODELS_I18N[ui_lang]
    model_options = {
        models_loc.get(m["id"], {}).get("name", m["name"]): m["id"]
        for m in RECOMMENDED_MODELS
    }
    selected_model_label = st.selectbox(
        txt["model_select_label"],
        options=list(model_options.keys()),
        index=0,
        help=txt["model_select_help"],
    )
    selected_model = model_options[selected_model_label]

    custom_api_key = st.text_input(
        txt["custom_key_label"],
        value="",
        type="password",
        placeholder=txt["custom_key_placeholder"],
    )
    use_cache = st.checkbox(txt["cache_checkbox"], value=True)

    st.divider()
    st.subheader(txt["plugins_header"])
    st.markdown(txt["plugins_md"])

# Cabeçalho da página
st.title(txt["app_title"])
st.caption(txt["app_caption"])

col_left, col_right = st.columns([1.08, 0.92], gap="large")

with col_left:
    # Seção 1: Modalidade e Modelo LaTeX
    st.subheader(txt["sec1_title"])
    c1, c2 = st.columns(2)
    with c1:
        resume_type_label = st.radio(
            txt["resume_type_label"],
            options=[txt["resume_type_prof"], txt["resume_type_acad"]],
            index=0,
        )
        resume_type = "academico" if resume_type_label == txt["resume_type_acad"] else "profissional"

    with c2:
        template_mode = st.radio(
            txt["tpl_mode_label"],
            options=[txt["tpl_mode_builtin"], txt["tpl_mode_custom"]],
            index=0,
        )

    custom_latex_str: str | None = None
    selected_template_id = "academic_classic" if resume_type == "academico" else "modern_pro"

    if template_mode == txt["tpl_mode_builtin"]:
        tpl_loc = TEMPLATES_I18N[ui_lang]
        tpl_labels = {
            tpl_loc.get(k, {}).get("name", v["name"]): k
            for k, v in BUILTIN_TEMPLATES.items()
        }
        default_idx = 1 if resume_type == "academico" else 0
        chosen_label = st.selectbox(
            txt["tpl_select_label"],
            options=list(tpl_labels.keys()),
            index=default_idx,
        )
        selected_template_id = tpl_labels[chosen_label]
        st.info(tpl_loc.get(selected_template_id, {}).get("description", ""))
    else:
        uploaded_tex = st.file_uploader(txt["upload_tex_label"], type=["tex"])
        pasted_tex = st.text_area(
            txt["paste_tex_label"],
            height=160,
            placeholder="\\documentclass{article}\n\\begin{document}\n...\n\\end{document}",
        )
        if uploaded_tex is not None:
            custom_latex_str = uploaded_tex.read().decode("utf-8", errors="ignore")
        elif pasted_tex.strip():
            custom_latex_str = pasted_tex.strip()

    # Seção de Customização de Cores do Currículo
    st.subheader(txt["color_sec_title"])
    preset_map = {v[ui_lang]: k for k, v in COLOR_PRESETS.items()}
    preset_options = list(preset_map.keys()) + [txt["color_custom_opt"]]
    default_preset_idx = 1 if resume_type == "academico" else 0

    col_preset, col_c1, col_c2 = st.columns([1.6, 0.7, 0.7])
    with col_preset:
        selected_preset_label = st.selectbox(
            txt["color_preset_label"],
            options=preset_options,
            index=default_preset_idx,
        )

    if selected_preset_label != txt["color_custom_opt"]:
        preset_key = preset_map[selected_preset_label]
        default_p_col = COLOR_PRESETS[preset_key]["primary"]
        default_s_col = COLOR_PRESETS[preset_key]["secondary"]
    else:
        default_p_col = "#0F4C81"
        default_s_col = "#1E293B"

    with col_c1:
        primary_color = st.color_picker(txt["primary_color_label"], value=default_p_col)
    with col_c2:
        secondary_color = st.color_picker(txt["secondary_color_label"], value=default_s_col)

    # Aplica folha de estilo CSS do tema (Claro / Escuro) com a cor de destaque escolhida
    st.markdown(get_theme_css(active_theme, primary_color), unsafe_allow_html=True)

    # Seção 2: Perfis Online, Portfólio e Foto
    st.subheader(txt["sec2_title"])
    p1, p2 = st.columns(2)
    with p1:
        github_input = st.text_input(txt["github_label"], placeholder=txt["github_ph"])
        orcid_input = st.text_input(txt["orcid_label"], placeholder=txt["orcid_ph"])
        portfolio_url = st.text_input(txt["portfolio_label"], placeholder=txt["portfolio_ph"])
    with p2:
        linkedin_url = st.text_input(txt["linkedin_label"], placeholder=txt["linkedin_ph"])
        lattes_url = st.text_input(txt["lattes_label"], placeholder=txt["lattes_ph"])
        photo_upload = st.file_uploader(
            txt["photo_label"],
            type=["png", "jpg", "jpeg", "webp"],
        )

    with st.expander(txt["expander_extra"]):
        st.caption(txt["expander_caption"])
        lattes_file = st.file_uploader(
            txt["lattes_file_label"],
            type=["xml", "zip", "pdf", "html"],
        )
        linkedin_pdf = st.file_uploader(
            txt["linkedin_pdf_label"],
            type=["pdf"],
        )
        extra_profile_text = st.text_area(
            txt["extra_text_label"],
            height=100,
            placeholder=txt["extra_text_ph"],
        )

    # Seção 3: Dados Pessoais de Cabeçalho
    st.subheader(txt["sec3_title"])
    u1, u2 = st.columns(2)
    with u1:
        user_name = st.text_input(txt["name_label"], placeholder=txt["name_ph"])
        user_role = st.text_input(txt["role_label"], placeholder=txt["role_ph"])
        user_email = st.text_input(txt["email_label"], placeholder=txt["email_ph"])
    with u2:
        user_phone = st.text_input(txt["phone_label"], placeholder=txt["phone_ph"])
        user_location = st.text_input(txt["loc_label"], placeholder=txt["loc_ph"])

    generate_btn = st.button(txt["gen_btn"], type="primary", use_container_width=True)

with col_right:
    # Preview Visual ao Vivo do Modelo LaTeX e das Cores Selecionadas
    st.subheader(txt["preview_card_title"])
    st.caption(txt["preview_card_caption"])
    preview_html = render_template_preview_html(
        template_id=selected_template_id,
        primary_color=primary_color,
        secondary_color=secondary_color,
        lang=resume_lang,
        has_photo=True,
    )
    st.markdown(preview_html, unsafe_allow_html=True)

    st.divider()
    st.subheader(txt["res_header"])
    if generate_btn:
        with st.spinner(txt["spinner_msg"]):
            try:
                res = build_resume_pipeline(
                    resume_type=resume_type,
                    linkedin_url=linkedin_url,
                    linkedin_pdf_bytes=linkedin_pdf.read() if linkedin_pdf else None,
                    github_input=github_input,
                    orcid_input=orcid_input,
                    lattes_url=lattes_url,
                    lattes_file_bytes=lattes_file.read() if lattes_file else None,
                    lattes_filename=lattes_file.name if lattes_file else "",
                    portfolio_url=portfolio_url,
                    photo_bytes=photo_upload.read() if photo_upload else None,
                    template_id=selected_template_id,
                    custom_latex_template=custom_latex_str,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                    user_name=user_name,
                    user_role=user_role,
                    user_email=user_email,
                    user_phone=user_phone,
                    user_location=user_location,
                    extra_notes=extra_profile_text,
                    api_key=custom_api_key if custom_api_key.strip() else None,
                    model=selected_model,
                    use_cache=use_cache,
                    output_stem=f"resume_{resume_lang}_{resume_type}_{selected_template_id}",
                    lang=resume_lang,
                )

                tm = res.token_metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(txt["metric_total"], tm.get("total_tokens_actual", 0))
                m2.metric(txt["metric_reasoning"], tm.get("reasoning_tokens_actual", 0))
                m3.metric(txt["metric_saved"], f"~{tm.get('estimated_tokens_saved', 0)}")
                m4.metric(txt["metric_pct"], f"{tm.get('estimated_savings_pct', 0)}%")

                cache_str = txt["yes_zero_tokens"] if tm.get("cache_hit") else txt["no_lbl"]
                st.caption(
                    f"**{txt['model_used_lbl']}:** `{tm.get('model_used')}` • "
                    f"**{txt['cache_hit_lbl']}:** `{cache_str}`"
                )

                if res.success and res.pdf_path and res.pdf_path.exists():
                    st.success(f"{txt['pdf_ok_msg']}: `{res.pdf_path.name}`")
                    pdf_bytes = res.pdf_path.read_bytes()
                    d1, d2 = st.columns(2)
                    with d1:
                        st.download_button(
                            txt["dl_pdf_btn"],
                            data=pdf_bytes,
                            file_name=res.pdf_path.name,
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True,
                        )
                    with d2:
                        st.download_button(
                            txt["dl_tex_btn"],
                            data=res.latex_code.encode("utf-8"),
                            file_name=res.tex_path.name,
                            mime="text/plain",
                            use_container_width=True,
                        )

                    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_iframe = (
                        f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
                        f'width="100%" height="680" type="application/pdf"></iframe>'
                    )
                    st.markdown(pdf_iframe, unsafe_allow_html=True)
                else:
                    st.warning(f"{txt['pdf_warn_msg']}:\n\n`{res.compiler_message}`")
                    st.download_button(
                        txt["dl_tex_btn"],
                        data=res.latex_code.encode("utf-8"),
                        file_name=res.tex_path.name,
                        mime="text/plain",
                    )

                with st.expander(txt["view_tex_exp"]):
                    st.code(res.latex_code, language="latex")

                with st.expander(txt["view_audit_exp"]):
                    st.json({"token_metrics": tm, "structured_cv": res.structured_cv})

            except Exception as exc:
                st.error(f"{txt['err_msg']}: {exc}")
    else:
        st.info(txt["idle_info"])
