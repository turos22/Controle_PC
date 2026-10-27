import pytest

from controle.plataforma import macos as m
from controle.plataforma.base import Botao, Tecla


class QuartzFalso:
    kCGHIDEventTap = "hid"
    kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventLeftMouseDragged = 5, 1, 2, 6
    kCGEventRightMouseDown, kCGEventRightMouseUp, kCGEventRightMouseDragged = 3, 4, 7
    kCGMouseButtonLeft, kCGMouseButtonRight = 0, 1
    kCGScrollEventUnitPixel = 0

    def __init__(self):
        self.postados = []

    def CGEventCreateMouseEvent(self, fonte, tipo, ponto, botao):
        return {"tipo": tipo, "ponto": tuple(ponto), "botao": botao}

    def CGEventCreateKeyboardEvent(self, fonte, codigo, baixo):
        return {"tecla": codigo, "baixo": baixo, "flags": 0}

    def CGEventCreateScrollWheelEvent(self, fonte, unidade, eixos, vertical, horizontal):
        return {"rolagem": (horizontal, vertical)}

    def CGEventSetFlags(self, evento, flags):
        evento["flags"] = flags

    def CGEventPost(self, destino, evento):
        self.postados.append(evento)


TELAS = [(0, 0, 1920, 1080), (1920, 0, 1422, 800)]


def entrada():
    q = QuartzFalso()
    return m.EntradaMacos(quartz=q, telas=TELAS), q.postados


def test_mover_posiciona_sobre_a_area_que_envolve_todas_as_telas():
    e, p = entrada()
    e.mover_absoluto(0.0, 0.0)
    e.mover_absoluto(1.0, 1.0)
    assert p[0]["ponto"] == (0, 0) and p[0]["tipo"] == QuartzFalso.kCGEventMouseMoved
    assert p[1]["ponto"] == (3341, 1079)


def test_com_o_botao_esquerdo_apertado_mover_arrasta():
    e, p = entrada()
    e.mover_absoluto(0.5, 0.5)
    e.botao(Botao.ESQUERDO, True)
    e.mover_absoluto(0.6, 0.5)
    e.botao(Botao.ESQUERDO, False)
    assert [x["tipo"] for x in p] == [QuartzFalso.kCGEventMouseMoved, QuartzFalso.kCGEventLeftMouseDown,
                                      QuartzFalso.kCGEventLeftMouseDragged, QuartzFalso.kCGEventLeftMouseUp]
    assert p[1]["ponto"] == p[0]["ponto"]  # o clique cai onde o ponteiro está


def test_botao_direito():
    e, p = entrada()
    e.botao(Botao.DIREITO, True)
    e.botao(Botao.DIREITO, False)
    assert [(x["tipo"], x["botao"]) for x in p] == [(QuartzFalso.kCGEventRightMouseDown, 1),
                                                    (QuartzFalso.kCGEventRightMouseUp, 1)]


def test_rolagem_em_pixels_com_sinal():
    e, p = entrada()
    e.rolar(0, 120, 0, 1)
    e.rolar(-120, 0, -1, 0)
    assert p[0]["rolagem"][1] > 0 and p[0]["rolagem"][0] == 0
    assert p[1]["rolagem"][0] < 0 and p[1]["rolagem"][1] == 0


def test_rolagem_nula_nao_envia():
    e, p = entrada()
    e.rolar(0, 0, 0, 0)
    assert p == []


def test_tecla_leva_os_modificadores_que_estao_apertados():
    e, p = entrada()
    e.tecla(Tecla.META, True)
    e.tecla(Tecla.TAB, True)
    e.tecla(Tecla.TAB, False)
    e.tecla(Tecla.META, False)
    e.tecla(Tecla.TAB, True)
    assert [(x["tecla"], x["baixo"]) for x in p] == [(55, True), (48, True), (48, False), (55, False), (48, True)]
    assert p[1]["flags"] & m.FLAG_COMANDO and p[2]["flags"] & m.FLAG_COMANDO
    assert not p[3]["flags"] & m.FLAG_COMANDO and p[4]["flags"] == 0


def test_todas_as_teclas_tem_codigo():
    assert set(m.CODIGO_TECLA) == set(Tecla)
    assert m.CODIGO_TECLA[Tecla.W] == 13 and m.CODIGO_TECLA[Tecla.CIMA] == 126


def test_no_macos_o_comando_troca_janela_e_da_zoom():
    e, _ = entrada()
    assert (e.modificador_troca, e.modificador_zoom) == (Tecla.META, Tecla.META)


def test_sem_pyobjc_a_entrada_real_falha_com_importerror():
    with pytest.raises(ImportError):
        m.EntradaMacos()  # nesta máquina não há Quartz


def test_sem_pyobjc_a_acessibilidade_conta_como_nao_liberada():
    assert m.acessibilidade_liberada() is False
