import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def normalize_doi(value):
    doi = str(value).strip().strip("<>").replace("\u200b", "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    doi = urllib.parse.unquote(doi)
    return doi.strip().rstrip(".,;")


def _user_agent(contact_email=""):
    ua = "pub-assist-doi-to-bibtex/1.0"
    if contact_email:
        ua += f" (mailto:{contact_email})"
    return ua


def _read_url(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _fetch_from_doi_org(doi, timeout, contact_email=""):
    url = f"https://doi.org/{urllib.parse.quote(doi, safe='/')}"
    return _read_url(url, {"Accept": "application/x-bibtex", "User-Agent": _user_agent(contact_email)}, timeout)


def _fetch_from_crossref(doi, timeout, contact_email=""):
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}/transform/application/x-bibtex"
    return _read_url(url, {"Accept": "application/x-bibtex", "User-Agent": _user_agent(contact_email)}, timeout)


def format_bibtex_entry(bibtex, indent="  "):
    text = " ".join(str(bibtex).strip().split())
    if not text.startswith("@"):
        return str(bibtex).strip()

    def fmt_seg(seg):
        seg = seg.strip()
        if seg.startswith("@") or seg == "}":
            return seg
        return re.sub(r"^([^=]+?)\s*=\s*", lambda m: f"{m.group(1).strip()} = ", seg, count=1)

    lines, current, brace_depth, in_quote, escaped = [], [], 0, False, False

    def append_line(seg):
        seg = fmt_seg(seg)
        if seg:
            lines.append(seg if not lines else indent + seg)

    for char in text:
        current.append(char)
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and brace_depth == 1:
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                final = "".join(current).rstrip()
                append_line(final[:-1] if final.endswith("}") else final)
                lines.append("}")
                current = []
        elif char == "," and brace_depth == 1:
            append_line("".join(current))
            current = []

    trailing = "".join(current).strip()
    if trailing:
        append_line(trailing)

    return "\n".join(line.rstrip() for line in lines if line.strip())


def fetch_bibtex(doi, timeout=30, contact_email=""):
    errors = []
    for name, fetcher in [("doi.org", _fetch_from_doi_org), ("crossref", _fetch_from_crossref)]:
        try:
            bibtex = fetcher(doi, timeout=timeout, contact_email=contact_email).strip()
            if bibtex.startswith("@"):
                return format_bibtex_entry(bibtex)
            errors.append(f"{name}: response was not BibTeX")
        except urllib.error.HTTPError as exc:
            errors.append(f"{name}: HTTP {exc.code} {exc.reason}")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("; ".join(errors))


def generate_bibtex_entries(dois, timeout=30, contact_email="", pause_seconds=0.2, progress_cb=None):
    """
    Fetch BibTeX for a list of DOIs.
    progress_cb(doi, status) called for each DOI if provided.
    Returns (entries, failures) where entries = [(doi, bibtex_str)].
    """
    entries, failures, seen = [], [], set()
    for raw_doi in dois:
        doi = normalize_doi(raw_doi)
        if not doi:
            continue
        key = doi.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            bibtex = fetch_bibtex(doi, timeout=timeout, contact_email=contact_email)
            entries.append((doi, bibtex))
            if progress_cb:
                progress_cb(doi, "ok")
        except Exception as exc:
            failures.append((doi, str(exc)))
            if progress_cb:
                progress_cb(doi, f"failed: {exc}")
        time.sleep(pause_seconds)
    return entries, failures


def write_bibtex_file(entries, output_file, append=False):
    output_path = Path(output_file)
    mode = "a" if append and output_path.exists() else "w"
    with output_path.open(mode, encoding="utf-8") as f:
        if mode == "a" and output_path.stat().st_size > 0:
            f.write("\n\n")
        f.write("\n\n".join(bib for _, bib in entries))
        if entries:
            f.write("\n")
    return str(output_path.resolve())
