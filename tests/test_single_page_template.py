"""Testes dedicados ao template Single Page + Keywords garantindo página única e cabeçalho estético."""

import re
import subprocess
from pathlib import Path
import pypdf
import pytest

from src.templates import render_builtin_template

SAMPLE_MASSIVE_PROFILE = {
    "name": "João Lucas Mayrinck",
    "title": "Technology & Software Specialist",
    "email": "lucas.mayrinck@dcc.ufmg.br",
    "location": "Belo Horizonte, MG",
    "summary": "Computer Science researcher and software developer with expertise in educational technologies, computing history, and digital game development. Experience with university extension programs, interactive mathematical tools, and full-stack software engineering.",
    "experience": [
        {"role": "Student Electoral Board Member", "organization": "Federal University of Minas Gerais (DCC / UFMG)", "period": "2026", "bullets": ["Participation in the student representation election process for the Graduate Student Academic Center (CAPosComp/UFMG)."]},
        {"role": "Introduction to Game Development Teaching Assistant", "organization": "Federal University of Viçosa (UFV · Game Dev)", "period": "2025", "bullets": ["Practical guidance and technical mentoring for students in the game development course."]},
        {"role": "Extension Project Fellow", "organization": "Federal University of Viçosa", "period": "2023 - 2024", "bullets": ["Development of dynamic interactive figures in GeoGebra for mathematics education and academic outreach."]},
        {"role": "Frontend Developer", "organization": "Health Lake Institute", "period": "2021 - 2023", "bullets": ["Volunteer work in Science and Technology, supporting academic events and educational workshops."]},
        {"role": "Programming Teaching Assistant", "organization": "Federal University of Viçosa", "period": "2021 - 2022", "bullets": ["Instruction in fundamental concepts of computing history and digital game development."]},
        {"role": "Programming Tutor", "organization": "Federal University of Viçosa", "period": "2019 - 2020", "bullets": ["Practical guidance and technical mentoring for students in the game development course."]},
    ],
    "education": [
        {"degree": "M.Sc. in Computer Science", "institution": "Universidade Federal de Minas Gerais", "period": "2026 - Present"},
        {"degree": "B.Sc. in Information Systems", "institution": "Universidade Federal de Viçosa", "period": "2019 - 2025"},
    ],
    "awards": [
        "Honorable Mention – Poster Track – WSIS 2025 (Explorando a Grécia Antiga)",
        "Honorable Mention – Games Track – SBIE 2024 (Palavras ao Ar)",
        "Second Place – Teaching & Education – SIA 2023 (Palavras ao Ar)",
    ],
    "projects": [
        {"name": "latex-resume", "tech": "Python, JavaScript, LaTeX, HTML5, CSS3, Bash", "url": "https://github.com/jluckmay/latex-resume", "description": "Automatic generator for Academic and Professional resumes in LaTeX + PDF (supporting both en-US and pt-BR), powered by Multiple AI Providers (NVIDIA NIM, Google Gemini, Anthropic Claude, OpenAI, DeepSeek)..."},
        {"name": "jluckmay.github.io", "tech": "HTML5, Python, JavaScript, LaTeX, CSS3, Bash", "url": "https://jluckmay.github.io", "description": "Personal and academic portfolio built as a static website."},
        {"name": "minecraft-map-convertion", "tech": "Python, Java, Bash, Git", "url": "https://github.com/jluckmay/minecraft-map-convertion", "description": "While existing terrain tools (such as Chunker or Amulet) convert blocks, biomes, containers, and dimensions, they do not convert entities, player inventories, custom villager NBT trades, or datapack logic."},
        {"name": "C-Codes", "tech": "C, JavaScript, GitHub Pages", "url": "https://github.com/jluckmay/C-Codes", "description": "By João Lucas Mayrinck, Information Systems Bachelor by the Federal University of Viçosa (UFV)."},
        {"name": "Quadro-Branco", "tech": "JavaScript, Python, HTML5, CSS3, SQL, FastAPI", "url": "https://github.com/jluckmay/Quadro-Branco", "description": "Collaborative Whiteboard is a multi-user web application for creating and editing visual content simultaneously."},
        {"name": "MineMan", "tech": "HTML5, Python, C++, Bash", "url": "https://github.com/jluckmay/MineMan", "description": "MineMan is a maze exploration game inspired by the Minecraft universe."},
    ],
    "publications": [
        {"title": "Math-O-Ween: Um Jogo Digital Educacional para Explorar Operações Matemáticas de Forma Divertida e Assustadora-Resumo Estendido", "venue": "Operações Matemáticas de Forma Divertida e Assustadora Revista Brasileira de Informática na Educação", "year": "2026", "url": "https://rbie.org"},
        {"title": "PDI Interativo: Uma Ferramenta para Estudo e Experimentação com Abordagem Espacial e Frequencial", "venue": "com Abordagem Espacial e Frequencial Anais do XVI Workshop de Sistemas de Informação", "year": "2025"},
        {"title": "Jogo Digital Educativo como Ferramenta de Apoio no Ensino de Frações", "venue": "XVI Workshop de Sistemas de Informação – UFV Rio Paranaíba Campus", "year": "2025"},
        {"title": "Impacto da Solução Inicial na Otimização por Simulated Annealing: Uma Análise Comparativa entre GRASP e HPG", "venue": "Annealing: Uma Análise Comparativa entre GRASP e HPG Anais do XVI Workshop de Sistemas de Informação", "year": "2025"},
        {"title": "Gamificação no Ensino de Física: Projeto e Teste de Usabilidade de um Jogo de Física para Ensino Médio", "venue": "Usabilidade de um Jogo de Física para Ensino Médio XVI Workshop de Sistemas de Informação", "year": "2025"},
        {"title": "Explorando a Grécia Antiga: Um Jogo Digital Educativo", "venue": "XVI Workshop de Sistemas de Informação", "year": "2025"},
        {"title": "Atividades de aprendizagem em matemática baseadas no uso interativo de figuras dinâmicas em ambientes virtuais", "venue": "Autoria, tecnologia e direitos humanos na educação: diálogos com Pedro Demo", "year": "2025"},
        {"title": "Palavras ao Ar: um jogo digital de descoberta de novas palavras e seus significados para auxiliar na alfabetização", "venue": "Simpósio Brasileiro de Informática na Educação (SBIE), 591-601 , 2024", "year": "2024"},
        {"title": "Palavras ao Ar: um jogo digital de descoberta de novas palavras e seus significados para auxiliar na alfabetização", "venue": "XIV Workshop de Sistemas de Informação – UFV Rio Paranaíba Campus", "year": "2023"},
    ],
    "languages": ["Portuguese (Fluent)", "English (Intermediate)", "Spanish (Iniciante)", "Libras (Iniciante)"],
    "skills": [{"category": "Tech Stack", "items": "Python, JavaScript, LaTeX, C++, SQL"}],
}

SAMPLE_LINKS = {
    "portfolio": "https://jluckmay.github.io",
    "linkedin": "https://linkedin.com/in/jluckmay",
    "github": "https://github.com/jluckmay",
    "orcid": "https://orcid.org/0009-0001-0178-4877",
    "scholar": "https://scholar.google.com/citations?user=jluckmay",
    "lattes": "http://lattes.cnpq.br/7395864900833083",
}


def test_single_page_keywords_header_2_columns_layout():
    """Valida se o cabeçalho distribui os contatos em grade harmônica tabular de 2 colunas."""
    tex = render_builtin_template(
        "overleaf_single_page_keywords",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="academico",
        lang="en-us",
    )
    # Deve conter a tabela de contatos em duas colunas
    assert r"\begin{tabular}[c]{@{} l @{\hspace{14pt}} l @{}}" in tex
    assert r"\end{tabular}" in tex
    # Deve conter os contatos principais e ícones
    assert "lucas.mayrinck@dcc.ufmg.br" in tex
    assert "jluckmay.github.io" in tex
    assert "Belo Horizonte, MG" in tex
    assert "0009-0001-0178-4877" in tex
    assert "7395864900833083" in tex


def test_single_page_keywords_strictly_one_page_compilation(tmp_path):
    """Garante que a compilação do template single page com perfil acadêmico massivo produz estritamente 1 página."""
    tex = render_builtin_template(
        "overleaf_single_page_keywords",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="academico",
        lang="en-us",
    )
    tex_file = tmp_path / "resume.tex"
    tex_file.write_text(tex, encoding="utf-8")

    res = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"pdflatex compilation failed:\n{res.stdout[-600:]}"

    pdf_file = tmp_path / "resume.pdf"
    assert pdf_file.exists()

    reader = pypdf.PdfReader(str(pdf_file))
    assert len(reader.pages) == 1, f"Expected strictly 1 page, got {len(reader.pages)}"


def test_single_page_keywords_strictly_one_page_professional(tmp_path):
    """Garante que a compilação do template single page em modo profissional também produz estritamente 1 página."""
    tex = render_builtin_template(
        "overleaf_single_page_keywords",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="pt-br",
    )
    tex_file = tmp_path / "resume_prof.tex"
    tex_file.write_text(tex, encoding="utf-8")

    res = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"pdflatex compilation failed:\n{res.stdout[-600:]}"

    pdf_file = tmp_path / "resume_prof.pdf"
    assert pdf_file.exists()

    reader = pypdf.PdfReader(str(pdf_file))
    assert len(reader.pages) == 1, f"Expected strictly 1 page, got {len(reader.pages)}"

def test_minimal_ats_strictly_one_page_academic_and_professional(tmp_path):
    """Garante que o template Minimal ATS produz estritamente 1 página nos modos acadêmico e profissional."""
    for resume_type in ["academico", "profissional"]:
        tex = render_builtin_template(
            "minimal_ats",
            SAMPLE_MASSIVE_PROFILE,
            SAMPLE_LINKS,
            resume_type=resume_type,
            lang="en-us",
        )
        tex_file = tmp_path / f"min_{resume_type}.tex"
        tex_file.write_text(tex, encoding="utf-8")

        res = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"pdflatex compilation failed for {resume_type}:\n{res.stdout[-600:]}"

        pdf_file = tmp_path / f"min_{resume_type}.pdf"
        assert pdf_file.exists()

        reader = pypdf.PdfReader(str(pdf_file))
        assert len(reader.pages) == 1, f"Expected strictly 1 page for Minimal ATS ({resume_type}), got {len(reader.pages)}"


def test_minimal_ats_experience_two_tier_layout():
    """Valida se as experiências no Minimal ATS utilizam formatação em dois níveis para evitar quebras de data."""
    tex = render_builtin_template(
        "minimal_ats",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="en-us",
    )
    # Role e período na primeira linha, organização na segunda linha
    assert r"\noindent\textbf{Introduction to Game Development Teaching Assistant} \hfill \textit{2025}" in tex
    assert r"\textit{Federal University of Viçosa (UFV · Game Dev)}" in tex
    # Não deve ter '--- \textit{Federal University' na mesma linha que cause quebra anômala
    assert r"Teaching Assistant --- \textit{Federal" not in tex


def test_minimal_ats_publications_sanitizes_conference_as_authors():
    """Garante que títulos de anais/workshops não sejam indevidamente renderizados como autores."""
    profile_with_bogus_author = dict(SAMPLE_MASSIVE_PROFILE)
    profile_with_bogus_author["publications"] = [
        {
            "title": "PDI Interativo",
            "authors": "Anais do XVI Workshop de Sistemas de Informação",
            "venue": "XVI Workshop de Sistemas de Informação",
            "year": "2025",
        }
    ]
    tex = render_builtin_template(
        "minimal_ats",
        profile_with_bogus_author,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="en-us",
    )
    # Não deve renderizar o nome do workshop como autor
    assert "Anais do XVI Workshop de Sistemas de Informação." not in tex

def test_tech_sidebar_no_blank_page_and_full_content(tmp_path):
    """Garante que o template Tech Sidebar não cria página inicial em branco e preserva o conteúdo completo sem truncamento indevido."""
    for resume_type in ["profissional", "academico"]:
        tex = render_builtin_template(
            "tech_sidebar",
            SAMPLE_MASSIVE_PROFILE,
            SAMPLE_LINKS,
            resume_type=resume_type,
            lang="en-us",
        )
        tex_file = tmp_path / f"tech_{resume_type}.tex"
        tex_file.write_text(tex, encoding="utf-8")

        res = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"pdflatex compilation failed for {resume_type}:\n{res.stdout[-600:]}"

        pdf_file = tmp_path / f"tech_{resume_type}.pdf"
        assert pdf_file.exists()

        reader = pypdf.PdfReader(str(pdf_file))
        assert len(reader.pages) >= 1
        page1_text = reader.pages[0].extract_text().strip()
        assert len(page1_text) > 1000, f"Page 1 is unexpectedly empty or sparse: len={len(page1_text)}"

        full_text = "\n".join(p.extract_text() for p in reader.pages)
        # Garante que experiências, projetos e publicações completas são preservados
        assert "Programming Teaching Assistant" in full_text
        assert "Math-O-Ween" in full_text
        assert "PDI Interativo" in full_text


def test_tech_sidebar_balanced_columns_layout():
    """Valida se o Tech Sidebar distribui Formação e Contatos na barra lateral e Experiência/Projetos no corpo principal."""
    tex = render_builtin_template(
        "tech_sidebar",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="en-us",
    )
    # Verifica divisão em paracol com régua vertical de separação
    assert r"\begin{paracol}{2}" in tex
    assert r"\switchcolumn" in tex
    assert r"\setlength{\columnseprule}{0.6pt}" in tex

    # Separação das colunas via \switchcolumn
    sidebar_part, main_part = tex.split(r"\switchcolumn")

    # Sidebar deve conter Educação, Contatos, Resumo Profissional, Idiomas e Prêmios
    assert "Education" in sidebar_part
    assert "M.Sc. in Computer Science" in sidebar_part
    assert "lucas.mayrinck@dcc.ufmg.br" in sidebar_part
    assert "Professional Summary" in sidebar_part
    assert "Languages" in sidebar_part
    assert "Awards, Honors" in sidebar_part

    # Main Body deve conter Experiência e Projetos (resumo movido para a esquerda para layout compacto)
    assert "Professional Summary" not in main_part
    assert "Professional Experience" in main_part
    assert "Featured" in main_part
    assert "Introduction to Game Development Teaching Assistant" in main_part

    # Experiência deve utilizar layout de dois níveis
    assert r"\noindent\textbf{Introduction to Game Development Teaching Assistant} \hfill {\small\textit{2025}}" in main_part
    assert r"\textit{Federal University of Viçosa (UFV · Game Dev)}" in main_part


def test_tech_sidebar_previews_have_education_in_sidebar():
    """Garante que a pré-visualização do Tech Sidebar em Python e index.html mostre Formação Acadêmica na coluna lateral."""
    from src.ui_theme import render_template_preview_html

    html_preview = render_template_preview_html("tech_sidebar")
    sidebar_part, main_part = html_preview.split("width:67%")
    assert "M.Sc. Computer Science" in sidebar_part
    assert "M.Sc. Computer Science" not in main_part

    index_html = Path("index.html").read_text(encoding="utf-8")
    assert 'state.templateId === "tech_sidebar"' in index_html
    tech_js_match = re.search(r'state\.templateId === "tech_sidebar".*?width:67%', index_html, re.DOTALL)
    assert tech_js_match is not None
    assert "${lblEdu}" in tech_js_match.group(0)


def test_google_standard_strictly_one_page_academic_and_professional(tmp_path):
    """Garante que o template Padrão Google produz estritamente 1 página conforme sua descrição."""
    for resume_type in ["profissional", "academico"]:
        for lang in ["pt-br", "en-us"]:
            tex = render_builtin_template(
                "google_standard",
                SAMPLE_MASSIVE_PROFILE,
                SAMPLE_LINKS,
                resume_type=resume_type,
                lang=lang,
            )
            tex_file = tmp_path / f"google_{resume_type}_{lang}.tex"
            tex_file.write_text(tex, encoding="utf-8")

            res = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
            )
            assert res.returncode == 0, f"pdflatex compilation failed for Google Standard ({resume_type}, {lang}):\n{res.stdout[-600:]}"

            pdf_file = tmp_path / f"google_{resume_type}_{lang}.pdf"
            assert pdf_file.exists()

            reader = pypdf.PdfReader(str(pdf_file))
            assert len(reader.pages) == 1, (
                f"Expected strictly 1 page for Google Standard ({resume_type}, {lang}), got {len(reader.pages)}"
            )

            # Garante que o orçamento enriquecido inclui múltiplos itens sem truncar excessivamente
            if resume_type == "academico":
                assert "Math-O-Ween" in tex
                assert "PDI Interativo" in tex
                assert "Impacto da Solução Inicial" in tex
                assert "latex-resume" in tex
                assert "jluckmay.github.io" in tex
            else:
                assert "latex-resume" in tex
                assert "jluckmay.github.io" in tex
                assert "minecraft-map-convertion" in tex


def test_google_standard_gayle_mcdowell_layout_and_accent():
    """Valida se o template Google Standard utiliza cor de destaque Google Blue e formatação Gayle McDowell."""
    tex = render_builtin_template(
        "google_standard",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="en-us",
    )
    # Deve conter a cor de destaque Google Blue
    assert r"\definecolor{accent}{HTML}{0B57D0}" in tex
    # Deve conter títulos de seção com accent
    assert r"\titleformat{\section}{\normalsize\bfseries\scshape\color{accent}}" in tex
    # Deve conter divisória horizontal com accent
    assert r"{\color{accent}\titlerule}" in tex
    assert r"{\color{accent}\hrule height 0.8pt}" in tex
    # Experiência: Organização em negrito e cargo em itálico abaixo (Gayle Laakmann McDowell SWE layout)
    assert r"\noindent\textbf{Federal University of Minas Gerais (DCC / UFMG)} \hfill \textbf{2026}" in tex
    assert r"\textit{Student Electoral Board Member}" in tex


def test_nico_krieger_education_in_sidebar_and_tight_spacing():
    """Valida se o template Nico Krieger posiciona a Formação Acadêmica na coluna lateral (sidebar)
    e utiliza espaçamentos compactos entre itens na coluna da direita."""
    tex_pt = render_builtin_template(
        "nico_krieger",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="academico",
        lang="pt-br",
    )
    tex_en = render_builtin_template(
        "nico_krieger",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="academico",
        lang="en-us",
    )

    # 1. Deve possuir paracol com \switchcolumn
    assert r"\begin{paracol}{2}" in tex_pt
    assert r"\switchcolumn" in tex_pt
    parts_pt = tex_pt.split(r"\switchcolumn")
    sidebar_pt = parts_pt[0]
    main_pt = parts_pt[1]

    # Formação Acadêmica deve estar estritamente na barra lateral (esquerda)
    assert "FORMAÇÃO ACADÊMICA" in sidebar_pt
    assert "FORMAÇÃO ACADÊMICA" not in main_pt

    # Em inglês, EDUCATION deve estar na barra lateral
    parts_en = tex_en.split(r"\switchcolumn")
    sidebar_en = parts_en[0]
    main_en = parts_en[1]
    assert "EDUCATION" in sidebar_en
    assert "EDUCATION" not in main_en

    # 2. Experiência e Publicações na coluna da direita
    assert "EXPERIÊNCIA PROFISSIONAL" in main_pt
    assert "PUBLICAÇÕES" in main_pt

    # 3. Espaçamentos reduzidos e regras com \nopagebreak
    assert r"\rule{\linewidth}{0.8pt}\nopagebreak\\[3pt]" in tex_pt
    assert r"\begin{itemize}[leftmargin=1.1em,noitemsep,topsep=0pt,partopsep=0pt,parsep=0pt,before=\vspace{-2.5pt}]" in tex_pt
    assert r"\vspace{2pt}" in main_pt


def test_nico_krieger_single_page_layout(tmp_path):
    """Garante que o template Nico Krieger produz 1 página com perfil completo sem transbordamento órfão."""
    tex = render_builtin_template(
        "nico_krieger",
        SAMPLE_MASSIVE_PROFILE,
        SAMPLE_LINKS,
        resume_type="profissional",
        lang="pt-br",
    )
    tex_file = tmp_path / "nico_test.tex"
    tex_file.write_text(tex, encoding="utf-8")
    res = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"pdflatex compilation failed:\n{res.stdout[-600:]}"
    pdf_file = tmp_path / "nico_test.pdf"
    assert pdf_file.exists()
    reader = pypdf.PdfReader(str(pdf_file))
    assert len(reader.pages) == 1, f"Expected 1 page for Nico Krieger, got {len(reader.pages)}"
    text = reader.pages[0].extract_text()
    assert "CONTATO" in text
    assert "FORMAÇÃO ACADÊMICA" in text
    assert "IDIOMAS" in text
    assert "PRÊMIOS & DESTAQUES" in text
    assert "EXPERIÊNCIA PROFISSIONAL" in text
    assert "PUBLICA" in text


def test_nico_krieger_previews_have_education_in_sidebar():
    """Garante que a pré-visualização do Nico Krieger em Python e index.html mostre Formação Acadêmica na coluna lateral."""
    from src.ui_theme import render_template_preview_html

    html_preview = render_template_preview_html("nico_krieger")
    # A coluna lateral de 34% deve conter CONTATO e FORMAÇÃO ACADÊMICA
    sidebar_part, main_part = html_preview.split('width:66%')
    assert "FORMAÇÃO ACADÊMICA" in sidebar_part
    assert "FORMAÇÃO ACADÊMICA" not in main_part

    # index.html deve manter a mesma coerência estrutural
    index_html = Path("index.html").read_text(encoding="utf-8")
    assert 'state.templateId === "nico_krieger"' in index_html
    nico_js_match = re.search(r'state\.templateId === "nico_krieger".*?width:66%', index_html, re.DOTALL)
    assert nico_js_match is not None
    assert "FORMAÇÃO ACADÊMICA" in nico_js_match.group(0)


def test_location_auto_resolved_when_user_location_omitted(tmp_path):
    """Garante que a localização é inferida das fontes (GitHub / Portfólio) mesmo se omitida no formulário."""
    from src.pipeline import build_resume_pipeline

    res = build_resume_pipeline(
        resume_type="profissional",
        github_input="https://github.com/jluckmay",
        portfolio_url="https://jluckmay.github.io",
        template_id="overleaf_single_page_keywords",
        user_name="João Lucas Mayrinck",
        user_location="",  # Omitida pelo usuário
        provider="none",
        use_ai=False,
        build_dir=tmp_path,
        lang="pt-br",
    )
    assert res.success is True
    assert "Belo Horizonte" in res.latex_code
    assert r"\faIcon{map-marker-alt}" in res.latex_code


def test_single_page_keywords_and_minimal_ats_fill_page_richly(tmp_path):
    """Garante que perfis com muitas experiências e publicações aproveitam bem o espaço da página única sem subutilização."""
    profile_rich = {
        "name": "João Lucas Mayrinck",
        "title": "Especialista em Tecnologia & Desenvolvimento",
        "summary": "Pesquisador e desenvolvedor com atuação em engenharia de software e jogos digitais.",
        "email": "lucas.mayrinck@dcc.ufmg.br",
        "location": "Belo Horizonte, MG",
        "education": [
            {"degree": "Mestrado em Ciência da Computação", "institution": "UFMG", "period": "2026 - Atual"},
            {"degree": "Bacharelado em Sistemas de Informação", "institution": "UFV", "period": "2019 - 2025"},
        ],
        "languages": ["Português (Fluente)", "Inglês (Intermediário)", "Espanhol (Iniciante)", "Libras (Iniciante)"],
        "awards": [
            "Menção Honrosa – WSIS 2025",
            "Menção Honrosa – SBIE 2024",
            "Segundo Lugar – SIA 2023",
        ],
        "experience": [
            {"role": "Comissão eleitoral", "organization": "CAPosComp/UFMG", "period": "2026", "bullets": ["Apoio à representação discente."]},
            {"role": "Monitor de Jogos", "organization": "UFV", "period": "2025", "bullets": ["Mentoria de estudantes."]},
            {"role": "Bolsista de Extensão", "organization": "UFV", "period": "2023 - 2024", "bullets": ["Desenvolvimento no GeoGebra."]},
            {"role": "Frontend Developer", "organization": "Health Lake", "period": "2021 - 2023", "bullets": ["Desenvolvimento web."]},
            {"role": "Tutor de Informática", "organization": "UFV", "period": "2022", "bullets": ["Ensino de informática básica."]},
        ],
        "publications": [
            {"title": "Math-0-Ween: Jogo Educacional", "venue": "RBIE", "year": "2026"},
            {"title": "PDI Interativo: Estudo e Experimentação", "venue": "Anais WSIS", "year": "2025"},
            {"title": "Jogo Digital no Ensino de Frações", "venue": "Anais WSIS", "year": "2025"},
            {"title": "Otimização por Simulated Annealing", "venue": "Anais WSIS", "year": "2025"},
            {"title": "Gamificação no Ensino de Física", "venue": "Anais WSIS", "year": "2025"},
        ],
        "projects": [],
    }
    links = {
        "portfolio": "https://jluckmay.github.io",
        "github": "https://github.com/jluckmay",
    }

    # 1. Minimal ATS deve incluir até 5 experiências e 5 publicações e ter exatamente 1 página
    tex_ats = render_builtin_template("minimal_ats", profile_rich, links, resume_type="profissional", lang="pt-br")
    f_ats = tmp_path / "fill_ats.tex"
    f_ats.write_text(tex_ats, encoding="utf-8")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", str(f_ats)], cwd=str(tmp_path), capture_output=True)
    pdf_ats = tmp_path / "fill_ats.pdf"
    assert pdf_ats.exists()
    reader_ats = pypdf.PdfReader(str(pdf_ats))
    assert len(reader_ats.pages) == 1
    t_ats = reader_ats.pages[0].extract_text()
    assert "Tutor de Informática" in t_ats
    assert "Gamificação no Ensino de Física" in t_ats

    # 2. Overleaf Single Page Keywords deve incluir até 5 experiências e 5 publicações e ter exatamente 1 página
    tex_kw = render_builtin_template("overleaf_single_page_keywords", profile_rich, links, resume_type="profissional", lang="pt-br")
    f_kw = tmp_path / "fill_kw.tex"
    f_kw.write_text(tex_kw, encoding="utf-8")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", str(f_kw)], cwd=str(tmp_path), capture_output=True)
    pdf_kw = tmp_path / "fill_kw.pdf"
    assert pdf_kw.exists()
    reader_kw = pypdf.PdfReader(str(pdf_kw))
    assert len(reader_kw.pages) == 1
    t_kw = reader_kw.pages[0].extract_text()
    assert "Tutor de Informática" in t_kw
    assert "Gamificação no Ensino de Física" in t_kw




