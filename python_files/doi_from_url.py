import html
import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from doi2bib import normalize_doi


DOI_RE = re.compile(
    r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s\"'<>]+)",
    re.IGNORECASE,
)

META_DOI_KEYS = {
    "citation_doi",
    "dc.identifier",
    "dc.identifier.doi",
    "dc.description.uri",
    "dc.source",
    "dc.doi",
    "doi",
    "prism.doi",
    "bepress_citation_doi",
}


def _clean_extracted_doi(value):
    doi = normalize_doi(html.unescape(urllib.parse.unquote(str(value))))
    doi = doi.strip().strip("<>").rstrip(".,;:")
    bracket_pairs = [("(", ")"), ("[", "]"), ("{", "}")]
    changed = True
    while changed and doi:
        changed = False
        for opener, closer in bracket_pairs:
            if doi.endswith(closer) and doi.count(closer) > doi.count(opener):
                doi = doi[:-1].rstrip(".,;:")
                changed = True
    return doi


def _unique(values):
    seen = set()
    out = []
    for value in values:
        doi = _clean_extracted_doi(value)
        if not doi:
            continue
        key = doi.lower()
        if key not in seen:
            seen.add(key)
            out.append(doi)
    return out


def extract_dois_from_text(text):
    return _unique(match.group(1) for match in DOI_RE.finditer(str(text or "")))


class _DoiHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata_dois = []
        self.link_dois = []
        self.json_text = []
        self._in_json_ld = False

    def handle_starttag(self, tag, attrs):
        attr = {str(k).lower(): v for k, v in attrs if v is not None}
        tag = tag.lower()

        if tag == "meta":
            key = (attr.get("name") or attr.get("property") or attr.get("itemprop") or "").lower()
            content = attr.get("content", "")
            if content and (key in META_DOI_KEYS or key.endswith(".doi") or "doi" in key):
                self.metadata_dois.extend(extract_dois_from_text(content))

        if tag in {"a", "link"}:
            href = attr.get("href", "")
            if "doi.org/" in href.lower() or DOI_RE.search(href):
                self.link_dois.extend(extract_dois_from_text(href))

        if tag == "script" and "ld+json" in (attr.get("type", "").lower()):
            self._in_json_ld = True

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self._in_json_ld = False

    def handle_data(self, data):
        if self._in_json_ld and data:
            self.json_text.append(data)


def _collect_json_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _collect_json_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _collect_json_values(item)
    elif isinstance(value, str):
        yield value


def _extract_json_dois(json_chunks):
    dois = []
    for chunk in json_chunks:
        text = chunk.strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            for value in _collect_json_values(parsed):
                dois.extend(extract_dois_from_text(value))
        except json.JSONDecodeError:
            dois.extend(extract_dois_from_text(text))
    return _unique(dois)


def _normalize_url(url):
    url = str(url or "").strip()
    if not url:
        raise ValueError("Journal article URL is required.")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, flags=re.IGNORECASE):
        url = "https://" + url
    return url


def _save_url_to_temp_html(url, target_dir, timeout=30, contact_email=""):
    parsed = urllib.parse.urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else url
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": origin,
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    if contact_email:
        headers["From"] = contact_email
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        final_url = response.geturl()
        html_path = Path(target_dir) / "journal_page.html"
        html_path.write_bytes(response.read())
    return final_url, html_path, charset


def _detect_html_charset(data):
    head = data[:8192].decode("ascii", errors="ignore")
    patterns = [
        r"<meta[^>]+charset=[\"']?\s*([a-z0-9._-]+)",
        r"<meta[^>]+content=[\"'][^\"']*charset=\s*([a-z0-9._-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, head, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return "utf-8"


def _read_saved_html(html_path, charset=""):
    data = Path(html_path).read_bytes()
    encoding = charset or _detect_html_charset(data)
    return data.decode(encoding, errors="replace")


def _doi_result(requested_url, final_url, doi, source, all_dois):
    return {
        "requested_url": requested_url,
        "final_url": final_url,
        "doi": doi,
        "doi_source": source,
        "all_dois": _unique(all_dois),
    }


def _sciencedirect_pii_from_url(url):
    parsed = urllib.parse.urlsplit(str(url or ""))
    if "sciencedirect.com" not in parsed.netloc.lower():
        return ""
    match = re.search(r"/pii/([^/?#]+)", parsed.path, flags=re.IGNORECASE)
    if not match:
        return ""
    return urllib.parse.unquote(match.group(1)).strip()


def _crossref_doi_from_alternative_id(identifier, timeout=30, contact_email=""):
    identifier = str(identifier or "").strip()
    if not identifier:
        return ""
    url = (
        "https://api.crossref.org/works?"
        f"filter=alternative-id:{urllib.parse.quote(identifier, safe='')}&rows=1"
    )
    user_agent = "pub-assist-doi-from-url/1.0"
    if contact_email:
        user_agent += f" (mailto:{contact_email})"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    items = data.get("message", {}).get("items", [])
    if not items:
        return ""
    return _clean_extracted_doi(items[0].get("DOI", ""))


def _elsevier_doi_from_pii(pii, timeout=30, contact_email=""):
    pii = str(pii or "").strip()
    if not pii:
        return ""
    url = (
        "https://api.elsevier.com/content/article/pii/"
        f"{urllib.parse.quote(pii, safe='')}?httpAccept=application/json"
    )
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    if contact_email:
        headers["From"] = contact_email
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    core = data.get("full-text-retrieval-response", {}).get("coredata", {})
    return _clean_extracted_doi(core.get("prism:doi") or core.get("dc:identifier") or "")


def _resolve_sciencedirect_pii(url, timeout=30, contact_email=""):
    pii = _sciencedirect_pii_from_url(url)
    if not pii:
        return None

    errors = []
    for source, resolver in [
        ("sciencedirect_pii_crossref", _crossref_doi_from_alternative_id),
        ("sciencedirect_pii_elsevier", _elsevier_doi_from_pii),
    ]:
        try:
            doi = resolver(pii, timeout=timeout, contact_email=contact_email)
            if doi:
                return _doi_result(url, url, doi, source, [doi])
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    if errors:
        raise RuntimeError(
            "Could not resolve the ScienceDirect PII to a DOI. "
            + "; ".join(errors)
        )
    return None


def _extract_doi_from_html_text(page_text, requested_url, final_url, url_dois=None):
    parser = _DoiHTMLParser()
    parser.feed(page_text)

    candidates = {
        "metadata": _unique(parser.metadata_dois),
        "json_ld": _extract_json_dois(parser.json_text),
        "doi_link": _unique(parser.link_dois),
        "url": _unique((url_dois or []) + extract_dois_from_text(final_url)),
        "page_text": extract_dois_from_text(page_text),
    }

    for source in ["metadata", "json_ld", "doi_link", "url", "page_text"]:
        if candidates[source]:
            all_dois = []
            for values in candidates.values():
                all_dois.extend(values)
            return _doi_result(requested_url, final_url, candidates[source][0], source, all_dois)

    raise RuntimeError("No DOI was found on the supplied page.")


def extract_doi_from_saved_html(html_path, charset=""):
    """
    Return the best article DOI found in a browser-saved HTML file.

    This is useful for publisher pages that block automated HTTP reads but
    still expose DOI metadata in the page a user saved from their browser.
    """
    html_path = Path(str(html_path or "").strip()).expanduser()
    if not html_path:
        raise ValueError("Saved HTML file path is required.")
    if not html_path.exists():
        raise FileNotFoundError(f"Saved HTML file does not exist: {html_path}")
    if not html_path.is_file():
        raise ValueError(f"Saved HTML path is not a file: {html_path}")

    resolved_path = html_path.resolve()
    page_text = _read_saved_html(resolved_path, charset)
    return _extract_doi_from_html_text(
        page_text,
        str(resolved_path),
        str(resolved_path),
        extract_dois_from_text(str(resolved_path)),
    )


def extract_doi_from_journal_url(url, timeout=30, contact_email=""):
    """
    Return the best article DOI found on a journal article page.

    Metadata DOIs are preferred over DOI links and page-text matches because
    page text often contains reference-list DOIs.
    """
    raw_url = str(url or "").strip()
    url_dois = extract_dois_from_text(raw_url)
    if url_dois:
        return _doi_result(raw_url, raw_url, url_dois[0], "url", url_dois)
    requested_url = _normalize_url(raw_url)
    sciencedirect_result = _resolve_sciencedirect_pii(requested_url, timeout, contact_email)
    if sciencedirect_result:
        return sciencedirect_result

    try:
        with tempfile.TemporaryDirectory(prefix="pub_assist_doi_page_") as temp_dir:
            final_url, html_path, charset = _save_url_to_temp_html(
                requested_url,
                temp_dir,
                timeout=timeout,
                contact_email=contact_email,
            )
            page_text = _read_saved_html(html_path, charset)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            "The journal page blocked Pub Assist from reading it "
            f"(HTTP {exc.code}: {exc.reason}). Paste a DOI or doi.org URL directly "
            "into the article URL field, or open the page in your browser and copy "
            "the DOI from the article page."
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(
            "Pub Assist could not read the journal page. "
            f"Reason: {reason}. Paste a DOI or doi.org URL directly if the site blocks automated access."
        ) from exc

    return _extract_doi_from_html_text(page_text, requested_url, final_url, url_dois)
