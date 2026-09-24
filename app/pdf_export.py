"""Renders a generated question set into an official-looking .pdf paper.

Built with reportlab directly (no MS Word / docx2pdf dependency), so it
works the same on any machine the packaged .exe runs on.
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

NAVY = colors.HexColor("#1f3a5f")

PAGE_MARGIN = 2 * cm
USABLE_WIDTH = A4[0] - 2 * PAGE_MARGIN
MARK_COL_WIDTH = 2.2 * cm
QUESTION_COL_WIDTH = USABLE_WIDTH - MARK_COL_WIDTH

SECTION_TITLES = {
    "descriptive": "Descriptive Questions",
    "fill_blank": "Fill in the Blanks",
    "mcq": "Multiple Choice Questions",
}
OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"]

_styles = getSampleStyleSheet()
STYLE_TITLE = ParagraphStyle("PaperTitle", parent=_styles["Title"], fontSize=15, textColor=NAVY, spaceAfter=2, alignment=TA_CENTER)
STYLE_SUBTITLE = ParagraphStyle("PaperSubtitle", parent=_styles["Normal"], fontSize=11, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
STYLE_INFO = ParagraphStyle("Info", parent=_styles["Normal"], fontSize=10.5)
STYLE_SECTION = ParagraphStyle("SectionHeading", parent=_styles["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=10, spaceAfter=2)
STYLE_NOTE = ParagraphStyle("Note", parent=_styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#5a6472"), spaceAfter=6)
STYLE_QUESTION = ParagraphStyle("Question", parent=_styles["Normal"], fontSize=10.5, spaceBefore=6, spaceAfter=2, leading=14)
STYLE_QUESTION_NO_SPACE = ParagraphStyle("QuestionNoSpace", parent=STYLE_QUESTION, spaceBefore=0, spaceAfter=0)
STYLE_MARK_BOX = ParagraphStyle("MarkBox", parent=_styles["Normal"], fontSize=10.5, alignment=TA_RIGHT, leading=14)
STYLE_OPTIONS = ParagraphStyle("Options", parent=_styles["Normal"], fontSize=10.5, leftIndent=18, spaceAfter=4, leading=14)
STYLE_KEY_HEADING = ParagraphStyle("KeyHeading", parent=_styles["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=10, spaceAfter=4)
STYLE_KEY_LINE = ParagraphStyle("KeyLine", parent=_styles["Normal"], fontSize=10, spaceAfter=3)


def _header_flowables(meta, course_name, fmt, date_str, set_label):
    total_marks = sum(
        (sec["display_count"] - sec.get("choice_leave", 0)) * sec["marks_each"]
        for sec in fmt["sections"]
    )
    story = [
        Paragraph(meta.get("institute", "Diesel Traction Training Centre, Kazipet (DTTC/KZJ)"), STYLE_TITLE),
        Paragraph(meta.get("zone", "South Central Railway"), STYLE_SUBTITLE),
        Paragraph(f"Question Paper &mdash; {fmt['name']}", STYLE_SUBTITLE),
        Spacer(1, 10),
    ]
    info_table = Table(
        [
            [Paragraph(f"Course: {course_name}", STYLE_INFO), Paragraph(f"Set: {set_label}", STYLE_INFO)],
            [Paragraph(f"Date: {date_str}", STYLE_INFO), Paragraph(f"Maximum Marks: {total_marks:g}", STYLE_INFO)],
        ],
        colWidths=[9 * cm, 8 * cm],
    )
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#d7dce3"), thickness=1))
    story.append(Spacer(1, 8))
    return story


def _section_flowables(sec, questions, section_no):
    title = SECTION_TITLES[sec["type"]]
    story = [Paragraph(f"Section {section_no}: {title} ({sec['marks_each']:g} Mark(s) each)", STYLE_SECTION)]

    choice_leave = sec.get("choice_leave", 0)
    if choice_leave:
        answer_n = sec["display_count"] - choice_leave
        story.append(Paragraph(f"(Answer any {answer_n} out of {sec['display_count']} questions)", STYLE_NOTE))

    for i, q in enumerate(questions, start=1):
        if sec["type"] == "mcq":
            q_para = Paragraph(f"{i}. {_escape(q['text'])}", STYLE_QUESTION_NO_SPACE)
            mark_para = Paragraph("[&nbsp;&nbsp;&nbsp;&nbsp;]", STYLE_MARK_BOX)
            row = Table(
                [[q_para, mark_para]],
                colWidths=[QUESTION_COL_WIDTH, MARK_COL_WIDTH],
            )
            row.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(row)
            opts = q.get("_shuffled_options", q["options"])
            opt_text = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(
                f"({OPTION_LETTERS[i]}) {_escape(opt)}" for i, opt in enumerate(opts)
            )
            story.append(Paragraph(opt_text, STYLE_OPTIONS))
        else:
            story.append(Paragraph(f"{i}. {_escape(q['text'])}", STYLE_QUESTION))
            if sec["type"] == "descriptive":
                story.append(Spacer(1, 10))
    story.append(Spacer(1, 4))
    return story


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_paper(fmt, meta, course_name, date_str, set_label, set_data, output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    story = _header_flowables(meta, course_name, fmt, date_str, set_label)
    for idx, sec in enumerate(fmt["sections"], start=1):
        story.extend(_section_flowables(sec, set_data[sec["type"]], idx))
    doc.build(story)
    return output_path


def build_answer_key(fmt, meta, course_name, date_str, set_label, set_data, output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    story = [
        Paragraph(
            f"ANSWER KEY &mdash; {_escape(course_name)} &mdash; {_escape(fmt['name'])} &mdash; Set {set_label} &mdash; {date_str}",
            STYLE_TITLE,
        ),
        Spacer(1, 10),
    ]
    for sec in fmt["sections"]:
        story.append(Paragraph(SECTION_TITLES[sec["type"]], STYLE_KEY_HEADING))
        for i, q in enumerate(set_data[sec["type"]], start=1):
            if sec["type"] == "mcq":
                text = f"{i}. {q['id']} &mdash; Correct: {_escape(q['correct_option'])}"
            elif sec["type"] == "fill_blank":
                text = f"{i}. {q['id']} &mdash; Answer: {_escape(q['answer'])}"
            else:
                text = f"{i}. {q['id']} &mdash; (Topic: {_escape(q['topic'])}, Level: {q['level']}) &mdash; see subject notes"
            story.append(Paragraph(text, STYLE_KEY_LINE))
    doc.build(story)
    return output_path
