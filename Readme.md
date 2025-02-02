# **Pub Assist: LaTeX Manuscript Preparation for Journal Submission**

## **Overview**
**Pub Assist** is a structured workflow for preparing and formatting LaTeX manuscripts for journal submission. It helps researchers efficiently organize, clean, and enhance their documents while maintaining version control and compliance with journal guidelines.

## **Features**
- **Modularize LaTeX Files**: Splits a large LaTeX file into section-based modular files.
- **Version Control Friendly Formatting**: Ensures each sentence starts on a new line.
- **Structured Project Setup**: Creates a well-organized directory for LaTeX projects.
- **Automated Document Assembly**: Reassembles sections into a complete LaTeX document.
- **Cleanup & Formatting**: Removes redundant elements and enhances readability.
- **Float Management**: Ensures figures and tables are correctly placed and referenced.
- **Figure Organization**: Moves all used figures to a dedicated directory.
- **Final Beautification**: Optimizes formatting for journal compliance.
- **Journal Style Integration**: Copies required style files for submission.

## **Workflow Steps**
The project follows a structured approach to preparing a manuscript:

1. **Modularize LaTeX File (`Modularize_Latex_file_in_Latex_project.ipynb`)**
   - Splits a monolithic LaTeX file into smaller files for sections.
   - Helps in organization and collaborative editing.
   - Facilitates easier tracking of changes and reuse of sections in different papers.

2. **Format Each Sentence on a New Line (`New_line_each_sentence_each_section_in_Sections_folder.ipynb`)**
   - Ensures each sentence starts on a new line for better version control.
   - Improves readability when tracking changes using version control tools like Git.

3. **Generate LaTeX Project (`Step_1_generate_latex_project.ipynb`)**
   - Creates a structured directory for LaTeX files, figures, and references.
   - Prepares a template that aligns with common journal submission formats.

4. **Reassemble Document (`Step_2_reassemble_document_from_project.ipynb`)**
   - Merges modular LaTeX files into a complete document.
   - Ensures correct linking of figures, tables, citations, and sections.
   - Verifies the integrity of cross-references and bibliographies.

5. **Clean LaTeX Files (`Step_3_clean_latex_files.ipynb`)**
   - Removes unnecessary comments, whitespace, and redundant code.
   - Standardizes formatting to ensure consistency throughout the document.
   - Checks for deprecated LaTeX commands and replaces them with updated ones.

6. **Review Figures & Tables (`Step_4_review_floats.ipynb`)**
   - Checks for error in floats such as table, equation, figures, etc.

7. **Organize Figures (`Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb`)**
   - Moves all figures used in the manuscript into a dedicated folder.
   - Prevents missing figure errors during compilation.
   - Ensures compliance with journal submission guidelines for figure file organization.

8. **Beautification (`Step_6_beautification.ipynb`)**
   - Applies formatting enhancements for improved readability and aesthetics.
   - Ensures uniform font styles, spacing, and indentation.
   - Adjusts title and section formatting to align with journal-specific requirements.

9. **Copy Style Files (`copy_style_files_to_folder.ipynb`)**
   - Copies necessary style files into the project directory.
   - Journals often compile articles on their own server and may require specific style files for proper compilation.

## **Installation & Usage**
1. Clone or download the repository.
2. If you have an existing latex project copy and paste that folder it in the repository.
3. Ensure you have Python 3.x installed.
4. Open and execute the Jupyter Notebooks in sequential order (recommended not mandatory).
5. Use `beautify.py` to apply final formatting to the document.


## **Project Structure**
```
pub_assist-main/
│── .gitignore
│── Modularize_Latex_file_in_Latex_project.ipynb
│── New_line_each_sentence_each_section_in_Sections_folder.ipynb
│── Step_1_generate_latex_project.ipynb
│── Step_2_reassemble_document_from_project.ipynb
│── Step_3_clean_latex_files.ipynb
│── Step_4_review_floats.ipynb
│── Step_5_put_all_figures_used_in_a_sep_fig_folder.ipynb
│── Step_6_beautification.ipynb
│── copy_style_files_to_folder.ipynb
│── Resources/
│   └── symbols.md
│── python_files/
│   ├── beautify.py
```

## **Contributing**
- Fork the repository.
- Create a feature branch.
- Submit a pull request.

## **License**
This project is licensed under the MIT License (if applicable).

