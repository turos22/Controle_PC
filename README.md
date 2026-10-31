🖐️ Controle por gestos · [English](README.en.md)

Controle do computador por gestos das mãos em tempo real, com Python, OpenCV e MediaPipe.
Roda em **Linux, Windows e macOS**; só o Linux (KDE Plasma em Wayland) foi verificado de ponta a ponta.

| Sistema | Mouse e teclado | Ações de janela | Situação |
|---|---|---|---|
| Linux, KDE Plasma (Wayland ou X11) | `uinput` | atalhos do KWin por D-Bus | **verificado** |
| Linux, GNOME | `uinput` | atalhos de teclado padrão | código e testes; sem prova |
| Linux, outros | `uinput` | só mouse, cliques, rolagem e zoom | parcial |
| Windows 10/11 | `SendInput` | atalhos do Windows | código e testes; sem prova no Windows real |
| macOS | Quartz (pyobjc) | atalhos do macOS | código e testes com Quartz falso; sem prova |

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

Roteiro de teste de cada gesto: [docs/guia-de-testes.md](docs/guia-de-testes.md). Verificação no Windows:
[docs/verificacao-windows.md](docs/verificacao-windows.md).

## Instalação

Precisa de Python 3.10 ou mais novo (testado no 3.13) e uma webcam. Se o `pip` não achar uma versão do
`mediapipe` para o seu Python, use o Python 3.12.

### Linux

```bash
python -m venv .venv
.venv/bin/pip install .
```

O programa cria um mouse e um teclado virtuais em `/dev/uinput`. Confira o acesso com
`test -w /dev/uinput && echo ok`. Sem isso ele abre em modo demonstração. Para liberar:

```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo usermod -aG input $USER   # depois, saia da sessão e entre de novo
```

### Windows

```powershell
py -m venv .venv
.venv\Scripts\pip install .
.venv\Scripts\controle-por-gestos
```

- Libere o acesso à câmera em Configurações → Privacidade → Câmera.
- O Windows não deixa um programa comum controlar janelas de programas abertos como administrador.

### macOS

```bash
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/controle-por-gestos
```

- Libere **Câmera** e **Acessibilidade** para o aplicativo de onde você roda o comando (Terminal, iTerm…)
  em Ajustes do Sistema → Privacidade e Segurança. Sem Acessibilidade o programa avisa e nada age.
- No Mac, "alternar janelas" é Comando+Tab (troca de **aplicativo**), "expandir" põe a janela em tela cheia
  e o zoom usa Comando + roda.

Para desenvolver: `pip install -e ".[dev]"`. O `requirements.txt` guarda as versões exatas em que o projeto
foi testado.

## Uso

```bash
.venv/bin/controle-por-gestos      # ou: .venv/bin/python main.py / python -m controle
```

- `--demonstracao`: reconhece e mostra os gestos sem agir no sistema.
- `--camera N`: escolhe a câmera (0 é a primeira).
- `Esc` pausa (só pausa, nunca retoma); `P` pausa e retoma. Pausar solta qualquer botão ou
  tecla pressionado. `Ctrl+Q` sai.
- **Calibração**: na primeira abertura o programa oferece calibrar os gestos para a sua mão (cerca de 40
  segundos, sete poses). Dá para refazer pelo botão "Calibrar meus gestos". Se os padrões já servem, nada muda.
- Menu à esquerda: calibrar, gravar sessão, zoom digital, espelhar a visualização, modo e velocidade do
  cursor, suavização, velocidade e sentido da rolagem, ligar ou desligar cada gesto. Os ajustes ficam salvos.
- Idioma: português ou inglês, conforme o sistema (ou `"idioma": "pt" | "en"` no perfil).
- O perfil (`perfil.json`) fica em `~/.config/controle-por-gestos` (Linux), `%APPDATA%\controle-por-gestos`
  (Windows) ou `~/Library/Application Support/controle-por-gestos` (macOS).
- Gravações de sessão guardam só os pontos das mãos, nenhuma imagem: em `gravacoes/` no repositório, ou na
  pasta do perfil quando instalado.
- Diagnóstico da saída (passa o ponteiro pelos cantos das telas e abre/fecha a visão geral,
  sem clicar): `python -m controle.diagnostico`.

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
  plataforma/     detecta o sistema; entrada e ações por sistema (linux, windows, macos, atalhos)
  perfil.py       perfil do usuário em JSON (limiares, ajustes, idioma, câmera)
  calibracao.py   calibração guiada dos limiares de pose
  idioma.py       português e inglês
  dados/          modelo do MediaPipe
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

Os testes rodam em qualquer sistema: os backends de Windows e macOS são testados com substitutos.

As fixtures em `tests/fixtures/` são os landmarks extraídos dos vídeos de referência dos gestos,
espelhados como no uso ao vivo. Para regerar a partir de uma pasta de vídeos:
`.venv/bin/python tests/ferramentas/gerar_fixtures.py <pasta>`.

## Licença

[MIT](LICENSE). O modelo `controle/dados/hand_landmarker.task` vem do MediaPipe (Google) e segue a licença do MediaPipe.

Python • OpenCV • MediaPipe • PySide6 • Computer Vision
