# Pub Assist

A workflow tool for preparing LaTeX manuscripts for journal submission, revision, and reviewer response. Pub Assist provides a local web app for browser-based access and a set of Jupyter notebooks for cell-by-cell control.

---

## Local Web App

### Installation

The app requires Python 3.10+. Installer scripts handle virtual environment setup and dependency installation automatically.

**Windows (PowerShell):**
```powershell
.\install_app.ps1
```
If PowerShell blocks scripts:
```powershell
powershell -ExecutionPolicy Bypass -File .\install_app.ps1
```

**Windows (Command Prompt):**
```bat
install_app.bat
```
If Python is missing and `winget` is available, the installer installs Python 3.12 automatically. Otherwise it opens the official Python download page.

**macOS / Linux:**
```bash
sh install_app.sh
```
Uses an existing Python 3.10+ if found; otherwise tries common package managers (Homebrew, apt, dnf, yum, pacman, zypper, apk).

During installation, you will be asked whether to install Node.js LTS. Choose `y` to enable the BibTeX Cleaner website-bundle route and npm/npx support, or press Enter to skip.

### Starting the App

**Windows (PowerShell):**
```powershell
.\start_app.ps1
```

**Windows (Command Prompt):**
```bat
start_app.bat
```

**macOS / Linux:**
```bash
sh start_app.sh
```

**Manual start (after installation):**
```bash
# Windows
.venv\Scripts\python.exe -m uvicorn app:app --reload --host 127.0.0.1 --port 7654

# macOS / Linux
.venv/bin/python -m uvicorn app:app --reload --host 127.0.0.1 --port 7654
```

Then open [http://127.0.0.1:7654](http://127.0.0.1:7654) in your browser.

### App Layout

```text
app.py
static/
install_app.bat
install_app.ps1
install_app.sh
start_app.bat
start_app.ps1
start_app.sh
requirements_app.txt
```

---

## Features

### Project Builder and Modularization

The app guides you through the full manuscript preparation pipeline: initialize a structured LaTeX project, split a large manuscript into per-section files, format each sentence on its own line for clean Git diffs, reassemble section files into a single document, and run a final beautification pass.

In Step 1, choose a destination folder. Pub Assist creates a clean `manuscript/` folder and `manuscript.zip` inside that destination; existing files already in the destination are not included in the ZIP. After Step 1 generates the archive, the app shows an Overleaf handoff panel. Use **Open ZIP Folder** to locate the archive, then **Open Overleaf** and choose **New Project > Upload Project**. Authentication stays in your own browser session.

### Figure and Float Management

Review all figures, tables, and other floats in your manuscript, then collect every figure actually used into a single folder for submission.

### Reviewer Response Template

Generates a ready-to-edit `response_to_reviewers_template.tex` structured for point-by-point replies.

### LaTeX Diff PDF

Produces a visual diff between two manuscript versions — additions in blue underline, deletions in red strikethrough. Three engines are supported:

- **Online** — sends only the old and new `.tex` files to [3142.nl/latex-diff/](https://3142.nl/latex-diff/), receives a diff `.tex`, and compiles locally.
- **Local** — uses your installed MiKTeX, TeX Live, or MacTeX `latexdiff` and `pdflatex`.
- **Docker** — runs `am009/latexdiff-web-worker` from Docker Hub. Pub Assist prepares `old.zip`, `new.zip`, and `config.json` in a workspace folder, then runs:
  ```bash
  docker run --rm -v <workspace-folder>:/work am009/latexdiff-web-worker
  ```
  To pre-download the image: `docker pull am009/latexdiff-web-worker`

**Bibliography modes** (for local and Docker engines):

- `bib = None` — default; use when `.bib` files are absent or when using pre-generated `.bbl` files.
- `bib = "bibtex"` — BibTeX/natbib workflows with `.bib` files present in both projects.
- `bib = "biber"` — Biber workflows with `.bib` files present in both projects.

**Troubleshooting diffs:**

- Docker failures: confirm Docker Desktop (Windows/macOS) or the Docker daemon (Linux) is running.
- Perl errors on MiKTeX: install Perl (e.g. Strawberry Perl on Windows) and restart your terminal.
- Missing `manuscript.tex`: verify `main_tex` matches the filename inside the zip.
- Huge or corrupt `old.zip`/`new.zip`: make sure the selected old/new inputs are the actual manuscript project folders, not a broad parent folder, and keep the workspace outside both selected project folders. Pub Assist now refuses workspaces nested inside old/new and stops archive creation when the input is unexpectedly large.
- `PermissionError` on Windows when deleting `latexdiff_runs/current`: Docker, OneDrive, Explorer, or antivirus may be holding the previous `.git` folder. Pub Assist will try to move the old workspace aside automatically; if it fails, close anything using that folder or set a fresh path such as `latexdiff_runs/current_2`.
- To print build logs, enable `show_build_log = True`.

### DOI to BibTeX

The **DOI → BibTeX** card accepts DOIs, `https://doi.org/...` URLs, journal article URLs, and browser-saved HTML files. It tries DOI content negotiation first, then Crossref, and formats entries in a readable style. The generated entry is appended to your selected `.bib` file and previewed in the browser.

For ScienceDirect URLs containing `/pii/...`, Pub Assist resolves the PII through Crossref and Elsevier metadata before fetching the page, avoiding most HTTP 403 blocks. If a publisher still returns 403, save the article page from your browser (`Ctrl+S` or a save-page extension) and select the local `.html` file instead.

### BibTeX Cleaner

Powered by [`bibtex-tidy`](https://github.com/FlamingTempura/bibtex-tidy), the cleaner offers two routes:

- **Website bundle** — downloads the BibTeX Tidy JS bundle and runs it via Node.js. No npm package needed, but Node.js is required.
- **Local npm/npx** — runs the npm package directly using `npx --yes bibtex-tidy@latest`. For a global install instead: `npm install -g bibtex-tidy`, then change the command field in the app to `bibtex-tidy`.

The default preset mirrors the online BibTeX Tidy UI:
```
--curly --numeric --tab --align=13 --duplicates=key --no-escape --sort-fields --no-remove-dupe-fields
```

The app exposes all major option groups: indentation, whitespace, value formatting, sorting, duplicate detection and merging, and cleanup options.

### TexCount

Select a `.tex` file or paste content directly into the TexCount box. Pub Assist sends it to the [TeXcount web service](https://app.uio.no/ifi/texcount/online.php) and displays the compact count summary in the results panel, optionally saving a `*_texcount.html` report.

Note: the online service analyses only the submitted content and cannot follow `\input` or `\include` subfiles. For subfile-aware counting, switch to **Local texcount command**, which runs `texcount` with `-utf8`, `-inc`, and `-sum`. MiKTeX/TeX Live/MacTeX include TexCount, but Windows/MiKTeX users may also need Perl.

If the online service fails with `CERTIFICATE_VERIFY_FAILED`, re-run the installer so the app environment gets `certifi`, then restart. On networks with institutional SSL inspection, the local route is more reliable.

### Submission Word Documents

Auto-generates `.docx` files required for journal submission: cover letters (original and revised), highlights, declarations, and title pages. When `double_blind` is set, both blinded and author versions are written.

### Style File Copy

Copies `.sty` files from your TeX distribution into the project folder. On Linux/macOS, leave the TeX path blank if `kpsewhich` is available; Pub Assist will locate each package automatically. A manual path can be provided if needed.

---

## Notebooks

The notebooks in `notebooks/` cover the same workflow as the browser app. They are useful when a long step benefits from cell-by-cell inspection, when you want to tweak a workflow before running it on a manuscript, or when the app feels slow for a particular task.

| Notebook | Purpose |
|---|---|
| `Modularize_Latex_file_in_Latex_project.ipynb` | Split a single `.tex` file into per-section files |
| `New_line_each_sentence_each_section_in_Sections_folder.ipynb` | One sentence per line for cleaner diffs |
| `Step_1_generate_latex_project.ipynb` | Initialize a structured LaTeX project |
| `Step_2_reassemble_document_from_project.ipynb` | Merge section files into one document |
| `Step_3_clean_latex_files.ipynb` | Remove comments and tidy whitespace |
| `Step_4_review_floats.ipynb` | List and review figures, tables, and floats |
| `Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb` | Collect used figures into one directory |
| `Step_6_beautification.ipynb` | Final formatting pass |
| `Step_7_generate_reviewer_response_template.ipynb` | Generate `response_to_reviewers_template.tex` |
| `Step_8_generate_latexdiff_report.ipynb` | Visual diff between two manuscript versions |
| `Step_9_generate_submission_word_documents.ipynb` | Export cover letters, highlights, and declarations as `.docx` |
| `Generate_BibTeX_from_DOIs.ipynb` | Build a `.bib` file from a list of DOIs |
| `copy_style_files_to_folder.ipynb` | Copy journal class/style files into a project |

### Quick Start

1. Install Python 3.x and Jupyter.
2. Open a notebook from `notebooks/` and fill in the user-input cell near the top.
3. Run cells in order.

For `Step_8` (LaTeX diff), install a TeX distribution with `pdflatex` — MiKTeX on Windows, TeX Live on Linux, MacTeX or TeX Live on macOS. Ensure `latexdiff` and `bibtex`/`biber` are available. If MiKTeX reports a missing Perl script engine, install Strawberry Perl and restart your terminal. Docker Desktop (Windows/macOS) or Docker Engine (Linux) is required for the Docker diff engine.

For `Step_9` (Word documents), install `python-docx`.

---

## Project Layout

```text
pub_assist/
├── app.py
├── requirements_app.txt
├── install_app.bat / .ps1 / .sh
├── start_app.bat / .ps1 / .sh
├── notebooks/
│   ├── Modularize_Latex_file_in_Latex_project.ipynb
│   ├── New_line_each_sentence_each_section_in_Sections_folder.ipynb
│   ├── Step_1_generate_latex_project.ipynb
│   ├── Step_2_reassemble_document_from_project.ipynb
│   ├── Step_3_clean_latex_files.ipynb
│   ├── Step_4_review_floats.ipynb
│   ├── Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb
│   ├── Step_6_beautification.ipynb
│   ├── Step_7_generate_reviewer_response_template.ipynb
│   ├── Step_8_generate_latexdiff_report.ipynb
│   ├── Step_9_generate_submission_word_documents.ipynb
│   ├── Generate_BibTeX_from_DOIs.ipynb
│   └── copy_style_files_to_folder.ipynb
├── Resources/
│   ├── endfloat.md
│   └── symbols.md
├── static/
│   ├── app.js
│   ├── index.html
│   └── style.css
└── python_files/
    ├── beautify.py
    ├── latexdiff_web.py
    └── submission_docs.py
```
