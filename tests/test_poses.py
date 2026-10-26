import time

import pytest

from controle.geometria import medir
from controle.poses import Pose, classificar
from tests.conftest import carregar_gravacao, mao_em

# (vídeo, segundos, rótulo da mão ou None, pose esperada) — trechos conferidos nos vídeos
ROTULADOS = [
    *[("v01", t, None, Pose.L) for t in (2.4, 2.6, 3.5, 4.9, 5.1)],
    *[("v01", t, None, Pose.PINCA) for t in (2.0, 2.1, 4.2, 4.4, 4.6)],
    *[("v06", t, None, Pose.PUNHO) for t in (4.6, 5.0, 6.6, 7.0)],
    *[("v04", t, None, Pose.INDICADOR) for t in (1.0, 1.4, 6.4, 7.2)],
    *[("v10", t, None, Pose.DOIS_DEDOS) for t in (4.2, 4.6, 6.4)],
    *[("v11", t, None, Pose.DOIS_DEDOS) for t in (2.0, 2.8, 3.4, 4.0)],
    *[("v03", t, None, Pose.ABERTA) for t in (1.0, 1.2, 1.4, 3.4, 4.2, 4.4, 6.2)],
    *[("v08", t, "Left", Pose.PINCA) for t in (4.0, 4.8, 17.8, 18.0)],
    *[("v02", t, None, Pose.PUNHO) for t in (1.5, 2.7, 3.9, 5.1)],
    *[("v02", t, None, Pose.ABERTA) for t in (2.0, 3.2, 4.4)],
    *[("v12", t, r, Pose.C) for t in (3.0, 5.0) for r in ("Left", "Right")],
    *[("v09", t, None, Pose.ABERTA) for t in (1.0, 1.8)],
]


@pytest.mark.parametrize("video,segundos,rotulo,esperada", ROTULADOS)
def test_pose_dos_trechos_rotulados(video, segundos, rotulo, esperada):
    assert classificar(medir(mao_em(video, segundos, rotulo))) is esperada


# três dedos do Arthur (gravação ao vivo): o mínimo fica meio dobrado, retidão 0,62–0,76
@pytest.mark.parametrize("segundos", [2.06, 2.53, 3.26, 3.60, 4.20])
def test_tres_dedos_com_o_minimo_meio_dobrado(segundos):
    assert classificar(medir(mao_em("g_alt_tab", segundos))) is Pose.TRES_DEDOS


def test_mao_aberta_do_arthur_nao_vira_tres_dedos():
    # na gravação de troca de área, o mínimo da mão aberta fica em 0,92–0,99
    maos = [medir(m) for q in carregar_gravacao("g_area") for m in q.maos]
    esticadas = [m for m in maos if min(m.retidao["I"], m.retidao["M"], m.retidao["A"]) >= 0.86]
    tres = [m for m in esticadas if classificar(m) is Pose.TRES_DEDOS]
    assert len(esticadas) > 300 and len(tres) <= 0.02 * len(esticadas)


# poses da iteração 2 ainda sem gravação: medidas sintéticas até a calibração com as do Arthur
def test_tres_dedos_e_indicador_medio_e_anelar_esticados_com_minimo_dobrado():
    from tests.test_gestos import med
    assert classificar(med(ret={"I": 0.95, "M": 0.95, "A": 0.92, "P": 0.5})) is Pose.TRES_DEDOS
    assert classificar(med(ret={"I": 0.95, "M": 0.95, "A": 0.5, "P": 0.5})) is Pose.DOIS_DEDOS


def test_polegar_para_baixo_e_punho_com_polegar_esticado_apontando_para_baixo():
    from tests.test_gestos import med
    dobrados = {"T": 0.95, "I": 0.5, "M": 0.45, "A": 0.45, "P": 0.5}
    assert classificar(med(ret=dobrados, polegar_dy=0.9, afastamento_polegar=1.2, pinca=1.2)) is Pose.POLEGAR_BAIXO
    # polegar enrolado no punho (perto do indicador) com a mão baixa: continua punho
    assert classificar(med(ret=dobrados, polegar_dy=0.9, afastamento_polegar=0.7, pinca=0.8)) is Pose.PUNHO
    # polegar esticado mas para o lado: não é polegar para baixo
    assert classificar(med(ret=dobrados, polegar_dy=0.1, afastamento_polegar=1.2, pinca=1.2)) is not Pose.POLEGAR_BAIXO


def test_medir_e_classificar_custa_menos_de_1_ms_por_mao():
    maos = [m for q in carregar_gravacao("v12") for m in q.maos]
    assert len(maos) > 500
    inicio = time.perf_counter()
    for mao in maos:
        classificar(medir(mao))
    por_mao_ms = (time.perf_counter() - inicio) * 1000 / len(maos)
    assert por_mao_ms < 1.0, f"{por_mao_ms:.3f} ms por mão"
