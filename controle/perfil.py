"""Perfil por usuário: limiares calibrados, ajustes da interface, idioma e câmera, em um JSON.

O arquivo é editável à mão e tolerante: JSON quebrado, chave desconhecida ou valor de tipo errado são
descartados com um aviso, e valem os padrões. Nada do arquivo é executado.
"""
import dataclasses
import json
import math
import os
import pathlib
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field

from controle.gestos import Parametros
from controle.poses import Limites

NOME_DO_PROGRAMA = "controle-por-gestos"
IDIOMAS = ("pt", "en")


def pasta_de_configuracao(sistema: str, ambiente: Mapping[str, str] = os.environ,
                          home: pathlib.Path | None = None) -> pathlib.Path:
    home = home or pathlib.Path.home()
    if sistema == "windows":
        base = pathlib.Path(ambiente["APPDATA"]) if ambiente.get("APPDATA") else home / "AppData" / "Roaming"
    elif sistema == "macos":
        base = home / "Library" / "Application Support"
    else:
        base = pathlib.Path(ambiente["XDG_CONFIG_HOME"]) if ambiente.get("XDG_CONFIG_HOME") else home / ".config"
    return base / NOME_DO_PROGRAMA


def _validar(secao: str, dados: object, classe, avisos: list[str]) -> dict:
    """Mantém só os campos que existem em `classe` e têm o tipo (e o sinal) do padrão."""
    if not isinstance(dados, dict):
        avisos.append(f"perfil: '{secao}' deveria ser um objeto; ignorado")
        return {}
    padroes = {f.name: f.default for f in dataclasses.fields(classe)}
    validos = {}
    for nome, valor in dados.items():
        padrao = padroes.get(nome)
        if padrao is None:
            avisos.append(f"perfil: {secao}.{nome} não existe; ignorado")
        elif isinstance(valor, bool) or not isinstance(valor, int | float):
            avisos.append(f"perfil: {secao}.{nome} precisa ser número; ignorado")
        elif not math.isfinite(valor) or valor < 0:
            avisos.append(f"perfil: {secao}.{nome} fora do intervalo; ignorado")
        elif isinstance(padrao, int) and not isinstance(padrao, bool):
            if isinstance(valor, float):
                avisos.append(f"perfil: {secao}.{nome} precisa ser inteiro; ignorado")
            else:
                validos[nome] = valor
        else:
            validos[nome] = float(valor)
    return validos


@dataclass
class Perfil:
    limites: dict = field(default_factory=dict)       # sobrescritas de poses.Limites
    parametros: dict = field(default_factory=dict)    # sobrescritas de gestos.Parametros
    ajustes: dict = field(default_factory=dict)       # estado do menu (velocidade, rolagem, ...)
    idioma: str = "pt"
    camera: int = 0
    avisos: list[str] = field(default_factory=list, compare=False)

    def limites_efetivos(self) -> Limites:
        return dataclasses.replace(Limites(), **self.limites)

    def parametros_efetivos(self) -> Parametros:
        return dataclasses.replace(Parametros(), **self.parametros)

    @classmethod
    def carregar(cls, caminho: pathlib.Path) -> "Perfil":
        caminho = pathlib.Path(caminho)
        if not caminho.exists():
            return cls()
        try:
            bruto = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            return cls(avisos=[f"perfil: não consegui ler {caminho} ({erro}); usando os padrões"])
        if not isinstance(bruto, dict):
            return cls(avisos=[f"perfil: {caminho} não é um objeto JSON; usando os padrões"])
        avisos: list[str] = []
        idioma = bruto.get("idioma", "pt")
        if idioma not in IDIOMAS:
            avisos.append(f"perfil: idioma '{idioma}' desconhecido; usando pt")
            idioma = "pt"
        camera = bruto.get("camera", 0)
        if isinstance(camera, bool) or not isinstance(camera, int) or camera < 0:
            avisos.append("perfil: camera precisa ser um inteiro ≥ 0; usando 0")
            camera = 0
        ajustes = bruto.get("ajustes", {})
        if not isinstance(ajustes, dict):
            avisos.append("perfil: 'ajustes' deveria ser um objeto; ignorado")
            ajustes = {}
        return cls(limites=_validar("limites", bruto.get("limites", {}), Limites, avisos),
                   parametros=_validar("parametros", bruto.get("parametros", {}), Parametros, avisos),
                   ajustes=ajustes, idioma=idioma, camera=camera, avisos=avisos)

    def salvar(self, caminho: pathlib.Path):
        """Grava em arquivo temporário e troca: um desligamento no meio não deixa JSON pela metade."""
        caminho = pathlib.Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        conteudo = {"limites": self.limites, "parametros": self.parametros, "ajustes": self.ajustes,
                    "idioma": self.idioma, "camera": self.camera}
        descritor, temporario = tempfile.mkstemp(dir=caminho.parent, suffix=".tmp")
        try:
            with os.fdopen(descritor, "w", encoding="utf-8") as f:
                json.dump(conteudo, f, ensure_ascii=False, indent=2)
            os.replace(temporario, caminho)
        except BaseException:
            pathlib.Path(temporario).unlink(missing_ok=True)
            raise
