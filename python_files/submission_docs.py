from datetime import date
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
except ImportError as exc:
    raise ImportError("Install python-docx first: pip install python-docx") from exc

COLORS = {
    "ink": "1A1A1A",
    "title": "11233A",
    "accent": "2E74B5",
    "muted": "8A8F99",
    "hairline": "D8DCE2",
}

CONTENT_WIDTH_IN = 6.3  # 8.5 - 1.1 - 1.1


def _rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _value(config, key, default=""):
    value = config.get(key, default)
    return default if value is None else value


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _set_run_font(run, size=None, color=None, bold=None, italic=None, spacing=None, font="Calibri"):
    run.font.name = font
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), font)
    rfonts.set(qn("w:hAnsi"), font)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = _rgb(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if spacing is not None:
        element = OxmlElement("w:spacing")
        element.set(qn("w:val"), str(int(spacing * 20)))
        rpr.append(element)


def _fmt(paragraph, before=0, after=6, line_spacing=1.2, alignment=None, left_indent=None):
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.line_spacing = line_spacing
    if alignment is not None:
        paragraph.alignment = alignment
    if left_indent is not None:
        paragraph.paragraph_format.left_indent = Pt(left_indent)


def _hairline(paragraph, color=None, size=6, space=6):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color or COLORS["hairline"])
    pBdr.append(bottom)
    pPr.append(pBdr)


def _new_document(document_label, subtitle, config):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.1)
    section.right_margin = Inches(1.1)
    section.footer_distance = Inches(0.5)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = _rgb(COLORS["ink"])

    # Minimal footer: centered page number.
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fmt(footer, after=0)
    run = footer.add_run()
    _set_run_font(run, size=8.5, color=COLORS["muted"])
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._element.append(begin)
    run._element.append(instr)
    run._element.append(end)

    # Eyebrow: journal name, small caps style.
    eyebrow = doc.add_paragraph()
    _fmt(eyebrow, after=2)
    run = eyebrow.add_run(_value(config, "journal_name", "[Journal Name]").upper())
    _set_run_font(run, size=8.5, color=COLORS["muted"], bold=True, spacing=1.2)

    # Title.
    title = doc.add_paragraph()
    _fmt(title, after=2)
    run = title.add_run(document_label)
    _set_run_font(run, size=22, color=COLORS["title"], bold=True)

    # Subtitle + closing hairline rule.
    sub = doc.add_paragraph()
    _fmt(sub, after=10)
    if subtitle:
        run = sub.add_run(subtitle)
        _set_run_font(run, size=10.5, color=COLORS["muted"], italic=True)
    _hairline(sub, color=COLORS["hairline"], size=6, space=10)

    return doc


def _section(doc, title):
    heading = doc.add_paragraph()
    _fmt(heading, before=16, after=5)
    run = heading.add_run(title.upper())
    _set_run_font(run, size=10, color=COLORS["accent"], bold=True, spacing=0.8)
    return heading


def _body(doc, text, after=8, italic=None, justify=False, color=None):
    paragraph = doc.add_paragraph()
    _fmt(paragraph, after=after, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY if justify else None)
    run = paragraph.add_run(str(text))
    _set_run_font(run, size=11, color=color or COLORS["ink"], italic=italic)
    return paragraph


def _meta(doc, label, value, after=3, indent=0):
    paragraph = doc.add_paragraph()
    _fmt(paragraph, after=after, left_indent=indent or None)
    label_run = paragraph.add_run(f"{label} ")
    _set_run_font(label_run, size=9.5, color=COLORS["muted"], bold=True, spacing=0.4)
    value_run = paragraph.add_run(str(value))
    _set_run_font(value_run, size=10.5, color=COLORS["ink"])
    return paragraph


def _person(doc, name, after=1):
    paragraph = doc.add_paragraph()
    _fmt(paragraph, before=4, after=after)
    run = paragraph.add_run(str(name))
    _set_run_font(run, size=11, color=COLORS["title"], bold=True)
    return paragraph


def _sub(doc, text, after=2, indent=14):
    paragraph = doc.add_paragraph()
    _fmt(paragraph, after=after, left_indent=indent)
    run = paragraph.add_run(str(text))
    _set_run_font(run, size=10, color=COLORS["muted"])
    return paragraph


def _note(doc, label, text):
    paragraph = doc.add_paragraph()
    _fmt(paragraph, after=10)
    label_run = paragraph.add_run(f"{label}. ")
    _set_run_font(label_run, size=9.5, color=COLORS["accent"], bold=True, italic=True)
    text_run = paragraph.add_run(str(text))
    _set_run_font(text_run, size=9.5, color=COLORS["muted"], italic=True)
    return paragraph


def _bullets(doc, items):
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        _fmt(paragraph, after=4)
        run = paragraph.add_run(str(item))
        _set_run_font(run, size=11, color=COLORS["ink"])


def _signature_block(doc, config):
    _body(doc, "Sincerely,", after=4)
    name = doc.add_paragraph()
    _fmt(name, before=6, after=1)
    run = name.add_run(_value(config, "corresponding_author", "[Corresponding Author Name]"))
    _set_run_font(run, size=11, color=COLORS["title"], bold=True)
    _sub(doc, _value(config, "corresponding_email", "[Email]"), after=1, indent=0)
    _sub(doc, _value(config, "corresponding_address", "[Address]"), after=6, indent=0)


def _save(doc, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


# ------------------------------------------------------------------------------
# COVER LETTERS — plain flowing prose, no subsections
# ------------------------------------------------------------------------------

def build_original_cover_letter(config):
    """Cover letter for first submission. No subsections — just flowing prose."""
    doc = _new_document("Cover Letter", "Original submission", config)

    # Date
    _body(doc, date.today().strftime("%B %d, %Y"), after=10, color=COLORS["muted"])

    # Salutation
    _body(doc, f"Dear {_value(config, 'editor_name', '[Editor Name]')},", after=8)

    # Opening: submission statement
    _body(
        doc,
        f"We wish to submit our manuscript, \u201c{_value(config, 'paper_title', '[Full Manuscript Title]')}\u201d, "
        f"for consideration as a {_value(config, 'manuscript_type', '[Research Article / Review Article / Short Communication]')} "
        f"in {_value(config, 'journal_name', '[Journal Name]')}.",
        justify=True,
    )

    # Free prose body: novelty, fit, significance — written by the author
    for paragraph in _as_list(config.get("cover_letter_body")):
        _body(doc, paragraph, justify=True)

    # Confirmations — single prose paragraph
    _body(
        doc,
        _value(
            config,
            "originality_statement",
            "We confirm that this manuscript is original, has not been published previously, "
            "and is not under consideration elsewhere. All authors have read and approved the "
            "submitted version, and all necessary ethical approvals and disclosures are included.",
        ),
        justify=True,
    )

    # Closing
    _body(doc, "We look forward to hearing from you.", after=14)
    _signature_block(doc, config)
    return doc


def build_revised_cover_letter(config):
    """Cover letter for revised resubmission. No subsections — just flowing prose."""
    doc = _new_document("Cover Letter", "Revised manuscript \u2014 resubmission after peer review", config)

    # Muted reference line
    ref_line = (
        f"{_value(config, 'journal_name', '[Journal Name]')}  \u00b7  "
        f"Manuscript ID: {_value(config, 'manuscript_id', '[MS-XXXX]')}"
    )
    _body(doc, ref_line, after=2, color=COLORS["muted"])
    _body(doc, date.today().strftime("%B %d, %Y"), after=10, color=COLORS["muted"])

    # Salutation
    _body(doc, f"Dear {_value(config, 'editor_name', '[Editor Name]')},", after=8)

    # Paragraph 1: resubmission statement
    _body(
        doc,
        f"We are pleased to submit a revised version of our manuscript, "
        f"\u201c{_value(config, 'paper_title', '[Full Manuscript Title]')}\u201d, "
        f"for further consideration in {_value(config, 'journal_name', '[Journal Name]')}.",
        justify=True,
    )

    # Paragraph 2: acknowledgement + pointer to response document
    _body(
        doc,
        _value(
            config,
            "revision_opening",
            "We thank the editor and reviewers for their constructive feedback. "
            "All comments have been carefully addressed, and a detailed point-by-point "
            "response is provided in the accompanying document.",
        ),
        justify=True,
    )

    # Paragraph 3: confirmations
    _body(
        doc,
        _value(
            config,
            "revised_confirmation",
            "We confirm that all authors have approved the revised version and that "
            "all ethical requirements remain satisfied.",
        ),
        justify=True,
    )

    # Closing
    _body(doc, "We look forward to your decision.", after=14)
    _signature_block(doc, config)
    return doc


def build_cover_letter(config):
    return build_original_cover_letter(config)


# ------------------------------------------------------------------------------
# OTHER DOCUMENTS (unchanged from original)
# ------------------------------------------------------------------------------

def build_highlights(config):
    doc = _new_document("Highlights", "Concise claims for the submission system", config)
    _note(doc, "Guidance", _value(config, "highlight_guidance", "[Keep each highlight concise and check the journal character limit.]"))
    for index, item in enumerate(_as_list(config.get("highlights")), start=1):
        if isinstance(item, dict):
            text = item.get("text", "[Highlight]")
            detail = item.get("detail", "")
            line = f"{text} {detail}".strip()
        else:
            line = str(item)
        paragraph = doc.add_paragraph()
        _fmt(paragraph, after=6, left_indent=20)
        paragraph.paragraph_format.first_line_indent = Pt(-20)
        num_run = paragraph.add_run(f"{index}. ")
        _set_run_font(num_run, size=11, color=COLORS["accent"], bold=True)
        text_run = paragraph.add_run(line)
        _set_run_font(text_run, size=11, color=COLORS["ink"])
    return doc


def build_conflict_of_interest(config):
    doc = _new_document("Conflict of Interest Statement", "Competing-interest disclosure", config)
    _section(doc, "Statement")
    _body(doc, _value(config, "conflict_of_interest_statement", "[Insert conflict of interest statement.]"), justify=True)
    _section(doc, "Author Disclosures")
    for author in _as_list(config.get("authors")):
        _person(doc, author.get("name", "[Author Name]"))
        _sub(doc, "Financial: " + author.get("financial_conflict", "[None declared]"))
        _sub(doc, "Personal: " + author.get("personal_conflict", "[None declared]"))
        _sub(doc, "Intellectual property: " + author.get("ip_conflict", "[None declared]"))
        _sub(doc, "Other: " + author.get("other_conflict", "[None declared]"), after=6)
    return doc


def build_author_declaration(config):
    doc = _new_document("Author Declaration", "Authorship, ethics, and submission confirmations", config)
    _note(doc, "Before submission", "Confirm journal-specific wording for ethics, consent, AI/tool use, and competing interests.")
    _section(doc, "Author Contributions")
    for author in _as_list(config.get("authors")):
        _person(doc, author.get("name", "[Author Name]"))
        _sub(doc, author.get("contribution", "[Contribution]"))
        _sub(doc, author.get("affiliation", "[Affiliation]"), after=6)
    _section(doc, "Required Statements")
    _meta(doc, "Originality", _value(config, "originality_confirmation", "[The manuscript is original and not under consideration elsewhere.]"))
    _meta(doc, "Author approval", _value(config, "author_approval_confirmation", "[All authors approved the submission.]"))
    _meta(doc, "Ethics", _value(config, "ethics_statement", "[Ethics statement.]"))
    _meta(doc, "Funding", _value(config, "funding_statement", "[Funding statement.]"))
    _meta(doc, "Data availability", _value(config, "data_availability_statement", "[Data availability statement.]"))
    _meta(doc, "Acknowledgements", _value(config, "acknowledgements", "[Acknowledgements or Not applicable.]"))
    return doc


def build_funding_statement(config):
    doc = _new_document("Funding Statement", "Funding sources and funder-role disclosure", config)
    _section(doc, "Statement")
    _body(doc, _value(config, "funding_statement", "[Insert funding statement.]"), justify=True)
    sources = _as_list(config.get("funding_sources"))
    if sources:
        _section(doc, "Funding Details")
        for source in sources:
            _person(doc, source.get("funder", "[Funder]"))
            _sub(doc, "Grant: " + source.get("grant", "[Grant number]"))
            _sub(doc, "Recipient: " + source.get("recipient", "[Recipient]"))
            _sub(doc, "Funder role: " + source.get("role", "[No role]"), after=6)
    return doc


def build_data_availability_statement(config):
    doc = _new_document("Data Availability Statement", "Repository, access, and restrictions", config)
    _section(doc, "Statement")
    _body(doc, _value(config, "data_availability_statement", "[Insert data availability statement.]"), justify=True)
    _section(doc, "Access Details")
    _meta(doc, "Repository", _value(config, "data_repository", "[Repository name or Not applicable]"))
    _meta(doc, "DOI / accession", _value(config, "data_accession", "[DOI, accession number, or Not applicable]"))
    _meta(doc, "Access conditions", _value(config, "data_access_conditions", "[Open access / reasonable request / restricted]"))
    _meta(doc, "License", _value(config, "data_license", "[License or Not applicable]"))
    _meta(doc, "Contact", _value(config, "data_contact", _value(config, "corresponding_email", "[Contact email]")))
    return doc


def build_title_file(config, include_authors=True, blinded=False):
    doc_type = "Blinded Title Page" if blinded else "Title Page" if include_authors else "Title File"
    subtitle = "Anonymized for double-blind review" if blinded else "Title page material for journal upload"
    doc = _new_document(doc_type, subtitle, config)
    _section(doc, "Title")
    _meta(doc, "Full title", _value(config, "paper_title", "[Full Manuscript Title]"))
    _meta(doc, "Short title", _value(config, "short_title", "[Short Running Title]"))
    _meta(doc, "Keywords", "; ".join(_as_list(config.get("keywords"))), after=6)
    _section(doc, "Abstract")
    _body(doc, _value(config, "abstract_text", "[Paste the manuscript abstract here.]"), justify=True)
    if blinded:
        _section(doc, "Double-Blind Review Note")
        _body(doc, "[Author names, affiliations, acknowledgements, funding identifiers, and self-identifying details intentionally omitted or anonymized.]")
        _bullets(doc, [
            "[Author names and affiliations omitted.]",
            "[Acknowledgements moved to author-containing file or anonymized.]",
            "[Funding details checked against journal double-blind policy.]",
            "[Self-citations written neutrally where required.]",
        ])
    elif include_authors:
        _section(doc, "Authors")
        for index, author in enumerate(_as_list(config.get("authors")), start=1):
            _person(doc, f"{index}. {author.get('name', '[Author Name]')}")
            _sub(doc, author.get("affiliation", "[Affiliation]"))
            _sub(doc, author.get("email", "[Email]") + " \u00b7 ORCID " + author.get("orcid", "[ORCID]"), after=6)
        _section(doc, "Corresponding Author")
        _meta(doc, "Name", _value(config, "corresponding_author", "[Corresponding Author Name]"))
        _meta(doc, "Email", _value(config, "corresponding_email", "[Email]"))
        _meta(doc, "Address", _value(config, "corresponding_address", "[Address]"))
    return doc


def build_reviewer_suggestions(config):
    doc = _new_document("Reviewer Suggestions", "Optional reviewer recommendations and exclusions", config)
    _note(doc, "Check journal policy", "Remove this file if reviewer suggestions are not requested.")
    _section(doc, "Suggested Reviewers")
    reviewers = _as_list(config.get("suggested_reviewers")) or [
        {"name": "[Reviewer Name]", "email": "[Email]", "institution": "[Institution]", "reason": "[Relevant expertise]", "conflict_check": "[No known conflict]"}
    ]
    for reviewer in reviewers:
        _person(doc, f"{reviewer.get('name', '[Reviewer Name]')} \u00b7 {reviewer.get('institution', '[Institution]')}")
        _sub(doc, "Email: " + reviewer.get("email", "[Email]"))
        _sub(doc, "Expertise: " + reviewer.get("reason", "[Relevant expertise]"))
        _sub(doc, "Conflict check: " + reviewer.get("conflict_check", "[No known conflict]"), after=6)
    _section(doc, "Opposed Reviewers")
    opposed = _as_list(config.get("opposed_reviewers")) or [
        {"name": "[Reviewer Name]", "institution": "[Institution]", "reason": "[Reason for exclusion, if any]"}
    ]
    for reviewer in opposed:
        _person(doc, f"{reviewer.get('name', '[Reviewer Name]')} \u00b7 {reviewer.get('institution', '[Institution]')}")
        _sub(doc, "Reason: " + reviewer.get("reason", "[Reason for exclusion, if any]"), after=6)
    return doc


def build_submission_checklist(config):
    doc = _new_document("Submission Checklist", "Internal check before journal upload", config)
    _section(doc, "Document Package")
    _bullets(doc, [
        "[Cover letters: original and revised versions reviewed.]",
        "[Highlights checked against journal count and character limits.]",
        "[Conflict of interest statement reviewed by all authors.]",
        "[Title file checked against double-blind requirements.]",
        "[Funding statement includes grant numbers and funder role.]",
        "[Data availability statement includes repository links and access terms.]",
    ])
    _section(doc, "Policy Checks")
    _bullets(doc, [
        "[Confirm journal-specific Word file naming requirements.]",
        "[Confirm whether author identifiers must be removed for double-blind review.]",
        "[Confirm whether reviewer suggestions or exclusions are allowed.]",
        "[Confirm declaration wording for ethics, consent, AI/tool use, and competing interests.]",
    ])
    return doc


def generate_submission_documents(config, output_folder="submission_word_documents"):
    output_dir = Path(output_folder)
    if bool(config.get("clean_output_folder", True)) and output_dir.exists():
        for old_docx in output_dir.glob("*.docx"):
            old_docx.unlink()

    documents = {
        "original_cover_letter.docx": build_original_cover_letter(config),
        "revised_cover_letter.docx": build_revised_cover_letter(config),
        "highlights.docx": build_highlights(config),
        "conflict_of_interest.docx": build_conflict_of_interest(config),
        # "author_declaration.docx": build_author_declaration(config),
        "funding_statement.docx": build_funding_statement(config),
        "data_availability_statement.docx": build_data_availability_statement(config),
        "reviewer_suggestions.docx": build_reviewer_suggestions(config),
        "submission_checklist.docx": build_submission_checklist(config),
    }

    if bool(config.get("double_blind", True)):
        documents["title_file.docx"] = build_title_file(config, include_authors=True, blinded=False)

    written = []
    for filename, document in documents.items():
        written.append(_save(document, output_dir / filename))
    return written
