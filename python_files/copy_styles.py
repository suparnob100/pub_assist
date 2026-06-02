import os
import re
import shutil
from pathlib import Path


def find_and_copy_latex_style_files(latex_file, output_folder, miktex_path=None):
    """
    Parse \\usepackage commands in latex_file, locate each .sty file in miktex_path,
    and copy them to output_folder.

    Returns a dict with keys: copied (list), not_found (list).
    """
    default_paths = [
        r"C:\Users\suparnob\AppData\Local\Programs\MiKTeX\tex\latex",
        r"C:\Program Files\MiKTeX\tex\latex",
        r"C:\Program Files (x86)\MiKTeX\tex\latex",
    ]
    search_paths = [miktex_path] if miktex_path else default_paths

    latex_file = Path(latex_file)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    content = latex_file.read_text(encoding="utf-8")
    pkg_pattern = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")
    packages = set()
    for m in pkg_pattern.findall(content):
        packages.update(p.strip() for p in m.split(","))

    copied, not_found = [], []
    for pkg in packages:
        found = False
        for base in search_paths:
            for root, _, files in os.walk(base):
                if f"{pkg}.sty" in files:
                    src = Path(root) / f"{pkg}.sty"
                    shutil.copy(src, output_folder / f"{pkg}.sty")
                    copied.append(pkg)
                    found = True
                    break
            if found:
                break
        if not found:
            not_found.append(pkg)

    return {"copied": sorted(copied), "not_found": sorted(not_found)}
