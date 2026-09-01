#!/usr/bin/env python3
"""Build the comprehensive beginner-facing Open RAN/Kubernetes/Nephio guide."""

from __future__ import annotations

import base64
import re
import textwrap
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/guia-didatico-openran-kubernetes-nephio-unb.pdf"
CONFIG = ROOT / "infra/nephio/webui-compat/unb-configmap.yaml"

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 19 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

UNB_BLUE = colors.HexColor("#0B3E75")
UNB_GREEN = colors.HexColor("#087C3A")
TEAL = colors.HexColor("#0E7490")
VIOLET = colors.HexColor("#6B4BA3")
AMBER = colors.HexColor("#A85A00")
RED = colors.HexColor("#A33A32")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#5D6975")
RULE = colors.HexColor("#C8D2DA")
SOFT = colors.HexColor("#F3F6F8")
PALE_BLUE = colors.HexColor("#EAF2FA")
PALE_GREEN = colors.HexColor("#E8F4ED")
PALE_TEAL = colors.HexColor("#E7F5F8")
PALE_VIOLET = colors.HexColor("#F0EBF8")
PALE_AMBER = colors.HexColor("#FFF4D6")
PALE_RED = colors.HexColor("#FBECEB")
WHITE = colors.white


def register_fonts() -> None:
    font_dir = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("Arial", str(font_dir / "Arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(font_dir / "Arial Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(font_dir / "Arial Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Courier-New", str(font_dir / "Courier New.ttf")))


register_fonts()


def extract_logo() -> bytes:
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"logoUrl:\s*data:image/png;base64,([^\n]+)", text)
    if not match:
        raise RuntimeError(f"official UnB logo not found in {CONFIG}")
    return base64.b64decode(match.group(1).strip())


LOGO_BYTES = extract_logo()

styles = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Arial",
    fontSize=9.5,
    leading=13.3,
    textColor=INK,
    spaceAfter=5.5,
)
LEAD = ParagraphStyle(
    "Lead",
    parent=BODY,
    fontSize=11.2,
    leading=15.5,
    textColor=UNB_BLUE,
    spaceAfter=8,
)
H1 = ParagraphStyle(
    "H1",
    parent=styles["Heading1"],
    fontName="Arial-Bold",
    fontSize=19,
    leading=23,
    textColor=UNB_BLUE,
    spaceBefore=0,
    spaceAfter=9,
)
H2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontName="Arial-Bold",
    fontSize=12.5,
    leading=15.5,
    textColor=UNB_GREEN,
    spaceBefore=7,
    spaceAfter=5,
    keepWithNext=True,
)
H3 = ParagraphStyle(
    "H3",
    parent=styles["Heading3"],
    fontName="Arial-Bold",
    fontSize=10.3,
    leading=13,
    textColor=UNB_BLUE,
    spaceBefore=5,
    spaceAfter=3,
    keepWithNext=True,
)
BULLET = ParagraphStyle(
    "Bullet",
    parent=BODY,
    leftIndent=13,
    firstLineIndent=-7,
    bulletIndent=2,
    spaceAfter=3,
)
SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=7.9,
    leading=10.5,
    textColor=MUTED,
)
CODE = ParagraphStyle(
    "Code",
    parent=styles["Code"],
    fontName="Courier-New",
    fontSize=7.05,
    leading=9.4,
    leftIndent=6,
    rightIndent=6,
    borderColor=RULE,
    borderWidth=0.5,
    borderPadding=7,
    backColor=colors.HexColor("#F6F8FA"),
    textColor=colors.HexColor("#203040"),
    spaceBefore=3,
    spaceAfter=7,
)
CAPTION = ParagraphStyle(
    "Caption",
    parent=SMALL,
    alignment=TA_CENTER,
    fontName="Arial-Italic",
    spaceBefore=3,
    spaceAfter=8,
)
CALLOUT = ParagraphStyle(
    "Callout",
    parent=BODY,
    leftIndent=8,
    rightIndent=8,
    borderPadding=8,
    spaceBefore=4,
    spaceAfter=7,
)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def h1(number: str, title: str) -> Paragraph:
    return p(f'<font color="#087C3A">{number}</font>  {title}', H1)


def h2(title: str) -> Paragraph:
    return p(title, H2)


def h3(title: str) -> Paragraph:
    return p(title, H3)


def bullet(text: str) -> Paragraph:
    return Paragraph(text, BULLET, bulletText="•")


def bullets(items: list[str]) -> list[Paragraph]:
    return [bullet(item) for item in items]


def code_block(text: str) -> Preformatted:
    wrapped: list[str] = []
    for line in text.strip("\n").splitlines():
        if len(line) <= 92:
            wrapped.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        parts = textwrap.wrap(
            line.strip(), width=max(48, 92 - indent), subsequent_indent=" " * (indent + 2)
        )
        wrapped.extend((" " * indent + parts[0], *parts[1:]))
    return Preformatted("\n".join(wrapped), CODE)


def callout(label: str, text: str, tone: str = "blue") -> Table:
    palette = {
        "blue": (PALE_BLUE, UNB_BLUE),
        "green": (PALE_GREEN, UNB_GREEN),
        "teal": (PALE_TEAL, TEAL),
        "violet": (PALE_VIOLET, VIOLET),
        "amber": (PALE_AMBER, AMBER),
        "red": (PALE_RED, RED),
    }
    fill, accent = palette[tone]
    content = p(f'<font color="{accent.hexval()}"><b>{label}</b></font>  {text}', CALLOUT)
    table = Table([[content]], colWidths=[CONTENT_W], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.5, accent),
                ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    header = [p(f"<b>{item}</b>", SMALL) for item in headers]
    body = [[p(cell, SMALL) for cell in row] for row in rows]
    table = Table([header, *body], colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), UNB_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CE")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7F9FA")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


class LayerStack(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 93 * mm

    def draw(self):
        c = self.canv
        layers = [
            ("6", "Observabilidade", "Prometheus · Grafana · Loki · Alertmanager", UNB_BLUE, PALE_BLUE),
            ("5", "Nephio + GitOps", "blueprints · variantes · Porch · Gitea · Flux", UNB_GREEN, PALE_GREEN),
            ("4", "RIC + xApps", "E2 · KPM · RMR · algoritmos", AMBER, PALE_AMBER),
            ("3", "Telecom 5G", "Open5GS · UE · RAN · N2/N3/F1/E2", VIOLET, PALE_VIOLET),
            ("2", "Kubernetes", "nós · namespaces · pods · Services", TEAL, PALE_TEAL),
            ("1", "Infraestrutura", "servidores · Proxmox · VMs · pfSense · redes", UNB_BLUE, PALE_BLUE),
        ]
        y = 245
        for number, title, description, color, fill in layers:
            c.setFillColor(color)
            c.circle(18, y + 15, 15, fill=1, stroke=0)
            c.setFont("Arial-Bold", 8.5)
            c.setFillColor(WHITE)
            c.drawCentredString(18, y + 12, number)
            c.setFillColor(fill)
            c.setStrokeColor(color)
            c.roundRect(42, y, 150, 30, 5, fill=1, stroke=1)
            c.setFont("Arial-Bold", 8.2)
            c.setFillColor(color)
            c.drawString(53, y + 10, title)
            c.setFont("Arial", 8)
            c.setFillColor(INK)
            c.drawString(210, y + 10, description)
            y -= 42


class ThreeFlows(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 62 * mm

    def box(self, x, title, path, text, color, fill):
        c = self.canv
        c.setFillColor(color)
        c.setStrokeColor(color)
        c.roundRect(x, 105, 155, 32, 5, fill=1, stroke=1)
        c.setFont("Arial-Bold", 8.2)
        c.setFillColor(WHITE)
        c.drawCentredString(x + 77.5, 117, title)
        c.setFont("Arial-Bold", 8.2)
        c.setFillColor(color)
        c.drawCentredString(x + 77.5, 80, path)
        c.setFont("Arial", 7.4)
        c.setFillColor(MUTED)
        c.drawCentredString(x + 77.5, 60, text)

    def draw(self):
        self.box(0, "PLANO DE DADOS", "UE → RAN → UPF", "bytes do usuário", VIOLET, PALE_VIOLET)
        self.box(177, "TELEMETRIA E2", "O-DU → RIC → xApp", "medições KPM", AMBER, PALE_AMBER)
        self.box(354, "GESTÃO GITOPS", "Git → Nephio → Flux", "configuração", UNB_GREEN, PALE_GREEN)
        c = self.canv
        c.setStrokeColor(RULE)
        c.setLineWidth(1.2)
        c.line(77, 38, 431, 38)
        c.setFillColor(UNB_BLUE)
        c.roundRect(160, 5, 190, 26, 5, fill=1, stroke=0)
        c.setFont("Arial-Bold", 8)
        c.setFillColor(WHITE)
        c.drawCentredString(255, 14, "PROMETHEUS · GRAFANA · LOKI")


class SignalPath(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 56 * mm

    def draw(self):
        c = self.canv
        columns = [
            ("UE", "srsUE\nperfil IMSI", UNB_GREEN),
            ("RAN", "ZMQ\nDU/CU", VIOLET),
            ("RIC", "E2Term\nSubMgr", AMBER),
            ("xApp", "callback\nalgoritmo", UNB_GREEN),
            ("OBS", "Prometheus\nGrafana", UNB_BLUE),
        ]
        box_w, gap, y = 82, 18, 74
        for idx, (title, subtitle, color) in enumerate(columns):
            x = idx * (box_w + gap)
            c.setFillColor(WHITE)
            c.setStrokeColor(color)
            c.setLineWidth(1.2)
            c.roundRect(x, y, box_w, 48, 6, fill=1, stroke=1)
            c.setFont("Arial-Bold", 8.5)
            c.setFillColor(color)
            c.drawCentredString(x + box_w / 2, y + 32, title)
            c.setFont("Arial", 7.2)
            c.setFillColor(INK)
            for line_index, line_text in enumerate(subtitle.split("\n")):
                c.drawCentredString(x + box_w / 2, y + 19 - line_index * 9, line_text)
            if idx < len(columns) - 1:
                c.setStrokeColor(MUTED)
                c.line(x + box_w, y + 24, x + box_w + gap - 2, y + 24)
                c.line(x + box_w + gap - 2, y + 24, x + box_w + gap - 7, y + 28)
                c.line(x + box_w + gap - 2, y + 24, x + box_w + gap - 7, y + 20)
        c.setFont("Arial", 7.3)
        c.setFillColor(MUTED)
        c.drawString(0, 48, "Autenticação do assinante acontece no Open5GS; a xApp não cadastra SIM.")
        c.drawString(0, 33, "DRB.UEThpDl nasce no O-DU e chega pela cadeia E2SM-KPM/RMR.")
        c.drawString(0, 18, "O teste estimula tun_srsue e correlaciona o pico no dashboard.")


class GitOpsFlow(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 54 * mm

    def draw(self):
        c = self.canv
        labels = ["Código", "Imagem\nmultiarch", "Team\nBlueprint", "Package\nVariant", "Porch", "Gitea", "Flux", "xApp"]
        box_w = 53
        gap = 9
        x = 0
        for index, label in enumerate(labels):
            color = UNB_GREEN if index in (0, 7) else UNB_BLUE
            c.setFillColor(WHITE)
            c.setStrokeColor(color)
            c.roundRect(x, 72, box_w, 37, 5, fill=1, stroke=1)
            c.setFillColor(color)
            c.setFont("Arial-Bold", 7.3)
            for line_index, line_text in enumerate(label.split("\n")):
                c.drawCentredString(x + box_w / 2, 94 - line_index * 10, line_text)
            if index < len(labels) - 1:
                c.setStrokeColor(MUTED)
                c.line(x + box_w, 90, x + box_w + gap - 2, 90)
                c.line(x + box_w + gap - 2, 90, x + box_w + gap - 7, 94)
                c.line(x + box_w + gap - 2, 90, x + box_w + gap - 7, 86)
            x += box_w + gap
        c.setFont("Arial", 7.2)
        c.setFillColor(MUTED)
        c.drawString(0, 46, "O aluno produz código, teste, imagem e blueprint.")
        c.drawString(0, 32, "A infraestrutura revisa digest, RBAC, portas e variante do site.")
        c.drawString(0, 18, "Nephio publica configuração; Flux entrega; Kubernetes executa.")


class LabTopology(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 116 * mm

    def box(self, x, y, w, h, title, lines, color):
        c = self.canv
        c.setFillColor(WHITE)
        c.setStrokeColor(color)
        c.setLineWidth(1.3)
        c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(x, y + h - 18, w, 18, fill=1, stroke=0)
        c.setFont("Arial-Bold", 8.5)
        c.setFillColor(WHITE)
        c.drawString(x + 7, y + h - 13, title)
        c.setFont("Arial", 7.2)
        c.setFillColor(INK)
        line_y = y + h - 31
        for line_text in lines:
            c.drawString(x + 7, line_y, line_text)
            line_y -= 11

    def arrow(self, x1, y1, x2, y2, label=""):
        c = self.canv
        c.setStrokeColor(MUTED)
        c.setLineWidth(1.2)
        c.line(x1, y1, x2, y2)
        if x2 >= x1:
            c.line(x2, y2, x2 - 6, y2 + 4)
            c.line(x2, y2, x2 - 6, y2 - 4)
        else:
            c.line(x2, y2, x2 + 6, y2 + 4)
            c.line(x2, y2, x2 + 6, y2 - 4)
        if label:
            c.setFont("Arial", 6.6)
            c.setFillColor(MUTED)
            c.drawCentredString((x1 + x2) / 2, y1 + 5, label)

    def draw(self):
        c = self.canv
        c.setFont("Arial-Bold", 11)
        c.setFillColor(UNB_BLUE)
        c.drawString(0, 316, "Topologia didática multi-site")
        self.box(0, 230, 92, 65, "ALUNO / VPN NMI", ["Git + código Python", "Nephio WebUI", "Grafana / logs"], UNB_GREEN)
        self.box(113, 196, 252, 112, "NMI · CLUSTER AMD64", ["5 nós Kubernetes", "Open5GS + UE/RAN ZMQ", "Near-RT RIC + xApps", "Prometheus/Grafana/Loki", "Nephio/Porch/Gitea/Flux"], UNB_BLUE)
        self.box(386, 212, 123, 82, "CIC · CLUSTER ARM64", ["Ampere 2 + Ampere 3", "Flux mínimo", "xApp arm64", "telemetria ao NMI"], VIOLET)
        self.arrow(92, 262, 113, 262, "VPN")
        self.arrow(365, 264, 386, 264, "rede")
        self.box(113, 96, 112, 72, "CAMINHO 5G", ["srsUE → ZMQ", "O-DU / O-CU", "Open5GS / UPF"], VIOLET)
        self.box(253, 96, 112, 72, "CAMINHO E2", ["E2Term / E2Mgr", "SubMgr / RTMgr", "KPM → xApp"], AMBER)
        self.box(386, 96, 123, 72, "OBSERVABILIDADE", ["/metrics", "Prometheus", "Grafana + Loki"], TEAL)
        self.arrow(225, 132, 253, 132, "E2")
        self.arrow(365, 132, 386, 132, "métricas")
        self.arrow(309, 196, 309, 168, "workloads")
        c.setFont("Arial", 7.2)
        c.setFillColor(MUTED)
        c.drawString(0, 54, "Gestão: Git → Porch → Gitea → Flux → Kubernetes")
        c.drawString(0, 41, "Dados: UE → RAN → UPF → Internet")
        c.drawString(0, 28, "Telemetria: O-DU → E2 → Near-RT RIC → xApp → Grafana")


class RepoMap(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 94 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(UNB_BLUE)
        c.roundRect(0, 250, 120, 30, 5, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Arial-Bold", 9)
        c.drawCentredString(60, 261, "oran-stack/")
        c.setStrokeColor(RULE)
        c.setLineWidth(1.2)
        c.line(60, 250, 60, 10)
        rows = [
            ("ansible/", "provisionamento de hosts, cluster e rede", UNB_BLUE),
            ("helm/", "charts da pilha base", TEAL),
            ("xapps/", "código Python e templates", UNB_GREEN),
            ("packages/nephio/", "Team Blueprints KRM", UNB_GREEN),
            ("infra/nephio/", "Porch, variantes, onboarding e WebUI", VIOLET),
            ("scripts/", "demos, geradores e verificação", AMBER),
            ("docs/", "arquitetura, status e tutoriais", UNB_BLUE),
        ]
        y = 212
        for name, role, color in rows:
            c.setStrokeColor(RULE)
            c.line(60, y + 10, 88, y + 10)
            c.setStrokeColor(color)
            c.setFillColor(WHITE)
            c.roundRect(96, y, 130, 22, 4, fill=1, stroke=1)
            c.setFont("Arial-Bold", 7.8)
            c.setFillColor(color)
            c.drawString(104, y + 8, name)
            c.setFont("Arial", 7.8)
            c.setFillColor(INK)
            c.drawString(244, y + 8, role)
            y -= 34


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Guia didático - Open RAN, Kubernetes e Nephio na UnB",
            author="Laboratório Open RAN - Universidade de Brasília",
            subject="Fundamentos, arquitetura, reprodução e desenvolvimento de xApps",
        )
        frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            CONTENT_W,
            PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="guide", frames=[frame], onPage=self.draw_page))

    def draw_page(self, canvas, doc):
        page = canvas.getPageNumber()
        canvas.saveState()
        if page == 1:
            canvas.setFillColor(UNB_BLUE)
            canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            canvas.setFillColor(UNB_GREEN)
            canvas.rect(0, 0, 9 * mm, PAGE_H, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#134E87"))
            canvas.circle(PAGE_W - 9 * mm, PAGE_H - 15 * mm, 46 * mm, fill=1, stroke=0)
        else:
            canvas.setStrokeColor(colors.HexColor("#D4DCE3"))
            canvas.setLineWidth(0.5)
            canvas.line(MARGIN_X, PAGE_H - 12 * mm, PAGE_W - MARGIN_X, PAGE_H - 12 * mm)
            canvas.setFont("Arial-Bold", 7.4)
            canvas.setFillColor(UNB_BLUE)
            canvas.drawString(MARGIN_X, PAGE_H - 9.2 * mm, "LABORATÓRIO OPEN RAN · UnB")
            canvas.setFont("Arial", 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 9.2 * mm, "Guia didático | Kubernetes + Nephio + xApps")
            canvas.line(MARGIN_X, 11 * mm, PAGE_W - MARGIN_X, 11 * mm)
            canvas.setFont("Arial", 7.2)
            canvas.drawString(MARGIN_X, 7.5 * mm, "PoC acadêmica · VPN institucional NMI")
            canvas.drawRightString(PAGE_W - MARGIN_X, 7.5 * mm, f"página {page}")
        canvas.restoreState()


def cover_story() -> list:
    logo = Image(BytesIO(LOGO_BYTES), width=34 * mm, height=30 * mm)
    title_style = ParagraphStyle(
        "CoverTitle", fontName="Arial-Bold", fontSize=29, leading=33, textColor=WHITE, alignment=TA_LEFT, spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle", fontName="Arial", fontSize=14, leading=19, textColor=colors.HexColor("#DCEAF7"), alignment=TA_LEFT
    )
    meta_style = ParagraphStyle("CoverMeta", fontName="Arial", fontSize=9, leading=13, textColor=colors.HexColor("#DCEAF7"))
    kicker = ParagraphStyle("Kicker", parent=SMALL, fontName="Arial-Bold", fontSize=10, textColor=colors.HexColor("#9AD0AE"), leading=13)
    return [
        Spacer(1, 5 * mm),
        logo,
        Spacer(1, 27 * mm),
        p("GUIA DIDÁTICO COMPLETO", kicker),
        p("Open RAN sem mistério", title_style),
        p("Kubernetes, Nephio, 5G Core, RIC, xApps e o laboratório multi-site da UnB.", subtitle_style),
        Spacer(1, 22 * mm),
        callout("OBJETIVO", "Ensinar do servidor físico ao KPI no Grafana, documentar o que foi construído e permitir que alunos reproduzam a PoC e criem novos experimentos.", "green"),
        Spacer(1, 12 * mm),
        p("NMI + CIC | PoC acadêmica | versão 1.0 | 1º de setembro de 2026", meta_style),
        p("Repositório: github.com/lucasrodri/oran-stack", meta_style),
        PageBreak(),
    ]


def chapter(story: list, number: str, title: str, lead: str, content: list) -> None:
    story += [h1(number, title), p(lead, LEAD), *content, PageBreak()]


def build_story() -> list:
    story: list = []
    story.extend(cover_story())

    story += [
        h1("0", "Como usar este guia"),
        p("Este documento foi escrito para alunos e professores que ainda não dominam Kubernetes, telecom 5G ou Nephio. Ele não pressupõe que a pessoa conheça a sopa de letrinhas."),
        callout("LEITURA EM DUAS VELOCIDADES", "Para uma visão geral, leia os capítulos 1 a 8 e 22 a 27. Para reproduzir, siga os capítulos 28 a 42 com o laboratório já provisionado.", "blue"),
        h2("O que você deve conseguir explicar ao final"),
        *bullets([
            "por que servidor físico, VM, nó, namespace, pod e contêiner não são sinônimos;",
            "por que Kubernetes e Nephio são complementares, não concorrentes;",
            "como UE, RAN, Open5GS, Near-RT RIC, xApp e Grafana formam um experimento;",
            "como um código Python vira imagem, pacote, variante, Deployment e métrica;",
            "onde cada componente está implantado no NMI e no CIC;",
            "quais limitações da PoC são intencionais e quais viram temas de pesquisa.",
        ]),
        h2("Partes do documento"),
        data_table(
            ["Parte", "Capítulos", "Pergunta respondida"],
            [
                ["I · Fundamentos", "1–8", "o que é cada tecnologia?"],
                ["II · Laboratório", "9–15", "onde tudo roda?"],
                ["III · Repositório", "16–21", "onde está cada artefato?"],
                ["IV · Fluxos", "22–27", "como a PoC funciona de ponta a ponta?"],
                ["V · Reprodução", "28–34", "como validar e operar com segurança?"],
                ["VI · Nova xApp", "35–42", "como criar um experimento próprio?"],
                ["Apêndices", "A–E", "quais comandos e termos consultar?"],
            ],
            [38 * mm, 28 * mm, 103 * mm],
        ),
        callout("ESCOPO", "É uma PoC acadêmica. Não buscamos alta disponibilidade, SLA ou backups de produção; buscamos transparência, repetibilidade e evidência científica.", "amber"),
        PageBreak(),
    ]

    chapter(story, "1", "Uma visão em seis camadas", "O laboratório fica simples quando cada responsabilidade tem uma camada e um dono.", [
        LayerStack(),
        p("Figura 1 · As seis camadas da PoC, da infraestrutura à observabilidade.", CAPTION),
        callout("REGRA MENTAL", "As camadas cooperam, mas uma não substitui a outra. O erro mais comum é pedir ao Kubernetes uma função do Nephio ou atribuir ao Nephio o tráfego 5G.", "green"),
        h2("Uma frase por camada"),
        *bullets([
            "<b>Infraestrutura</b> fornece CPU, RAM, disco e redes.",
            "<b>Kubernetes</b> executa e reconcilia workloads em contêineres.",
            "<b>Telecom 5G</b> registra o UE e transporta os dados do usuário.",
            "<b>RIC + xApps</b> recebe telemetria da RAN e executa algoritmos.",
            "<b>Nephio + GitOps</b> organiza e entrega configuração por site.",
            "<b>Observabilidade</b> transforma estado, métricas e logs em evidência.",
        ]),
    ])

    chapter(story, "2", "Do servidor ao pod", "O caminho físico ajuda a entender onde um processo realmente está rodando.", [
        data_table(
            ["Nível", "Definição", "Exemplo"],
            [
                ["Servidor físico", "máquina real com CPU, RAM, NIC e disco", "Dell ou Ampere"],
                ["Hipervisor", "software que hospeda VMs", "Proxmox VE"],
                ["VM", "computador virtual com SO próprio", "oran-k8s-01"],
                ["Nó Kubernetes", "máquina participante do cluster", "control plane ou worker"],
                ["Pod", "menor unidade executável do Kubernetes", "pod do AMF ou da xApp"],
                ["Contêiner", "processo empacotado com dependências", "imagem oran-xapps"],
            ],
            [35 * mm, 82 * mm, 52 * mm],
        ),
        callout("EXEMPLO REAL", "Proxmox002 hospeda a VM oran-k8s-01. Essa VM é um nó Kubernetes. Nela rodam pods do Open5GS, da RAN e do RIC base.", "blue"),
        h2("Um ou dez servidores?"),
        p("A lógica de comunicação entre pods é a mesma. Mais máquinas aumentam capacidade, permitem distribuição de falhas e tornam o experimento multi-host, mas não mudam o modelo declarativo do Kubernetes."),
        callout("POC, NÃO PRODUÇÃO", "Nesta bancada, distribuir workloads serve para ensinar rede, scheduling e arquitetura. Não estamos perseguindo alta disponibilidade completa.", "amber"),
    ])

    chapter(story, "3", "Kubernetes em linguagem simples", "Kubernetes mantém aplicações em execução a partir de objetos declarativos.", [
        data_table(
            ["Objeto", "Modelo mental", "Exemplo na PoC"],
            [
                ["Cluster", "conjunto administrado de nós", "NMI ou CIC"],
                ["Node", "máquina que executa workloads", "oran-k8s-w02"],
                ["Pod", "um ou mais contêineres co-localizados", "kpm-load-watch-*"],
                ["Deployment", "declara réplicas e atualização", "deployment/kpm-load-watch"],
                ["Service", "endereço estável para pods", "monitoring-grafana"],
                ["Namespace", "escopo lógico de objetos", "ricxapp"],
                ["ConfigMap/Secret", "configuração e dado sensível", "credenciais e YAML"],
            ],
            [32 * mm, 72 * mm, 65 * mm],
        ),
        h2("Spec e status"),
        p("O manifesto declara a <b>spec</b>, isto é, o estado desejado. Os controladores observam o <b>status</b> e tentam fazer o estado real convergir para o desejado."),
        code_block("""kubectl get deployment -n ricxapp kpm-load-watch
kubectl describe deployment -n ricxapp kpm-load-watch
kubectl get pods -n ricxapp -o wide"""),
        callout("NÃO CRIE PODS DIRETAMENTE", "Deployments administram pods substituíveis. Um pod isolado não oferece a mesma reconciliação e atualização.", "green"),
    ])

    chapter(story, "4", "Namespace não é outro cluster", "Namespaces dividem recursos e nomes dentro de uma única API Kubernetes.", [
        p("No NMI, 5g-core, ran, near-rt-ric, ricxapp, monitoring e nephio-* são namespaces do <b>mesmo cluster de cinco nós</b>. Eles não possuem control planes independentes."),
        data_table(
            ["Namespace", "Conteúdo"],
            [
                ["5g-core", "Open5GS, MongoDB e WebUI"],
                ["ran", "O-CU, O-DU e srsUE"],
                ["near-rt-ric", "E2Term, E2Mgr, SubMgr, RTMgr, AppMgr e serviços base"],
                ["ricxapp", "r4-simple-mon e kpm-load-watch"],
                ["monitoring", "Prometheus, Grafana, Loki, Alloy e Alertmanager"],
                ["nephio-* / porch-*", "WebUI, Porch e controllers"],
            ],
            [49 * mm, 120 * mm],
        ),
        callout("COMPARAÇÃO", "Um condomínio pode ter blocos e apartamentos; continua sendo um condomínio. Namespaces organizam o cluster, mas não criam um novo cluster.", "blue"),
        code_block("""kubectl get namespaces
kubectl get pods -A
kubectl get pods -n ricxapp"""),
    ])

    chapter(story, "5", "Kubernetes executa; Nephio entrega", "Essa é a distinção mais importante do material.", [
        data_table(
            ["Kubernetes", "Nephio/Porch"],
            [
                ["agenda pods nos nós", "organiza pacotes declarativos"],
                ["mantém estado desejado", "especializa variantes por site"],
                ["oferece rede e descoberta", "publica revisões no Git"],
                ["reinicia/substitui workloads", "automatiza o fluxo de configuração"],
            ],
            [84.5 * mm, 84.5 * mm],
        ),
        callout("NÃO É UMA ESCOLHA", "Usamos Nephio sobre Kubernetes. Sem Kubernetes não há onde executar a xApp. Sem Nephio ainda seria possível aplicar YAML/Helm manualmente.", "amber"),
        h2("E Rancher ou OpenShift?"),
        p("Rancher e OpenShift ajudam a administrar/oferecer a plataforma Kubernetes. Nephio é especializado no ciclo de pacotes e configuração de funções de rede por sites e variantes. Nenhum deles substitui o runtime Kubernetes."),
        h2("E Helm?"),
        p("Helm renderiza templates parametrizados. Nephio/Porch governa pacotes, revisões e variantes. Nesta PoC, Helm continua responsável pela pilha base; Nephio foi introduzido de forma incremental para xApps."),
    ])

    chapter(story, "6", "O que é Open RAN", "Open RAN separa funções da RAN e define interfaces mais abertas entre elas.", [
        data_table(
            ["Função", "Responsabilidade", "Na PoC"],
            [
                ["UE", "equipamento do usuário", "srsUE em software"],
                ["O-RU", "rádio e conversão de sinais", "RF substituída por ZMQ"],
                ["O-DU", "funções de rádio de menor camada", "OCUDU DU"],
                ["O-CU", "controle e plano de usuário centralizados", "OCUDU CU"],
                ["5G Core", "registro, sessão e tráfego", "Open5GS"],
                ["Near-RT RIC", "telemetria/controle próximo de tempo real", "O-RAN SC RIC"],
            ],
            [29 * mm, 80 * mm, 60 * mm],
        ),
        callout("RF SIMULADA", "ZMQ substitui o enlace de rádio físico. O restante do fluxo — registro, sessão PDU, E2 e KPM — é software real da pilha.", "violet"),
        h2("Por que isso é interessante para ensino?"),
        *bullets([
            "permite trocar componentes e estudar interfaces;",
            "separa plano de dados, telemetria e gestão;",
            "abre espaço para xApps e algoritmos de pesquisa;",
            "permite começar sem SDR, antena e licenciamento de espectro.",
        ]),
    ])

    chapter(story, "7", "UE, SIM, IMSI e IMEI", "O assinante, o aparelho e a xApp têm papéis independentes.", [
        data_table(
            ["Termo", "Significado", "Quem usa"],
            [
                ["UE", "equipamento do usuário", "RAN e Core"],
                ["SIM", "credencial do assinante", "UE + Open5GS"],
                ["IMSI", "identidade do assinante", "Open5GS autentica"],
                ["K / OPc", "material criptográfico do SIM", "UE + Core"],
                ["IMEI", "identidade do aparelho", "não substitui o IMSI"],
                ["PDU Session", "sessão de dados 5G", "SMF/UPF + UE"],
            ],
            [30 * mm, 79 * mm, 60 * mm],
        ),
        callout("A XAPP NÃO CADASTRA SIM", "O cadastro ocorre no Open5GS WebUI/MongoDB. A xApp recebe telemetria da RAN pelo E2.", "amber"),
        h2("Quando houver rádio e celular reais"),
        p("Será possível usar um SIM programável, desde que o cartão e o Open5GS compartilhem IMSI, K, OPc/OP e parâmetros compatíveis. Também serão necessários SDR/RU, banda permitida, sincronismo e configuração de RF segura."),
    ])

    chapter(story, "8", "RIC, xApp, KPI, KPM e RMR", "A xApp executa um algoritmo sobre informação recebida do E2 node.", [
        SignalPath(),
        p("Figura 2 · O caminho didático do assinante até a observabilidade.", CAPTION),
        data_table(
            ["Sigla", "Definição curta", "Exemplo"],
            [
                ["RIC", "controlador inteligente da RAN", "Near-RT RIC"],
                ["xApp", "aplicação hospedada pelo RIC", "simple-mon"],
                ["E2", "interface RAN ↔ RIC", "SCTP/E2AP"],
                ["KPM", "modelo/serviço de medições", "E2SM-KPM"],
                ["KPI", "valor de desempenho", "DRB.UEThpDl"],
                ["RMR", "mensageria do RIC", "indicação 12050"],
            ],
            [24 * mm, 91 * mm, 54 * mm],
        ),
        callout("HOJE", "simple-mon e load-watch monitoram. Elas não enviam ações de controle para a RAN.", "green"),
    ])

    chapter(story, "9", "Três fluxos que não devem ser confundidos", "Dados do usuário, telemetria e gestão coexistem, mas são fluxos diferentes.", [
        ThreeFlows(),
        p("Figura 3 · Dados, telemetria e gestão observados por uma camada comum.", CAPTION),
        h2("Plano de dados"),
        p("Transporta o tráfego do usuário: srsUE → RAN → UPF → rede externa."),
        h2("Telemetria E2"),
        p("Transporta medições e assinaturas: O-DU → E2Term/SubMgr/RMR → xApp."),
        h2("Gestão GitOps"),
        p("Transporta estado desejado: código/pacote → Porch/Git → Flux → Kubernetes."),
        callout("OBSERVABILIDADE", "Prometheus, Grafana e Loki reúnem evidências dos três fluxos sem se tornarem parte do plano de dados 5G.", "blue"),
    ])

    chapter(story, "10", "Topologia atual NMI + CIC", "A arquitetura implantada combina cinco nós amd64 no NMI e dois nós arm64 no CIC.", [
        LabTopology(),
        p("Figura 4 · Topologia lógica multi-site validada em 1º de setembro de 2026.", CAPTION),
        callout("DECISÃO ARQUITETURAL", "NMI concentra a pilha 5G, o management plane Nephio e a observabilidade. CIC valida portabilidade ARM sem duplicar toda a pilha.", "violet"),
    ])

    chapter(story, "11", "NMI: cinco nós e papéis", "O cluster NMI mistura Debian e Ubuntu sem problema; Kubernetes abstrai o sistema operacional desde que os requisitos sejam compatíveis.", [
        data_table(
            ["Nó", "SO", "Papel principal", "Workloads"],
            [
                ["oran-k8s-01", "Debian 12", "control plane + telecom", "Open5GS, RAN, RIC base"],
                ["oran-k8s-w01", "Debian 12", "RIC distribuído", "E2Term, RTMgr"],
                ["oran-k8s-w02", "Debian 12", "xApps", "simple-mon, load-watch"],
                ["nmi-srv03", "Ubuntu 24.04", "observabilidade", "Prometheus, Grafana, Loki"],
                ["nephio-k8s-w01", "Ubuntu 22.04", "gestão GitOps", "Porch, Gitea, Flux, WebUI"],
            ],
            [38 * mm, 29 * mm, 49 * mm, 53 * mm],
        ),
        callout("SNAPSHOT", "Todos os cinco nós estavam Ready, amd64 e em Kubernetes v1.30.14 na consulta de 1º de setembro de 2026.", "green"),
        code_block("""kubectl get nodes -o wide
kubectl get pods -A -o wide"""),
    ])

    chapter(story, "12", "CIC: cluster ARM mínimo", "Duas VMs Ampere formam um cluster separado para experimentar workloads arm64.", [
        data_table(
            ["VM", "Host", "Endereço", "Recursos", "Papel"],
            [
                ["120 · cic-k8s-cp01", "Ampere 2", "192.168.0.210", "8 vCPU · 16 GiB · 100 GB", "control plane"],
                ["121 · cic-k8s-w01", "Ampere 3", "192.168.0.211", "8 vCPU · 16 GiB · 100 GB", "worker/xApp"],
            ],
            [38 * mm, 27 * mm, 31 * mm, 45 * mm, 28 * mm],
        ),
        *bullets([
            "Kubernetes v1.32.13 arm64;",
            "Flannel, Multus, OVS-CNI e local-path;",
            "Flux mínimo no CIC; Nephio/Porch continuam no NMI;",
            "r4-simple-mon-cic executa nativamente como aarch64;",
            "telemetria do CIC é centralizada no Grafana NMI.",
        ]),
        callout("POR QUE OUTRO CLUSTER?", "É outro site e outra arquitetura. Um cluster Kubernetes multiarch seria possível, mas não representaria tão bem a separação física NMI/CIC nem simplificaria a conectividade dos dois laboratórios.", "violet"),
    ])

    chapter(story, "13", "Rede: Flannel, Multus e OVS", "A PoC usa uma rede de cluster e redes adicionais de telecom.", [
        data_table(
            ["Tecnologia", "Resolve", "Na PoC"],
            [
                ["Flannel", "pod ↔ pod entre nós", "overlay VXLAN padrão"],
                ["Service/DNS", "descoberta estável de pods", "*.svc.cluster.local"],
                ["Multus", "mais de uma interface por pod", "anexa redes de telecom"],
                ["OVS-CNI", "bridges e conectividade L2", "n2br, f1cbr, e2br"],
                ["pfSense", "roteamento/firewall entre redes", ".71, .72 e CIC"],
            ],
            [34 * mm, 69 * mm, 66 * mm],
        ),
        callout("DOIS PROBLEMAS", "Flannel mantém a comunicação Kubernetes simples; Multus/OVS preserva interfaces e endereços específicos de N2, F1-C e E2.", "blue"),
        h2("Por que SCTP aparece tanto?"),
        p("NGAP/N2 e E2AP usam SCTP. Por isso, firewall, NAT e caminhos multi-host precisam ser validados com atenção; HTTP funcionando não garante que SCTP esteja liberado."),
    ])

    chapter(story, "14", "Distribuição dos workloads", "A colocação de pods foi escolhida para mostrar o laboratório distribuído e preservar interfaces sensíveis.", [
        data_table(
            ["Domínio", "Nó predominante", "Motivo"],
            [
                ["5G Core", "oran-k8s-01", "baseline estável e acesso às redes"],
                ["RAN", "oran-k8s-01", "ZMQ e interfaces de telecom"],
                ["RIC base", "oran-k8s-01", "serviços centrais"],
                ["E2Term / RTMgr", "oran-k8s-w01", "provar RIC multi-host"],
                ["xApps", "oran-k8s-w02", "isolar algoritmos"],
                ["Observabilidade", "nmi-srv03", "CPU/RAM e armazenamento"],
                ["Nephio", "nephio-k8s-w01", "isolar a gestão em outro worker"],
            ],
            [45 * mm, 46 * mm, 78 * mm],
        ),
        callout("NAMESPACE NÃO FIXA NÓ", "A colocação resulta de affinity/nodeSelector/taints e do scheduler. O namespace organiza; ele não determina sozinho onde o pod roda.", "amber"),
    ])

    chapter(story, "15", "Observabilidade e acesso", "O NMI centraliza métricas, dashboards, logs curtos e alertas para toda a PoC.", [
        data_table(
            ["Componente", "Função", "Onde roda"],
            [
                ["Prometheus", "coleta e armazena métricas", "nmi-srv03"],
                ["Grafana", "dashboards e correlação", "nmi-srv03"],
                ["Loki", "logs com retenção curta", "nmi-srv03"],
                ["Alloy", "coleta logs nos nós", "DaemonSet"],
                ["Alertmanager", "agrupa alertas", "nmi-srv03"],
            ],
            [38 * mm, 78 * mm, 53 * mm],
        ),
        callout("LOGS LIMITADOS", "O laboratório evita loops de log e retenção longa. O objetivo é diagnóstico, não arquivamento de produção.", "green"),
        h2("Acesso"),
        p("As interfaces são privadas e acessíveis pela VPN institucional do NMI. Credenciais ficam em Secrets/cofre ou são fornecidas pelo responsável; não devem ser publicadas no repositório ou neste guia."),
        data_table(
            ["Interface", "URL pela VPN"],
            [
                ["Open5GS WebUI", "http://192.168.72.10:30454"],
                ["Nephio WebUI", "http://192.168.71.30:30707/config-as-data"],
                ["Grafana Overview", "http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview"],
                ["Grafana Multi-site", "http://192.168.72.10:30300/d/oran-multisite/cic-arm-lab"],
                ["Grafana Logs", "http://192.168.72.10:30300/d/oran-logs/o-ran-kubernetes-logs"],
                ["Alertmanager", "http://192.168.72.10:30301"],
            ],
            [48 * mm, 121 * mm],
        ),
    ])

    chapter(story, "16", "O repositório como mapa", "O código versionado é a fonte de conhecimento e reprodução da bancada.", [
        RepoMap(),
        p("Figura 5 · Diretórios principais e sua responsabilidade.", CAPTION),
        callout("LEITURA RECOMENDADA", "README.md explica a entrada; docs/STATUS.md registra fatos e resultados; os inventários e charts materializam a arquitetura.", "blue"),
    ])

    chapter(story, "17", "Ansible: preparar a base", "Ansible automatiza máquinas, Kubernetes, rede, imagens e a implantação inicial.", [
        *bullets([
            "inventários descrevem hosts e variáveis;",
            "roles instalam container runtime, Kubernetes e plugins;",
            "playbooks criam/juntam os nós ao cluster;",
            "tarefas configuram Multus, OVS e bridges;",
            "playbooks de deploy instalam charts Helm da pilha base.",
        ]),
        code_block("""ansible/
├── inventories/
├── playbooks/
└── roles/"""),
        callout("LIMITAÇÃO INTENCIONAL", "Nephio não substituiu Ansible no provisionamento de Proxmox, VMs ou Kubernetes. O caminho de bootstrap continua independente.", "amber"),
    ])

    chapter(story, "18", "Helm: empacotar a pilha base", "Os charts organizam recursos Kubernetes parametrizados.", [
        data_table(
            ["Chart", "Conteúdo"],
            [
                ["helm/5g-core", "Open5GS, MongoDB, WebUI e Services"],
                ["helm/ran", "O-CU, O-DU, srsUE e redes adicionais"],
                ["helm/near-rt-ric", "plataforma RIC e rotas"],
                ["helm/xapps", "caminho histórico/base das xApps"],
                ["helm/monitoring", "Prometheus, Grafana, Loki e alertas"],
            ],
            [49 * mm, 120 * mm],
        ),
        p("Helm transforma values + templates em YAML. O Kubernetes continua sendo quem executa e reconcilia os objetos resultantes."),
        callout("MIGRAÇÃO INCREMENTAL", "As xApps de laboratório passaram a ter entrega por Nephio/Flux, mas a pilha base permanece reproduzível por Helm/Ansible.", "green"),
    ])

    chapter(story, "19", "Código das xApps", "A base Python encapsula integração com o RIC para que o aluno foque no algoritmo.", [
        data_table(
            ["Arquivo/diretório", "Responsabilidade"],
            [
                ["xapps/python/xAppBase.py", "registro, assinatura, RMR, decode e métricas"],
                ["xapps/python/kpm_mon_xapp.py", "simple-mon de referência"],
                ["xapps/python/kpm_load_watch_xapp.py", "média móvel e estados"],
                ["xapps/templates/kpm-monitor", "scaffold para nova xApp"],
                ["tests/", "testes automatizados"],
            ],
            [62 * mm, 107 * mm],
        ),
        callout("CONTRATO", "Uma xApp deve registrar-se, criar uma assinatura, receber RMR, decodificar KPM, limitar logs e expor /metrics.", "green"),
    ])

    chapter(story, "20", "Pacotes Nephio", "Packages e infra/nephio registram o ciclo declarativo das xApps.", [
        data_table(
            ["Caminho", "Conteúdo"],
            [
                ["packages/nephio/r4-simple-mon", "blueprint reutilizável"],
                ["packages/nephio/kpm-load-watch", "blueprint da xApp do aluno"],
                ["infra/nephio/blueprints", "publicação e PackageVariants"],
                ["infra/nephio/nmi-onboarding", "RBAC e Flux do NMI"],
                ["infra/nephio/cic-onboarding", "entrega mínima ao CIC"],
                ["infra/nephio/webui-compat", "WebUI e identidade visual UnB"],
            ],
            [68 * mm, 101 * mm],
        ),
        callout("OBJETOS VIVOS", "WorkloadClusters nmi/cic e PackageVariants simple-mon-nmi-v5, simple-mon-cic-arm64 e kpm-load-watch-nmi estavam presentes no snapshot.", "blue"),
    ])

    chapter(story, "21", "Scripts, documentação e evidência", "Uma boa PoC precisa ser demonstrável e auditável.", [
        data_table(
            ["Artefato", "Uso"],
            [
                ["scripts/demo-kpm.sh", "gera tráfego e observa KPM"],
                ["scripts/demo-load-watch.sh", "prova estados idle/active/busy"],
                ["scripts/demo-kpm-multisite.sh", "compara NMI e CIC"],
                ["scripts/demo-ue-lab.sh", "troca perfis UE sequenciais"],
                ["scripts/new-kpm-xapp.sh", "gera uma nova xApp"],
                ["docs/STATUS.md", "linha do tempo, fatos e limitações"],
                ["docs/STUDENT_XAPP_LAB.md", "laboratório do aluno"],
                ["docs/UE_SIMULATION_LAB.md", "perfis e limites ZMQ"],
            ],
            [67 * mm, 102 * mm],
        ),
        callout("CIÊNCIA REPRODUZÍVEL", "O script define o estímulo; Prometheus/Grafana registram a resposta; Git registra a configuração e o código.", "green"),
    ])

    chapter(story, "22", "Plano de dados de ponta a ponta", "O download do UE atravessa RAN e Core; o RIC não carrega os bytes do usuário.", [
        data_table(
            ["Etapa", "Evento"],
            [
                ["1", "srsUE estabelece enlace ZMQ com a RAN"],
                ["2", "UE executa registro NAS pelo AMF"],
                ["3", "SMF cria a sessão PDU e programa o UPF"],
                ["4", "tun_srsue recebe endereço do pool 10.45.0.0/16"],
                ["5", "requisição HTTP sai pelo GTP-U/UPF e recebe retorno"],
                ["6", "O-DU mede throughput e gera KPM em paralelo"],
            ],
            [22 * mm, 147 * mm],
        ),
        code_block("""ip addr show tun_srsue
curl --interface tun_srsue -I http://example.com/
sudo ./scripts/demo-kpm.sh"""),
        callout("PROVA", "O laboratório validou registro 5G SA, sessão PDU, egress com HTTP 200 e transferência limitada de 50 MB.", "green"),
    ])

    chapter(story, "23", "Caminho E2/KPM", "A xApp só é funcional quando a indicação percorre toda a cadeia.", [
        SignalPath(),
        h2("Critérios de aceite"),
        *bullets([
            "E2 node aparece CONNECTED no E2Mgr;",
            "AppMgr lista a xApp e seu endpoint RMR;",
            "SubMgr mantém uma assinatura ativa;",
            "contadores RMR e KPM aumentam;",
            "o valor DRB.UEThpDl muda com o estímulo;",
            "Prometheus descobre o ServiceMonitor/Service;",
            "Grafana mostra a série separada pelo label da xApp.",
        ]),
        callout("RUNNING NÃO BASTA", "Um pod Running prova apenas que o processo iniciou. A aceitação exige estímulo conhecido e resposta mensurável.", "amber"),
    ])

    chapter(story, "24", "Nephio e GitOps de ponta a ponta", "O pacote é preparado por intenção e entregue por reconciliação.", [
        GitOpsFlow(),
        p("Figura 6 · Pipeline declarativo da xApp na PoC.", CAPTION),
        h2("O papel de cada componente"),
        *bullets([
            "<b>Team Blueprint</b>: modelo reutilizável sem detalhes de um site;",
            "<b>PackageVariant</b>: intenção que especializa NMI ou CIC;",
            "<b>Porch</b>: orquestra revisões e transformação de pacotes;",
            "<b>Gitea</b>: armazena o pacote publicado;",
            "<b>Flux</b>: reconcilia o Git no workload cluster;",
            "<b>Kubernetes</b>: executa Deployment, Service e demais recursos.",
        ]),
        callout("ROLLBACK PARA FRENTE", "Em vez de apagar histórico, publicamos uma revisão posterior que restaura a configuração desejada.", "green"),
    ])

    chapter(story, "25", "Comparação objetiva das ferramentas", "A tabela abaixo evita sobreposição de responsabilidades.", [
        data_table(
            ["Ferramenta", "Pergunta", "Papel"],
            [
                ["Proxmox", "onde criar as VMs?", "virtualização"],
                ["Ansible", "como preparar hosts/cluster?", "provisionamento"],
                ["Kubernetes", "onde executar pods?", "runtime/reconciliação"],
                ["Helm", "como parametrizar YAML?", "templating/pacote"],
                ["Nephio/Porch", "qual variante vai para cada site?", "ciclo de pacotes"],
                ["Flux", "como aplicar o Git?", "reconciliador GitOps"],
                ["Rancher/OpenShift", "como administrar a plataforma?", "não usados"],
                ["RIC", "como interagir com a RAN via E2?", "plataforma telecom"],
            ],
            [33 * mm, 76 * mm, 60 * mm],
        ),
        callout("ATALHO", "Helm empacota templates; Nephio governa variantes; Flux sincroniza Git; Kubernetes executa; o RIC conversa com a RAN.", "blue"),
    ])

    chapter(story, "26", "Resultados comprovados", "A PoC possui uma cadeia de evidências, não apenas pods verdes.", [
        data_table(
            ["Evidência", "Resultado"],
            [
                ["Cluster NMI", "5/5 nós Ready, Kubernetes v1.30.14"],
                ["Cluster CIC", "2 nós ARM64 funcionais"],
                ["Open5GS", "três perfis de assinante e sessões testadas"],
                ["RAN/E2", "DU conectado ao Near-RT RIC"],
                ["simple-mon", "KPM no NMI e no CIC"],
                ["load-watch", "média móvel de 5 amostras e estados"],
                ["Tráfego", "50 MB; pico de 28.841 kbps"],
                ["GitOps", "3 Flux Kustomizations Ready"],
                ["Nephio", "2 WorkloadClusters e 3 PackageVariants"],
            ],
            [52 * mm, 117 * mm],
        ),
        callout("CICLO OBSERVADO", "idle → active → busy → active → idle durante o teste controlado de tráfego.", "amber"),
    ])

    chapter(story, "27", "Limitações atuais e agenda de pesquisa", "As limitações são conhecidas e úteis para formular os próximos experimentos.", [
        data_table(
            ["Hoje", "Consequência", "Próximo experimento"],
            [
                ["um peer ZMQ", "um perfil UE ativo por vez", "múltiplos UEs/RUs ou SDR"],
                ["KPM agregado", "sem atribuição direta ao IMSI", "Report Style/per-UE + correlação"],
                ["xApps monitoram", "sem ação de controle", "E2SM-RC + guardrails"],
                ["management no NMI", "dependência de um site", "estudo de placement/latência"],
                ["PoC sem HA", "falhas interrompem partes", "automação de recuperação didática"],
            ],
            [43 * mm, 56 * mm, 70 * mm],
        ),
        callout("DRB.UEThpDl STYLE 1", "Com noLabel=true, a medição é agregada no O-DU/célula. Ela prova carga de rádio, mas não diz que o valor pertence ao IMSI ...001, ...002 ou ...003.", "amber"),
        p("Para medir por UE será preciso suporte do E2 node a outro Report Style/label e correlacionar identificadores de RAN com a identidade do assinante no Core."),
    ])

    chapter(story, "28", "Pré-requisitos para reproduzir", "A reprodução começa com acesso e uma baseline saudável.", [
        *bullets([
            "VPN institucional do NMI ativa;",
            "conta SSH de laboratório e chave pública autorizada;",
            "clone atualizado do repositório;",
            "kubectl e KUBECONFIG apropriado;",
            "credenciais fornecidas separadamente/Secrets;",
            "permissão para usar os scripts de demo;",
            "janela de teste sem outro aluno alterando RAN/RIC.",
        ]),
        callout("NÃO PUBLIQUE SEGREDOS", "IPs privados podem aparecer na documentação do laboratório; senhas, tokens, chaves privadas, K e OPc não devem aparecer em commit ou PDF público.", "red"),
        h2("Clone"),
        code_block("""git clone https://github.com/lucasrodri/oran-stack.git
cd oran-stack
git status
git log -5 --oneline"""),
    ])

    chapter(story, "29", "Pré-voo do cluster", "Valide a infraestrutura antes de culpar a nova xApp.", [
        code_block("""kubectl get nodes -o wide
kubectl get namespaces
kubectl get pods -A -o wide
kubectl get svc -A
kubectl get events -A --sort-by=.lastTimestamp | tail -n 40"""),
        h2("Critério mínimo"),
        *bullets([
            "todos os nós esperados estão Ready;",
            "pods de 5g-core, ran, near-rt-ric e monitoring estão Ready;",
            "nenhum CrashLoopBackOff cresce continuamente;",
            "Services NodePort estão presentes;",
            "não há evento recente de falta de disco/memória.",
        ]),
        callout("PARE", "Se o baseline estiver quebrado, registre a evidência e trate a infraestrutura primeiro. Não modifique o algoritmo para compensar uma RAN desconectada.", "red"),
    ])

    chapter(story, "30", "Pré-voo do Core, RAN e RIC", "O experimento exige UE, sessão PDU e E2 node conectado.", [
        code_block("""kubectl -n 5g-core get pods
kubectl -n ran get pods -o wide
kubectl -n near-rt-ric get pods -o wide
curl -fsS http://127.0.0.1:30380/v1/nodeb/states"""),
        h2("Sinais de saúde"),
        *bullets([
            "Open5GS NFs e MongoDB estão Ready;",
            "O-CU, O-DU e srsUE estão Ready;",
            "UE conclui RRC e PDU Session;",
            "E2 node gnbd_* aparece CONNECTED;",
            "E2Term, E2Mgr, SubMgr, RTMgr e AppMgr estão Ready.",
        ]),
        callout("DEPENDÊNCIAS", "Uma xApp KPM depende de RAN + E2 + RIC. A WebUI do Open5GS, por sua vez, cuida dos assinantes e não prova a saúde do E2.", "amber"),
    ])

    chapter(story, "31", "Pré-voo do Nephio e Flux", "Nephio e Flux devem mostrar os objetos que representam NMI e CIC.", [
        code_block("""kubectl get workloadclusters.infra.nephio.org
kubectl get packagevariants.config.porch.kpt.dev
kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A"""),
        data_table(
            ["Objeto esperado", "Estado de referência"],
            [
                ["WorkloadCluster/nmi", "presente"],
                ["WorkloadCluster/cic", "presente"],
                ["PackageVariant/kpm-load-watch-nmi", "presente"],
                ["PackageVariant/simple-mon-nmi-v5", "presente"],
                ["PackageVariant/simple-mon-cic-arm64", "presente"],
                ["Flux Kustomizations", "Ready=True"],
            ],
            [75 * mm, 94 * mm],
        ),
        callout("INTERPRETAÇÃO", "PackageVariant presente não significa pod saudável. Confirme também o Flux e o Deployment no workload cluster.", "blue"),
    ])

    chapter(story, "32", "Comandos kubectl essenciais", "Os comandos abaixo cobrem 80% do diagnóstico inicial.", [
        code_block("""# inventário
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get svc -A

# detalhes
kubectl describe pod -n <namespace> <pod>
kubectl get deployment -n <namespace> <nome> -o yaml

# logs
kubectl logs -n <namespace> <pod> --tail=100
kubectl logs -n <namespace> deployment/<nome> --tail=100
kubectl logs -n <namespace> <pod> --previous --tail=100

# acompanhar
kubectl get pods -n ricxapp -w
kubectl rollout status -n ricxapp deployment/<nome> --timeout=180s"""),
        callout("CUIDADO", "get, describe e logs são consultas. apply, delete, rollout restart e scale alteram estado; use somente quando o roteiro autorizar.", "amber"),
    ])

    chapter(story, "33", "Acessar as interfaces", "Cada WebUI responde a uma pergunta diferente.", [
        data_table(
            ["Interface", "Pergunta"],
            [
                ["Open5GS WebUI", "quais assinantes/perfis existem?"],
                ["Nephio WebUI", "quais repositórios e pacotes estão publicados?"],
                ["Grafana Overview", "Core, RAN, RIC, xApps e nós estão saudáveis?"],
                ["Grafana Multi-site", "NMI e CIC recebem a mesma telemetria?"],
                ["Grafana Logs", "qual componente registrou erro?"],
                ["Alertmanager", "qual condição ultrapassou uma regra?"],
            ],
            [55 * mm, 114 * mm],
        ),
        callout("VPN", "Use os endereços privados pela VPN NMI. Tailscale foi ferramenta operacional temporária, não é a arquitetura oficial apresentada aos alunos.", "green"),
    ])

    chapter(story, "34", "Troubleshooting por cadeia", "Diagnostique do estímulo para a evidência, sem reiniciar tudo.", [
        data_table(
            ["Sintoma", "Primeiras verificações"],
            [
                ["UE não registra", "perfil Open5GS, K/OPc, RAN, AMF, RRC/NAS"],
                ["sem tun_srsue", "PDU Session, SMF/UPF, pool e DNN"],
                ["sem egress", "rota, NAT UPF, pfSense e interface correta"],
                ["E2 desconectado", "E2Term, SCTP, e2br, node ID e RTMgr"],
                ["xApp sem assinatura", "AppMgr, SubMgr, RAN function e período"],
                ["KPM zero", "tráfego real, métrica implementada e labels"],
                ["Grafana No data", "ServiceMonitor, target Prometheus e consulta"],
                ["Flux não Ready", "GitRepository, path, RBAC e YAML inválido"],
            ],
            [52 * mm, 117 * mm],
        ),
        callout("MÉTODO", "Mude uma variável por vez, limite logs, preserve a evidência anterior e registre a hipótese no relatório.", "green"),
    ])

    chapter(story, "35", "Começar uma nova xApp pela pergunta", "Um experimento bom nasce de uma hipótese, não de um Deployment.", [
        h2("Exemplo de pergunta"),
        p("“Uma média móvel de DRB.UEThpDl consegue classificar a carga da RAN em idle, active e busy durante um estímulo controlado?”"),
        data_table(
            ["Elemento", "Definição"],
            [
                ["Entrada", "DRB.UEThpDl a cada 3000 ms"],
                ["Transformação", "média móvel de cinco amostras"],
                ["Saída", "estado 0/1/2 + valor médio"],
                ["Estímulo", "transferência de 50 MB pela tun_srsue"],
                ["Aceite", "ciclo idle → active → busy → active → idle"],
            ],
            [50 * mm, 119 * mm],
        ),
        callout("ANTES DE PROGRAMAR", "Defina métrica, período, janela, limiares, estímulo e evidência. Isso evita uma xApp que “roda” mas não responde a uma pergunta.", "amber"),
    ])

    chapter(story, "36", "Gerar o scaffold", "O gerador cria código, pacote e objetos de onboarding coerentes.", [
        code_block("""git switch main
git pull --ff-only
git switch -c aluno/kpm-latency-lab

./scripts/new-kpm-xapp.sh kpm-latency-lab DRB.UEThpDl 2000"""),
        data_table(
            ["Artefato", "Finalidade"],
            [
                ["xapps/python/kpm_latency_lab_xapp.py", "algoritmo"],
                ["packages/nephio/kpm-latency-lab", "Team Blueprint"],
                ["infra/nephio/blueprints/*variant.yaml", "variante NMI"],
                ["infra/nephio/nmi-onboarding/*rbac.yaml", "permissões"],
                ["infra/nephio/nmi-onboarding/*flux-sync.yaml", "reconciliação"],
            ],
            [91 * mm, 78 * mm],
        ),
        callout("NOME", "Use letras minúsculas, números e hífens. O gerador não deve sobrescrever uma xApp existente.", "green"),
    ])

    chapter(story, "37", "Programar o callback", "xAppBase abstrai a plataforma; o aluno implementa a transformação da medição.", [
        code_block("""def indication_callback(self, e2_agent_id, subscription_id,
                        indication_header, indication_message):
    measurements = self.e2sm_kpm.extract_meas_data(indication_message)
    value = measurements.get("measData", {}).get("DRB.UEThpDl", 0)

    self.window.append(float(value or 0))
    average = sum(self.window) / len(self.window)
    state = "busy" if average >= 20000 else \
            "active" if average >= 1000 else "idle"
    self.export_state(average, state)"""),
        h2("Boas práticas"),
        *bullets([
            "callback rápido e não bloqueante;",
            "validação de valor ausente/não numérico;",
            "logs apenas em transição ou amostrados;",
            "métricas com labels controlados;",
            "estado interno pequeno e testável;",
            "sem credenciais no código.",
        ]),
    ])

    chapter(story, "38", "Testar antes do cluster", "A maioria dos erros simples deve falhar na máquina do aluno ou na CI.", [
        code_block("""python3 -m py_compile xapps/python/kpm_latency_lab_xapp.py
python3 -m unittest discover -s tests -v
bash -n scripts/new-kpm-xapp.sh
git diff --check

rg 'REPLACE_WITH_MULTIARCH_IMAGE_DIGEST|:latest' \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml"""),
        callout("ACEITE LOCAL", "Código compila, testes passam, shell é válido, não há whitespace quebrado e nenhum marcador de imagem permanece antes da publicação.", "green"),
        h2("Teste de unidade útil"),
        p("Alimente o algoritmo com uma sequência sintética de valores e verifique transições e média. Esse teste independe do RIC e reduz o tempo de diagnóstico no cluster."),
    ])

    chapter(story, "39", "Publicar uma imagem multiarch", "A mesma referência imutável deve atender amd64 e arm64.", [
        p("A CI constrói um índice OCI com linux/amd64 e linux/arm64. O pacote deve usar o digest do índice, não <b>:latest</b> e não o digest de uma única plataforma."),
        code_block("""git add xapps/python/kpm_latency_lab_xapp.py \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml \
  infra/nephio/nmi-onboarding/kpm-latency-lab-*.yaml

git commit -m "feat(xapp): add kpm latency lab monitor"
git push -u origin aluno/kpm-latency-lab"""),
        callout("IMUTABILIDADE", "Digest permite provar exatamente qual conjunto de bytes foi executado nos dois sites.", "violet"),
        h2("Referência esperada"),
        code_block("ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:<digest-do-indice>"),
    ])

    chapter(story, "40", "Publicar blueprint e variante", "O Team Blueprint vira um pacote específico do NMI por meio do PackageVariant.", [
        GitOpsFlow(),
        code_block("""export KUBECONFIG=/etc/nephio/nmi-admin.conf

sudo -E ./infra/nephio/blueprints/publish-xapp-blueprint.sh \
  kpm-latency-lab packages/nephio/kpm-latency-lab v1

sudo -E kubectl apply -f \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml

sudo -E ./infra/nephio/blueprints/approve-packagevariant.sh \
  kpm-latency-lab-nmi"""),
        callout("O QUE O NEPHIO FEZ", "Publicou e especializou configuração. Ele ainda não iniciou o processo da xApp; isso acontece depois da reconciliação no Kubernetes.", "green"),
    ])

    chapter(story, "41", "Entregar pelo Flux e aceitar", "A reconciliação deve resultar em workload funcional, não apenas em Git atualizado.", [
        code_block("""sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-rbac.yaml
sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-flux-sync.yaml

sudo -E kubectl -n flux-system wait \
  kustomization/kpm-latency-lab \
  --for=condition=Ready --timeout=300s

kubectl -n ricxapp rollout status \
  deployment/kpm-latency-lab --timeout=180s"""),
        h2("Aceite da plataforma"),
        *bullets([
            "Flux Ready=True e revisão Git esperada;",
            "Deployment disponível;",
            "pod Ready sem restart crescente;",
            "Service e /metrics acessíveis;",
            "AppMgr e SubMgr reconhecem a xApp;",
            "contadores RMR/KPM aumentam.",
        ]),
    ])

    chapter(story, "42", "Estimular, observar, atualizar e reverter", "O experimento termina com evidência e histórico.", [
        code_block("""sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  XAPP_DEPLOYMENT=kpm-latency-lab ./scripts/demo-kpm.sh

# referência didática
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-load-watch.sh"""),
        h2("O que observar"),
        *bullets([
            "assinatura ativa = 1;",
            "taxa de indicações > 0;",
            "pico de DRB.UEThpDl durante a transferência;",
            "retorno próximo de zero depois do estímulo;",
            "estado/transições coerentes com os limiares.",
        ]),
        h2("Update e rollback"),
        p("Altere um parâmetro ou versão do blueprint, publique a revisão seguinte, espere o Flux reconciliar e repita o teste. Para reverter, publique uma nova revisão que restaure os valores anteriores."),
        callout("RELATÓRIO", "Registre hipótese, versão/digest, parâmetros, horário, estímulo, gráfico, resultado e limitações. Isso transforma uma demo em experimento.", "green"),
    ])

    story += [
        h1("A", "Glossário rápido"),
        data_table(
            ["Termo", "Definição"],
            [
                ["5G Core", "núcleo que registra assinantes e transporta sessões"],
                ["AMF", "função de acesso e mobilidade"],
                ["SMF", "função de gestão de sessão"],
                ["UPF", "plano de usuário e egress"],
                ["RAN", "rede de acesso por rádio"],
                ["O-DU / O-CU", "funções distribuída e centralizada da RAN"],
                ["Near-RT RIC", "plataforma de controle/telemetria da RAN"],
                ["xApp", "aplicação executada junto ao Near-RT RIC"],
                ["E2", "interface entre E2 node e Near-RT RIC"],
                ["E2SM-KPM", "modelo de serviço para medições"],
                ["KPI", "indicador de desempenho"],
                ["RMR", "mensageria interna do RIC"],
                ["GitOps", "reconciliação de estado desejado a partir do Git"],
                ["Porch", "orquestração de pacotes kpt/KRM"],
                ["PackageVariant", "especialização declarativa de um pacote"],
                ["Flux", "reconciliador GitOps"],
            ],
            [43 * mm, 126 * mm],
        ),
        PageBreak(),

        h1("B", "Folha de consulta kubectl"),
        code_block("""kubectl get nodes -o wide
kubectl get ns
kubectl get pods -A -o wide
kubectl get svc -A
kubectl get deploy -A
kubectl get events -A --sort-by=.lastTimestamp

kubectl describe pod -n <ns> <pod>
kubectl logs -n <ns> <pod> --tail=100
kubectl logs -n <ns> <pod> --previous --tail=100
kubectl exec -n <ns> -it <pod> -- /bin/sh

kubectl rollout status -n <ns> deployment/<nome>
kubectl rollout history -n <ns> deployment/<nome>

kubectl get workloadclusters.infra.nephio.org
kubectl get packagevariants.config.porch.kpt.dev
kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A"""),
        callout("CONSULTA ANTES DE MUDANÇA", "Use get/describe/logs para localizar a camada da falha. Não reinicie toda a pilha como primeira resposta.", "amber"),
        PageBreak(),

        h1("C", "Roteiro de demonstração em 10 minutos"),
        data_table(
            ["Tempo", "Ação", "Mensagem"],
            [
                ["00–02", "mostrar topologia e nós", "5 nós NMI + 2 nós ARM"],
                ["02–04", "abrir Open5GS", "assinantes e sessão são do Core"],
                ["04–06", "abrir Nephio", "blueprint + variantes NMI/CIC"],
                ["06–08", "executar estímulo UE", "50 MB atravessam a rede 5G"],
                ["08–10", "abrir Grafana", "KPM e estados comprovam o efeito"],
            ],
            [24 * mm, 58 * mm, 87 * mm],
        ),
        callout("FRASE FINAL", "Código no Git virou pacote por site, pod em duas arquiteturas e evidência de rádio no Grafana.", "green"),
        PageBreak(),

        h1("D", "Checklist do relatório do aluno"),
        *bullets([
            "[ ] pergunta de pesquisa e hipótese;",
            "[ ] arquitetura e versão do cluster;",
            "[ ] nome da xApp, branch, commit e digest;",
            "[ ] métrica, período, janela e limiares;",
            "[ ] PackageVariant e revisão Flux;",
            "[ ] perfil UE e estímulo aplicado;",
            "[ ] gráfico antes/durante/depois;",
            "[ ] logs apenas dos eventos relevantes;",
            "[ ] resultado esperado versus observado;",
            "[ ] limitações e ameaça à validade;",
            "[ ] proposta do próximo experimento.",
        ]),
        callout("CRITÉRIO", "O leitor deve conseguir repetir o estímulo e verificar se obtém a mesma tendência, mesmo que os valores exatos variem.", "blue"),
        PageBreak(),

        h1("E", "Referências e fontes"),
        p("Este guia combina documentação oficial com o estado observado e os arquivos versionados da PoC."),
        h2("Documentação oficial"),
        *bullets([
            "Kubernetes Concepts: https://kubernetes.io/docs/concepts/",
            "Kubernetes Objects: https://kubernetes.io/docs/concepts/overview/working-with-objects/",
            "Kubernetes Namespaces: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/",
            "Kubernetes Pods: https://kubernetes.io/docs/concepts/workloads/pods/",
            "Kubernetes Services: https://kubernetes.io/docs/concepts/services-networking/service/",
            "Nephio documentation: https://docs.nephio.org/docs/",
            "Nephio Porch: https://docs.nephio.org/docs/porch/",
            "O-RAN Alliance: https://www.o-ran.org/",
        ]),
        h2("Fontes do repositório"),
        *bullets([
            "README.md;",
            "docs/STATUS.md;",
            "docs/NMI_DEPLOYMENT.md;",
            "docs/CIC_ARM_CLUSTER.md;",
            "docs/OBSERVABILITY.md;",
            "docs/STUDENT_XAPP_LAB.md;",
            "docs/UE_SIMULATION_LAB.md;",
            "packages/nephio/ e infra/nephio/;",
            "snapshot kubectl do cluster NMI em 1º de setembro de 2026.",
        ]),
        callout("VERSÃO", "O ambiente é uma bancada viva. Antes de uma aula, confirme STATUS.md, os nós Ready e as revisões Flux em uso.", "amber"),
    ]

    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = GuideDocTemplate(str(OUTPUT))
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
