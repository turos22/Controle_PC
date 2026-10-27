from controle.plataforma import windows as w
from controle.plataforma.base import Botao, Tecla


def entrada():
    enviados = []
    return w.EntradaWindows(enviar=lambda itens: enviados.extend(itens)), enviados


def mouse(item):
    assert item.type == w.INPUT_MOUSE
    return item.u.mi


def teclado(item):
    assert item.type == w.INPUT_KEYBOARD
    return item.u.ki


def test_mover_usa_coordenadas_absolutas_sobre_a_area_virtual_inteira():
    e, enviados = entrada()
    e.mover_absoluto(0.5, 1.0)
    m = mouse(enviados[0])
    assert (m.dx, m.dy) == (round(0.5 * 65535), 65535)
    assert m.dwFlags == w.MOUSEEVENTF_MOVE | w.MOUSEEVENTF_ABSOLUTE | w.MOUSEEVENTF_VIRTUALDESK


def test_mover_limita_ao_intervalo_valido():
    e, enviados = entrada()
    e.mover_absoluto(-0.2, 1.4)
    m = mouse(enviados[0])
    assert (m.dx, m.dy) == (0, 65535)


def test_botoes_apertam_e_soltam():
    e, enviados = entrada()
    e.botao(Botao.ESQUERDO, True)
    e.botao(Botao.ESQUERDO, False)
    e.botao(Botao.DIREITO, True)
    e.botao(Botao.DIREITO, False)
    assert [mouse(i).dwFlags for i in enviados] == [w.MOUSEEVENTF_LEFTDOWN, w.MOUSEEVENTF_LEFTUP,
                                                    w.MOUSEEVENTF_RIGHTDOWN, w.MOUSEEVENTF_RIGHTUP]


def test_rolagem_vertical_e_horizontal_usam_a_alta_resolucao_com_sinal():
    e, enviados = entrada()
    e.rolar(0, -60, 0, 0)
    e.rolar(120, 0, 1, 0)
    primeiro, segundo = (mouse(i) for i in enviados)
    assert primeiro.dwFlags == w.MOUSEEVENTF_WHEEL and primeiro.mouseData == (-60) & 0xFFFFFFFF
    assert segundo.dwFlags == w.MOUSEEVENTF_HWHEEL and segundo.mouseData == 120


def test_rolagem_nula_nao_envia_nada():
    e, enviados = entrada()
    e.rolar(0, 0, 0, 0)
    assert enviados == []


def test_tecla_comum_usa_o_codigo_virtual_sem_flag_estendida():
    e, enviados = entrada()
    e.tecla(Tecla.ALT, True)
    e.tecla(Tecla.ALT, False)
    a, b = (teclado(i) for i in enviados)
    assert a.wVk == 0x12 and a.dwFlags == 0
    assert b.wVk == 0x12 and b.dwFlags == w.KEYEVENTF_KEYUP


def test_teclas_estendidas_levam_a_flag_estendida():
    e, enviados = entrada()
    for tecla in (Tecla.META, Tecla.CIMA, Tecla.ESQUERDA, Tecla.DIREITA, Tecla.PAGE_UP, Tecla.PAGE_DOWN):
        e.tecla(tecla, True)
    assert all(teclado(i).dwFlags & w.KEYEVENTF_EXTENDEDKEY for i in enviados)


def test_todas_as_teclas_tem_codigo_virtual():
    assert set(w.CODIGO_TECLA) == set(Tecla)


def test_codigos_virtuais_de_referencia():
    assert w.CODIGO_TECLA[Tecla.META] == 0x5B and w.CODIGO_TECLA[Tecla.F4] == 0x73
    assert w.CODIGO_TECLA[Tecla.TAB] == 0x09 and w.CODIGO_TECLA[Tecla.CTRL] == 0x11


def test_declara_os_modificadores_do_windows():
    e, _ = entrada()
    assert (e.modificador_troca, e.modificador_zoom) == (Tecla.ALT, Tecla.CTRL)


def test_fora_do_windows_criar_a_entrada_real_falha_com_oserror():
    import sys

    import pytest
    if sys.platform == "win32":
        pytest.skip("só vale fora do Windows")
    with pytest.raises(OSError):
        w.EntradaWindows()


def test_tamanho_da_estrutura_input_no_windows():
    # só tem como conferir no Windows: o SendInput recusa a chamada se o tamanho estiver errado
    import ctypes
    import sys

    import pytest
    if sys.platform != "win32":
        pytest.skip("só vale no Windows")
    assert ctypes.sizeof(w.INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_envio_real_de_um_movimento_no_windows():
    import sys

    import pytest
    if sys.platform != "win32":
        pytest.skip("só vale no Windows")
    w.EntradaWindows().mover_absoluto(0.5, 0.5)    # não pode levantar OSError
