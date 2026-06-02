import os
import re
from pathlib import Path


def process_latex_file(input_filepath, output_filepath):
    """
    Rewrite a .tex file so each sentence starts on a new line.
    LaTeX environments are left untouched.
    """
    content = Path(input_filepath).read_text(encoding="utf-8")
    env_pattern = re.compile(r"(\\begin\{.*?\}.*?\\end\{.*?\})", re.DOTALL)
    chunks = re.split(env_pattern, content)

    processed = []
    for chunk in chunks:
        if chunk.strip().startswith("\\begin"):
            processed.append(chunk)
        else:
            lines = chunk.split("\n")
            new_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    new_lines.append("")
                    continue
                sentences = re.split(r"(?<=\.)\s", line)
                if len(sentences) > 1:
                    new_lines.append("\n".join(s.strip() for s in sentences if s.strip()))
                else:
                    new_lines.append(line)
            processed.append("\n".join(new_lines))

    Path(output_filepath).write_text("".join(processed), encoding="utf-8")


def process_all_tex_files(root_dir, output_dir=None):
    """
    Apply one-sentence-per-line formatting to every .tex file in root_dir.
    Writes *_processed.tex files to output_dir (defaults to root_dir).
    Returns a dict with key: processed_files (list of output paths).
    """
    root_dir = Path(root_dir)
    output_dir = Path(output_dir) if output_dir else root_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    processed = []
    for tex_file in root_dir.rglob("*.tex"):
        if "_processed" in tex_file.name:
            continue
        out = output_dir / tex_file.with_stem(tex_file.stem + "_processed").name
        process_latex_file(str(tex_file), str(out))
        processed.append(str(out))

    return {"processed_files": processed}
