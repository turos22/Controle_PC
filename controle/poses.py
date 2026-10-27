"""Pose estática da mão em um quadro. Limiares calibrados nos vídeos de referência."""
from dataclasses import dataclass
from enum import Enum

from controle.geometria import Medidas



@dataclass(frozen=True)
class Limites:
    """Limiares de retidão e ângulo que separam as poses; o perfil de cada pessoa pode ajustá-los."""
    esticado: float = 0.86          # retidão acima disso: dedo reto
    dobrado: float = 0.65           # abaixo disso: dedo enrolado
    punho_indicador: float = 0.62
    aberta_minimo: float = 0.74     # mão aberta tolera dedos um pouco curvos (garra aberta, varredura)
    pinca_max: float = 0.65         # pontas de polegar e indicador a até ~2/3 da palma (pinça frouxa conta)
    l_angulo_min: float = 45.0      # polegar aberto em relação ao indicador; apontando fica abaixo de ~35°
    c_pinca_max: float = 1.4
    minimo_tres_dedos: float = 0.82     # três dedos do Arthur: mínimo 0,62–0,76; mão aberta dele: 0,92–0,99
    # polegar para baixo (fechar)
    polegar_esticado: float = 0.85
    polegar_para_baixo: float = 0.7     # componente vertical da direção do polegar na imagem
    polegar_afastado: float = 1.0       # longe do punho: não é o polegar enrolado de um punho comum


LIMITES_PADRAO = Limites()


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


def classificar(m: Medidas, limites: Limites = LIMITES_PADRAO) -> Pose:
    L = limites
    r = m.retidao
    outros_dobrados = r["M"] < L.dobrado and r["A"] < L.dobrado and r["P"] < L.dobrado
    if min(r["I"], r["M"], r["A"]) >= L.esticado and r["P"] < L.minimo_tres_dedos:
        return Pose.TRES_DEDOS  # antes da mão aberta: o mínimo meio dobrado é a única diferença
    if min(r["I"], r["M"], r["A"], r["P"]) >= L.aberta_minimo:
        return Pose.ABERTA
    if r["I"] >= L.esticado and r["M"] >= L.esticado and r["A"] < L.dobrado:
        return Pose.DOIS_DEDOS
    if r["I"] >= L.esticado and outros_dobrados:
        if m.angulo_polegar >= L.l_angulo_min:
            return Pose.L
        return Pose.INDICADOR
    quatro_dobrados = outros_dobrados and r["I"] < L.dobrado
    if (quatro_dobrados and r["T"] >= L.polegar_esticado and m.polegar_dy >= L.polegar_para_baixo
            and m.afastamento_polegar >= L.polegar_afastado and m.pinca >= L.pinca_max):
        return Pose.POLEGAR_BAIXO
    if r["I"] < L.punho_indicador and outros_dobrados:
        return Pose.PUNHO
    if m.pinca <= L.pinca_max and outros_dobrados:
        return Pose.PINCA
    if outros_dobrados and m.pinca <= L.c_pinca_max:
        return Pose.C
    return Pose.DESCONHECIDA
