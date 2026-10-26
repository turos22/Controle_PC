"""Gestos temporais de uma mão: transforma (tempo, medidas, pose) em eventos.

Limiares calibrados nos vídeos de referência e no teste ao vivo (spec, R4 e "Iteração 2").
Tempos em ms, posições em unidades de altura da imagem espelhada.
"""
import math
from collections import deque
from dataclasses import dataclass

from controle.eventos import Evento, Tipo
from controle.geometria import Medidas
from controle.poses import FECHADAS, Pose

NAO_FECHADAS = frozenset({Pose.INDICADOR, Pose.DOIS_DEDOS, Pose.TRES_DEDOS, Pose.C, Pose.L, Pose.ABERTA})
VARREDURA = frozenset({Pose.ABERTA, Pose.DESCONHECIDA})  # na varredura rápida a pose borra
FOLGA = 1e-9


@dataclass(frozen=True)
class Parametros:
    quadros_estaveis: int = 3           # quadros seguidos para uma pose valer
    desconhecida_max_ms: int = 300      # quadros "?" ignorados até esse tempo
    # clique: pinça rápida a partir do indicador apontando
    pinca_fecha: float = 0.35           # pontas a até 0,35 palma: encostou
    pinca_abre: float = 0.55            # acima disso: soltou (histerese entre os dois)
    clique_max_ms: int = 350
    clique_palma_max: float = 0.04      # a palma não pode andar mais que isso durante a pinça
    duplo_clique_ms: int = 500          # segunda pinça pode começar até aqui depois de apontar
    toque_ambiguo: float = 0.40         # polegar a menos disso dos dois dedos: não sabe qual, não clica
    # rolagem joystick
    rolagem_zona: float = 0.03          # zona morta em volta do centro
    rolagem_ganho: float = 60.0         # entalhes por segundo por unidade além da zona morta
    rolagem_max: float = 20.0           # entalhes por segundo
    rolagem_pos_clique_ms: int = 500    # depois de um clique o centro do joystick acompanha a mão
    # Alt+Tab com três dedos
    alttab_degrau: float = 0.08         # deslocamento lateral por janela
    # fechar com polegar para baixo
    fechar_espera_ms: int = 800
    fechar_intervalo_ms: int = 2000
    # mão fechada: expandir, visão geral, arrastar
    l_espera_ms: int = 300
    l_janela_ms: int = 600              # o L precisa vir até esse tempo depois da mão fechada
    l_fechada_min_ms: int = 250         # pinça rápida (clique, ajeitar a mão) seguida de L não expande
    aberta_recente_ms: int = 400        # visão geral: a mão estava aberta antes de fechar
    visao_fechada_max_ms: int = 1500
    arrasto_min: float = 0.08
    arrasto_espera_ms: int = 200        # mão fechada parada antes de o arraste poder começar
    arrasto_viu_abrir_ms: int = 1000    # a mão precisa ter sido vista aberta pouco antes de fechar
    tamanho_estavel: float = 0.85       # fração do tamanho de referência
    palma_parada: float = 0.012         # deslocamento da palma por quadro considerado parado
    # troca de área
    varredura_distancia: float = 0.30
    varredura_janela_ms: int = 300
    varredura_dominancia: float = 2.0
    varredura_rearme_ms: int = 150      # mão parada esse tempo antes de valer outra troca
    varredura_fora_ms: int = 300        # ou esse tempo fora da mão aberta


class FiltroPose:
    """Pose estável: muda só depois de N quadros iguais; "?" curtos não contam."""

    def __init__(self, p: Parametros):
        self.p = p
        self.estavel = Pose.DESCONHECIDA
        self.desde_ms = 0
        self._candidata, self._contagem, self._candidata_desde = None, 0, 0
        self._ultima_conhecida_ms = None

    def atualizar(self, t: int, pose: Pose) -> Pose:
        if pose is Pose.DESCONHECIDA:
            if self._ultima_conhecida_ms is None or t - self._ultima_conhecida_ms > self.p.desconhecida_max_ms:
                self._mudar(Pose.DESCONHECIDA, t)
            return self.estavel
        self._ultima_conhecida_ms = t
        if pose is self._candidata:
            self._contagem += 1
        else:
            self._candidata, self._contagem, self._candidata_desde = pose, 1, t
        if self._contagem >= self.p.quadros_estaveis:
            self._mudar(pose, self._candidata_desde)
        return self.estavel

    def _mudar(self, pose: Pose, desde: int):
        if pose is not self.estavel:
            self.estavel, self.desde_ms = pose, desde


class DetectorToquePolegar:
    """Polegar encosta num dedo e solta rápido, com a mão parada: indicador = clique esquerdo,
    médio = clique direito. O dedo é o que chegou mais perto do polegar; se os dois chegaram perto,
    é ambíguo e não clica.

    Usa as distâncias brutas das pontas (com histerese), não a pose estável: um toque dura ~4-8
    quadros, pouco mais que os 3 que a pose estável precisa para mudar.
    """

    def __init__(self, p: Parametros):
        self.p = p
        self.reiniciar()

    def reiniciar(self):
        self._desde = None
        self._centro = (0.0, 0.0)
        self._valido = False
        self._menor = [9.0, 9.0]  # menor distância do polegar ao indicador e ao médio

    @property
    def em_andamento(self) -> bool:
        return self._desde is not None

    def atualizar(self, t: int, m: Medidas, pode_comecar: bool) -> tuple[int, int] | None:
        """(botão, instante em que o toque começou) se acabou de virar clique; senão None."""
        p = self.p
        distancias = (m.pinca, m.pinca_medio)
        if self._desde is None:
            if min(distancias) <= p.pinca_fecha and pode_comecar:
                self._desde, self._centro, self._valido = t, m.centro, True
                self._menor = list(distancias)
            return None
        self._menor = [min(a, b) for a, b in zip(self._menor, distancias)]
        andou = math.dist(m.centro, self._centro) > p.clique_palma_max
        self._valido = self._valido and not andou and t - self._desde <= p.clique_max_ms
        dedo = 1 if self._menor[1] < self._menor[0] else 0
        if distancias[dedo] < p.pinca_abre:
            return None
        inicio, self._desde = self._desde, None
        if not self._valido or max(self._menor) <= p.toque_ambiguo:
            return None
        return (3 if dedo == 1 else 1), inicio


@dataclass
class _Fechada:
    inicio_ms: int
    centro: tuple[float, float]
    tamanho: float
    veio_de_aberta: bool
    viu_abrir: bool                    # houve pose aberta pouco antes: não é mão que entrou fechada
    parada_desde_ms: int
    armada: bool = False               # ficou parada o bastante: pode virar arraste
    arrastando: bool = False
    ultimo_centro: tuple[float, float] | None = None


class MaquinaMao:
    def __init__(self, ident: int, p: Parametros):
        self.ident, self.p = ident, p
        self.filtro = FiltroPose(p)
        self.em_zoom = False
        self.bloqueada = False                # outra mão arrastando: não começa nenhum gesto
        self._pose_bloqueio: Pose | None = None
        self.progresso_fechar = 0.0
        self._ultimo_apontando_ms = None     # última vez com pose estável indicador ou dois dedos
        self._anterior: Medidas | None = None
        self._toque = DetectorToquePolegar(p)
        self._ultimo_clique_ms = None
        self._joystick: tuple[float, float] | None = None
        self._joystick_ms = 0
        self._alttab: float | None = None     # posição x do último degrau; None = fora do Alt+Tab
        self._fechou_neste_gesto = False
        self._ultimo_fechar_ms = None
        self._fechada: _Fechada | None = None
        self._fim_fechada_ms = None
        self._ultima_aberta_ms = None
        self._ultima_nao_fechada_ms = None
        self._l_expandiu = False
        self._hist_aberta: deque = deque()
        self._varredura_armada = True
        self._parada_desde_ms = None

    @property
    def pose(self) -> Pose:
        return self.filtro.estavel

    @property
    def arrastando(self) -> bool:
        return self._fechada is not None and self._fechada.arrastando

    def atualizar(self, t: int, m: Medidas, pose_bruta: Pose) -> list[Evento]:
        estavel = self.filtro.atualizar(t, pose_bruta)
        ev: list[Evento] = []
        if self.bloqueada or self._pose_bloqueio is estavel:
            # bloqueada, ou ainda na mesma pose de quando estava: só solta o que estiver segurando
            self._pose_bloqueio = estavel
            self._bloquear(t, ev)
            self._anterior = m
            return ev
        self._pose_bloqueio = None
        self._indicador(t, m, estavel, ev)
        self._rolagem(t, m, estavel, ev)
        self._alt_tab(t, m, estavel, ev)
        self._fechar(t, estavel, ev)
        self._mao_fechada(t, m, estavel, pose_bruta, ev)
        self._l(t, estavel, ev)
        self._aberta(t, m, estavel, pose_bruta, ev)
        if estavel is Pose.ABERTA:
            self._ultima_aberta_ms = t
        if estavel in NAO_FECHADAS:
            self._ultima_nao_fechada_ms = t
        self._anterior = m
        return ev

    def encerrar(self, t: int) -> list[Evento]:
        """A mão sumiu: solta qualquer botão ou tecla que esteja pressionado."""
        ev: list[Evento] = []
        self._sair_da_fechada(t, None, ev)
        if self._alttab is not None:
            ev.append(Evento(Tipo.ALT_TAB_FIM, t, self.ident))
            self._alttab = None
        return ev

    def _bloquear(self, t: int, ev: list[Evento]):
        self._toque.reiniciar()
        self._joystick = None
        self.progresso_fechar = 0.0
        self._hist_aberta.clear()
        if self._alttab is not None:
            ev.append(Evento(Tipo.ALT_TAB_FIM, t, self.ident))
            self._alttab = None
        if self._fechada is not None and not self._fechada.arrastando:
            self._fechada = None
        self._fim_fechada_ms = None  # um L logo depois não expande

    def _palma_parada(self, m: Medidas) -> bool:
        a = self._anterior
        return a is None or math.dist(m.centro, a.centro) < self.p.palma_parada

    # ---------- indicador: cursor e clique por pinça ----------

    def _indicador(self, t: int, m: Medidas, estavel: Pose, ev: list[Evento]):
        apontando = estavel is Pose.INDICADOR and not self.arrastando
        if apontando:
            ev.append(Evento(Tipo.APONTAR, t, self.ident, *m.no_indicador))
        if self.arrastando:
            self._toque.reiniciar()
            return
        familia = estavel in (Pose.INDICADOR, Pose.DOIS_DEDOS)
        if familia:
            self._ultimo_apontando_ms = t
        # a pose estável atrasa 3 quadros: logo depois de apontar (ou de outro toque, num duplo
        # clique) ela ainda pode estar em pinça ou "?"
        recente = (estavel in (Pose.PINCA, Pose.DESCONHECIDA, Pose.C, Pose.L)
                   and self._ultimo_apontando_ms is not None
                   and t - self._ultimo_apontando_ms <= self.p.duplo_clique_ms)
        clique = self._toque.atualizar(t, m, familia or recente)
        if clique is not None:
            botao, inicio = clique
            ev.append(Evento(Tipo.CLIQUE, t, self.ident, valor=botao, t_ref=inicio))
            self._ultimo_clique_ms = t

    # ---------- rolagem joystick (dois dedos) ----------

    def _rolagem(self, t: int, m: Medidas, estavel: Pose, ev: list[Evento]):
        if estavel is not Pose.DOIS_DEDOS:
            self._joystick = None
            return
        logo_apos_clique = (self._ultimo_clique_ms is not None
                            and t - self._ultimo_clique_ms <= self.p.rolagem_pos_clique_ms)
        if self._joystick is None or self._toque.em_andamento or logo_apos_clique:
            # onde a pose se formou vira o centro; durante e logo depois de um clique direito a mão
            # escorrega um pouco, então o centro acompanha
            self._joystick, self._joystick_ms = m.centro, t
            return
        dt = min((t - self._joystick_ms) / 1000, 0.1)  # mão sumiu por um instante: sem rajada
        self._joystick_ms = t
        p = self.p

        def velocidade(deslocamento: float) -> float:
            alem = abs(deslocamento) - p.rolagem_zona
            return 0.0 if alem <= 0 else math.copysign(min(p.rolagem_ganho * alem, p.rolagem_max), deslocamento)

        vx = velocidade(m.centro[0] - self._joystick[0])
        vy = velocidade(m.centro[1] - self._joystick[1])
        if vx or vy:
            # mão para a esquerda rola para a direita; para baixo rola para cima (regra do Arthur)
            ev.append(Evento(Tipo.ROLAGEM, t, self.ident, x=-vx * dt, y=vy * dt))

    # ---------- Alt+Tab com três dedos ----------

    def _alt_tab(self, t: int, m: Medidas, estavel: Pose, ev: list[Evento]):
        if estavel is not Pose.TRES_DEDOS:
            if self._alttab is not None:
                ev.append(Evento(Tipo.ALT_TAB_FIM, t, self.ident))  # mudar de pose escolhe
                self._alttab = None
            return
        if self._alttab is None:
            ev.append(Evento(Tipo.ALT_TAB_INICIO, t, self.ident))
            self._alttab = m.centro[0]
            return
        degrau = self.p.alttab_degrau
        while m.centro[0] - self._alttab >= degrau - FOLGA:
            ev.append(Evento(Tipo.ALT_TAB_PROXIMO, t, self.ident))
            self._alttab += degrau
        while self._alttab - m.centro[0] >= degrau - FOLGA:
            ev.append(Evento(Tipo.ALT_TAB_ANTERIOR, t, self.ident))
            self._alttab -= degrau

    # ---------- fechar: polegar para baixo segurado ----------

    def _fechar(self, t: int, estavel: Pose, ev: list[Evento]):
        if estavel is not Pose.POLEGAR_BAIXO:
            self.progresso_fechar, self._fechou_neste_gesto = 0.0, False
            return
        self.progresso_fechar = min(1.0, (t - self.filtro.desde_ms) / self.p.fechar_espera_ms)
        livre = self._ultimo_fechar_ms is None or t - self._ultimo_fechar_ms >= self.p.fechar_intervalo_ms
        if self.progresso_fechar >= 1.0 and not self._fechou_neste_gesto and livre:
            ev.append(Evento(Tipo.FECHAR_JANELA, t, self.ident))
            self._fechou_neste_gesto, self._ultimo_fechar_ms = True, t

    # ---------- mão fechada: arrastar, visão geral, expandir ----------

    def _mao_fechada(self, t: int, m: Medidas, estavel: Pose, bruta: Pose, ev: list[Evento]):
        fechada = estavel in FECHADAS and not self.em_zoom
        if not fechada:
            if self._fechada:
                self._sair_da_fechada(t, estavel, ev)
            return
        f = self._fechada
        p = self.p
        if f is None:
            veio = self._ultima_aberta_ms is not None and t - self._ultima_aberta_ms <= p.aberta_recente_ms
            viu_abrir = (self._ultima_nao_fechada_ms is not None
                         and t - self._ultima_nao_fechada_ms <= p.arrasto_viu_abrir_ms)
            self._fechada = _Fechada(t, m.centro, m.tamanho, veio, viu_abrir, parada_desde_ms=t)
            return
        if not f.armada:
            # só arma o arraste depois de a mão fechada ficar parada; até lá a referência
            # acompanha a mão (ela pode estar entrando no quadro ou terminando de fechar)
            if not self._palma_parada(m):
                f.parada_desde_ms = t
            f.centro, f.tamanho = m.centro, m.tamanho
            f.armada = t - f.parada_desde_ms >= p.arrasto_espera_ms
            return
        if not p.tamanho_estavel <= m.tamanho / f.tamanho <= 1 / p.tamanho_estavel:
            return  # mão inclinando ou abrindo: o centro aparente se desloca sem a mão sair do lugar
        f.tamanho += 0.1 * (m.tamanho - f.tamanho)
        if not f.arrastando:
            dx, dy = m.centro[0] - f.centro[0], m.centro[1] - f.centro[1]
            pode = f.viu_abrir and not m.na_borda and bruta in FECHADAS
            if pode and math.hypot(dx, dy) >= p.arrasto_min:
                f.arrastando, f.ultimo_centro = True, m.centro
                ev.append(Evento(Tipo.SEGURAR_INICIO, t, self.ident))
                ev.append(Evento(Tipo.ARRASTAR, t, self.ident, x=dx, y=dy))
        else:
            # nos quadros em que a mão já está abrindo, a palma se desloca: não arrasta
            if bruta in FECHADAS:
                ev.append(Evento(Tipo.ARRASTAR, t, self.ident,
                                 x=m.centro[0] - f.ultimo_centro[0], y=m.centro[1] - f.ultimo_centro[1]))
            f.ultimo_centro = m.centro

    def _sair_da_fechada(self, t: int, nova: Pose | None, ev: list[Evento]):
        f = self._fechada
        if f is None:
            return
        if f.arrastando:
            ev.append(Evento(Tipo.SEGURAR_FIM, t, self.ident))
        elif (nova is Pose.ABERTA and f.veio_de_aberta
              and t - f.inicio_ms <= self.p.visao_fechada_max_ms):
            ev.append(Evento(Tipo.VISAO_GERAL, t, self.ident))
        self._fechada = None
        # só uma mão fechada de propósito (não a pinça rápida de um clique) habilita o L de expandir
        self._fim_fechada_ms = t if t - f.inicio_ms >= self.p.l_fechada_min_ms else None

    def _l(self, t: int, estavel: Pose, ev: list[Evento]):
        if estavel is not Pose.L:
            self._l_expandiu = False
            return
        inicio = self.filtro.desde_ms
        elegivel = self._fim_fechada_ms is not None and inicio - self._fim_fechada_ms <= self.p.l_janela_ms
        if elegivel and not self._l_expandiu and t - inicio >= self.p.l_espera_ms:
            ev.append(Evento(Tipo.EXPANDIR, t, self.ident))
            self._l_expandiu = True

    # ---------- mão aberta: troca de área ----------

    def _aberta(self, t: int, m: Medidas, estavel: Pose, bruta: Pose, ev: list[Evento]):
        p = self.p
        if estavel is not Pose.ABERTA or bruta not in VARREDURA:
            # outra pose apareceu (a estável demora 3 quadros para mudar): episódio interrompido
            self._hist_aberta.clear()
            fora = self._ultima_aberta_ms is None or t - self._ultima_aberta_ms >= p.varredura_fora_ms
            if estavel is not Pose.ABERTA and fora:
                # ficou um tempo em outra pose: próxima mão aberta é um gesto novo. Um giro rápido
                # da palma no retorno (C por 3 quadros) não rearma
                self._varredura_armada, self._parada_desde_ms = True, None
            return
        h = self._hist_aberta
        if not self._varredura_armada:
            # depois de uma troca, o retorno natural da mão não conta: só rearma com a mão parada
            if self._palma_parada(m):
                self._parada_desde_ms = self._parada_desde_ms or t
                if t - self._parada_desde_ms >= p.varredura_rearme_ms:
                    self._varredura_armada = True
                    h.clear()
            else:
                self._parada_desde_ms = None
            if not self._varredura_armada:
                return
        h.append((t, *m.centro))
        while h and t - h[0][0] > p.varredura_janela_ms:
            h.popleft()
        _, x0, y0 = h[0]
        dx, dy = m.centro[0] - x0, m.centro[1] - y0
        if abs(dx) >= p.varredura_distancia and abs(dx) >= p.varredura_dominancia * abs(dy):
            ev.append(Evento(Tipo.AREA_DE_TRABALHO, t, self.ident, valor=1 if dx > 0 else -1))
            self._varredura_armada, self._parada_desde_ms = False, None
            h.clear()
