import pytest

from controle.cursor import Cursor, Retangulo
from controle.eventos import Evento, Tipo
from controle.plataforma import Ambiente, criar_saida
from controle.plataforma.atalhos import (ATALHOS_GNOME, ATALHOS_MACOS, ATALHOS_WINDOWS, AcoesPorAtalho,
                                         MODIFICADORES_PADRAO)
from controle.plataforma.base import Acao, Tecla
from controle.saida import Executor


class TecladoFalso:
    def __init__(self):
        self.chamadas = []

    def tecla(self, tecla, pressionada):
        self.chamadas.append((tecla, pressionada))

    def fechar(self):
        pass


def test_atalho_aperta_na_ordem_e_solta_na_ordem_inversa():
    t = TecladoFalso()
    AcoesPorAtalho(t, {Acao.FECHAR_JANELA: (Tecla.ALT, Tecla.F4)}).executar(Acao.FECHAR_JANELA)
    assert t.chamadas == [(Tecla.ALT, True), (Tecla.F4, True), (Tecla.F4, False), (Tecla.ALT, False)]


def test_acao_sem_atalho_na_tabela_nao_faz_nada():
    t = TecladoFalso()
    AcoesPorAtalho(t, {}).executar(Acao.MAXIMIZAR)
    assert t.chamadas == []


@pytest.mark.parametrize("tabela", [ATALHOS_GNOME, ATALHOS_WINDOWS, ATALHOS_MACOS])
def test_cada_sistema_cobre_todas_as_acoes(tabela):
    assert set(tabela) == set(Acao)
    assert all(len(combinacao) >= 1 for combinacao in tabela.values())


def test_atalhos_do_windows():
    assert ATALHOS_WINDOWS == {
        Acao.MAXIMIZAR: (Tecla.META, Tecla.CIMA),
        Acao.VISAO_GERAL: (Tecla.META, Tecla.TAB),
        Acao.AREA_ESQUERDA: (Tecla.CTRL, Tecla.META, Tecla.ESQUERDA),
        Acao.AREA_DIREITA: (Tecla.CTRL, Tecla.META, Tecla.DIREITA),
        Acao.FECHAR_JANELA: (Tecla.ALT, Tecla.F4),
    }


def test_atalhos_do_gnome():
    assert ATALHOS_GNOME[Acao.VISAO_GERAL] == (Tecla.META,)
    assert ATALHOS_GNOME[Acao.MAXIMIZAR] == (Tecla.META, Tecla.CIMA)
    assert ATALHOS_GNOME[Acao.AREA_ESQUERDA] == (Tecla.META, Tecla.PAGE_UP)
    assert ATALHOS_GNOME[Acao.AREA_DIREITA] == (Tecla.META, Tecla.PAGE_DOWN)
    assert ATALHOS_GNOME[Acao.FECHAR_JANELA] == (Tecla.ALT, Tecla.F4)


def test_atalhos_do_macos_usam_comando_e_controle():
    assert ATALHOS_MACOS[Acao.FECHAR_JANELA] == (Tecla.META, Tecla.W)
    assert ATALHOS_MACOS[Acao.VISAO_GERAL] == (Tecla.CTRL, Tecla.CIMA)
    assert ATALHOS_MACOS[Acao.AREA_ESQUERDA] == (Tecla.CTRL, Tecla.ESQUERDA)
    assert ATALHOS_MACOS[Acao.AREA_DIREITA] == (Tecla.CTRL, Tecla.DIREITA)


# ---------- montagem da saída ----------

class EntradaFalsa(TecladoFalso):
    pass


def test_gnome_age_por_atalhos_de_teclado():
    s = criar_saida(Ambiente("linux", "gnome", "wayland"), fabrica_entrada=EntradaFalsa)
    assert isinstance(s.acoes, AcoesPorAtalho) and s.aviso is None and not s.demonstracao


def test_linux_sem_area_de_trabalho_conhecida_mantem_o_aviso():
    s = criar_saida(Ambiente("linux", "xfce", "x11"), fabrica_entrada=EntradaFalsa)
    assert "xfce" in s.aviso.lower() and not isinstance(s.acoes, AcoesPorAtalho)


def test_windows_usa_a_entrada_do_windows_com_atalhos_do_windows():
    s = criar_saida(Ambiente("windows", None, None), fabrica_entrada=EntradaFalsa)
    assert isinstance(s.acoes, AcoesPorAtalho) and not s.demonstracao and s.aviso is None


def test_macos_avisa_quando_falta_permissao_de_acessibilidade():
    s = criar_saida(Ambiente("macos", None, None), fabrica_entrada=EntradaFalsa,
                    acessibilidade_liberada=lambda: False)
    assert "acessibilidade" in s.aviso.lower()


def test_macos_com_permissao_nao_avisa():
    s = criar_saida(Ambiente("macos", None, None), fabrica_entrada=EntradaFalsa,
                    acessibilidade_liberada=lambda: True)
    assert s.aviso is None and not s.demonstracao


def test_falha_ao_criar_a_entrada_cai_para_demonstracao_com_aviso():
    def quebra():
        raise OSError("sem acesso")
    s = criar_saida(Ambiente("windows", None, None), fabrica_entrada=quebra)
    assert s.demonstracao and "sem acesso" in s.aviso


def test_sistema_desconhecido_continua_em_demonstracao():
    assert criar_saida(Ambiente("outro", None, None)).demonstracao


# ---------- modificadores por sistema ----------

class SaidaCmd(TecladoFalso):
    modificador_troca = Tecla.META
    modificador_zoom = Tecla.META

    def mover_absoluto(self, u, v): pass
    def botao(self, b, p): pass
    def rolar(self, *a): self.chamadas.append(("rolar", a))
    def executar(self, a): pass


def executor_com(entrada):
    return Executor(entrada, entrada, Cursor([Retangulo(0, 0, 1920, 1080)]))


def test_executor_usa_o_modificador_da_troca_de_janela_do_sistema():
    s = SaidaCmd()
    executor_com(s).executar([Evento(Tipo.ALT_TAB_INICIO, 0, 1), Evento(Tipo.ALT_TAB_FIM, 100, 1)])
    assert s.chamadas == [(Tecla.META, True), (Tecla.TAB, True), (Tecla.TAB, False), (Tecla.META, False)]


def test_executor_usa_o_modificador_de_zoom_do_sistema():
    s = SaidaCmd()
    executor_com(s).executar([Evento(Tipo.ZOOM_INICIO, 0, 1), Evento(Tipo.ZOOM_FIM, 100, 1)])
    assert s.chamadas == [(Tecla.META, True), (Tecla.META, False)]


def test_sem_declarar_modificadores_vale_alt_e_ctrl():
    assert MODIFICADORES_PADRAO == (Tecla.ALT, Tecla.CTRL)
