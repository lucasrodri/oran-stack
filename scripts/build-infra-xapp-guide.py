#!/usr/bin/env python3
"""Render the infrastructure-team xApp quickstart as a polished PDF."""

from __future__ import annotations

import base64
import html
import re
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/INFRA_XAPP_QUICKSTART.md"
OUTPUT = ROOT / "output/pdf/guia-equipe-infra-desenvolvimento-xapps.pdf"
CONFIG = ROOT / "infra/nephio/webui-compat/unb-configmap.yaml"

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 16 * mm
FRAME_BOTTOM = 23 * mm
CONTENT_W = PAGE_W - (2 * MARGIN_X)

UNB_BLUE = colors.HexColor("#0B3E75")
UNB_GREEN = colors.HexColor("#087C3A")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#5D6975")
SOFT = colors.HexColor("#EDF2F6")
PALE_BLUE = colors.HexColor("#EAF2FA")
PALE_GREEN = colors.HexColor("#E8F4ED")
WHITE = colors.white


def register_fonts() -> None:
    font_dir = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("Arial", str(font_dir / "Arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(font_dir / "Arial Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(font_dir / "Arial Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Courier-New", str(font_dir / "Courier New.ttf")))


def extract_logo() -> bytes:
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"logoUrl:\s*data:image/png;base64,([^\n]+)", text)
    if not match:
        raise RuntimeError(f"official UnB logo not found in {CONFIG}")
    return base64.b64decode(match.group(1).strip())


register_fonts()
styles = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body", parent=styles["BodyText"], fontName="Arial", fontSize=9.3,
    leading=13.1, textColor=INK, spaceAfter=5.5,
)
H1 = ParagraphStyle(
    "H1", parent=BODY, fontName="Arial-Bold", fontSize=18, leading=22,
    textColor=UNB_BLUE, spaceBefore=7, spaceAfter=8, keepWithNext=True,
)
H2 = ParagraphStyle(
    "H2", parent=BODY, fontName="Arial-Bold", fontSize=13.2, leading=17,
    textColor=UNB_BLUE, spaceBefore=9, spaceAfter=5, keepWithNext=True,
)
H3 = ParagraphStyle(
    "H3", parent=BODY, fontName="Arial-Bold", fontSize=10.8, leading=14,
    textColor=UNB_GREEN, spaceBefore=7, spaceAfter=4, keepWithNext=True,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=12, firstLineIndent=-7, bulletIndent=4,
    spaceAfter=3.5,
)
NUMBERED = ParagraphStyle(
    "Numbered", parent=BODY, leftIndent=14, firstLineIndent=-9, spaceAfter=3.5,
)
CODE = ParagraphStyle(
    "Code", parent=BODY, fontName="Courier-New", fontSize=7.3, leading=10.1,
    textColor=INK, backColor=SOFT, borderColor=colors.HexColor("#CCD6E0"),
    borderWidth=0.5, borderPadding=7, spaceBefore=3, spaceAfter=7,
)
TABLE_HEADER = ParagraphStyle(
    "TableHeader", parent=BODY, fontName="Arial-Bold", textColor=WHITE,
    fontSize=8.2, leading=10.5,
)
TABLE_CELL = ParagraphStyle(
    "TableCell", parent=BODY, fontSize=8.0, leading=10.5, spaceAfter=0,
)


def inline_markup(value: str) -> str:
    escaped = html.escape(value.strip())
    return re.sub(
        r"`([^`]+)`",
        r'<font name="Courier-New" color="#0B3E75">\1</font>',
        escaped,
    )


def make_table(rows: list[list[str]]) -> Table:
    width_count = max(len(row) for row in rows)
    if width_count == 2:
        widths = [CONTENT_W * 0.39, CONTENT_W * 0.61]
    else:
        widths = [CONTENT_W / width_count] * width_count
    rendered = []
    for row_index, row in enumerate(rows):
        style = TABLE_HEADER if row_index == 0 else TABLE_CELL
        rendered.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), UNB_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C6D0DA")),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_BLUE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def parse_markdown(text: str) -> list:
    lines = text.splitlines()
    story: list = []
    paragraph: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(paragraph)), BODY))
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(code_lines), CODE, maxLineLength=92))
            index += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[3:]), H2))
            index += 1
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[4:]), H3))
            index += 1
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and re.match(
            r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", lines[index + 1]
        ):
            flush_paragraph()
            table_lines = [line]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = [[cell.strip() for cell in row.strip().strip("|").split("|")]
                    for row in table_lines]
            table_bundle = [make_table(rows), Spacer(1, 6)]
            if story and isinstance(story[-1], Paragraph) and story[-1].style.name == "H3":
                table_bundle.insert(0, story.pop())
            story.append(KeepTogether(table_bundle))
            continue
        bullet = re.match(r"^-\s+(.*)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            story.append(Paragraph("- " + inline_markup(bullet.group(1)), BULLET))
            index += 1
            continue
        if numbered:
            flush_paragraph()
            story.append(Paragraph(
                f"{numbered.group(1)}. " + inline_markup(numbered.group(2)), NUMBERED
            ))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    flush_paragraph()
    return story


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
            title="Guia da equipe de infraestrutura - desenvolvimento de xApps",
            author="Laboratório Open RAN - Universidade de Brasília",
        )
        frame = Frame(
            MARGIN_X, FRAME_BOTTOM, CONTENT_W,
            PAGE_H - MARGIN_TOP - FRAME_BOTTOM - 9 * mm,
            id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPageEnd=self.decorate)])

    def decorate(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(UNB_GREEN)
        canvas.setLineWidth(1.2)
        canvas.line(MARGIN_X, PAGE_H - 11 * mm, PAGE_W - MARGIN_X, PAGE_H - 11 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, 9 * mm, "Open RAN Lab - FT/UnB")
        canvas.drawRightString(PAGE_W - MARGIN_X, 9 * mm, f"Pag. {doc.page}")
        canvas.restoreState()


def cover() -> list:
    logo = Image(BytesIO(extract_logo()), width=48 * mm, height=25 * mm)
    logo.hAlign = "LEFT"
    title = Paragraph(
        "Guia da equipe de infraestrutura:<br/>desenvolvimento de xApps",
        ParagraphStyle(
            "CoverTitle", parent=H1, fontSize=25, leading=30, spaceAfter=14,
        ),
    )
    subtitle = Paragraph(
        "Acesso seguro, Git, Nephio, Flux, Near-RT RIC e validação KPM",
        ParagraphStyle(
            "CoverSubtitle", parent=BODY, fontSize=13, leading=18,
            textColor=UNB_GREEN, spaceAfter=18,
        ),
    )
    purpose = Table(
        [[Paragraph(
            "OBJETIVO", TABLE_HEADER
        )], [Paragraph(
            "Levar um integrante do primeiro SSH até a entrega revisada de uma "
            "xApp, sem conceder administração total do cluster compartilhado.", BODY
        )]],
        colWidths=[CONTENT_W],
    )
    purpose.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), UNB_BLUE),
        ("BACKGROUND", (0, 1), (-1, 1), PALE_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.8, UNB_GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [
        Spacer(1, 16 * mm), logo, Spacer(1, 18 * mm), title, subtitle,
        purpose, Spacer(1, 15 * mm),
        Paragraph(
            "Ambiente acadêmico e POC - não é procedimento de produção",
            ParagraphStyle(
                "CoverNote", parent=BODY, fontName="Arial-Bold", fontSize=10.5,
                textColor=MUTED, alignment=TA_CENTER,
            ),
        ),
        PageBreak(),
    ]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    markdown = SOURCE.read_text(encoding="utf-8")
    story = cover() + parse_markdown(markdown)
    GuideDocTemplate(str(OUTPUT)).build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
