import os
import re
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".eps"]

_INCLUDEGRAPHICS = re.compile(r"(\\includegraphics(?:\[[^\]]*\])?)\{([^}]+)\}")
_INPUT = re.compile(r"\\input\{(.+?)\}")
_INCLUDE = re.compile(r"\\include\{(.+?)\}")
_BIBLIOGRAPHY = re.compile(r"\\bibliography\{(.+?)\}")
_GRAPHICSPATH = re.compile(r"\\graphicspath\{\{(.+?)\}\}")


def _get_unique_filename(folder, basename):
    base, ext = os.path.splitext(basename)
    name = basename
    count = 1
    while os.path.exists(os.path.join(folder, name)):
        name = f"{base}_{count}{ext}"
        count += 1
    return name


def _update_references(content, old, new):
    for cmd in ("ref", "cref", "eqref", "label"):
        content = content.replace(f"\\{cmd}{{{old}}}", f"\\{cmd}{{{new}}}")
    return content


def _find_file(base_dir, graphics_paths, old_filename):
    has_ext = any(old_filename.endswith(ext) for ext in IMAGE_EXTENSIONS)
    candidates = []
    if has_ext:
        candidates.append(os.path.join(base_dir, old_filename))
        for gp in graphics_paths:
            candidates.append(os.path.join(base_dir, gp, os.path.basename(old_filename)))
    else:
        for ext in IMAGE_EXTENSIONS:
            candidates.append(os.path.join(base_dir, old_filename + ext))
        for gp in graphics_paths:
            for ext in IMAGE_EXTENSIONS:
                candidates.append(os.path.join(base_dir, gp, old_filename + ext))
    return next((c for c in candidates if os.path.exists(c)), None)


def collect_figures(input_folder, source_file, fig_folder_name="Figures_"):
    """
    Copy all figures referenced by source_file into a new figures folder and
    rewrite the tex to point at the new location.

    Returns a dict with keys: fig_folder, messages, output_tex.
    """
    input_folder = Path(input_folder)
    source_path = input_folder / source_file
    fig_folder = input_folder / fig_folder_name
    fig_folder.mkdir(parents=True, exist_ok=True)

    # Work on a copy so the original is not touched
    copy_path = source_path.with_stem(source_path.stem + "_copy")
    shutil.copy2(source_path, copy_path)

    base_dir = str(copy_path.parent.resolve())
    content = copy_path.read_text(encoding="utf-8")
    graphics_paths = _GRAPHICSPATH.findall(content)
    file_map = {}
    messages = []

    for prefix, old_filename in _INCLUDEGRAPHICS.findall(content):
        if old_filename in file_map:
            new_filename = file_map[old_filename]
            content = re.sub(
                rf"({re.escape(prefix)})\{{{re.escape(old_filename)}}}",
                rf"\1{{{new_filename}}}",
                content,
            )
            content = _update_references(content, old_filename, new_filename)
            continue
        found = _find_file(base_dir, graphics_paths, old_filename)
        if found:
            basename = os.path.basename(found)
            unique = _get_unique_filename(str(fig_folder), basename)
            shutil.copy(found, str(fig_folder / unique))
            file_map[old_filename] = unique
            content = re.sub(
                rf"({re.escape(prefix)})\{{{re.escape(old_filename)}}}",
                rf"\1{{{unique}}}",
                content,
            )
            content = _update_references(content, old_filename, unique)
        else:
            messages.append(f"Image not found: {old_filename}")

    for pattern in (_INPUT, _INCLUDE, _BIBLIOGRAPHY):
        for match in pattern.findall(content):
            if match in file_map:
                content = content.replace(match, file_map[match])
                content = _update_references(content, match, file_map[match])
                continue
            is_bib = pattern is _BIBLIOGRAPHY and not match.endswith(".bib")
            match_ext = match + ".bib" if is_bib else match
            candidates = [os.path.join(base_dir, match_ext)]
            for gp in graphics_paths:
                candidates.append(os.path.join(base_dir, gp, os.path.basename(match_ext)))
            found = next((c for c in candidates if os.path.exists(c)), None)
            if found:
                basename = os.path.basename(found)
                unique = _get_unique_filename(str(fig_folder), basename)
                shutil.copy(found, str(fig_folder / unique))
                file_map[match] = unique
                content = content.replace(match, unique)
                content = _update_references(content, match, unique)
            else:
                messages.append(f"File not found: {match}")

    content = re.sub(r"\\graphicspath\{\{.+?\}\}", "", content)
    graphicspath_line = f"\\graphicspath{{{{{fig_folder_name}/}}}}\n"
    gx_match = re.search(r"(\\usepackage\{graphicx\}.*?\n)", content)
    if gx_match:
        pos = gx_match.end()
        content = content[:pos] + graphicspath_line + content[pos:]
    else:
        content = graphicspath_line + content

    copy_path.write_text(content, encoding="utf-8")

    return {
        "fig_folder": str(fig_folder.resolve()),
        "output_tex": str(copy_path.resolve()),
        "messages": messages,
    }
