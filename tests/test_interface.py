import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from controle.cursor import Cursor, Retangulo  # noqa: E402
from controle.interface import JanelaPrincipal  # noqa: E402
from controle.pipeline import Config, Metricas, Resultado  # noqa: E402
from controle.plataforma.base import AcoesNulas, EntradaNula  # noqa: E402
from controle.saida import Executor  # noqa: E402
from tests.conftest import mao_em  # noqa: E402


class PipelineFalso:
    def __init__(self):
        self.config = Config()
        self.executor = Executor(EntradaNula(), AcoesNulas(), Cursor([Retangulo(0, 0, 1920, 1080)]))
        self.gravador = None
        self.chamadas = []

    def pausar(self):
        self.chamadas.append("pausar")
        self.executor.ativo = False

    def retomar(self):
        self.chamadas.append("retomar")
        self.executor.ativo = True

    def parar(self):
        self.chamadas.append("parar")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def janela(app, tmp_path):
    p = PipelineFalso()
    j = JanelaPrincipal(p, modo_demonstracao=False, pasta_gravacoes=tmp_path)
    yield j, p
    j.close()


def resultado(feitas=(), maos=()):
    m = Metricas(fps=30.0, espera_ms=0.1, mediapipe_ms=9.4, gestos_ms=0.3, total_ms=9.8)
    return Resultado(0, np.zeros((720, 1280, 3), np.uint8), list(maos), [], list(feitas), m)


def test_resultado_acende_o_gesto_na_legenda_e_atualiza_metricas(janela):
    j, _ = janela
    j.ao_resultado(resultado(feitas=[("expandir", "maximizou")]))
    assert j.legenda.destacado() == "expandir"
    assert "30 fps" in j.texto_status()
    assert "9.4" in j.texto_status() or "9,4" in j.texto_status()


def test_botao_de_pausa_pausa_e_retoma(janela):
    j, p = janela
    j.botao_pausa.click()
    assert p.chamadas == ["pausar"] and "Pausado" in j.botao_pausa.text()
    j.botao_pausa.click()
    assert p.chamadas == ["pausar", "retomar"]


def test_esc_so_pausa_nunca_retoma(janela):
    j, p = janela
    j.pausar_agora()
    j.pausar_agora()
    assert p.chamadas == ["pausar"] and not p.executor.ativo


def test_desligar_gesto_tira_do_executor(janela):
    j, p = janela
    j.menu.caixas_gestos["fechar_janela"].setChecked(False)
    assert "fechar_janela" not in p.executor.habilitados


def test_controles_alteram_zoom_regiao_e_espelho(janela):
    j, p = janela
    j.menu.zoom.setValue(20)
    j.menu.regiao.setValue(70)
    j.menu.espelhar.setChecked(False)
    assert p.config.zoom == pytest.approx(2.0)
    assert p.executor.cursor.regiao == pytest.approx(0.7)
    assert j.video.espelhar is False


def test_desenha_quadro_com_maos_sem_erro(janela):
    j, _ = janela
    j.resize(1400, 800)
    j.ao_resultado(resultado(maos=[mao_em("v04", 1.0)]))
    imagem = j.grab().toImage()
    assert imagem.width() > 0


def test_modo_do_cursor_velocidade_e_inverter_rolagem(janela):
    j, p = janela
    assert p.executor.cursor.modo == "relativo"
    j.menu.cursor_relativo.setChecked(False)
    j.menu.velocidade.setValue(200)
    j.menu.inverter_rolagem.setChecked(True)
    assert p.executor.cursor.modo == "absoluto"
    assert p.executor.cursor.velocidade == pytest.approx(2.0)
    assert p.executor.inverter_rolagem is True


def test_gravar_e_parar_salva_a_sessao(janela, tmp_path):
    j, p = janela
    j.menu.gesto_gravacao.setCurrentIndex(1)  # "Clique e duplo clique"
    j.menu.botao_gravar.click()
    assert p.gravador is not None and p.gravador.gesto == "clique"
    p.gravador.adicionar(0, [mao_em("v04", 1.0)], [])
    j.menu.botao_gravar.click()
    assert p.gravador is None
    import time
    from PySide6.QtWidgets import QApplication
    limite = time.monotonic() + 5
    while "Salvo" not in j.menu.rotulo_gravacao.text() and time.monotonic() < limite:
        QApplication.processEvents()  # o salvamento roda numa thread e avisa por sinal
        time.sleep(0.01)
    arquivos = list(tmp_path.glob("*_clique.npz"))
    assert len(arquivos) == 1 and arquivos[0].name in j.menu.rotulo_gravacao.text()


def test_desenha_anel_de_contagem_do_fechar_sem_erro(janela):
    from controle.geometria import medir
    from controle.poses import Pose
    from controle.reconhecedor import EstadoMao
    j, _ = janela
    mao = mao_em("v04", 1.0)
    estado = EstadoMao(1, "Right", Pose.POLEGAR_BAIXO, medir(mao), False, False, 0.5)
    m = Metricas(fps=30.0, espera_ms=0.1, mediapipe_ms=9.4, gestos_ms=0.3, total_ms=9.8)
    j.resize(1400, 800)
    j.ao_resultado(Resultado(0, np.zeros((720, 1280, 3), np.uint8), [mao], [estado], [], m))
    assert j.grab().toImage().width() > 0
