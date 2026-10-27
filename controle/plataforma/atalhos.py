"""Ações de janela por atalhos de teclado: Windows, macOS e áreas de trabalho Linux sem API própria.

Cada tabela traduz o vocabulário neutro (`Acao`) para a combinação padrão do sistema. Quem mudou os
atalhos do sistema precisa ajustar a tabela.
"""
from collections.abc import Mapping

from controle.plataforma.base import Acao, Entrada, Tecla

MODIFICADORES_PADRAO = (Tecla.ALT, Tecla.CTRL)  # (troca de janela, zoom)

ATALHOS_GNOME = {
    Acao.MAXIMIZAR: (Tecla.META, Tecla.CIMA),
    Acao.VISAO_GERAL: (Tecla.META,),
    Acao.AREA_ESQUERDA: (Tecla.META, Tecla.PAGE_UP),
    Acao.AREA_DIREITA: (Tecla.META, Tecla.PAGE_DOWN),
    Acao.FECHAR_JANELA: (Tecla.ALT, Tecla.F4),
}

ATALHOS_WINDOWS = {
    Acao.MAXIMIZAR: (Tecla.META, Tecla.CIMA),
    Acao.VISAO_GERAL: (Tecla.META, Tecla.TAB),
    Acao.AREA_ESQUERDA: (Tecla.CTRL, Tecla.META, Tecla.ESQUERDA),
    Acao.AREA_DIREITA: (Tecla.CTRL, Tecla.META, Tecla.DIREITA),
    Acao.FECHAR_JANELA: (Tecla.ALT, Tecla.F4),
}

# macOS não tem atalho de "maximizar": Ctrl+Comando+F põe a janela em tela cheia, o equivalente mais próximo
ATALHOS_MACOS = {
    Acao.MAXIMIZAR: (Tecla.CTRL, Tecla.META, Tecla.F),
    Acao.VISAO_GERAL: (Tecla.CTRL, Tecla.CIMA),
    Acao.AREA_ESQUERDA: (Tecla.CTRL, Tecla.ESQUERDA),
    Acao.AREA_DIREITA: (Tecla.CTRL, Tecla.DIREITA),
    Acao.FECHAR_JANELA: (Tecla.META, Tecla.W),
}


class AcoesPorAtalho:
    """Aperta a combinação na ordem e solta na ordem inversa, pelo teclado virtual da entrada."""

    def __init__(self, entrada: Entrada, atalhos: Mapping[Acao, tuple[Tecla, ...]]):
        self._entrada, self._atalhos = entrada, atalhos

    def executar(self, acao: Acao):
        combinacao = self._atalhos.get(acao, ())
        for tecla in combinacao:
            self._entrada.tecla(tecla, True)
        for tecla in reversed(combinacao):
            self._entrada.tecla(tecla, False)
