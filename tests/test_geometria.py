import numpy as np
import pytest

from controle.geometria import medir, retidao
from tests.conftest import mao_em


def test_retidao_de_segmentos_alinhados_e_1():
    pontos = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], float)
    assert retidao(pontos) == pytest.approx(1.0)


def test_retidao_de_dedo_dobrado_em_angulo_reto_cai():
    # base → nó → meio → ponta, dobrando 90° no nó
    pontos = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 2, 0]], float)
    assert retidao(pontos) == pytest.approx(np.sqrt(5) / 3)


def test_l_do_video_1_tem_indicador_e_polegar_esticados_e_resto_dobrado():
    m = medir(mao_em("v01", 2.5))
    assert m.retidao["I"] > 0.9 and m.retidao["T"] > 0.95
    assert max(m.retidao["M"], m.retidao["A"], m.retidao["P"]) < 0.6
    assert m.pinca > 1.5
    assert m.angulo_polegar > 60


def test_indicador_apontando_tem_polegar_proximo_do_indicador():
    assert medir(mao_em("v04", 1.0)).angulo_polegar < 40


def test_pinca_do_video_8_aproxima_pontas_de_polegar_e_indicador():
    m = medir(mao_em("v08", 4.4, rotulo="Left"))
    assert m.pinca < 0.2


def test_mao_aberta_do_video_3_tem_todos_os_dedos_esticados():
    m = medir(mao_em("v03", 1.0))
    assert min(m.retidao.values()) > 0.9


def test_apontando_o_polegar_fica_longe_da_ponta_do_medio():
    # clique direito = encostar o polegar no médio; apontando, ele está a ~0,8 palma
    assert medir(mao_em("v04", 1.0)).pinca_medio > 0.6


def test_polegar_do_l_aponta_para_o_lado_e_esta_afastado():
    m = medir(mao_em("v01", 2.5))
    assert abs(m.polegar_dy) < 0.6
    assert m.afastamento_polegar > 1.0


def test_centro_e_ponta_ficam_em_unidades_de_altura_da_imagem():
    mao = mao_em("v01", 2.5)
    m = medir(mao, aspecto=16 / 9)
    x, y = m.no_indicador
    assert x == pytest.approx(mao.img[5, 0] * 16 / 9)
    assert y == pytest.approx(mao.img[5, 1])
    assert 0 < m.tamanho < 1
