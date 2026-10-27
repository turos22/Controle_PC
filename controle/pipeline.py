"""Laço principal: câmera → MediaPipe → gestos → ações, com métricas de cada etapa."""
import pathlib
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from controle.gestos import Parametros
from controle.imagem import aplicar_zoom
from controle.maos import Mao, Quadro
from controle.poses import LIMITES_PADRAO, Limites
from controle.reconhecedor import EstadoMao, Reconhecedor
from controle.saida import Executor

MODELO = pathlib.Path(__file__).resolve().parent / "dados" / "hand_landmarker.task"
TAMANHO_INFERENCIA = (640, 360)  # o modelo reduz internamente; reduzir antes economiza tempo


@dataclass
class Config:
    zoom: float = 1.0


@dataclass(frozen=True)
class Metricas:
    fps: float
    espera_ms: float       # da captura até o processamento começar
    mediapipe_ms: float
    gestos_ms: float       # reconhecimento + execução das ações
    total_ms: float        # da captura do quadro até a ação executada


@dataclass(frozen=True)
class Resultado:
    t_ms: int
    imagem: np.ndarray     # BGR, já espelhada e com zoom: é o que o MediaPipe viu
    maos: list[Mao]
    estado: list[EstadoMao]
    feitas: list[tuple[str, str]]
    metricas: Metricas
    pausado: bool = field(default=False)


class Pipeline:
    def __init__(self, camera, executor: Executor, config: Config,
                 ao_resultado: Callable[[Resultado], None], params: Parametros | None = None,
                 modelo: pathlib.Path = MODELO, limites: Limites = LIMITES_PADRAO):
        self.camera, self.executor, self.config = camera, executor, config
        self.ao_resultado = ao_resultado
        self.reconhecedor = Reconhecedor(params, limites=limites)
        self.modelo = modelo
        self.gravador = None  # Gravador ativo, ou None (definido pela interface)
        self._trava = threading.Lock()
        self._parar = False
        self._t0 = None
        self._ultimo_ts = -1
        self._fps = 0.0
        self._anterior = None

    def rodar(self):
        opcoes = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(self.modelo)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
        )
        with vision.HandLandmarker.create_from_options(opcoes) as landmarker:
            while not self._parar:
                entrada = self.camera.esperar_quadro(timeout=0.1)
                if entrada is None:
                    if self._parar or not self.camera.rodando:
                        break
                    self._sem_quadro()  # câmera travada: o tempo segue e mãos sumidas soltam botões
                    continue
                self._processar(landmarker, *entrada)
        with self._trava:
            self.executor.liberar_tudo()

    def _processar(self, landmarker, imagem: np.ndarray, t_captura: float):
        inicio = time.monotonic()
        if self._t0 is None:
            self._t0 = t_captura
        ts = max(int((t_captura - self._t0) * 1000), self._ultimo_ts + 1)  # MediaPipe exige crescente
        self._ultimo_ts = ts
        # sempre espelhado: limiares e sentidos (cursor, varredura, rolagem) assumem imagem de espelho;
        # o "espelhar" do menu muda só a visualização
        imagem = cv2.flip(imagem, 1)
        imagem = aplicar_zoom(imagem, self.config.zoom)
        pequena = cv2.resize(imagem, TAMANHO_INFERENCIA, interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(pequena, cv2.COLOR_BGR2RGB)
        r = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        depois_mp = time.monotonic()
        maos = [
            Mao(img=np.array([(p.x, p.y, p.z) for p in li], np.float32),
                mundo=np.array([(p.x, p.y, p.z) for p in lm], np.float32),
                rotulo=lado[0].category_name, confianca=lado[0].score)
            for li, lm, lado in zip(r.hand_landmarks, r.hand_world_landmarks, r.handedness)
        ]
        with self._trava:
            eventos = self.reconhecedor.processar(Quadro(ts, tuple(maos)))
            feitas = self.executor.executar(eventos)
            estado = list(self.reconhecedor.estado)
            pausado = not self.executor.ativo
        gravador = self.gravador
        if gravador is not None:
            gravador.adicionar(ts, maos, eventos)
        fim = time.monotonic()
        if self._anterior is not None:
            self._fps += 0.1 * (1 / max(fim - self._anterior, 1e-3) - self._fps)
        self._anterior = fim
        metricas = Metricas(
            fps=self._fps,
            espera_ms=(inicio - t_captura) * 1000,
            mediapipe_ms=(depois_mp - inicio) * 1000,
            gestos_ms=(fim - depois_mp) * 1000,
            total_ms=(fim - t_captura) * 1000,
        )
        self.ao_resultado(Resultado(ts, imagem, maos, estado, feitas, metricas, pausado))

    def _sem_quadro(self):
        if self._t0 is None:
            return  # nenhum quadro ainda: nada pressionado
        ts = max(int((time.monotonic() - self._t0) * 1000), self._ultimo_ts + 1)
        self._ultimo_ts = ts
        with self._trava:
            self.executor.executar(self.reconhecedor.processar(Quadro(ts, ())))

    def pausar(self):
        """Para de agir: solta botões e teclas e esquece o estado das mãos."""
        with self._trava:
            self.executor.executar(self.reconhecedor.reiniciar(self._ultimo_ts))
            self.executor.liberar_tudo()
            self.executor.ativo = False

    def retomar(self):
        with self._trava:
            self.executor.ativo = True

    def parar(self):
        self._parar = True
        self.camera.parar()
