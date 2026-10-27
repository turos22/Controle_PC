"""Ponto de entrada: monta câmera, reconhecimento, saída e janela."""
import os
import sys
import threading

import cv2  # noqa: F401 — importado antes do Qt: ele define o caminho de plugins do Qt dele

os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)  # o PySide6 usa os próprios plugins

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from controle.captura import Camera  # noqa: E402
from controle.cursor import Cursor, Retangulo  # noqa: E402
from controle.idioma import definir_idioma, idioma_do_sistema, tr  # noqa: E402
from controle.interface import JanelaPrincipal  # noqa: E402
from controle.perfil import Perfil, pasta_de_configuracao  # noqa: E402
from controle.pipeline import Config, Pipeline  # noqa: E402
from controle.plataforma import criar_saida, detectar  # noqa: E402
from controle.saida import Executor  # noqa: E402


def telas_do_qt(app: QApplication) -> list[Retangulo]:
    """Geometria lógica de cada tela: é o espaço em que o KWin posiciona o ponteiro absoluto."""
    return [Retangulo(g.x(), g.y(), g.width(), g.height()) for g in (s.geometry() for s in app.screens())]


def indice_da_camera(argv: list[str], padrao: int = 0) -> int:
    """`--camera N` ou `--camera=N`; sem o argumento vale o `padrao` (a câmera do perfil)."""
    for i, a in enumerate(argv):
        valor = a.split("=", 1)[1] if a.startswith("--camera=") else (argv[i + 1] if a == "--camera" and i + 1 < len(argv) else None)
        if valor is not None and valor.isdigit():
            return int(valor)
    return padrao


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    demonstracao = "--demonstracao" in argv
    app = QApplication(argv)
    app.setApplicationName("Controle por gestos")
    telas = telas_do_qt(app)
    print("Telas:", ", ".join(f"{t.w}x{t.h}+{t.x}+{t.y}" for t in telas))

    ambiente = detectar()
    caminho_perfil = pasta_de_configuracao(ambiente.sistema) / "perfil.json"
    perfil = Perfil.carregar(caminho_perfil)
    for aviso in perfil.avisos:
        print(aviso)
    definir_idioma(perfil.idioma or idioma_do_sistema())
    saida = criar_saida(ambiente, demonstracao)  # depois do idioma: os avisos saem traduzidos
    print(f"Sistema: {ambiente.sistema} {ambiente.area_de_trabalho or ''} {ambiente.sessao or ''}".rstrip())

    camera = Camera(indice_da_camera(argv, perfil.camera))
    try:
        camera.iniciar()
    except RuntimeError as erro:
        QMessageBox.critical(None, tr("Câmera"), str(erro))
        saida.entrada.fechar()
        return 1

    executor = Executor(saida.entrada, saida.acoes, Cursor(telas))
    janela: JanelaPrincipal | None = None
    pipeline = Pipeline(camera, executor, Config(), ao_resultado=lambda r: janela.ponte.resultado.emit(r),
                        params=perfil.parametros_efetivos(), limites=perfil.limites_efetivos())
    janela = JanelaPrincipal(pipeline, modo_demonstracao=saida.demonstracao, aviso=saida.aviso,
                             perfil=perfil, caminho_perfil=caminho_perfil)
    thread = threading.Thread(target=pipeline.rodar, name="pipeline", daemon=True)
    thread.start()
    janela.show()
    QTimer.singleShot(1000, janela.oferecer_calibracao)  # só pergunta se o perfil ainda não foi calibrado
    codigo = app.exec()
    pipeline.parar()
    thread.join(timeout=3)
    saida.entrada.fechar()
    return codigo
