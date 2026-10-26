import functools
import pathlib

import numpy as np
import pytest

from controle.maos import Mao, Quadro

PASTA_FIXTURES = pathlib.Path(__file__).parent / "fixtures"
ROTULOS = {0: "Left", 1: "Right"}


@functools.cache
def carregar_gravacao(nome: str, pasta: pathlib.Path = PASTA_FIXTURES) -> tuple[Quadro, ...]:
    """Lê a fixture `nome` (ex.: "v01") como a sequência de quadros que o pipeline ao vivo produz."""
    d = np.load(pasta / f"{nome}.npz")
    quadros = []
    for i, t in enumerate(d["t_ms"]):
        maos = tuple(
            Mao(img=d["img"][i, m], mundo=d["mundo"][i, m], rotulo=ROTULOS[int(d["rotulo"][i, m])],
                confianca=float(d["confianca"][i, m]))
            for m in range(d["rotulo"].shape[1]) if d["rotulo"][i, m] >= 0
        )
        quadros.append(Quadro(t_ms=int(t), maos=maos))
    return tuple(quadros)


def mao_em(nome: str, segundos: float, rotulo: str | None = None) -> Mao:
    """Mão do quadro mais próximo de `segundos` (a primeira, ou a de `rotulo`)."""
    quadros = carregar_gravacao(nome)
    inicio = quadros[0].t_ms  # gravações ao vivo não começam em 0
    quadro = min(quadros, key=lambda q: abs(q.t_ms - inicio - segundos * 1000))
    maos = [m for m in quadro.maos if rotulo is None or m.rotulo == rotulo]
    assert maos, f"sem mão em {nome} {segundos}s"
    return maos[0]


@pytest.fixture
def gravacao():
    return carregar_gravacao
