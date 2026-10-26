# Guia de testes — controle por gestos (iteração 2)

Roteiro manual, do mais seguro para o mais impactante. Para cada gesto: como fazer, o que deve
acontecer e o que olhar se falhar. No fim, a tabela de registro e o roteiro de **gravação para
calibração**, que é o que mais ajuda a acertar os gestos novos.

**Como ler a tela durante os testes**
- **Legenda (direita):** o card do gesto acende quando ele é reconhecido. O quadro "Agora" mostra
  a pose que o programa está vendo em cada mão.
- **Vídeo:** a pose aparece num rótulo perto da mão. A ação executada aparece num aviso embaixo.
- **Barra inferior:** fps e latência.

Se a pose no "Agora" não for a que você está fazendo, o problema está no reconhecimento da pose:
grave uma sessão desse gesto (seção final).

**Em caso de problema:** `Esc` pausa na hora e solta qualquer botão ou tecla pressionado. Ele só
pausa; para retomar, use `P` ou o botão.

---

## 0. Preparação

1. Feche o OBS e qualquer programa que use a câmera.
2. Rode a suíte automática. Todos os testes devem passar:
   ```bash
   .venv/bin/pytest
   ```
3. Abra o programa:
   ```bash
   .venv/bin/python main.py
   ```
   Para ver os gestos sem agir no sistema, use `--demonstracao`.

## 1. Cursor (relativo, com aceleração)

- **Como:** só o indicador esticado.
  - Mover devagar dá precisão; mover rápido atravessa as duas telas.
  - Para reposicionar a mão, saia da pose (feche ou abra a mão), mude de lugar e aponte de novo. O
    cursor não pula.
- **Ajustes no menu:**
  - mais alcance ou mais rápido: **Velocidade**;
  - tremendo parado: aumente a **Suavização**;
  - atrasado: diminua a **Suavização**.
- **Para voltar ao modo antigo** (posição da mão = posição na tela): desmarque "Relativo, com
  aceleração".

## 2. Clique e duplo clique (pinça rápida)

- **Como:** apontando, encoste o polegar no indicador e solte rápido (menos de ~0,35 s), com a mão
  parada. Duas vezes seguidas fazem o duplo clique.
- **Teste:** clique em ícones e abra uma pasta no Dolphin com duplo clique.
- **Se não clicar:** a pinça demorou, a mão andou, ou você não estava apontando antes. Grave uma
  sessão de "Clique".

## 3. Clique direito

- **Como:** apontando, encoste e solte rápido o polegar no **dedo médio**.
- **Esperado:** abre o menu de contexto.
- **Se sair clique esquerdo:** o polegar pegou no indicador. Grave uma sessão de "Clique direito".

## 4. Segurar e arrastar

- **Como:** feche a pinça, fique parado um instante (~0,2 s) e mova. Abra a mão para soltar.
- **Esperado:** enquanto arrasta, **nenhum outro gesto age**, nem da outra mão.
- **Teste:** arraste um arquivo no Dolphin, ou uma janela pela barra de título.

## 5. Expandir janela e visão geral

Os dois foram aprovados no primeiro teste e não mudaram.
- **Expandir:** mão fechada, abra em L com o polegar bem aberto e segure ~0,3 s.
- **Visão geral:** mão aberta, feche em garra e abra de novo, rápido.

## 6. Rolagem (joystick)

- **Como:** indicador e médio esticados. O ponto onde você formou a pose vira o centro.
  - Afaste a mão do centro para rolar, sem parar.
  - Quanto mais longe, mais rápido. Volte ao centro, ou saia da pose, para parar.

| Mão em relação ao centro | Rola |
|---|---|
| Abaixo | para cima |
| Acima | para baixo |
| À esquerda | para a direita |
| À direita | para a esquerda |

- **Se o sentido estiver ao contrário do que você quer:** marque "Inverter o sentido" no menu.
- **Velocidade:** ajuste em "Velocidade da rolagem".

## 7. Zoom

- **Como:** as duas mãos em **pinça** ao mesmo tempo. Afaste as mãos para aproximar e junte para
  afastar.
- **Teste:** navegador ou visualizador de imagens.

## 8. Alternar janelas (três dedos)

- **Como:** indicador, médio e anelar esticados, com o mindinho dobrado. Isso abre o seletor e já
  passa para a próxima janela.
  - Deslize a mão para a direita para a próxima e para a esquerda para a anterior. Cada ~0,08 da
    largura da imagem é uma janela.
  - Mude a pose para escolher.
- **Se o Alt ficar preso:** `Esc`.

## 9. Trocar de área de trabalho

- **Como:** mão aberta, varra rápido para o lado. Para a esquerda vai para a área da esquerda; para
  a direita, para a da direita.
- **Para trocar de novo:** pare a mão um instante antes de varrer. O movimento de retorno logo
  depois da troca é ignorado de propósito.

## 10. Fechar janela (por último)

Abra uma janela descartável só para isso, como um Kate vazio ou um terminal novo.

- **Como:** polegar para baixo (punho com o polegar esticado apontando para o chão), segurado
  ~0,8 s.
  - Um anel vermelho completa em volta da mão.
  - Mudar a pose antes de completar cancela.
- **Esperado:** a janela em foco fecha. Para fechar outra, espere 2 s.
- **Se o anel não aparecer:** a pose não foi reconhecida (o "Agora" mostra outra coisa). Grave uma
  sessão de "Fechar janela".

## 11. Segurança e controles

| Teste | Esperado |
|---|---|
| `Esc` no meio de um arraste | O botão solta e o aviso "PAUSADO" aparece |
| `Esc` duas vezes | Continua pausado (`Esc` nunca retoma) |
| Desligar um gesto no menu e fazê-lo | O card fica apagado na legenda e nada acontece |
| Tirar a mão do quadro segurando a pinça | Solta em ~0,3 s |
| Desmarcar "Espelhar visualização" | Só a imagem vira; o cursor continua indo para o mesmo lado da mão |
| Tirar a câmera (ou abrir o OBS) segurando a pinça | O botão solta em ~0,3 s mesmo sem imagem |

---

## Gravação para calibração

As gravações guardam só os pontos das mãos, nenhuma imagem, em `gravacoes/` (fora do git). Elas
viram os testes automáticos, do mesmo jeito que os seus vídeos viraram.

1. No menu, em **Gravar sessão**, escolha o gesto e clique em **Gravar**.
2. Faça o gesto umas **8 a 10 vezes**, do seu jeito natural, com pausas de ~1 s entre as
   repetições. Varie um pouco a posição da mão.
3. Clique em **Parar e salvar**. O nome do arquivo aparece embaixo do botão.

**Prioridade** (os gestos novos ainda usam limiares estimados):

| # | Gravar | Por quê |
|---|---|---|
| 1 | Clique e duplo clique | Pinça rápida: calibrar tempo e distância |
| 2 | Clique direito | Polegar no médio: medir como você faz |
| 3 | Alternar janelas | Pose de três dedos: nunca vista em gravação |
| 4 | Fechar janela | Polegar para baixo: nunca vista em gravação |
| 5 | Rolar | Zona morta e velocidade do joystick |
| 6 | Mover o cursor | Movimentos lentos e rápidos, para a curva de aceleração |
| 7 | Trocar de área | Idas e voltas, com e sem parada |
| 8 | Livre | Uso normal por 1 a 2 minutos, para caçar falsos positivos |

Quando terminar, me avise. Eu leio as gravações, ajusto os limiares e transformo tudo em testes.

## Registro

| # | Gesto | Funcionou? | Observação |
|---|---|---|---|
| 1 | Cursor | | |
| 2 | Clique / duplo clique | | |
| 3 | Clique direito | | |
| 4 | Segurar e arrastar | | |
| 5 | Expandir / visão geral | | |
| 6 | Rolagem | | |
| 7 | Zoom | | |
| 8 | Alternar janelas | | |
| 9 | Trocar de área | | |
| 10 | Fechar janela | | |
| 11 | Segurança e controles | | |
