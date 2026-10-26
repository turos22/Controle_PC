"""Teste manual da saída: passa o ponteiro pelo centro e cantos de cada tela e abre/fecha a visão geral.

Não clica nem digita. Uso: python -m controle.diagnostico
"""
import os
import sys
import time

from controle.cursor import Retangulo, envolvente

MARGEM = 40


def executar(saida, telas: list[Retangulo], pausa: float = 0.8, avisar=print):
    area = envolvente(telas)

    def mover(x: float, y: float):
        saida.mover_absoluto((x - area.x) / (area.w - 1), (y - area.y) / (area.h - 1))
        time.sleep(pausa)

    for i, t in enumerate(telas, start=1):
        avisar(f"Tela {i} ({t.w}x{t.h}+{t.x}+{t.y}): centro e quatro cantos")
        mover(t.x + t.w / 2, t.y + t.h / 2)
        for x, y in ((t.x + MARGEM, t.y + MARGEM), (t.x + t.w - MARGEM, t.y + MARGEM),
                     (t.x + t.w - MARGEM, t.y + t.h - MARGEM), (t.x + MARGEM, t.y + t.h - MARGEM)):
            mover(x, y)
    avisar("Abrindo a visão geral do KDE…")
    saida.atalho_kwin("Overview")
    time.sleep(pausa * 2)
    avisar("…e fechando")
    saida.atalho_kwin("Overview")
    t0 = telas[0]
    mover(t0.x + t0.w / 2, t0.y + t0.h / 2)


def main() -> int:
    import cv2  # noqa: F401
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    from PySide6.QtWidgets import QApplication

    from controle.app import telas_do_qt
    from controle.saida import SaidaUinput

    app = QApplication(sys.argv)
    telas = telas_do_qt(app)
    saida = SaidaUinput()
    time.sleep(1)  # o KWin leva um instante para adotar o dispositivo novo
    try:
        executar(saida, telas)
    finally:
        saida.fechar()
    print("Fim. O ponteiro passou pelos cantos certos das duas telas?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
