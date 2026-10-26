"""Gera as fixtures de landmarks a partir dos vídeos de referência.

Reproduz o pipeline ao vivo: quadro espelhado, reduzido para 640x360, MediaPipe em modo VIDEO
a 30 fps. Só os landmarks são salvos (nenhuma imagem).

Uso: python tests/ferramentas/gerar_fixtures.py <pasta_dos_videos>
"""
import pathlib
import re
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

RAIZ = pathlib.Path(__file__).resolve().parents[2]
MODELO = RAIZ / "hand_landmarker.task"
DESTINO = RAIZ / "tests" / "fixtures"
FPS_ALVO = 30
MAOS = 2


def extrair(caminho: pathlib.Path) -> dict:
    opcoes = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODELO)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=MAOS,
    )
    landmarker = vision.HandLandmarker.create_from_options(opcoes)
    cap = cv2.VideoCapture(str(caminho))
    passo = max(1, round(cap.get(cv2.CAP_PROP_FPS) / FPS_ALVO))
    t_ms, img, mundo, rotulo, confianca = [], [], [], [], []
    indice = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if indice % passo:
            indice += 1
            continue
        frame = cv2.flip(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA), 1)
        ts = int(len(t_ms) * 1000 / FPS_ALVO)
        r = landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), ts)
        q_img = np.full((MAOS, 21, 3), np.nan, np.float32)
        q_mundo = np.full((MAOS, 21, 3), np.nan, np.float32)
        q_rotulo = np.full(MAOS, -1, np.int8)
        q_conf = np.zeros(MAOS, np.float32)
        for i, (li, lm, lado) in enumerate(zip(r.hand_landmarks, r.hand_world_landmarks, r.handedness)):
            q_img[i] = [(p.x, p.y, p.z) for p in li]
            q_mundo[i] = [(p.x, p.y, p.z) for p in lm]
            q_rotulo[i] = 1 if lado[0].category_name == "Right" else 0
            q_conf[i] = lado[0].score
        t_ms.append(ts)
        img.append(q_img)
        mundo.append(q_mundo)
        rotulo.append(q_rotulo)
        confianca.append(q_conf)
        indice += 1
    cap.release()
    landmarker.close()
    return {
        "t_ms": np.array(t_ms, np.int32),
        "img": np.stack(img),
        "mundo": np.stack(mundo),
        "rotulo": np.stack(rotulo),
        "confianca": np.stack(confianca),
    }


def main() -> None:
    pasta = pathlib.Path(sys.argv[1])
    DESTINO.mkdir(parents=True, exist_ok=True)
    for video in sorted(pasta.glob("*.mp4")):
        numero = re.match(r"(\d+)", video.name)
        if not numero:
            continue
        dados = extrair(video)
        saida = DESTINO / f"v{int(numero.group(1)):02d}.npz"
        np.savez_compressed(saida, **dados)
        print(f"{saida.name}: {len(dados['t_ms'])} quadros, "
              f"{int((dados['rotulo'] >= 0).any(axis=1).sum())} com mão")


if __name__ == "__main__":
    main()
