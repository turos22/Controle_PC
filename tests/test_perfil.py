import json
import math
import pathlib

from controle.gestos import Parametros
from controle.perfil import Perfil, pasta_de_configuracao
from controle.poses import LIMITES_PADRAO, Limites, Pose, classificar


# ---------- limites de pose ----------

def test_limites_padrao_sao_os_valores_calibrados():
    assert (LIMITES_PADRAO.esticado, LIMITES_PADRAO.dobrado) == (0.86, 0.65)
    assert LIMITES_PADRAO.minimo_tres_dedos == 0.82 and LIMITES_PADRAO.l_angulo_min == 45.0


def test_classificar_respeita_os_limites_recebidos():
    from controle.geometria import medir
    from tests.conftest import carregar_gravacao
    medidas = [medir(m, 16 / 9) for q in carregar_gravacao("g_cursor") for m in q.maos]
    indicador = next(m for m in medidas if classificar(m) is Pose.INDICADOR)
    assert classificar(indicador, LIMITES_PADRAO) is Pose.INDICADOR
    assert classificar(indicador, Limites(esticado=1.01)) is not Pose.INDICADOR  # ninguém estica tanto


# ---------- perfil ----------

def test_perfil_vazio_devolve_os_padroes():
    p = Perfil()
    assert p.limites_efetivos() == LIMITES_PADRAO and p.parametros_efetivos() == Parametros()


def test_sobrescritas_valem_so_para_os_campos_informados():
    p = Perfil(limites={"esticado": 0.9}, parametros={"clique_max_ms": 400})
    assert p.limites_efetivos().esticado == 0.9 and p.limites_efetivos().dobrado == LIMITES_PADRAO.dobrado
    assert p.parametros_efetivos().clique_max_ms == 400 and p.parametros_efetivos().pinca_fecha == Parametros().pinca_fecha


def test_salvar_e_carregar_devolve_o_mesmo_perfil(tmp_path):
    caminho = tmp_path / "pasta" / "perfil.json"
    original = Perfil(limites={"esticado": 0.9}, parametros={"clique_max_ms": 400},
                      ajustes={"velocidade": 150, "inverter_rolagem": True}, idioma="en", camera=1)
    original.salvar(caminho)
    carregado = Perfil.carregar(caminho)
    assert carregado == original and carregado.avisos == []


def test_arquivo_inexistente_vira_perfil_padrao_sem_aviso(tmp_path):
    p = Perfil.carregar(tmp_path / "nao_existe.json")
    assert p == Perfil() and p.avisos == []


def test_arquivo_corrompido_vira_padrao_com_aviso(tmp_path):
    caminho = tmp_path / "perfil.json"
    caminho.write_text("{ isso não é json")
    p = Perfil.carregar(caminho)
    assert p == Perfil() and any("perfil" in a.lower() for a in p.avisos)


def test_valores_invalidos_sao_descartados_com_aviso(tmp_path):
    caminho = tmp_path / "perfil.json"
    caminho.write_text(json.dumps({
        "limites": {"esticado": "alto", "dobrado": 0.5, "inexistente": 1, "pinca_max": float("nan")},
        "parametros": {"clique_max_ms": 12.5, "pinca_fecha": -1},
        "idioma": "klingon", "camera": -3,
    }))
    p = Perfil.carregar(caminho)
    assert p.limites == {"dobrado": 0.5}                 # só o válido sobra
    assert p.parametros == {}                            # int não aceita fração; negativo não vale
    assert p.idioma is None and p.camera == 0
    assert len(p.avisos) >= 5


def test_inteiro_vale_como_decimal_mas_decimal_nao_vale_como_inteiro(tmp_path):
    caminho = tmp_path / "perfil.json"
    caminho.write_text(json.dumps({"limites": {"esticado": 1}, "parametros": {"clique_max_ms": 300}}))
    p = Perfil.carregar(caminho)
    assert p.limites["esticado"] == 1.0 and p.parametros["clique_max_ms"] == 300


def test_json_que_nao_e_objeto_vira_padrao(tmp_path):
    caminho = tmp_path / "perfil.json"
    caminho.write_text("[1, 2]")
    assert Perfil.carregar(caminho) == Perfil()


def test_salvar_nao_deixa_arquivo_pela_metade(tmp_path):
    caminho = tmp_path / "perfil.json"
    Perfil(camera=2).salvar(caminho)
    assert [p.name for p in tmp_path.iterdir()] == ["perfil.json"]
    assert json.loads(caminho.read_text())["camera"] == 2


# ---------- onde fica o arquivo ----------

def test_pasta_no_linux_segue_o_xdg():
    home = pathlib.Path("/home/ana")
    assert pasta_de_configuracao("linux", {"XDG_CONFIG_HOME": "/cfg"}, home) == pathlib.Path("/cfg/controle-por-gestos")
    assert pasta_de_configuracao("linux", {}, home) == home / ".config" / "controle-por-gestos"


def test_pasta_no_windows_usa_appdata():
    home = pathlib.Path("C:/Users/ana")
    assert pasta_de_configuracao("windows", {"APPDATA": "C:/Users/ana/AppData/Roaming"}, home) == \
        pathlib.Path("C:/Users/ana/AppData/Roaming/controle-por-gestos")
    assert pasta_de_configuracao("windows", {}, home) == home / "AppData" / "Roaming" / "controle-por-gestos"


def test_pasta_no_macos_usa_application_support():
    home = pathlib.Path("/Users/ana")
    assert pasta_de_configuracao("macos", {}, home) == home / "Library" / "Application Support" / "controle-por-gestos"


def test_sem_idioma_no_perfil_fica_para_o_idioma_do_sistema():
    assert Perfil().idioma is None


def test_calibrado_e_lembrado_e_valida_tipo(tmp_path):
    caminho = tmp_path / "perfil.json"
    Perfil(calibrado=True).salvar(caminho)
    assert Perfil.carregar(caminho).calibrado is True
    caminho.write_text(json.dumps({"calibrado": "sim"}))
    p = Perfil.carregar(caminho)
    assert p.calibrado is False and p.avisos
