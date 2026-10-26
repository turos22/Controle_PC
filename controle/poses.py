"""Pose estática da mão em um quadro. Limiares calibrados nos vídeos de referência."""
from enum import Enum

from controle.geometria import Medidas

ESTICADO = 0.86        # retidão acima disso: dedo reto
DOBRADO = 0.65         # abaixo disso: dedo enrolado
PUNHO_INDICADOR = 0.62
ABERTA_MINIMO = 0.74   # mão aberta tolera dedos um pouco curvos (garra aberta, varredura)
PINCA_MAX = 0.65       # pontas de polegar e indicador a até ~2/3 da palma (pinça frouxa conta)
L_ANGULO_MIN = 45.0    # polegar aberto em relação ao indicador; apontando fica abaixo de ~35°
C_PINCA_MAX = 1.4
MINIMO_TRES_DEDOS = 0.82   # três dedos do Arthur: mínimo 0,62–0,76; mão aberta dele: 0,92–0,99
# polegar para baixo (fechar): calibrar com as gravações do Arthur
POLEGAR_ESTICADO = 0.85
POLEGAR_PARA_BAIXO = 0.7   # componente vertical da direção do polegar na imagem
POLEGAR_AFASTADO = 1.0     # longe do punho: não é o polegar enrolado de um punho comum


class Pose(Enum):
    ABERTA = "aberta"
    PUNHO = "punho"
    PINCA = "pinça"
    C = "C"
    L = "L"
    INDICADOR = "indicador"
    DOIS_DEDOS = "dois dedos"
    TRES_DEDOS = "três dedos"
    POLEGAR_BAIXO = "polegar p/ baixo"
    DESCONHECIDA = "?"


FECHADAS = frozenset({Pose.PUNHO, Pose.PINCA})


def classificar(m: Medidas) -> Pose:
    r = m.retidao
    outros_dobrados = r["M"] < DOBRADO and r["A"] < DOBRADO and r["P"] < DOBRADO
    if min(r["I"], r["M"], r["A"]) >= ESTICADO and r["P"] < MINIMO_TRES_DEDOS:
        return Pose.TRES_DEDOS  # antes da mão aberta: o mínimo meio dobrado é a única diferença
    if min(r["I"], r["M"], r["A"], r["P"]) >= ABERTA_MINIMO:
        return Pose.ABERTA
    if r["I"] >= ESTICADO and r["M"] >= ESTICADO and r["A"] < DOBRADO:
        return Pose.DOIS_DEDOS
    if r["I"] >= ESTICADO and outros_dobrados:
        if m.angulo_polegar >= L_ANGULO_MIN:
            return Pose.L
        return Pose.INDICADOR
    quatro_dobrados = outros_dobrados and r["I"] < DOBRADO
    if (quatro_dobrados and r["T"] >= POLEGAR_ESTICADO and m.polegar_dy >= POLEGAR_PARA_BAIXO
            and m.afastamento_polegar >= POLEGAR_AFASTADO and m.pinca >= PINCA_MAX):
        return Pose.POLEGAR_BAIXO
    if r["I"] < PUNHO_INDICADOR and outros_dobrados:
        return Pose.PUNHO
    if m.pinca <= PINCA_MAX and outros_dobrados:
        return Pose.PINCA
    if outros_dobrados and m.pinca <= C_PINCA_MAX:
        return Pose.C
    return Pose.DESCONHECIDA
