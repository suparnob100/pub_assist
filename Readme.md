# Pub Assist: LaTeX Manuscript Preparation for Journal Submission

Pub Assist is a notebook-based workflow for preparing LaTeX manuscripts for journal submission, revision, and response-to-review. It helps organize manuscript files, clean and reassemble LaTeX, manage figures, generate reviewer-response templates, build DOI-based BibTeX files, and create visual LaTeX diff PDFs.

## Features

- **Modularize LaTeX files**: Split a large manuscript into section files.
- **Version-control friendly formatting**: Put each sentence on a separate line.
- **Project generation**: Create a structured LaTeX project with sections, appendices, figures, and references.
- **Document reassembly**: Merge modular files back into a single manuscript.
- **Cleanup and beautification**: Remove redundant LaTeX and apply formatting.
- **Float review and figure organization**: Inspect figures/tables and collect used figures into one folder.
- **Reviewer-response template**: Generate a structured LaTeX response-to-reviewers file.
- **DOI to BibTeX**: Fetch BibTeX entries from a list of DOIs.
- **LaTeX diff report**: Generate `diff.pdf` from old and new manuscript projects using `git-latexdiff-web`.

## Notebooks

1. `Modularize_Latex_file_in_Latex_project.ipynb`
   - Splits a monolithic LaTeX manuscript into section-based files.

2. `New_line_each_sentence_each_section_in_Sections_folder.ipynb`
   - Rewrites section files so each sentence starts on a new line.
   - This makes Git diffs and revision tracking easier to read.

3. `Step_1_generate_latex_project.ipynb`
   - Creates a starter LaTeX project structure.

4. `Step_2_reassemble_document_from_project.ipynb`
   - Reassembles modular section files into one manuscript file.

5. `Step_3_clean_latex_files.ipynb`
   - Cleans redundant comments, whitespace, and LaTeX fragments.

6. `Step_4_review_floats.ipynb`
   - Reviews figure, table, equation, and other float-related LaTeX.

7. `Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb`
   - Copies all figures used by the manuscript into a separate figure folder.

8. `Step_6_beautification.ipynb`
   - Applies final LaTeX formatting using `python_files/beautify.py`.

9. `Step_7_generate_reviewer_response_template.ipynb`
   - Generates `response_to_reviewers_template.tex`.

10. `Step_8_generate_latexdiff_report.ipynb`
    - Builds a visual revision diff between old and new LaTeX projects.
    - Uses `am009/git-latexdiff-web` through Docker.
    - Default style shows blue added text and red struck-through deleted text.

11. `Generate_BibTeX_from_DOIs.ipynb`
    - Fetches BibTeX entries from DOI strings or DOI URLs.
    - Writes one BibTeX field per line for readability.

12. `copy_style_files_to_folder.ipynb`
    - Copies journal class/style files into a manuscript project.

## Quick Start

1. Clone or download this repository.
2. Install Python 3.x and Jupyter.
3. Open the notebook you need and edit the user-input cell near the top.
4. Run the notebook cells in order.
5. Install and start Docker Desktop before running `Step_8_generate_latexdiff_report.ipynb`.

## Generating a LaTeX Diff PDF

Use `Step_8_generate_latexdiff_report.ipynb`.

The notebook supports either:

- Expanded LaTeX project folders.
- Direct `.zip` files.
- Folders containing one usable `.zip` file, such as:

```text
old/old.zip
new/new.zip
```

For the current repo layout, the notebook is configured as:

```python
old_project = r"old"
new_project = r"new"
main_tex = "manuscript.tex"
bib = "bibtex"
run_worker = True
```

The notebook automatically resolves `old` to `old/old.zip` and `new` to `new/new.zip` if those zip files contain `manuscript.tex`.

### Bibliography Modes

Use:

```python
bib = "bibtex"
```

for ordinary `.bib` workflows using BibTeX or natbib.

Use:

```python
bib = "biber"
```

for biber workflows.

Use:

```python
bib = None
```

when the old and new projects already include generated `.bbl` files, or when citations are not needed in the diff PDF. For a main file named `main.tex`, the matching generated bibliography file is usually `main.bbl`.

### Diff Style

By default:

- Added text is blue with underline-wave markup.
- Deleted text is red with strikeout markup.

This is controlled by `style = None`, which uses Pub Assist's default style from `python_files/latexdiff_web.py`.

### Outputs

Each notebook run creates a fresh timestamped workspace:

```text
latexdiff_runs/notebook_runs/YYYYMMDD_HHMMSS/
```

Important outputs:

```text
latexdiff_runs/notebook_runs/YYYYMMDD_HHMMSS/diff.pdf
latexdiff_runs/notebook_runs/YYYYMMDD_HHMMSS/git-latexdiff/new/manuscript.tex
```

`latexdiff_runs/` is generated output and is ignored by Git.

### Troubleshooting

- If Docker fails, make sure Docker Desktop is running.
- If the notebook says `manuscript.tex` is missing, check that `main_tex` matches the path inside both zip files.
- If a folder contains multiple zip files that each contain `main_tex`, point `old_project` or `new_project` directly to the intended zip.
- Set `show_worker_log = True` in the notebook to print the full LaTeX build log.

## Generating BibTeX from DOIs

Use `Generate_BibTeX_from_DOIs.ipynb`.

Edit:

```python
doi_list = [
    "10.1038/nphys1170",
    "https://doi.org/10.1145/3375630",
]

output_bib_file = "references_from_dois.bib"
```

Then run the notebook. It first tries DOI content negotiation through `doi.org`, then falls back to Crossref. Generated entries are formatted with one BibTeX field per line.

## Project Structure

```text
pub_assist/
|-- .gitignore
|-- Readme.md
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
|-- Generate_BibTeX_from_DOIs.ipynb
|-- copy_style_files_to_folder.ipynb
|-- Resources/
|   |-- endfloat.md
|   `-- symbols.md
`-- python_files/
    |-- beautify.py
    `-- latexdiff_web.py
```
