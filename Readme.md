# Pub Assist: Prepare LaTeX Manuscripts for Journal Submission

**Pub Assist** offers a notebook-driven workflow to prepare LaTeX manuscripts for submission, revision, and reviewer response. It helps you organize files, modularize and reassemble LaTeX documents, manage figures, generate reviewer response templates, build BibTeX files from DOIs, and create visual diff PDFs of your manuscript revisions.

Pub Assist also comes with a local web app that enables the complete workflow through your browser.

## Features

- **Modularize LaTeX:** Split large manuscripts into separate section files.
- **Version control optimized:** Format so each sentence is on its own line for improved Git diffs.
- **Project builder:** Assemble a well-structured LaTeX project with sections, figures, appendices, and references.
- **Reassembly:** Combine modular files back to a single manuscript.
- **Cleanup:** Remove redundant code and beautify your LaTeX.
- **Figure/floats organization:** Review and gather all figures used in one folder.
- **Reviewer response template:** Create a structured response file in LaTeX.
- **DOI to BibTeX:** Retrieve BibTeX entries automatically from DOIs.
- **LaTeX diff PDF:** Visually compare manuscript versions using MiKTeX/latexdiff locally, Docker, or via an online service.
- **Submission Word Docs:** Auto-generate `.docx` files required for journal submission (cover letter, highlights, declarations, etc.) from project inputs.

## Workflow Notebooks

The following notebooks guide you through the preparation workflow:

1. **`Modularize_Latex_file_in_Latex_project.ipynb`:**  
   Splits a single LaTeX file into section-based files.
   
2. **`New_line_each_sentence_each_section_in_Sections_folder.ipynb`:**  
   Ensures each sentence starts on a new line for improved diffing and collaboration.

3. **`Step_1_generate_latex_project.ipynb`:**  
   Initializes a new, structured LaTeX project.
   
4. **`Step_2_reassemble_document_from_project.ipynb`:**  
   Merges section files into a single document.
   
5. **`Step_3_clean_latex_files.ipynb`:**  
   Cleans up comments and whitespace.
   
6. **`Step_4_review_floats.ipynb`:**  
   Lists and reviews figures, tables, and other floats.
   
7. **`Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb`:**  
   Collects used figures into one directory.
   
8. **`Step_6_beautification.ipynb`:**  
   Final formatting and beautification.

9. **`Step_7_generate_reviewer_response_template.ipynb`:**  
   Creates a ready-to-edit `response_to_reviewers_template.tex`.

10. **`Step_8_generate_latexdiff_report.ipynb`:**  
    Builds a diff (visual changes) between two manuscript versions using various engines (local, Docker, or online).

11. **`Step_9_generate_submission_word_documents.ipynb`:**  
    Exports submission materials like cover letters, titles, and declarations as `.docx` files, supporting both single- and double-blind workflows.

12. **`Generate_BibTeX_from_DOIs.ipynb`:**  
    Creates a BibTeX file from provided DOIs.

13. **`copy_style_files_to_folder.ipynb`:**  
    Copies journal class/style files into your project.

## Quick Start

1. Clone or download the repository.
2. Install Python 3.x and Jupyter.
3. Open the desired notebook and fill out the user input cell near the top.
4. Run each cell in order.
5. For `Step_8_generate_latexdiff_report.ipynb`, install MiKTeX with `pdflatex`. For local diffing, ensure `latexdiff` and `bibtex`/`biber` utilities are available.
6. If MiKTeX reports a missing script engine `'perl'`, install Perl (e.g., Strawberry Perl on Windows).
7. Optionally, install Docker Desktop for Docker-based diffing.
8. For Word document generation, make sure `python-docx` is installed.

## Local Web App

Pub Assist provides a FastAPI web app for browser-based access to the workflow.

App layout:
```text
app.py
static/
start_app.bat
requirements_app.txt
```

### Installation and Launch

Install dependencies:
```bash
pip install -r requirements_app.txt
```

On Windows:
```bat
start_app.bat
```
Or start manually:
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 7654
```

Browse to [http://127.0.0.1:7654](http://127.0.0.1:7654) for the app UI, which covers the entire workflow: project generation, modularization, formatting, float/fugure review, beautification, response template, LaTeX diff generation, DOI-to-BibTeX, etc.

**LaTeX Diff supports:**
```python
latexdiff_engine = "online"   # Uses online form + local pdflatex
latexdiff_engine = "local"    # Uses local MiKTeX/latexdiff
latexdiff_engine = "docker"   # Uses Docker worker
```
*Online mode only sends the main .tex file text to the online service.*

---

## Generate a LaTeX Diff PDF

Running `Step_8_generate_latexdiff_report.ipynb` creates a visual diff of two manuscript versions. Three methods are supported:

- **Online** (`latexdiff_engine = "online"`):  
  Sends only the old and new main `.tex` files to [3142.nl/latex-diff/](https://3142.nl/latex-diff/), receives a diff `.tex` file, and compiles it locally.
- **Local** (`latexdiff_engine = "local"`):  
  Uses your installed MiKTeX/latexdiff.
- **Docker** (`latexdiff_engine = "docker"`):  
  Runs a Dockerized diff worker.

The notebook accepts either full project folders, zip files, or folders containing a single `.zip` file containing `manuscript.tex`:
```python
old_project = r"old"
new_project = r"new"
main_tex = "manuscript.tex"
bib = "bibtex"
latexdiff_engine = "online"
confirm_online_upload = True
run_worker = True
```

### Bibliography Modes

- `bib = "bibtex"` : For BibTeX/natbib workflows
- `bib = "biber"` : For biber workflows
- `bib = None` : When using generated `.bbl` files directly, or bibliography is not needed

### Diff Styles

- Blue underlined for additions, red strikethrough for deletions (default).
- Style is managed in `python_files/latexdiff_web.py`.

### Troubleshooting

- If Docker fails, confirm Docker Desktop is running.
- For a Perl error (`MiKTeX could not find the script engine 'perl'`), install Perl and restart your terminal/session.
- If `manuscript.tex` is missing, verify `main_tex` matches inside zip files.
- To print build logs, enable `show_build_log = True` in the notebook.

---

## Creating BibTeX from DOIs

Launch `Generate_BibTeX_from_DOIs.ipynb`, update:

```python
doi_list = [
    "10.1038/nphys1170",
    "https://doi.org/10.1145/3375630",
]
output_bib_file = "references_from_dois.bib"
```
Run the notebook. It tries DOI content negotiation first, then Crossref, and formats entries in a readable way.

---

## Generating Submission Word Documents

Edit your manuscript metadata in `Step_9_generate_submission_word_documents.ipynb`:

```python
journal_name = "[Journal Name]"
paper_title = "[Full Manuscript Title]"
double_blind = True
clean_output_folder = True
authors = [...]
highlights = [...]
```
Generated `.docx` files go in `submission_word_documents/`. If `double_blind` is set, both blinded and author title files are written. Two cover letters are produced: original and revised, with fields for manuscript ID, revision, major changes, and other declarations.

---

## Project Layout

```text
pub_assist/
|-- .gitignore
|-- Readme.md
|-- app.py
|-- requirements_app.txt
|-- start_app.bat
|-- Modularize_Latex_file_in_Latex_project.ipynb
|-- New_line_each_sentence_each_section_in_Sections_folder.ipynb
|-- Step_1_generate_latex_project.ipynb
|-- Step_2_reassemble_document_from_project.ipynb
|-- Step_3_clean_latex_files.ipynb
|-- Step_4_review_floats.ipynb
|-- Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb
|-- Step_6_beautification.ipynb
|-- Step_7_generate_reviewer_response_template.ipynb
|-- Step_8_generate_latexdiff_report.ipynb
|-- Step_9_generate_submission_word_documents.ipynb
|-- Generate_BibTeX_from_DOIs.ipynb
|-- copy_style_files_to_folder.ipynb
|-- Resources/
|   |-- endfloat.md
|   `-- symbols.md
|-- static/
|   |-- app.js
|   |-- index.html
|   `-- style.css
`-- python_files/
    |-- beautify.py
    |-- latexdiff_web.py
    `-- submission_docs.py
```
