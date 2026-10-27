"""Windows: mouse e teclado virtuais por SendInput (ctypes, sem dependências).

Posição absoluta em [0, 65535] sobre a área virtual (todas as telas), então a escala de DPI de cada
tela não interfere. Verificado só pelos testes com `enviar` substituído; o envio real exige o Windows.
"""
import ctypes
from ctypes import wintypes

from controle.plataforma.base import Botao, Tecla

ESCALA_ABS = 65535

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010
MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL = 0x0800, 0x1000
MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_ABSOLUTE = 0x4000, 0x8000
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x0001, 0x0002

CODIGO_TECLA = {
    Tecla.ALT: 0x12, Tecla.TAB: 0x09, Tecla.CTRL: 0x11, Tecla.SHIFT: 0x10, Tecla.META: 0x5B,
    Tecla.CIMA: 0x26, Tecla.ESQUERDA: 0x25, Tecla.DIREITA: 0x27, Tecla.PAGE_UP: 0x21,
    Tecla.PAGE_DOWN: 0x22, Tecla.F4: 0x73, Tecla.W: 0x57, Tecla.F: 0x46,
}
ESTENDIDAS = frozenset({Tecla.META, Tecla.CIMA, Tecla.ESQUERDA, Tecla.DIREITA, Tecla.PAGE_UP, Tecla.PAGE_DOWN})
BOTOES = {Botao.ESQUERDO: (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
          Botao.DIREITO: (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.WPARAM)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.WPARAM)]


class _UNIAO(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _UNIAO)]


def _mouse(flags: int, dx: int = 0, dy: int = 0, dados: int = 0) -> INPUT:
    return INPUT(INPUT_MOUSE, _UNIAO(mi=MOUSEINPUT(dx, dy, dados & 0xFFFFFFFF, flags, 0, 0)))


def _teclado(tecla: Tecla, pressionada: bool) -> INPUT:
    flags = (KEYEVENTF_EXTENDEDKEY if tecla in ESTENDIDAS else 0) | (0 if pressionada else KEYEVENTF_KEYUP)
    return INPUT(INPUT_KEYBOARD, _UNIAO(ki=KEYBDINPUT(CODIGO_TECLA[tecla], 0, flags, 0, 0)))


def _enviar_pelo_windows(itens: list[INPUT]):
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    except AttributeError as erro:
        raise OSError("SendInput só existe no Windows") from erro
    vetor = (INPUT * len(itens))(*itens)
    if user32.SendInput(len(itens), vetor, ctypes.sizeof(INPUT)) != len(itens):
        raise OSError("o Windows recusou a entrada (janela com privilégio maior, ou bloqueio de segurança)")


class EntradaWindows:
    modificador_troca = Tecla.ALT
    modificador_zoom = Tecla.CTRL

    def __init__(self, enviar=None):
        if enviar is None:
            if not hasattr(ctypes, "windll"):
                raise OSError("SendInput só existe no Windows")
            enviar = _enviar_pelo_windows
        self._enviar = enviar

    def mover_absoluto(self, u: float, v: float):
        dx, dy = (round(min(max(c, 0.0), 1.0) * ESCALA_ABS) for c in (u, v))
        self._enviar([_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, dx, dy)])

    def botao(self, botao: Botao, pressionado: bool):
        baixo, cima = BOTOES[botao]
        self._enviar([_mouse(baixo if pressionado else cima)])

    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int):
        itens = [_mouse(flag, dados=valor)
                 for flag, valor in ((MOUSEEVENTF_HWHEEL, horizontal_hr), (MOUSEEVENTF_WHEEL, vertical_hr)) if valor]
        if itens:
            self._enviar(itens)

    def tecla(self, tecla: Tecla, pressionada: bool):
        self._enviar([_teclado(tecla, pressionada)])

    def fechar(self):
        pass
