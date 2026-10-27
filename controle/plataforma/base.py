"""Vocabulário neutro entre o reconhecimento e o sistema operacional.

O executor fala só em `Botao`, `Tecla` e `Acao`; cada sistema traduz para o seu jeito (uinput e
KWin no Linux; SendInput no Windows; Quartz no macOS).
"""
from enum import Enum
from typing import Protocol


class Botao(Enum):
    ESQUERDO = "esquerdo"
    DIREITO = "direito"


class Tecla(Enum):
    ALT = "alt"
    TAB = "tab"
    CTRL = "ctrl"
    SHIFT = "shift"
    META = "meta"            # tecla Windows, Super ou Comando
    CIMA = "cima"
    ESQUERDA = "esquerda"
    DIREITA = "direita"
    PAGE_UP = "page up"
    PAGE_DOWN = "page down"
    F4 = "f4"
    W = "w"
    F = "f"


class Acao(Enum):
    """Ações de janela, que cada ambiente executa do seu jeito (D-Bus, atalho de teclado...)."""
    MAXIMIZAR = "maximizar"
    VISAO_GERAL = "visão geral"
    AREA_ESQUERDA = "área à esquerda"
    AREA_DIREITA = "área à direita"
    FECHAR_JANELA = "fechar janela"


class Entrada(Protocol):
    """Mouse e teclado do sistema.

    Pode declarar `modificador_troca` (Alt no Windows e no Linux, Comando no macOS) e
    `modificador_zoom` (Ctrl; Comando no macOS); sem declarar, valem Alt e Ctrl.
    """

    def mover_absoluto(self, u: float, v: float) -> None:
        """Posição em [0, 1] sobre a área que envolve todas as telas."""

    def botao(self, botao: Botao, pressionado: bool) -> None: ...

    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int) -> None:
        """Roda: alta resolução (120 por entalhe) e entalhes inteiros; x > 0 direita, y > 0 cima."""

    def tecla(self, tecla: Tecla, pressionada: bool) -> None: ...

    def fechar(self) -> None: ...


class AcoesJanela(Protocol):
    def executar(self, acao: Acao) -> None: ...


class EntradaNula:
    """Modo demonstração: reconhece e mostra os gestos sem agir no sistema."""

    modificador_troca = Tecla.ALT
    modificador_zoom = Tecla.CTRL

    def mover_absoluto(self, u, v): pass
    def botao(self, botao, pressionado): pass
    def rolar(self, horizontal_hr, vertical_hr, horizontal, vertical): pass
    def tecla(self, tecla, pressionada): pass
    def fechar(self): pass


class AcoesNulas:
    def executar(self, acao): pass
