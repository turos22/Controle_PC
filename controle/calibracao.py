"""Calibração dos limiares de pose a partir de amostras da própria pessoa.

A pessoa faz cada pose por alguns segundos; os limiares ficam entre a faixa em que ela estica o dedo e a
faixa em que ela dobra, com uma folga. Um resultado só vale se classificar as amostras pelo menos tão
bem quanto os padrões e se ficar dentro de faixas seguras (mão de outra pessoa nunca deve poder
inutilizar o programa).
"""
import dataclasses
from dataclasses import dataclass, field

import numpy as np

from controle.geometria import Medidas
from controle.poses import LIMITES_PADRAO, Limites, Pose, classificar

PASSOS = (Pose.ABERTA, Pose.PUNHO, Pose.INDICADOR, Pose.DOIS_DEDOS, Pose.TRES_DEDOS, Pose.PINCA, Pose.L)
MINIMO_AMOSTRAS = 15
FOLGA = 0.03
FAIXAS = {  # (mínimo, máximo) de cada limiar ajustável
    "esticado": (0.74, 0.92), "dobrado": (0.53, 0.75), "aberta_minimo": (0.60, 0.85),
    "minimo_tres_dedos": (0.70, 0.92), "l_angulo_min": (35.0, 60.0), "pinca_max": (0.40, 0.90),
}


class Coletor:
    """Guarda as medidas de cada pose enquanto a pessoa a mantém."""

    def __init__(self):
        self.amostras: dict[Pose, list[Medidas]] = {}
        self._pose: Pose | None = None

    def iniciar(self, pose: Pose):
        self._pose = pose
        self.amostras.setdefault(pose, [])

    def adicionar(self, medidas: Medidas):
        if self._pose is not None and not medidas.na_borda:  # mão cortada pela borda mede errado
            self.amostras[self._pose].append(medidas)

    def quantidade(self, pose: Pose) -> int:
        return len(self.amostras.get(pose, []))


@dataclass
class Resultado:
    limites: Limites
    ajustados: dict[str, float] = field(default_factory=dict)
    acuracia_antes: float = 0.0
    acuracia_depois: float = 0.0
    por_pose: dict[Pose, tuple[float, float]] = field(default_factory=dict)  # (antes, depois)
    avisos: list[str] = field(default_factory=list)


def _acuracia(amostras: dict[Pose, list[Medidas]], limites: Limites) -> tuple[float, dict[Pose, float]]:
    por_pose = {p: float(np.mean([classificar(m, limites) is p for m in lista]))
                for p, lista in amostras.items() if lista}
    total = sum(len(lista) for lista in amostras.values())
    certas = sum(por_pose[p] * len(amostras[p]) for p in por_pose)
    return (certas / total if total else 0.0), por_pose


def _serie(amostras, poses, dedos) -> np.ndarray:
    """Valores de retidão dos `dedos` nas amostras de `poses`."""
    return np.array([m.retidao[d] for p in poses for m in amostras.get(p, []) for d in dedos])


def _limitar(nome: str, valor: float) -> float:
    return float(min(max(valor, FAIXAS[nome][0]), FAIXAS[nome][1]))


def _propor(amostras: dict[Pose, list[Medidas]], avisos: list[str]) -> dict[str, float]:
    p = {}
    suficientes = {pose for pose, lista in amostras.items() if len(lista) >= MINIMO_AMOSTRAS}
    for pose in amostras.keys() - suficientes:
        avisos.append(f"{pose.value}: só {len(amostras[pose])} amostras (mínimo {MINIMO_AMOSTRAS}); ignorada")
    ok = {pose: amostras[pose] for pose in suficientes}

    esticados = np.concatenate([
        _serie(ok, [Pose.INDICADOR, Pose.L, Pose.DOIS_DEDOS, Pose.TRES_DEDOS], "I"),
        _serie(ok, [Pose.DOIS_DEDOS, Pose.TRES_DEDOS], "M"),
        _serie(ok, [Pose.TRES_DEDOS], "A"),
    ])
    dobrados = np.concatenate([
        _serie(ok, [Pose.PUNHO], "IMAP"), _serie(ok, [Pose.INDICADOR, Pose.L], "MAP"),
        _serie(ok, [Pose.DOIS_DEDOS], "AP"), _serie(ok, [Pose.PINCA], "MAP"),
    ])
    if len(esticados) and len(dobrados):
        esticado = np.percentile(esticados, 10) - FOLGA
        dobrado = np.percentile(dobrados, 90) + FOLGA
        if dobrado + 0.05 <= esticado:
            p["esticado"], p["dobrado"] = _limitar("esticado", esticado), _limitar("dobrado", dobrado)
        else:
            avisos.append("dedos esticados e dobrados se confundem; limiares de dedo mantidos")

    aberta = _serie(ok, [Pose.ABERTA], "IMAP")
    if len(aberta):
        minimo_por_mao = [min(m.retidao[d] for d in "IMAP") for m in ok[Pose.ABERTA]]
        p["aberta_minimo"] = _limitar("aberta_minimo", np.percentile(minimo_por_mao, 10) - FOLGA)

    mindinho_tres, mindinho_aberta = _serie(ok, [Pose.TRES_DEDOS], "P"), _serie(ok, [Pose.ABERTA], "P")
    if len(mindinho_tres) and len(mindinho_aberta):
        a, b = np.percentile(mindinho_tres, 90), np.percentile(mindinho_aberta, 10)
        if a + 0.04 < b:
            p["minimo_tres_dedos"] = _limitar("minimo_tres_dedos", (a + b) / 2)
        else:
            avisos.append("mindinho de três dedos e de mão aberta se confundem; limiar mantido")

    if Pose.L in ok and Pose.INDICADOR in ok:
        a = np.percentile([m.angulo_polegar for m in ok[Pose.INDICADOR]], 90)
        b = np.percentile([m.angulo_polegar for m in ok[Pose.L]], 10)
        if a + 6 < b:
            p["l_angulo_min"] = _limitar("l_angulo_min", (a + b) / 2)
        else:
            avisos.append("polegar apontando e em L se confundem; ângulo mantido")

    if Pose.PINCA in ok:
        p["pinca_max"] = _limitar("pinca_max", np.percentile([m.pinca for m in ok[Pose.PINCA]], 90) + 0.05)
    return p


def calcular(amostras: dict[Pose, list[Medidas]], base: Limites = LIMITES_PADRAO) -> Resultado:
    avisos: list[str] = []
    proposta = _propor(amostras, avisos)
    antes, por_antes = _acuracia(amostras, base)
    candidato = dataclasses.replace(base, **proposta)
    depois, por_depois = _acuracia(amostras, candidato)
    if depois < antes:
        avisos.append("os limiares novos acertariam menos que os padrões; mantidos os padrões")
        candidato, proposta, depois, por_depois = base, {}, antes, por_antes
    ajustados = {k: v for k, v in proposta.items() if v != getattr(base, k)}
    return Resultado(limites=candidato, ajustados=ajustados, acuracia_antes=antes, acuracia_depois=depois,
                     por_pose={p: (por_antes[p], por_depois[p]) for p in por_antes}, avisos=avisos)
