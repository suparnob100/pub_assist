import os
import json
import shlex
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BIBTEX_TIDY_COMMAND = "npx --yes bibtex-tidy@latest"
BIBTEX_TIDY_WEB_PAGE = "https://flamingtempura.github.io/bibtex-tidy/"
BIBTEX_TIDY_WEB_BUNDLE_URL = "https://flamingtempura.github.io/bibtex-tidy/bundle.js"
BIBTEX_TIDY_WEB_EXTRACT_MARKER = ";var Up=[]"
DEFAULT_SORT_FIELDS = [
    "title",
    "shorttitle",
    "author",
    "year",
    "month",
    "day",
    "journal",
    "booktitle",
    "location",
    "on",
    "publisher",
    "address",
    "series",
    "volume",
    "number",
    "pages",
    "doi",
    "isbn",
    "issn",
    "url",
    "urldate",
    "copyright",
    "category",
    "note",
    "metadata",
]


def _resolve_path(path):
    return Path(str(path or "").strip()).expanduser()


def _split_command(command):
    command = str(command or "").strip() or DEFAULT_BIBTEX_TIDY_COMMAND
    return shlex.split(command, posix=os.name != "nt")


def _tail(text, limit=4000):
    text = str(text or "")
    return text[-limit:] if len(text) > limit else text


def _count_entries(text):
    count = 0
    for line in str(text or "").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("@") and "{" in stripped:
            count += 1
    return count


def _int_or_none(value):
    text = str(value or "").strip()
    if not text:
        return None
    return int(text)


def _list_option(value):
    return [item for item in str(value or "").replace(",", " ").split() if item]


def _list_cli_option(value):
    return ",".join(_list_option(value))


def _safe_jsonable_warnings(warnings):
    cleaned = []
    for warning in warnings or []:
        if isinstance(warning, dict):
            cleaned.append({
                "code": str(warning.get("code", "")),
                "rule": str(warning.get("rule", "")),
                "message": str(warning.get("message", "")),
            })
        else:
            cleaned.append({"message": str(warning)})
    return cleaned


def _build_options(
    backup=True,
    indent_mode="tab",
    space_count=2,
    align_values=True,
    align_column=13,
    wrap_values=False,
    wrap_column=80,
    blank_lines=False,
    curly=True,
    enclosing_braces=False,
    enclosing_braces_fields="",
    remove_braces=False,
    remove_braces_fields="",
    strip_enclosing_braces=False,
    numeric=True,
    months=False,
    drop_all_caps=False,
    escape=False,
    encode_urls=False,
    remove_empty_fields=False,
    remove_duplicate_fields=False,
    max_authors=False,
    max_authors_count=20,
    sort_entries=False,
    sort_order="",
    sort_fields=True,
    sort_field_order="",
    check_duplicates=True,
    duplicate_keys=True,
    duplicate_dois=False,
    duplicate_citations=False,
    duplicate_abstracts=False,
    merge_duplicates=False,
    merge_strategy="combine",
    omit_fields=False,
    omit_field_list="",
    strip_comments=False,
    tidy_comments=True,
    lowercase=True,
    generate_keys=False,
    generate_key_pattern="",
    trailing_commas=False,
):
    options = {
        "backup": bool(backup),
        "space": max(0, _int_or_none(space_count) or 0),
        "tab": str(indent_mode or "").lower() == "tab",
        "align": (_int_or_none(align_column) or 13) if align_values else 1,
        "blankLines": bool(blank_lines),
        "curly": bool(curly),
        "stripEnclosingBraces": bool(strip_enclosing_braces),
        "numeric": bool(numeric),
        "months": bool(months),
        "dropAllCaps": bool(drop_all_caps),
        "escape": bool(escape),
        "encodeUrls": bool(encode_urls),
        "tidyComments": bool(tidy_comments),
        "removeEmptyFields": bool(remove_empty_fields),
        "removeDuplicateFields": bool(remove_duplicate_fields),
        "lowercase": bool(lowercase),
        "stripComments": bool(strip_comments),
        "trailingCommas": bool(trailing_commas),
    }
    if wrap_values:
        options["wrap"] = _int_or_none(wrap_column) or 80
    if enclosing_braces:
        fields = _list_option(enclosing_braces_fields)
        if fields:
            options["enclosingBraces"] = fields
    if remove_braces:
        fields = _list_option(remove_braces_fields)
        if fields:
            options["removeBraces"] = fields
    if max_authors:
        options["maxAuthors"] = max(1, _int_or_none(max_authors_count) or 1)
    if sort_entries:
        sort = _list_option(sort_order)
        options["sort"] = sort or ["key"]
    if sort_fields:
        options["sortFields"] = _list_option(sort_field_order) or DEFAULT_SORT_FIELDS
    duplicates = []
    if check_duplicates:
        if duplicate_keys:
            duplicates.append("key")
        if duplicate_dois:
            duplicates.append("doi")
        if duplicate_citations:
            duplicates.append("citation")
        if duplicate_abstracts:
            duplicates.append("abstract")
    if duplicates:
        options["duplicates"] = duplicates
    if merge_duplicates:
        options["merge"] = str(merge_strategy or "combine").strip().lower() or "combine"
    if omit_fields:
        fields = _list_option(omit_field_list)
        if fields:
            options["omit"] = fields
    if generate_keys:
        pattern = str(generate_key_pattern or "").strip()
        options["generateKeys"] = pattern or "[auth][year][veryshorttitle]"
    return options


def _options_to_cli_args(options):
    args = []
    if options.get("curly"):
        args.append("--curly")
    if options.get("numeric"):
        args.append("--numeric")
    if options.get("tab"):
        args.append("--tab")
    else:
        args.append(f"--space={options.get('space', 2)}")
    align = options.get("align", 1)
    if align and align > 1:
        args.append(f"--align={align}")
    if options.get("wrap"):
        args.append(f"--wrap={options['wrap']}")
    if options.get("blankLines"):
        args.append("--blank-lines")
    if options.get("enclosingBraces"):
        args.append(f"--enclosing-braces={','.join(options['enclosingBraces'])}")
    if options.get("removeBraces"):
        args.append(f"--remove-braces={','.join(options['removeBraces'])}")
    if options.get("stripEnclosingBraces"):
        args.append("--strip-enclosing-braces")
    if options.get("months"):
        args.append("--months")
    if options.get("dropAllCaps"):
        args.append("--drop-all-caps")
    args.append("--escape" if options.get("escape") else "--no-escape")
    if options.get("encodeUrls"):
        args.append("--encode-urls")
    if options.get("removeEmptyFields"):
        args.append("--remove-empty-fields")
    args.append("--remove-dupe-fields" if options.get("removeDuplicateFields") else "--no-remove-dupe-fields")
    if options.get("maxAuthors"):
        args.append(f"--max-authors={options['maxAuthors']}")
    if options.get("sort"):
        args.append(f"--sort={','.join(options['sort'])}")
    if options.get("sortFields"):
        fields = options["sortFields"]
        args.append("--sort-fields" if fields == DEFAULT_SORT_FIELDS else f"--sort-fields={','.join(fields)}")
    if options.get("duplicates"):
        args.append(f"--duplicates={','.join(options['duplicates'])}")
    if options.get("merge"):
        args.append(f"--merge={options['merge']}")
    if options.get("omit"):
        args.append(f"--omit={','.join(options['omit'])}")
    if options.get("stripComments"):
        args.append("--strip-comments")
    if not options.get("tidyComments", True):
        args.append("--no-tidy-comments")
    if not options.get("lowercase", True):
        args.append("--no-lowercase")
    if options.get("generateKeys"):
        args.append(f"--generate-keys={options['generateKeys']}")
    if options.get("trailingCommas"):
        args.append("--trailing-commas")
    return args


def _download_web_bundle(timeout_seconds=120):
    request = urllib.request.Request(
        BIBTEX_TIDY_WEB_BUNDLE_URL,
        headers={"User-Agent": "PubAssist/1.0 (+https://flamingtempura.github.io/bibtex-tidy/)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            bundle = response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach the BibTeX Tidy website bundle: {exc}") from exc
    if BIBTEX_TIDY_WEB_EXTRACT_MARKER not in bundle or "function Hp" not in bundle or "function Ul" not in bundle:
        raise RuntimeError("The BibTeX Tidy website bundle changed and Pub Assist could not find the tidy function.")
    return bundle


def _write_web_runner(path):
    path.write_text(
        r'''
const fs = require("fs");
const vm = require("vm");

const [bundlePath, inputPath, optionsPath, outputPath] = process.argv.slice(2);
const bundle = fs.readFileSync(bundlePath, "utf8");
const marker = ";var Up=[]";
const markerIndex = bundle.indexOf(marker);
if (markerIndex === -1) throw new Error("Could not find BibTeX Tidy website extraction marker.");
const patched = `${bundle.slice(0, markerIndex)};globalThis.__pubAssistBibtexTidy={tidy:Hp,makeOptions:Ul,defaultBibtex:g_};})();`;
const context = {
  console: { log() {}, error() {}, warn() {} },
  URLSearchParams,
  setTimeout,
  clearTimeout,
};
context.globalThis = context;
context.window = { location: { search: "" }, addEventListener() {}, history: { pushState() {} } };
context.document = { body: {} };
vm.createContext(context);
vm.runInContext(patched, context, { timeout: 20000 });
const bibtex = fs.readFileSync(inputPath, "utf8");
const options = context.__pubAssistBibtexTidy.makeOptions(JSON.parse(fs.readFileSync(optionsPath, "utf8")));
const result = context.__pubAssistBibtexTidy.tidy(bibtex, options);
fs.writeFileSync(outputPath, result.bibtex, "utf8");
process.stdout.write(JSON.stringify({
  count: result.count,
  warnings: result.warnings || [],
  bundle_url: "https://flamingtempura.github.io/bibtex-tidy/bundle.js"
}));
'''.lstrip(),
        encoding="utf-8",
    )


def clean_bibtex_file(
    input_bib_file,
    output_bib_file="",
    service="website",
    command=DEFAULT_BIBTEX_TIDY_COMMAND,
    modify_input=False,
    backup=True,
    indent_mode="tab",
    space_count=2,
    align_values=True,
    align_column=13,
    wrap_values=False,
    wrap_column=80,
    blank_lines=False,
    curly=True,
    enclosing_braces=False,
    enclosing_braces_fields="",
    remove_braces=False,
    remove_braces_fields="",
    strip_enclosing_braces=False,
    numeric=True,
    months=False,
    drop_all_caps=False,
    escape=False,
    encode_urls=False,
    remove_empty_fields=False,
    remove_duplicate_fields=False,
    max_authors=False,
    max_authors_count=20,
    sort_entries=False,
    sort_order="",
    sort_fields=True,
    sort_field_order="",
    check_duplicates=True,
    duplicate_keys=True,
    duplicate_dois=False,
    duplicate_citations=False,
    duplicate_abstracts=False,
    merge_duplicates=False,
    merge_strategy="combine",
    omit_fields=False,
    omit_field_list="",
    strip_comments=False,
    tidy_comments=True,
    lowercase=True,
    generate_keys=False,
    generate_key_pattern="",
    trailing_commas=False,
    extra_options="",
    timeout_seconds=120,
):
    input_path = _resolve_path(input_bib_file).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"BibTeX input file does not exist: {input_path}")

    modify_input = bool(modify_input)
    if output_bib_file and not modify_input:
        output_path = _resolve_path(output_bib_file).resolve()
    elif modify_input:
        output_path = input_path
    else:
        output_path = input_path.with_name(f"{input_path.stem}_cleaned{input_path.suffix or '.bib'}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    before_text = input_path.read_text(encoding="utf-8", errors="replace")
    options = _build_options(
        backup=backup,
        indent_mode=indent_mode,
        space_count=space_count,
        align_values=align_values,
        align_column=align_column,
        wrap_values=wrap_values,
        wrap_column=wrap_column,
        blank_lines=blank_lines,
        curly=curly,
        enclosing_braces=enclosing_braces,
        enclosing_braces_fields=enclosing_braces_fields,
        remove_braces=remove_braces,
        remove_braces_fields=remove_braces_fields,
        strip_enclosing_braces=strip_enclosing_braces,
        numeric=numeric,
        months=months,
        drop_all_caps=drop_all_caps,
        escape=escape,
        encode_urls=encode_urls,
        remove_empty_fields=remove_empty_fields,
        remove_duplicate_fields=remove_duplicate_fields,
        max_authors=max_authors,
        max_authors_count=max_authors_count,
        sort_entries=sort_entries,
        sort_order=sort_order,
        sort_fields=sort_fields,
        sort_field_order=sort_field_order,
        check_duplicates=check_duplicates,
        duplicate_keys=duplicate_keys,
        duplicate_dois=duplicate_dois,
        duplicate_citations=duplicate_citations,
        duplicate_abstracts=duplicate_abstracts,
        merge_duplicates=merge_duplicates,
        merge_strategy=merge_strategy,
        omit_fields=omit_fields,
        omit_field_list=omit_field_list,
        strip_comments=strip_comments,
        tidy_comments=tidy_comments,
        lowercase=lowercase,
        generate_keys=generate_keys,
        generate_key_pattern=generate_key_pattern,
        trailing_commas=trailing_commas,
    )
    service = str(service or "website").strip().lower()
    backup_path = input_path.with_name(f"{input_path.name}.original")
    warnings = []
    stdout_tail = ""
    stderr_tail = ""

    if modify_input and backup:
        backup_path.write_text(before_text, encoding="utf-8")

    if service in {"website", "web", "online"}:
        node = shutil.which("node")
        if not node:
            raise FileNotFoundError(
                "The BibTeX Tidy website-bundle route needs Node.js to execute the website JavaScript. "
                "Install Node.js LTS, then rerun the cleaner. This route does not require npm installing bibtex-tidy."
            )
        bundle = _download_web_bundle(timeout_seconds=timeout_seconds)
        with tempfile.TemporaryDirectory(prefix=".pubassist_bibclean_", dir=str(output_path.parent)) as tmp:
            tmp_dir = Path(tmp)
            bundle_path = tmp_dir / "bundle.js"
            runner_path = tmp_dir / "run_bibtex_tidy_web.js"
            options_path = tmp_dir / "options.json"
            bundle_path.write_text(bundle, encoding="utf-8")
            options_path.write_text(json.dumps(options), encoding="utf-8")
            _write_web_runner(runner_path)
            full_cmd = [node, str(runner_path), str(bundle_path), str(input_path), str(options_path), str(output_path)]
            result = subprocess.run(
                full_cmd,
                cwd=str(input_path.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        if result.returncode != 0:
            raise RuntimeError(
                "BibTeX Tidy website-bundle route failed.\n\n"
                f"Command: {' '.join(full_cmd)}\n\n"
                f"stdout:\n{_tail(result.stdout)}\n\n"
                f"stderr:\n{_tail(result.stderr)}"
            )
        try:
            web_result = json.loads(result.stdout or "{}")
            warnings = _safe_jsonable_warnings(web_result.get("warnings", []))
        except json.JSONDecodeError:
            warnings = []
        stdout_tail = _tail(result.stdout)
        stderr_tail = _tail(result.stderr)
        command_for_report = ["GET", BIBTEX_TIDY_WEB_BUNDLE_URL, "then", "node", "website-bundle"]
        service_label = "BibTeX Tidy website bundle"
    elif service in {"local", "npm", "npx"}:
        cmd = _split_command(command)
        args = []
        if modify_input:
            args.append("--modify")
            if backup:
                args.append("--backup")
        else:
            args.extend(["--output", str(output_path)])
        args.extend(_options_to_cli_args(options))
        if extra_options:
            args.extend(shlex.split(str(extra_options), posix=os.name != "nt"))
        args.append(str(input_path))

        full_cmd = [*cmd, *args]
        try:
            result = subprocess.run(
                full_cmd,
                cwd=str(input_path.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Could not find '{cmd[0]}'. Install Node.js/npm for the default npx command, "
                "or install bibtex-tidy globally and set the command to 'bibtex-tidy'."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "bibtex-tidy failed.\n\n"
                f"Command: {' '.join(full_cmd)}\n\n"
                f"stdout:\n{_tail(result.stdout)}\n\n"
                f"stderr:\n{_tail(result.stderr)}"
            )
        stdout_tail = _tail(result.stdout)
        stderr_tail = _tail(result.stderr)
        command_for_report = full_cmd
        service_label = "Local npm/npx bibtex-tidy"
    else:
        raise ValueError("BibTeX cleaner service must be 'website' or 'local'.")

    if not output_path.is_file():
        raise RuntimeError("BibTeX cleaner finished without creating the output file.")

    after_text = output_path.read_text(encoding="utf-8", errors="replace")
    return {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "backup_file": str(backup_path) if backup_path.is_file() else "",
        "service": service,
        "service_label": service_label,
        "website_page": BIBTEX_TIDY_WEB_PAGE if service in {"website", "web", "online"} else "",
        "website_bundle": BIBTEX_TIDY_WEB_BUNDLE_URL if service in {"website", "web", "online"} else "",
        "entries_before": _count_entries(before_text),
        "entries_after": _count_entries(after_text),
        "bytes_before": len(before_text.encode("utf-8")),
        "bytes_after": len(after_text.encode("utf-8")),
        "warnings": warnings,
        "command": command_for_report,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "preview": after_text[:3000],
    }
