import html
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


TEXCOUNT_ONLINE_PAGE = "https://app.uio.no/ifi/texcount/online.php"
TEXCOUNT_ONLINE_ENDPOINT = "https://app.uio.no/cgi-bin/ifi/texcount/texcount_3_2_0_41.cgi"


def _resolve_path(path):
    return Path(str(path or "").strip()).expanduser()


def _safe_prefix(value, fallback):
    text = str(value or "").strip() or fallback
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or fallback


def _tail(text, limit=2000):
    text = str(text or "")
    return text[-limit:] if len(text) > limit else text


def _resolve_command(command):
    command = str(command or "texcount").strip() or "texcount"
    if any(sep in command for sep in ("/", "\\")):
        path = _resolve_path(command)
        if not path.is_file():
            raise FileNotFoundError(f"TexCount command does not exist: {path}")
        return str(path.resolve())
    found = shutil.which(command)
    if not found:
        raise FileNotFoundError(
            f"TexCount command '{command}' was not found on PATH. "
            "Install a TeX distribution with texcount, or use the online service."
        )
    return found


class _HTMLTextExtractor(HTMLParser):
    _break_tags = {"br", "p", "div", "h1", "h2", "h3", "li", "tr"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in self._break_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in self._break_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        if data:
            self.parts.append(data)

    def text(self):
        text = html.unescape("".join(self.parts))
        lines = []
        for line in text.splitlines():
            cleaned = re.sub(r"[ \t]+", " ", line).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines) + "\n"


def _html_to_text(html_text):
    parser = _HTMLTextExtractor()
    parser.feed(html_text or "")
    text = parser.text()
    marker = "Format/colour codes of verbose output:"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n"
    return text


def _extract_counts(text):
    counts = {}
    patterns = {
        "words_in_text": r"Words in text:\s*([0-9]+)",
        "words_in_headers": r"Words in headers:\s*([0-9]+)",
        "words_outside_text": r"Words outside text.*?:\s*([0-9]+)",
        "headers": r"Number of headers:\s*([0-9]+)",
        "floats": r"Number of floats/tables/figures:\s*([0-9]+)",
        "math_inlines": r"Number of math inlines:\s*([0-9]+)",
        "math_displayed": r"Number of math displayed:\s*([0-9]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            counts[key] = int(match.group(1))
    return counts


def _read_latex_file(path):
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def _prepare_output(latex_path=None, output_folder="", output_prefix="", fallback_stem="pasted_text"):
    if output_folder:
        out_dir = _resolve_path(output_folder).resolve()
    elif latex_path is not None:
        out_dir = latex_path.parent / "texcount_reports"
    else:
        out_dir = Path.cwd() / "texcount_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = _safe_prefix(output_prefix, latex_path.stem if latex_path is not None else fallback_stem)
    return out_dir, prefix


def _source_from_file_or_text(latex_file="", latex_text=""):
    latex_text = str(latex_text or "")
    if latex_text.strip():
        return None, latex_text, "pasted_text", "Pasted text"

    raw_path = str(latex_file or "").strip()
    if not raw_path:
        raise ValueError("Provide a main .tex file or paste LaTeX/text into the text box.")

    latex_path = _resolve_path(raw_path).resolve()
    if not latex_path.is_file():
        raise FileNotFoundError(f"LaTeX file does not exist: {latex_path}")

    latex_code, encoding = _read_latex_file(latex_path)
    return latex_path, latex_code, encoding, str(latex_path)


def _post_texcount_online(latex_code, summary=True, timeout_seconds=120):
    fields = {
        "verbosity": "3",
        "subcounts": "subsection",
        "sum": "111" if summary else "0",
        "wordrule": "normal",
        "incbib": "0",
        "language": "count-all",
        "wordfreq": "0",
        "fileencoding": "utf8",
        "latexcode": latex_code,
    }
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        TEXCOUNT_ONLINE_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "PubAssist/1.0 (+https://app.uio.no/ifi/texcount/)",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _run_texcount_online(
    latex_path,
    latex_code,
    file_encoding,
    source_label,
    output_folder="",
    output_prefix="",
    summary=True,
    html_report=True,
    timeout_seconds=120,
):
    out_dir, prefix = _prepare_output(latex_path, output_folder, output_prefix)
    text_path = out_dir / f"{prefix}_texcount.txt"
    html_path = out_dir / f"{prefix}_texcount.html"

    try:
        html_text = _post_texcount_online(latex_code, summary=summary, timeout_seconds=timeout_seconds)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"TeXcount web service returned HTTP {exc.code}.\n\n{_tail(detail)}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach the TeXcount web service: {exc}") from exc

    if "LaTeX word count" not in html_text:
        raise RuntimeError(
            "TeXcount web service returned an unexpected response.\n\n"
            f"{_tail(_html_to_text(html_text))}"
        )

    text_report = _html_to_text(html_text)
    text_path.write_text(text_report, encoding="utf-8")
    if html_report:
        html_path.write_text(html_text, encoding="utf-8")

    return {
        "returncode": 0,
        "service": "online",
        "service_label": "TeXcount web service",
        "online_page": TEXCOUNT_ONLINE_PAGE,
        "online_endpoint": TEXCOUNT_ONLINE_ENDPOINT,
        "source": source_label,
        "latex_file": str(latex_path) if latex_path is not None else "",
        "file_encoding": file_encoding,
        "include_subfiles": False,
        "summary": summary,
        "html_report": html_report,
        "paths": {
            "text_report": str(text_path.resolve()),
            "html_report": str(html_path.resolve()) if html_report else "",
            "output_folder": str(out_dir.resolve()),
        },
        "counts": _extract_counts(text_report),
        "command": ["POST", TEXCOUNT_ONLINE_ENDPOINT],
        "notes": [
            "The online TeXcount service analyses the selected file content only; it does not read local \\input or \\include subfiles.",
        ],
    }


def _run_texcount_local(
    latex_path,
    output_folder="",
    output_prefix="",
    texcount_command="texcount",
    include_subfiles=True,
    summary=True,
    html_report=True,
    timeout_seconds=120,
):
    out_dir, prefix = _prepare_output(latex_path, output_folder, output_prefix)
    text_path = out_dir / f"{prefix}_texcount.txt"
    html_path = out_dir / f"{prefix}_texcount.html"
    command = _resolve_command(texcount_command)

    base_args = [command, "-utf8"]
    if include_subfiles:
        base_args.append("-inc")
    if summary:
        base_args.append("-sum")

    text_cmd = [*base_args, str(latex_path)]
    text_result = subprocess.run(
        text_cmd,
        cwd=str(latex_path.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    text_path.write_text(text_result.stdout or "", encoding="utf-8")

    html_result = None
    if html_report:
        html_cmd = [*base_args, "-html", str(latex_path)]
        html_result = subprocess.run(
            html_cmd,
            cwd=str(latex_path.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        html_path.write_text(html_result.stdout or "", encoding="utf-8")

    stderr_parts = [text_result.stderr or ""]
    if html_result is not None:
        stderr_parts.append(html_result.stderr or "")
    stderr = "\n".join(part for part in stderr_parts if part)
    returncode = text_result.returncode
    if html_result is not None and html_result.returncode != 0:
        returncode = html_result.returncode

    response = {
        "returncode": returncode,
        "service": "local",
        "service_label": "Local texcount command",
        "source": str(latex_path),
        "latex_file": str(latex_path),
        "texcount_command": command,
        "include_subfiles": include_subfiles,
        "summary": summary,
        "html_report": html_report,
        "paths": {
            "text_report": str(text_path.resolve()),
            "html_report": str(html_path.resolve()) if html_report else "",
            "output_folder": str(out_dir.resolve()),
        },
        "counts": _extract_counts(text_result.stdout or ""),
        "command": text_cmd,
        "notes": [],
    }
    if returncode != 0:
        raise RuntimeError(
            "Local TexCount failed.\n\n"
            f"Command: {' '.join(text_cmd)}\n\n"
            f"stdout:\n{_tail(text_result.stdout)}\n\n"
            f"stderr:\n{_tail(stderr)}"
        )
    return response


def run_texcount(
    latex_file,
    latex_text="",
    output_folder="",
    output_prefix="",
    service="online",
    texcount_command="texcount",
    include_subfiles=True,
    summary=True,
    html_report=True,
    timeout_seconds=120,
):
    latex_path, latex_code, file_encoding, source_label = _source_from_file_or_text(latex_file, latex_text)

    service = str(service or "online").strip().lower()
    if service == "local":
        if latex_path is None:
            raise ValueError("Local texcount mode requires a .tex file. Use TeXcount website mode for pasted text.")
        return _run_texcount_local(
            latex_path,
            output_folder=output_folder,
            output_prefix=output_prefix,
            texcount_command=texcount_command,
            include_subfiles=include_subfiles,
            summary=summary,
            html_report=html_report,
            timeout_seconds=timeout_seconds,
        )
    if service != "online":
        raise ValueError("TexCount service must be 'online' or 'local'.")

    return _run_texcount_online(
        latex_path,
        latex_code,
        file_encoding,
        source_label,
        output_folder=output_folder,
        output_prefix=output_prefix,
        summary=summary,
        html_report=html_report,
        timeout_seconds=timeout_seconds,
    )
