"""Orquestra as mãos de cada quadro: identidade, máquinas por mão, zoom e posse do cursor."""
import math
from dataclasses import dataclass

from controle.eventos import Evento, Tipo
from controle.geometria import Medidas, medir
from controle.gestos import MaquinaMao, Parametros
from controle.maos import Quadro
from controle.poses import LIMITES_PADRAO, Limites, Pose, classificar

POSES_ZOOM = frozenset({Pose.C, Pose.PINCA})
LIBERAM_CURSOR = frozenset({Pose.ABERTA, Pose.L, Pose.C})
DURANTE_ARRASTE = frozenset({Tipo.ARRASTAR, Tipo.SEGURAR_INICIO, Tipo.SEGURAR_FIM, Tipo.ALT_TAB_FIM})
DURANTE_ZOOM = frozenset({Tipo.ZOOM_INICIO, Tipo.ZOOM, Tipo.ZOOM_FIM, Tipo.SEGURAR_FIM, Tipo.ALT_TAB_FIM})


def so_o_arraste(eventos: list[Evento]) -> list[Evento]:
    """Enquanto alguma mão arrasta, nada mais acontece (só o arraste e solturas)."""
    return [e for e in eventos if e.tipo in DURANTE_ARRASTE]


class Rastreador:
    """Dá a cada mão uma identidade estável pela proximidade entre quadros.

    O rótulo Left/Right do MediaPipe troca sozinho às vezes; a posição não.
    """

    def __init__(self, distancia_max: float = 0.5, perda_ms: int = 300):
        self.distancia_max, self.perda_ms = distancia_max, perda_ms
        self._trilhas: dict[int, tuple[tuple[float, float], int]] = {}
        self._proximo = 1

    def atualizar(self, t: int, centros: list[tuple[float, float]]) -> tuple[list[int], list[int]]:
        pares = sorted(
            (math.dist(c, pos), i, ident)
            for i, c in enumerate(centros) for ident, (pos, _) in self._trilhas.items()
        )
        ids: list[int | None] = [None] * len(centros)
        usadas = set()
        for distancia, i, ident in pares:
            if distancia <= self.distancia_max and ids[i] is None and ident not in usadas:
                ids[i] = ident
                usadas.add(ident)
        for i, c in enumerate(centros):
            if ids[i] is None:
                ids[i] = self._proximo
                self._proximo += 1
            self._trilhas[ids[i]] = (c, t)
        perdidas = [ident for ident, (_, visto) in self._trilhas.items() if t - visto > self.perda_ms]
        for ident in perdidas:
            del self._trilhas[ident]
        return ids, perdidas


@dataclass(frozen=True, slots=True)
class CandidataZoom:
    ident: int
    pose: Pose            # pose estável
    centro: tuple[float, float]
    desde_ms: int         # desde quando a pose estável vale
    ocupada: bool         # arrastando (pinça só parada, pronta para arrastar, não impede o zoom)


class DetectorZoom:
    """Duas mãos em C (ou pinça): afastar aproxima, juntar afasta. Um passo a cada ~10%.

    Só liga se as duas mãos formaram a pose perto no tempo e nenhuma está segurando algo: uma
    mão em repouso com os dedos curvos parece um C e não pode sequestrar o arraste da outra.
    """

    def __init__(self, passo: float = 0.1, sincronia_ms: int = 3000, religar_ms: int = 2000):
        self.passo, self.sincronia_ms, self.religar_ms = passo, sincronia_ms, religar_ms
        self.ativo: set[int] = set()
        self._referencia = 0.0
        self._ultimo_ativo_ms = None

    def _desligar(self, t: int) -> list[Evento]:
        if not self.ativo:
            return []
        self.ativo, self._ultimo_ativo_ms = set(), t
        return [Evento(Tipo.ZOOM_FIM, t, 0)]

    def atualizar(self, t: int, maos: list[CandidataZoom]) -> list[Evento]:
        candidatas = [m for m in maos if m.pose in POSES_ZOOM]
        if len(candidatas) != 2 or len(maos) != 2:
            return self._desligar(t)
        a, b = candidatas
        distancia = max(math.dist(a.centro, b.centro), 1e-6)
        if self.ativo != {a.ident, b.ident}:
            ev = self._desligar(t)
            # reajustar uma das mãos no meio da sessão religa mesmo com a outra em pinça há tempo
            recente = self._ultimo_ativo_ms is not None and t - self._ultimo_ativo_ms <= self.religar_ms
            if a.ocupada or b.ocupada or (abs(a.desde_ms - b.desde_ms) > self.sincronia_ms and not recente):
                return ev
            self.ativo, self._referencia, self._ultimo_ativo_ms = {a.ident, b.ident}, distancia, t
            return ev + [Evento(Tipo.ZOOM_INICIO, t, 0)]
        self._ultimo_ativo_ms = t
        ev = []
        razao = math.log(distancia / self._referencia)
        while abs(razao) >= self.passo:
            sinal = 1 if razao > 0 else -1
            ev.append(Evento(Tipo.ZOOM, t, 0, valor=sinal))
            self._referencia *= math.exp(sinal * self.passo)
            razao -= sinal * self.passo
        return ev


@dataclass(frozen=True, slots=True)
class EstadoMao:
    ident: int
    rotulo: str
    pose: Pose
    medidas: Medidas
    dono_cursor: bool
    em_zoom: bool
    progresso_fechar: float = 0.0


class Reconhecedor:
    def __init__(self, params: Parametros | None = None, aspecto: float = 16 / 9,
                 limites: Limites = LIMITES_PADRAO):
        self.params = params or Parametros()
        self.limites = limites
        self.aspecto = aspecto
        self.rastreador = Rastreador()
        self.zoom = DetectorZoom()
        self.maquinas: dict[int, MaquinaMao] = {}
        self.dono_cursor: int | None = None
        self.estado: list[EstadoMao] = []

    def processar(self, quadro: Quadro) -> list[Evento]:
        t = quadro.t_ms
        medidas = [medir(mao, self.aspecto) for mao in quadro.maos]
        ids, perdidas = self.rastreador.atualizar(t, [m.centro for m in medidas])
        ev: list[Evento] = []
        for ident in perdidas:
            ev += self.maquinas.pop(ident).encerrar(t)
            if self.dono_cursor == ident:
                self.dono_cursor = None
        # zoom decide com as poses estáveis do quadro anterior, antes das máquinas rodarem
        arrastando = any(q.arrastando for q in self.maquinas.values())
        ev += [] if arrastando else self.zoom.atualizar(t, [
            CandidataZoom(i, q.pose, m.centro, q.filtro.desde_ms, q.arrastando)
            for i, m in zip(ids, medidas) if (q := self.maquinas.get(i)) is not None
        ])
        arrastam = {i for i, q in self.maquinas.items() if q.arrastando}
        for i, m in zip(ids, medidas):
            maquina = self.maquinas.setdefault(i, MaquinaMao(i, self.params))
            maquina.em_zoom = i in self.zoom.ativo
            # arrastando ou em zoom, nenhum outro gesto começa; depois, cada mão precisa mudar de pose
            maquina.bloqueada = (bool(arrastam) and i not in arrastam) or maquina.em_zoom
            for e in maquina.atualizar(t, m, classificar(m, self.limites)):
                if e.tipo is Tipo.APONTAR:
                    if self.dono_cursor is None:
                        self.dono_cursor = i
                    if self.dono_cursor != i:
                        continue
                ev.append(e)
        dono = self.maquinas.get(self.dono_cursor)
        if dono is None or dono.pose in LIBERAM_CURSOR:
            self.dono_cursor = None
        self.estado = [EstadoMao(i, mao.rotulo, self.maquinas[i].pose, m, i == self.dono_cursor,
                                 self.maquinas[i].em_zoom, self.maquinas[i].progresso_fechar)
                       for i, mao, m in zip(ids, quadro.maos, medidas)]
        if any(q.arrastando for q in self.maquinas.values()):
            ev = so_o_arraste(ev)
        if self.zoom.ativo:
            ev = [e for e in ev if e.tipo in DURANTE_ZOOM]
        return ev

    def reiniciar(self, t: int) -> list[Evento]:
        """Pausa: solta tudo que estiver pressionado e esquece as mãos."""
        ev = [e for maquina in self.maquinas.values() for e in maquina.encerrar(t)]
        self.__init__(self.params, self.aspecto)
        return ev
