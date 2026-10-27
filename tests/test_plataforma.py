import pytest

from controle.plataforma import Ambiente, criar_saida, detectar
from controle.plataforma.base import Acao, AcoesNulas, Botao, EntradaNula, Tecla


# ---------- detecção do ambiente ----------

def test_detecta_kde_no_wayland():
    a = detectar("linux", {"XDG_CURRENT_DESKTOP": "KDE", "XDG_SESSION_TYPE": "wayland"})
    assert a == Ambiente("linux", "kde", "wayland")


def test_detecta_gnome_do_ubuntu_no_x11():
    a = detectar("linux", {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME", "XDG_SESSION_TYPE": "x11"})
    assert a == Ambiente("linux", "gnome", "x11")


def test_area_de_trabalho_desconhecida_fica_com_o_proprio_nome():
    a = detectar("linux", {"XDG_CURRENT_DESKTOP": "X-Cinnamon"})
    assert a == Ambiente("linux", "x-cinnamon", None)


@pytest.mark.parametrize("plataforma,sistema", [("win32", "windows"), ("darwin", "macos"),
                                                 ("linux", "linux"), ("freebsd14", "outro")])
def test_detecta_o_sistema(plataforma, sistema):
    assert detectar(plataforma, {}).sistema == sistema


# ---------- montagem da saída ----------

class EntradaFalsaLinux:
    def fechar(self):
        pass


def test_demonstracao_nunca_age_no_sistema():
    s = criar_saida(Ambiente("linux", "kde", "wayland"), demonstracao=True)
    assert isinstance(s.entrada, EntradaNula) and isinstance(s.acoes, AcoesNulas)
    assert s.demonstracao


def test_kde_usa_uinput_e_kwin():
    from controle.plataforma.linux import AcoesKWin
    s = criar_saida(Ambiente("linux", "kde", "wayland"), demonstracao=False,
                    entrada_linux=EntradaFalsaLinux)
    assert isinstance(s.entrada, EntradaFalsaLinux) and isinstance(s.acoes, AcoesKWin)
    assert s.aviso is None and not s.demonstracao


def test_sem_acesso_ao_uinput_cai_para_demonstracao_com_aviso():
    def sem_permissao():
        raise PermissionError("/dev/uinput")
    s = criar_saida(Ambiente("linux", "kde", "wayland"), demonstracao=False, entrada_linux=sem_permissao)
    assert isinstance(s.entrada, EntradaNula) and s.demonstracao and "uinput" in s.aviso


def test_linux_fora_do_kde_move_o_mouse_mas_avisa_que_janelas_ainda_nao():
    s = criar_saida(Ambiente("linux", "gnome", "wayland"), demonstracao=False,
                    entrada_linux=EntradaFalsaLinux)
    assert isinstance(s.entrada, EntradaFalsaLinux) and isinstance(s.acoes, AcoesNulas)
    assert "gnome" in s.aviso.lower()


@pytest.mark.parametrize("sistema", ["windows", "macos", "outro"])
def test_sistemas_ainda_sem_suporte_abrem_em_demonstracao_com_aviso(sistema):
    s = criar_saida(Ambiente(sistema, None, None), demonstracao=False)
    assert s.demonstracao and isinstance(s.entrada, EntradaNula) and s.aviso


# ---------- Linux: tradução do vocabulário neutro ----------

def test_kwin_chama_cada_acao_pelo_nome_do_atalho():
    from controle.plataforma.linux import comando_kwin
    nomes = {acao: comando_kwin(acao)[-1] for acao in Acao}
    assert nomes == {
        Acao.MAXIMIZAR: "Window Maximize", Acao.VISAO_GERAL: "Overview",
        Acao.AREA_ESQUERDA: "Switch One Desktop to the Left",
        Acao.AREA_DIREITA: "Switch One Desktop to the Right", Acao.FECHAR_JANELA: "Window Close",
    }
    assert comando_kwin(Acao.MAXIMIZAR)[:3] == ["busctl", "--user", "call"]


def test_uinput_traduz_botoes_e_teclas_para_codigos_do_kernel():
    from evdev import ecodes
    from controle.plataforma.linux import CODIGO_BOTAO, CODIGO_TECLA
    assert CODIGO_BOTAO == {Botao.ESQUERDO: ecodes.BTN_LEFT, Botao.DIREITO: ecodes.BTN_RIGHT}
    assert CODIGO_TECLA == {Tecla.ALT: ecodes.KEY_LEFTALT, Tecla.TAB: ecodes.KEY_TAB,
                            Tecla.CTRL: ecodes.KEY_LEFTCTRL, Tecla.SHIFT: ecodes.KEY_LEFTSHIFT}


def test_nucleo_nao_importa_evdev():
    # Windows e macOS não têm evdev: o núcleo não pode depender dele
    import subprocess
    import sys
    codigo = ("import sys; sys.modules['evdev'] = None\n"
              "import controle.saida, controle.reconhecedor, controle.plataforma\n"
              "print('ok')")
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert r.stdout.strip() == "ok", r.stderr
