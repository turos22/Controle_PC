import numpy as np

from controle.eventos import Evento, Tipo
from controle.gravacao import Gravador
from tests.conftest import carregar_gravacao, mao_em


def test_gravacao_salva_no_formato_das_fixtures_e_relê_igual(tmp_path):
    mao = mao_em("v04", 1.0)
    g = Gravador(tmp_path, "clique")
    g.adicionar(0, [mao], [])
    g.adicionar(33, [], [Evento(Tipo.CLIQUE, 33, 1, valor=1)])
    g.adicionar(66, [mao, mao_em("v12", 3.0, "Right")], [])
    caminho = g.salvar()

    assert caminho.parent == tmp_path and "clique" in caminho.name
    d = np.load(caminho)
    assert d["img"].shape == (3, 2, 21, 3)
    assert list(d["t_ms"]) == [0, 33, 66]
    assert str(d["gesto"]) == "clique"
    assert list(d["eventos_tipo"]) == ["clique"] and list(d["eventos_t_ms"]) == [33]

    quadros = carregar_gravacao.__wrapped__(caminho.stem, pasta=tmp_path)
    assert [len(q.maos) for q in quadros] == [1, 0, 2]
    np.testing.assert_allclose(quadros[0].maos[0].img, mao.img)
    assert quadros[0].maos[0].rotulo == mao.rotulo


def test_gravacao_vazia_nao_salva(tmp_path):
    assert Gravador(tmp_path, "livre").salvar() is None


def test_depois_de_salvar_novos_quadros_sao_ignorados(tmp_path):
    g = Gravador(tmp_path, "livre")
    g.adicionar(0, [mao_em("v04", 1.0)], [])
    caminho = g.salvar()
    g.adicionar(33, [mao_em("v04", 1.0)], [])  # o pipeline ainda tinha a referência
    d = np.load(caminho)
    assert len(d["t_ms"]) == len(d["img"]) == 1
    assert g.quadros == 1
