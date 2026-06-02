import os
import re
import shutil
import subprocess
from pathlib import Path


def _default_search_paths():
    if os.name == "nt":
        candidates = [
            r"C:\Users\suparnob\AppData\Local\Programs\MiKTeX\tex\latex",
            r"C:\Program Files\MiKTeX\tex\latex",
            r"C:\Program Files (x86)\MiKTeX\tex\latex",
        ]
    else:
        candidates = [
            "/usr/share/texlive/texmf-dist/tex/latex",
            "/usr/local/texlive/texmf-local/tex/latex",
            "/Library/TeX/Root/texmf-dist/tex/latex",
            "/Library/TeX/Local/texmf/tex/latex",
        ]
        texlive_root = Path("/usr/local/texlive")
        if texlive_root.exists():
            for child in sorted(texlive_root.iterdir(), reverse=True):
                candidates.append(child / "texmf-dist" / "tex" / "latex")

    return [str(Path(path).expanduser()) for path in candidates if Path(path).expanduser().exists()]


def _find_with_kpsewhich(pkg):
    kpsewhich = shutil.which("kpsewhich")
    if not kpsewhich:
        return None

    result = subprocess.run(
        [kpsewhich, f"{pkg}.sty"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    path = Path(result.stdout.strip())
    return path if path.exists() else None


def _find_in_search_paths(pkg, search_paths):
    for base in search_paths:
        base_path = Path(base).expanduser()
        if not base_path.exists():
            continue
        for root, _, files in os.walk(base_path):
            if f"{pkg}.sty" in files:
                return Path(root) / f"{pkg}.sty"
    return None


def find_and_copy_latex_style_files(latex_file, output_folder, miktex_path=None):
    """
    Parse \\usepackage commands in latex_file, locate each .sty file, and copy
    them to output_folder.

    Returns a dict with keys: copied (list), not_found (list).
    """
    user_path = str(Path(miktex_path).expanduser()) if miktex_path else None
    search_paths = [user_path] if user_path else _default_search_paths()

    latex_file = Path(latex_file).expanduser()
    output_folder = Path(output_folder).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)

    content = latex_file.read_text(encoding="utf-8")
    pkg_pattern = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")
    packages = set()
    for m in pkg_pattern.findall(content):
        packages.update(p.strip() for p in m.split(","))

    copied, not_found = [], []
    for pkg in packages:
        src = _find_in_search_paths(pkg, search_paths)
        if src is None and not user_path:
            src = _find_with_kpsewhich(pkg)

        if src is None:
            not_found.append(pkg)
            continue

        shutil.copy2(src, output_folder / f"{pkg}.sty")
        copied.append(pkg)

    return {
        "copied": sorted(copied),
        "not_found": sorted(not_found),
        "search_paths": search_paths,
        "kpsewhich_available": shutil.which("kpsewhich") is not None,
    }
