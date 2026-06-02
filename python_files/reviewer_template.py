from pathlib import Path


def latex_escape(text):
    replacements = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


def _format_affils(affils):
    return ",".join(str(a) for a in affils)


def build_author_block(authors, affiliations, corresponding_email):
    lines = []
    for author in authors:
        name = latex_escape(author["name"])
        tag = _format_affils(author["affils"])
        if author.get("corresponding", False):
            lines.append(
                rf"\author[{tag}]{{{name}\thanks{{corresponding author: {latex_escape(corresponding_email)}}}}}"
            )
        else:
            lines.append(rf"\author[{tag}]{{{name}}}")
    lines.append("")
    for idx, affil in affiliations.items():
        lines.append(rf"\affil[{idx}]{{{latex_escape(affil)}}}")
    return "\n".join(lines)


def build_reviewer_section(reviewer_number, n_comments):
    lines = [
        rf"\section*{{Reviewer \#{reviewer_number}}}",
        "",
        rf"\begin{{enumerate}}[label=\textbf{{Comment {reviewer_number}.\arabic*:}}]",
        "",
    ]
    for _ in range(n_comments):
        lines += [
            r"\item",
            r"\commenttext{Paste reviewer comment here.}",
            "",
            r"\responsetext{Write the response here.}",
            "",
            r"\revisiontext{Describe the manuscript change here.}",
            "",
        ]
    lines += [r"\end{enumerate}", ""]
    return "\n".join(lines)


_LATEX_DOC = r"""\documentclass[10pt]{article}
\usepackage[centertags]{amsmath}
\usepackage{amssymb,amsfonts,bm,authblk}
\usepackage{graphicx}
\usepackage[dvipsnames]{xcolor}
\usepackage{enumitem}
\setlist[enumerate]{leftmargin=*,partopsep=0pt,itemsep=6pt,parsep=6pt}
\usepackage[margin=1.25in]{geometry}
\usepackage{setspace}
\usepackage[labelfont=bf,labelsep=space]{caption}
\definecolor{Blue}{rgb}{0,0,.8}
\usepackage[colorlinks=true,citecolor=green,linkcolor=black,urlcolor=Blue]{hyperref}
\usepackage[sort]{natbib}
\bibliographystyle{abbrv}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\renewenvironment{quote}{\color{Blue}\list{}{\leftmargin=.25in\rightmargin=0.25in\topsep=0in\parsep=6pt}\item[]}{\endlist}
\newcommand{\commenttext}[1]{\noindent\textbf{Reviewer comment:}\begin{quote}#1\end{quote}}
\newcommand{\responsetext}[1]{\noindent\textbf{Response:} #1}
\newcommand{\revisiontext}[1]{\noindent\textbf{Revision made:} #1}
\title{\large \bf Response to Reviewers' Comments:\\[2pt]
\vspace{5pt}\Large __TITLE__\\
\vspace{5pt}\emph{__JOURNAL__}\\
\vspace{5pt}\large Submission~ID:~__ID__}
__AUTHOR_BLOCK__
\date{\today}
\begin{document}
\maketitle
\begin{quote}
We thank the editor and reviewers for their constructive comments.
\end{quote}
__REVIEWER_SECTIONS__
\section*{Additional Changes}
List any additional revisions not tied to a specific reviewer comment.
\end{document}
"""


def build_template(
    manuscript_title,
    journal_name,
    submission_id,
    corresponding_author_email,
    authors,
    affiliations,
    reviewer_comment_counts,
    output_tex_file,
):
    """
    Generate a response-to-reviewers LaTeX template.

    authors: list of dicts with keys: name, affils (list), corresponding (bool)
    affiliations: dict mapping int → str
    reviewer_comment_counts: dict mapping reviewer_number → n_comments
    Returns a dict with key: output_file.
    """
    author_block = build_author_block(authors, affiliations, corresponding_author_email)
    reviewer_sections = "\n".join(
        build_reviewer_section(num, n) for num, n in reviewer_comment_counts.items()
    )

    latex = (
        _LATEX_DOC
        .replace("__TITLE__", latex_escape(manuscript_title))
        .replace("__JOURNAL__", latex_escape(journal_name))
        .replace("__ID__", latex_escape(submission_id))
        .replace("__AUTHOR_BLOCK__", author_block)
        .replace("__REVIEWER_SECTIONS__", reviewer_sections)
    )

    output_path = Path(output_tex_file)
    output_path.write_text(latex, encoding="utf-8")
    return {"output_file": str(output_path.resolve())}
