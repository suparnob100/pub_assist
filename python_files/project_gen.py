import os
import shutil
from pathlib import Path


DEFAULT_SECTIONS = ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion"]
DEFAULT_APPENDICES = ["AppendixA", "AppendixB"]

MAIN_TEX_TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[margin=1.25in]{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{mathpazo}
\pagestyle{fancy}
\lhead{} \chead{} \rhead{}
\lfoot{} \cfoot{\thepage} \rfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\usepackage{amsmath, amssymb, bm, mathtools, amsfonts}
\usepackage{siunitx}
\usepackage{algorithm}
\usepackage{algcompatible}
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\newtheorem{theorem}{Theorem}[section]
\usepackage{graphicx, xcolor, tikz}
\usepackage{float}
\graphicspath{{Figures/}}
\usepackage{multirow, booktabs}
\renewcommand{\arraystretch}{1.7}
\usepackage{caption, subcaption}
\captionsetup[figure]{labelfont={bf}}
\captionsetup[table]{labelfont={bf}}
\usepackage[numbers,sort&compress]{natbib}
\usepackage[colorlinks=true, citecolor=blue, linkcolor=red, urlcolor=blue]{hyperref}
\usepackage[capitalise]{cleveref}
\usepackage{authblk}
\title{\textbf{Title of the Paper}}
\author[1]{Author Name 1}
\author[2]{Author Name 2}
\affil[1]{Affiliation 1}
\affil[2]{Affiliation 2}
\date{}
\begin{document}
\maketitle
\tableofcontents
__SECTION_INPUTS__
\bibliographystyle{unsrtnat}
\bibliography{references.bib}
\appendix
__APPENDIX_INPUTS__
\end{document}
"""

BIB_TEMPLATE = """\
@article{sample2023,
  author    = {John Doe and Jane Smith},
  title     = {A Sample Paper on LaTeX Automation},
  journal   = {Journal of Automated Documentation},
  year      = {2023},
  volume    = {10},
  number    = {2},
  pages     = {100--120},
  doi       = {10.1234/sample.2023},
}
"""


def _safe_zip_project(project_path):
    tmp_base = project_path.parent / f".{project_path.name}_archive_tmp"
    tmp_zip = tmp_base.with_suffix(".zip")
    final_zip = project_path.parent / f"{project_path.name}.zip"

    if tmp_zip.exists():
        tmp_zip.unlink()

    try:
        archive_path = shutil.make_archive(str(tmp_base), "zip", str(project_path))
        archive_path = Path(archive_path)
        os.replace(archive_path, final_zip)
    except Exception:
        if tmp_zip.exists():
            tmp_zip.unlink()
        raise

    return str(final_zip.resolve())


def create_project(project_dir, sections=None, appendices=None, zip_result=True, project_name="manuscript"):
    """
    Create a structured LaTeX project folder inside the selected parent folder.

    Returns a dict with keys: project_dir, files_created, zip_path (if zip_result).
    """
    sections = sections or DEFAULT_SECTIONS
    appendices = appendices or DEFAULT_APPENDICES

    parent_path = Path(project_dir).expanduser().resolve()
    parent_path.mkdir(parents=True, exist_ok=True)

    project_name = str(project_name or "manuscript").strip() or "manuscript"
    if project_name in {".", ".."} or any(sep in project_name for sep in ("/", "\\")):
        raise ValueError("project_name must be a simple folder name, such as 'manuscript'.")

    project_path = parent_path / project_name
    if project_path.exists() and any(project_path.iterdir()):
        raise FileExistsError(
            f"Project folder already exists and is not empty: {project_path}\n"
            "Choose an empty destination folder, or remove/rename the existing manuscript folder."
        )

    sections_path = project_path / "Sections"
    appendices_path = sections_path / "Appendices"
    figures_path = project_path / "Figures"

    sections_path.mkdir(parents=True, exist_ok=True)
    appendices_path.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)

    files_created = []
    figures_placeholder = figures_path / ".gitkeep"
    figures_placeholder.write_text(
        "Placeholder so empty Figures/ folders are preserved in zip uploads.\n",
        encoding="utf-8",
    )
    files_created.append(str(figures_placeholder))

    for section in sections:
        p = sections_path / f"{section}.tex"
        p.write_text(f"% {section}\n\n\\section{{{section}}}\n\nText here.\n", encoding="utf-8")
        files_created.append(str(p))

    for appendix in appendices:
        p = appendices_path / f"{appendix}.tex"
        p.write_text(f"% {appendix}\n\n\\section{{{appendix}}}\n\nText here.\n", encoding="utf-8")
        files_created.append(str(p))

    section_inputs = "\n".join(f"\\input{{Sections/{s}}}" for s in sections)
    appendix_inputs = "\n".join(f"\\input{{Sections/Appendices/{a}}}" for a in appendices)
    main_tex = (
        MAIN_TEX_TEMPLATE
        .replace("__SECTION_INPUTS__", section_inputs)
        .replace("__APPENDIX_INPUTS__", appendix_inputs)
    )
    main_path = project_path / "Manuscript_main.tex"
    main_path.write_text(main_tex, encoding="utf-8")
    files_created.append(str(main_path))

    bib_path = project_path / "references.bib"
    bib_path.write_text(BIB_TEMPLATE, encoding="utf-8")
    files_created.append(str(bib_path))

    result = {"project_dir": str(project_path.resolve()), "files_created": files_created}

    if zip_result:
        zip_path = _safe_zip_project(project_path)
        result["zip_path"] = zip_path

    return result
