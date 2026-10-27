"""Calibração dos limiares de pose a partir de amostras da própria pessoa.

A pessoa faz cada pose por alguns segundos; os limiares ficam entre a faixa em que ela estica o dedo e a
faixa em que ela dobra, com uma folga. Um resultado só vale se classificar as amostras pelo menos tão
bem quanto os padrões e se ficar dentro de faixas seguras (mão de outra pessoa nunca deve poder
inutilizar o programa).
"""
import dataclasses
from enum import Enum
from dataclasses import dataclass, field

import numpy as np

from controle.geometria import Medidas
from controle.idioma import tr
from controle.poses import LIMITES_PADRAO, Limites, Pose, classificar

PASSOS = (Pose.ABERTA, Pose.PUNHO, Pose.INDICADOR, Pose.DOIS_DEDOS, Pose.TRES_DEDOS, Pose.PINCA, Pose.L)
INSTRUCOES = {
    Pose.ABERTA: "Mão aberta, dedos afastados, palma para a câmera.",
    Pose.PUNHO: "Mão fechada em punho.",
    Pose.INDICADOR: "Só o indicador esticado, como se apontasse.",
    Pose.DOIS_DEDOS: "Indicador e médio esticados (um V); os outros dobrados.",
    Pose.TRES_DEDOS: "Indicador, médio e anelar esticados; mindinho e polegar dobrados.",
    Pose.PINCA: "Pinça: ponta do polegar encostada na ponta do indicador; os outros dedos dobrados.",
    Pose.L: "Indicador esticado e polegar bem aberto, formando um L; os outros dobrados.",
}
MINIMO_AMOSTRAS = 15
ACURACIA_MINIMA = 0.8  # os limiares novos precisam classificar ao menos isso das poses gravadas
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
        avisos.append(tr("{pose}: só {n} amostras (mínimo {minimo}); ignorada", pose=tr(pose.value),
                         n=len(amostras[pose]), minimo=MINIMO_AMOSTRAS))
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
            avisos.append(tr("dedos esticados e dobrados se confundem; limiares de dedo mantidos"))

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
            avisos.append(tr("mindinho de três dedos e de mão aberta se confundem; limiar mantido"))

    if Pose.L in ok and Pose.INDICADOR in ok:
        a = np.percentile([m.angulo_polegar for m in ok[Pose.INDICADOR]], 90)
        b = np.percentile([m.angulo_polegar for m in ok[Pose.L]], 10)
        if a + 6 < b:
            p["l_angulo_min"] = _limitar("l_angulo_min", (a + b) / 2)
        else:
            avisos.append(tr("polegar apontando e em L se confundem; ângulo mantido"))

    if Pose.PINCA in ok:
        p["pinca_max"] = _limitar("pinca_max", np.percentile([m.pinca for m in ok[Pose.PINCA]], 90) + 0.05)
    return p


def calcular(amostras: dict[Pose, list[Medidas]], base: Limites = LIMITES_PADRAO) -> Resultado:
    avisos: list[str] = []
    proposta = _propor(amostras, avisos)
    antes, por_antes = _acuracia(amostras, base)
    candidato = dataclasses.replace(base, **proposta)
    depois, por_depois = _acuracia(amostras, candidato)
    if depois < antes or depois < ACURACIA_MINIMA:
        avisos.append(tr("não consegui separar bem as suas poses (ou os limiares novos acertariam menos que os "
                         "padrões); mantidos os padrões. Repita a calibração com calma."))
        candidato, proposta, depois, por_depois = base, {}, antes, por_antes
    ajustados = {k: v for k, v in proposta.items() if v != getattr(base, k)}
    return Resultado(limites=candidato, ajustados=ajustados, acuracia_antes=antes, acuracia_depois=depois,
                     por_pose={p: (por_antes[p], por_depois[p]) for p in por_antes}, avisos=avisos)


class Fase(Enum):
    PREPARAR = "preparar"   # a pessoa se posiciona; nada é coletado
    GRAVAR = "gravar"
    FIM = "fim"


MAX_TENTATIVAS = 2
EPS = 1e-9


class Sessao:
    """Conduz a pessoa pelas poses, uma por vez: prepara, grava, e repete o passo se faltou amostra.

    O tempo vem de fora (`atualizar(agora, ...)`), então a mesma lógica serve à interface e aos testes.
    """

    def __init__(self, passos=PASSOS, preparo_s: float = 2.5, captura_s: float = 3.0, descarte_s: float = 0.6):
        self.passos, self.preparo_s, self.captura_s, self.descarte_s = tuple(passos), preparo_s, captura_s, descarte_s
        self.coletor = Coletor()
        self.indice = 0
        self.tentativa = 1
        self.fase = Fase.PREPARAR
        self.progresso = 0.0
        self._inicio: float | None = None
        self._cancelada = False

    @property
    def concluida(self) -> bool:
        return self._cancelada or self.indice >= len(self.passos)

    @property
    def pose_atual(self) -> Pose | None:
        return None if self.concluida else self.passos[self.indice]

    def cancelar(self):
        self._cancelada = True
        self.fase = Fase.FIM

    def atualizar(self, agora: float, medidas: list[Medidas]):
        if self.concluida:
            return
        if self._inicio is None:
            self._inicio = agora
            if self.fase is Fase.GRAVAR:
                self.coletor.iniciar(self.pose_atual)
        decorrido = agora - self._inicio
        if self.fase is Fase.PREPARAR:
            self.progresso = min(decorrido / self.preparo_s, 1.0)
            if decorrido + EPS >= self.preparo_s:
                self.fase, self._inicio, self.progresso = Fase.GRAVAR, agora, 0.0
                self.coletor.iniciar(self.pose_atual)
            return
        self.progresso = min(decorrido / self.captura_s, 1.0)
        if decorrido + EPS >= self.descarte_s and medidas:
            self.coletor.adicionar(max(medidas, key=lambda m: m.tamanho))
        if decorrido + EPS >= self.captura_s:
            self._terminar_passo()

    def _terminar_passo(self):
        pose = self.pose_atual
        faltou = self.coletor.quantidade(pose) < MINIMO_AMOSTRAS
        if faltou and self.tentativa < MAX_TENTATIVAS:
            self.coletor.amostras[pose] = []
            self.tentativa += 1
        else:
            self.indice += 1
            self.tentativa = 1
        self.fase = Fase.FIM if self.concluida else Fase.PREPARAR
        self._inicio, self.progresso = None, 0.0

    def resultado(self) -> Resultado:
        return calcular(self.coletor.amostras)
