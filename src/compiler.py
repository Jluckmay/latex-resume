"""Compilador LaTeX (pdflatex) com blindagem de segurança, preparação de foto e auto-reparo de erros."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from .config import OUTPUT_DIR

# Proteção contra Image Decompression Bomb (DoS)
Image.MAX_IMAGE_PIXELS = 25_000_000

# Primitivas LaTeX perigosas bloqueadas em templates customizados (prevenção de RCE e leitura de arquivos)
_FORBIDDEN_LATEX_PATTERNS = (
    r"\\write18\b",
    r"\\immediate\s*\\write18\b",
    r"\\openin\b",
    r"\\openout\b",
    r"\\read\b",
    r"\\input\s*\{\s*(/|\\|\.\.)",
    r"\\include\s*\{\s*(/|\\|\.\.)",
    r"\\verbatiminput\b",
    r"\\lstinputlisting\b",
    r"\\import\s*\{",
    r"\\subimport\s*\{",
    r"\\catcode\b",
    r"\\csname\s*write",
    r"\\pdfprimitive\b",
    r"\\directlua\b",
)


def sanitize_custom_latex(latex_code: str) -> str:
    """Inspeciona e bloqueia primitivas LaTeX perigosas (RCE / Path Traversal / File Read)."""
    if not latex_code:
        return ""
    if len(latex_code) > 250_000:
        raise ValueError("Template LaTeX excede o tamanho máximo permitido (250 KB).")
    for pat in _FORBIDDEN_LATEX_PATTERNS:
        if re.search(pat, latex_code, flags=re.IGNORECASE):
            raise ValueError(
                "Template LaTeX bloqueado por segurança: contém comando de sistema ou leitura externa não permitido."
            )
    return latex_code


def _build_safe_tex_env() -> dict[str, str]:
    """Cria um ambiente isolado para o subprocesso pdflatex, sem vazar variáveis de ambiente do servidor."""
    safe_keys = (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "TEXMFMAIN",
        "TEXMFDIST",
        "TEXMFLOCAL",
        "TEXMFHOME",
        "TEXMFVAR",
        "TEXMFCONFIG",
    )
    env: dict[str, str] = {}
    for k in safe_keys:
        val = os.environ.get(k)
        if val:
            env[k] = val
    # Modo paranóico do Web2C/TeX Live: proíbe leitura/escrita fora do diretório de compilação e desativa shell_escape
    env["openin_any"] = "p"
    env["openout_any"] = "p"
    env["shell_escape"] = "f"
    return env


def prepare_photo_for_latex(
    build_dir: Path,
    photo_bytes: bytes | None = None,
    photo_path: str | Path | None = None,
    target_stem: str = "profile_photo",
) -> str | None:
    """Converte e salva a foto do usuário em PNG RGB compatível com pdflatex."""
    raw_bytes: bytes | None = photo_bytes
    if not raw_bytes and photo_path:
        p = Path(photo_path)
        if p.exists() and p.is_file():
            raw_bytes = p.read_bytes()

    if not raw_bytes:
        return None

    if len(raw_bytes) > 6 * 1024 * 1024:
        raise ValueError("A imagem de perfil excede o limite máximo de 6 MB.")

    build_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", target_stem).strip("_") or "profile_photo"
    out_filename = f"{safe_stem}.png"
    out_path = build_dir / out_filename

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        # Redimensiona mantendo proporção para evitar PDFs pesados
        img.thumbnail((600, 600))
        img.save(out_path, format="PNG")
        return out_filename
    except Exception:
        return None


def extract_concise_latex_error(log_text: str) -> str:
    """Extrai apenas as linhas decisivas de erro do log do pdflatex (economia de tokens)."""
    lines = log_text.splitlines()
    err_lines = []
    for idx, line in enumerate(lines):
        if line.startswith("!"):
            snippet = lines[max(0, idx - 1) : min(len(lines), idx + 6)]
            err_lines.extend(snippet)
            break
    if err_lines:
        return "\n".join(err_lines)
    return "\n".join(lines[-20:])


def get_pdflatex_path() -> str | None:
    """Localiza o executável `pdflatex` no PATH ou em instalações padrão do TeX Live / MiKTeX."""
    found = shutil.which("pdflatex")
    if found:
        return found
    candidates = [
        "/usr/bin/pdflatex",
        "/usr/local/bin/pdflatex",
        r"C:\texlive\2025\bin\windows\pdflatex.exe",
        r"C:\texlive\2024\bin\windows\pdflatex.exe",
        r"C:\texlive\2023\bin\windows\pdflatex.exe",
        str(Path.home() / r"AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"),
        r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def check_latex_compiler() -> Tuple[bool, str]:
    """Verifica se o compilador LaTeX (`pdflatex`) obrigatório está instalado e funcional."""
    bin_path = get_pdflatex_path()
    if not bin_path:
        return (
            False,
            "pdflatex não encontrado (instale TeX Live ou MiKTeX) / pdflatex not found (install TeX Live or MiKTeX).",
        )
    try:
        proc = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=_build_safe_tex_env(),
        )
        first_line = (proc.stdout or "").splitlines()[0].strip() if proc.stdout else "pdflatex"
        return True, first_line
    except Exception:
        return False, "Erro ao verificar pdflatex / Error checking pdflatex"


def sanitize_latex_layout(tex: str) -> str:
    """Higieniza o layout do LaTeX garantindo separação visual de parágrafos entre entradas estruturadas.

    Previne que linhas de instituições, empresas ou subtítulos se fundam na mesma linha
    que a próxima formação acadêmica ou cargo com `\\hfill`.
    """
    if not tex or not tex.strip():
        return tex

    lines = tex.splitlines()
    fixed_lines: List[str] = []

    # Detecta linhas de início de entrada (Grau, Cargo, Projeto) geralmente acompanhadas de \\hfill ou traço
    entry_header_pattern = re.compile(
        r"^\s*(?:\\noindent\s*)?\\textbf\{[^\}]+\}(?:\s*\\hfill|\s*---|---|\s*--|--)",
        re.IGNORECASE,
    )

    safe_end_pattern = re.compile(
        r"(\\par(?:\s*\\vspace\{[^\}]*\})?|\\end\{(?:itemize|enumerate|tabular|tabular\*|minipage)\})\s*$",
        re.IGNORECASE,
    )
    sec_header_pattern = re.compile(
        r"^\s*\\(?:section|subsection|subsubsection|cvsection|cventry|resumeSubHeadingListStart)\b",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if entry_header_pattern.match(stripped) and fixed_lines:
            prev_idx = len(fixed_lines) - 1
            while prev_idx >= 0 and not fixed_lines[prev_idx].strip():
                prev_idx -= 1

            if prev_idx >= 0:
                prev = fixed_lines[prev_idx].strip()
                if prev and not prev.startswith("%") and not sec_header_pattern.match(prev):
                    if prev.endswith(r"\\"):
                        fixed_lines[prev_idx] = fixed_lines[prev_idx][:-2].rstrip() + r"\par\vspace{3pt}"
                        if not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                            fixed_lines.append("")
                    elif not safe_end_pattern.search(prev):
                        fixed_lines[prev_idx] = fixed_lines[prev_idx] + r"\par\vspace{3pt}"
                        if not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                            fixed_lines.append("")
                    elif not any(not l.strip() for l in fixed_lines[prev_idx + 1:]):
                        fixed_lines.append("")

        fixed_lines.append(line)

    cleaned = "\n".join(fixed_lines)
    return clean_latex_project_verbs(cleaned)


def clean_latex_project_verbs(tex: str) -> str:
    """Higieniza itens na seção de projetos para iniciarem com substantivos e não verbos no passado."""
    if not tex or not tex.strip():
        return tex

    proj_sec_pattern = re.compile(
        r"(\\section\*?\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\\cvsection\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\\textbf\{[^}]*(?:Projetos|Projects)[^}]*\}|"
        r"\{\\large\\bfseries\\color\{accent\}\s*(?:TECHNICAL PROJECTS|PROJETOS TÉCNICOS|PROJETOS)[^}]*\})"
        r"(.*?)"
        r"(?=(\\(?:section\*?|cvsection|subsection)\b|\{\\large\\bfseries|\\end\{document\}|\Z))",
        re.IGNORECASE | re.DOTALL,
    )

    pt_verbs = r"(?:Desenvolveu|Criou|Implementou|Reuniu|Construiu|Elaborou|Projetou|Estruturou|Idealizou|Programou|Confeccionou|Organizou)"
    en_verbs = r"(?:Developed|Created|Implemented|Built|Designed|Engineered|Crafted|Constructed|Programmed|Gathered|Assembled|Authored)"

    item_pattern_pt = re.compile(rf"(\\item\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)
    colon_pattern_pt = re.compile(rf"(:\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)
    small_pattern_pt = re.compile(rf"(\{{\\small\s+)(?:{pt_verbs})\s+(?:(?:um|uma|o|a|os|as)\s+)?([A-Za-zÀ-ÖØ-öø-ÿ])", re.IGNORECASE)

    item_pattern_en = re.compile(rf"(\\item\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)
    colon_pattern_en = re.compile(rf"(:\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)
    small_pattern_en = re.compile(rf"(\{{\\small\s+)(?:{en_verbs})\s+(?:(?:a|an|the)\s+)?([A-Za-z])", re.IGNORECASE)

    def repl_sec(match):
        header = match.group(1)
        body = match.group(2)
        b = item_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", body)
        b = colon_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = small_pattern_pt.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = item_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = colon_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        b = small_pattern_en.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", b)
        return f"{header}{b}"

    return proj_sec_pattern.sub(repl_sec, tex)


def compile_latex_to_pdf(
    latex_code: str,
    output_stem: str = "curriculo",
    build_dir: Path | None = None,
) -> Tuple[bool, Path | None, Path, str]:
    """Compila código LaTeX em PDF usando pdflatex em ambiente restrito (-no-shell-escape).

    Retorna: (sucesso, caminho_pdf, caminho_tex, log_resumido)
    """
    sanitize_custom_latex(latex_code)
    latex_code = sanitize_latex_layout(latex_code)

    target_dir = (build_dir or OUTPUT_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", output_stem).strip("_") or "curriculo"
    tex_path = target_dir / f"{safe_stem}.tex"
    pdf_path = target_dir / f"{safe_stem}.pdf"

    tex_path.write_text(latex_code, encoding="utf-8")

    pdflatex_bin = get_pdflatex_path()
    if not pdflatex_bin:
        return (
            False,
            None,
            tex_path,
            "Requisito ausente: compilador `pdflatex` (TeX Live / MiKTeX) não encontrado no sistema.",
        )

    cmd = [
        pdflatex_bin,
        "-no-shell-escape",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            env=_build_safe_tex_env(),
        )
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True, pdf_path, tex_path, "Compilado com sucesso via pdflatex."
        err_msg = extract_concise_latex_error(proc.stdout + "\n" + proc.stderr)
        return False, None, tex_path, err_msg
    except Exception as exc:
        return False, None, tex_path, f"Falha na compilação LaTeX ({type(exc).__name__})."


def secure_wipe_and_remove_dir(dir_path: Path | str | None) -> None:
    """Sobrescreve com bytes nulos e remove com segurança todos os arquivos de um diretório efêmero.

    Garante a política de Zero-Storage no servidor: documentos recebidos (fotos, PDFs, XMLs)
    e gerados (.tex, .pdf, .aux, .log) são destruídos imediatamente após a requisição.
    """
    if not dir_path:
        return
    try:
        p = Path(dir_path).resolve()
        if not p.exists() or not p.is_dir():
            return
        for item in p.iterdir():
            try:
                if item.is_file():
                    size = item.stat().st_size
                    if size > 0:
                        with open(item, "wb") as f:
                            f.write(b"\x00" * min(size, 65536))
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass
        shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass



