from controle.eventos import Tipo
from controle.poses import Pose
from controle.eventos import Evento
from controle.reconhecedor import CandidataZoom, DetectorZoom, Rastreador, so_o_arraste


def test_durante_o_arraste_so_passam_os_eventos_do_arraste():
    ev = [Evento(Tipo.APONTAR, 0, 2, 1, 1), Evento(Tipo.CLIQUE, 0, 2, valor=1), Evento(Tipo.ARRASTAR, 0, 1, 0.1, 0),
          Evento(Tipo.AREA_DE_TRABALHO, 0, 2, valor=1), Evento(Tipo.SEGURAR_FIM, 0, 1),
          Evento(Tipo.ALT_TAB_FIM, 0, 2), Evento(Tipo.ROLAGEM, 0, 2, y=1)]
    assert [e.tipo for e in so_o_arraste(ev)] == [Tipo.ARRASTAR, Tipo.SEGURAR_FIM, Tipo.ALT_TAB_FIM]


def Z(ident, pose, centro, desde_ms=0, ocupada=False):
    return CandidataZoom(ident, pose, centro, desde_ms, ocupada)


def test_rastreador_mantem_identidade_pela_posicao_mesmo_com_ordem_trocada():
    r = Rastreador()
    a, _ = r.atualizar(0, [(0.3, 0.5), (1.4, 0.5)])
    b, _ = r.atualizar(33, [(1.41, 0.5), (0.31, 0.5)])
    assert b == [a[1], a[0]]


def test_rastreador_tolera_sumico_curto_e_encerra_sumico_longo():
    r = Rastreador(perda_ms=300)
    (ident,), _ = r.atualizar(0, [(0.5, 0.5)])
    _, perdidas = r.atualizar(200, [])
    assert perdidas == []
    (mesmo,), _ = r.atualizar(233, [(0.52, 0.5)])
    assert mesmo == ident
    _, perdidas = r.atualizar(600, [])
    assert perdidas == [ident]


def test_rastreador_cria_nova_identidade_para_mao_longe():
    r = Rastreador()
    (a,), _ = r.atualizar(0, [(0.2, 0.5)])
    ids, _ = r.atualizar(33, [(0.2, 0.5), (1.5, 0.5)])
    assert ids[0] == a and ids[1] != a


def test_zoom_com_duas_maos_em_c_afastando_aproxima_e_juntando_afasta():
    z = DetectorZoom()
    eventos = []
    for i in range(12):  # afasta de 0,6 para ~1,1
        d = 0.6 + 0.045 * i
        eventos += z.atualizar(i * 33, [Z(1, Pose.C, (0.9 - d / 2, 0.5)), Z(2, Pose.C, (0.9 + d / 2, 0.5))])
    positivos = [e for e in eventos if e.tipo is Tipo.ZOOM and e.valor == 1]
    assert len(positivos) >= 4
    eventos = []
    for i in range(12):  # volta
        d = 1.1 - 0.045 * i
        eventos += z.atualizar(400 + i * 33, [Z(1, Pose.C, (0.9 - d / 2, 0.5)), Z(2, Pose.C, (0.9 + d / 2, 0.5))])
    assert all(e.valor == -1 for e in eventos) and len(eventos) >= 4
    assert z.ativo == {1, 2}


def test_zoom_avisa_inicio_e_fim_da_sessao():
    z = DetectorZoom()
    eventos = []
    for i in range(6):
        eventos += z.atualizar(i * 33, [Z(1, Pose.PINCA, (0.6, 0.5)), Z(2, Pose.PINCA, (1.2, 0.5))])
    eventos += z.atualizar(300, [Z(1, Pose.ABERTA, (0.6, 0.5)), Z(2, Pose.PINCA, (1.2, 0.5))])
    assert [e.tipo for e in eventos] == [Tipo.ZOOM_INICIO, Tipo.ZOOM_FIM]


def test_zoom_religa_logo_depois_mesmo_com_uma_pinca_antiga():
    # reajustar uma das mãos no meio da sessão: a outra segue em pinça há mais de 3 s
    z = DetectorZoom()
    for i in range(6):
        z.atualizar(i * 33, [Z(1, Pose.PINCA, (0.6, 0.5)), Z(2, Pose.PINCA, (1.2, 0.5))])
    z.atualizar(4000, [Z(1, Pose.ABERTA, (0.6, 0.5)), Z(2, Pose.PINCA, (1.2, 0.5))])
    eventos = z.atualizar(4500, [Z(1, Pose.PINCA, (0.6, 0.5), desde_ms=4400), Z(2, Pose.PINCA, (1.2, 0.5), desde_ms=0)])
    assert [e.tipo for e in eventos] == [Tipo.ZOOM_INICIO]


def test_zoom_exige_as_duas_maos():
    z = DetectorZoom()
    eventos = []
    for i in range(12):
        eventos += z.atualizar(i * 33, [Z(1, Pose.C, (0.5 + 0.05 * i, 0.5)), Z(2, Pose.INDICADOR, (1.4, 0.5))])
    assert eventos == [] and z.ativo == set()


def test_zoom_nao_liga_se_uma_mao_esta_arrastando():
    z = DetectorZoom()
    eventos = []
    for i in range(12):
        d = 0.6 + 0.045 * i
        eventos += z.atualizar(i * 33, [Z(1, Pose.PINCA, (0.9 - d / 2, 0.5), ocupada=True),
                                         Z(2, Pose.C, (0.9 + d / 2, 0.5))])
    assert eventos == [] and z.ativo == set()


def test_zoom_liga_com_a_segunda_pinca_ate_3_s_depois_da_primeira():
    # a primeira pinça já estava parada (pronta para arrastar): antes isso bloqueava o zoom
    z = DetectorZoom()
    eventos = []
    for i in range(12):
        d = 0.6 + 0.045 * i
        eventos += z.atualizar(5000 + i * 33, [Z(1, Pose.PINCA, (0.9 - d / 2, 0.5), desde_ms=2400),
                                                Z(2, Pose.PINCA, (0.9 + d / 2, 0.5), desde_ms=4900)])
    assert [e.valor for e in eventos].count(1) >= 4


def test_zoom_exige_que_as_duas_maos_formem_o_c_perto_no_tempo():
    # mão parada em C há tempo (repouso) + outra que fecha a pinça depois: não é zoom
    z = DetectorZoom()
    eventos = []
    for i in range(12):
        d = 0.6 + 0.045 * i
        eventos += z.atualizar(5000 + i * 33, [Z(1, Pose.C, (0.9 - d / 2, 0.5), desde_ms=0),
                                                Z(2, Pose.PINCA, (0.9 + d / 2, 0.5), desde_ms=4800)])
    assert eventos == []
