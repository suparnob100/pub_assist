"""
Pub Assist — local web app.
Run: uvicorn app:app --reload --port 7654
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent / "python_files"))

from beautify import process_all_tex_files as beautify_files
from bibtex_cleaner import DEFAULT_BIBTEX_TIDY_COMMAND, DEFAULT_SORT_FIELDS, clean_bibtex_file
from clean_latex import clean_latex
from collect_figures import collect_figures
from copy_styles import find_and_copy_latex_style_files
from doi2bib import generate_bibtex_entries, write_bibtex_file
from doi_from_url import extract_doi_from_journal_url, extract_doi_from_saved_html
from latexdiff_web import (
    normalize_bib_mode,
    prepare_latexdiff_workspace,
    run_local_latexdiff,
    run_latexdiff_worker,
    run_online_latexdiff,
)
from modularize import modularize
from one_sentence import process_all_tex_files as one_sentence_files
from project_gen import create_project
from reassemble import reassemble
from review_floats import review_floats
from reviewer_template import build_template
from submission_docs import generate_submission_documents
from texcount_runner import run_texcount

app = FastAPI(title="Pub Assist")
_pool = ThreadPoolExecutor(max_workers=4)
_jobs: dict[str, dict] = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_job():
    jid = str(uuid.uuid4())[:8]
    _jobs[jid] = {"status": "running", "started": datetime.now().isoformat(), "result": None, "error": None}
    return jid


def _finish_job(jid, result):
    _jobs[jid]["status"] = "done"
    _jobs[jid]["result"] = result


def _fail_job(jid, exc):
    _jobs[jid]["status"] = "error"
    _jobs[jid]["error"] = traceback.format_exc()


async def _run_in_pool(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, lambda: fn(*args, **kwargs))


def _ok(data: Any):
    return JSONResponse({"status": "ok", **data})


def _err(msg: str, code: int = 400):
    return JSONResponse({"status": "error", "error": msg}, status_code=code)


def _user_path(path: str | None):
    if not path:
        return path
    return os.path.expandvars(os.path.expanduser(path))


# ── static + root ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def root():
    return FileResponse(str(Path(__file__).parent / "static" / "index.html"))


@app.get("/api/jobs/{jid}")
async def get_job(jid: str):
    job = _jobs.get(jid)
    if not job:
        return _err("Job not found", 404)
    return JSONResponse({"status": job["status"], "result": job["result"], "error": job["error"]})


# ── Open folder in the OS file manager ────────────────────────────────────────

class OpenFolderRequest(BaseModel):
    path: str


class SelectPathRequest(BaseModel):
    mode: str = "file"
    title: str = "Select path"
    initial_path: str = ""
    file_kind: str = ""


def _dialog_initial_path(path):
    if not path:
        return Path.home(), ""

    candidate = Path(_user_path(path))
    if not candidate.is_absolute():
        candidate = Path(__file__).parent / candidate
    candidate = candidate.expanduser()

    if candidate.is_dir():
        return candidate, ""
    if candidate.parent.exists():
        return candidate.parent, candidate.name
    return Path.home(), candidate.name


def _dialog_filetypes(kind):
    if kind == "tex":
        return [("LaTeX files", "*.tex"), ("All files", "*.*")]
    if kind == "zip":
        return [("Zip files", "*.zip"), ("All files", "*.*")]
    if kind == "bib":
        return [("BibTeX files", "*.bib"), ("All files", "*.*")]
    if kind == "html":
        return [("HTML files", "*.html *.htm"), ("All files", "*.*")]
    return [("All files", "*.*")]


def _select_path_dialog(mode, title, initial_path="", file_kind=""):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(
            "Native file picker is unavailable. Install Tk support for Python "
            "(for example python3-tk on many Linux distributions), or type the path manually."
        ) from exc

    initial_dir, initial_file = _dialog_initial_path(initial_path)
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    def ask_file():
        return filedialog.askopenfilename(
            title=title,
            initialdir=str(initial_dir),
            initialfile=initial_file,
            filetypes=_dialog_filetypes(file_kind),
            parent=root,
        )

    def ask_folder():
        return filedialog.askdirectory(
            title=title,
            initialdir=str(initial_dir),
            parent=root,
        )

    try:
        if mode == "folder":
            selected = ask_folder()
        elif mode == "file-or-folder":
            choice = {"path": ""}
            window = tk.Toplevel(root)
            window.title(title)
            window.resizable(False, False)
            try:
                window.attributes("-topmost", True)
            except tk.TclError:
                pass

            label = tk.Label(window, text="Choose a project folder or a zip file.", padx=18, pady=12)
            label.pack()
            buttons = tk.Frame(window, padx=12, pady=12)
            buttons.pack()

            def choose_folder():
                choice["path"] = ask_folder()
                window.destroy()

            def choose_file():
                choice["path"] = ask_file()
                window.destroy()

            tk.Button(buttons, text="Choose Folder", command=choose_folder, width=16).pack(side=tk.LEFT, padx=4)
            tk.Button(buttons, text="Choose Zip/File", command=choose_file, width=16).pack(side=tk.LEFT, padx=4)
            tk.Button(buttons, text="Cancel", command=window.destroy, width=10).pack(side=tk.LEFT, padx=4)
            window.protocol("WM_DELETE_WINDOW", window.destroy)
            window.grab_set()
            window.wait_window()
            selected = choice["path"]
        else:
            selected = ask_file()
    finally:
        root.destroy()

    return str(Path(selected).resolve()) if selected else ""


@app.post("/api/open-folder")
async def api_open_folder(req: OpenFolderRequest):
    raw = (req.path or "").strip()
    if not raw:
        return _err("No path provided.")

    p = Path(_user_path(raw))
    if not p.is_absolute():
        p = Path(__file__).parent / p
    p = p.resolve()

    select = p.is_file()
    if p.is_file():
        folder = p.parent
    elif p.is_dir():
        folder = p
    elif p.parent.is_dir():
        folder, select = p.parent, False
    else:
        return _err(f"Path does not exist: {p}")

    try:
        if sys.platform.startswith("win"):
            if select:
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                os.startfile(str(folder))  # noqa: S606 — local desktop action
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p)] if select else ["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except Exception as exc:
        return _err(f"Could not open folder: {exc}")

    return _ok({"opened": str(folder)})


@app.post("/api/select-path")
async def api_select_path(req: SelectPathRequest):
    try:
        mode = (req.mode or "file").strip().lower()
        if mode not in {"file", "folder", "file-or-folder"}:
            return _err("mode must be 'file', 'folder', or 'file-or-folder'.")
        selected = _select_path_dialog(
            mode=mode,
            title=req.title or "Select path",
            initial_path=req.initial_path or "",
            file_kind=(req.file_kind or "").strip().lower(),
        )
        if not selected:
            return _ok({"path": ""})
        return _ok({"path": selected})
    except Exception as exc:
        return _err(str(exc))


# ── Step 1 — New Project ──────────────────────────────────────────────────────

class NewProjectRequest(BaseModel):
    project_dir: str
    sections: list[str] = []
    appendices: list[str] = []
    zip_result: bool = True


@app.post("/api/project/create")
async def api_create_project(req: NewProjectRequest):
    try:
        result = await _run_in_pool(
            create_project, _user_path(req.project_dir), req.sections or None, req.appendices or None, req.zip_result
        )
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Modularize ────────────────────────────────────────────────────────────────

class FolderFileRequest(BaseModel):
    input_folder: str
    source_file: str


@app.post("/api/modularize")
async def api_modularize(req: FolderFileRequest):
    try:
        result = await _run_in_pool(modularize, _user_path(req.input_folder), req.source_file)
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── One sentence per line ─────────────────────────────────────────────────────

class OneSentenceRequest(BaseModel):
    root_dir: str
    output_dir: str = ""


@app.post("/api/one-sentence")
async def api_one_sentence(req: OneSentenceRequest):
    try:
        result = await _run_in_pool(one_sentence_files, _user_path(req.root_dir), _user_path(req.output_dir) if req.output_dir else None)
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 2 — Reassemble ───────────────────────────────────────────────────────

class ReassembleRequest(BaseModel):
    input_folder: str
    filename: str


@app.post("/api/reassemble")
async def api_reassemble(req: ReassembleRequest):
    try:
        result = await _run_in_pool(reassemble, _user_path(req.input_folder), req.filename)
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 3 — Clean LaTeX ──────────────────────────────────────────────────────

class CleanRequest(BaseModel):
    latex_file: str
    keep_bib: bool = True


@app.post("/api/clean")
async def api_clean(req: CleanRequest):
    try:
        result = await _run_in_pool(clean_latex, _user_path(req.latex_file), req.keep_bib)
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 4 — Review Floats ────────────────────────────────────────────────────

class ReviewFloatsRequest(BaseModel):
    input_folder: str
    input_filename: str
    environments: list[str] = []


@app.post("/api/review-floats")
async def api_review_floats(req: ReviewFloatsRequest):
    try:
        result = await _run_in_pool(
            review_floats, req.input_folder, req.input_filename, req.environments or None
        )
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 5 — Collect Figures ──────────────────────────────────────────────────

@app.post("/api/collect-figures")
async def api_collect_figures(req: FolderFileRequest):
    try:
        result = await _run_in_pool(collect_figures, _user_path(req.input_folder), req.source_file)
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 6 — Beautify ─────────────────────────────────────────────────────────

class BeautifyRequest(BaseModel):
    root_dir: str
    input_file: str
    comment_column: int = 0
    indent_size: int = 4


@app.post("/api/beautify")
async def api_beautify(req: BeautifyRequest):
    try:
        result = await _run_in_pool(
            beautify_files, _user_path(req.root_dir), req.input_file, _user_path(req.root_dir), req.comment_column, req.indent_size
        )
        return _ok({"message": "Beautification complete.", "root_dir": req.root_dir, "input_file": req.input_file})
    except Exception as exc:
        return _err(str(exc))


# ── Step 7 — Reviewer Response Template ──────────────────────────────────────

class ReviewerTemplateRequest(BaseModel):
    manuscript_title: str
    journal_name: str
    submission_id: str
    corresponding_author_email: str
    authors: list[dict]
    affiliations: dict
    reviewer_comment_counts: dict
    output_tex_file: str


@app.post("/api/reviewer-template")
async def api_reviewer_template(req: ReviewerTemplateRequest):
    try:
        affils = {int(k): v for k, v in req.affiliations.items()}
        counts = {int(k): v for k, v in req.reviewer_comment_counts.items()}
        result = await _run_in_pool(
            build_template,
            req.manuscript_title, req.journal_name, req.submission_id,
            req.corresponding_author_email, req.authors, affils, counts,
            _user_path(req.output_tex_file),
        )
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 8 — LaTeX Diff (background job) ─────────────────────────────────────

class LatexdiffRequest(BaseModel):
    old_project: str
    new_project: str
    main_tex: str = "manuscript.tex"
    bib: str | None = None
    latexdiff_engine: str = "online"
    use_docker: bool = False
    confirm_online_upload: bool = True
    online_latexdiff_url: str = "https://3142.nl/latex-diff/"
    online_latexdiff_timeout_seconds: int = 120
    style: str | None = None
    workspace_dir: str = "latexdiff_runs/current"


@app.post("/api/latexdiff")
async def api_latexdiff(req: LatexdiffRequest):
    jid = _new_job()

    async def _run():
        try:
            engine = (req.latexdiff_engine or "").lower().strip()
            if req.use_docker:
                engine = "docker"
            if engine not in {"online", "local", "docker"}:
                raise ValueError("latexdiff_engine must be 'online', 'local', or 'docker'.")
            if engine == "online" and not req.confirm_online_upload:
                raise ValueError("Online latexdiff selected, but confirm_online_upload is false.")
            bib = normalize_bib_mode(req.bib)

            ws = await _run_in_pool(
                prepare_latexdiff_workspace,
                _user_path(req.old_project), _user_path(req.new_project), req.main_tex,
                _user_path(req.workspace_dir), bib, req.style,
            )
            if engine == "docker":
                docker_use_cmd = os.name == "nt" and shutil.which("cmd") is not None
                result = await _run_in_pool(
                    run_latexdiff_worker,
                    ws["workspace"],
                    use_cmd=docker_use_cmd,
                    check=False,
                )
            elif engine == "online":
                result = await _run_in_pool(
                    run_online_latexdiff,
                    ws["workspace"],
                    req.online_latexdiff_url,
                    "pdflatex",
                    True,
                    req.online_latexdiff_timeout_seconds,
                )
            else:
                result = await _run_in_pool(run_local_latexdiff, ws["workspace"])
            if result.get("returncode", 0) != 0:
                raise RuntimeError(
                    "Latexdiff failed. Inspect the returned paths and logs below.\n\n"
                    + json.dumps(result, indent=2)
                )
            _finish_job(jid, {**ws, "latexdiff_engine": engine, **result})
        except Exception as exc:
            _fail_job(jid, exc)

    asyncio.create_task(_run())
    return JSONResponse({"status": "running", "job_id": jid})


# ── DOI → BibTeX ──────────────────────────────────────────────────────────────

class Doi2BibRequest(BaseModel):
    dois: list[str]
    saved_html_files: list[str] = []
    output_bib_file: str = "references_from_dois.bib"
    append: bool = False
    contact_email: str = ""
    timeout: int = 30
    pause_seconds: float = 0.2


class BibtexCleanRequest(BaseModel):
    input_bib_file: str
    output_bib_file: str = ""
    service: str = "website"
    command: str = DEFAULT_BIBTEX_TIDY_COMMAND
    modify_input: bool = False
    backup: bool = True
    indent_mode: str = "tab"
    space_count: int = 2
    align_values: bool = True
    align_column: int = 13
    wrap_values: bool = False
    wrap_column: int = 80
    blank_lines: bool = False
    curly: bool = True
    enclosing_braces: bool = False
    enclosing_braces_fields: str = ""
    remove_braces: bool = False
    remove_braces_fields: str = ""
    strip_enclosing_braces: bool = False
    numeric: bool = True
    months: bool = False
    drop_all_caps: bool = False
    escape: bool = False
    encode_urls: bool = False
    remove_empty_fields: bool = False
    remove_duplicate_fields: bool = False
    max_authors: bool = False
    max_authors_count: int = 20
    sort_entries: bool = False
    sort_order: str = ""
    sort_fields: bool = True
    sort_field_order: str = " ".join(DEFAULT_SORT_FIELDS)
    check_duplicates: bool = True
    duplicate_keys: bool = True
    duplicate_dois: bool = False
    duplicate_citations: bool = False
    duplicate_abstracts: bool = False
    merge_duplicates: bool = False
    merge_strategy: str = "combine"
    omit_fields: bool = False
    omit_field_list: str = ""
    strip_comments: bool = False
    tidy_comments: bool = True
    lowercase: bool = True
    generate_keys: bool = False
    generate_key_pattern: str = ""
    trailing_commas: bool = False
    extra_options: str = ""


def _split_doi_inputs(values):
    for value in values or []:
        for item in str(value or "").replace(",", "\n").splitlines():
            item = item.strip()
            if item:
                yield item


@app.post("/api/doi2bib")
async def api_doi2bib(req: Doi2BibRequest):
    jid = _new_job()

    async def _run():
        try:
            resolved, extraction_failures, seen = [], [], set()

            def add_resolved(raw, extracted):
                doi_key = extracted["doi"].lower()
                if doi_key in seen:
                    return
                seen.add(doi_key)
                resolved.append({
                    "input": raw,
                    "doi": extracted["doi"],
                    "doi_source": extracted["doi_source"],
                    "resolved_url": extracted["final_url"],
                })

            for raw in _split_doi_inputs(req.dois):
                try:
                    extracted = extract_doi_from_journal_url(raw, req.timeout, req.contact_email)
                    add_resolved(raw, extracted)
                except Exception as exc:
                    extraction_failures.append((raw, str(exc)))

            for raw in req.saved_html_files:
                raw = str(raw or "").strip()
                if not raw:
                    continue
                try:
                    html_path = _user_path(raw)
                    extracted = extract_doi_from_saved_html(html_path)
                    add_resolved(raw, extracted)
                except Exception as exc:
                    extraction_failures.append((raw, str(exc)))

            entries, failures = await _run_in_pool(
                generate_bibtex_entries,
                [item["doi"] for item in resolved],
                req.timeout,
                req.contact_email,
                req.pause_seconds,
            )
            out_file = _user_path(req.output_bib_file.strip() or "references_from_dois.bib")
            output_path = str(Path(out_file).resolve())
            if entries:
                output_path = await _run_in_pool(write_bibtex_file, entries, out_file, req.append)
            _finish_job(jid, {
                "output_file": output_path,
                "entries_count": len(entries),
                "resolved_inputs": resolved,
                "bibtex_entries": [{"doi": doi, "bibtex": bibtex} for doi, bibtex in entries],
                "bibtex_text": "\n\n".join(bibtex for _, bibtex in entries),
                "failures": extraction_failures + failures,
            })
        except Exception as exc:
            _fail_job(jid, exc)

    asyncio.create_task(_run())
    return JSONResponse({"status": "running", "job_id": jid})


@app.post("/api/bibtex-clean")
async def api_bibtex_clean(req: BibtexCleanRequest):
    jid = _new_job()

    async def _run():
        try:
            result = await _run_in_pool(
                clean_bibtex_file,
                _user_path(req.input_bib_file),
                _user_path(req.output_bib_file) if req.output_bib_file else "",
                service=req.service,
                command=req.command,
                modify_input=req.modify_input,
                backup=req.backup,
                indent_mode=req.indent_mode,
                space_count=req.space_count,
                align_values=req.align_values,
                align_column=req.align_column,
                wrap_values=req.wrap_values,
                wrap_column=req.wrap_column,
                blank_lines=req.blank_lines,
                curly=req.curly,
                enclosing_braces=req.enclosing_braces,
                enclosing_braces_fields=req.enclosing_braces_fields,
                remove_braces=req.remove_braces,
                remove_braces_fields=req.remove_braces_fields,
                strip_enclosing_braces=req.strip_enclosing_braces,
                numeric=req.numeric,
                months=req.months,
                drop_all_caps=req.drop_all_caps,
                escape=req.escape,
                encode_urls=req.encode_urls,
                remove_empty_fields=req.remove_empty_fields,
                remove_duplicate_fields=req.remove_duplicate_fields,
                max_authors=req.max_authors,
                max_authors_count=req.max_authors_count,
                sort_entries=req.sort_entries,
                sort_order=req.sort_order,
                sort_fields=req.sort_fields,
                sort_field_order=req.sort_field_order,
                check_duplicates=req.check_duplicates,
                duplicate_keys=req.duplicate_keys,
                duplicate_dois=req.duplicate_dois,
                duplicate_citations=req.duplicate_citations,
                duplicate_abstracts=req.duplicate_abstracts,
                merge_duplicates=req.merge_duplicates,
                merge_strategy=req.merge_strategy,
                omit_fields=req.omit_fields,
                omit_field_list=req.omit_field_list,
                strip_comments=req.strip_comments,
                tidy_comments=req.tidy_comments,
                lowercase=req.lowercase,
                generate_keys=req.generate_keys,
                generate_key_pattern=req.generate_key_pattern,
                trailing_commas=req.trailing_commas,
                extra_options=req.extra_options,
            )
            _finish_job(jid, result)
        except Exception as exc:
            _fail_job(jid, exc)

    asyncio.create_task(_run())
    return JSONResponse({"status": "running", "job_id": jid})


# ── Copy Style Files ──────────────────────────────────────────────────────────

class CopyStylesRequest(BaseModel):
    latex_file: str
    output_folder: str
    miktex_path: str = ""


@app.post("/api/copy-styles")
async def api_copy_styles(req: CopyStylesRequest):
    try:
        result = await _run_in_pool(
            find_and_copy_latex_style_files,
            _user_path(req.latex_file), _user_path(req.output_folder), _user_path(req.miktex_path) if req.miktex_path else None,
        )
        return _ok(result)
    except Exception as exc:
        return _err(str(exc))


# ── Step 9 — Submission Documents ────────────────────────────────────────────

class TexCountRequest(BaseModel):
    latex_file: str
    latex_text: str = ""
    output_folder: str = ""
    output_prefix: str = ""
    service: str = "online"
    texcount_command: str = "texcount"
    include_subfiles: bool = True
    summary: bool = True
    html_report: bool = True


@app.post("/api/texcount")
async def api_texcount(req: TexCountRequest):
    jid = _new_job()

    async def _run():
        try:
            result = await _run_in_pool(
                run_texcount,
                _user_path(req.latex_file),
                req.latex_text,
                _user_path(req.output_folder) if req.output_folder else "",
                req.output_prefix,
                req.service,
                _user_path(req.texcount_command) if req.texcount_command else "texcount",
                req.include_subfiles,
                req.summary,
                req.html_report,
            )
            _finish_job(jid, result)
        except Exception as exc:
            _fail_job(jid, exc)

    asyncio.create_task(_run())
    return JSONResponse({"status": "running", "job_id": jid})


class SubmissionDocsRequest(BaseModel):
    config: dict
    output_folder: str = "submission_word_documents"


@app.post("/api/submission-docs")
async def api_submission_docs(req: SubmissionDocsRequest):
    try:
        written = await _run_in_pool(
            generate_submission_documents, req.config, _user_path(req.output_folder)
        )
        return _ok({"files": [str(p) for p in written]})
    except Exception as exc:
        return _err(str(exc))
