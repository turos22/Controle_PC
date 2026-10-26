"""Grava sessões ao vivo (landmarks + eventos) no mesmo formato das fixtures de teste.

Nenhuma imagem é salva: só os 21 pontos de cada mão por quadro.
"""
import datetime
import pathlib
import threading

import numpy as np

from controle.eventos import Evento
from controle.maos import Mao

MAOS = 2
ROTULOS = {"Left": 0, "Right": 1}


class Gravador:
    def __init__(self, pasta: pathlib.Path, gesto: str):
        self.pasta, self.gesto = pathlib.Path(pasta), gesto
        self._t, self._img, self._mundo, self._rotulo, self._conf = [], [], [], [], []
        self._eventos: list[Evento] = []
        self._trava = threading.Lock()  # o pipeline adiciona numa thread; a interface salva em outra
        self._fechado = False

    def adicionar(self, t_ms: int, maos: list[Mao], eventos: list[Evento]):
        img = np.full((MAOS, 21, 3), np.nan, np.float32)
        mundo = np.full((MAOS, 21, 3), np.nan, np.float32)
        rotulo = np.full(MAOS, -1, np.int8)
        conf = np.zeros(MAOS, np.float32)
        for i, mao in enumerate(maos[:MAOS]):
            img[i], mundo[i] = mao.img, mao.mundo
            rotulo[i], conf[i] = ROTULOS.get(mao.rotulo, 0), mao.confianca
        with self._trava:
            if self._fechado:
                return
            self._t.append(t_ms)
            self._img.append(img)
            self._mundo.append(mundo)
            self._rotulo.append(rotulo)
            self._conf.append(conf)
            self._eventos += eventos

    @property
    def quadros(self) -> int:
        return len(self._t)

    def salvar(self) -> pathlib.Path | None:
        with self._trava:
            self._fechado = True
        if not self._t:
            return None
        self.pasta.mkdir(parents=True, exist_ok=True)
        carimbo = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        caminho = self.pasta / f"{carimbo}_{self.gesto}.npz"
        np.savez_compressed(
            caminho,
            t_ms=np.array(self._t, np.int32), img=np.stack(self._img), mundo=np.stack(self._mundo),
            rotulo=np.stack(self._rotulo), confianca=np.stack(self._conf), gesto=np.array(self.gesto),
            eventos_tipo=np.array([e.tipo.value for e in self._eventos]),
            eventos_t_ms=np.array([e.t_ms for e in self._eventos], np.int32),
            eventos_valor=np.array([e.valor for e in self._eventos], np.int32),
        )
        return caminho
