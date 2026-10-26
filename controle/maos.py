from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Mao:
    """Uma mão detectada num quadro já espelhado."""
    img: np.ndarray    # (21, 3) normalizado: x pela largura, y pela altura da imagem
    mundo: np.ndarray  # (21, 3) em metros, centrado na mão
    rotulo: str        # "Left" ou "Right", como o MediaPipe reporta
    confianca: float


@dataclass(frozen=True, slots=True)
class Quadro:
    t_ms: int
    maos: tuple[Mao, ...]
