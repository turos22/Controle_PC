import threading
import time

import numpy as np

from controle.cursor import Cursor, Retangulo
from controle.eventos import Evento, Tipo
from controle.imagem import aplicar_zoom
from controle.pipeline import Config, Pipeline
from controle.plataforma.base import Botao
from controle.saida import Executor
from tests.test_saida import SaidaFalsa


def test_zoom_1x_devolve_o_mesmo_quadro():
    quadro = np.arange(16 * 9 * 3, dtype=np.uint8).reshape(9, 16, 3)
    assert aplicar_zoom(quadro, 1.0) is quadro


def test_zoom_2x_amplia_o_centro_mantendo_o_tamanho():
    quadro = np.zeros((90, 160, 3), np.uint8)
    quadro[40:50, 70:90] = 255  # mancha no centro
    ampliado = aplicar_zoom(quadro, 2.0)
    assert ampliado.shape == quadro.shape
    assert (ampliado > 128).sum() > 3 * (quadro > 128).sum()


class CameraFalsa:
    """Entrega quadros pretos a ~30 fps, como a thread de câmera real."""

    def __init__(self, total: int = 20, quadro: np.ndarray | None = None):
        self.total, self.entregues = total, 0
        self.fps = 30.0
        self.quadro = np.zeros((720, 1280, 3), np.uint8) if quadro is None else quadro

    @property
    def rodando(self) -> bool:
        return self.entregues < self.total

    def esperar_quadro(self, timeout: float = 1.0):
        if self.entregues >= self.total:
            return None
        time.sleep(1 / 30)
        self.entregues += 1
        return self.quadro, time.monotonic()

    def parar(self):
        pass


def pipeline_com(camera, saida=None):
    saida = saida or SaidaFalsa()
    cursor = Cursor([Retangulo(0, 0, 1920, 1080)])
    resultados = []
    p = Pipeline(camera, Executor(saida, saida, cursor), Config(), ao_resultado=resultados.append)
    return p, resultados, saida


def test_pipeline_processa_quadros_sem_mao_e_mede_latencia():
    p, resultados, _ = pipeline_com(CameraFalsa(total=15))
    p.rodar()  # roda até a câmera acabar
    assert len(resultados) == 15
    r = resultados[-1]
    assert r.maos == [] and r.feitas == []
    assert r.imagem.shape == (720, 1280, 3)
    assert 0 < r.metricas.mediapipe_ms < 100
    assert r.metricas.total_ms >= r.metricas.mediapipe_ms


def test_reconhecimento_sempre_recebe_imagem_espelhada():
    # espelhar é só visualização: desligar não pode inverter cursor e varreduras
    quadro = np.zeros((720, 1280, 3), np.uint8)
    quadro[:, :640] = 255  # metade esquerda branca
    p, resultados, _ = pipeline_com(CameraFalsa(total=2, quadro=quadro))
    p.rodar()
    imagem = resultados[-1].imagem
    assert imagem[:, :640].mean() < 10 and imagem[:, 640:].mean() > 245


class CameraTravada(CameraFalsa):
    """Entrega 3 quadros e para de entregar (cabo solto, outro programa pegou a câmera)."""

    def __init__(self):
        super().__init__(total=3)
        self.travada_desde = None

    @property
    def rodando(self) -> bool:
        return self.travada_desde is None or time.monotonic() - self.travada_desde < 0.8

    def esperar_quadro(self, timeout: float = 1.0):
        if self.entregues < 3:
            return super().esperar_quadro(timeout)
        self.travada_desde = self.travada_desde or time.monotonic()
        time.sleep(min(timeout, 0.1))
        return None


def test_camera_travada_continua_alimentando_o_reconhecedor_para_soltar_botoes():
    p, _, _ = pipeline_com(CameraTravada())
    vistos = []
    original = p.reconhecedor.processar
    p.reconhecedor.processar = lambda q: (vistos.append(q), original(q))[1]
    p.rodar()
    vazios = [q for q in vistos if not q.maos]
    assert len(vazios) > 3 + 2  # além dos 3 quadros pretos, quadros vazios durante a trava
    assert vazios[-1].t_ms - vazios[3].t_ms > 300  # tempo avança: a mão perdida é encerrada


def test_pausar_solta_botao_pressionado_e_bloqueia_acoes():
    saida = SaidaFalsa()
    p, _, _ = pipeline_com(CameraFalsa(total=0), saida)
    p.executor.executar([Evento(Tipo.SEGURAR_INICIO, 0, 1)])
    p.pausar()
    assert saida.chamadas[-1] == ("botao", Botao.ESQUERDO, False)
    p.executor.executar([Evento(Tipo.CLIQUE, 0, 1, valor=1)])
    assert saida.chamadas[-1] == ("botao", Botao.ESQUERDO, False)  # nada novo
    p.retomar()
    assert p.executor.ativo


def test_pipeline_em_thread_para_quando_pedido():
    p, resultados, _ = pipeline_com(CameraFalsa(total=1000))
    t = threading.Thread(target=p.rodar)
    t.start()
    time.sleep(0.3)
    p.parar()
    t.join(timeout=2)
    assert not t.is_alive() and resultados


def test_pipeline_grava_os_quadros_quando_ha_gravador(tmp_path):
    from controle.gravacao import Gravador
    p, _, _ = pipeline_com(CameraFalsa(total=5))
    p.gravador = Gravador(tmp_path, "livre")
    p.rodar()
    assert p.gravador.quadros == 5
