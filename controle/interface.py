"""Janela principal: menu auxiliar à esquerda, câmera no centro, legenda viva à direita."""
import pathlib
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QVBoxLayout, QWidget)

from controle.calibracao import INSTRUCOES, Fase, Sessao
from controle.geometria import medir
from controle.gravacao import Gravador
from controle.idioma import tr
from controle.legenda import GESTOS
from controle.pipeline import Resultado
from controle.poses import Pose

CORES = {
    "fundo": "#14161b", "painel": "#1b1e25", "cartao": "#232832", "borda": "#2e3440",
    "texto": "#e6e8ec", "suave": "#98a2b3", "destaque": "#4cc2ff", "ok": "#3fd07a",
    "alerta": "#ffb84d", "perigo": "#ff6b6b", "video": "#0d0f12",
}
DESTAQUE_S = 1.2
CONEXOES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
            (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17))
PASTA_GRAVACOES = pathlib.Path(__file__).resolve().parents[1] / "gravacoes"
POSE_TEXTO = {
    Pose.INDICADOR: "indicador · cursor e clique (pinça)",
    Pose.DOIS_DEDOS: "dois dedos · rolagem joystick",
    Pose.TRES_DEDOS: "três dedos · Alt+Tab",
    Pose.POLEGAR_BAIXO: "polegar para baixo · fechar janela",
    Pose.PINCA: "pinça · clique, segurar, zoom",
    Pose.PUNHO: "punho · visão geral, expandir",
    Pose.L: "L · expandir",
    Pose.ABERTA: "aberta · área, visão geral, fechar",
    Pose.C: "C · zoom com as duas mãos",
    Pose.DESCONHECIDA: "—",
}

ESTILO = f"""
QMainWindow, QWidget#raiz {{ background: {CORES['fundo']}; color: {CORES['texto']}; }}
QWidget {{ color: {CORES['texto']}; font-size: 10pt; }}
QScrollArea {{ border: none; background: transparent; }}
QWidget#painel {{ background: {CORES['painel']}; border-radius: 12px; }}
QLabel#titulo {{ font-size: 13pt; font-weight: 600; }}
QLabel#secao {{ color: {CORES['suave']}; font-size: 8pt; font-weight: 700; letter-spacing: 1px;
               margin-top: 10px; }}
QLabel#suave {{ color: {CORES['suave']}; font-size: 9pt; }}
QFrame#cartao {{ background: {CORES['cartao']}; border: 1px solid {CORES['borda']}; border-radius: 9px; }}
QFrame#cartao[destaque="true"] {{ border: 1px solid {CORES['destaque']}; background: #1f3a4d; }}
QFrame#cartao[desligado="true"] QLabel {{ color: #5d6574; }}
QPushButton#pausa {{ border: none; border-radius: 10px; padding: 12px; font-weight: 600;
                    background: #1f4d34; color: {CORES['ok']}; }}
QPushButton#pausa[pausado="true"] {{ background: #4d3a1f; color: {CORES['alerta']}; }}
QPushButton#pequeno {{ background: {CORES['cartao']}; border: 1px solid {CORES['borda']};
                      border-radius: 6px; padding: 4px 10px; }}
QSlider::groove:horizontal {{ height: 4px; background: {CORES['borda']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {CORES['destaque']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {CORES['texto']}; width: 14px; height: 14px; margin: -5px 0;
                             border-radius: 7px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: {CORES['borda']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QProgressBar {{ background: {CORES['cartao']}; border: none; border-radius: 4px; max-height: 8px; }}
QProgressBar::chunk {{ background: {CORES['destaque']}; border-radius: 4px; }}
QLabel#aviso {{ background: #4d3a1f; color: {CORES['alerta']}; border-radius: 8px; padding: 8px; }}
QStatusBar {{ background: {CORES['painel']}; color: {CORES['suave']}; }}
"""


class Ponte(QObject):
    """Leva resultados de outras threads para a thread da interface."""
    resultado = Signal(object)
    gravacao_salva = Signal(str)


def _repolir(w: QWidget):
    w.style().unpolish(w)
    w.style().polish(w)


class VideoWidget(QWidget):
    def __init__(self, cursor):
        super().__init__()
        self.cursor = cursor
        self.mostrar_landmarks = True
        self.mostrar_regiao = True
        self.espelhar = True  # só visualização: o reconhecimento sempre recebe a imagem espelhada
        self._r: Resultado | None = None
        self._aviso = ("", 0.0)
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def mostrar(self, r: Resultado):
        self._r = r
        if r.feitas:
            self._aviso = (r.feitas[-1][1], time.monotonic())
        self.update()

    def _alvo(self, largura: int, altura: int) -> QRectF:
        area = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        escala = min(area.width() / largura, area.height() / altura)
        w, h = largura * escala, altura * escala
        return QRectF(area.center().x() - w / 2, area.center().y() - h / 2, w, h)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(CORES["fundo"]))
        r = self._r
        if r is None:
            p.setPen(QColor(CORES["suave"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("Aguardando a câmera…"))
            return
        quadro = r.imagem if self.espelhar else np.ascontiguousarray(r.imagem[:, ::-1])
        altura, largura = quadro.shape[:2]
        imagem = QImage(quadro.data, largura, altura, quadro.strides[0], QImage.Format.Format_BGR888)
        alvo = self._alvo(largura, altura)
        caminho = QPainterPath()
        caminho.addRoundedRect(alvo, 10, 10)
        p.setClipPath(caminho)
        p.drawImage(alvo, imagem)
        aspecto = largura / altura

        def ponto(x: float, y: float) -> QPointF:  # x, y normalizados na imagem espelhada
            if not self.espelhar:
                x = 1 - x
            return QPointF(alvo.x() + x * alvo.width(), alvo.y() + y * alvo.height())

        if self.mostrar_regiao and self.cursor.modo == "absoluto":
            x0, y0, w, h = self.cursor.limites_regiao()
            p.setPen(QPen(QColor(CORES["destaque"]), 1.5, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(ponto(x0 / aspecto, y0), ponto((x0 + w) / aspecto, y0 + h)).normalized(), 8, 8)
        if self.mostrar_landmarks:
            for mao in r.maos:
                pts = [ponto(float(x), float(y)) for x, y, _ in mao.img]
                p.setPen(QPen(QColor(255, 255, 255, 170), 2))
                for a, b in CONEXOES:
                    p.drawLine(pts[a], pts[b])
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(CORES["destaque"]))
                for i, pt in enumerate(pts):
                    p.drawEllipse(pt, 4.5 if i in (4, 8, 12) else 3, 4.5 if i in (4, 8, 12) else 3)
        for estado in r.estado:
            cx, cy = estado.medidas.centro
            if estado.progresso_fechar > 0:
                centro = ponto(cx / aspecto, cy)
                caixa = QRectF(centro.x() - 46, centro.y() - 46, 92, 92)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, 60), 6))
                p.drawEllipse(caixa)
                p.setPen(QPen(QColor(CORES["perigo"]), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(caixa, 90 * 16, -int(estado.progresso_fechar * 360 * 16))
            texto = tr(estado.pose.value) + (" · " + tr("cursor") if estado.dono_cursor else "") \
                + (" · " + tr("zoom") if estado.em_zoom else "")
            self._pilula(p, ponto(cx / aspecto, cy) + QPointF(0, 40), texto, CORES["destaque"] if estado.dono_cursor else CORES["cartao"])
        p.setClipping(False)
        if r.pausado:
            p.fillRect(alvo, QColor(0, 0, 0, 120))
            fonte = QFont(self.font())
            fonte.setPointSize(22)
            fonte.setBold(True)
            p.setFont(fonte)
            p.setPen(QColor(CORES["alerta"]))
            p.drawText(alvo, Qt.AlignmentFlag.AlignCenter, "PAUSADO")
        texto, quando = self._aviso
        idade = time.monotonic() - quando
        if texto and idade < DESTAQUE_S:
            fonte = QFont(self.font())
            fonte.setPointSize(15)
            fonte.setBold(True)
            p.setFont(fonte)
            self._pilula(p, QPointF(alvo.center().x(), alvo.bottom() - 36), texto, CORES["destaque"],
                         opacidade=1 - idade / DESTAQUE_S, cor_texto="#0b1a24")

    @staticmethod
    def _pilula(p: QPainter, centro: QPointF, texto: str, cor: str, opacidade: float = 0.9,
                cor_texto: str = CORES["texto"]):
        metricas = p.fontMetrics()
        w, h = metricas.horizontalAdvance(texto) + 22, metricas.height() + 10
        caixa = QRectF(centro.x() - w / 2, centro.y() - h / 2, w, h)
        fundo = QColor(cor)
        fundo.setAlphaF(opacidade)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fundo)
        p.drawRoundedRect(caixa, h / 2, h / 2)
        cor_t = QColor(cor_texto)
        cor_t.setAlphaF(min(1.0, opacidade + 0.1))
        p.setPen(cor_t)
        p.drawText(caixa, Qt.AlignmentFlag.AlignCenter, texto)


def _secao(texto: str) -> QLabel:
    rotulo = QLabel(tr(texto).upper())
    rotulo.setObjectName("secao")
    return rotulo


class ControleDeslizante(QWidget):
    """Rótulo com valor + slider horizontal."""

    def __init__(self, nome: str, minimo: int, maximo: int, valor: int, formato):
        super().__init__()
        self.nome, self.formato = nome, formato
        caixa = QVBoxLayout(self)
        caixa.setContentsMargins(0, 2, 0, 2)
        caixa.setSpacing(4)
        self.rotulo = QLabel()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimo, maximo)
        self.slider.valueChanged.connect(self._atualizar_rotulo)
        caixa.addWidget(self.rotulo)
        caixa.addWidget(self.slider)
        self.slider.setValue(valor)
        self._atualizar_rotulo(valor)

    def _atualizar_rotulo(self, valor: int):
        self.rotulo.setText(f"{self.nome}  <span style='color:{CORES['destaque']}'>{self.formato(valor)}</span>")


class PainelMenu(QScrollArea):
    DESLIZANTES = ("zoom", "velocidade", "suavizacao", "regiao", "rolagem")
    CAIXAS = ("cursor_relativo", "inverter_rolagem", "espelhar", "landmarks", "mostrar_regiao")

    def __init__(self, ao_mudar):
        super().__init__()
        self._silencio = False  # ao carregar o perfil, a janela ainda não existe por inteiro
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedWidth(270)
        conteudo = QWidget()
        conteudo.setObjectName("painel")
        caixa = QVBoxLayout(conteudo)
        caixa.setContentsMargins(14, 12, 14, 14)
        caixa.setSpacing(6)

        caixa.addWidget(_secao("Câmera"))
        z = ControleDeslizante(tr("Zoom"), 10, 30, 10, lambda v: f"{v / 10:.1f}×")
        self.zoom = z.slider
        caixa.addWidget(z)
        self.espelhar = QCheckBox(tr("Espelhar visualização"))
        self.espelhar.setChecked(True)
        caixa.addWidget(self.espelhar)

        caixa.addWidget(_secao("Calibração"))
        self.botao_calibrar = QPushButton(tr("Calibrar meus gestos"))
        self.botao_calibrar.setObjectName("pequeno")
        caixa.addWidget(self.botao_calibrar)
        caixa.addWidget(_secao("Gravar sessão (calibração)"))
        self.gesto_gravacao = QComboBox()
        for gesto in GESTOS:
            self.gesto_gravacao.addItem(tr(gesto.nome), gesto.id)
        self.gesto_gravacao.addItem(tr("Livre (vários gestos)"), "livre")
        caixa.addWidget(self.gesto_gravacao)
        self.botao_gravar = QPushButton(tr("●  Gravar"))
        self.botao_gravar.setObjectName("pequeno")
        caixa.addWidget(self.botao_gravar)
        self.rotulo_gravacao = QLabel(tr("Grave cada gesto algumas vezes, do jeito que você faz."))
        self.rotulo_gravacao.setObjectName("suave")
        self.rotulo_gravacao.setWordWrap(True)
        caixa.addWidget(self.rotulo_gravacao)
        caixa.addWidget(_secao("Cursor"))
        self.cursor_relativo = QCheckBox(tr("Relativo, com aceleração"))
        self.cursor_relativo.setChecked(True)
        caixa.addWidget(self.cursor_relativo)
        v = ControleDeslizante(tr("Velocidade"), 25, 400, 100, lambda v: f"{v}%")
        self.velocidade = v.slider
        caixa.addWidget(v)
        s = ControleDeslizante(tr("Suavização"), 0, 100, 40, lambda v: f"{v}%")
        self.suavizacao = s.slider
        caixa.addWidget(s)
        r = ControleDeslizante(tr("Região ativa (modo absoluto)"), 30, 90, 60, lambda v: f"{v}%")
        self.regiao = r.slider
        caixa.addWidget(r)

        caixa.addWidget(_secao("Rolagem"))
        g = ControleDeslizante(tr("Velocidade da rolagem"), 25, 300, 100, lambda v: f"{v}%")
        self.rolagem = g.slider
        caixa.addWidget(g)
        self.inverter_rolagem = QCheckBox(tr("Inverter o sentido"))
        caixa.addWidget(self.inverter_rolagem)

        caixa.addWidget(_secao("Exibição"))
        self.landmarks = QCheckBox(tr("Mostrar pontos da mão"))
        self.landmarks.setChecked(True)
        self.mostrar_regiao = QCheckBox(tr("Mostrar região ativa (modo absoluto)"))
        self.mostrar_regiao.setChecked(True)
        caixa.addWidget(self.landmarks)
        caixa.addWidget(self.mostrar_regiao)

        caixa.addWidget(_secao("Gestos ligados"))
        botoes = QHBoxLayout()
        todos, nenhum = QPushButton(tr("Todos")), QPushButton(tr("Nenhum"))
        for b in (todos, nenhum):
            b.setObjectName("pequeno")
            botoes.addWidget(b)
        botoes.addStretch()
        caixa.addLayout(botoes)
        self.caixas_gestos: dict[str, QCheckBox] = {}
        for gesto in GESTOS:
            c = QCheckBox(tr(gesto.nome))
            c.setChecked(True)
            self.caixas_gestos[gesto.id] = c
            caixa.addWidget(c)
        todos.clicked.connect(lambda: [c.setChecked(True) for c in self.caixas_gestos.values()])
        nenhum.clicked.connect(lambda: [c.setChecked(False) for c in self.caixas_gestos.values()])

        caixa.addStretch()
        self.setWidget(conteudo)

        for sinal in (self.zoom.valueChanged, self.regiao.valueChanged, self.suavizacao.valueChanged,
                      self.rolagem.valueChanged, self.velocidade.valueChanged, self.cursor_relativo.toggled,
                      self.inverter_rolagem.toggled, self.espelhar.toggled, self.landmarks.toggled,
                      self.mostrar_regiao.toggled, *(c.toggled for c in self.caixas_gestos.values())):
            sinal.connect(lambda *_: None if self._silencio else ao_mudar())

    def ajustes(self) -> dict:
        """Estado do menu, para o perfil."""
        dados = {nome: getattr(self, nome).value() for nome in self.DESLIZANTES}
        dados |= {nome: getattr(self, nome).isChecked() for nome in self.CAIXAS}
        dados["gestos_desligados"] = [g for g, c in self.caixas_gestos.items() if not c.isChecked()]
        return dados

    def aplicar_ajustes(self, dados: dict):
        """Aplica o que vier do perfil; valor de tipo errado é ignorado e o deslizante limita ao seu intervalo."""
        self._silencio = True
        try:
            for nome in self.DESLIZANTES:
                valor = dados.get(nome)
                if isinstance(valor, int | float) and not isinstance(valor, bool) and valor == valor:
                    getattr(self, nome).setValue(int(max(-10**6, min(10**6, valor))))
            for nome in self.CAIXAS:
                if isinstance(dados.get(nome), bool):
                    getattr(self, nome).setChecked(dados[nome])
            desligados = dados.get("gestos_desligados")
            if isinstance(desligados, list):
                for gesto, caixa in self.caixas_gestos.items():
                    caixa.setChecked(gesto not in desligados)
        finally:
            self._silencio = False


class ItemLegenda(QFrame):
    def __init__(self, gesto):
        super().__init__()
        self.setObjectName("cartao")
        caixa = QVBoxLayout(self)
        caixa.setContentsMargins(10, 8, 10, 8)
        caixa.setSpacing(2)
        nome = QLabel(f"<b>{tr(gesto.nome)}</b>  <span style='color:{CORES['destaque']}'>→ {tr(gesto.acao)}</span>")
        nome.setWordWrap(True)
        como = QLabel(tr(gesto.como))
        como.setWordWrap(True)
        como.setObjectName("suave")
        caixa.addWidget(nome)
        caixa.addWidget(como)

    def definir(self, propriedade: str, valor: bool):
        if self.property(propriedade) != valor:
            self.setProperty(propriedade, valor)
            _repolir(self)
            for filho in self.findChildren(QLabel):
                _repolir(filho)


class PainelLegenda(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedWidth(330)
        conteudo = QWidget()
        conteudo.setObjectName("painel")
        caixa = QVBoxLayout(conteudo)
        caixa.setContentsMargins(14, 12, 14, 14)
        caixa.setSpacing(6)
        caixa.addWidget(_secao("Agora"))
        self.agora = QLabel(tr("Nenhuma mão no quadro"))
        self.agora.setObjectName("suave")
        self.agora.setWordWrap(True)
        caixa.addWidget(self.agora)
        caixa.addWidget(_secao("Legenda dos gestos"))
        self.itens: dict[str, ItemLegenda] = {}
        for gesto in GESTOS:
            item = ItemLegenda(gesto)
            self.itens[gesto.id] = item
            caixa.addWidget(item)
        caixa.addStretch()
        self.setWidget(conteudo)
        self._acesos: dict[str, float] = {}
        self._relogio = QTimer(self)
        self._relogio.timeout.connect(self._apagar_antigos)
        self._relogio.start(100)

    def atualizar(self, r: Resultado):
        agora = time.monotonic()
        for gesto, _ in r.feitas:
            self._acesos[gesto] = agora
            self.itens[gesto].definir("destaque", True)
        if r.estado:
            linhas = [f"<b>{tr('Mão {ident}', ident=e.ident)}</b> · {tr(POSE_TEXTO[e.pose])}" + (" <span style='color:#4cc2ff'>(cursor)</span>"
                      if e.dono_cursor else "") for e in r.estado]
            self.agora.setText("<br>".join(linhas))
        else:
            self.agora.setText(tr("Nenhuma mão no quadro"))

    def destacado(self) -> str | None:
        return max(self._acesos, key=self._acesos.get) if self._acesos else None

    def definir_habilitado(self, gesto: str, ligado: bool):
        self.itens[gesto].definir("desligado", not ligado)

    def _apagar_antigos(self):
        agora = time.monotonic()
        for gesto, quando in list(self._acesos.items()):
            if agora - quando > DESTAQUE_S:
                del self._acesos[gesto]
                self.itens[gesto].definir("destaque", False)


class DialogoCalibracao(QDialog):
    """Conduz a calibração: instrução do passo, barra de tempo e, no fim, o antes/depois."""

    def __init__(self, pai, total_passos: int):
        super().__init__(pai)
        self.setWindowTitle(tr("Calibrar meus gestos"))
        self.setObjectName("raiz")  # o fundo escuro vem do estilo da janela principal
        self.setStyleSheet(ESTILO)
        self.setMinimumSize(480, 300)
        self._total = total_passos
        caixa = QVBoxLayout(self)
        caixa.setContentsMargins(20, 18, 20, 18)
        caixa.setSpacing(10)
        self.passo = QLabel()
        self.passo.setObjectName("secao")
        self.instrucao = QLabel()
        self.instrucao.setObjectName("titulo")
        self.instrucao.setWordWrap(True)
        self.estado = QLabel()
        self.estado.setObjectName("suave")
        self.estado.setWordWrap(True)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        self.relatorio = QLabel()
        self.relatorio.setWordWrap(True)
        self.relatorio.setTextFormat(Qt.TextFormat.RichText)
        for w in (self.passo, self.instrucao, self.estado, self.barra, self.relatorio):
            caixa.addWidget(w)
        botoes = QHBoxLayout()
        botoes.addStretch()
        self.botao_cancelar = QPushButton(tr("Cancelar"))
        self.botao_cancelar.setObjectName("pequeno")
        self.botao_aplicar = QPushButton(tr("Aplicar e salvar"))
        self.botao_aplicar.setObjectName("pequeno")
        self.botao_aplicar.setEnabled(False)
        botoes.addWidget(self.botao_cancelar)
        botoes.addWidget(self.botao_aplicar)
        caixa.addLayout(botoes)

    def atualizar(self, sessao: Sessao):
        if sessao.concluida:
            return
        self.passo.setText(tr("Passo {n} de {total}", n=sessao.indice + 1, total=self._total).upper())
        self.instrucao.setText(tr(INSTRUCOES[sessao.pose_atual]))
        if sessao.fase is Fase.PREPARAR:
            texto = tr("Prepare a mão…") if sessao.tentativa == 1 else tr("Não vi sua mão. Vamos repetir.")
        else:
            texto = tr("Segure a pose…")
        self.estado.setText(texto)
        self.barra.setValue(round(sessao.progresso * 100))

    def mostrar_resultado(self, resultado):
        self.passo.setText(tr("Pronto").upper())
        self.instrucao.setText(tr("Calibração concluída"))
        self.estado.setText("")
        self.barra.setValue(100)
        if resultado.ajustados:
            linhas = [f"{nome}: {getattr(resultado.limites, nome):.2f}" for nome in sorted(resultado.ajustados)]
            texto = tr("Acerto nas suas poses: {antes:.0%} → {depois:.0%}", antes=resultado.acuracia_antes,
                       depois=resultado.acuracia_depois) + "<br>" + ", ".join(linhas)
        else:
            texto = tr("Os padrões já servem para a sua mão; nada precisou mudar.")
        if resultado.avisos:
            texto += "<br><span style='color:#ffb84d'>" + "<br>".join(resultado.avisos) + "</span>"
        self.relatorio.setText(texto)
        self.botao_aplicar.setEnabled(True)


class JanelaPrincipal(QMainWindow):
    def __init__(self, pipeline, modo_demonstracao: bool = False, aviso: str | None = None,
                 pasta_gravacoes: pathlib.Path = PASTA_GRAVACOES, perfil=None,
                 caminho_perfil: pathlib.Path | None = None, perguntar=None):
        super().__init__()
        self.perfil, self.caminho_perfil = perfil, caminho_perfil
        self._perguntar = perguntar or self._perguntar_sim_ou_nao
        self.sessao: Sessao | None = None
        self.dialogo_calibracao: DialogoCalibracao | None = None
        self._relogio = time.monotonic
        self._ativo_antes = True
        self.pipeline = pipeline
        self.pasta_gravacoes = pasta_gravacoes
        self.executor = pipeline.executor
        self.setWindowTitle(tr("Controle por gestos"))
        self.setStyleSheet(ESTILO)
        self.resize(1500, 860)

        raiz = QWidget()
        raiz.setObjectName("raiz")
        linhas = QHBoxLayout(raiz)
        linhas.setContentsMargins(10, 10, 10, 10)
        linhas.setSpacing(10)

        esquerda = QVBoxLayout()
        esquerda.setSpacing(10)
        titulo = QLabel(tr("Controle por gestos"))
        titulo.setObjectName("titulo")
        esquerda.addWidget(titulo)
        self.botao_pausa = QPushButton()
        self.botao_pausa.setObjectName("pausa")
        self.botao_pausa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_pausa.clicked.connect(self.alternar_pausa)
        esquerda.addWidget(self.botao_pausa)
        dica = QLabel(tr("Esc pausa · P pausa/retoma · Ctrl+Q sai"))
        dica.setObjectName("suave")
        esquerda.addWidget(dica)
        if modo_demonstracao or aviso:
            rotulo = QLabel(aviso or tr("Modo demonstração: os gestos aparecem, mas não agem no sistema."))
            rotulo.setObjectName("aviso")
            rotulo.setWordWrap(True)
            rotulo.setMaximumWidth(270)
            esquerda.addWidget(rotulo)
        self.menu = PainelMenu(self._aplicar_menu)
        if perfil is not None:
            self.menu.aplicar_ajustes(perfil.ajustes)
        self.menu.botao_gravar.clicked.connect(self.alternar_gravacao)
        self.menu.botao_calibrar.clicked.connect(lambda: self.iniciar_calibracao())
        esquerda.addWidget(self.menu, 1)
        linhas.addLayout(esquerda)

        self.video = VideoWidget(self.executor.cursor)
        linhas.addWidget(self.video, 1)
        self.legenda = PainelLegenda()
        linhas.addWidget(self.legenda)
        self.setCentralWidget(raiz)

        self._status = QLabel(tr("Iniciando…"))
        self.statusBar().addWidget(self._status, 1)

        QShortcut(QKeySequence("P"), self, activated=self.alternar_pausa)
        QShortcut(QKeySequence("Esc"), self, activated=self.pausar_agora)  # pânico: só pausa
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)

        self.ponte = Ponte()
        self.ponte.resultado.connect(self.ao_resultado)
        self.ponte.gravacao_salva.connect(self._gravacao_salva)
        self._ultima_status = 0.0
        self._aplicar_menu()
        self._atualizar_botao()

    # ---------- ações ----------

    def alternar_pausa(self):
        if self.executor.ativo:
            self.pipeline.pausar()
        else:
            self.pipeline.retomar()
        self._atualizar_botao()

    def pausar_agora(self):
        if self.executor.ativo:
            self.pipeline.pausar()
        self._atualizar_botao()

    def _atualizar_botao(self):
        pausado = not self.executor.ativo
        self.botao_pausa.setText(tr("▶  Pausado — clique para retomar") if pausado
                                 else tr("⏸  Gestos ativos — clique para pausar"))
        self.botao_pausa.setProperty("pausado", pausado)
        _repolir(self.botao_pausa)

    def alternar_gravacao(self):
        m = self.menu
        gravador = self.pipeline.gravador
        if gravador is None:
            self.pipeline.gravador = Gravador(self.pasta_gravacoes, m.gesto_gravacao.currentData())
            m.botao_gravar.setText(tr("■  Parar e salvar"))
            m.gesto_gravacao.setEnabled(False)
            m.rotulo_gravacao.setText(tr("Gravando…"))
            return
        self.pipeline.gravador = None
        m.botao_gravar.setText(tr("●  Gravar"))
        m.gesto_gravacao.setEnabled(True)
        m.rotulo_gravacao.setText(tr("Salvando…"))

        def salvar():  # compactar uma sessão longa não pode travar a janela
            caminho = gravador.salvar()
            self.ponte.gravacao_salva.emit(tr("Salvo: {nome} ({quadros} quadros)", nome=caminho.name, quadros=gravador.quadros)
                                           if caminho else tr("Nada gravado."))

        threading.Thread(target=salvar, name="gravacao", daemon=True).start()

    def _gravacao_salva(self, texto: str):
        self.menu.rotulo_gravacao.setText(texto)

    def _aplicar_menu(self):
        m = self.menu
        self.pipeline.config.zoom = m.zoom.value() / 10
        self.video.espelhar = m.espelhar.isChecked()
        cursor = self.executor.cursor
        cursor.modo = "relativo" if m.cursor_relativo.isChecked() else "absoluto"
        cursor.velocidade = m.velocidade.value() / 100
        m.regiao.setEnabled(cursor.modo == "absoluto")
        self.executor.inverter_rolagem = m.inverter_rolagem.isChecked()
        cursor.regiao = m.regiao.value() / 100
        s = m.suavizacao.value() / 100
        cursor.ajustar_filtro(freq_min=3.0 - 2.5 * s, beta=8.0 - 6.0 * s)
        self.executor.ganho_rolagem = m.rolagem.value() / 100
        self.video.mostrar_landmarks = m.landmarks.isChecked()
        self.video.mostrar_regiao = m.mostrar_regiao.isChecked()
        for gesto, caixa in m.caixas_gestos.items():
            if caixa.isChecked():
                self.executor.habilitados.add(gesto)
            else:
                self.executor.habilitados.discard(gesto)
            self.legenda.definir_habilitado(gesto, caixa.isChecked())
        self.video.update()

    # ---------- resultados ----------

    def ao_resultado(self, r: Resultado):
        if self.sessao is not None:
            self._avancar_calibracao(r)
        self.video.mostrar(r)
        self.legenda.atualizar(r)
        gravador = self.pipeline.gravador
        if gravador is not None:
            self.menu.rotulo_gravacao.setText(tr("Gravando… {quadros} quadros", quadros=gravador.quadros))
        agora = time.monotonic()
        if agora - self._ultima_status >= 0.25:  # barra legível: 4 atualizações por segundo
            self._ultima_status = agora
            m = r.metricas
            altura, largura = r.imagem.shape[:2]
            self._status.setText(
                f"{m.fps:.0f} fps · MediaPipe {m.mediapipe_ms:.1f} ms · "
                + tr("gestos {gestos:.1f} ms · captura→ação {total:.1f} ms", gestos=m.gestos_ms, total=m.total_ms)
                + f" · {largura}×{altura} · " + (tr("pausado") if r.pausado else tr("ativo")))

    def texto_status(self) -> str:
        return self._status.text()

    # ---------- calibração guiada ----------

    def _perguntar_sim_ou_nao(self, titulo: str, texto: str) -> bool:
        caixa = QMessageBox(QMessageBox.Icon.Question, titulo, texto,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        caixa.button(QMessageBox.StandardButton.Yes).setText(tr("Calibrar agora"))
        caixa.button(QMessageBox.StandardButton.No).setText(tr("Depois"))
        return caixa.exec() == QMessageBox.StandardButton.Yes

    def oferecer_calibracao(self):
        """No primeiro uso: a calibração é opcional, mas ajuda quem tem a mão diferente dos padrões."""
        if self.perfil is None or self.perfil.calibrado or self.sessao is not None:
            return
        if self._perguntar(tr("Primeiro uso"), tr("Quer calibrar os gestos para a sua mão? Leva cerca de 40 segundos. "
                                                  "Você pode fazer isso depois, pelo botão do menu.")):
            self.iniciar_calibracao()

    def iniciar_calibracao(self, sessao: Sessao | None = None, relogio=None):
        if self.sessao is not None:
            return
        self.sessao = sessao or Sessao()
        self._relogio = relogio or time.monotonic
        self._ativo_antes = self.executor.ativo
        if self._ativo_antes:
            self.pipeline.pausar()  # as poses de calibração não podem clicar nem fechar nada
            self._atualizar_botao()
        self.dialogo_calibracao = DialogoCalibracao(self, len(self.sessao.passos))
        self.dialogo_calibracao.botao_cancelar.clicked.connect(self.cancelar_calibracao)
        self.dialogo_calibracao.botao_aplicar.clicked.connect(self.aplicar_calibracao)
        self.dialogo_calibracao.rejected.connect(self.cancelar_calibracao)
        self.dialogo_calibracao.atualizar(self.sessao)
        self.dialogo_calibracao.show()

    def _avancar_calibracao(self, r: Resultado):
        largura_altura = r.imagem.shape[1] / r.imagem.shape[0]
        self.sessao.atualizar(self._relogio(), [medir(m, largura_altura) for m in r.maos])
        if self.sessao.concluida:
            self.dialogo_calibracao.mostrar_resultado(self.sessao.resultado())
        else:
            self.dialogo_calibracao.atualizar(self.sessao)

    def _encerrar_calibracao(self):
        dialogo, self.sessao, self.dialogo_calibracao = self.dialogo_calibracao, None, None
        if dialogo is not None:
            dialogo.rejected.disconnect(self.cancelar_calibracao)
            dialogo.close()
        if self._ativo_antes:
            self.pipeline.retomar()
        self._atualizar_botao()

    def cancelar_calibracao(self):
        if self.sessao is not None:
            self.sessao.cancelar()
            self._encerrar_calibracao()

    def aplicar_calibracao(self):
        if self.sessao is None or not self.sessao.concluida:
            return
        resultado = self.sessao.resultado()
        if self.perfil is not None:
            self.perfil.limites = {k: getattr(resultado.limites, k) for k in resultado.ajustados}
            self.perfil.calibrado = True
        reconhecedor = getattr(self.pipeline, "reconhecedor", None)
        if reconhecedor is not None:
            reconhecedor.limites = resultado.limites  # vale já no próximo quadro
        self._encerrar_calibracao()
        self._salvar_perfil()

    def _salvar_perfil(self):
        if self.perfil is None or self.caminho_perfil is None:
            return
        self.perfil.ajustes = self.menu.ajustes()
        try:
            self.perfil.salvar(self.caminho_perfil)
        except OSError as erro:  # disco cheio ou pasta sem escrita: sair importa mais que lembrar
            print(tr("Não consegui salvar o perfil em {caminho}: {erro}", caminho=self.caminho_perfil, erro=erro))

    def closeEvent(self, evento):
        self._salvar_perfil()
        self.pipeline.parar()
        super().closeEvent(evento)
