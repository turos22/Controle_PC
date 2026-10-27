import ast
import pathlib

import pytest

from controle import idioma
from controle.interface import POSE_TEXTO
from controle.legenda import GESTOS
from controle.poses import Pose

RAIZ = pathlib.Path(idioma.__file__).parent


@pytest.fixture(autouse=True)
def volta_ao_portugues():
    yield
    idioma.definir_idioma("pt")


def test_portugues_e_o_padrao_e_devolve_o_proprio_texto():
    assert idioma.tr("Mover o cursor") == "Mover o cursor"


def test_ingles_traduz_e_texto_desconhecido_fica_como_veio():
    idioma.definir_idioma("en")
    assert idioma.tr("Mover o cursor") == "Move the cursor"
    assert idioma.tr("texto que ninguém cadastrou") == "texto que ninguém cadastrou"


def test_idioma_invalido_e_ignorado():
    idioma.definir_idioma("en")
    idioma.definir_idioma("klingon")
    assert idioma.idioma_atual() == "en"


def test_tr_formata_com_argumentos():
    idioma.definir_idioma("en")
    assert idioma.tr("Salvo: {nome} ({quadros} quadros)", nome="a.npz", quadros=3) == "Saved: a.npz (3 frames)"


def _textos_traduzidos() -> set[str]:
    """Todo literal passado a tr(...) (ou a _secao, que traduz o título) no código."""
    achados = set()
    for arquivo in RAIZ.rglob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if (isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in ("tr", "_secao")
                    and no.args and isinstance(no.args[0], ast.Constant) and isinstance(no.args[0].value, str)):
                achados.add(no.args[0].value)
    return achados


def test_todo_texto_marcado_com_tr_tem_traducao():
    faltam = sorted(t for t in _textos_traduzidos() if t not in idioma.EN)
    assert faltam == []


def test_tabela_em_ingles_nao_tem_entrada_sobrando():
    # entradas fora do código e fora do catálogo de gestos/poses são lixo que acumula
    usadas = _textos_traduzidos() | {t for g in GESTOS for t in (g.nome, g.como, g.acao)} \
        | {p.value for p in Pose} | set(POSE_TEXTO.values()) | idioma.TEXTOS_DINAMICOS
    sobram = sorted(t for t in idioma.EN if t not in usadas)
    assert sobram == []


def test_catalogo_de_gestos_e_poses_esta_traduzido():
    textos = [t for g in GESTOS for t in (g.nome, g.como, g.acao)] + [p.value for p in Pose] + list(POSE_TEXTO.values())
    assert [t for t in textos if t not in idioma.EN and t not in idioma.IGUAIS] == []
