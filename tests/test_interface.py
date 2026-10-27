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


def test_indice_da_camera_vem_do_argumento():
    from controle.app import indice_da_camera
    assert indice_da_camera(["prog"]) == 0
    assert indice_da_camera(["prog", "--camera", "2"]) == 2
    assert indice_da_camera(["prog", "--camera=1"]) == 1
    assert indice_da_camera(["prog", "--camera", "x"]) == 0
    assert indice_da_camera(["prog"], padrao=3) == 3 and indice_da_camera(["prog", "--camera=1"], padrao=3) == 1


# ---------- perfil: o menu lembra os ajustes entre sessões ----------

def test_ajustes_do_perfil_valem_ao_abrir(app, tmp_path):
    from controle.perfil import Perfil
    p = PipelineFalso()
    perfil = Perfil(ajustes={"velocidade": 150, "inverter_rolagem": True, "rolagem": 200,
                             "gestos_desligados": ["zoom"]})
    j = JanelaPrincipal(p, pasta_gravacoes=tmp_path, perfil=perfil, caminho_perfil=tmp_path / "perfil.json")
    assert p.executor.cursor.velocidade == 1.5 and p.executor.inverter_rolagem
    assert p.executor.ganho_rolagem == 2.0 and "zoom" not in p.executor.habilitados
    j.close()


def test_ajustes_invalidos_do_perfil_nao_derrubam_a_janela(app, tmp_path):
    from controle.perfil import Perfil
    p = PipelineFalso()
    perfil = Perfil(ajustes={"velocidade": "muito", "rolagem": 99999, "gestos_desligados": "zoom", "x": 1})
    j = JanelaPrincipal(p, pasta_gravacoes=tmp_path, perfil=perfil, caminho_perfil=tmp_path / "perfil.json")
    assert 25 <= j.menu.velocidade.value() <= 400 and j.menu.rolagem.value() <= 300
    j.close()


def test_fechar_a_janela_salva_os_ajustes_no_perfil(app, tmp_path):
    import json
    from controle.perfil import Perfil
    caminho = tmp_path / "perfil.json"
    p = PipelineFalso()
    j = JanelaPrincipal(p, pasta_gravacoes=tmp_path, perfil=Perfil(), caminho_perfil=caminho)
    j.menu.velocidade.setValue(220)
    j.menu.inverter_rolagem.setChecked(True)
    j.close()
    salvo = json.loads(caminho.read_text())
    assert salvo["ajustes"]["velocidade"] == 220 and salvo["ajustes"]["inverter_rolagem"] is True


def test_sem_caminho_de_perfil_nada_e_gravado(app, tmp_path):
    p = PipelineFalso()
    j = JanelaPrincipal(p, pasta_gravacoes=tmp_path)
    j.close()
    assert list(tmp_path.iterdir()) == []


def test_falha_ao_gravar_o_perfil_nao_impede_de_fechar(app, tmp_path):
    from controle.perfil import Perfil
    bloqueio = tmp_path / "arquivo"
    bloqueio.write_text("x")                       # uma pasta não pode ser criada dentro de um arquivo
    j = JanelaPrincipal(PipelineFalso(), pasta_gravacoes=tmp_path, perfil=Perfil(),
                        caminho_perfil=bloqueio / "perfil.json")
    j.close()


def test_interface_em_ingles(app, tmp_path):
    from controle import idioma
    idioma.definir_idioma("en")
    try:
        p = PipelineFalso()
        j = JanelaPrincipal(p, pasta_gravacoes=tmp_path)
        assert j.windowTitle() == "Gesture control" and "Gestures active" in j.botao_pausa.text()
        j.ao_resultado(resultado(maos=[mao_em("v01", 1.0)]))
        j.close()
    finally:
        idioma.definir_idioma("pt")


# ---------- calibração guiada ----------

def feed_calibracao(j, relogio, de, ate, passo=0.1, mao=None):
    mao = mao or mao_em("v01", 1.0)
    for i in range(round(de / passo), round(ate / passo)):
        relogio[0] = i * passo
        j.ao_resultado(resultado(maos=[mao]))


def janela_com_perfil(app, tmp_path):
    from controle.perfil import Perfil
    p = PipelineFalso()
    perfil = Perfil()
    j = JanelaPrincipal(p, pasta_gravacoes=tmp_path, perfil=perfil, caminho_perfil=tmp_path / "perfil.json")
    return j, p, perfil


def test_botao_de_calibrar_pausa_os_gestos_e_abre_a_sessao(app, tmp_path):
    from controle.calibracao import Sessao
    from controle.poses import Pose
    j, p, _ = janela_com_perfil(app, tmp_path)
    relogio = [0.0]
    j.menu.botao_calibrar.click()
    assert j.sessao is not None and not p.executor.ativo and "pausar" in p.chamadas
    j.close()


def test_sessao_conclui_mostra_resultado_e_aplicar_salva_no_perfil(app, tmp_path):
    import json
    from controle.calibracao import Sessao
    from controle.poses import Pose
    j, p, perfil = janela_com_perfil(app, tmp_path)
    relogio = [0.0]
    j.iniciar_calibracao(sessao=Sessao(passos=(Pose.ABERTA,), preparo_s=0.2, captura_s=2.4, descarte_s=0.1),
                         relogio=lambda: relogio[0])
    feed_calibracao(j, relogio, 0.0, 3.5)
    assert j.sessao.concluida and j.dialogo_calibracao.botao_aplicar.isEnabled()
    j.dialogo_calibracao.botao_aplicar.click()
    assert perfil.calibrado and p.executor.ativo and j.sessao is None
    assert json.loads((tmp_path / "perfil.json").read_text())["calibrado"] is True
    j.close()


def test_descartar_nao_muda_o_perfil_e_devolve_o_estado(app, tmp_path):
    from controle.calibracao import Sessao
    from controle.poses import Pose
    j, p, perfil = janela_com_perfil(app, tmp_path)
    relogio = [0.0]
    j.iniciar_calibracao(sessao=Sessao(passos=(Pose.ABERTA,), preparo_s=0.2, captura_s=2.4, descarte_s=0.1),
                         relogio=lambda: relogio[0])
    feed_calibracao(j, relogio, 0.0, 1.0)
    j.dialogo_calibracao.botao_cancelar.click()
    assert not perfil.calibrado and perfil.limites == {} and p.executor.ativo and j.sessao is None
    j.close()


def test_cancelar_nao_reativa_gestos_que_ja_estavam_pausados(app, tmp_path):
    j, p, _ = janela_com_perfil(app, tmp_path)
    j.botao_pausa.click()                       # a pessoa já tinha pausado
    j.menu.botao_calibrar.click()
    j.dialogo_calibracao.botao_cancelar.click()
    assert not p.executor.ativo
    j.close()


def test_primeiro_uso_oferece_calibrar_so_quando_pedido_e_ainda_nao_calibrado(app, tmp_path):
    from controle.perfil import Perfil
    perguntas = []
    j = JanelaPrincipal(PipelineFalso(), pasta_gravacoes=tmp_path, perfil=Perfil(),
                        caminho_perfil=tmp_path / "perfil.json", perguntar=lambda *a: perguntas.append(a) or False)
    j.oferecer_calibracao()
    assert len(perguntas) == 1
    j.close()
    j2 = JanelaPrincipal(PipelineFalso(), pasta_gravacoes=tmp_path, perfil=Perfil(calibrado=True),
                         caminho_perfil=tmp_path / "perfil.json", perguntar=lambda *a: perguntas.append(a) or False)
    j2.oferecer_calibracao()
    assert len(perguntas) == 1                 # já calibrado: não pergunta de novo
    j2.close()
