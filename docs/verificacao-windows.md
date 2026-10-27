# Verificação no Windows (M10)

O código do Windows foi escrito e testado com substitutos no Linux. Nada disso prova que funciona no
Windows de verdade: este roteiro é a prova. Faça na ordem; pare no primeiro item que falhar e me mande a
saída do terminal.

## 1. Instalar

```powershell
git clone <repositório> ; cd cv-controle-do-pc
git checkout gestos-iteracao-2
py -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

Anote: a versão do Windows, `py --version` e se o `pip` achou o `mediapipe`. Se não achou, instale o
Python 3.12 e refaça.

## 2. Testes automáticos (incluem dois que só rodam no Windows)

```powershell
.venv\Scripts\pytest
```

Esperado: tudo passa; `test_tamanho_da_estrutura_input_no_windows` e `test_envio_real_de_um_movimento_no_windows`
**não** aparecem como ignorados. Se o primeiro falhar, a estrutura do `SendInput` está errada
(`controle/plataforma/windows.py`). O segundo move o mouse para o centro da tela.

## 3. Diagnóstico da saída (não clica nem digita)

```powershell
.venv\Scripts\python -m controle.diagnostico
```

O ponteiro deve passar pelo centro e pelos quatro cantos de **cada** tela, e a visão geral
(Win+Tab) deve abrir e fechar. Veja principalmente: telas com escala diferente (100 % e 150 %) e a segunda
tela em posições estranhas.

## 4. Programa, em modo demonstração

```powershell
.venv\Scripts\controle-por-gestos --demonstracao
```

A câmera abre? Quantos fps aparecem na barra inferior? Se não abrir, tente `--camera 1`.
Na primeira abertura aparece a pergunta de calibração: faça a calibração e veja se o resultado mostra
"Acerto … → …" e aplica.

## 5. Programa de verdade, gesto por gesto

```powershell
.venv\Scripts\controle-por-gestos
```

Use o roteiro de [guia-de-testes.md](guia-de-testes.md) e preencha:

| Gesto | Ação esperada no Windows | Funcionou? | Observação |
|---|---|---|---|
| Mover o cursor | ponteiro acompanha, nas duas telas | | |
| Clique / duplo clique / direito | clique esquerdo, duplo, menu de contexto | | |
| Segurar e arrastar | arrasta uma janela pela barra de título | | |
| Rolar | rola uma página do navegador nos 4 sentidos | | |
| Expandir (L) | Win+↑: maximiza a janela | | |
| Visão geral | Win+Tab abre a Visão de Tarefas | | |
| Trocar de área | Ctrl+Win+←/→: muda de área de trabalho virtual (crie 2 antes) | | |
| Alternar janelas | Alt+Tab mostra o seletor, desliza e escolhe | | |
| Fechar janela | Alt+F4 fecha a janela ativa (**use uma janela sem nada importante**) | | |
| Zoom | Ctrl + roda dá zoom no navegador | | |

## 6. O que me mandar

- Saída do terminal de cada etapa que falhou (copie o texto).
- Versão do Windows, do Python e do `mediapipe` (`.venv\Scripts\pip list`).
- Se a câmera é interna ou USB, e os fps medidos.

## Limites conhecidos

- Janelas de programas abertos como administrador não recebem a entrada (isolamento do Windows).
- Win+Tab pode precisar de um instante para abrir; o gesto de visão geral dispara uma vez.
- Se você mudou os atalhos do Windows, ajuste `controle/plataforma/atalhos.py`.
