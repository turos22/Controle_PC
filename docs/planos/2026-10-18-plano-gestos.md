# Plano — gestos, captura e interface

Spec: `docs/specs/2026-10-17-captura-e-gestos.md`. Ambiente: `.venv` (Python 3.13). Testes: `pytest`.
Regra: em cada tarefa, o teste falhando vem antes do código. Fechar a tarefa só com saída de teste colada.

## Arquitetura alvo

```
controle/
  geometria.py   features por mão (dedos esticados, pinça, direção, palma, centro) — funções puras
  poses.py       pose por quadro: PUNHO, PINCA, INDICADOR, DOIS_DEDOS, L, ABERTA, DESCONHECIDA
  gestos.py      máquinas de estado por mão + gesto de duas mãos → eventos
  eventos.py     tipos de evento (Clique, Rolagem, Expandir, ...)
  cursor.py      região ativa → coordenadas das telas; filtro One Euro
  saida.py       executor de eventos: uinput (evdev) + KWin (busctl invokeShortcut); falso p/ testes
  captura.py     thread de câmera: 1080p MJPG, sempre o quadro mais recente, zoom, espelho
  pipeline.py    captura → MediaPipe → gestos → saída, com métricas de latência
  interface.py   janela PySide6: menu à esquerda, vídeo, legenda à direita, barra de status
main.py          ponto de entrada
tests/
  fixtures/      landmarks dos 13 vídeos (npz, espelhados como no ao vivo) — sem imagem
  ferramentas/   script que gera as fixtures a partir dos vídeos
```

## Tarefas

- [x] **T0 — Infra**: `requirements.txt` fixado, `pytest.ini`, pacote `controle/`, script de
      fixtures (vídeo espelhado → MediaPipe → npz a 30 fps). Gerar as 13 fixtures.
      Verificação: `pytest` roda (0 testes ok); fixtures carregam com o formato esperado.
- [x] **T1 — Geometria**: features por mão. Testes com mãos sintéticas (dedo reto/dobrado) e com
      quadros escolhidos das fixtures (ex.: "L" no vídeo 1 em 2,5 s).
- [x] **T2 — Poses**: classificador por quadro. Testes por trechos rotulados das fixtures e de
      desempenho (< 1 ms por quadro).
- [x] **T3 — Gestos**: máquinas de estado e eventos (toque, duplo toque, segurar/arrastar,
      expandir, visão geral, Alt+Tab, fechar, rolagem, área de trabalho, zoom). Testes com
      sequências sintéticas, cobrindo tempos-limite.
- [x] **T4 — Matriz de confusão**: cada vídeo gera o gesto esperado e não gera ações destrutivas
      ou de janela que não pertencem a ele. Ajuste de limiares guiado por esse teste.
- [x] **T5 — Cursor**: mapeamento da região ativa para a área das telas e filtro One Euro.
      Testes numéricos.
- [~] **T6 — Saída**: uinput (mouse absoluto, botões, roda alta resolução, teclas) e KWin via
      D-Bus. Testes com executor falso: ok. Dispositivos criados e classificados pelo udev como
      `ID_INPUT_MOUSE` e `ID_INPUT_KEY`; `invokeShortcut` existe no KWin. **Aberto:** ver o ponteiro e
      os atalhos agindo de verdade (`python -m controle.diagnostico`, com o Arthur olhando).
- [x] **T7 — Captura e pipeline**: thread com quadro mais recente, 1280x720 a 30 fps (mesmo campo
      do 1080p), zoom, espelho, métricas. Câmera real: MediaPipe 9,4 ms, gestos 0,3 ms,
      captura→ação 9,7 ms (mediana).
- [x] **T8 — Interface**: PySide6 com menu à esquerda, legenda à direita e barra de status.
      Rodou no Wayland com a câmera real (modo demonstração); captura da janela conferida.
- [x] **T9 — Limpeza**: `main.py` virou só o ponto de entrada; modos, ditado e dependências
      antigas removidos; README reescrito.
- [x] **T10 — Guia de testes** (`docs/guia-de-testes.md`) escrito. Verificação final: `pytest`
      completo (172 passando) e `/code-review` (10 achados, todos corrigidos; ver registro).

## Registro

### 2026-10-18 — T0 a T4 fechadas (128 testes passando)
- **Captura em 1280x720**: mesmo campo de visão do 1080p (correlação 0,955 contra 0,475 do
  recorte) e 30 fps reais. O 1080p cai para 25 fps.
- Removido o `opencv-python` (duplicava o `cv2` do `opencv-contrib-python` que o MediaPipe exige).
- `cv2` define `QT_QPA_PLATFORM_PLUGIN_PATH`; mesmo assim o PySide6 sobe em `wayland`. Remover a
  variável depois de importar o `cv2` por garantia.
- Rótulos Left/Right do MediaPipe se invertem com o espelhamento: a identidade de cada mão vem do
  rastreador por posição, não do rótulo. Confirmar com a câmera ao vivo qual rótulo é qual.
- Desvios e descobertas guiadas pelos dados (todas com teste):
  - duplo clique do vídeo 5 = dois toques a 170–230 ms, cabe nos 400 ms do KDE: cada toque é um
    clique imediato, sem lógica de duplo clique;
  - cursor segue o **nó** do indicador (quase parado no toque), não a ponta;
  - rolagem no modelo "puxar" (só enquanto os dois dedos dobram); vídeo 13 rola para a esquerda;
  - "L" definido pelo ângulo polegar×indicador ≥ 45°. O "L" do vídeo 7 assenta em ~33° (igual a
    apontar) e **não expande**; o guia pede o polegar bem aberto;
  - fechar janela: o vídeo 9 só tomba ~100 ms (a regra pede 300 ms), então não fecha; o começo do
    tapa é igual a uma varredura, que troca de área. Se o fechar confirmar até 1 s depois de uma
    varredura, a troca é desfeita antes de fechar;
  - mão na borda não inicia fechar nem arrastar (mão saindo do quadro parecia tombo);
  - arraste só depois de a mão fechada ficar parada 200 ms, ter sido vista aberta antes e com
    tamanho estável (fechar e abrir a mão deslocam o centro aparente da palma).

### 2026-10-18 — T5 a T10, revisão de código
- Interface PySide6 rodando no Wayland com a câmera real (modo demonstração): 30 fps, MediaPipe
  ~9 ms, captura→ação ~9 ms. Geometria das telas do Qt = a do KWin.
- `/code-review` (esforço alto) achou 10 problemas; todos corrigidos com teste antes:
  câmera travada deixava botão preso (agora o reconhecedor recebe quadros vazios e solta);
  "desfazer troca de área" só no mesmo episódio de mão aberta e até 700 ms (antes podia fechar a
  janela da área errada); toque não clica durante arraste/Alt+Tab; Tab nunca sai sem Alt;
  toque reassenta a base (o vídeo 5 passou de 9 cliques com fantasma para exatamente 8);
  zoom não sequestra arraste (mão ocupada ou poses formadas com mais de 1,5 s de diferença);
  espelhar virou só visualização; Esc só pausa; cursor em float; campos mortos removidos.
- `/security-review` não rodado (sem merge nesta etapa). Superfície: `uinput` e `busctl` com
  argumentos fixos, sem entrada externa.

### Aberto
- Ver a saída agindo de verdade: `python -m controle.diagnostico` e o guia de testes, com o Arthur.
- Confirmar no uso real: sentido da rolagem (modelo "puxar"), "L" do vídeo 7 (polegar pouco
  aberto não expande) e o tapa de fechar com a palma segurada ~0,3 s.
- Nada commitado (aguardando pedido).

## Iteração 2 (2026-10-18) — spec: seção "Iteração 2"

- [x] **I1 — Gravação de sessão**: gravador (npz no formato das fixtures + rótulo) e controles no
      menu. `gravacoes/` fora do git.
- [x] **I2 — Bloqueio durante o arraste** no reconhecedor.
- [x] **I3 — Cursor relativo com aceleração** + embreagem; modo absoluto opcional.
- [x] **I4 — Poses novas**: três dedos, polegar para baixo; medida polegar–médio.
- [x] **I5 — Clique por pinça rápida** (esquerdo: polegar–indicador; direito: polegar–médio).
- [x] **I6 — Rolagem joystick** (+ inverter).
- [x] **I7 — Alt+Tab com três dedos** (Tab / Shift+Tab por degrau).
- [x] **I8 — Fechar com polegar para baixo segurado** + anel de contagem.
- [x] **I9 — Troca de área com rearme só depois de parar**; remover tapa, piparote, toque e o
      "desfazer".
- [x] **I10 — Matriz revisada**: vídeos antigos como teste de falso positivo; legenda, README e
      guia atualizados.
- [x] **I11 — Calibração com gravações do Arthur** (depende das gravações).

### 2026-10-18 — Iteração 2 implementada (223 testes passando)
- I1–I10 fechadas. Matriz revisada: os vídeos dos gestos antigos (toque, piparote, tapa, curl)
  viraram teste de falso positivo; o v06 passou a gerar arraste (punho parado que anda, coerente
  com o desenho novo).
- `/code-review` da iteração 2: 10 achados, todos corrigidos com teste (duplo clique com a 2ª pinça
  rápida, corrida ao salvar gravação, bloqueio do arraste no nível das máquinas, arraste com o ganho
  do cursor relativo, rajada no joystick, arrancada rápida do cursor, clique volta à posição de
  antes da pinça, rearme da varredura, salvar em thread, limpeza).
- Ao vivo (Wayland, câmera real, modo demonstração): 30 fps, captura→ação ~9 ms.

### Aberto
- **I11**: calibrar com as gravações do Arthur (clique, clique direito, três dedos, polegar para
  baixo, rolagem, cursor, troca de área, livre). Limiares dos gestos novos ainda são estimados.
- Saída real (cursor/atalhos) só verificada pelo Arthur no uso; nada commitado.

### 2026-10-25 — I11 (calibração), primeira rodada (236 testes passando)
- Gravações do Arthur viraram fixtures `tests/fixtures/g_*.npz` (clique, alt_tab, fechar_janela,
  rolagem, cursor, area — a 2ª "cursor" era a sessão de troca de área, gravada com o rótulo errado).
- Feedback: clique bom; rolagem, fechar e troca de área perfeitos; cursor ótimo; clique direito não
  reconhece; Alt+Tab péssimo; zoom impossível de testar.
- **Alt+Tab**: na pose de três dedos do Arthur o mínimo fica meio dobrado (retidão 0,62–0,76); o
  limite antigo (< 0,65) fazia a pose piscar e o seletor abrir/fechar 11× em 20 s. Novo critério:
  indicador, médio e anelar ≥ 0,86 e mínimo < 0,82 (mão aberta dele: 0,92–0,99), checado antes da
  mão aberta. Na gravação: 3 sessões contínuas.
- **Zoom**: a primeira pinça ficava "pronta para arrastar" em 200 ms e isso bloqueava o zoom, que só
  ligava com as duas pinças no mesmo décimo de segundo. Agora só uma mão *arrastando* bloqueia, e
  a segunda pinça pode vir até 3 s depois.
- **Aberto**: clique direito sem gravação (no repouso apontando, o polegar já fica a 0,38–0,64 palma
  do médio; precisa ver como o Arthur faz). Zoom ainda sem gravação ao vivo.

### 2026-10-26 — I11, segunda rodada (248 testes passando)
- Novas fixtures: g_clique_direito, g_zoom_1..3, g_alt_tab_2. Feedback: clique direito ~70%, zoom
  "identifica mas move o cursor e não aplica", Alt+Tab bom.
- **Clique direito**: o Arthur estica o médio e encosta o polegar na ponta dele (passa por "dois
  dedos"/"?"); o detector só armava com pose estável em indicador. Das 37 tentativas na gravação,
  14 viravam clique (38%). Novo: um detector único de toque do polegar; o dedo mais perto decide
  (indicador = esquerdo, médio = direito); polegar perto dos dois (< 0,40) não clica; arma também a
  partir de "dois dedos". Na gravação: 36 cliques direitos. A gravação de clique de 25/10 tinha 14
  toques claros no médio além dos 13 no indicador (ele já testava o direito ali): agora 13 + 14.
- Joystick: durante e até 500 ms depois de um clique o centro acompanha a mão (soltar o clique
  direito em "dois dedos" fazia rolar).
- **Zoom**: reconhecimento estava certo (blocos de +/− seguindo a mão). Saída: Ctrl (teclado
  virtual) e roda (mouse virtual) iam juntos a cada passo; o KDE pode processar a roda antes do
  Ctrl. Agora há sessão de zoom (ZOOM_INICIO/ZOOM_FIM) com Ctrl segurado do início ao fim; durante
  a sessão nada mais age e, depois, cada mão precisa mudar de pose. Religa até 2 s depois ao
  reajustar uma das mãos. **Não verificado ao vivo** (precisa do Arthur olhando o zoom acontecer).
- **Expandir** exige mão fechada ≥ 250 ms: a pinça rápida de clique seguida do polegar aberto
  (o "apontar" dele às vezes fica a 45–52°, que conta como L) maximizava a janela.
- **Validado ao vivo pelo Arthur em 2026-10-26** ("funcionando"): zoom aplicando e clique direito.
  I11 fechada. Pendente: commit (nada versionado ainda).
