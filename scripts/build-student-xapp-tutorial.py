#!/usr/bin/env python3
"""Build the student-facing Open RAN/Nephio laboratory tutorial PDF."""

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
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Flowable,
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
OUTPUT = ROOT / "output/pdf/tutorial-aluno-xapp-nephio-openran-unb.pdf"
CONFIG = ROOT / "infra/nephio/webui-compat/unb-configmap.yaml"

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 19 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

UNB_BLUE = colors.HexColor("#0B3E75")
UNB_GREEN = colors.HexColor("#087C3A")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#5D6975")
SOFT = colors.HexColor("#EDF2F6")
PALE_BLUE = colors.HexColor("#EAF2FA")
PALE_GREEN = colors.HexColor("#E8F4ED")
PALE_AMBER = colors.HexColor("#FFF4D6")
AMBER = colors.HexColor("#B26A00")
RED = colors.HexColor("#A33A32")
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
    fontSize=9.4,
    leading=13.2,
    textColor=INK,
    spaceAfter=5.5,
)
LEAD = ParagraphStyle(
    "Lead",
    parent=BODY,
    fontSize=11.1,
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
    fontSize=10.2,
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
    fontSize=7.15,
    leading=9.5,
    leftIndent=6,
    rightIndent=6,
    borderColor=colors.HexColor("#CBD5DE"),
    borderWidth=0.5,
    borderPadding=7,
    backColor=colors.HexColor("#F5F7F9"),
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
    borderWidth=0,
    spaceBefore=4,
    spaceAfter=7,
)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def bullet(text: str) -> Paragraph:
    return Paragraph(text, BULLET, bulletText="•")


def bullets(items: list[str]) -> list[Paragraph]:
    return [bullet(item) for item in items]


def h1(number: str, title: str) -> Paragraph:
    return p(f'<font color="#087C3A">{number}</font>  {title}', H1)


def h2(title: str) -> Paragraph:
    return p(title, H2)


def h3(title: str) -> Paragraph:
    return p(title, H3)


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
        "amber": (PALE_AMBER, AMBER),
        "red": (colors.HexColor("#FBECEB"), RED),
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


class LabTopology(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 116 * mm

    def box(self, x, y, w, h, title, lines, color):
        c = self.canv
        c.setFillColor(colors.white)
        c.setStrokeColor(color)
        c.setLineWidth(1.3)
        c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(x, y + h - 18, w, 18, fill=1, stroke=0)
        c.setFont("Arial-Bold", 8.5)
        c.setFillColor(colors.white)
        c.drawString(x + 7, y + h - 13, title)
        c.setFont("Arial", 7.2)
        c.setFillColor(INK)
        line_y = y + h - 31
        for line in lines:
            c.drawString(x + 7, line_y, line)
            line_y -= 11

    def arrow(self, x1, y1, x2, y2, label=""):
        c = self.canv
        c.setStrokeColor(MUTED)
        c.setLineWidth(1.2)
        c.line(x1, y1, x2, y2)
        angle = 4
        if x2 >= x1:
            c.line(x2, y2, x2 - 6, y2 + angle)
            c.line(x2, y2, x2 - 6, y2 - angle)
        else:
            c.line(x2, y2, x2 + 6, y2 + angle)
            c.line(x2, y2, x2 + 6, y2 - angle)
        if label:
            c.setFont("Arial", 6.6)
            c.setFillColor(MUTED)
            c.drawCentredString((x1 + x2) / 2, y1 + 5, label)

    def draw(self):
        c = self.canv
        c.setFont("Arial-Bold", 11)
        c.setFillColor(UNB_BLUE)
        c.drawString(0, 316, "Topologia didática multi-site")
        self.box(0, 230, 92, 65, "ALUNO / VPN NMI", ["Git + código Python", "WebUI Nephio", "Grafana / logs"], UNB_GREEN)
        self.box(113, 196, 252, 112, "NMI - CLUSTER AMD64", ["control plane + workers", "Open5GS + UE/RAN ZMQ", "Near-RT RIC + xApps", "Prometheus / Grafana / Loki", "Nephio, Porch, Gitea e Flux"], UNB_BLUE)
        self.box(386, 212, 123, 82, "CIC - CLUSTER ARM64", ["Ampere 2 + Ampere 3", "Flux mínimo", "xApp arm64", "telemetria ao NMI"], UNB_GREEN)
        self.arrow(92, 262, 113, 262, "VPN")
        self.arrow(365, 264, 386, 264, "rede privada")

        self.box(113, 96, 112, 72, "CAMINHO 5G", ["srsUE -> ZMQ", "O-DU / O-CU", "Open5GS / UPF"], colors.HexColor("#5A4EA3"))
        self.box(253, 96, 112, 72, "CAMINHO E2", ["E2Term / E2Mgr", "SubMgr / RTMgr", "KPM -> xApp"], colors.HexColor("#C45D21"))
        self.box(386, 96, 123, 72, "OBSERVABILIDADE", ["/metrics", "Prometheus", "Grafana + Loki"], colors.HexColor("#54707A"))
        self.arrow(225, 132, 253, 132, "E2 SCTP")
        self.arrow(365, 132, 386, 132, "métricas")
        self.arrow(309, 196, 309, 168, "workloads")

        c.setFont("Arial", 7.2)
        c.setFillColor(MUTED)
        c.drawString(0, 54, "Plano de gestão: Git -> Porch -> Gitea -> Flux -> Kubernetes")
        c.drawString(0, 41, "Plano de dados: UE -> RAN -> UPF -> Internet")
        c.drawString(0, 28, "Plano de controle/telemetria: O-DU -> E2 -> Near-RT RIC -> xApp -> Grafana")


class GitOpsFlow(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 50 * mm

    def draw(self):
        c = self.canv
        labels = ["Código", "Imagem\nmultiarch", "Team\nBlueprint", "Package\nVariant", "Porch", "Gitea", "Flux", "xApp"]
        box_w = 53
        gap = 9
        x = 0
        for index, label in enumerate(labels):
            color = UNB_GREEN if index in (0, 7) else UNB_BLUE
            c.setFillColor(colors.white)
            c.setStrokeColor(color)
            c.setLineWidth(1.1)
            c.roundRect(x, 72, box_w, 37, 5, fill=1, stroke=1)
            c.setFillColor(color)
            c.setFont("Arial-Bold", 7.3)
            lines = label.split("\n")
            for line_index, line in enumerate(lines):
                c.drawCentredString(x + box_w / 2, 94 - line_index * 10, line)
            if index < len(labels) - 1:
                c.setStrokeColor(MUTED)
                c.line(x + box_w, 90, x + box_w + gap - 2, 90)
                c.line(x + box_w + gap - 2, 90, x + box_w + gap - 7, 94)
                c.line(x + box_w + gap - 2, 90, x + box_w + gap - 7, 86)
            x += box_w + gap
        c.setFont("Arial", 7.2)
        c.setFillColor(MUTED)
        c.drawString(0, 46, "O aluno produz código, teste, imagem e blueprint.")
        c.drawString(0, 32, "A infraestrutura aprova publicação, RBAC, portas e variantes remotas.")
        c.drawString(0, 18, "Nephio renderiza configuração; Flux realiza a entrega no cluster escolhido.")


class SignalPath(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_W
        self.height = 51 * mm

    def draw(self):
        c = self.canv
        columns = [
            ("UE", "srsUE\nperfil IMSI"),
            ("RAN", "ZMQ\nDU/CU"),
            ("RIC", "E2Term\nSubMgr"),
            ("xApp", "callback\nalgoritmo"),
            ("OBS", "Prometheus\nGrafana"),
        ]
        box_w, gap, y = 82, 18, 74
        for idx, (title, subtitle) in enumerate(columns):
            x = idx * (box_w + gap)
            color = [UNB_GREEN, colors.HexColor("#5A4EA3"), colors.HexColor("#C45D21"), UNB_BLUE, colors.HexColor("#54707A")][idx]
            c.setFillColor(colors.white)
            c.setStrokeColor(color)
            c.setLineWidth(1.2)
            c.roundRect(x, y, box_w, 48, 6, fill=1, stroke=1)
            c.setFont("Arial-Bold", 8.5)
            c.setFillColor(color)
            c.drawCentredString(x + box_w / 2, y + 32, title)
            c.setFont("Arial", 7.2)
            c.setFillColor(INK)
            for line_index, line in enumerate(subtitle.split("\n")):
                c.drawCentredString(x + box_w / 2, y + 19 - line_index * 9, line)
            if idx < len(columns) - 1:
                c.setStrokeColor(MUTED)
                c.line(x + box_w, y + 24, x + box_w + gap - 2, y + 24)
                c.line(x + box_w + gap - 2, y + 24, x + box_w + gap - 7, y + 28)
                c.line(x + box_w + gap - 2, y + 24, x + box_w + gap - 7, y + 20)
        c.setFont("Arial", 7.2)
        c.setFillColor(MUTED)
        c.drawString(0, 48, "A autenticação do assinante acontece no Open5GS; a xApp não cadastra SIM.")
        c.drawString(0, 33, "O KPI DRB.UEThpDl é medido no O-DU e chega à xApp como indicação E2SM-KPM.")
        c.drawString(0, 18, "O teste gera tráfego no tun_srsue e observa a mudança no dashboard.")


class TutorialDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Tutorial do aluno - xApp KPM, Nephio e Open RAN UnB",
            author="Laboratório Open RAN - Universidade de Brasília",
            subject="Roteiro didático para criação, entrega e teste de xApps KPM",
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
        self.addPageTemplates(PageTemplate(id="tutorial", frames=[frame], onPage=self.draw_page))

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
            canvas.drawString(MARGIN_X, PAGE_H - 9.2 * mm, "LABORATÓRIO OPEN RAN - UnB")
            canvas.setFont("Arial", 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 9.2 * mm, "Tutorial do aluno | xApp KPM + Nephio")
            canvas.line(MARGIN_X, 11 * mm, PAGE_W - MARGIN_X, 11 * mm)
            canvas.setFont("Arial", 7.2)
            canvas.drawString(MARGIN_X, 7.5 * mm, "PoC acadêmica - ambiente de laboratório")
            canvas.drawRightString(PAGE_W - MARGIN_X, 7.5 * mm, f"página {page}")
        canvas.restoreState()


def cover_story() -> list:
    logo = Image(BytesIO(LOGO_BYTES), width=31 * mm, height=27.3 * mm)
    title_style = ParagraphStyle(
        "CoverTitle",
        fontName="Arial-Bold",
        fontSize=28,
        leading=32,
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        fontName="Arial",
        fontSize=14,
        leading=19,
        textColor=colors.HexColor("#DCEAF7"),
        alignment=TA_LEFT,
    )
    meta_style = ParagraphStyle(
        "CoverMeta",
        fontName="Arial",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#DCEAF7"),
    )
    return [
        Spacer(1, 6 * mm),
        logo,
        Spacer(1, 32 * mm),
        p("TUTORIAL DO ALUNO", ParagraphStyle("Kicker", parent=SMALL, fontName="Arial-Bold", fontSize=10, textColor=colors.HexColor("#9AD0AE"), leading=13)),
        p("Criando e entregando uma xApp KPM com Nephio", title_style),
        p("Da ideia ao KPI no Grafana, com deploy no NMI e experimento ARM no CIC.", subtitle_style),
        Spacer(1, 31 * mm),
        callout("OBJETIVO", "Ensinar o aluno a programar, empacotar, implantar, estimular e avaliar uma xApp de monitoramento em uma Open RAN de laboratório.", "green"),
        Spacer(1, 12 * mm),
        p("NMI + CIC | PoC acadêmica | versão 1.0 | 31 de agosto de 2026", meta_style),
        p("Repositório: github.com/lucasrodri/oran-stack", meta_style),
        PageBreak(),
    ]


def build_story() -> list:
    story: list = []
    story.extend(cover_story())

    story += [
        h1("0", "Como usar este tutorial"),
        p("Este roteiro é um laboratório guiado, não um manual de produção. Ele parte de uma pilha Open RAN já implantada e saudável e leva o aluno até uma xApp KPM observável e entregue por GitOps."),
        callout("TEMPO ESPERADO", "60 a 90 minutos quando a infraestrutura base, a CI e as credenciais já estão prontas.", "blue"),
        h2("Resultado final"),
        *bullets([
            "uma xApp Python com um algoritmo pequeno e mensurável;",
            "uma imagem imutável compatível com <b>amd64</b> e <b>arm64</b>;",
            "um Team Blueprint e uma variante NMI publicados pelo Nephio/Porch;",
            "um Deployment entregue pelo Flux com identidade restrita;",
            "um experimento reproduzível de tráfego do UE e evidência no Grafana;",
            "uma atualização e um rollback para frente, sem apagar histórico.",
        ]),
        h2("Mapa do roteiro"),
        data_table(
            ["Etapa", "O que acontece", "Responsável principal"],
            [
                ["1-3", "entender arquitetura, validar base e gerar scaffold", "aluno"],
                ["4-5", "programar, testar e publicar imagem", "aluno + CI"],
                ["6-7", "publicar pacote e entregar pelo Flux", "aluno assistido + infra"],
                ["8-9", "validar KPM e estimular UE", "aluno"],
                ["10", "variante ARM e bridges RMR", "infra assistindo o aluno"],
                ["11-13", "update, rollback, diagnóstico e relatório", "aluno"],
            ],
            [25 * mm, 93 * mm, 51 * mm],
        ),
        Spacer(1, 6 * mm),
        callout("REGRA DO LABORATÓRIO", "Se RAN, E2 ou UE não estão saudáveis, pare. Não trate uma falha da pilha base como defeito da nova xApp.", "amber"),
        PageBreak(),

        h1("1", "Arquitetura do laboratório"),
        p("A PoC usa dois clusters porque há duas arquiteturas de CPU e dois locais físicos. O NMI concentra a pilha de telecom, o management plane Nephio e a observabilidade. O CIC executa workloads ARM e recebe configuração pelo Flux."),
        LabTopology(),
        p("Figura 1 - Topologia lógica da PoC acadêmica NMI/CIC.", CAPTION),
        data_table(
            ["Site", "Arquitetura", "Papel no laboratório"],
            [
                ["NMI", "amd64", "Open5GS, RAN/UE ZMQ, Near-RT RIC, observabilidade, Nephio/Porch/Gitea e xApps locais"],
                ["CIC", "arm64", "cluster Ampere, Flux mínimo, xApps remotas e telemetria enviada ao NMI"],
            ],
            [28 * mm, 32 * mm, 109 * mm],
        ),
        PageBreak(),

        h1("2", "Modelo mental: quem faz o quê"),
        SignalPath(),
        p("Figura 2 - Caminhos independentes de autenticação, rádio, telemetria e observabilidade.", CAPTION),
        h2("UE, SIM e Open5GS"),
        p("O UE representa o aparelho. O IMSI identifica o assinante/SIM e é provisionado no Open5GS com suas credenciais de autenticação. O IMEI identifica o equipamento. A xApp não cadastra SIM, não autentica UE e não substitui o Core."),
        h2("KPI, KPM e xApp"),
        p("<b>KPI</b> é um indicador de desempenho. <b>KPM</b> é o serviço E2 que transporta medições da RAN. A xApp assina uma métrica, recebe indicações pelo RMR, executa o algoritmo do aluno e expõe séries Prometheus."),
        h2("Nephio não é Helm nem Rancher"),
        p("Nephio gerencia pacotes declarativos e suas variantes por site. Porch publica revisões; Gitea guarda a configuração resultante; Flux aplica essa configuração no cluster. Kubernetes continua executando os pods, e o RIC continua cuidando das funções E2/RMR."),
        callout("NESTA POC", "Nephio roda em namespaces próprios no cluster NMI, agendado no worker nephio-k8s-w01. Ele não é um segundo cluster Kubernetes.", "green"),
        PageBreak(),

        h1("3", "Pré-voo: validar a pilha antes de programar"),
        p("Conecte a VPN NMI, atualize sua branch a partir de <b>main</b> e use um nome DNS seguro, com letras minúsculas, números e hífens."),
        h2("Acesso inicial"),
        code_block("""ssh aluno@192.168.72.10
sudo kubectl get nodes -o wide
sudo kubectl -n near-rt-ric get pods
sudo kubectl -n ran get pods
curl -fsS http://127.0.0.1:30380/v1/nodeb/states"""),
        h2("Critérios mínimos"),
        *bullets([
            "E2Term, E2Mgr, SubMgr, RTMgr e AppMgr estão Ready;",
            "o nó <b>gnbd_001_001_00019b_e2</b> aparece como CONNECTED;",
            "O-DU, O-CU e srsUE estão Ready;",
            "a interface <b>tun_srsue</b> possui endereço;",
            "Prometheus e Grafana estão acessíveis.",
        ]),
        h2("Interfaces pela VPN"),
        data_table(
            ["Serviço", "URL"],
            [
                ["Nephio WebUI", "http://192.168.71.30:30707/config-as-data"],
                ["Grafana - visão geral", "http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview"],
                ["Grafana - logs", "http://192.168.72.10:30300/d/oran-logs/o-ran-kubernetes-logs"],
                ["Alertmanager", "http://192.168.72.10:30301"],
            ],
            [48 * mm, 121 * mm],
        ),
        callout("PARE AQUI SE", "o E2 node estiver DISCONNECTED, o UE não tiver tun_srsue ou os contadores da xApp de referência estiverem congelados.", "red"),
        PageBreak(),

        h1("4", "Gerar a nova xApp"),
        p("O gerador cria o ponto de entrada Python, o pacote reutilizável Nephio, a variante NMI e a identidade Flux. Ele se recusa a sobrescrever uma xApp existente."),
        code_block("""git switch main
git pull --ff-only
git switch -c aluno/kpm-latency-lab

./scripts/new-kpm-xapp.sh kpm-latency-lab DRB.UEThpDl 2000"""),
        h2("Artefatos criados"),
        data_table(
            ["Caminho", "Finalidade"],
            [
                ["xapps/python/kpm_latency_lab_xapp.py", "código executado no container"],
                ["packages/nephio/kpm-latency-lab/", "Team Blueprint reutilizável"],
                ["infra/nephio/blueprints/*-nmi-variant.yaml", "especialização para o NMI"],
                ["infra/nephio/nmi-onboarding/*-rbac.yaml", "permissões restritas da entrega"],
                ["infra/nephio/nmi-onboarding/*-flux-sync.yaml", "reconciliação GitOps"],
            ],
            [91 * mm, 78 * mm],
        ),
        h2("Escolher métrica e período"),
        p("O primeiro laboratório usa <b>DRB.UEThpDl</b>, throughput downlink observado no O-DU. Use um período diferente de outra xApp concorrente que peça a mesma métrica. Solicitações idênticas podem ser fundidas pelo SubMgr."),
        callout("EXEMPLO", "r4-simple-mon NMI usa 1000 ms, simple-mon CIC usa 2000 ms e kpm-load-watch usa 3000 ms.", "blue"),
        PageBreak(),

        h1("5", "Programar e testar o comportamento"),
        p("O ponto de extensão é <b>indication_callback</b>. xAppBase já cuida do registro no AppMgr, assinatura no SubMgr, loop RMR, decodificação KPM e métricas Prometheus."),
        h2("Exemplo de algoritmo seguro"),
        code_block("""def indication_callback(self, e2_agent_id, subscription_id,
                        indication_header, indication_message):
    measurements = self.e2sm_kpm.extract_meas_data(indication_message)
    value = measurements.get("measData", {}).get("DRB.UEThpDl", 0)

    self.window.append(float(value or 0))
    average = sum(self.window) / len(self.window)
    state = "busy" if average >= 20000 else \
            "active" if average >= 1000 else "idle"
    self.export_state(average, state)"""),
        callout("BOA PRÁTICA", "Mantenha o callback rápido e não bloqueante. Exporte valores em /metrics e limite os logs; não escreva uma linha para cada indicação.", "green"),
        h2("Métricas padrão já disponíveis"),
        *bullets([
            "oran_xapp_active_subscriptions;",
            "oran_xapp_rmr_indications_total;",
            "oran_xapp_kpm_indications_total;",
            "oran_xapp_kpm_measurement;",
            "oran_kpm_drb_ue_throughput_dl_kbps para DRB.UEThpDl.",
        ]),
        h2("Validação local"),
        code_block("""python3 -m py_compile xapps/python/kpm_latency_lab_xapp.py
python3 -m unittest discover -s tests -v
bash -n scripts/new-kpm-xapp.sh
git diff --check

rg 'REPLACE_WITH_MULTIARCH_IMAGE_DIGEST' \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml"""),
        PageBreak(),

        h1("6", "Construir a imagem multiarch"),
        p("O Dockerfile comum inclui toda a pasta xapps/python. O aluno não precisa criar um Dockerfile por xApp. Depois do push, a CI deve publicar um índice com as plataformas linux/amd64 e linux/arm64."),
        code_block("""git add xapps/python/kpm_latency_lab_xapp.py \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml \
  infra/nephio/nmi-onboarding/kpm-latency-lab-*.yaml

git commit -m "feat(xapp): add kpm latency lab monitor"
git push -u origin aluno/kpm-latency-lab"""),
        h2("Fixar pelo digest do índice"),
        p("Nunca use <b>:latest</b> e não copie o digest de apenas uma arquitetura. A referência deve apontar para o índice multiarch imutável."),
        code_block("""IMAGE='ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:<digest>'

# Substitua o marcador nos dois arquivos gerados:
# packages/nephio/kpm-latency-lab/workload-cluster.yaml
# infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml

rg 'REPLACE_WITH|:latest' packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml"""),
        callout("ACEITE", "O último comando não retorna nada, e a CI confirma amd64 + arm64 para o mesmo digest do índice.", "blue"),
        PageBreak(),

        h1("7", "Publicar com Nephio e entregar com Flux"),
        GitOpsFlow(),
        p("Figura 3 - Pipeline declarativo usado na PoC.", CAPTION),
        h2("No worker Nephio"),
        code_block("""ssh -J aluno@192.168.72.10 aluno@192.168.71.30
cd /caminho/para/oran-stack
export KUBECONFIG=/etc/nephio/nmi-admin.conf

sudo -E ./infra/nephio/blueprints/publish-xapp-blueprint.sh \
  kpm-latency-lab packages/nephio/kpm-latency-lab v1

sudo -E kubectl apply -f \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml

sudo -E ./infra/nephio/blueprints/approve-packagevariant.sh \
  kpm-latency-lab-nmi"""),
        h2("Iniciar a reconciliação"),
        code_block("""sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-rbac.yaml
sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-flux-sync.yaml

sudo -E kubectl -n flux-system wait \
  kustomization/kpm-latency-lab \
  --for=condition=Ready --timeout=300s"""),
        callout("O QUE O NEPHIO FEZ", "Blueprint + intenção de site produziram um pacote NMI publicado. O Porch não executou a xApp; o Flux aplicou o pacote no Kubernetes.", "green"),
        PageBreak(),

        h1("8", "Aceite funcional da xApp"),
        p("Uma xApp não está aceita apenas porque o pod está Running. É preciso provar registro, assinatura, recebimento RMR, decodificação KPM e observabilidade."),
        code_block("""sudo kubectl -n ricxapp rollout status \
  deployment/kpm-latency-lab --timeout=180s

sudo kubectl -n ricxapp get pod,service \
  -l app=kpm-latency-lab -o wide

curl -fsS http://127.0.0.1:30080/ric/v1/xapps | \
  grep -F 'kpm-latency-lab'

sudo kubectl -n ricxapp exec deployment/kpm-latency-lab \
  -c xapp -- curl -fsS http://127.0.0.1:8091/metrics | \
  grep -E '^oran_xapp_(active_subscriptions|rmr_indications_total|kpm_indications_total)'"""),
        h2("Checklist de aceite"),
        *bullets([
            "[ ] pod Ready, sem aumento contínuo de restarts;",
            "[ ] AppMgr lista o endpoint RMR correto;",
            "[ ] active_subscriptions = 1;",
            "[ ] contadores RMR e KPM aumentam entre duas leituras;",
            "[ ] RMR_FLAGS=1 e um único listener TCP em 4561;",
            "[ ] Prometheus descobre o Service com monitoring=true;",
            "[ ] Grafana separa a série pelo label service.",
        ]),
        callout("IMPORTANTE", "Running prova apenas que o processo iniciou. O aceite científico exige um estímulo conhecido e uma resposta mensurável.", "amber"),
        PageBreak(),

        h1("9", "Gerar tráfego e enxergar o KPI"),
        p("O estímulo é uma transferência limitada de 50 MB pela interface tun_srsue. O tráfego cruza UE -> RAN -> UPF -> Internet, enquanto a xApp recebe DRB.UEThpDl pelo E2."),
        code_block("""cd /home/aluno/oran-stack-main
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  XAPP_DEPLOYMENT=kpm-latency-lab ./scripts/demo-kpm.sh"""),
        h2("O que observar no Grafana"),
        *bullets([
            "assinatura ativa igual a 1;",
            "taxa de indicações KPM acima de zero;",
            "pico de DRB.UEThpDl durante a transferência;",
            "retorno do KPI para próximo de zero após o tráfego;",
            "se houver classificador: transição idle -> active -> busy -> active -> idle.",
        ]),
        h2("Demonstração de referência"),
        code_block("""sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-load-watch.sh

# Sucesso esperado:
DEMO_LOAD_WATCH_OK"""),
        p("Na validação de referência, kpm-load-watch calculou média móvel de cinco amostras, atingiu pico de aproximadamente 28.841 kbps e completou o ciclo de estados."),
        callout("SE O KPI FICAR ZERO", "Confirme que o HTTP retornou 200, que o curl usou tun_srsue, que o UE tem PDU session e que a métrica é implementada pelo E2 node.", "red"),
        PageBreak(),

        h1("10", "Perfis de UE no laboratório"),
        p("O laboratório possui três perfis de assinante, mas usa um por vez no único enlace ZMQ. Isso equivale a trocar o SIM/aparelho conectado ao rádio virtual; não equivale a três UEs simultâneos."),
        data_table(
            ["Perfil", "IMSI", "Uso"],
            [
                ["ue1", "001010000000001", "referência"],
                ["ue2", "001010000000002", "aluno / experimento A"],
                ["ue3", "001010000000003", "aluno / experimento B"],
            ],
            [25 * mm, 64 * mm, 80 * mm],
        ),
        h2("Trocar o perfil e executar a demonstração"),
        code_block("""sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-ue-lab.sh ue2

# repetir com outro assinante
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-ue-lab.sh ue3

# voltar à referência
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/select-ue-lab-profile.sh ue1"""),
        callout("LIMITAÇÃO ATUAL", "DRB.UEThpDl Report Style 1 é agregado no O-DU. Ele prova carga de rádio, mas não atribui a medição a um IMSI específico.", "amber"),
        h2("Por que não escalar srsUE para três réplicas?"),
        p("O DU atual oferece um único par tx_port/rx_port ZMQ. Réplicas concorrentes disputariam o mesmo enlace e criariam uma topologia inválida. Multi-UE real requer rádio, emulador ou broker RF apropriado."),
        PageBreak(),

        h1("11", "Variante ARM no CIC"),
        p("Depois que a xApp funciona no NMI, a mesma imagem multiarch pode ser especializada para o CIC. O container roda nativamente como aarch64, enquanto RIC, RAN, UE e Core permanecem no NMI."),
        h2("O que muda"),
        *bullets([
            "PackageVariant injeta site=cic, architecture=arm64 e o nó Ampere;",
            "Flux no CIC puxa o repositório de deployment publicado no NMI;",
            "NodePorts e bridges RMR conectam a xApp remota ao RTMgr/E2Term no NMI;",
            "Prometheus no NMI recebe a telemetria da xApp CIC por um relay sem logs.",
        ]),
        h2("Teste de aceite multi-site"),
        code_block("""sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-kpm-multisite.sh

# Sucesso esperado:
DEMO_KPM_MULTISITE_OK"""),
        data_table(
            ["Verificação", "Resultado esperado"],
            [
                ["arquitetura do processo", "aarch64 no cic-k8s-w01"],
                ["Flux", "Kustomization Ready=True"],
                ["RMR", "um listener receive-only e retorno ao RTMgr"],
                ["KPM", "contadores avançam no NMI e CIC"],
                ["Grafana", "séries locais e cic-simple-mon no mesmo painel"],
            ],
            [66 * mm, 103 * mm],
        ),
        callout("AÇÃO DA INFRA", "O aluno não escolhe NodePorts nem cria regras no pfSense. Cada xApp remota precisa de portas e bridges exclusivas para evitar colisões.", "red"),
        PageBreak(),

        h1("12", "Atualização e rollback"),
        p("Pacotes Published são imutáveis. Atualização e rollback criam novas revisões para frente; o histórico Git e Porch permanece auditável."),
        h2("Atualização"),
        *bullets([
            "1. altere o algoritmo e acrescente um teste;",
            "2. gere uma nova imagem e fixe o novo digest;",
            "3. publique a revisão v2 do Team Blueprint;",
            "4. atualize o PackageVariant para workspaceName: v2;",
            "5. aprove o downstream, espere Flux Ready e repita o experimento.",
        ]),
        h2("Rollback para frente"),
        p("Copie o conteúdo conhecido de v1 para uma nova revisão, por exemplo v3-rollback. Não use git reset, não mova tags publicadas e não edite uma PackageRevision Published."),
        callout("DEMONSTRAÇÃO", "O repositório inclui demo-xapp-update-rollback.sh para a xApp de referência. Ele cria uma atualização inofensiva e um rollback para frente.", "blue"),
        h2("Evidências a guardar"),
        *bullets([
            "revisões Porch de origem e downstream;",
            "commit Git consumido pelo Flux;",
            "digest da imagem;",
            "status do rollout;",
            "assinatura, contadores KPM e gráfico antes/durante/depois.",
        ]),
        PageBreak(),

        h1("13", "Diagnóstico rápido"),
        data_table(
            ["Sintoma", "Primeira verificação"],
            [
                ["init container esperando", "E2 node ausente ou DISCONNECTED no E2Mgr"],
                ["registro existe, assinatura falha", "nome/endpoint do Service e resposta HTTP do SubMgr"],
                ["KPM congelou após DU", "nova associação E2; recriar somente pods stateless das xApps"],
                ["contadores avançam, KPI zero", "UE ocioso, PDU, tun_srsue ou métrica não implementada"],
                ["duas xApps compartilham ID", "métrica e período idênticos; escolher período distinto"],
                ["RMR intermitente", "RMR_FLAGS=1 e exatamente um listener em 4561"],
                ["Flux Ready=False", "Git, RBAC, digest e manifesto renderizado"],
                ["funciona NMI, falha CIC", "índice sem arm64 ou dependência nativa incompatível"],
                ["Grafana No Data", "Service monitoring=true, target Prometheus e janela de tempo"],
            ],
            [61 * mm, 108 * mm],
        ),
        h2("Recuperação controlada do ZMQ"),
        code_block("""sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/recover-ran-zmq.sh"""),
        p("Depois de confirmar o gNB CONNECTED, recrie somente os pods stateless das xApps para abrir novas assinaturas. Não reinicie o E2Term se a associação SCTP já estiver saudável."),
        h2("Logs sem exagero"),
        p("O laboratório usa retenção curta. Consulte logs por namespace, pod e janela de tempo. Prefira métricas para séries temporais e limite mensagens no callback a uma amostra periódica."),
        PageBreak(),

        h1("14", "Entrega do experimento"),
        p("A entrega deve permitir que outra pessoa reproduza o resultado e entenda o que a xApp acrescentou ao laboratório."),
        h2("Checklist do aluno"),
        *bullets([
            "[ ] problema ou hipótese descritos em até um parágrafo;",
            "[ ] código da xApp e teste unitário no repositório;",
            "[ ] logs limitados e nenhum segredo no código;",
            "[ ] imagem amd64/arm64 fixada pelo digest do índice;",
            "[ ] Team Blueprint e PackageVariant publicados;",
            "[ ] Flux Ready com ServiceAccount restrita;",
            "[ ] AppMgr, assinatura, RMR e KPM validados;",
            "[ ] estímulo do UE reproduzível;",
            "[ ] atualização e rollback demonstrados;",
            "[ ] gráfico ou tabela com hipótese, estímulo e resultado.",
        ]),
        h2("Estrutura sugerida do relatório"),
        data_table(
            ["Seção", "Conteúdo mínimo"],
            [
                ["Objetivo", "pergunta e comportamento esperado"],
                ["Método", "métrica, período, algoritmo, UE e volume de tráfego"],
                ["Ambiente", "site, arquitetura, digest e revisão do pacote"],
                ["Resultados", "KPI, estados, tempos e gráfico"],
                ["Discussão", "limitações, erros e próximos testes"],
                ["Reprodução", "comandos e critérios de aceite"],
            ],
            [44 * mm, 125 * mm],
        ),
        callout("OBJETIVO ACADÊMICO", "O valor não está apenas em fazer o pod subir. Está em formular uma hipótese, produzir um estímulo controlado e medir uma resposta da RAN.", "green"),
        PageBreak(),

        h1("A", "Glossário e referência rápida"),
        data_table(
            ["Termo", "Significado neste laboratório"],
            [
                ["UE", "equipamento do usuário; aqui, srsUE simulado"],
                ["IMSI", "identidade do assinante/SIM provisionada no Open5GS"],
                ["IMEI", "identidade do equipamento"],
                ["O-DU / O-CU", "funções distribuída e central da RAN"],
                ["Near-RT RIC", "plataforma que hospeda e conecta xApps à RAN via E2"],
                ["xApp", "aplicação do Near-RT RIC que monitora ou controla a RAN"],
                ["KPI", "indicador de desempenho"],
                ["E2SM-KPM", "modelo de serviço E2 para medições de desempenho"],
                ["RMR", "mensageria usada entre componentes do RIC e xApps"],
                ["Nephio", "automação de pacotes declarativos e variantes por site"],
                ["Porch", "servidor de pacotes e revisões KRM"],
                ["Flux", "reconciliador GitOps que aplica o pacote no Kubernetes"],
            ],
            [40 * mm, 129 * mm],
        ),
        h2("Arquivos canônicos do repositório"),
        *bullets([
            "docs/STUDENT_XAPP_LAB.md - procedimento técnico completo;",
            "docs/UE_SIMULATION_LAB.md - perfis UE e limitações ZMQ;",
            "scripts/new-kpm-xapp.sh - gerador da xApp;",
            "scripts/demo-load-watch.sh - experimento de referência;",
            "infra/nephio/blueprints/ - publicação e variantes;",
            "packages/nephio/ - Team Blueprints reutilizáveis.",
        ]),
        h2("Fonte da identidade visual"),
        p("Logo oficial da Universidade de Brasília: cen.unb.br/wp-content/uploads/2025/02/logo_unb_oficial_2025.png", SMALL),
        Spacer(1, 8 * mm),
        callout("PRÓXIMO LABORATÓRIO", "Crie uma xApp nova a partir deste roteiro, escolha um algoritmo simples e compare seu resultado com kpm-load-watch.", "blue"),
    ]
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = TutorialDocTemplate(str(OUTPUT))
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
