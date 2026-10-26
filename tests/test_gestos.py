"""Máquina de estados de uma mão, com sequências sintéticas de medidas (30 fps)."""
import dataclasses

import pytest

from controle.eventos import Tipo
from controle.geometria import Medidas
from controle.gestos import MaquinaMao, Parametros
from controle.poses import Pose

QUADRO_MS = 33


def med(**kw) -> Medidas:
    base = dict(
        retidao={"T": 0.95, "I": 0.95, "M": 0.95, "A": 0.95, "P": 0.95},
        pinca=1.0, pinca_medio=1.0, angulo_polegar=20.0, afastamento_polegar=0.9, polegar_dy=0.0,
        centro=(0.9, 0.5), no_indicador=(0.9, 0.4), tamanho=0.25, na_borda=False,
    )
    if "ret" in kw:
        base["retidao"] = {**base["retidao"], **kw.pop("ret")}
    base.update(kw)
    return Medidas(**base)


class Roteiro:
    """Alimenta a máquina quadro a quadro e guarda os eventos."""

    def __init__(self, params: Parametros | None = None):
        self.maquina = MaquinaMao(1, params or Parametros())
        self.t = 0
        self.eventos = []

    def quadros(self, n: int, pose: Pose, **kw):
        for _ in range(n):
            self.um(pose, **kw)
        return self

    def um(self, pose: Pose, **kw):
        self.eventos += self.maquina.atualizar(self.t, med(**kw), pose)
        self.t += QUADRO_MS
        return self

    def tipos(self) -> list[Tipo]:
        return [e.tipo for e in self.eventos if e.tipo not in (Tipo.APONTAR, Tipo.ROLAGEM)]

    def de(self, tipo: Tipo):
        return [e for e in self.eventos if e.tipo is tipo]


# ---------- indicador: cursor e clique por pinça ----------

def test_indicador_estavel_aponta_pelo_no_do_dedo():
    r = Roteiro().quadros(5, Pose.INDICADOR, no_indicador=(0.7, 0.45))
    apontar = r.de(Tipo.APONTAR)
    assert apontar and (apontar[-1].x, apontar[-1].y) == (0.7, 0.45)


def pinca_rapida(r: Roteiro, quadros: int = 4, **kw):
    r.quadros(quadros, Pose.PINCA, pinca=0.2, ret={"I": 0.8}, **kw)


def test_pinca_rapida_apontando_e_clique_esquerdo():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    pinca_rapida(r)
    r.quadros(5, Pose.INDICADOR)
    cliques = r.de(Tipo.CLIQUE)
    assert len(cliques) == 1 and cliques[0].valor == 1


def test_duas_pincas_rapidas_sao_dois_cliques():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    pinca_rapida(r)
    r.quadros(3, Pose.INDICADOR)
    pinca_rapida(r)
    r.quadros(3, Pose.INDICADOR)
    assert [e.valor for e in r.de(Tipo.CLIQUE)] == [1, 1]


def test_duplo_clique_com_segunda_pinca_logo_em_seguida():
    # só 1 quadro aberto entre as pinças: a pose estável ainda é PINCA quando a segunda começa
    r = Roteiro().quadros(10, Pose.INDICADOR)
    pinca_rapida(r)
    r.um(Pose.INDICADOR)
    pinca_rapida(r)
    r.quadros(5, Pose.INDICADOR)
    assert [e.valor for e in r.de(Tipo.CLIQUE)] == [1, 1]


def test_clique_informa_quando_a_pinca_comecou_para_o_cursor_voltar():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    inicio = r.t
    pinca_rapida(r)
    r.quadros(3, Pose.INDICADOR)
    assert r.de(Tipo.CLIQUE)[0].t_ref == inicio


def test_pinca_demorada_parada_nao_clica_nem_arrasta():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    pinca_rapida(r, quadros=20)
    r.quadros(5, Pose.INDICADOR)
    assert not r.de(Tipo.CLIQUE) and Tipo.SEGURAR_INICIO not in r.tipos()


def test_pinca_vinda_da_mao_aberta_nao_clica():
    r = Roteiro().quadros(10, Pose.ABERTA)
    pinca_rapida(r)
    r.quadros(5, Pose.ABERTA)
    assert not r.de(Tipo.CLIQUE)


def test_pinca_rapida_com_a_mao_andando_nao_clica():
    r = Roteiro().quadros(10, Pose.INDICADOR, centro=(0.9, 0.5))
    for i in range(1, 5):
        r.um(Pose.PINCA, pinca=0.2, centro=(0.9 + 0.03 * i, 0.5))
    r.quadros(5, Pose.INDICADOR, centro=(1.02, 0.5))
    assert not r.de(Tipo.CLIQUE)


def test_polegar_no_medio_rapido_e_clique_direito():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    r.quadros(4, Pose.INDICADOR, pinca_medio=0.2)
    r.quadros(5, Pose.INDICADOR)
    cliques = r.de(Tipo.CLIQUE)
    assert len(cliques) == 1 and cliques[0].valor == 3


def test_clique_direito_a_partir_de_dois_dedos():
    # jeito do Arthur: estica o médio e encosta o polegar na ponta dele; volta para dois dedos
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS)
    r.quadros(5, Pose.DESCONHECIDA, pinca_medio=0.2, ret={"M": 0.7})
    r.quadros(5, Pose.DOIS_DEDOS)
    cliques = r.de(Tipo.CLIQUE)
    assert [c.valor for c in cliques] == [3]


def test_polegar_encostando_nos_dois_dedos_ao_mesmo_tempo_nao_clica():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    r.quadros(4, Pose.DESCONHECIDA, pinca=0.21, pinca_medio=0.35)
    r.quadros(5, Pose.INDICADOR)
    assert not r.de(Tipo.CLIQUE)


def test_depois_do_clique_direito_a_mao_escorregando_nao_rola():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(5, Pose.DESCONHECIDA, pinca_medio=0.2, ret={"M": 0.7}, centro=(0.9, 0.5))
    for i in range(1, 6):  # solta em dois dedos e a mão escorrega 0,04
        r.um(Pose.DOIS_DEDOS, centro=(0.9 + 0.008 * i, 0.5))
    r.quadros(20, Pose.DOIS_DEDOS, centro=(0.94, 0.5))
    assert [c.valor for c in r.de(Tipo.CLIQUE)] == [3]
    assert not r.de(Tipo.ROLAGEM)


def test_mao_fechando_inteira_nao_e_clique_direito():
    r = Roteiro().quadros(10, Pose.INDICADOR)
    r.quadros(4, Pose.PUNHO, pinca=0.2, pinca_medio=0.2, ret={"I": 0.5})
    r.quadros(5, Pose.INDICADOR)
    assert not [e for e in r.de(Tipo.CLIQUE) if e.valor == 3]


# ---------- segurar e arrastar ----------

def test_fechar_e_deslocar_segura_arrasta_e_solta():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 11):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.02 * i))
    r.quadros(5, Pose.ABERTA)
    tipos = r.tipos()
    assert tipos[0] is Tipo.SEGURAR_INICIO and tipos[-1] is Tipo.SEGURAR_FIM
    assert sum(e.y for e in r.de(Tipo.ARRASTAR)) == pytest.approx(0.2, abs=0.05)
    assert Tipo.VISAO_GERAL not in tipos and not r.de(Tipo.CLIQUE)


def test_arrastando_a_maquina_avisa_e_nao_gera_clique_ao_soltar():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 6):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.03 * i))
    assert r.maquina.arrastando
    r.quadros(5, Pose.INDICADOR, centro=(0.9, 0.65))
    assert not r.maquina.arrastando and not r.de(Tipo.CLIQUE)


def test_mao_que_chega_fechada_e_em_movimento_nao_arrasta():
    r = Roteiro()
    for i in range(12):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.3 + 0.03 * i))
    assert Tipo.SEGURAR_INICIO not in r.tipos()


def test_mao_que_aparece_ja_fechada_nao_arrasta():
    r = Roteiro().quadros(12, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 11):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.02 * i))
    assert Tipo.SEGURAR_INICIO not in r.tipos()


def test_arraste_nao_comeca_em_quadro_de_mao_abrindo():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    r.um(Pose.DESCONHECIDA, centro=(0.85, 0.55))
    r.um(Pose.DESCONHECIDA, centro=(0.83, 0.57))
    r.quadros(5, Pose.ABERTA, centro=(0.83, 0.57))
    assert Tipo.SEGURAR_INICIO not in r.tipos()


def test_arraste_nao_comeca_com_a_palma_na_borda():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 11):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.02 * i), na_borda=True)
    assert Tipo.SEGURAR_INICIO not in r.tipos()


def test_mao_perdida_solta_o_botao():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 6):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.03 * i))
    r.eventos += r.maquina.encerrar(r.t)
    assert r.tipos()[-1] is Tipo.SEGURAR_FIM


# ---------- expandir e visão geral (aprovados no teste ao vivo) ----------

def test_fechada_e_depois_l_por_300_ms_expande():
    r = Roteiro().quadros(5, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.2).quadros(12, Pose.L)
    assert r.tipos().count(Tipo.EXPANDIR) == 1


def test_pinca_rapida_seguida_de_l_nao_expande():
    # g_zoom_3: apontando com o polegar aberto (~50°, conta como L), pinça de ~100 ms e volta
    r = Roteiro().quadros(10, Pose.L).quadros(4, Pose.PINCA, pinca=0.3).quadros(15, Pose.L)
    assert Tipo.EXPANDIR not in r.tipos()


def test_l_rapido_nao_expande():
    r = Roteiro().quadros(10, Pose.PINCA, pinca=0.2).quadros(4, Pose.L).quadros(10, Pose.PINCA)
    assert Tipo.EXPANDIR not in r.tipos()


def test_l_sem_mao_fechada_antes_nao_expande():
    r = Roteiro().quadros(10, Pose.INDICADOR).quadros(15, Pose.L)
    assert Tipo.EXPANDIR not in r.tipos()


def test_soltar_em_l_solta_e_depois_expande():
    r = Roteiro().quadros(5, Pose.INDICADOR).quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 11):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9 - 0.02 * i, 0.5))
    r.quadros(12, Pose.L)
    tipos = r.tipos()
    assert tipos.index(Tipo.SEGURAR_FIM) < tipos.index(Tipo.EXPANDIR)


def test_abrir_fechar_e_abrir_rapido_abre_visao_geral():
    r = Roteiro().quadros(10, Pose.ABERTA).quadros(15, Pose.PUNHO).quadros(10, Pose.ABERTA)
    assert r.tipos() == [Tipo.VISAO_GERAL]


def test_punho_demorado_nao_abre_visao_geral():
    r = Roteiro().quadros(10, Pose.ABERTA).quadros(60, Pose.PUNHO).quadros(10, Pose.ABERTA)
    assert Tipo.VISAO_GERAL not in r.tipos()


# ---------- rolagem joystick ----------

def test_dois_dedos_com_a_mao_abaixo_do_centro_rolam_para_cima_sem_parar():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(15, Pose.DOIS_DEDOS, centro=(0.9, 0.62))
    rolagem = r.de(Tipo.ROLAGEM)
    assert len(rolagem) >= 14 and sum(e.y for e in rolagem) > 1
    assert sum(e.x for e in rolagem) == 0


def test_mao_a_esquerda_do_centro_rola_para_a_direita():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(15, Pose.DOIS_DEDOS, centro=(0.78, 0.5))
    assert sum(e.x for e in r.de(Tipo.ROLAGEM)) > 1


def test_mao_acima_do_centro_rola_para_baixo():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(15, Pose.DOIS_DEDOS, centro=(0.9, 0.38))
    assert sum(e.y for e in r.de(Tipo.ROLAGEM)) < -1


def test_dentro_da_zona_morta_nao_rola():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(15, Pose.DOIS_DEDOS, centro=(0.915, 0.515))
    assert not r.de(Tipo.ROLAGEM)


def test_mais_longe_do_centro_rola_mais_rapido():
    perto = Roteiro().quadros(10, Pose.DOIS_DEDOS).quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.58))
    longe = Roteiro().quadros(10, Pose.DOIS_DEDOS).quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.68))
    assert sum(e.y for e in longe.de(Tipo.ROLAGEM)) > 2 * sum(e.y for e in perto.de(Tipo.ROLAGEM))


def test_falha_de_rastreio_nao_gera_rajada_de_rolagem():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(3, Pose.DOIS_DEDOS, centro=(0.9, 0.9))  # longe: velocidade máxima
    r.t += 250  # mão sumiu 250 ms
    r.um(Pose.DOIS_DEDOS, centro=(0.9, 0.9))
    assert r.de(Tipo.ROLAGEM)[-1].y <= 20 * 0.1 + 1e-9  # no máximo ~3 quadros de rolagem


def test_sair_da_pose_para_e_voltar_recentra():
    r = Roteiro().quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.5))
    r.quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.62))
    r.quadros(5, Pose.INDICADOR, centro=(0.9, 0.62))
    antes = len(r.de(Tipo.ROLAGEM))
    r.quadros(10, Pose.DOIS_DEDOS, centro=(0.9, 0.62))
    assert len(r.de(Tipo.ROLAGEM)) == antes


# ---------- Alt+Tab com três dedos ----------

def test_tres_dedos_abre_desliza_nos_dois_sentidos_e_mudar_de_pose_escolhe():
    r = Roteiro().quadros(10, Pose.TRES_DEDOS, centro=(0.9, 0.5))
    for i in range(1, 9):  # 0,16 para a direita: dois degraus
        r.um(Pose.TRES_DEDOS, centro=(0.9 + 0.02 * i, 0.5))
    for i in range(1, 5):  # 0,08 de volta: um degrau
        r.um(Pose.TRES_DEDOS, centro=(1.06 - 0.02 * i, 0.5))
    r.quadros(5, Pose.ABERTA, centro=(0.98, 0.5))
    assert r.tipos() == [Tipo.ALT_TAB_INICIO, Tipo.ALT_TAB_PROXIMO, Tipo.ALT_TAB_PROXIMO,
                         Tipo.ALT_TAB_ANTERIOR, Tipo.ALT_TAB_FIM]


def test_mao_perdida_no_alt_tab_solta_o_alt():
    r = Roteiro().quadros(10, Pose.TRES_DEDOS)
    r.eventos += r.maquina.encerrar(r.t)
    assert r.tipos() == [Tipo.ALT_TAB_INICIO, Tipo.ALT_TAB_FIM]


# ---------- fechar janela: polegar para baixo segurado ----------

def test_polegar_para_baixo_segurado_fecha_e_mostra_progresso():
    r = Roteiro().quadros(13, Pose.POLEGAR_BAIXO)
    assert 0.3 < r.maquina.progresso_fechar < 0.7 and Tipo.FECHAR_JANELA not in r.tipos()
    r.quadros(15, Pose.POLEGAR_BAIXO)
    assert r.tipos() == [Tipo.FECHAR_JANELA]
    r.quadros(5, Pose.ABERTA)
    assert r.maquina.progresso_fechar == 0


def test_polegar_para_baixo_curto_cancela():
    r = Roteiro().quadros(12, Pose.POLEGAR_BAIXO).quadros(10, Pose.ABERTA)
    assert Tipo.FECHAR_JANELA not in r.tipos()


def test_dois_fechamentos_respeitam_intervalo_de_2_s():
    r = Roteiro().quadros(30, Pose.POLEGAR_BAIXO).quadros(5, Pose.ABERTA).quadros(30, Pose.POLEGAR_BAIXO)
    assert r.tipos().count(Tipo.FECHAR_JANELA) == 1


# ---------- bloqueio (outra mão arrastando) ----------

def test_maquina_bloqueada_nao_comeca_gestos_e_exige_nova_pose_depois():
    r = Roteiro()
    r.maquina.bloqueada = True
    r.quadros(10, Pose.TRES_DEDOS)
    assert r.tipos() == []
    r.maquina.bloqueada = False
    r.quadros(10, Pose.TRES_DEDOS)  # pose segurada desde o bloqueio: não abre o Alt+Tab
    assert r.tipos() == []
    r.quadros(5, Pose.ABERTA).quadros(5, Pose.TRES_DEDOS)
    assert r.tipos() == [Tipo.ALT_TAB_INICIO]


def test_bloquear_no_meio_do_alt_tab_solta_o_alt():
    r = Roteiro().quadros(10, Pose.TRES_DEDOS)
    r.maquina.bloqueada = True
    r.um(Pose.TRES_DEDOS)
    assert r.tipos() == [Tipo.ALT_TAB_INICIO, Tipo.ALT_TAB_FIM]


# ---------- troca de área ----------

def varrer(r: Roteiro, de: float, ate: float, quadros: int, y: float = 0.6):
    for i in range(1, quadros + 1):
        r.um(Pose.ABERTA, centro=(de + (ate - de) * i / quadros, y))


def test_varredura_rapida_para_a_esquerda_vai_para_a_area_da_esquerda():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    varrer(r, 1.2, 0.7, 7)
    assert [e.valor for e in r.de(Tipo.AREA_DE_TRABALHO)] == [-1]


def test_ida_e_volta_sem_parar_troca_uma_vez_so():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    varrer(r, 1.2, 0.7, 7)
    varrer(r, 0.7, 1.2, 7)
    assert [e.valor for e in r.de(Tipo.AREA_DE_TRABALHO)] == [-1]


def test_ida_parada_e_volta_trocam_nos_dois_sentidos():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    varrer(r, 1.2, 0.7, 7)
    r.quadros(8, Pose.ABERTA, centro=(0.7, 0.6))
    varrer(r, 0.7, 1.2, 7)
    assert [e.valor for e in r.de(Tipo.AREA_DE_TRABALHO)] == [-1, 1]


def test_mao_virando_de_lado_no_retorno_nao_rearma():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    varrer(r, 1.2, 0.7, 7)
    for i in range(1, 4):  # a palma gira e vira C por 3 quadros no meio do retorno
        r.um(Pose.C, centro=(0.7 + 0.07 * i, 0.6))
    varrer(r, 0.91, 1.3, 6)
    assert [e.valor for e in r.de(Tipo.AREA_DE_TRABALHO)] == [-1]


def test_movimento_lento_nao_troca_area():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    varrer(r, 1.2, 0.7, 30)
    assert not r.de(Tipo.AREA_DE_TRABALHO)


def test_mao_virando_indicador_no_meio_do_movimento_nao_troca_area():
    r = Roteiro().quadros(5, Pose.ABERTA, centro=(1.2, 0.6))
    for i, pose in enumerate([Pose.ABERTA, Pose.INDICADOR, Pose.INDICADOR, Pose.PINCA, Pose.INDICADOR,
                              Pose.INDICADOR, Pose.INDICADOR], start=1):
        r.um(pose, centro=(1.2 - 0.07 * i, 0.6))
    assert not r.de(Tipo.AREA_DE_TRABALHO)


# ---------- outros ----------

def test_maquina_em_zoom_ignora_mao_fechada():
    r = Roteiro()
    r.maquina.em_zoom = True
    r.quadros(10, Pose.PINCA, pinca=0.1, centro=(0.9, 0.5))
    for i in range(1, 11):
        r.um(Pose.PINCA, pinca=0.1, centro=(0.9, 0.5 + 0.03 * i))
    assert Tipo.SEGURAR_INICIO not in r.tipos()


def test_parametros_sao_imutaveis_por_instancia():
    p = Parametros()
    assert dataclasses.replace(p, l_espera_ms=500).l_espera_ms == 500
