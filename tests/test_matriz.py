"""Matriz de confusão nos vídeos de referência.

Iteração 2: clique, rolagem, Alt+Tab e fechar mudaram de gesto (spec, "Iteração 2"). Os vídeos
desses gestos antigos continuam úteis como teste de falso positivo. Expandir, visão geral,
arrastar, troca de área e zoom (duas pinças) continuam valendo.
"""
from collections import Counter

import pytest

from controle.eventos import Evento, Tipo
from controle.reconhecedor import Reconhecedor
from tests.conftest import carregar_gravacao

JANELA = {Tipo.FECHAR_JANELA, Tipo.AREA_DE_TRABALHO, Tipo.VISAO_GERAL, Tipo.EXPANDIR,
          Tipo.ALT_TAB_INICIO, Tipo.ZOOM, Tipo.SEGURAR_INICIO}


def eventos_de(video: str) -> list[Evento]:
    reconhecedor = Reconhecedor()
    eventos = []
    for quadro in carregar_gravacao(video):
        eventos += reconhecedor.processar(quadro)
    return eventos


def contagem(eventos: list[Evento]) -> Counter:
    c = Counter(e.tipo for e in eventos)
    c["clique_esquerdo"] = sum(1 for e in eventos if e.tipo is Tipo.CLIQUE and e.valor == 1)
    c["clique_direito"] = sum(1 for e in eventos if e.tipo is Tipo.CLIQUE and e.valor == 3)
    return c


def proibidos(eventos: list[Evento], permitidos: set[Tipo]) -> list[Tipo]:
    return sorted({e.tipo for e in eventos if e.tipo in JANELA - permitidos}, key=lambda t: t.value)


# ---------- gestos que continuam valendo ----------

def test_v01_expandir():
    ev = eventos_de("v01")
    assert contagem(ev)[Tipo.EXPANDIR] >= 2
    assert proibidos(ev, {Tipo.EXPANDIR}) == []


def test_v02_visao_geral():
    ev = eventos_de("v02")
    assert contagem(ev)[Tipo.VISAO_GERAL] >= 3
    assert proibidos(ev, {Tipo.VISAO_GERAL}) == []


def test_v03_area_de_trabalho_nos_dois_sentidos_sem_ida_e_volta_duplicada():
    ev = eventos_de("v03")
    trocas = [e for e in ev if e.tipo is Tipo.AREA_DE_TRABALHO]
    assert {e.valor for e in trocas} == {-1, 1}
    # nenhuma troca no sentido contrário menos de 0,5 s depois da anterior (era o "vai e volta")
    assert all(b.t_ms - a.t_ms >= 500 for a, b in zip(trocas, trocas[1:]) if a.valor != b.valor)
    assert proibidos(ev, {Tipo.AREA_DE_TRABALHO}) == []


def test_v07_mover_janela():
    ev = eventos_de("v07")
    c = contagem(ev)
    assert c[Tipo.SEGURAR_INICIO] >= 2 and c[Tipo.SEGURAR_INICIO] == c[Tipo.SEGURAR_FIM]
    assert proibidos(ev, {Tipo.SEGURAR_INICIO, Tipo.EXPANDIR}) == []


def test_v08_clique_segurando():
    ev = eventos_de("v08")
    c = contagem(ev)
    assert c[Tipo.SEGURAR_INICIO] >= 3 and c[Tipo.SEGURAR_INICIO] == c[Tipo.SEGURAR_FIM]
    assert proibidos(ev, {Tipo.SEGURAR_INICIO, Tipo.EXPANDIR}) == []


def test_v12_zoom_nos_dois_sentidos():
    ev = eventos_de("v12")
    valores = Counter(e.valor for e in ev if e.tipo is Tipo.ZOOM)
    assert valores[1] >= 2 and valores[-1] >= 2
    assert proibidos(ev, {Tipo.ZOOM}) == []


# ---------- vídeos de gestos antigos: só falso positivo ----------

@pytest.mark.parametrize("video", ["v04", "v05", "v06", "v09", "v10", "v11", "v13"])
def test_videos_dos_gestos_antigos_nao_disparam_acoes_de_janela(video):
    ev = eventos_de(video)
    permitidos = {
        "v09": {Tipo.AREA_DE_TRABALHO},  # o tapa começa varrendo de lado
        "v06": {Tipo.SEGURAR_INICIO},    # sem o piparote, punho parado que depois anda é arrastar
    }.get(video, set())
    assert proibidos(ev, permitidos) == []


@pytest.mark.parametrize("video", [f"v{i:02d}" for i in range(1, 14)])
def test_nenhum_video_fecha_janela_nem_abre_alt_tab(video):
    c = contagem(eventos_de(video))
    assert c[Tipo.FECHAR_JANELA] == 0
    assert c[Tipo.ALT_TAB_INICIO] == 0


@pytest.mark.parametrize("video", [f"v{i:02d}" for i in range(1, 14)])
def test_botoes_e_teclas_sempre_sao_soltos(video):
    c = contagem(eventos_de(video))
    assert c[Tipo.SEGURAR_INICIO] == c[Tipo.SEGURAR_FIM]
    assert c[Tipo.ALT_TAB_INICIO] == c[Tipo.ALT_TAB_FIM]


@pytest.mark.parametrize("video", [f"v{i:02d}" for i in range(1, 14)])
def test_durante_o_arraste_nada_mais_acontece(video):
    arrastando = False
    for e in eventos_de(video):
        if e.tipo is Tipo.SEGURAR_INICIO:
            arrastando = True
        elif e.tipo is Tipo.SEGURAR_FIM:
            arrastando = False
        elif arrastando:
            assert e.tipo in (Tipo.ARRASTAR, Tipo.ALT_TAB_FIM), (video, e)


# ---------- gravações ao vivo do Arthur (2026-10-25) ----------
# feedback dele: clique bom, rolagem/fechar/troca de área perfeitos, cursor ótimo, Alt+Tab péssimo
# (a pose de três dedos piscava: 11 aberturas do seletor em 20 s)

def test_g_clique():
    # a sessão tem 13 toques no indicador (os 13 cliques do ao vivo) e 14 toques claros no médio
    # (polegar a 0,14–0,33 do médio e a 0,56–0,93 do indicador): o Arthur já testava o clique
    # direito ali, e ao vivo nenhum desses 14 tinha sido reconhecido
    ev = eventos_de("g_clique")
    c = contagem(ev)
    assert c["clique_esquerdo"] == 13 and c["clique_direito"] >= 12
    assert proibidos(ev, set()) == []


def test_g_alt_tab_abre_o_seletor_poucas_vezes_e_passa_janelas_nos_dois_sentidos():
    ev = eventos_de("g_alt_tab")
    c = contagem(ev)
    assert 2 <= c[Tipo.ALT_TAB_INICIO] <= 4 and c[Tipo.ALT_TAB_INICIO] == c[Tipo.ALT_TAB_FIM]
    assert c[Tipo.ALT_TAB_PROXIMO] >= 3 and c[Tipo.ALT_TAB_ANTERIOR] >= 3
    assert proibidos(ev, {Tipo.ALT_TAB_INICIO}) == []


def test_g_fechar_janela():
    ev = eventos_de("g_fechar_janela")
    assert contagem(ev)[Tipo.FECHAR_JANELA] == 3
    assert proibidos(ev, {Tipo.FECHAR_JANELA}) == []


def test_g_rolagem():
    ev = eventos_de("g_rolagem")
    assert contagem(ev)[Tipo.ROLAGEM] >= 100
    assert proibidos(ev, set()) == []


def test_g_cursor():
    ev = eventos_de("g_cursor")
    assert contagem(ev)[Tipo.APONTAR] >= 300
    assert proibidos(ev, set()) == []


def test_g_area_troca_nos_dois_sentidos_sem_vai_e_volta():
    ev = eventos_de("g_area")
    trocas = [e for e in ev if e.tipo is Tipo.AREA_DE_TRABALHO]
    assert len(trocas) >= 10 and {e.valor for e in trocas} == {-1, 1}
    assert all(b.t_ms - a.t_ms >= 500 for a, b in zip(trocas, trocas[1:]) if a.valor != b.valor)
    assert proibidos(ev, {Tipo.AREA_DE_TRABALHO, Tipo.VISAO_GERAL}) == []


# ---------- gravações de 2026-10-26 ----------
# clique direito: 37 vezes o polegar no médio, só 14 viraram clique ao vivo (38%), porque o
# detector só armava com a pose estável em indicador; o Arthur faz a partir de "dois dedos".

def test_g_clique_direito_reconhece_quase_todas_as_tentativas():
    ev = eventos_de("g_clique_direito")
    c = contagem(ev)
    assert c["clique_direito"] >= 33        # de 37 tentativas no médio
    assert c["clique_esquerdo"] <= 3        # 3 pinças claras no indicador; as 2 ambíguas não clicam
    assert abs(sum(e.y for e in ev if e.tipo is Tipo.ROLAGEM)) < 1
    assert proibidos(ev, set()) == []


@pytest.mark.parametrize("video", ["g_zoom_1", "g_zoom_2", "g_zoom_3"])
def test_g_zoom_faz_zoom_e_nada_mais_durante_e_logo_depois(video):
    ev = eventos_de(video)
    c = contagem(ev)
    assert c[Tipo.ZOOM_INICIO] >= 1 and c[Tipo.ZOOM_INICIO] == c[Tipo.ZOOM_FIM]
    assert Counter(e.valor for e in ev if e.tipo is Tipo.ZOOM)[1] >= 10
    em_zoom = False
    for e in ev:
        if e.tipo is Tipo.ZOOM_INICIO:
            em_zoom = True
        elif e.tipo is Tipo.ZOOM_FIM:
            em_zoom = False
        elif em_zoom:
            assert e.tipo is Tipo.ZOOM, (video, e)
    # expandir e segurar apareceram ao soltar uma das pinças entre rodadas de zoom
    assert proibidos(ev, {Tipo.ZOOM}) == []


def test_g_alt_tab_2_ficou_bom():
    ev = eventos_de("g_alt_tab_2")
    c = contagem(ev)
    assert c[Tipo.ALT_TAB_INICIO] >= 5 and c[Tipo.ALT_TAB_INICIO] == c[Tipo.ALT_TAB_FIM]
    assert proibidos(ev, {Tipo.ALT_TAB_INICIO}) == []
