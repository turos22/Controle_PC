from dataclasses import dataclass
from enum import Enum


class Tipo(Enum):
    APONTAR = "apontar"                    # x, y: nó do indicador (imagem, unidades de altura)
    CLIQUE = "clique"                      # valor: 1 esquerdo, 3 direito
    SEGURAR_INICIO = "segurar"
    ARRASTAR = "arrastar"                  # x, y: deslocamento da palma desde o último quadro
    SEGURAR_FIM = "soltar"
    ROLAGEM = "rolagem"                    # x > 0 direita, y > 0 cima; em entalhes (fração)
    EXPANDIR = "expandir"
    VISAO_GERAL = "visão geral"
    AREA_DE_TRABALHO = "área de trabalho"  # valor: -1 esquerda, +1 direita
    ALT_TAB_INICIO = "alt+tab"
    ALT_TAB_PROXIMO = "tab"
    ALT_TAB_ANTERIOR = "shift+tab"
    ALT_TAB_FIM = "solta alt"
    FECHAR_JANELA = "fechar janela"
    ZOOM_INICIO = "zoom: início"           # sessão de zoom (Ctrl fica segurado até o fim)
    ZOOM = "zoom"                          # valor: +1 aproxima, -1 afasta
    ZOOM_FIM = "zoom: fim"


@dataclass(frozen=True, slots=True)
class Evento:
    tipo: Tipo
    t_ms: int
    mao: int
    x: float = 0.0
    y: float = 0.0
    valor: int = 0
    t_ref: int = 0   # clique: quando a pinça começou (o cursor volta para onde estava)
