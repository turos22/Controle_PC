"""Executa os eventos reconhecidos no sistema, pela entrada e pelas ações de janela da plataforma.

Só usa o vocabulário neutro de `controle.plataforma.base`; cada sistema traduz do seu jeito.
"""
from controle.cursor import Cursor
from controle.eventos import Evento, Tipo
from controle.legenda import GESTOS, gesto_do_evento
from controle.plataforma.base import Acao, AcoesJanela, Botao, Entrada, Tecla

ENTALHE = 120  # unidades de alta resolução por entalhe da roda (padrão do kernel e do Windows)

ACOES = {
    Tipo.EXPANDIR: (Acao.MAXIMIZAR, "maximizou"),
    Tipo.VISAO_GERAL: (Acao.VISAO_GERAL, "visão geral"),
    Tipo.FECHAR_JANELA: (Acao.FECHAR_JANELA, "fechou a janela"),
}
AREAS = {-1: Acao.AREA_ESQUERDA, 1: Acao.AREA_DIREITA}
SOLTURAS = frozenset({Tipo.SEGURAR_FIM, Tipo.ALT_TAB_FIM, Tipo.ZOOM_FIM})


class Executor:
    def __init__(self, entrada: Entrada, acoes: AcoesJanela, cursor: Cursor):
        self.entrada, self.acoes, self.cursor = entrada, acoes, cursor
        self.mod_troca = getattr(entrada, "modificador_troca", Tecla.ALT)
        self.mod_zoom = getattr(entrada, "modificador_zoom", Tecla.CTRL)
        self.ativo = True
        self.habilitados = {g.id for g in GESTOS}
        self.ganho_rolagem = 1.0
        self.inverter_rolagem = False
        self._pressionados: set[Botao | Tecla] = set()
        self._resto_roda = [0, 0]

    def executar(self, eventos: list[Evento]) -> list[tuple[str, str]]:
        """Executa e devolve (gesto, descrição) do que agiu, para a legenda acender."""
        feitas = []
        for e in eventos:
            gesto = gesto_do_evento(e)
            if e.tipo not in SOLTURAS and (not self.ativo or gesto not in self.habilitados):
                continue
            descricao = self._executar(e)
            if descricao and e.tipo not in (Tipo.APONTAR, Tipo.ARRASTAR):
                feitas.append((gesto, descricao))
        return feitas

    def liberar_tudo(self):
        for item in list(self._pressionados):
            self._enviar(item, False)
        self._pressionados.clear()

    def _executar(self, e: Evento) -> str | None:
        s = self.entrada
        match e.tipo:
            case Tipo.APONTAR:
                self.cursor.apontar(e.t_ms, e.x, e.y)
                s.mover_absoluto(*self.cursor.normalizada())
            case Tipo.ARRASTAR:
                self.cursor.arrastar(e.x, e.y, e.t_ms)
                s.mover_absoluto(*self.cursor.normalizada())
            case Tipo.CLIQUE:
                if e.t_ref:
                    # clica onde o cursor estava quando a pinça começou (a mão mexe ao pinçar)
                    self.cursor.voltar_para(e.t_ref)
                    s.mover_absoluto(*self.cursor.normalizada())
                botao = Botao.DIREITO if e.valor == 3 else Botao.ESQUERDO
                s.botao(botao, True)
                s.botao(botao, False)
                return "clique direito" if e.valor == 3 else "clique"
            case Tipo.SEGURAR_INICIO:
                self._apertar(Botao.ESQUERDO)
                return "segurando"
            case Tipo.SEGURAR_FIM:
                return "soltou" if self._soltar(Botao.ESQUERDO) else None
            case Tipo.ROLAGEM:
                return self._rolar(e.x, e.y)
            case Tipo.AREA_DE_TRABALHO:
                self.acoes.executar(AREAS[e.valor])
                return "área à esquerda" if e.valor < 0 else "área à direita"
            case Tipo.ALT_TAB_INICIO:
                self._apertar(self.mod_troca)
                self._tocar(Tecla.TAB)
                return "Alt+Tab"
            case Tipo.ALT_TAB_PROXIMO:
                if self.mod_troca not in self._pressionados:
                    # o início foi pulado (pausa ou gesto desligado): sem Alt, Tab seria digitado
                    self._apertar(self.mod_troca)
                    self._tocar(Tecla.TAB)
                    return "Alt+Tab"
                self._tocar(Tecla.TAB)
                return "próxima janela"
            case Tipo.ALT_TAB_ANTERIOR:
                if self.mod_troca not in self._pressionados:
                    self._apertar(self.mod_troca)
                s.tecla(Tecla.SHIFT, True)
                self._tocar(Tecla.TAB)
                s.tecla(Tecla.SHIFT, False)
                return "janela anterior"
            case Tipo.ALT_TAB_FIM:
                return "escolheu a janela" if self._soltar(self.mod_troca) else None
            case Tipo.ZOOM_INICIO:
                # Ctrl fica segurado a sessão inteira: apertar e soltar junto de cada passo, em
                # dispositivos diferentes, deixava o KDE ver a roda antes do Ctrl (rolava em vez de zoom)
                self._apertar(self.mod_zoom)
            case Tipo.ZOOM:
                if self.mod_zoom not in self._pressionados:
                    self._apertar(self.mod_zoom)
                s.rolar(0, ENTALHE * e.valor, 0, e.valor)
                return "zoom +" if e.valor > 0 else "zoom −"
            case Tipo.ZOOM_FIM:
                self._soltar(self.mod_zoom)
            case _ if e.tipo in ACOES:
                acao, descricao = ACOES[e.tipo]
                self.acoes.executar(acao)
                return descricao
        return None

    def _enviar(self, item: Botao | Tecla, pressionado: bool):
        if isinstance(item, Botao):
            self.entrada.botao(item, pressionado)
        else:
            self.entrada.tecla(item, pressionado)

    def _apertar(self, item: Botao | Tecla):
        self._enviar(item, True)
        self._pressionados.add(item)

    def _soltar(self, item: Botao | Tecla) -> bool:
        if item not in self._pressionados:
            return False
        self._enviar(item, False)
        self._pressionados.discard(item)
        return True

    def _tocar(self, tecla: Tecla):
        self.entrada.tecla(tecla, True)
        self.entrada.tecla(tecla, False)

    def _rolar(self, x: float, y: float) -> str:
        ganho = ENTALHE * self.ganho_rolagem * (-1 if self.inverter_rolagem else 1)
        hr = [round(x * ganho), round(y * ganho)]
        entalhes = []
        for i in range(2):
            self._resto_roda[i] += hr[i]
            inteiros = int(self._resto_roda[i] / ENTALHE)  # trunca em direção ao zero
            self._resto_roda[i] -= inteiros * ENTALHE
            entalhes.append(inteiros)
        self.entrada.rolar(hr[0], hr[1], entalhes[0], entalhes[1])
        if abs(hr[1]) >= abs(hr[0]):
            return "rolou para cima" if hr[1] > 0 else "rolou para baixo"
        return "rolou para a direita" if hr[0] > 0 else "rolou para a esquerda"
