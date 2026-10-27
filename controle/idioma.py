"""Português e inglês: o texto em português é a chave; sem tradução, aparece como está.

Uso: `tr("texto em português")`, ou `tr("Salvo: {nome}", nome=...)` quando há valores. O idioma vale para
a interface montada depois de `definir_idioma`, então a escolha acontece antes de abrir a janela.
"""
import locale

IDIOMAS = ("pt", "en")
_atual = "pt"

# Textos que são iguais nos dois idiomas (siglas, símbolos): dispensam entrada em EN.
IGUAIS = frozenset({"C", "L", "?", "—"})
# Textos montados em tempo de execução que a varredura do código não enxerga.
TEXTOS_DINAMICOS: frozenset[str] = frozenset()

EN = {
    # --- catálogo de gestos ---
    "Mover o cursor": "Move the cursor",
    "Só o indicador esticado. Devagar = preciso, rápido = longe. Para reposicionar a mão, saia da pose, "
    "mude de lugar e aponte de novo.":
        "Index finger only. Slow = precise, fast = far. To reposition your hand, leave the pose, move, "
        "and point again.",
    "Move o ponteiro": "Moves the pointer",
    "Clique e duplo clique": "Click and double click",
    "Apontando, encoste e solte rápido o polegar no indicador. Duas vezes seguidas faz o duplo clique.":
        "While pointing, quickly touch and release your thumb to your index finger. Twice in a row makes a "
        "double click.",
    "Clique esquerdo": "Left click",
    "Clique direito": "Right click",
    "Apontando, encoste e solte rápido o polegar no dedo médio.":
        "While pointing, quickly touch and release your thumb to your middle finger.",
    "Segurar e arrastar": "Hold and drag",
    "Feche a pinça, fique parado um instante e mova. Abra a mão para soltar. Enquanto arrasta, nenhum "
    "outro gesto age.":
        "Close the pinch, hold still for a moment, then move. Open your hand to release. While dragging, "
        "no other gesture acts.",
    "Botão esquerdo pressionado": "Left button held down",
    "Rolar": "Scroll",
    "Indicador e médio esticados: onde formou a pose é o centro. Afaste a mão para rolar (mais longe, "
    "mais rápido); volte ao centro para parar.":
        "Index and middle fingers extended: where you formed the pose is the center. Move your hand away to "
        "scroll (farther = faster); return to the center to stop.",
    "Roda do mouse": "Mouse wheel",
    "Expandir janela": "Maximize window",
    "Mão fechada, depois abra em L com o polegar bem aberto e segure ~0,3 s.":
        "Closed fist, then open into an L with the thumb wide open and hold ~0.3 s.",
    "Maximiza a janela": "Maximizes the window",
    "Visão geral": "Overview",
    "Mão aberta, feche em garra e abra de novo, rápido.": "Open hand, close into a claw and open again, quickly.",
    "Visão geral das janelas": "Window overview",
    "Trocar de área": "Switch desktop",
    "Mão aberta varrendo rápido para o lado. Pare a mão antes de varrer de novo (o retorno não conta).":
        "Open hand sweeping quickly to the side. Stop your hand before sweeping again (the return stroke "
        "does not count).",
    "Área à esquerda / à direita": "Desktop to the left / right",
    "Alternar janelas": "Switch windows",
    "Três dedos esticados (indicador, médio, anelar) abrem o seletor. Deslize para os lados para passar; "
    "mude a pose para escolher.":
        "Three extended fingers (index, middle, ring) open the switcher. Slide sideways to move through; "
        "change the pose to choose.",
    "Alt+Tab": "Alt+Tab",
    "Fechar janela": "Close window",
    "Polegar para baixo, segurado ~0,8 s (o anel na tela completa). Mudar a pose antes cancela.":
        "Thumb down, held ~0.8 s (the ring on screen fills up). Changing the pose before then cancels.",
    "Fecha a janela (Alt+F4)": "Closes the window (Alt+F4)",
    "Zoom": "Zoom",
    "As duas mãos em pinça ao mesmo tempo. Afaste para aproximar, junte para afastar.":
        "Both hands pinching at the same time. Move apart to zoom in, together to zoom out.",
    "Ctrl + roda": "Ctrl + wheel",
    # --- poses ---
    "aberta": "open", "punho": "fist", "pinça": "pinch", "indicador": "index", "dois dedos": "two fingers",
    "três dedos": "three fingers", "polegar p/ baixo": "thumb down",
    "indicador · cursor e clique (pinça)": "index · cursor and click (pinch)",
    "dois dedos · rolagem joystick": "two fingers · joystick scroll",
    "três dedos · Alt+Tab": "three fingers · Alt+Tab",
    "polegar para baixo · fechar janela": "thumb down · close window",
    "pinça · clique, segurar, zoom": "pinch · click, hold, zoom",
    "punho · visão geral, expandir": "fist · overview, maximize",
    "L · expandir": "L · maximize",
    "aberta · área, visão geral, fechar": "open · desktop, overview, close",
    "C · zoom com as duas mãos": "C · two-hand zoom",
    # --- interface ---
    "Aguardando a câmera…": "Waiting for the camera…",
    "cursor": "cursor",
    "zoom": "zoom",
    "Espelhar visualização": "Mirror the preview",
    "Livre (vários gestos)": "Free (several gestures)",
    "●  Gravar": "●  Record",
    "■  Parar e salvar": "■  Stop and save",
    "Grave cada gesto algumas vezes, do jeito que você faz.": "Record each gesture a few times, the way you do it.",
    "Gravando…": "Recording…",
    "Gravando… {quadros} quadros": "Recording… {quadros} frames",
    "Salvando…": "Saving…",
    "Salvo: {nome} ({quadros} quadros)": "Saved: {nome} ({quadros} frames)",
    "Nada gravado.": "Nothing recorded.",
    "Câmera": "Camera",
    "Gravar sessão (calibração)": "Record session (calibration)",
    "Cursor": "Cursor",
    "Relativo, com aceleração": "Relative, with acceleration",
    "Velocidade": "Speed",
    "Suavização": "Smoothing",
    "Região ativa (modo absoluto)": "Active region (absolute mode)",
    "Rolagem": "Scrolling",
    "Velocidade da rolagem": "Scroll speed",
    "Inverter o sentido": "Reverse direction",
    "Exibição": "Display",
    "Mostrar pontos da mão": "Show hand landmarks",
    "Mostrar região ativa (modo absoluto)": "Show active region (absolute mode)",
    "Gestos ligados": "Enabled gestures",
    "Todos": "All",
    "Nenhum": "None",
    "Agora": "Now",
    "Legenda dos gestos": "Gesture legend",
    "Nenhuma mão no quadro": "No hand in view",
    "Mão {ident}": "Hand {ident}",
    "Controle por gestos": "Gesture control",
    "Esc pausa · P pausa/retoma · Ctrl+Q sai": "Esc pauses · P pauses/resumes · Ctrl+Q quits",
    "Modo demonstração: os gestos aparecem, mas não agem no sistema.":
        "Demo mode: gestures show up, but nothing acts on the system.",
    "Iniciando…": "Starting…",
    "▶  Pausado — clique para retomar": "▶  Paused — click to resume",
    "⏸  Gestos ativos — clique para pausar": "⏸  Gestures active — click to pause",
    "gestos {gestos:.1f} ms · captura→ação {total:.1f} ms": "gestures {gestos:.1f} ms · capture→action {total:.1f} ms",
    "pausado": "paused",
    "ativo": "active",
    "Não consegui salvar o perfil em {caminho}: {erro}": "Could not save the profile to {caminho}: {erro}",
    # --- calibração ---
    "Calibração": "Calibration",
    "Calibrar meus gestos": "Calibrate my gestures",
    "Cancelar": "Cancel",
    "Aplicar e salvar": "Apply and save",
    "Passo {n} de {total}": "Step {n} of {total}",
    "Pronto": "Done",
    "Prepare a mão…": "Get your hand ready…",
    "Não vi sua mão. Vamos repetir.": "I could not see your hand. Let's repeat.",
    "Segure a pose…": "Hold the pose…",
    "Calibração concluída": "Calibration complete",
    "Acerto nas suas poses: {antes:.0%} → {depois:.0%}": "Accuracy on your poses: {antes:.0%} → {depois:.0%}",
    "Os padrões já servem para a sua mão; nada precisou mudar.": "The defaults already suit your hand; nothing needed to change.",
    "Calibrar agora": "Calibrate now",
    "Depois": "Later",
    "Primeiro uso": "First use",
    "Quer calibrar os gestos para a sua mão? Leva cerca de 40 segundos. Você pode fazer isso depois, pelo "
    "botão do menu.":
        "Do you want to calibrate the gestures to your hand? It takes about 40 seconds. You can also do it "
        "later, from the menu button.",
    "Mão aberta, dedos afastados, palma para a câmera.": "Open hand, fingers apart, palm facing the camera.",
    "Mão fechada em punho.": "Closed fist.",
    "Só o indicador esticado, como se apontasse.": "Only the index finger extended, as if pointing.",
    "Indicador e médio esticados (um V); os outros dobrados.": "Index and middle fingers extended (a V); the others curled.",
    "Indicador, médio e anelar esticados; mindinho e polegar dobrados.":
        "Index, middle and ring fingers extended; pinky and thumb curled.",
    "Pinça: ponta do polegar encostada na ponta do indicador; os outros dedos dobrados.":
        "Pinch: thumb tip touching index tip; the other fingers curled.",
    "Indicador esticado e polegar bem aberto, formando um L; os outros dobrados.":
        "Index finger extended and thumb wide open, forming an L; the others curled.",
    "{pose}: só {n} amostras (mínimo {minimo}); ignorada": "{pose}: only {n} samples (minimum {minimo}); ignored",
    "dedos esticados e dobrados se confundem; limiares de dedo mantidos":
        "extended and curled fingers overlap; finger thresholds kept",
    "mindinho de três dedos e de mão aberta se confundem; limiar mantido":
        "pinky in three-fingers and in open hand overlap; threshold kept",
    "polegar apontando e em L se confundem; ângulo mantido": "thumb pointing and in L overlap; angle kept",
    "não consegui separar bem as suas poses (ou os limiares novos acertariam menos que os padrões); "
    "mantidos os padrões. Repita a calibração com calma.":
        "I could not tell your poses apart well (or the new thresholds would do worse than the defaults); "
        "defaults kept. Please repeat the calibration calmly.",
    # --- avisos do sistema ---
    "não abriu a câmera {indice} (outro programa usando, como o OBS, ou sem permissão de câmera para "
    "este programa?)":
        "could not open camera {indice} (another program using it, such as OBS, or no camera permission "
        "for this program?)",
    "Ações de janela ainda não suportadas em {ambiente} (só KDE e GNOME). Mouse, cliques, rolagem e zoom funcionam.":
        "Window actions are not supported on {ambiente} yet (KDE and GNOME only). Mouse, clicks, scrolling "
        "and zoom work.",
    "este ambiente": "this environment",
    "{sistema}: ainda sem suporte para agir no sistema. Rodando em modo demonstração.":
        "{sistema}: not supported yet for acting on the system. Running in demo mode.",
    "Sem acesso a /dev/uinput ({erro}). Rodando em modo demonstração.":
        "No access to /dev/uinput ({erro}). Running in demo mode.",
    "Sem acesso à entrada do sistema ({erro}). Rodando em modo demonstração.":
        "No access to the system input ({erro}). Running in demo mode.",
    "Falta a permissão de Acessibilidade: libere este programa em Ajustes do Sistema → Privacidade e "
    "Segurança → Acessibilidade e abra de novo.":
        "Accessibility permission is missing: allow this program in System Settings → Privacy & Security → "
        "Accessibility and open it again.",
}


def definir_idioma(codigo: str):
    global _atual
    if codigo in IDIOMAS:
        _atual = codigo


def idioma_atual() -> str:
    return _atual


def idioma_do_sistema() -> str:
    """Português se o sistema está em português; inglês para o resto."""
    try:
        codigo = locale.getlocale()[0] or ""
    except ValueError:
        codigo = ""
    return "pt" if codigo.lower().startswith("pt") else "en"


def tr(texto: str, **valores) -> str:
    if _atual == "en":
        texto = EN.get(texto, texto)
    return texto.format(**valores) if valores else texto
