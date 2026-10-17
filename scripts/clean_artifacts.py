"""Script utilitário para higienização e limpeza de arquivos temporários, caches e resíduos de compilação."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEMPORARY_EXTENSIONS = {
    ".aux",
    ".log",
    ".out",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".toc",
    ".nav",
    ".snm",
    ".vrb",
    ".bbl",
    ".blg",
    ".pyc",
    ".pyo",
}

DIRECTORIES_TO_CLEAN = [
    ROOT / ".cache",
    ROOT / "output",
    ROOT / ".pytest_cache",
]


def clean_project() -> None:
    print("🧹 Iniciando limpeza de resíduos temporários do projeto...")
    removed_files = 0
    removed_dirs = 0

    # 1. Remove arquivos temporários de compilação e cache Python
    for file_path in ROOT.rglob("*"):
        if file_path.is_file() and file_path.suffix in TEMPORARY_EXTENSIONS:
            try:
                file_path.unlink()
                removed_files += 1
            except Exception as e:
                print(f"⚠️ Não foi possível remover {file_path.name}: {e}")

    # 2. Remove pastas de cache Python (__pycache__)
    for pycache_dir in ROOT.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                removed_dirs += 1
            except Exception as e:
                print(f"⚠️ Não foi possível remover {pycache_dir}: {e}")

    # 3. Limpa pastas de cache temporárias configuradas
    for target_dir in DIRECTORIES_TO_CLEAN:
        if target_dir.exists() and target_dir.is_dir():
            for item in target_dir.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                        removed_files += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        removed_dirs += 1
                except Exception as e:
                    print(f"⚠️ Não foi possível limpar {item.name}: {e}")

    print(f"✅ Limpeza concluída: {removed_files} arquivos e {removed_dirs} diretórios limpos com sucesso.")


if __name__ == "__main__":
    clean_project()
