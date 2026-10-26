import numpy as np

from tests.conftest import PASTA_FIXTURES, carregar_gravacao


def test_existem_13_fixtures():
    assert sorted(p.stem for p in PASTA_FIXTURES.glob("v*.npz")) == [f"v{i:02d}" for i in range(1, 14)]


def test_gravacao_vira_quadros_a_30_fps_com_maos_validas():
    quadros = carregar_gravacao("v01")
    assert len(quadros) > 150
    assert quadros[1].t_ms - quadros[0].t_ms == 33
    com_mao = [q for q in quadros if q.maos]
    assert len(com_mao) > 100
    mao = com_mao[0].maos[0]
    assert mao.img.shape == (21, 3) and mao.mundo.shape == (21, 3)
    assert not np.isnan(mao.img).any()
    assert mao.rotulo in ("Left", "Right")
