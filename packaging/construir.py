"""Gera o pacote para distribuição do sistema atual: .zip (Windows), .dmg (macOS) ou .tar.gz (Linux).

Uso: python packaging/construir.py [--saida pasta]   (precisa do extra `empacotar`: pip install ".[empacotar]")
O executável é montado com o PyInstaller e leva o modelo do MediaPipe dentro.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
NOME = "controle-por-gestos"


def argumentos_pyinstaller(sistema: str, saida: pathlib.Path, raiz: pathlib.Path = RAIZ) -> list[str]:
    modelo = raiz / "controle" / "dados" / "hand_landmarker.task"
    return [
        "--noconfirm", "--name", NOME, "--windowed",
        "--collect-all", "mediapipe",
        "--add-data", f"{modelo}{os.pathsep}controle/dados",  # ';' no Windows, ':' nos demais
        "--distpath", str(saida / "dist"), "--workpath", str(saida / "work"), "--specpath", str(saida),
        str(raiz / "main.py"),
    ]


def empacotar(sistema: str, saida: pathlib.Path) -> pathlib.Path:
    dist = saida / "dist"
    if sistema == "windows":
        return pathlib.Path(shutil.make_archive(str(saida / f"{NOME}-windows"), "zip", dist, NOME))
    if sistema == "macos":
        destino = saida / f"{NOME}-macos.dmg"
        subprocess.run(["hdiutil", "create", "-volname", NOME, "-srcfolder", str(dist / f"{NOME}.app"),
                        "-ov", "-format", "UDZO", str(destino)], check=True)
        return destino
    destino = saida / f"{NOME}-linux.tar.gz"
    with tarfile.open(destino, "w:gz") as pacote:
        pacote.add(dist / NOME, arcname=NOME)
    return destino


def main() -> int:
    from controle.plataforma import detectar

    analise = argparse.ArgumentParser()
    analise.add_argument("--saida", type=pathlib.Path, default=RAIZ / "build" / "pacote")
    args = analise.parse_args()
    sistema = detectar().sistema
    shutil.rmtree(args.saida, ignore_errors=True)
    args.saida.mkdir(parents=True)
    import PyInstaller.__main__ as pyinstaller

    pyinstaller.run(argumentos_pyinstaller(sistema, args.saida))
    pacote = empacotar(sistema, args.saida)
    print(f"Pacote: {pacote} ({pacote.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    raise SystemExit(main())
