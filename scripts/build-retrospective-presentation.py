#!/usr/bin/env python3
"""Build the lab retrospective presentation.

The deck is a 15-minute talk: where the stack started, the xApp work in
progress, and the challenges that are still open. Speaker notes are the
script.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/presentations/retrospectiva-bancada-openran.pptx"
METRIC_COVERAGE = ROOT / "output/presentations/ocudu-metric-coverage.png"
METRIC_EXTENSION = ROOT / "output/presentations/ocudu-extending-metric-set.png"

W, H = Inches(13.333), Inches(7.5)
FONT = "Calibri"

BLUE = RGBColor(0x0B, 0x3E, 0x75)
GREEN = RGBColor(0x08, 0x7C, 0x3A)
TEAL = RGBColor(0x0E, 0x74, 0x90)
AMBER = RGBColor(0x8A, 0x4B, 0x08)
INK = RGBColor(0x17, 0x21, 0x2B)
MUTED = RGBColor(0x5C, 0x6B, 0x78)
SOFT = RGBColor(0xF4, 0xF7, 0xF9)
LINE = RGBColor(0xD5, 0xDE, 0xE6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE_BLUE = RGBColor(0xE7, 0xF0, 0xF8)
PALE_GREEN = RGBColor(0xE7, 0xF4, 0xEC)
PALE_TEAL = RGBColor(0xE5, 0xF4, 0xF7)
PALE_AMBER = RGBColor(0xFB, 0xF3, 0xE4)


def rgb_hex(color: RGBColor) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def set_run(run, size, color, bold=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_text(slide, x, y, w, h, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    shape = slide.shapes.add_textbox(x, y, w, h)
    frame = shape.text_frame
    frame.word_wrap = True
    frame.auto_size = None
    frame.margin_left = Emu(0)
    frame.margin_right = Emu(0)
    frame.margin_top = Emu(0)
    frame.margin_bottom = Emu(0)
    try:
        frame._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    run = paragraph.add_run()
    run.text = text
    set_run(run, size, color, bold)
    return shape


def fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def rect(slide, x, y, w, h, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    fill(shape, color)
    shape.shadow.inherit = False
    return shape


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text.strip()


def footer(slide, number, total, dark=False):
    color = RGBColor(0xC5, 0xD4, 0xE4) if dark else MUTED
    rule = RGBColor(0x1E, 0x58, 0x96) if dark else LINE
    rect(slide, Inches(0.7), Inches(7.12), Inches(11.95), Inches(0.01), rule)
    add_text(slide, Inches(0.7), Inches(7.18), Inches(8.5), Inches(0.24),
             "Infraestrutura de rede Open RAN  ·  UnB", 11, color)
    add_text(slide, Inches(10.3), Inches(7.18), Inches(2.35), Inches(0.24),
             f"{number}  /  {total}", 11, color, align=PP_ALIGN.RIGHT)


def kicker(slide, text):
    rect(slide, Inches(0), Inches(0), W, Inches(0.08), BLUE)
    add_text(slide, Inches(0.7), Inches(0.28), Inches(11.9), Inches(0.28),
             text.upper(), 12, TEAL, bold=True)


def title(slide, text, y=Inches(0.58), h=Inches(0.7)):
    add_text(slide, Inches(0.7), y, Inches(12.0), h, text, 32, BLUE, bold=True)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = W
        self.prs.slide_height = H
        self.prs.core_properties.title = "Infraestrutura de rede Open RAN, de março até agora"
        self.prs.core_properties.subject = "Retrospectiva da infraestrutura de rede Open RAN da UnB"
        self.prs.core_properties.category = "Apresentação de laboratório"
        self.slides = []

    def blank(self):
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.slides.append(slide)
        return slide

    def save(self):
        total = len(self.slides)
        for index, slide in enumerate(self.slides, start=1):
            dark = index == 1 or index == total
            footer(slide, index, total, dark=dark)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(OUTPUT)


def cover(deck: Deck):
    slide = deck.blank()
    rect(slide, 0, 0, W, H, BLUE)
    rect(slide, 0, 0, Inches(0.18), H, GREEN)
    add_text(slide, Inches(0.85), Inches(1.35), Inches(11), Inches(0.3),
             "Grupo Open RAN UNB", 14, RGBColor(0x9F, 0xC4, 0xE8), bold=True)
    add_text(slide, Inches(0.85), Inches(1.85), Inches(11.5), Inches(1.7),
             "Infraestrutura de rede Open RAN,\nde março até agora", 44, WHITE, bold=True)
    add_text(slide, Inches(0.85), Inches(4.15), Inches(11), Inches(1.15),
             "Evolução da infraestrutura de rede Open RAN\nda UnB no ano de 2026 até agora",
             20, RGBColor(0xD6, 0xE6, 0xF2))
    add_text(slide, Inches(0.85), Inches(6.35), Inches(8), Inches(0.3),
             "Novembro de 2026", 14, RGBColor(0x9F, 0xC4, 0xE8))
    notes(slide, """
Abra dizendo que isto é uma PoC de ensino e pesquisa da FT/UnB, não uma operadora. O critério é repetir o experimento e explicar a evidência.
Os dois guias de setembro são o mapa: um ensina do servidor físico ao KPI; o outro leva um integrante do SSH até uma xApp revisada, sem administração do cluster.
Esta fala atualiza esse mapa. Em setembro as xApps mediam. Em novembro a kpm-anomaly-prb também manda um controle. Esse controle fica com a equipe. O exercício do aluno continua sendo medir.
Não prometa produção, alta disponibilidade nem vários UEs ao mesmo tempo.
""")


def agenda(deck: Deck):
    slide = deck.blank()
    kicker(slide, "A conversa")
    title(slide, "Três partes")
    items = [
        ("01", "Março", "Open5GS no Docker, numa máquina. O UE ainda não fazia attach.", PALE_BLUE, BLUE),
        ("02", "Agora", "NMI e CIC no ar. O aluno gera uma xApp, manda tráfego e vê o KPI no Grafana.", PALE_GREEN, GREEN),
        ("03", "Depois", "As 27 métricas do OCUDU, cota de PRB que dá para desfazer, e um repositório por xApp.", PALE_AMBER, AMBER),
    ]
    for index, (number, head, body, bg, accent) in enumerate(items):
        y = Inches(1.7 + index * 1.65)
        rect(slide, Inches(0.7), y, Inches(11.95), Inches(1.48), bg)
        rect(slide, Inches(0.7), y, Inches(0.1), Inches(1.48), accent)
        add_text(slide, Inches(1.1), y + Inches(0.28), Inches(1.2), Inches(0.9), number, 28, accent, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(slide, Inches(2.5), y + Inches(0.22), Inches(9.6), Inches(0.45), head, 22, INK, bold=True)
        add_text(slide, Inches(2.5), y + Inches(0.72), Inches(9.6), Inches(0.55), body, 16, MUTED)
    notes(slide, """
Gaste menos de um minuto aqui. Diga a ordem e siga.
O ponto da fala inteira: a infraestrutura deixou de ser o experimento. O experimento agora é a xApp.
""")


def origin(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Retrospectiva  ·  março de 2026")
    title(slide, "Em março o attach ainda não fechava")
    facts = [
        ("Core", "Open5GS 2.7.7 no Docker Compose. O trabalho era o schema, o SCP, o NRF e um assinante no MongoDB."),
        ("RAN", "CU e DU do srsRAN entram no fim do mês. O E2 começa desligado: sem RIC, o DU caía."),
        ("UE", "O srsUE acha o ZMQ e fica procurando a célula. Attach e sessão PDU ainda não existem."),
        ("RIC", "O gNB registra e some. A rota de keep-alive chega tarde, e o E2Term é apagado."),
    ]
    for index, (head, body) in enumerate(facts):
        col = index % 2
        row = index // 2
        x = Inches(0.7 + col * 6.15)
        y = Inches(1.75 + row * 2.35)
        rect(slide, x, y, Inches(5.9), Inches(2.15), SOFT)
        rect(slide, x, y, Inches(5.9), Inches(0.08), BLUE)
        add_text(slide, x + Inches(0.3), y + Inches(0.3), Inches(5.3), Inches(0.4), head, 20, BLUE, bold=True)
        add_text(slide, x + Inches(0.3), y + Inches(0.85), Inches(5.3), Inches(1.05), body, 15, INK)
    notes(slide, """
Situe o começo em março. Não era Kubernetes, não era Nephio, não era xApp.
O core subia. A RAN e o RIC eram depuração.
Vale uma frase sobre o RIC: o E2Term registra uma vez, o Routing Manager ainda não tem a rota de keep-alive, e o gerenciador apaga a instância. Era um problema de ordem e de temporizador, não de rádio.
""")


def lessons(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Retrospectiva  ·  o que quebrava")
    title(slide, "Quatro quebras do começo")
    rows = [
        ("SCTP", "N2 e F1 completavam o setup e caíam em seguida. O NAT do cluster perde a associação. Esse tráfego foi para pontes OVS, fora do overlay.", BLUE),
        ("PFCP", "A sessão PDU era recusada: SMF e UPF anunciavam endereços diferentes. Os dois passaram a usar o IP do pod.", TEAL),
        ("E2", "O E2Term se anuncia uma vez na subida. Reiniciar ele no meio derruba a associação, e o CU muitas vezes fica desconectado.", AMBER),
        ("ZMQ", "O UE só sincroniza se a célula já está ativa. Subir os dois juntos deixa os dois esperando o primeiro quadro.", GREEN),
    ]
    for index, (head, body, accent) in enumerate(rows):
        y = Inches(1.65 + index * 1.28)
        rect(slide, Inches(0.7), y, Inches(11.95), Inches(1.16), SOFT)
        rect(slide, Inches(0.7), y, Inches(0.1), Inches(1.16), accent)
        add_text(slide, Inches(1.1), y + Inches(0.18), Inches(1.8), Inches(0.8), head, 20, accent, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(slide, Inches(3.1), y + Inches(0.18), Inches(9.2), Inches(0.82), body, 16, INK, anchor=MSO_ANCHOR.MIDDLE)
    notes(slide, """
Não conte o histórico de bugs. Conte a regra que ficou.
SCTP: por isso N2, F1 e E2 usam interfaces secundárias, não a rede de pods.
PFCP: por isso o UPF está na rede do pod, com Service headless.
E2: esta frase volta no fim. Não se reinicia o E2Term para consertar uma xApp.
ZMQ: por isso a ordem de subida é CU, DU, UE, e por isso ainda não há UEs simultâneos.
""")


def timeline(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Retrospectiva  ·  linha do tempo")
    title(slide, "De março a novembro")
    steps = [
        ("Mar", "Compose", "Core sobe.\nRAN e RIC\nainda quebram."),
        ("Abr", "kubeadm", "Primeira pilha\ncompleta. N2, F1\ne E2 no ar."),
        ("Jul", "OCUDU", "CU e DU passam\nao OCUDU 26.04.\nO UE continua srsUE."),
        ("Ago", "NMI e CIC", "PDU session, KPM\nao vivo, Nephio\ne um cluster ARM."),
        ("Nov", "Controle", "A xApp deixa\nde só medir\ne envia um comando."),
    ]
    rect(slide, Inches(1.15), Inches(2.55), Inches(10.95), Inches(0.04), LINE)
    for index, (when, head, body) in enumerate(steps):
        x = Inches(0.7 + index * 2.5)
        rect(slide, x + Inches(0.85), Inches(2.42), Inches(0.3), Inches(0.3), BLUE if index < 4 else AMBER)
        add_text(slide, x, Inches(1.7), Inches(2.2), Inches(0.35), when, 14, TEAL, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, x, Inches(2.9), Inches(2.2), Inches(0.45), head, 18, INK, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, x, Inches(3.45), Inches(2.2), Inches(1.3), body, 14, MUTED, align=PP_ALIGN.CENTER)
    rect(slide, Inches(0.7), Inches(5.15), Inches(11.95), Inches(1.7), PALE_BLUE)
    add_text(slide, Inches(1.0), Inches(5.35), Inches(11.3), Inches(0.4),
             "O que passou a contar como pronto", 18, BLUE, bold=True)
    add_text(slide, Inches(1.0), Inches(5.85), Inches(11.3), Inches(0.75),
             "Em abril, 50 pods Running já bastavam. Em agosto, a gente pedia sessão PDU, KPM decodificado e o mesmo número no NMI e no CIC.",
             16, INK)
    notes(slide, """
Percorra a linha sem parar em cada mês.
Abril: duas VMs, kubeadm, core, RIC, RAN e monitoração. O UE ainda parava em Switching on. GKE tinha sido tentado antes; SCTP e nó preemptível tornaram o laboratório inviável.
Julho: o CU/DU migra de srsRAN Project para OCUDU, release 26.04. O UE simulado continua o srsUE do srsRAN 4G.
Agosto é o mês da bancada: NMI em Proxmox, PDU session no dia 25, KPM com número, Nephio R6, cluster ARM no CIC.
Novembro é o capítulo atual: a xApp de anomalia manda controle.
Feche com a frase do quadro azul.
""")


def today(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Onde estamos")
    title(slide, "Dados, E2 e Git, cada um no seu caminho")
    flows = [
        ("Plano de dados", "UE → RAN → UPF", "Bytes do assinante. O SIM é cadastrado no Open5GS.", PALE_BLUE, BLUE),
        ("Telemetria E2", "O-DU → RIC → xApp", "Medição KPM. Nesta xApp nova, também volta um controle. O download segue pelo UPF.", PALE_TEAL, TEAL),
        ("Gestão", "Git → Nephio → Flux", "Configuração de cada site. Ansible sobe a máquina. Helm sobe a pilha base.", PALE_GREEN, GREEN),
    ]
    for index, (head, path, body, bg, accent) in enumerate(flows):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(1.6), Inches(3.95), Inches(3.15), bg)
        add_text(slide, x + Inches(0.22), Inches(1.78), Inches(3.5), Inches(0.3), head.upper(), 12, accent, bold=True)
        add_text(slide, x + Inches(0.22), Inches(2.2), Inches(3.5), Inches(0.85), path, 20, INK, bold=True)
        add_text(slide, x + Inches(0.22), Inches(3.2), Inches(3.5), Inches(1.3), body, 15, INK)
    rect(slide, Inches(0.7), Inches(4.95), Inches(11.95), Inches(1.9), SOFT)
    add_text(slide, Inches(0.95), Inches(5.12), Inches(11.45), Inches(0.35),
             "Onde isso roda", 16, BLUE, bold=True)
    add_text(slide, Inches(0.95), Inches(5.52), Inches(11.45), Inches(1.1),
             "NMI, cinco nós amd64: core e RAN no control plane, E2Term no primeiro worker, xApps no segundo, Grafana no servidor físico, Nephio na VM de gestão. CIC, dois nós Ampere, com a xApp ARM. O RIC fica no NMI.",
             15, INK)
    notes(slide, """
Esta é a frase que o guia didático pede que a pessoa consiga explicar. Kubernetes executa. Nephio entrega configuração. O RIC recebe telemetria. Nenhum dos três carrega o tráfego do assinante.
Grafana observa os três fluxos e não faz parte de nenhum deles.
Papéis no NMI, se pedirem detalhe: oran-k8s-01 tem Open5GS, CU, DU e o RIC base; oran-k8s-w01 tem E2Term e RTMgr; oran-k8s-w02 tem as xApps; nmi-srv03 tem Prometheus, Grafana e Loki; nephio-k8s-w01 tem Porch, Gitea e Flux.
CIC existe para provar outra arquitetura e outro site, não para duplicar a pilha. O ZMQ substitui o O-RU: o restante do fluxo, registro, sessão, E2 e KPM, é software real.
""")


def evidence(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Onde estamos  ·  o que já foi medido")
    title(slide, "O que a gente mediu")
    cards = [
        ("Sessão", "PDU no ar", "O UE registra, autentica e recebe um endereço 10.45.0.x. O ping ao gateway do UPF fecha com perda zero.", PALE_GREEN, GREEN),
        ("KPI", "28.841 kbps", "Numa transferência de 50 MB, HTTP 200, o pico de DRB.UEThpDl foi o mesmo no NMI e no CIC.", PALE_BLUE, BLUE),
        ("Entrega", "Um digest", "A imagem é publicada para amd64 e arm64. O pacote fixa o digest. Os dois sites não rodam builds diferentes.", PALE_AMBER, AMBER),
    ]
    for index, (k, head, body, bg, accent) in enumerate(cards):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(1.7), Inches(3.95), Inches(3.55), bg)
        add_text(slide, x + Inches(0.25), Inches(1.9), Inches(3.45), Inches(0.3), k.upper(), 12, accent, bold=True)
        add_text(slide, x + Inches(0.25), Inches(2.3), Inches(3.45), Inches(0.9), head, 26, INK, bold=True)
        add_text(slide, x + Inches(0.25), Inches(3.4), Inches(3.45), Inches(1.55), body, 15, INK)
    add_text(slide, Inches(0.7), Inches(5.5), Inches(11.95), Inches(1.3),
             "Pod Running só diz que o processo subiu. O teste vale quando a gente sabe o estímulo e o KPI muda. A bancada é para repetir esse teste.",
             16, MUTED)
    notes(slide, """
Estes números são do caminho de monitoramento, repetido em agosto, outubro e novembro. Não os atribua à xApp de controle.
28.841 kbps é o pico observado de DRB.UEThpDl, igual nos dois sites, numa transferência limitada de 50 MB.
O guia didático fixa o critério: o relatório do aluno registra hipótese, digest, parâmetros, estímulo, gráfico e limitação. O leitor precisa repetir a tendência, não o valor exato.
Se perguntarem de produção: diga que não é o objetivo. Control plane único e retenção curta de log são escolha de bancada.
O endereço do UE muda entre sessões. Fale 10.45.0.x, não um host fixo.
""")


def family(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Trabalho atual  ·  xApps")
    title(slide, "As quatro xApps")
    add_text(slide, Inches(0.7), Inches(1.45), Inches(12), Inches(0.4),
             "Cada uma foi feita em cima da anterior. O tráfego do assinante continua no UPF.", 16, MUTED)
    rows = [
        ("r4-simple-mon", "Mede", "Assina DRB.UEThpDl e publica a série. A indicação E2 chega no pod, no NMI e no CIC.", BLUE),
        ("kpm-load-watch", "Classifica", "Média móvel de cinco amostras. Três estados: idle, active, busy. Janela e limiares vêm do pacote.", TEAL),
        ("kpm-mon-tmt", "Feita por um aluno", "Média móvel no uplink, DRB.UEThpUl. Entrou pelo gerador e foi entregue pelo Flux.", GREEN),
        ("kpm-anomaly-prb", "Age", "Mede volume de downlink por UE. Passou do limiar, manda um controle E2SM-RC. É o que está em desenvolvimento.", AMBER),
    ]
    for index, (name, role, body, accent) in enumerate(rows):
        y = Inches(2.0 + index * 1.2)
        rect(slide, Inches(0.7), y, Inches(11.95), Inches(1.08), SOFT)
        rect(slide, Inches(0.7), y, Inches(0.1), Inches(1.08), accent)
        add_text(slide, Inches(1.05), y + Inches(0.14), Inches(3.3), Inches(0.38), name, 18, INK, bold=True)
        add_text(slide, Inches(1.05), y + Inches(0.52), Inches(3.3), Inches(0.38), role, 14, accent, bold=True)
        add_text(slide, Inches(4.5), y + Inches(0.18), Inches(7.85), Inches(0.75), body, 15, INK, anchor=MSO_ANCHOR.MIDDLE)
    notes(slide, """
Não abra código. A trajetória é o argumento.
simple-mon prova entrega. load-watch prova que um algoritmo cabe no callback e aparece no Grafana. mon-tmt prova que um aluno consegue entrar por esse caminho: média móvel no uplink, com a métrica que o O-DU realmente anuncia.
O guia de 1º de setembro ainda descreve só simple-mon e load-watch, e diz que elas não controlam a RAN. mon-tmt e anomaly-prb são o que aconteceu depois. Diga isso, para ninguém achar que o guia e o repositório discordam.
Ressalva da simple-mon e da load-watch: o Report Style delas é agregado no O-DU. Elas veem carga do rádio, não um IMSI.
""")


def closed_loop(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Trabalho atual  ·  kpm-anomaly-prb")
    title(slide, "A kpm-anomaly-prb manda um comando")
    steps = [
        ("1", "Observa", "KPM Style 4, por UE: volume de SDU RLC no downlink, em kbit."),
        ("2", "Calcula", "Média de 5 amostras. O limiar padrão é 1.000 kbit. Um UE parado fica abaixo."),
        ("3", "Age", "E2SM-RC Style 2, Ação 6. A cota máxima de PRB daquele UE vai a zero."),
    ]
    for index, (number, head, body) in enumerate(steps):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(1.65), Inches(3.95), Inches(2.15), PALE_AMBER if index == 2 else SOFT)
        add_text(slide, x + Inches(0.22), Inches(1.8), Inches(3.5), Inches(0.35), number, 14, AMBER if index == 2 else BLUE, bold=True)
        add_text(slide, x + Inches(0.22), Inches(2.15), Inches(3.5), Inches(0.4), head, 22, INK, bold=True)
        add_text(slide, x + Inches(0.22), Inches(2.65), Inches(3.5), Inches(0.9), body, 14, INK)
    limits = [
        ("Uma ação", "Nesta versão do OCUDU, o controle RIC que existe é essa cota de PRB. Release de RRC não está implementado."),
        ("Uma vez", "A xApp manda o comando no máximo uma vez por UE. Para decidir de novo, o pod precisa ser recriado."),
        ("O ensaio", "Rajada de download não vira SDU RLC a tempo. O teste é um fluxo constante, saindo do UPF."),
    ]
    for index, (head, body) in enumerate(limits):
        x = Inches(0.7 + index * 4.15)
        add_text(slide, x, Inches(4.1), Inches(3.95), Inches(0.35), head, 15, AMBER, bold=True)
        add_text(slide, x, Inches(4.48), Inches(3.95), Inches(1.15), body, 14, MUTED)
    notes(slide, """
Este é o miolo. Fale devagar.
A métrica desta xApp é DRB.RlcSduTransmittedVolumeDL. As outras usam throughput. O Style 4 traz o identificador do UE, e o controle precisa dele.
O comando é E2SM-RC Style 2 Action 6: cota de PRB do slice. Min, max e dedicated vão a zero. Até o comando, max fica em 100, que é a cota sem restrição.
O comando é a cota de PRB. Admissão, handover e release ficam de fora desta versão do OCUDU.
O ACK do controle é correlacionado ao UE que o originou, e o Grafana mostra a cota. Não invente um número de aceitação se a demo não tiver rodado na sala.
Um ping não dispara. O script demo-anomaly-prb.sh manda cerca de 80 Mbit/s durante 30 segundos, ritmado, do UPF para o UE.
""")


def delivery(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Trabalho atual  ·  como o código chega ao rádio")
    title(slide, "O aluno mexe no callback")
    stages = ["Python", "Imagem", "Blueprint", "Variante", "Git", "Flux", "Grafana"]
    for index, name in enumerate(stages):
        x = Inches(0.7 + index * 1.8)
        rect(slide, x, Inches(1.7), Inches(1.6), Inches(0.7), BLUE if index in (0, 6) else PALE_BLUE)
        add_text(slide, x, Inches(1.82), Inches(1.6), Inches(0.46), name, 14,
                 WHITE if index in (0, 6) else BLUE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    points = [
        ("O pacote", "O Team Blueprint descreve a xApp. A PackageVariant preenche site, arquitetura, imagem, nó E2, métrica, janela e limiar."),
        ("Quem publica", "O integrante entra pela VM 102, olha a bancada e abre o pull request. Outro membro da infra publica a revisão."),
        ("O exercício", "Média, limiar ou idle/active/busy. A kpm-anomaly-prb fica com a equipe da bancada."),
    ]
    for index, (head, body) in enumerate(points):
        y = Inches(2.75 + index * 1.3)
        add_text(slide, Inches(0.7), y, Inches(11.9), Inches(0.35), head, 18, BLUE, bold=True)
        add_text(slide, Inches(0.7), y + Inches(0.4), Inches(11.9), Inches(0.7), body, 16, INK)
    notes(slide, """
Se a plateia conhece Rancher ou Helm: Nephio versiona pacotes. Helm continua na pilha base. Ansible sobe as máquinas. O RIC é o lugar onde a xApp se registra.
O guia da equipe é explícito: na VM 102 o integrante usa kubectl, nunca sudo kubectl, porque o root cai num K3s legado. Pode listar e criar no namespace student-lab. Não lê Secret e não altera ran, 5g-core, near-rt-ric nem ricxapp.
A promoção é Draft, Proposed, Published, Git, Flux Ready, pod. O autor acompanha sem privilégio. O aceite é KPM no Grafana durante tráfego do UE, e volta ao estado ocioso depois.
O gerador é scripts/new-kpm-xapp.sh. O callback é o único lugar do algoritmo. xAppBase registra, assina, lê o RMR e expõe /metrics.
O primeiro exercício pede média, limiar ou idle/active/busy, sem controle. A anomaly-prb ultrapassa esse contrato de propósito, e por isso não entra no roteiro do aluno.
CIC continua etapa assistida: cada xApp remota precisa de NodePort e ponte RMR próprios.
""")


def challenges_map(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios")
    title(slide, "O que ainda falta")
    cards = [
        ("01", "Controle", "Hoje é um limiar e um corte para zero. O próximo é devolver a cota e tratar mais de um UE, com a ação que o OCUDU implementa.", AMBER, PALE_AMBER),
        ("02", "Plataforma", "O nome do gNB está gravado no pacote. Uma xApp nova só entra quando o RTMgr reaprende as rotas. O RIC ainda é só amd64.", BLUE, PALE_BLUE),
        ("03", "Rádio", "Três perfis de assinante e um peer ZMQ. As xApps de monitoramento veem a célula. Um UE por vez.", GREEN, PALE_GREEN),
    ]
    for index, (number, head, body, accent, bg) in enumerate(cards):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(1.7), Inches(3.95), Inches(4.95), bg)
        add_text(slide, x + Inches(0.25), Inches(1.95), Inches(3.45), Inches(0.4), number, 16, accent, bold=True)
        add_text(slide, x + Inches(0.25), Inches(2.5), Inches(3.45), Inches(1.3), head, 24, INK, bold=True)
        add_text(slide, x + Inches(0.25), Inches(4.05), Inches(3.45), Inches(2.2), body, 15, INK)
    notes(slide, """
A pilha já sobe. O trabalho daqui para frente está nestes três cartões.
Depois escolha a ordem: primeiro o controle, porque é o trabalho atual; depois a plataforma, porque ela limita quantas xApps cabem; por último o rádio, porque muda o tipo de pergunta.
Não abra os três no mesmo fôlego. O slide seguinte separa o que cada um pede. Os dois de depois fecham a seção de métricas: validar as 27 que a RAN já expõe, e elaborar a esteira para acrescentar outras. O último, antes do fecho, junta duas intenções: incluir o controle de slicing, e tirar o desenvolvimento de xApps deste repositório, com um repositório por xApp.
""")


def challenges_detail(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios  ·  o que cada um pede")
    title(slide, "O que cada frente pede", h=Inches(0.85))
    columns = [
        ("Controle", [
            "Devolver a cota quando o volume do UE cai.",
            "Decidir UE por UE, com cotas diferentes.",
            "Listar as ações que o OCUDU implementa antes de prometer outra.",
        ], AMBER),
        ("Plataforma", [
            "Ler o nome do gNB no E2Mgr quando ele conectar.",
            "Registrar uma xApp nova no RTMgr com o E2Term no ar.",
            "Publicar o RIC ARM como mais uma variante de pacote.",
        ], BLUE),
        ("Rádio", [
            "Trocar o peer ZMQ por um emulador com UEs ao mesmo tempo.",
            "Atribuir o KPI ao assinante.",
            "Levar a mesma xApp para rádio e SIM físicos.",
        ], GREEN),
    ]
    for index, (head, items, accent) in enumerate(columns):
        x = Inches(0.7 + index * 4.15)
        add_text(slide, x, Inches(1.7), Inches(3.9), Inches(0.4), head, 20, accent, bold=True)
        rect(slide, x, Inches(2.2), Inches(1.1), Inches(0.06), accent)
        for item_index, item in enumerate(items):
            y = Inches(2.5 + item_index * 1.4)
            add_text(slide, x, y, Inches(3.9), Inches(1.25), item, 15, INK)
    notes(slide, """
Controle: hoje a xApp marca o UE como já atuado e não desfaz. Uma política de verdade tem entrada e saída, e precisa conviver com o fato de que esta RAN só implementa a cota de PRB.
Plataforma: o NEXT_STEPS do repositório já diz isto. e2_node_id estático serve para um gNB. Não serve se o nó aparece e some. E a regra operacional continua: não reiniciar o E2Term depois que a xApp assinou.
Rádio: três assinantes no Open5GS, um de cada vez. O DU tem um peer ZMQ. Dizer “temos três UEs” é impreciso. KPI por IMSI depende de Report Style e do que a RAN anuncia; a anomaly já vê identificador de UE no Style 4, as monitoras agregadas não.
Feche dizendo que rádio físico é o último degrau, não o próximo. O próximo é fazer o ciclo atual ser reversível e explicável.
""")


def metric_coverage(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios  ·  métricas E2")
    title(slide, "Validar cada métrica que o OCUDU expõe", h=Inches(0.55))
    add_text(
        slide, Inches(0.7), Inches(1.28), Inches(12.0), Inches(0.85),
        "A bancada hoje exercita três KPIs. O OCUDU implementa E2SM-KPM v3.00 e lista 27 métricas suportadas, de 287 definidas. Queremos assinar, estimular e decodificar essas 27.",
        16, INK,
    )
    picture_width = Inches(10.7)
    slide.shapes.add_picture(
        str(METRIC_COVERAGE),
        (W - picture_width) / 2,
        Inches(2.22),
        width=picture_width,
    )
    notes(slide, """
Aponte a tabela, não leia as três linhas. O número que importa é 27 de 287.
24 vêm do 3GPP TS 28.552, que define 278. Três vêm do O-RAN WG3, que define 9. O conjunto cresce a cada release, quando o OCUDU passa a expor uma medição interna pela E2.
Hoje o laboratório exercita DRB.UEThpDl, DRB.UEThpUl e DRB.RlcSduTransmittedVolumeDL. Validar as 27 significa, para cada uma: a RAN anuncia, a xApp assina, a indicação chega, o valor decodificado muda com um estímulo conhecido e o Grafana mostra a série.
Não prometa as 260 que a especificação define e esta RAN não implementa. Também não confunda com o controle RIC: esta RAN só aceita a cota de PRB. Aqui o buraco é de medição, não de ação.
O slide seguinte é o complemento: uma esteira para acrescentar métrica, nos três passos que o próprio OCUDU documenta.
""")


def metric_pipeline(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios  ·  expansão de métricas")
    title(slide, "Uma esteira para cada métrica nova", h=Inches(0.5))
    add_text(
        slide, Inches(0.7), Inches(1.18), Inches(12.0), Inches(0.42),
        "Os três passos estão em lib/e2/e2sm/e2sm_kpm/. No laboratório, a métrica entra na conta quando a xApp decodifica a indicação.",
        15, INK,
    )
    steps = [
        ("1", "Confirmar", "O DU, o CU-CP ou o CU-UP já calcula esse valor. O código E2 só lê o que já está na memória."),
        ("2", "Medir", "O getter devolve um agregado, ou um registro por UE, a partir dos dados que o provider já recebe."),
        ("3", "Anunciar", "O provider registra nome, rótulo e granularidade. O E2 Setup passa a oferecer a métrica ao RIC."),
    ]
    for index, (number, head, body) in enumerate(steps):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(1.68), Inches(3.95), Inches(1.48), SOFT)
        rect(slide, x, Inches(1.68), Inches(0.08), Inches(1.48), TEAL)
        add_text(slide, x + Inches(0.22), Inches(1.78), Inches(3.5), Inches(0.3), f"{number}   {head}", 16, TEAL, bold=True)
        add_text(slide, x + Inches(0.22), Inches(2.12), Inches(3.5), Inches(0.9), body, 13, INK)
    picture_width = Inches(7.4)
    slide.shapes.add_picture(
        str(METRIC_EXTENSION),
        (W - picture_width) / 2,
        Inches(3.32),
        width=picture_width,
    )
    notes(slide, """
A imagem é a seção Extending the Metric Set, na mesma página Supported E2 Metrics. Não leia o código. Diga os três passos.
Primeiro: o getter só lê memória que o provider já recebeu da pilha. No DU são last_ue_metrics e ue_aggr_rlc_metrics. No CU-CP, cu_cp_metrics. No CU-UP, as métricas de PDCP e de F1-U. Se o valor não está nessas estruturas, ele entra antes no subsistema do gNB e só então chega ao provider por report_metrics().
Segundo: o getter segue a mesma assinatura dos que já existem. Sem UE na assinatura, devolve um agregado. Com UE, um registro para cada um.
Terceiro: supported_metrics.emplace no construtor do provider. Rótulo e granularidade não podem passar do que e2sm_kpm_metric_defs.h define para aquele nome. O processo confere isso na subida.
A esteira do laboratório acrescenta o que a documentação do OCUDU não faz: assinar a métrica nova com uma xApp, estimular o UE e ver a série no Grafana. Sem isso, o registro no provider não é evidência.
Fonte: docs.ocudu.org, Supported E2 Metrics.
""")


def slicing_control(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios  ·  slicing")
    title(slide, "Incluir o controle de slicing")
    add_text(
        slide, Inches(0.7), Inches(1.45), Inches(12.0), Inches(0.7),
        "A ação RIC que o OCUDU 26.04 implementa é a cota de PRB do slice. Hoje ela zera um UE. Queremos escolher os três percentuais e conseguir desfazer.",
        18, INK,
    )
    cards = [
        ("O que a RAN faz", "E2SM-RC Style 2, Ação 6. Três percentuais por UE: mínimo, máximo e dedicado. As outras ações recebem recusa.", BLUE, PALE_BLUE),
        ("O que a xApp faz hoje", "A kpm-anomaly-prb manda os três para zero, uma vez. PLMN e S-NSSAI estão fixos no código. A bancada tem um slice, SST 1.", AMBER, PALE_AMBER),
        ("O que queremos", "A cota vira parâmetro da xApp. O Grafana mostra os três números, e um comando seguinte devolve a cota anterior.", GREEN, PALE_GREEN),
    ]
    for index, (head, body, accent, bg) in enumerate(cards):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(2.4), Inches(3.95), Inches(4.2), bg)
        rect(slide, x, Inches(2.4), Inches(3.95), Inches(0.08), accent)
        add_text(slide, x + Inches(0.25), Inches(2.7), Inches(3.45), Inches(1.05), head, 22, INK, bold=True)
        add_text(slide, x + Inches(0.25), Inches(3.9), Inches(3.45), Inches(2.3), body, 16, INK)
    notes(slide, """
Não anuncie vários slices. A RAN e o core desta bancada anunciam um só: SST 1, no PLMN 00101. O SD no controle está fixo em 0.
O que existe de slicing no RIC é a cota de PRB desse slice, por UE: mínimo, máximo e dedicado, cada um de 0 a 100. É o E2SM-RC Style 2 Ação 6. O OCUDU 26.04 não aceita outra ação; handover e release de RRC continuam fora.
A kpm-anomaly-prb usa a ação uma vez, com os três valores em zero, para isolar um UE que passou do limiar. Não escolhe uma política e não restaura.
Incluir o controle de slicing é fazer a xApp escolher os três percentuais, publicar a cota no Grafana e conseguir desfazer. O identificador do slice deixa de ser constante no código e passa a ser parâmetro do pacote.
Não prometa um segundo SST no Open5GS nesta etapa. Isolar dois slices de verdade pede outro S-NSSAI na RAN, no core e no assinante. Isso vem depois de a cota deste slice ser reversível e observável.
""")


def xapp_repositories(deck: Deck):
    slide = deck.blank()
    kicker(slide, "Próximos desafios  ·  repositórios")
    title(slide, "Uma xApp, um repositório")
    add_text(
        slide, Inches(0.7), Inches(1.45), Inches(12.0), Inches(0.7),
        "Hoje o algoritmo, o pacote Nephio e a imagem nascem neste repositório. A ideia é cada xApp ter o seu.",
        18, INK,
    )
    cards = [
        ("O que fica aqui", "Core, RAN, RIC, Nephio e o contrato do xAppBase.", BLUE, PALE_BLUE),
        ("O que vai para fora", "Código, teste, imagem e blueprint de cada xApp, num repositório próprio.", TEAL, PALE_TEAL),
        ("A entrega", "Continua por digest, PackageVariant e Flux. A conta do aluno continua sem admin no cluster.", GREEN, PALE_GREEN),
    ]
    for index, (head, body, accent, bg) in enumerate(cards):
        x = Inches(0.7 + index * 4.15)
        rect(slide, x, Inches(2.4), Inches(3.95), Inches(4.2), bg)
        rect(slide, x, Inches(2.4), Inches(3.95), Inches(0.08), accent)
        add_text(slide, x + Inches(0.25), Inches(2.7), Inches(3.45), Inches(0.85), head, 22, INK, bold=True)
        add_text(slide, x + Inches(0.25), Inches(3.7), Inches(3.45), Inches(2.5), body, 16, INK)
    notes(slide, """
Hoje o workflow xapp-multiarch.yml publica um único índice, oran-xapps, com todas as xApps. Um pull request de algoritmo reconstrói a imagem compartilhada e mexe em packages/nephio e em infra/nephio dentro do repositório da pilha.
A separação é: este repositório guarda a bancada e o contrato de runtime. Cada xApp ganha repositório, histórico e imagem próprios. O pacote Nephio aponta para o digest daquele repositório.
Não diga que o aluno passa a publicar sozinho no cluster. A revisão de promoção continua. O que muda é onde o código vive, não quem tem permissão na RAN.
Também não prometa a mudança já feita. O gerador new-kpm-xapp.sh ainda escreve dentro deste repositório. A esteira nova é o passo seguinte.
""")


def close(deck: Deck):
    slide = deck.blank()
    rect(slide, 0, 0, W, H, BLUE)
    rect(slide, 0, 0, Inches(0.18), H, GREEN)
    add_text(slide, Inches(0.85), Inches(1.45), Inches(11.5), Inches(0.35),
             "ONDE ISSO CHEGOU", 14, RGBColor(0x9F, 0xC4, 0xE8), bold=True)
    add_text(slide, Inches(0.85), Inches(1.95), Inches(11.5), Inches(2.2),
             "Em março o UE\nnão fazia attach.", 36, WHITE, bold=True)
    add_text(slide, Inches(0.85), Inches(4.35), Inches(11.2), Inches(1.5),
             "Em novembro o UE tem sessão, o Grafana\nmostra o KPI, e uma xApp já manda cota de PRB.", 28, RGBColor(0xD6, 0xE6, 0xF2))
    notes(slide, """
Leia as duas frases e pare.
Se perguntarem o que vem depois, aponte os slides de métricas, slicing e repositórios.
""")


def main():
    deck = Deck()
    cover(deck)
    origin(deck)
    lessons(deck)
    timeline(deck)
    today(deck)
    evidence(deck)
    family(deck)
    closed_loop(deck)
    delivery(deck)
    challenges_map(deck)
    challenges_detail(deck)
    metric_coverage(deck)
    metric_pipeline(deck)
    slicing_control(deck)
    xapp_repositories(deck)
    close(deck)
    deck.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
