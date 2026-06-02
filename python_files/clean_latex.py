import shutil
import subprocess
import sys
from pathlib import Path


def clean_latex(latex_file, keep_bib=True):
    """
    Clean a single LaTeX file with arxiv_latex_cleaner.

    arxiv_latex_cleaner only operates on folders, so this wraps the file in a
    temporary folder, runs the cleaner (which emits a sibling *_arXiv folder),
    copies the cleaned file back out next to the original as *_cleaned.tex,
    then deletes both temporary folders.

    Requires: pip install arxiv_latex_cleaner

    Returns a dict with keys: output_file, returncode, stdout, stderr.
    """
    latex_file = Path(latex_file).resolve()
    if not latex_file.is_file():
        raise FileNotFoundError(f"LaTeX file not found: {latex_file}")

    parent = latex_file.parent
    tmp_src = parent / f"{latex_file.stem}__clean_src"
    arxiv_out = parent / f"{tmp_src.name}_arXiv"  # name arxiv_latex_cleaner produces

    # Clear any leftovers from a previous interrupted run.
    shutil.rmtree(tmp_src, ignore_errors=True)
    shutil.rmtree(arxiv_out, ignore_errors=True)

    tmp_src.mkdir()
    try:
        shutil.copy2(latex_file, tmp_src / latex_file.name)

        cmd = [sys.executable, "-m", "arxiv_latex_cleaner", str(tmp_src)]
        if keep_bib:
            cmd.append("--keep_bib")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        cleaned_src = arxiv_out / latex_file.name
        output_file = None
        if cleaned_src.is_file():
            dest = parent / f"{latex_file.stem}_cleaned.tex"
            shutil.copy2(cleaned_src, dest)
            output_file = str(dest)

        return {
            "output_file": output_file,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    finally:
        shutil.rmtree(tmp_src, ignore_errors=True)
        shutil.rmtree(arxiv_out, ignore_errors=True)
