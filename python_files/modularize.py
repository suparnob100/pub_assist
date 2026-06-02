import os
import re
from pathlib import Path


def modularize(input_folder, source_file):
    """
    Split a monolithic LaTeX file into per-section .tex files under a Sections/ subfolder,
    and rewrite the main file with \\include commands.

    Returns a dict with keys: sections_dir, main_file, section_files.
    """
    input_folder = Path(input_folder)
    source_path = input_folder / source_file
    sections_dir = input_folder / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    content = source_path.read_text(encoding="utf-8")

    section_content = []
    section_files = []
    preamble_content = ""
    inside_preamble = True
    inside_abstract = False
    outfile = None
    bib_commands = ""
    begin_abstract_in_line = False
    current_output_file = None

    for line in content.splitlines(keepends=True):
        # Collect bibliography commands
        bib_match = re.search(r"\\bibliography\{(.+?)\}", line)
        if bib_match:
            bib_commands += f"\\bibliography{{{bib_match.group(1)}}}\n"
        bibstyle_match = re.search(r"\\bibliographystyle\{(.+?)\}", line)
        if bibstyle_match:
            bib_commands += f"\\bibliographystyle{{{bibstyle_match.group(1)}}}\n"

        if "\\begin{abstract}" in line:
            inside_abstract = True
            begin_abstract_in_line = True
            current_output_file = "abstract"
            if outfile:
                outfile.close()
            outfile = open(sections_dir / "abstract.tex", "w", encoding="utf-8")
            continue

        if "\\end{abstract}" in line:
            inside_abstract = False
            if outfile:
                outfile.write("\n\\end{abstract}")
                outfile.close()
                outfile = None
            section_content.append(f"\\include{{sections/abstract}}")
            section_files.append("sections/abstract")
            continue

        match = re.match(r"\\(section\*?|appendix|preamble)\{(.+?)\}", line)

        if line.strip() == "\\begin{document}":
            inside_preamble = False
        elif inside_preamble:
            preamble_content += line
        elif match or line.strip() == "\\end{document}":
            if outfile:
                outfile.close()
                outfile = None
            if line.strip() == "\\end{document}":
                break
            current_output_file = match.group(2).strip().replace(" ", "_") if match else None
            if current_output_file:
                outfile = open(sections_dir / f"{current_output_file}.tex", "w", encoding="utf-8")
                section_content.append(f"\\include{{sections/{current_output_file}}}")
                section_files.append(f"sections/{current_output_file}")

        if outfile and not inside_preamble:
            if "\\bibliographystyle{" in line or "\\bibliography{" in line:
                continue
            if begin_abstract_in_line:
                outfile.write("\\begin{abstract}\n" + line)
                begin_abstract_in_line = False
            else:
                outfile.write(line)

    if outfile:
        outfile.close()

    # Build new main file
    preamble_base = preamble_content.split("\\begin{document}")[0]
    includeonly = (
        "\\includeonly{\n"
        + "\n".join(f"{f}," for f in section_files[:-1])
        + (f"\n{section_files[-1]}" if section_files else "")
        + "\n}\n"
    )
    all_includes = "\n".join(f"\\include{{{f}}}" for f in section_files)
    new_main = (
        preamble_base
        + includeonly
        + "\\begin{document}\n\\maketitle\n\\begingroup\n\\let\\clearpage\\relax\n\n"
        + all_includes
        + "\n\\endgroup\n"
        + bib_commands
        + "\\end{document}\n"
    )

    new_main_path = input_folder / "Manuscript_Main.tex"
    new_main_path.write_text(new_main, encoding="utf-8")

    return {
        "sections_dir": str(sections_dir.resolve()),
        "main_file": str(new_main_path.resolve()),
        "section_files": section_files,
    }
