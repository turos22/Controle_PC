"""Medidas de uma mão a partir dos 21 landmarks do MediaPipe. Funções puras."""
from dataclasses import dataclass

import numpy as np

from controle.maos import Mao

PULSO = 0
# cadeia usada na retidão de cada dedo; nos quatro dedos longos parte do pulso,
# para que a dobra no nó (MCP) também conte
CADEIAS = {
    "T": (1, 2, 3, 4),
    "I": (PULSO, 6, 7, 8),
    "M": (PULSO, 10, 11, 12),
    "A": (PULSO, 14, 15, 16),
    "P": (PULSO, 18, 19, 20),
}
MCP_INDICADOR, PONTA_INDICADOR = 5, 8
MCP_MEDIO, PONTA_MEDIO = 9, 12
MCP_MINIMO = 17
MCP_POLEGAR, PONTA_POLEGAR = 2, 4
BASE_PALMA = (0, 5, 9, 13, 17)
MARGEM_BORDA = 0.02


@dataclass(frozen=True, slots=True)
class Medidas:
    retidao: dict[str, float]         # 1 = dedo reto; ~0,4 = enrolado
    pinca: float                      # distância polegar–indicador / largura da palma
    pinca_medio: float                # distância polegar–médio / largura da palma (clique direito)
    angulo_polegar: float             # graus entre polegar e indicador (3D): ~70 no "L", <35 apontando
    afastamento_polegar: float        # ponta do polegar ao nó do indicador / largura da palma
    polegar_dy: float                 # direção do polegar na imagem: +1 para baixo, -1 para cima
    centro: tuple[float, float]       # centro da palma; imagem em unidades de altura
    no_indicador: tuple[float, float]  # nó (MCP) do indicador: quase não se mexe na pinça
    tamanho: float                    # pulso → nó do médio na imagem (unidades de altura)
    na_borda: bool                    # palma encostando na borda: mão parcialmente fora do quadro


def retidao(pontos: np.ndarray) -> float:
    """Distância da base à ponta dividida pela soma dos segmentos."""
    segmentos = np.linalg.norm(np.diff(pontos, axis=0), axis=1).sum()
    return float(np.linalg.norm(pontos[-1] - pontos[0]) / segmentos) if segmentos else 0.0


def _angulo(u: np.ndarray, v: np.ndarray) -> float:
    cos = float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) or 1e-9))
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def medir(mao: Mao, aspecto: float = 16 / 9) -> Medidas:
    w = mao.mundo
    escala = np.array([aspecto, 1.0])
    p2 = mao.img[:, :2] * escala
    largura_palma = float(np.linalg.norm(w[MCP_INDICADOR] - w[MCP_MINIMO])) or 1e-9
    palma = mao.img[list(BASE_PALMA), :2]
    polegar = p2[PONTA_POLEGAR] - p2[MCP_POLEGAR]
    return Medidas(
        retidao={nome: retidao(w[list(cadeia)]) for nome, cadeia in CADEIAS.items()},
        pinca=float(np.linalg.norm(w[PONTA_POLEGAR] - w[PONTA_INDICADOR])) / largura_palma,
        pinca_medio=float(np.linalg.norm(w[PONTA_POLEGAR] - w[PONTA_MEDIO])) / largura_palma,
        angulo_polegar=_angulo(w[PONTA_POLEGAR] - w[MCP_POLEGAR], w[PONTA_INDICADOR] - w[MCP_INDICADOR]),
        afastamento_polegar=float(np.linalg.norm(w[PONTA_POLEGAR] - w[MCP_INDICADOR])) / largura_palma,
        polegar_dy=float(polegar[1] / (np.linalg.norm(polegar) or 1e-9)),
        centro=tuple(p2[list(BASE_PALMA)].mean(axis=0)),
        no_indicador=tuple(p2[MCP_INDICADOR]),
        tamanho=float(np.linalg.norm(p2[MCP_MEDIO] - p2[PULSO])),
        na_borda=bool(np.any((palma < MARGEM_BORDA) | (palma > 1 - MARGEM_BORDA))),
    )
