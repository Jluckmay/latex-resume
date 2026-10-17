# 🛠️ Scripts Utilitários do Projeto / Project Utility Scripts

Este diretório contém ferramentas auxiliares de desenvolvimento e manutenção do projeto:

| Script | Descrição | Como Executar |
| :--- | :--- | :--- |
| **`generate_direct_resume.py`** | Constrói o currículo determinístico diretamente a partir dos dados dos extratores (GitHub, Lattes, ORCID, LinkedIn) sem utilizar IA (0 tokens). Suporta flag opcional `--review-ai` para revisão cirúrgica de texto. | `python scripts/generate_direct_resume.py --lattes-file examples/sample_lattes.xml` |
| **`generate_icons.py`** | Gera todos os ícones oficiais do projeto (`SVG`, `PNG` 512, 192, 32, 16 e `ICO` multi-frame) com desenho geométrico via Pillow e SVG vetorial. Salva na raiz e em `assets/`. | `python scripts/generate_icons.py` |
| **`clean_artifacts.py`** | Higieniza o projeto removendo caches do Python (`__pycache__`), resíduos do compilador LaTeX (`.aux`, `.log`, `.fls`, `.fdb_latexmk`) e pastas temporárias. | `python scripts/clean_artifacts.py` |
