from controle.cursor import Cursor, Retangulo
from controle.eventos import Evento, Tipo
from controle.legenda import GESTOS, gesto_do_evento
from controle.saida import BOTAO_DIREITO, BOTAO_ESQUERDO, CTRL, ALT, SHIFT, TAB, Executor


class SaidaFalsa:
    def __init__(self):
        self.chamadas = []

    def mover_absoluto(self, u, v):
        self.chamadas.append(("mover", round(u, 3), round(v, 3)))

    def botao(self, codigo, pressionado):
        self.chamadas.append(("botao", codigo, pressionado))

    def rolar(self, horizontal_hr, vertical_hr, horizontal, vertical):
        self.chamadas.append(("rolar", horizontal_hr, vertical_hr, horizontal, vertical))

    def tecla(self, codigo, pressionada):
        self.chamadas.append(("tecla", codigo, pressionada))

    def atalho_kwin(self, nome):
        self.chamadas.append(("kwin", nome))


def executor():
    saida = SaidaFalsa()
    cursor = Cursor([Retangulo(0, 0, 1920, 1080)], modo="absoluto", regiao=0.5, aspecto=16 / 9,
                    centro_regiao=(8 / 9, 0.5), suavizar=False)
    return Executor(saida, cursor), saida


def ev(tipo, **kw):
    return Evento(tipo, kw.pop("t", 0), 1, **kw)


def test_apontar_move_o_ponteiro_absoluto():
    ex, saida = executor()
    ex.executar([ev(Tipo.APONTAR, x=8 / 9, y=0.5)])
    assert saida.chamadas == [("mover", 0.5, 0.5)]


def test_clique_esquerdo_e_direito_apertam_e_soltam():
    ex, saida = executor()
    ex.executar([ev(Tipo.CLIQUE, valor=1), ev(Tipo.CLIQUE, valor=3)])
    assert saida.chamadas == [("botao", BOTAO_ESQUERDO, True), ("botao", BOTAO_ESQUERDO, False),
                              ("botao", BOTAO_DIREITO, True), ("botao", BOTAO_DIREITO, False)]


def test_clique_volta_o_cursor_para_onde_estava_quando_a_pinca_comecou():
    ex, saida = executor()
    ex.executar([ev(Tipo.APONTAR, t=0, x=8 / 9, y=0.5), ev(Tipo.APONTAR, t=33, x=8 / 9 + 0.1, y=0.5)])
    saida.chamadas.clear()
    ex.executar([ev(Tipo.CLIQUE, t=66, valor=1, t_ref=10)])
    assert saida.chamadas == [("mover", 0.5, 0.5), ("botao", BOTAO_ESQUERDO, True),
                              ("botao", BOTAO_ESQUERDO, False)]


def test_segurar_arrastar_e_soltar():
    ex, saida = executor()
    ex.executar([ev(Tipo.SEGURAR_INICIO), ev(Tipo.ARRASTAR, x=0.1, y=0.0), ev(Tipo.SEGURAR_FIM)])
    assert saida.chamadas[0] == ("botao", BOTAO_ESQUERDO, True)
    assert saida.chamadas[1][0] == "mover"
    assert saida.chamadas[2] == ("botao", BOTAO_ESQUERDO, False)


def test_rolagem_manda_alta_resolucao_e_entalhe_classico_ao_completar_120():
    ex, saida = executor()
    ex.executar([ev(Tipo.ROLAGEM, y=0.5), ev(Tipo.ROLAGEM, y=0.6)])
    assert saida.chamadas == [("rolar", 0, 60, 0, 0), ("rolar", 0, 72, 0, 1)]


def test_atalhos_do_kwin():
    ex, saida = executor()
    ex.executar([ev(Tipo.EXPANDIR), ev(Tipo.VISAO_GERAL), ev(Tipo.AREA_DE_TRABALHO, valor=-1),
                 ev(Tipo.AREA_DE_TRABALHO, valor=1), ev(Tipo.FECHAR_JANELA)])
    assert saida.chamadas == [("kwin", "Window Maximize"), ("kwin", "Overview"),
                              ("kwin", "Switch One Desktop to the Left"),
                              ("kwin", "Switch One Desktop to the Right"), ("kwin", "Window Close")]


def test_alt_tab_segura_alt_e_toca_tab():
    ex, saida = executor()
    ex.executar([ev(Tipo.ALT_TAB_INICIO), ev(Tipo.ALT_TAB_PROXIMO), ev(Tipo.ALT_TAB_FIM)])
    assert saida.chamadas == [("tecla", ALT, True), ("tecla", TAB, True), ("tecla", TAB, False),
                              ("tecla", TAB, True), ("tecla", TAB, False), ("tecla", ALT, False)]


def test_proximo_sem_alt_pressionado_comeca_o_alt_tab_em_vez_de_digitar_tab():
    # o ALT_TAB_INICIO pode ter sido pulado (pausa ou gesto desligado)
    ex, saida = executor()
    ex.executar([ev(Tipo.ALT_TAB_PROXIMO), ev(Tipo.ALT_TAB_FIM)])
    assert saida.chamadas == [("tecla", ALT, True), ("tecla", TAB, True), ("tecla", TAB, False),
                              ("tecla", ALT, False)]


def test_anterior_e_shift_tab_com_alt_segurado():
    ex, saida = executor()
    ex.executar([ev(Tipo.ALT_TAB_INICIO)])
    saida.chamadas.clear()
    ex.executar([ev(Tipo.ALT_TAB_ANTERIOR)])
    assert saida.chamadas == [("tecla", SHIFT, True), ("tecla", TAB, True), ("tecla", TAB, False),
                              ("tecla", SHIFT, False)]


def test_inverter_rolagem_troca_os_dois_sentidos():
    ex, saida = executor()
    ex.inverter_rolagem = True
    ex.executar([ev(Tipo.ROLAGEM, x=1.0, y=1.0)])
    assert saida.chamadas == [("rolar", -120, -120, -1, -1)]


def test_zoom_segura_ctrl_a_sessao_inteira():
    # Ctrl e roda em dispositivos diferentes, no mesmo instante: o KDE podia ver a roda antes do Ctrl
    ex, saida = executor()
    ex.executar([ev(Tipo.ZOOM_INICIO), ev(Tipo.ZOOM, valor=1), ev(Tipo.ZOOM, valor=-1), ev(Tipo.ZOOM_FIM)])
    assert saida.chamadas == [("tecla", CTRL, True), ("rolar", 0, 120, 0, 1), ("rolar", 0, -120, 0, -1),
                              ("tecla", CTRL, False)]


def test_passo_de_zoom_sem_inicio_aperta_ctrl_antes():
    ex, saida = executor()
    ex.executar([ev(Tipo.ZOOM, valor=1)])
    assert saida.chamadas == [("tecla", CTRL, True), ("rolar", 0, 120, 0, 1)]
    saida.chamadas.clear()
    ex.liberar_tudo()
    assert saida.chamadas == [("tecla", CTRL, False)]


def test_gesto_desligado_nao_executa_mas_soltar_sempre_executa():
    ex, saida = executor()
    ex.executar([ev(Tipo.SEGURAR_INICIO)])
    ex.habilitados.discard("segurar")
    ex.executar([ev(Tipo.SEGURAR_INICIO), ev(Tipo.SEGURAR_FIM)])
    assert saida.chamadas == [("botao", BOTAO_ESQUERDO, True), ("botao", BOTAO_ESQUERDO, False)]


def test_pausado_nao_executa_nada():
    ex, saida = executor()
    ex.ativo = False
    ex.executar([ev(Tipo.CLIQUE, valor=1), ev(Tipo.FECHAR_JANELA), ev(Tipo.APONTAR, x=1, y=0.5)])
    assert saida.chamadas == []


def test_liberar_tudo_solta_o_que_estiver_pressionado():
    ex, saida = executor()
    ex.executar([ev(Tipo.SEGURAR_INICIO), ev(Tipo.ALT_TAB_INICIO)])
    saida.chamadas.clear()
    ex.liberar_tudo()
    assert sorted(saida.chamadas) == sorted([("botao", BOTAO_ESQUERDO, False), ("tecla", ALT, False)])


def test_executar_devolve_as_acoes_para_a_legenda():
    ex, _ = executor()
    feitas = ex.executar([ev(Tipo.APONTAR, x=1, y=0.5), ev(Tipo.CLIQUE, valor=3), ev(Tipo.EXPANDIR)])
    assert [g for g, _ in feitas] == ["clique_direito", "expandir"]


def test_todo_evento_que_age_tem_gesto_na_legenda():
    ids = {g.id for g in GESTOS}
    for tipo in Tipo:
        for valor in (1, 3):
            gesto = gesto_do_evento(Evento(tipo, 0, 1, valor=valor))
            assert gesto is None or gesto in ids
