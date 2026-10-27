"""macOS: mouse e teclado virtuais por Quartz (pyobjc).

Exige a permissão de Acessibilidade para o programa (Ajustes do Sistema → Privacidade e Segurança) e,
para a câmera, a permissão de Câmera. Verificado só pelos testes com um Quartz falso; a prova real
exige um Mac.
"""
from controle.plataforma.base import Botao, Tecla

FLAG_COMANDO, FLAG_CONTROLE, FLAG_OPCAO, FLAG_SHIFT = 0x100000, 0x040000, 0x080000, 0x020000
CODIGO_TECLA = {
    Tecla.META: 55, Tecla.SHIFT: 56, Tecla.ALT: 58, Tecla.CTRL: 59, Tecla.TAB: 48, Tecla.CIMA: 126,
    Tecla.ESQUERDA: 123, Tecla.DIREITA: 124, Tecla.PAGE_UP: 116, Tecla.PAGE_DOWN: 121, Tecla.F4: 118,
    Tecla.W: 13, Tecla.F: 3,
}
FLAG_MODIFICADOR = {Tecla.META: FLAG_COMANDO, Tecla.CTRL: FLAG_CONTROLE, Tecla.ALT: FLAG_OPCAO,
                    Tecla.SHIFT: FLAG_SHIFT}
PIXELS_POR_ENTALHE = 12  # a roda do Mac anda ~10–12 px por clique em apps comuns


def acessibilidade_liberada() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        return False
    return bool(AXIsProcessTrusted())


def _telas_do_quartz(quartz) -> list[tuple[float, float, float, float]]:
    _, ids, _ = quartz.CGGetActiveDisplayList(16, None, None)
    limites = [quartz.CGDisplayBounds(i) for i in ids]
    return [(r.origin.x, r.origin.y, r.size.width, r.size.height) for r in limites]


class EntradaMacos:
    modificador_troca = Tecla.META  # Comando+Tab troca de aplicativo
    modificador_zoom = Tecla.META   # Comando+roda dá zoom na maioria dos aplicativos

    def __init__(self, quartz=None, telas=None):
        if quartz is None:
            import Quartz as quartz  # noqa: N813 — pyobjc; só existe no macOS
        self._q = quartz
        telas = telas if telas is not None else _telas_do_quartz(quartz)
        self._x0 = min(x for x, _, _, _ in telas)
        self._y0 = min(y for _, y, _, _ in telas)
        self._largura = max(x + w for x, _, w, _ in telas) - self._x0
        self._altura = max(y + h for _, y, _, h in telas) - self._y0
        self._ponto = (self._x0, self._y0)
        self._botoes: set[Botao] = set()
        self._modificadores = 0

    def _postar(self, evento):
        self._q.CGEventPost(self._q.kCGHIDEventTap, evento)

    def mover_absoluto(self, u: float, v: float):
        q = self._q
        self._ponto = (round(self._x0 + min(max(u, 0.0), 1.0) * (self._largura - 1)),
                       round(self._y0 + min(max(v, 0.0), 1.0) * (self._altura - 1)))
        if Botao.ESQUERDO in self._botoes:
            tipo, botao = q.kCGEventLeftMouseDragged, q.kCGMouseButtonLeft
        elif Botao.DIREITO in self._botoes:
            tipo, botao = q.kCGEventRightMouseDragged, q.kCGMouseButtonRight
        else:
            tipo, botao = q.kCGEventMouseMoved, q.kCGMouseButtonLeft
        self._postar(q.CGEventCreateMouseEvent(None, tipo, self._ponto, botao))

    def botao(self, botao: Botao, pressionado: bool):
        q = self._q
        esquerdo = botao is Botao.ESQUERDO
        tipo = {(True, True): q.kCGEventLeftMouseDown, (True, False): q.kCGEventLeftMouseUp,
                (False, True): q.kCGEventRightMouseDown, (False, False): q.kCGEventRightMouseUp}[(esquerdo, pressionado)]
        (self._botoes.add if pressionado else self._botoes.discard)(botao)
        self._postar(q.CGEventCreateMouseEvent(
            None, tipo, self._ponto, q.kCGMouseButtonLeft if esquerdo else q.kCGMouseButtonRight))

    def rolar(self, horizontal_hr: int, vertical_hr: int, horizontal: int, vertical: int):
        if not (horizontal_hr or vertical_hr):
            return
        q = self._q
        passo = PIXELS_POR_ENTALHE / 120
        evento = q.CGEventCreateScrollWheelEvent(None, q.kCGScrollEventUnitPixel, 2,
                                                 round(vertical_hr * passo), round(horizontal_hr * passo))
        self._postar(evento)

    def tecla(self, tecla: Tecla, pressionada: bool):
        flag = FLAG_MODIFICADOR.get(tecla, 0)
        if flag:
            self._modificadores = (self._modificadores | flag) if pressionada else (self._modificadores & ~flag)
        evento = self._q.CGEventCreateKeyboardEvent(None, CODIGO_TECLA[tecla], pressionada)
        self._q.CGEventSetFlags(evento, self._modificadores)
        self._postar(evento)

    def fechar(self):
        pass
