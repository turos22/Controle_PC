"""Thread de câmera: lê sem parar e guarda só o quadro mais recente (nada acumula em fila)."""
import threading
import time

import cv2

from controle.idioma import tr
from controle.plataforma import detectar


def backends_do_sistema(sistema: str) -> list[int]:
    """Do mais confiável para o menos; CAP_ANY por último deixa o OpenCV escolher."""
    return {
        "linux": [cv2.CAP_V4L2, cv2.CAP_ANY],
        "windows": [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY],
        "macos": [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY],
    }.get(sistema, [cv2.CAP_ANY])


class Camera:
    def __init__(self, indice: int = 0, largura: int = 1280, altura: int = 720, fps: int = 30,
                 abrir=None, sistema: str | None = None):
        self._abrir = abrir or cv2.VideoCapture
        self._backends = backends_do_sistema(sistema or detectar().sistema)
        # 1280x720 tem o mesmo campo de visão do 1080p nesta câmera e entrega 30 fps (o 1080p, 25)
        self.indice, self.pedido = indice, (largura, altura, fps)
        self.resolucao = (0, 0)
        self.fps = 0.0
        self._cap = None
        self._thread = None
        self._cond = threading.Condition()
        self._quadro = None
        self._numero = self._lido = 0
        self._rodando = False

    def _abrir_melhor(self):
        """Abre pelo primeiro backend que funciona e pede 720p a 30 fps; o driver devolve o que tiver."""
        for backend in self._backends:
            cap = self._abrir(self.indice, backend)
            if cap.isOpened():
                break
            cap.release()
        else:
            raise RuntimeError(tr("não abriu a câmera {indice} (outro programa usando, como o OBS, "
                                  "ou sem permissão de câmera para este programa?)", indice=self.indice))
        largura, altura, fps = self.pedido
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, largura)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, altura)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.resolucao = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self._cap = cap

    def iniciar(self):
        self._abrir_melhor()
        self._rodando = True
        self._thread = threading.Thread(target=self._laco, name="camera", daemon=True)
        self._thread.start()

    def _laco(self):
        anterior = None
        while self._rodando:
            ok, quadro = self._cap.read()
            agora = time.monotonic()
            if not ok:
                time.sleep(0.01)
                continue
            if anterior is not None:
                self.fps += 0.1 * (1 / max(agora - anterior, 1e-3) - self.fps)
            anterior = agora
            with self._cond:
                self._quadro = (quadro, agora)
                self._numero += 1
                self._cond.notify_all()

    @property
    def rodando(self) -> bool:
        return self._rodando

    def esperar_quadro(self, timeout: float = 1.0):
        """Próximo quadro ainda não entregue, como (imagem BGR, instante da captura).

        None se parou ou se nenhum quadro novo chegou dentro de `timeout` (câmera travada).
        """
        with self._cond:
            if self._rodando and self._numero == self._lido:
                self._cond.wait(timeout)
            if not self._rodando or self._numero == self._lido:
                return None
            self._lido = self._numero
            return self._quadro

    def parar(self):
        with self._cond:
            self._rodando = False
            self._cond.notify_all()
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
