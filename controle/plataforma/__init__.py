"""Detecta o sistema e monta a entrada (mouse/teclado) e as ações de janela adequadas."""
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from controle.idioma import tr
from controle.plataforma.atalhos import ATALHOS_GNOME, ATALHOS_MACOS, ATALHOS_WINDOWS, AcoesPorAtalho
from controle.plataforma.base import AcoesJanela, AcoesNulas, Entrada, EntradaNula


@dataclass(frozen=True)
class Ambiente:
    sistema: str                    # "linux" | "windows" | "macos" | "outro"
    area_de_trabalho: str | None    # Linux: "kde", "gnome" ou o nome que o sistema informar
    sessao: str | None              # Linux: "wayland" | "x11"


@dataclass
class Saida:
    entrada: Entrada
    acoes: AcoesJanela
    demonstracao: bool              # True: nada age no sistema
    aviso: str | None = None        # o que a pessoa precisa saber (falta de permissão, suporte parcial)


def detectar(plataforma: str = sys.platform, ambiente: Mapping[str, str] = os.environ) -> Ambiente:
    if plataforma.startswith("linux"):
        partes = [p.lower() for p in ambiente.get("XDG_CURRENT_DESKTOP", "").split(":") if p]
        area = next((a for a in ("kde", "gnome") if a in partes), partes[0] if partes else None)
        return Ambiente("linux", area, ambiente.get("XDG_SESSION_TYPE") or None)
    sistema = {"win32": "windows", "darwin": "macos"}.get(plataforma, "outro")
    return Ambiente(sistema, None, None)


def _fabrica_padrao(sistema: str) -> Callable[[], Entrada]:
    """Importa só o backend do sistema atual: cada um depende de uma biblioteca diferente."""
    if sistema == "linux":
        from controle.plataforma.linux import EntradaUinput
        return EntradaUinput
    if sistema == "windows":
        from controle.plataforma.windows import EntradaWindows
        return EntradaWindows
    from controle.plataforma.macos import EntradaMacos
    return EntradaMacos


def _acoes(ambiente: Ambiente, entrada: Entrada) -> tuple[AcoesJanela, str | None]:
    """As ações de janela do ambiente e, se faltar suporte, o aviso."""
    if ambiente.sistema == "windows":
        return AcoesPorAtalho(entrada, ATALHOS_WINDOWS), None
    if ambiente.sistema == "macos":
        return AcoesPorAtalho(entrada, ATALHOS_MACOS), None
    if ambiente.area_de_trabalho == "kde":
        from controle.plataforma.linux import AcoesKWin
        return AcoesKWin(), None
    if ambiente.area_de_trabalho == "gnome":
        return AcoesPorAtalho(entrada, ATALHOS_GNOME), None
    return AcoesNulas(), tr("Ações de janela ainda não suportadas em {ambiente} (só KDE e GNOME). "
                            "Mouse, cliques, rolagem e zoom funcionam.",
                            ambiente=ambiente.area_de_trabalho or tr("este ambiente"))


def criar_saida(ambiente: Ambiente, demonstracao: bool = False,
                fabrica_entrada: Callable[[], Entrada] | None = None,
                acessibilidade_liberada: Callable[[], bool] | None = None) -> Saida:
    """`fabrica_entrada` e `acessibilidade_liberada` substituem o que é do sistema real (testes)."""
    if demonstracao:
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True)
    if ambiente.sistema not in ("linux", "windows", "macos"):
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True,
                     aviso=tr("{sistema}: ainda sem suporte para agir no sistema. Rodando em modo demonstração.",
                              sistema=ambiente.sistema))
    try:
        entrada = (fabrica_entrada or _fabrica_padrao(ambiente.sistema))()
    except (OSError, ImportError) as erro:
        aviso = (tr("Sem acesso a /dev/uinput ({erro}). Rodando em modo demonstração.", erro=erro)
                 if ambiente.sistema == "linux"
                 else tr("Sem acesso à entrada do sistema ({erro}). Rodando em modo demonstração.", erro=erro))
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True, aviso=aviso)
    acoes, aviso = _acoes(ambiente, entrada)
    if ambiente.sistema == "macos":
        if acessibilidade_liberada is None:
            from controle.plataforma.macos import acessibilidade_liberada
        if not acessibilidade_liberada():
            aviso = tr("Falta a permissão de Acessibilidade: libere este programa em Ajustes do Sistema → "
                       "Privacidade e Segurança → Acessibilidade e abra de novo.")
    return Saida(entrada, acoes, demonstracao=False, aviso=aviso)
