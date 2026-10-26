"""Executa os eventos no sistema: uinput (mouse e teclado virtuais) e atalhos do KWin.

uinput funciona no Wayland porque é um dispositivo de entrada do kernel, não uma API do X11.
"""
import subprocess
from typing import Protocol

from evdev import ecodes

from controle.cursor import Cursor
from controle.eventos import Evento, Tipo
from controle.legenda import GESTOS, gesto_do_evento

BOTAO_ESQUERDO, BOTAO_DIREITO = ecodes.BTN_LEFT, ecodes.BTN_RIGHT
ALT, TAB, CTRL, SHIFT = ecodes.KEY_LEFTALT, ecodes.KEY_TAB, ecodes.KEY_LEFTCTRL, ecodes.KEY_LEFTSHIFT
ESCALA_ABS = 65535
ENTALHE = 120  # unidades de alta resolução por entalhe da roda (padrão do kernel)

KWIN = {
    Tipo.EXPANDIR: "Window Maximize",
    Tipo.VISAO_GERAL: "Overview",
    Tipo.FECHAR_JANELA: "Window Close",
}
AREAS = {-1: "Switch One Desktop to the Left", 1: "Switch One Desktop to the Right"}
SOLTURAS = frozenset({Tipo.SEGURAR_FIM, Tipo.ALT_TAB_FIM, Tipo.ZOOM_FIM})


class Saida(Protocol):
    def mover_absoluto(self, u: float, v: float) -> None: ...
    def botao(self, codigo: int, pressionado: bool) -> None: ...
    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int) -> None: ...
    def tecla(self, codigo: int, pressionada: bool) -> None: ...
    def atalho_kwin(self, nome: str) -> None: ...


class Executor:
    def __init__(self, saida: Saida, cursor: Cursor):
        self.saida, self.cursor = saida, cursor
        self.ativo = True
        self.habilitados = {g.id for g in GESTOS}
        self.ganho_rolagem = 1.0
        self.inverter_rolagem = False
        self._pressionados: set[tuple[str, int]] = set()
        self._resto_roda = [0, 0]

    def executar(self, eventos: list[Evento]) -> list[tuple[str, str]]:
        """Executa e devolve (gesto, descrição) do que agiu, para a legenda acender."""
        feitas = []
        for e in eventos:
            gesto = gesto_do_evento(e)
            if e.tipo not in SOLTURAS and (not self.ativo or gesto not in self.habilitados):
                continue
            descricao = self._executar(e)
            if descricao and e.tipo not in (Tipo.APONTAR, Tipo.ARRASTAR):
                feitas.append((gesto, descricao))
        return feitas

    def liberar_tudo(self):
        for tipo, codigo in list(self._pressionados):
            (self.saida.botao if tipo == "botao" else self.saida.tecla)(codigo, False)
        self._pressionados.clear()

    def _executar(self, e: Evento) -> str | None:
        s = self.saida
        match e.tipo:
            case Tipo.APONTAR:
                self.cursor.apontar(e.t_ms, e.x, e.y)
                s.mover_absoluto(*self.cursor.normalizada())
            case Tipo.ARRASTAR:
                self.cursor.arrastar(e.x, e.y, e.t_ms)
                s.mover_absoluto(*self.cursor.normalizada())
            case Tipo.CLIQUE:
                if e.t_ref:
                    # clica onde o cursor estava quando a pinça começou (a mão mexe ao pinçar)
                    self.cursor.voltar_para(e.t_ref)
                    s.mover_absoluto(*self.cursor.normalizada())
                codigo = BOTAO_DIREITO if e.valor == 3 else BOTAO_ESQUERDO
                s.botao(codigo, True)
                s.botao(codigo, False)
                return "clique direito" if e.valor == 3 else "clique"
            case Tipo.SEGURAR_INICIO:
                self._apertar("botao", BOTAO_ESQUERDO)
                return "segurando"
            case Tipo.SEGURAR_FIM:
                return "soltou" if self._soltar("botao", BOTAO_ESQUERDO) else None
            case Tipo.ROLAGEM:
                return self._rolar(e.x, e.y)
            case Tipo.AREA_DE_TRABALHO:
                s.atalho_kwin(AREAS[e.valor])
                return "área à esquerda" if e.valor < 0 else "área à direita"
            case Tipo.ALT_TAB_INICIO:
                self._apertar("tecla", ALT)
                self._tocar(TAB)
                return "Alt+Tab"
            case Tipo.ALT_TAB_PROXIMO:
                if ("tecla", ALT) not in self._pressionados:
                    # o início foi pulado (pausa ou gesto desligado): sem Alt, Tab seria digitado
                    self._apertar("tecla", ALT)
                    self._tocar(TAB)
                    return "Alt+Tab"
                self._tocar(TAB)
                return "próxima janela"
            case Tipo.ALT_TAB_ANTERIOR:
                if ("tecla", ALT) not in self._pressionados:
                    self._apertar("tecla", ALT)
                self.saida.tecla(SHIFT, True)
                self._tocar(TAB)
                self.saida.tecla(SHIFT, False)
                return "janela anterior"
            case Tipo.ALT_TAB_FIM:
                return "escolheu a janela" if self._soltar("tecla", ALT) else None
            case Tipo.ZOOM_INICIO:
                # Ctrl fica segurado a sessão inteira: apertar e soltar junto de cada passo, em
                # dispositivos diferentes, deixava o KDE ver a roda antes do Ctrl (rolava em vez de zoom)
                self._apertar("tecla", CTRL)
            case Tipo.ZOOM:
                if ("tecla", CTRL) not in self._pressionados:
                    self._apertar("tecla", CTRL)
                s.rolar(0, ENTALHE * e.valor, 0, e.valor)
                return "zoom +" if e.valor > 0 else "zoom −"
            case Tipo.ZOOM_FIM:
                self._soltar("tecla", CTRL)
            case _ if e.tipo in KWIN:
                s.atalho_kwin(KWIN[e.tipo])
                return {Tipo.EXPANDIR: "maximizou", Tipo.VISAO_GERAL: "visão geral",
                        Tipo.FECHAR_JANELA: "fechou a janela"}[e.tipo]
        return None

    def _apertar(self, tipo: str, codigo: int):
        (self.saida.botao if tipo == "botao" else self.saida.tecla)(codigo, True)
        self._pressionados.add((tipo, codigo))

    def _soltar(self, tipo: str, codigo: int) -> bool:
        if (tipo, codigo) not in self._pressionados:
            return False
        (self.saida.botao if tipo == "botao" else self.saida.tecla)(codigo, False)
        self._pressionados.discard((tipo, codigo))
        return True

    def _tocar(self, codigo: int):
        self.saida.tecla(codigo, True)
        self.saida.tecla(codigo, False)

    def _rolar(self, x: float, y: float) -> str:
        ganho = ENTALHE * self.ganho_rolagem * (-1 if self.inverter_rolagem else 1)
        hr = [round(x * ganho), round(y * ganho)]
        entalhes = []
        for i in range(2):
            self._resto_roda[i] += hr[i]
            inteiros = int(self._resto_roda[i] / ENTALHE)  # trunca em direção ao zero
            self._resto_roda[i] -= inteiros * ENTALHE
            entalhes.append(inteiros)
        self.saida.rolar(hr[0], hr[1], entalhes[0], entalhes[1])
        if abs(hr[1]) >= abs(hr[0]):
            return "rolou para cima" if hr[1] > 0 else "rolou para baixo"
        return "rolou para a direita" if hr[0] > 0 else "rolou para a esquerda"


class SaidaNula:
    """Modo demonstração: reconhece e mostra os gestos sem agir no sistema."""

    def mover_absoluto(self, u, v): pass
    def botao(self, codigo, pressionado): pass
    def rolar(self, horizontal_hr, vertical_hr, horizontal, vertical): pass
    def tecla(self, codigo, pressionada): pass
    def atalho_kwin(self, nome): pass
    def fechar(self): pass


class SaidaUinput:
    """Mouse absoluto + teclado virtuais. Precisa de escrita em /dev/uinput."""

    def __init__(self):
        from evdev import AbsInfo, UInput

        e = ecodes
        eixo = AbsInfo(value=0, min=0, max=ESCALA_ABS, fuzz=0, flat=0, resolution=0)
        self._ponteiro = UInput({
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
            e.EV_ABS: [(e.ABS_X, eixo), (e.ABS_Y, eixo)],
            e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL, e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES],
        }, name="cv-controle-do-pc ponteiro")
        self._teclado = UInput({e.EV_KEY: [ALT, TAB, CTRL, SHIFT]}, name="cv-controle-do-pc teclado")

    def mover_absoluto(self, u: float, v: float):
        self._ponteiro.write(ecodes.EV_ABS, ecodes.ABS_X, round(u * ESCALA_ABS))
        self._ponteiro.write(ecodes.EV_ABS, ecodes.ABS_Y, round(v * ESCALA_ABS))
        self._ponteiro.syn()

    def botao(self, codigo: int, pressionado: bool):
        self._ponteiro.write(ecodes.EV_KEY, codigo, int(pressionado))
        self._ponteiro.syn()

    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int):
        for codigo, valor in ((ecodes.REL_HWHEEL_HI_RES, horizontal_hr), (ecodes.REL_WHEEL_HI_RES, vertical_hr),
                              (ecodes.REL_HWHEEL, horizontal), (ecodes.REL_WHEEL, vertical)):
            if valor:
                self._ponteiro.write(ecodes.EV_REL, codigo, valor)
        self._ponteiro.syn()

    def tecla(self, codigo: int, pressionada: bool):
        self._teclado.write(ecodes.EV_KEY, codigo, int(pressionada))
        self._teclado.syn()

    def atalho_kwin(self, nome: str):
        # não bloqueia o laço de quadros: dispara e segue
        subprocess.Popen(
            ["busctl", "--user", "call", "org.kde.kglobalaccel", "/component/kwin",
             "org.kde.kglobalaccel.Component", "invokeShortcut", "s", nome],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def fechar(self):
        self._ponteiro.close()
        self._teclado.close()
