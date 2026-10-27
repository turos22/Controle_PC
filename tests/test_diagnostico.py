from controle.cursor import Retangulo
from controle.plataforma.base import Acao
from controle.diagnostico import executar
from tests.test_saida import SaidaFalsa

TELAS = [Retangulo(0, 0, 1920, 1080), Retangulo(1920, 588, 1422, 800)]


def test_diagnostico_percorre_centro_e_cantos_de_cada_tela_e_alterna_visao_geral():
    saida = SaidaFalsa()
    executar(saida, saida, TELAS, pausa=0, avisar=lambda _: None)
    movimentos = [c for c in saida.chamadas if c[0] == "mover"]
    assert len(movimentos) == 2 * 5 + 1
    assert [c for c in saida.chamadas if c[0] == "acao"] == [("acao", Acao.VISAO_GERAL)] * 2
    assert not [c for c in saida.chamadas if c[0] in ("botao", "tecla")]  # nunca clica nem digita


def test_diagnostico_aponta_dentro_das_telas():
    saida = SaidaFalsa()
    executar(saida, saida, TELAS, pausa=0, avisar=lambda _: None)
    area_w, area_h = 3342 - 1, 1388 - 1
    for _, u, v in (c for c in saida.chamadas if c[0] == "mover"):
        x, y = u * area_w, v * area_h
        assert any(t.contem(round(x), round(y)) for t in TELAS), (x, y)
