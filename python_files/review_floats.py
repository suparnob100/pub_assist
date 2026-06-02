import re
from pathlib import Path


def extract_preamble(latex_code):
    match = re.search(r"^(.*?)\\begin\{document\}", latex_code, re.DOTALL)
    return match.group(1) if match else ""


def extract_environments(latex_code, environments):
    extracted = {}
    for env in environments:
        pattern = re.compile(
            r"(?<!%)\\begin\{" + env + r"\}(.*?)\\end\{" + env + r"\}", re.DOTALL
        )
        matches = re.findall(pattern, latex_code)
        filtered = []
        for match in matches:
            lines = match.strip().split("\n")
            if any(not line.strip().startswith("%") for line in lines):
                filtered.append(f"\\begin{{{env}}}{match}\\end{{{env}}}")
        extracted[env] = filtered
    return extracted


def write_floats_file(extracted, output_path, preamble):
    postamble = "\n\\end{document}"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(preamble + "\n\\begin{document}\n")
        for env, items in extracted.items():
            if items:
                f.write(f"\n% Extracted {env} environments\n")
                f.write("\n\n".join(items) + "\n")
        f.write(postamble)


def review_floats(input_folder, input_filename, environments=None):
    """
    Extract LaTeX float environments into a separate *_floats_only.tex file.

    Returns a dict with key: output_file.
    """
    environments = environments or ["equation", "align", "table", "figure"]
    input_path = Path(input_folder) / input_filename

    latex_code = input_path.read_text(encoding="utf-8")
    preamble = extract_preamble(latex_code)
    extracted = extract_environments(latex_code, environments)

    stem = input_path.stem
    output_path = input_path.parent / f"{stem}_floats_only.tex"
    write_floats_file(extracted, output_path, preamble)

    counts = {env: len(items) for env, items in extracted.items()}
    return {"output_file": str(output_path.resolve()), "counts": counts}
