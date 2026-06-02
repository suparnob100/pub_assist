import re
from pathlib import Path


def reassemble(input_folder, filename):
    """
    Replace all \\include{...} and \\input{...} commands in the main tex file
    with the actual content of the referenced files. Resolution is recursive,
    so included files that themselves include others are expanded too.

    Returns a dict with keys:
      output_file (absolute path string),
      merged      (list of references that were found and inlined),
      not_found   (list of references that could not be resolved).
    """
    input_folder = Path(input_folder)
    main_path = input_folder / filename

    merged = []
    not_found = []

    def resolve(ref):
        ref = ref.strip()
        candidates = [
            input_folder / (ref + ".tex"),
            input_folder / ref,
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    pattern = re.compile(r"\\(?:include|input)\{(.+?)\}")

    def expand(text, depth=0):
        if depth > 20:  # guard against include cycles
            return text

        def replacer(match):
            ref = match.group(1)
            target = resolve(ref)
            if target is None:
                not_found.append(ref)
                return match.group(0)
            merged.append(ref)
            return expand(target.read_text(encoding="utf-8"), depth + 1)

        return pattern.sub(replacer, text)

    main_content = main_path.read_text(encoding="utf-8")
    # Drop \includeonly{...} — it only restricts compilation, irrelevant once merged.
    main_content = re.sub(r"\\includeonly\{.*?\}", "", main_content, flags=re.DOTALL)

    replaced = expand(main_content)

    stem = Path(filename).stem
    output_path = input_folder / f"{stem}_reassembled.tex"
    output_path.write_text(replaced, encoding="utf-8")

    return {
        "output_file": str(output_path.resolve()),
        "merged": merged,
        "not_found": not_found,
    }
