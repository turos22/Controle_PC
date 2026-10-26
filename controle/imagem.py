import cv2
import numpy as np


def aplicar_zoom(quadro: np.ndarray, fator: float) -> np.ndarray:
    """Zoom digital: corta o centro do quadro e amplia de volta ao tamanho original."""
    if fator <= 1.0:
        return quadro
    altura, largura = quadro.shape[:2]
    nova_largura, nova_altura = int(largura / fator), int(altura / fator)
    x0, y0 = (largura - nova_largura) // 2, (altura - nova_altura) // 2
    recorte = quadro[y0:y0 + nova_altura, x0:x0 + nova_largura]
    return cv2.resize(recorte, (largura, altura), interpolation=cv2.INTER_LINEAR)
