import numpy as np

from controle.calibracao import MINIMO_AMOSTRAS, PASSOS, Coletor, calcular
from controle.geometria import Medidas
from controle.poses import LIMITES_PADRAO, Pose, classificar

RNG = np.random.default_rng(7)


def medida(i, m, a, p, t=0.9, pinca=1.2, angulo=20.0, borda=False):
    return Medidas(retidao={"I": i, "M": m, "A": a, "P": p, "T": t}, pinca=pinca, pinca_medio=1.2,
                   angulo_polegar=angulo, afastamento_polegar=1.2, polegar_dy=0.0,
                   centro=(0.5, 0.5), no_indicador=(0.5, 0.5), tamanho=0.3, na_borda=borda)


def amostras_de(pose, base, n=40, ruido=0.015, **kw):
    """`base` = retidão de (I, M, A, P); o ruído é o tremor natural da medida."""
    return [medida(*(RNG.normal(b, ruido) for b in base), **kw) for _ in range(n)]


def sessao(rigido=False):
    """Mãos de uma pessoa cujos dedos esticados chegam a ~0,80 (e dobrados a ~0,55)."""
    e = 0.80 if rigido else 0.95   # esticado
    d = 0.55 if rigido else 0.45   # dobrado
    return {
        Pose.ABERTA: amostras_de(Pose.ABERTA, (e, e, e, e)),
        Pose.PUNHO: amostras_de(Pose.PUNHO, (d, d, d, d), pinca=1.4),
        Pose.INDICADOR: amostras_de(Pose.INDICADOR, (e, d, d, d), angulo=20),
        Pose.DOIS_DEDOS: amostras_de(Pose.DOIS_DEDOS, (e, e, d, d)),
        Pose.TRES_DEDOS: amostras_de(Pose.TRES_DEDOS, (e, e, e, d + 0.12)),
        Pose.PINCA: amostras_de(Pose.PINCA, (0.72, d, d, d), pinca=0.25),
        Pose.L: amostras_de(Pose.L, (e, d, d, d), angulo=70),
    }


def test_passos_cobrem_as_poses_que_calibram_limites():
    assert set(PASSOS) == {Pose.ABERTA, Pose.PUNHO, Pose.INDICADOR, Pose.DOIS_DEDOS, Pose.TRES_DEDOS,
                           Pose.PINCA, Pose.L}


def test_mao_comum_fica_com_limites_proximos_dos_padroes():
    r = calcular(sessao(rigido=False))
    assert abs(r.limites.esticado - LIMITES_PADRAO.esticado) < 0.13
    assert r.acuracia_depois >= r.acuracia_antes >= 0.9


def test_mao_com_dedos_menos_retos_baixa_os_limites_e_ganha_acuracia():
    r = calcular(sessao(rigido=True))
    assert r.limites.esticado < LIMITES_PADRAO.esticado
    assert r.acuracia_antes < 0.7 and r.acuracia_depois > 0.9
    assert "esticado" in r.ajustados


def test_limites_novos_classificam_as_proprias_amostras():
    amostras = sessao(rigido=True)
    r = calcular(amostras)
    for pose, lista in amostras.items():
        certas = sum(classificar(m, r.limites) is pose for m in lista) / len(lista)
        assert certas >= 0.9, pose


def test_poucas_amostras_nao_mudam_nada():
    amostras = {p: l[: MINIMO_AMOSTRAS - 1] for p, l in sessao(rigido=True).items()}
    r = calcular(amostras)
    assert r.limites == LIMITES_PADRAO and r.ajustados == {} and r.avisos


def test_faltou_um_passo_so_deixa_de_ajustar_o_que_dependia_dele():
    amostras = sessao(rigido=True)
    del amostras[Pose.L]
    r = calcular(amostras)
    assert r.limites.l_angulo_min == LIMITES_PADRAO.l_angulo_min
    assert r.limites.esticado < LIMITES_PADRAO.esticado


def test_dados_sobrepostos_mantem_os_padroes_e_avisa():
    # "dobrado" e "esticado" da pessoa se confundem: não há limiar que separe
    lixo = {p: amostras_de(p, (0.7, 0.7, 0.7, 0.7), ruido=0.1) for p in PASSOS}
    r = calcular(lixo)
    assert r.limites.esticado == LIMITES_PADRAO.esticado and r.limites.dobrado == LIMITES_PADRAO.dobrado
    assert r.avisos


def test_limites_ficam_dentro_de_faixas_seguras():
    absurdo = {p: amostras_de(p, (0.2 if p is Pose.PUNHO else 0.3,) * 4, ruido=0.001) for p in PASSOS}
    r = calcular(absurdo)
    assert 0.74 <= r.limites.esticado <= 0.92 and 0.53 <= r.limites.dobrado <= 0.75


def test_nao_aceita_resultado_pior_que_os_padroes():
    # amostras que os padrões acertam; qualquer ajuste que piore a acurácia é descartado
    r = calcular(sessao(rigido=False))
    assert r.acuracia_depois >= r.acuracia_antes


def test_coletor_ignora_mao_na_borda_e_conta_por_pose():
    c = Coletor()
    c.iniciar(Pose.ABERTA)
    c.adicionar(medida(0.9, 0.9, 0.9, 0.9))
    c.adicionar(medida(0.9, 0.9, 0.9, 0.9, borda=True))
    c.iniciar(Pose.PUNHO)
    c.adicionar(medida(0.5, 0.5, 0.5, 0.5))
    assert {p: len(l) for p, l in c.amostras.items()} == {Pose.ABERTA: 1, Pose.PUNHO: 1}
    assert c.quantidade(Pose.ABERTA) == 1
