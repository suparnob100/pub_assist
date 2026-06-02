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


def create_project(project_dir, sections=None, appendices=None, zip_result=True):
    """
    Create a structured LaTeX project folder.

    Returns a dict with keys: project_dir, files_created, zip_path (if zip_result).
    """
    sections = sections or DEFAULT_SECTIONS
    appendices = appendices or DEFAULT_APPENDICES

    project_path = Path(project_dir)
    sections_path = project_path / "Sections"
    appendices_path = sections_path / "Appendices"
    figures_path = project_path / "Figures"

    sections_path.mkdir(parents=True, exist_ok=True)
    appendices_path.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)

    files_created = []

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
        zip_path = shutil.make_archive(str(project_path), "zip", str(project_path))
        result["zip_path"] = zip_path

    return result
