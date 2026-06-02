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
from clean_latex import clean_latex
from collect_figures import collect_figures
from copy_styles import find_and_copy_latex_style_files
from doi2bib import generate_bibtex_entries, write_bibtex_file
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
    output_bib_file: str = "references_from_dois.bib"
    append: bool = False
    contact_email: str = ""
    timeout: int = 30
    pause_seconds: float = 0.2


@app.post("/api/doi2bib")
async def api_doi2bib(req: Doi2BibRequest):
    jid = _new_job()

    async def _run():
        try:
            entries, failures = await _run_in_pool(
                generate_bibtex_entries, req.dois, req.timeout, req.contact_email, req.pause_seconds
            )
            out_file = _user_path(req.output_bib_file.strip() or "references_from_dois.bib")
            output_path = await _run_in_pool(write_bibtex_file, entries, out_file, req.append)
            _finish_job(jid, {
                "output_file": output_path,
                "entries_count": len(entries),
                "failures": failures,
            })
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
