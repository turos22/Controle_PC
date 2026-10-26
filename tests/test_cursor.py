import random
import statistics

import pytest

from controle.cursor import Cursor, FiltroOneEuro, Retangulo

TELAS = [Retangulo(0, 0, 1920, 1080), Retangulo(1920, 588, 1422, 800)]  # medidas do KWin


def cursor(**kw) -> Cursor:
    return Cursor(TELAS, modo="absoluto", regiao=0.5, aspecto=16 / 9, centro_regiao=(8 / 9, 0.5),
                  suavizar=False, **kw)


def test_area_total_e_o_retangulo_que_envolve_as_telas():
    c = cursor()
    assert c.area == Retangulo(0, 0, 3342, 1388)


def test_canto_superior_esquerdo_da_regiao_vai_para_o_canto_da_area():
    c = cursor()
    assert c.apontar(0, 8 / 9 - 4 / 9, 0.25) == (0, 0)


def test_fora_da_regiao_gruda_na_borda():
    c = cursor()
    assert c.apontar(0, -1.0, -1.0) == (0, 0)


def test_ponto_na_area_morta_e_levado_para_a_tela_mais_proxima():
    c = cursor()
    # canto superior direito da área: acima da segunda tela, onde não há tela
    x, y = c.apontar(0, 8 / 9 + 4 / 9, 0.25)
    assert TELAS[1].contem(x, y)
    assert (x, y) == (3341, 588)


def test_arrastar_usa_a_mesma_escala_do_apontar():
    c = cursor()
    c.apontar(0, 8 / 9, 0.5)
    x0, y0 = c.posicao
    x1, y1 = c.arrastar(0.1, 0.05)
    assert x1 - x0 == pytest.approx(0.1 / (8 / 9) * 3341, abs=1)
    assert y1 - y0 == pytest.approx(0.05 / 0.5 * 1388, abs=1)


def test_arrastos_lentos_acumulam_fracoes_de_pixel():
    c = cursor()
    c.apontar(0, 8 / 9, 0.5)
    x0, _ = c.posicao
    passo = 0.45 / 3341 * (8 / 9)  # ~0,45 px por quadro
    for _ in range(10):
        c.arrastar(passo, 0.0)
    assert c.posicao[0] - x0 >= 4


def test_posicao_normalizada_para_o_dispositivo_absoluto():
    c = cursor()
    c.apontar(0, 8 / 9 - 4 / 9, 0.25)
    assert c.normalizada() == (0.0, 0.0)


def relativo(**kw) -> Cursor:
    return Cursor(TELAS, modo="relativo", suavizar=False, **kw)


def mover_mao(c: Cursor, de: float, ate: float, quadros: int, t0: int = 0) -> int:
    """Move a mão em x de `de` até `ate` em `quadros` quadros; devolve o deslocamento do cursor."""
    x0 = c.posicao[0]
    for i in range(quadros + 1):
        c.apontar(t0 + i * 33, de + (ate - de) * i / quadros, 0.5)
    return c.posicao[0] - x0


def test_relativo_mao_rapida_vai_bem_mais_longe_que_mao_lenta():
    lenta = mover_mao(relativo(), 0.8, 0.9, 30)   # 0,1 em 1 s
    rapida = mover_mao(relativo(), 0.8, 0.9, 3)   # 0,1 em 0,1 s
    assert lenta > 0 and rapida > 3 * lenta


def test_relativo_movimento_amplo_e_rapido_atravessa_as_duas_telas():
    c = relativo()
    c._x = 10.0
    assert mover_mao(c, 0.5, 1.3, 8) > 3000


def test_relativo_embreagem_sair_e_voltar_nao_pula():
    c = relativo()
    mover_mao(c, 0.8, 0.9, 10)
    antes = c.posicao
    c.apontar(2000, 0.3, 0.5)  # voltou a apontar em outro lugar depois de uma pausa
    assert c.posicao == antes


def test_relativo_ignora_tremor_minimo():
    c = relativo()
    c.apontar(0, 0.9, 0.5)
    antes = c.posicao
    for i in range(1, 30):
        c.apontar(i * 33, 0.9 + (0.0002 if i % 2 else -0.0002), 0.5)
    assert c.posicao == antes


def test_relativo_velocidade_multiplica_o_deslocamento():
    normal = mover_mao(relativo(), 0.8, 0.9, 10)
    dobro = mover_mao(relativo(velocidade=2.0), 0.8, 0.9, 10)
    assert dobro == pytest.approx(2 * normal, rel=0.05)


def test_relativo_arrancada_rapida_depois_de_parado_usa_ganho_rapido():
    parado_antes = relativo()
    for t in range(0, 2001, 33):  # 2 s apontando parado (sem embreagem)
        parado_antes.apontar(t, 0.9, 0.5)
    x0 = parado_antes.posicao[0]
    parado_antes.apontar(2033, 0.95, 0.5)  # 0,05 num quadro: rápido
    assert parado_antes.posicao[0] - x0 > 0.05 * 3000 * 1.5


def test_relativo_arrastar_usa_o_mesmo_ganho_e_velocidade_do_cursor():
    def arrasto(velocidade):
        c = relativo(velocidade=velocidade)
        x0 = c.posicao[0]
        for i in range(10):
            c.arrastar(0.01, 0.0, i * 33)
        return c.posicao[0] - x0
    assert arrasto(2.0) == pytest.approx(2 * arrasto(1.0), rel=0.05)
    assert arrasto(1.0) > 0


def test_voltar_para_posicao_de_antes():
    c = relativo()
    c.apontar(0, 0.8, 0.5)
    c.apontar(33, 0.8, 0.5)
    antes = c.posicao
    for i in range(2, 6):
        c.apontar(i * 33, 0.8 + 0.01 * i, 0.5)
    assert c.posicao != antes
    c.voltar_para(40)
    assert c.posicao == antes


def test_one_euro_parado_reduz_tremor():
    f = FiltroOneEuro(freq_min=1.0, beta=5.0)
    random.seed(1)
    entrada = [0.5 + random.gauss(0, 0.004) for _ in range(120)]
    saida = [f.filtrar(i / 30, v) for i, v in enumerate(entrada)]
    assert statistics.pstdev(saida[30:]) < statistics.pstdev(entrada[30:]) / 2


def test_one_euro_em_movimento_rapido_atrasa_pouco():
    f = FiltroOneEuro(freq_min=1.0, beta=5.0)
    for i in range(30):
        f.filtrar(i / 30, 0.2)
    for i in range(30, 36):  # salto rápido para 0,8 em 6 quadros
        valor = f.filtrar(i / 30, 0.2 + 0.1 * (i - 29))
    assert valor > 0.7
