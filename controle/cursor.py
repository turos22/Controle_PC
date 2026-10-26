"""Posição do cursor, com filtro One Euro.

Dois modos:
- relativo (padrão): como um touchpad com aceleração; mão devagar = movimento fino, rápida =
  atravessa as telas. Sair da pose de indicador é a "embreagem".
- absoluto: a região ativa da imagem é mapeada direto na área das telas.
"""
import math
from collections import deque
from dataclasses import dataclass

PX_POR_UNIDADE = 3000.0     # ganho 1: uma altura de imagem de movimento = 3000 px
GANHO_LENTO, GANHO_RAPIDO = 0.35, 3.0
VELOCIDADE_LENTA, VELOCIDADE_RAPIDA = 0.1, 1.5   # unidades de altura por segundo
TREMOR = 0.0006             # deslocamento abaixo disso não move (acumula até passar)
EMBREAGEM_MS = 150          # sem apontar por mais que isso: próximo apontar não move


@dataclass(frozen=True, slots=True)
class Retangulo:
    x: int
    y: int
    w: int
    h: int

    def contem(self, px: float, py: float) -> bool:
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

    def grampear(self, px: float, py: float) -> tuple[float, float]:
        return (min(max(px, self.x), self.x + self.w - 1), min(max(py, self.y), self.y + self.h - 1))


def envolvente(telas: list[Retangulo]) -> Retangulo:
    x0, y0 = min(t.x for t in telas), min(t.y for t in telas)
    x1, y1 = max(t.x + t.w for t in telas), max(t.y + t.h for t in telas)
    return Retangulo(x0, y0, x1 - x0, y1 - y0)


class FiltroOneEuro:
    """Filtro de Casiez et al.: suaviza muito parado e quase nada em movimento rápido."""

    def __init__(self, freq_min: float = 1.0, beta: float = 5.0, freq_derivada: float = 1.0):
        self.freq_min, self.beta, self.freq_derivada = freq_min, beta, freq_derivada
        self.reiniciar()

    def reiniciar(self):
        self._t = self._x = None
        self._dx = 0.0

    @staticmethod
    def _alfa(dt: float, corte: float) -> float:
        return 1.0 / (1.0 + 1.0 / (2 * math.pi * corte * dt))

    def filtrar(self, t: float, x: float) -> float:
        if self._t is None:
            self._t, self._x = t, x
            return x
        dt = max(t - self._t, 1e-6)
        self._dx += self._alfa(dt, self.freq_derivada) * ((x - self._x) / dt - self._dx)
        corte = self.freq_min + self.beta * abs(self._dx)
        self._x += self._alfa(dt, corte) * (x - self._x)
        self._t = t
        return self._x


class Cursor:
    def __init__(self, telas: list[Retangulo], modo: str = "relativo", regiao: float = 0.6,
                 aspecto: float = 16 / 9, centro_regiao: tuple[float, float] | None = None,
                 suavizar: bool = True, freq_min: float = 1.0, beta: float = 5.0, velocidade: float = 1.0):
        self.telas = telas
        self.modo, self.velocidade = modo, velocidade
        self._ancora: tuple[int, float, float] | None = None  # último ponto que moveu (relativo)
        self.area = envolvente(telas)
        self.regiao, self.aspecto = regiao, aspecto
        self.centro_regiao = centro_regiao or (aspecto / 2, 0.55)  # mãos ficam na metade de baixo
        self.suavizar = suavizar
        self._filtros = (FiltroOneEuro(freq_min, beta), FiltroOneEuro(freq_min, beta))
        self._ultimo_ms = None
        self._ultimo_arrasto_ms = None
        self._historico: deque[tuple[int, float, float]] = deque()
        t0 = telas[0]
        # posição guardada em float: arrastos lentos somam frações de pixel por quadro
        self._x, self._y = float(t0.x + t0.w // 2), float(t0.y + t0.h // 2)

    @property
    def posicao(self) -> tuple[int, int]:
        return round(self._x), round(self._y)

    def limites_regiao(self) -> tuple[float, float, float, float]:
        """(x0, y0, largura, altura) da região ativa, em unidades de altura da imagem."""
        w, h = self.regiao * self.aspecto, self.regiao
        return self.centro_regiao[0] - w / 2, self.centro_regiao[1] - h / 2, w, h

    def ajustar_filtro(self, freq_min: float, beta: float):
        for f in self._filtros:
            f.freq_min, f.beta = freq_min, beta

    def apontar(self, t_ms: int, x: float, y: float) -> tuple[int, int]:
        posicao = self._apontar_relativo(t_ms, x, y) if self.modo == "relativo" else self._apontar_absoluto(t_ms, x, y)
        h = self._historico
        h.append((t_ms, self._x, self._y))
        while h and t_ms - h[0][0] > 1000:
            h.popleft()
        return posicao

    def voltar_para(self, t_ms: int):
        """Volta à posição que o cursor tinha no instante `t_ms` (último registro até ele)."""
        anteriores = [(x, y) for t, x, y in self._historico if t <= t_ms]
        if anteriores:
            self._x, self._y = anteriores[-1]

    def _ganho(self, rapidez: float) -> float:
        """Pixels por unidade de altura, conforme a rapidez da mão (unidades por segundo)."""
        s = min(max((rapidez - VELOCIDADE_LENTA) / (VELOCIDADE_RAPIDA - VELOCIDADE_LENTA), 0.0), 1.0)
        s = s * s * (3 - 2 * s)  # transição suave entre lento e rápido
        return (GANHO_LENTO + (GANHO_RAPIDO - GANHO_LENTO) * s) * PX_POR_UNIDADE * self.velocidade

    def _apontar_absoluto(self, t_ms: int, x: float, y: float) -> tuple[int, int]:
        x0, y0, w, h = self.limites_regiao()
        u = min(max((x - x0) / w, 0.0), 1.0)
        v = min(max((y - y0) / h, 0.0), 1.0)
        if self.suavizar:
            if self._ultimo_ms is None or t_ms - self._ultimo_ms > 300:
                for f in self._filtros:
                    f.reiniciar()
            u = self._filtros[0].filtrar(t_ms / 1000, u)
            v = self._filtros[1].filtrar(t_ms / 1000, v)
        self._ultimo_ms = t_ms
        return self._mover(self.area.x + u * (self.area.w - 1), self.area.y + v * (self.area.h - 1))

    def _apontar_relativo(self, t_ms: int, x: float, y: float) -> tuple[int, int]:
        anterior_ms = self._ultimo_ms
        pausa = anterior_ms is None or t_ms - anterior_ms > EMBREAGEM_MS
        self._ultimo_ms = t_ms
        if self.suavizar:
            if pausa:
                for f in self._filtros:
                    f.reiniciar()
            x = self._filtros[0].filtrar(t_ms / 1000, x)
            y = self._filtros[1].filtrar(t_ms / 1000, y)
        if pausa or self._ancora is None:
            self._ancora = (t_ms, x, y)  # embreagem: a mão voltou a apontar, não move
            return self.posicao
        _, x0, y0 = self._ancora
        dx, dy = x - x0, y - y0
        distancia = math.hypot(dx, dy)
        if distancia < TREMOR:
            return self.posicao
        # rapidez pelo intervalo do último quadro: a âncora pode ser antiga (mão parada antes)
        rapidez = distancia / max((t_ms - anterior_ms) / 1000, 1e-3)
        ganho = self._ganho(rapidez)
        self._ancora = (t_ms, x, y)
        return self._mover(self._x + dx * ganho, self._y + dy * ganho)

    def arrastar(self, dx: float, dy: float, t_ms: int | None = None) -> tuple[int, int]:
        if self.modo == "relativo":
            # mesmo ganho e velocidade do cursor, senão arrastar fica mais lento que apontar
            anterior = self._ultimo_arrasto_ms
            self._ultimo_arrasto_ms = t_ms
            intervalo = 33 if t_ms is None or anterior is None or not 0 < t_ms - anterior <= EMBREAGEM_MS \
                else t_ms - anterior
            ganho = self._ganho(math.hypot(dx, dy) / (intervalo / 1000))
            return self._mover(self._x + dx * ganho, self._y + dy * ganho)
        _, _, w, h = self.limites_regiao()
        return self._mover(self._x + dx / w * (self.area.w - 1), self._y + dy / h * (self.area.h - 1))

    def normalizada(self) -> tuple[float, float]:
        """Posição em [0, 1] sobre a área envolvente (é o que o ponteiro absoluto recebe)."""
        return (self._x - self.area.x) / (self.area.w - 1), (self._y - self.area.y) / (self.area.h - 1)

    def _mover(self, px: float, py: float) -> tuple[int, int]:
        if not any(t.contem(px, py) for t in self.telas):
            # área envolvente tem cantos sem tela: leva para o ponto mais próximo de alguma tela
            px, py = min((t.grampear(px, py) for t in self.telas),
                         key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
        self._x, self._y = float(px), float(py)
        return self.posicao
