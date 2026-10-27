🖐️ Hand Gesture Controller

Controle do computador por gestos das mãos em tempo real, com Python, OpenCV e MediaPipe.
Feito para **Linux com KDE Plasma em Wayland**: o mouse e o teclado virtuais usam `uinput`, e as
ações de janela usam os atalhos do KWin via D-Bus.

## Gestos

Todos funcionam com qualquer uma das mãos. A janela do programa mostra a legenda completa e
acende o gesto reconhecido na hora.

| Gesto | Ação |
|---|---|
| Indicador esticado (relativo, com aceleração) | move o cursor |
| Apontando, polegar encosta e solta no indicador (duas vezes = duplo) | clique esquerdo |
| Apontando, polegar encosta e solta no médio | clique direito |
| Pinça fechada, parada um instante, e mover | segurar e arrastar (nada mais age enquanto isso) |
| Dois dedos esticados, afastando a mão do ponto onde formou a pose | rolagem joystick (4 sentidos) |
| Mão fechada → L com o polegar bem aberto | maximizar a janela |
| Mão aberta → garra → aberta | visão geral |
| Mão aberta varrendo rápido para o lado (parar antes da próxima) | área de trabalho à esquerda / à direita |
| Três dedos (indicador, médio, anelar) + deslizar para os lados | Alt+Tab (mudar a pose escolhe) |
| Polegar para baixo segurado ~0,8 s | fechar a janela |
| Duas pinças ao mesmo tempo, afastando ou juntando | zoom (Ctrl + roda) |

Roteiro de teste de cada gesto: [docs/guia-de-testes.md](docs/guia-de-testes.md).

## Requisitos

- Linux, KDE Plasma em Wayland, Python 3.13, uma webcam.
- Escrita em `/dev/uinput` para o seu usuário. Confira com:
  `test -w /dev/uinput && echo ok`. Sem isso, o programa abre em modo demonstração.

## Instalação

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Uso

```bash
.venv/bin/python main.py
```

- `--demonstracao`: reconhece e mostra os gestos sem agir no sistema.
- `Esc` pausa (só pausa, nunca retoma); `P` pausa e retoma. Pausar solta qualquer botão ou
  tecla pressionado. `Ctrl+Q` sai.
- Menu à esquerda: gravar sessão (calibração), zoom digital, espelhar a visualização, modo e
  velocidade do cursor, suavização, velocidade e sentido da rolagem, ligar ou desligar cada gesto.
- Gravações vão para `gravacoes/` (só os pontos das mãos, nenhuma imagem; fora do git).
- Diagnóstico da saída (passa o ponteiro pelos cantos das telas e abre/fecha a visão geral,
  sem clicar): `.venv/bin/python -m controle.diagnostico`.

A câmera é aberta em 1280x720 a 30 fps: nesta câmera é o mesmo campo de visão do 1080p (o
640x480 corta as laterais) e o 1080p cai para 25 fps.

## Desempenho medido

Com a câmera real, por quadro: MediaPipe ~9,4 ms, reconhecimento dos gestos + ações ~0,3 ms,
da entrega do quadro até a ação ~10 ms (p95). O limite é a câmera, que entrega um quadro a
cada 33 ms.

## Estrutura

```
controle/
  geometria.py    medidas da mão (retidão dos dedos, pinça, ângulo do polegar…)
  poses.py        pose de cada quadro (indicador, dois dedos, pinça, punho, L, aberta, C)
  gestos.py       máquina de estados por mão → eventos
  reconhecedor.py identidade das mãos, zoom com as duas mãos, dono do cursor
  cursor.py       região ativa → telas, filtro One Euro
  saida.py        executa os eventos no vocabulário neutro (botão, tecla, ação de janela)
  plataforma/     detecta o sistema; entrada e ações por sistema (Linux: uinput + KWin)
  captura.py      thread de câmera (sempre o quadro mais recente)
  pipeline.py     câmera → MediaPipe → gestos → ações, com métricas
  interface.py    janela Qt
  legenda.py      catálogo dos gestos
tests/            pytest; fixtures = landmarks dos vídeos de referência (sem imagens)
docs/             spec, plano e guia de testes
```

## Testes

```bash
.venv/bin/pytest
```

As fixtures em `tests/fixtures/` são os landmarks extraídos dos vídeos de referência dos gestos,
espelhados como no uso ao vivo. Para regerar a partir de uma pasta de vídeos:
`.venv/bin/python tests/ferramentas/gerar_fixtures.py <pasta>`.

Python • OpenCV • MediaPipe • PySide6 • Computer Vision
