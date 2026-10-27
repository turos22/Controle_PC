"""Linux: mouse e teclado virtuais por uinput; ações de janela pelo KWin (KDE).

uinput funciona no Wayland e no X11 porque é um dispositivo de entrada do kernel, não uma API do
servidor gráfico. Precisa de escrita em /dev/uinput.
"""
import subprocess

from evdev import AbsInfo, UInput, ecodes

from controle.plataforma.base import Acao, Botao, Tecla

ESCALA_ABS = 65535
CODIGO_BOTAO = {Botao.ESQUERDO: ecodes.BTN_LEFT, Botao.DIREITO: ecodes.BTN_RIGHT}
CODIGO_TECLA = {Tecla.ALT: ecodes.KEY_LEFTALT, Tecla.TAB: ecodes.KEY_TAB,
                Tecla.CTRL: ecodes.KEY_LEFTCTRL, Tecla.SHIFT: ecodes.KEY_LEFTSHIFT}
ATALHO_KWIN = {
    Acao.MAXIMIZAR: "Window Maximize",
    Acao.VISAO_GERAL: "Overview",
    Acao.AREA_ESQUERDA: "Switch One Desktop to the Left",
    Acao.AREA_DIREITA: "Switch One Desktop to the Right",
    Acao.FECHAR_JANELA: "Window Close",
}


class EntradaUinput:
    """Mouse absoluto + teclado virtuais."""

    def __init__(self):
        e = ecodes
        eixo = AbsInfo(value=0, min=0, max=ESCALA_ABS, fuzz=0, flat=0, resolution=0)
        self._ponteiro = UInput({
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
            e.EV_ABS: [(e.ABS_X, eixo), (e.ABS_Y, eixo)],
            e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL, e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES],
        }, name="cv-controle-do-pc ponteiro")
        self._teclado = UInput({e.EV_KEY: list(CODIGO_TECLA.values())}, name="cv-controle-do-pc teclado")

    def mover_absoluto(self, u: float, v: float):
        self._ponteiro.write(ecodes.EV_ABS, ecodes.ABS_X, round(u * ESCALA_ABS))
        self._ponteiro.write(ecodes.EV_ABS, ecodes.ABS_Y, round(v * ESCALA_ABS))
        self._ponteiro.syn()

    def botao(self, botao: Botao, pressionado: bool):
        self._ponteiro.write(ecodes.EV_KEY, CODIGO_BOTAO[botao], int(pressionado))
        self._ponteiro.syn()

    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int):
        for codigo, valor in ((ecodes.REL_HWHEEL_HI_RES, horizontal_hr), (ecodes.REL_WHEEL_HI_RES, vertical_hr),
                              (ecodes.REL_HWHEEL, horizontal), (ecodes.REL_WHEEL, vertical)):
            if valor:
                self._ponteiro.write(ecodes.EV_REL, codigo, valor)
        self._ponteiro.syn()

    def tecla(self, tecla: Tecla, pressionada: bool):
        self._teclado.write(ecodes.EV_KEY, CODIGO_TECLA[tecla], int(pressionada))
        self._teclado.syn()

    def fechar(self):
        self._ponteiro.close()
        self._teclado.close()


def comando_kwin(acao: Acao) -> list[str]:
    return ["busctl", "--user", "call", "org.kde.kglobalaccel", "/component/kwin",
            "org.kde.kglobalaccel.Component", "invokeShortcut", "s", ATALHO_KWIN[acao]]


class AcoesKWin:
    """Aciona os atalhos do KWin pelo nome via D-Bus: independe da tecla configurada."""

    def executar(self, acao: Acao):
        # não bloqueia o laço de quadros: dispara e segue
        subprocess.Popen(comando_kwin(acao), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
