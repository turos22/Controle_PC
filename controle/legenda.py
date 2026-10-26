"""Catálogo dos gestos: o que a interface mostra e o que pode ser ligado ou desligado."""
from dataclasses import dataclass

from controle.eventos import Evento, Tipo


@dataclass(frozen=True, slots=True)
class Gesto:
    id: str
    nome: str
    como: str
    acao: str


GESTOS = (
    Gesto("cursor", "Mover o cursor", "Só o indicador esticado. Devagar = preciso, rápido = longe. "
          "Para reposicionar a mão, saia da pose, mude de lugar e aponte de novo.", "Move o ponteiro"),
    Gesto("clique", "Clique e duplo clique", "Apontando, encoste e solte rápido o polegar no indicador. "
          "Duas vezes seguidas faz o duplo clique.", "Clique esquerdo"),
    Gesto("clique_direito", "Clique direito", "Apontando, encoste e solte rápido o polegar no dedo médio.",
          "Clique direito"),
    Gesto("segurar", "Segurar e arrastar", "Feche a pinça, fique parado um instante e mova. Abra a mão "
          "para soltar. Enquanto arrasta, nenhum outro gesto age.", "Botão esquerdo pressionado"),
    Gesto("rolagem", "Rolar", "Indicador e médio esticados: onde formou a pose é o centro. Afaste a mão "
          "para rolar (mais longe, mais rápido); volte ao centro para parar.", "Roda do mouse"),
    Gesto("expandir", "Expandir janela", "Mão fechada, depois abra em L com o polegar bem aberto e "
          "segure ~0,3 s.", "Maximiza a janela"),
    Gesto("visao_geral", "Visão geral", "Mão aberta, feche em garra e abra de novo, rápido.",
          "Visão geral do KDE"),
    Gesto("area_de_trabalho", "Trocar de área", "Mão aberta varrendo rápido para o lado. Pare a mão "
          "antes de varrer de novo (o retorno não conta).", "Área à esquerda / à direita"),
    Gesto("alt_tab", "Alternar janelas", "Três dedos esticados (indicador, médio, anelar) abrem o "
          "seletor. Deslize para os lados para passar; mude a pose para escolher.", "Alt+Tab"),
    Gesto("fechar_janela", "Fechar janela", "Polegar para baixo, segurado ~0,8 s (o anel na tela "
          "completa). Mudar a pose antes cancela.", "Fecha a janela (Alt+F4)"),
    Gesto("zoom", "Zoom", "As duas mãos em pinça ao mesmo tempo. Afaste para aproximar, junte para "
          "afastar.", "Ctrl + roda"),
)

_POR_TIPO = {
    Tipo.APONTAR: "cursor",
    Tipo.SEGURAR_INICIO: "segurar", Tipo.ARRASTAR: "segurar", Tipo.SEGURAR_FIM: "segurar",
    Tipo.ROLAGEM: "rolagem",
    Tipo.EXPANDIR: "expandir",
    Tipo.VISAO_GERAL: "visao_geral",
    Tipo.AREA_DE_TRABALHO: "area_de_trabalho",
    Tipo.ALT_TAB_INICIO: "alt_tab", Tipo.ALT_TAB_PROXIMO: "alt_tab", Tipo.ALT_TAB_ANTERIOR: "alt_tab",
    Tipo.ALT_TAB_FIM: "alt_tab",
    Tipo.FECHAR_JANELA: "fechar_janela",
    Tipo.ZOOM: "zoom", Tipo.ZOOM_INICIO: "zoom", Tipo.ZOOM_FIM: "zoom",
}


def gesto_do_evento(e: Evento) -> str | None:
    if e.tipo is Tipo.CLIQUE:
        return "clique_direito" if e.valor == 3 else "clique"
    return _POR_TIPO.get(e.tipo)
