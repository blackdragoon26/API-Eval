"""
Build the upload-ready FortyGuard evaluation PDF from the Markdown report.

The renderer is intentionally small: it handles the Markdown used in the
report, keeps tables readable, and avoids pulling in a heavier doc toolchain.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "FortyGuard_Evaluation_Report.md"
OUTPUT = ROOT / "output" / "pdf" / "FortyGuard_Evaluation_Report.pdf"


def inline_md(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            rendered.append(f'<font name="Courier">{escape(part[1:-1])}</font>')
            continue
        escaped = escape(part)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        rendered.append(escaped)
    return "".join(rendered)


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append([Paragraph(inline_md(cell), styles["table_cell"]) for cell in cells])

    col_count = max(len(row) for row in rows)
    for row in rows:
        while len(row) < col_count:
            row.append(Paragraph("", styles["table_cell"]))

    table = Table(rows, colWidths=[width / col_count] * col_count, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102A43")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CED6E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_story(markdown: str, doc_width: float) -> list:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleCustom",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#102A43"),
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.2,
            textColor=colors.HexColor("#1F2933"),
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=11.8,
            leftIndent=12,
            bulletIndent=3,
            textColor=colors.HexColor("#1F2933"),
        ),
        "code": ParagraphStyle(
            "CodeCustom",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.6,
            leading=9.5,
            leftIndent=6,
            rightIndent=6,
            backColor=colors.HexColor("#F4F6F8"),
            borderColor=colors.HexColor("#D9E2EC"),
            borderWidth=0.4,
            borderPadding=5,
            spaceBefore=3,
            spaceAfter=6,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=8.8,
            textColor=colors.HexColor("#1F2933"),
        ),
    }

    story: list = []
    lines = markdown.splitlines()
    index = 0
    in_code = False
    code_lines: list[str] = []

    while index < len(lines):
        line = lines[index].rstrip()

        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not line.strip():
            story.append(Spacer(1, 2.5))
            index += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(parse_table(table_lines, styles, doc_width))
            story.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline_md(line[2:].strip()), styles["title"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_md(line[3:].strip()), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_md(line[4:].strip()), styles["h3"]))
        elif line.startswith("- "):
            item = ListItem(Paragraph(inline_md(line[2:].strip()), styles["bullet"]))
            story.append(ListFlowable([item], bulletType="bullet", start="-", leftIndent=10))
        elif re.match(r"^\d+\. ", line):
            number, text = line.split(". ", 1)
            item = ListItem(Paragraph(inline_md(text), styles["bullet"]))
            story.append(ListFlowable([item], bulletType="1", start=number, leftIndent=10))
        else:
            story.append(Paragraph(inline_md(line), styles["body"]))

        index += 1

    return story


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(18 * mm, 10 * mm, "FortyGuard API Evaluation - Sankalp Jha")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    markdown = SOURCE.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title="FortyGuard API Evaluation - Engineering Notes",
        author="Sankalp Jha",
    )
    story = build_story(markdown, doc.width)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
