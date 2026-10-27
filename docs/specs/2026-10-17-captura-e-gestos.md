# Spec — captura com campo de visão completo e novos gestos

Status: **aprovada em 2026-10-18**. Os itens de "Em aberto" são resolvidos durante a execução.

## Contexto

- Plataforma alvo: **somente Linux, KDE Plasma em Wayland**. O código atual tem trechos de
  Windows (`notepad.exe`, `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS`) que saem ou são substituídos.
- Câmera: Jieli "USB Composite Device" (`5258:4a55`), `/dev/video0`. Só MJPEG, no máximo 30 fps.
  Resoluções: 1920x1080, 1280x720, 640x480, 640x360, 352x288, 352x240.
  Sem zoom, foco, pan ou tilt em hardware.

## Fatos medidos (2026-10-17)

| Fato | Evidência |
|---|---|
| `cv2.VideoCapture(0)` abre em 640x480, 30 fps, buffer de 4 quadros | `cap.get(...)` no venv |
| 640x480 é um corte 4:3 do centro do sensor (~1440x1080 dos 1920x1080) e perde ~25% da largura | comparação de quadros por referências fixas do fundo |
| 1920x1080 mostra o sensor inteiro | idem |
| MediaPipe `detect_for_video`: ~5 ms de mediana por quadro em qualquer resolução | `medir_pipeline.py` com 60 quadros |
| 1920x1080 sem pedir fps: ~25 fps (intervalo de 40 ms); 640x480: ~31 fps | idem |
| `resize` + `cvtColor` de 1080p para 640x360: < 1 ms | idem |
| OpenCV 5.0 do pip tem backend GUI Qt5, então a trackbar funciona | `cv2.getBuildInformation()` |
| Usuário tem escrita em `/dev/uinput` (ACL) | `getfacl`, `test -w` |

Ressalvas: o MediaPipe foi medido provavelmente **sem mão no quadro**, e com mão o custo pode
subir. O libjpeg emite `Corrupt JPEG data: extraneous bytes` em todo quadro: é ruído do MJPEG
da câmera e os quadros decodificam normalmente.

## Requisitos

### R1 — Campo de visão máximo ("zoom out")
- Capturar em 1920x1080 MJPEG para usar o sensor inteiro.
- Reduzir para 640x360 antes do MediaPipe. A coordenada normalizada não muda e o custo cai.
- O slider de zoom digital continua, com 1.0x = sensor inteiro (o máximo de zoom out possível).
- Abaixo disso, só mudando fisicamente (afastar a câmera ou usar lente grande-angular).

### R2 — Latência
1 ms ponta a ponta é impossível: a câmera entrega um quadro a cada 33,3 ms. Metas:
- Classificar gesto a partir dos landmarks em **< 1 ms** por quadro (teste automatizado).
- Processamento total por quadro **< 33 ms (p95)**, sem perder quadro.
- Latência medida por instrumentação no próprio programa, exibida na tela (modo debug).
- Captura sempre com o quadro mais recente (buffer 1 ou thread de leitura), sem fila acumulada.

### R3 — Entrada no Wayland
- Trocar `pyautogui` por um dispositivo virtual `uinput` (`python-evdev`) para mouse, scroll e teclas.
- Isolar a camada de entrada atrás de uma interface, para os testes não moverem o cursor real.

### R4 — Gestos e comandos

Fonte: 13 vídeos de referência do Arthur (`~/Vídeos/1..13 - *.mp4`, 1080p a 60 fps, ~150 s).
Analisados por mosaico de quadros (3 por segundo) e por landmarks do MediaPipe em todos os
quadros. Os landmarks extraídos viram fixtures de teste (ver "Testes").

Ambiente medido: 2 áreas de trabalho; 2 telas (1920x1080 em 0,0 e 1422x800 em 1920,588);
intervalo de duplo clique do KDE no padrão (400 ms). As ações do KWin abaixo existem e podem ser
acionadas pelo nome via D-Bus (`org.kde.kglobalaccel /component/kwin invokeShortcut`).

Interpretação (aguardando validação, ver "Perguntas"):

| # | Gesto | Mão | O que os dados mostram | Ação |
|---|---|---|---|---|
| 1 | Expandir janela | direita | punho fechado → "L" (indicador a ~80°, polegar para o lado; pinça de ~1 cm para ~12 cm). 3 repetições | KWin `Window Maximize` |
| 2 | Visão geral e voltar | esquerda | mão aberta (dedos para cima) → fecha em garra (~0,4 s fechada) → abre | KWin `Overview` (alterna) |
| 3 | Área de trabalho esq./dir. | esquerda | varredura lateral com a mão aberta: ida ao centro com a palma virada, volta para fora com a palma para a câmera; ~0,2 s por trecho | KWin `Switch One Desktop to the Left/Right` |
| 4 | Indicador como mouse + clique | direita | só o indicador esticado move o cursor; clique = "toque" (indicador dobra no nó do dedo e volta, < 0,4 s) | uinput: movimento + `BTN_LEFT` |
| 5 | Duplo clique | direita | dois toques do indicador, ~0,8 s de intervalo | uinput: dois cliques sintetizados juntos |
| 6 | Alt+Tab | direita | mão aberta → punho (segura Alt); cada "piparote" do punho para a frente = Tab (~0,6 s); mão sai ou abre = solta Alt | uinput: Alt mantido + Tab |
| 7 | Mover janela e expandir | direita | fecha a pinça (pega) → arrasta → "L" | composição de 8 + 1 |
| 8 | Clique segurando | direita | "C" fecha em pinça (pontas a < 2 cm) → botão pressionado; arrasta; abre → solta | uinput: `BTN_LEFT` press/release |
| 9 | Fechar janela | direita | palma aberta para a câmera → "tapa" rápido para baixo e volta (~0,6 s); muito borrão, rastreio perdido em alguns quadros | KWin `Window Close` |
| 10 | Clique direito | direita | indicador + médio esticados; toque com os dois dedos retos (dobram no nó) | uinput: `BTN_RIGHT` |
| 11 | Rolagem vertical | direita | indicador + médio para cima; os dedos enrolam por completo e voltam (ciclo ~0,6 s) | uinput: `REL_WHEEL` |
| 12 | Zoom | as duas | as duas mãos em "C"; afastar ou aproximar as mãos | a definir: Ctrl+roda ou zoom de tela do KWin |
| 13 | Rolagem horizontal | direita | indicador + médio apontando para o lado; enrolam e voltam | uinput: `REL_HWHEEL` |

Conflitos e riscos encontrados:
- **1/7 × 8**: no vídeo 8 a soltura do arraste é o mesmo "L" do gesto 1 (ângulos e pinça iguais).
  Se o "L" sempre expande, toda soltura em "L" expande a janela sob o cursor.
- **10 × 11**: mesma pose de partida (indicador + médio a ~60–70°). A única diferença é dedo reto
  dobrando no nó (clique) contra dedo enrolando (rolagem). É o par mais sujeito a confusão.
- **3, 11, 13**: os vídeos mostram o movimento, mas não como escolher o sentido (esquerda × direita,
  cima × baixo). No 3, cada ciclo tem ida e volta.
- **5**: toques a ~0,8 s não cabem nos 400 ms do KDE. O programa sintetiza o duplo clique. O
  primeiro toque continua gerando um clique imediato, sem latência extra.
- **9**: ação destrutiva e o movimento mais rápido do conjunto. A 30 fps, com pouca luz, o rastreio
  falha mais.
- **Modos atuais** (punho esquerdo alterna cursor/rolagem/volume; dois punhos = ditado) colidem
  com o gesto 2.
- Nos vídeos, a mão saiu do quadro várias vezes (bordas). O cursor deve mapear uma **região
  central** do quadro para as duas telas.
- O código atual não espelha a imagem, então mover a mão para a direita leva o cursor para a
  esquerda. A captura nova espelha. Rótulo de mão (Left/Right) do MediaPipe a confirmar com a
  câmera ao vivo.

#### Decisões do Arthur (2026-10-18) — sobrepõem a tabela acima

- **Todos os gestos valem para as duas mãos.** A coluna "Mão" acima é só a mão usada no vídeo.
  - O zoom continua exigindo as duas mãos.
  - O cursor fica com a mão que entrou primeiro na pose de indicador.
- **"L" sempre expande.** Abrir a pinça solta o clique. Se o "L" ficar parado por ~0,3 s, expande.
  Para soltar sem expandir, abrir a mão inteira.
- **Clique direito × rolagem vertical**: mantém os gestos e mede o acerto nas fixtures. Se
  confundir, revisar o clique direito.
- **Sentido da rolagem**: é o contrário do movimento dos dedos, como arrastar o conteúdo.
  - Dedos indo para a esquerda rolam para a direita, e vice-versa.
  - Dedos indo para baixo rolam para cima, e vice-versa.
  - Interpretação técnica (modelo "puxar", derivado das séries dos vídeos 11 e 13): rola só
    enquanto os dois dedos **dobram**, pelo movimento das pontas. Esticar é "levantar os dedos" e
    não rola, senão cada ciclo se anularia. O eixo fica travado no dominante de cada puxada.
    - Vídeo 11: dobra com a mão parada, pontas descendo → rola para cima.
    - Vídeo 13: os dedos dobram enquanto a mão vai para a direita → rola para a **esquerda**.
      Para rolar para a direita: dobrar com a mão indo para a esquerda.
- **Troca de área de trabalho**: ida é um sentido e volta é o outro. A mão indo para a esquerda
  (imagem espelhada) vai para a área da esquerda. Para encadear dois no mesmo sentido, voltar
  devagar: só conta movimento acima de um limiar de velocidade.
- **Zoom**: zoom de aplicativo (Ctrl + roda).
- **Fechar janela**: palma virada para baixo por ~0,3 s depois do tapa, e intervalo de 2 s entre
  dois fechamentos.
- **Modos removidos**: cursor/rolagem/volume e o ditado por voz saem (o ditado dependia de
  `notepad.exe` e do punho esquerdo duplo, que colide com o gesto 2). Isso tira as dependências
  `pyautogui`, `pyperclip`, `sounddevice` e `SpeechRecognition`.

#### Desambiguação derivada dos dados (proposta técnica)
- **Mão fechada é um estado de espera**, não um clique imediato. A partir dela:
  - **abre em "L"** → expande (gesto 1);
  - **piparote do punho** → Alt+Tab: Alt pressionado e um Tab a cada piparote (gesto 6);
  - **abre a mão inteira depois de < ~1,2 s, sem deslocar** → visão geral (gesto 2);
  - **desloca** (pinça ou punho, acima de um limiar) → clique segurando: o botão é pressionado na
    posição de **onde a mão fechou** e o cursor acompanha. Abrir solta (gestos 7 e 8).
- **Clique sem tremor**: o toque desloca a ponta do dedo. O clique sai na posição do cursor de
  ~150 ms antes do início do toque.
- **Cursor**: ponta do indicador numa região central do quadro, mapeada para a área das duas
  telas, com filtro One Euro (suaviza parado e responde rápido em movimento).

### R5 — Interface (pedido de 2026-10-18)
- Janela única em Qt (PySide6), nativa no KDE e no Wayland. Substitui o `cv2.imshow`.
- **Menu auxiliar à esquerda da câmera**:
  - pausar/retomar os gestos (botão e tecla);
  - zoom digital;
  - espelhar;
  - ligar/desligar cada gesto (útil para testar um por vez);
  - suavização do cursor e tamanho da região ativa;
  - mostrar landmarks, região ativa e métricas.
- **Legenda à direita**: cada gesto com a ação. O gesto reconhecido acende na hora (feedback),
  junto com a última ação executada.
- **Barra inferior**: fps, latência por quadro (captura, MediaPipe, gestos) e a pose de cada mão.

### R6 — Guia de testes
Ao final, um `docs/guia-de-testes.md` com o roteiro manual de cada gesto: pose de partida,
movimento, resultado esperado e como saber se falhou.

### Testes
- Landmarks dos 13 vídeos (JSON por vídeo, todos os quadros) como fixtures: cada gesto tem que
  ser reconhecido no próprio vídeo e **não** disparar nos outros (matriz de confusão).
- Classificação por quadro medida em teste: < 1 ms.

## Em aberto
- 1080p a 30 fps: testar `CAP_PROP_FPS=30`. Comparar com 1280x720, que deve ter o mesmo campo de
  visão a 30 fps (verificar). Medição interrompida porque o OBS estava usando a câmera.
- Medir o MediaPipe com uma e com duas mãos no quadro.
- Confirmar na prática que `pyautogui` falha no Wayland (motiva o R3).
- Ditado por voz: substituto do Bloco de Notas no KDE (digitar direto via `uinput` na janela focada?).
- `mediapipe 1.1.1` instala `opencv-contrib-python` junto com `opencv-python` (dois `cv2`), então
  fixar dependências num `requirements.txt`.

## Iteração 2 — decisões de 2026-10-18 (teste ao vivo do Arthur)

Resultado do teste: expandir e visão geral OK; arrastar bom. Cursor impreciso e com pouco
alcance; clique "totalmente desordenado"; clique direito confundido com rolagem (que só ia para
cima/direita); troca de área ia e voltava; Alt+Tab e fechar ruins; zoom só funcionou com duas
pinças (o C não foi reconhecido).

Decisões (sobrepõem as anteriores):
- **Cursor relativo com aceleração** (como touchpad): mão devagar = movimento fino, rápida =
  atravessa as telas. Sair da pose de indicador é a "embreagem" (reposiciona sem mover o cursor).
  O modo absoluto fica como opção no menu.
- **Clique = pinça rápida**: indicador apontando → polegar encosta no indicador e solta em
  < ~350 ms = clique esquerdo (dois seguidos = duplo). Polegar no **médio** = clique direito.
  Segurar a pinça e mover continua sendo arrastar. Sai o toque do indicador.
- **Durante o arraste nenhuma outra ação** (nas duas mãos).
- **Rolagem joystick**: dois dedos esticados; onde a pose se formou é o centro; afastar a mão rola
  sem parar, mais rápido quanto mais longe (quatro sentidos, zona morta no centro). Sentido segue
  a regra do Arthur (mão para a esquerda rola para a direita; para baixo, rola para cima), com
  opção de inverter no menu.
- **Troca de área**: depois de uma troca, só vale outra quando a mão parar (o retorno natural não
  conta).
- **Alt+Tab = três dedos + deslizar**: indicador, médio e anelar esticados abrem o seletor
  (Alt+Tab); cada degrau lateral passa uma janela (direita = próxima, esquerda = anterior);
  mudar de pose escolhe.
- **Fechar = polegar para baixo segurado ~0,8 s**, com anel de contagem na tela; mudar a pose
  antes cancela; 2 s entre fechamentos. Saem o tapa e o "desfazer troca de área".
- **Zoom = duas pinças** ao mesmo tempo (o C continua aceito).
- **Gravação de sessão** no programa: o Arthur grava cada gesto na posição real da câmera; as
  gravações viram fixtures de calibração e de teste (os vídeos do OBS tinham outro enquadramento).

## Iteração 3 — multiplataforma (decisões de 2026-10-27)

Objetivo: outras pessoas usarem o programa em Windows, macOS e Linux.

Decisões do Arthur:
- **Distribuição em duas fases**: fase 1 = o mesmo código roda nos três sistemas, instalado com
  Python (`pip`); fase 2 = instaladores prontos (.exe, .dmg, AppImage).
- **Assistente de calibração no primeiro uso**: a pessoa faz cada gesto algumas vezes e o programa
  ajusta os limites à mão dela (o que foi feito à mão com as gravações do Arthur, automatizado),
  salvos num perfil por usuário.
- **Teste real só em Windows** (além do Linux daqui). macOS fica com código pronto e testes
  simulados, **sem verificação real** até alguém rodar.
- **Interface em português e inglês**, pelo idioma do sistema, com troca no menu. Código continua
  em português.
- Linux além do KDE (padrão técnico, não perguntado): GNOME e X11 com ações por atalho de teclado.

O que muda por sistema:

| Camada | Linux | Windows | macOS |
|---|---|---|---|
| Mouse e teclado | uinput (já existe) | SendInput (ctypes, sem dependência) | Quartz CGEvent (pyobjc); exige permissão de Acessibilidade |
| Ações de janela | KDE: KWin D-Bus; GNOME/X11: atalhos | atalhos: Win+↑, Win+Tab, Ctrl+Win+←/→, Alt+Tab, Alt+F4 | atalhos: Mission Control (Ctrl+↑), Ctrl+←/→, Cmd+Tab, Cmd+W; maximizar = tela cheia |
| Zoom | Ctrl + roda | Ctrl + roda | Cmd + "=" / "-" |
| Câmera (OpenCV) | V4L2 | MSMF/DirectShow | AVFoundation; exige permissão de câmera |
| Telas | Qt | Qt (cuidar da escala de DPI) | Qt (pontos lógicos) |

Riscos a verificar: wheels do MediaPipe para Python 3.13 em Windows/macOS (talvez exigir 3.12);
mapeamento do ponteiro absoluto com escala de DPI no Windows; Cmd+Tab no macOS troca de app, não de
janela; resolução/campo de visão de cada câmera (o 1280x720 foi escolhido para a câmera do Arthur).
