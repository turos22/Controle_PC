import importlib.util
import os
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def carregar():
    especificacao = importlib.util.spec_from_file_location("construir", RAIZ / "packaging" / "construir.py")
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_o_modelo_vai_dentro_do_pacote_com_o_separador_do_sistema():
    args = carregar().argumentos_pyinstaller("linux", pathlib.Path("/tmp/saida"))
    dado = args[args.index("--add-data") + 1]
    origem, destino = dado.rsplit(os.pathsep, 1)
    assert pathlib.Path(origem).name == "hand_landmarker.task" and pathlib.Path(origem).exists()
    assert destino == "controle/dados"


def test_nada_e_escrito_fora_da_pasta_de_saida():
    saida = pathlib.Path("/tmp/saida")
    args = carregar().argumentos_pyinstaller("linux", saida)
    for opcao in ("--distpath", "--workpath", "--specpath"):
        assert pathlib.Path(args[args.index(opcao) + 1]).is_relative_to(saida) or args[args.index(opcao) + 1] == str(saida)


def test_empacota_linux_em_tar_gz(tmp_path):
    import tarfile
    (tmp_path / "dist" / "controle-por-gestos").mkdir(parents=True)
    (tmp_path / "dist" / "controle-por-gestos" / "controle-por-gestos").write_text("x")
    destino = carregar().empacotar("linux", tmp_path)
    assert destino.name == "controle-por-gestos-linux.tar.gz"
    with tarfile.open(destino) as t:
        assert "controle-por-gestos/controle-por-gestos" in t.getnames()


def test_empacota_windows_em_zip(tmp_path):
    import zipfile
    (tmp_path / "dist" / "controle-por-gestos").mkdir(parents=True)
    (tmp_path / "dist" / "controle-por-gestos" / "controle-por-gestos.exe").write_text("x")
    destino = carregar().empacotar("windows", tmp_path)
    assert destino.suffix == ".zip" and "controle-por-gestos/controle-por-gestos.exe" in zipfile.ZipFile(destino).namelist()
