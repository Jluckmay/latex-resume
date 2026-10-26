"""Testes dedicados ao template Single Page + Keywords garantindo página única e cabeçalho estético."""

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
