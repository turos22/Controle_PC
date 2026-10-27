import cv2
import pytest

from controle.captura import Camera, backends_do_sistema


class CapFalsa:
    """Câmera que só aceita resoluções até `maximo` (como uma webcam barata)."""

    def __init__(self, abre=True, maximo=(1920, 1080)):
        self.abre, self.maximo, self.res = abre, maximo, (640, 480)
        self.liberada = False

    def isOpened(self):
        return self.abre

    def set(self, prop, valor):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            self.res = (min(int(valor), self.maximo[0]), self.res[1])
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            self.res = (self.res[0], min(int(valor), self.maximo[1]))
        return True

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: self.res[0], cv2.CAP_PROP_FRAME_HEIGHT: self.res[1]}.get(prop, 0)

    def release(self):
        self.liberada = True


def test_backends_por_sistema():
    assert backends_do_sistema("linux")[0] == cv2.CAP_V4L2
    assert backends_do_sistema("windows")[:2] == [cv2.CAP_MSMF, cv2.CAP_DSHOW]
    assert backends_do_sistema("macos")[0] == cv2.CAP_AVFOUNDATION
    assert all(b[-1] == cv2.CAP_ANY for b in (backends_do_sistema(s) for s in ("linux", "windows", "macos")))


def test_abre_no_primeiro_backend_que_funciona_e_pede_720p():
    tentativas = []

    def abrir(indice, backend):
        tentativas.append(backend)
        return CapFalsa(abre=backend == cv2.CAP_MSMF)

    c = Camera(abrir=abrir, sistema="windows")
    c._abrir_melhor()
    assert tentativas == [cv2.CAP_MSMF] and c.resolucao == (1280, 720)


def test_pula_backend_que_nao_abre():
    tentativas = []

    def abrir(indice, backend):
        tentativas.append(backend)
        return CapFalsa(abre=backend == cv2.CAP_DSHOW)

    c = Camera(abrir=abrir, sistema="windows")
    c._abrir_melhor()
    assert tentativas == [cv2.CAP_MSMF, cv2.CAP_DSHOW]


def test_camera_que_nao_chega_ao_720p_cai_para_o_que_houver():
    c = Camera(abrir=lambda i, b: CapFalsa(maximo=(640, 480)), sistema="linux")
    c._abrir_melhor()
    assert c.resolucao == (640, 480)


def test_nenhum_backend_abre_levanta_erro_com_a_dica():
    c = Camera(abrir=lambda i, b: CapFalsa(abre=False), sistema="macos", indice=1)
    with pytest.raises(RuntimeError, match="câmera 1"):
        c._abrir_melhor()


def test_libera_a_camera_que_nao_abriu_antes_de_tentar_outro_backend():
    caps = []

    def abrir(indice, backend):
        caps.append(CapFalsa(abre=backend == cv2.CAP_ANY))
        return caps[-1]

    Camera(abrir=abrir, sistema="linux")._abrir_melhor()
    assert caps[0].liberada
