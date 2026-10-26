"""Ponto de entrada: monta câmera, reconhecimento, saída e janela."""
import os
import sys
import threading

import cv2  # noqa: F401 — importado antes do Qt: ele define o caminho de plugins do Qt dele

os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)  # o PySide6 usa os próprios plugins

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from controle.captura import Camera  # noqa: E402
from controle.cursor import Cursor, Retangulo  # noqa: E402
from controle.interface import JanelaPrincipal  # noqa: E402
from controle.pipeline import Config, Pipeline  # noqa: E402
from controle.saida import Executor, SaidaNula, SaidaUinput  # noqa: E402


def telas_do_qt(app: QApplication) -> list[Retangulo]:
    """Geometria lógica de cada tela: é o espaço em que o KWin posiciona o ponteiro absoluto."""
    return [Retangulo(g.x(), g.y(), g.width(), g.height()) for g in (s.geometry() for s in app.screens())]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    demonstracao = "--demonstracao" in argv
    app = QApplication(argv)
    app.setApplicationName("Controle por gestos")
    telas = telas_do_qt(app)
    print("Telas:", ", ".join(f"{t.w}x{t.h}+{t.x}+{t.y}" for t in telas))

    aviso = None
    try:
        saida = SaidaNula() if demonstracao else SaidaUinput()
    except OSError as erro:
        saida, demonstracao = SaidaNula(), True
        aviso = f"Sem acesso a /dev/uinput ({erro}). Rodando em modo demonstração."

    camera = Camera()
    try:
        camera.iniciar()
    except RuntimeError as erro:
        QMessageBox.critical(None, "Câmera", str(erro))
        saida.fechar()
        return 1

    executor = Executor(saida, Cursor(telas))
    janela: JanelaPrincipal | None = None
    pipeline = Pipeline(camera, executor, Config(), ao_resultado=lambda r: janela.ponte.resultado.emit(r))
    janela = JanelaPrincipal(pipeline, modo_demonstracao=demonstracao, aviso=aviso)
    thread = threading.Thread(target=pipeline.rodar, name="pipeline", daemon=True)
    thread.start()
    janela.show()
    codigo = app.exec()
    pipeline.parar()
    thread.join(timeout=3)
    saida.fechar()
    return codigo
