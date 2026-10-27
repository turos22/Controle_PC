"""Detecta o sistema e monta a entrada (mouse/teclado) e as ações de janela adequadas."""
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass

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


def criar_saida(ambiente: Ambiente, demonstracao: bool = False,
                entrada_linux: Callable[[], Entrada] | None = None) -> Saida:
    """`entrada_linux` substitui a criação dos dispositivos uinput (testes)."""
    if demonstracao:
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True)
    if ambiente.sistema != "linux":
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True,
                     aviso=f"{ambiente.sistema}: ainda sem suporte para agir no sistema. "
                           "Rodando em modo demonstração.")
    from controle.plataforma import linux  # só no Linux: depende de evdev

    try:
        entrada = (entrada_linux or linux.EntradaUinput)()
    except OSError as erro:
        return Saida(EntradaNula(), AcoesNulas(), demonstracao=True,
                     aviso=f"Sem acesso a /dev/uinput ({erro}). Rodando em modo demonstração.")
    if ambiente.area_de_trabalho == "kde":
        return Saida(entrada, linux.AcoesKWin(), demonstracao=False)
    return Saida(entrada, AcoesNulas(), demonstracao=False,
                 aviso=f"Ações de janela ainda não suportadas em {ambiente.area_de_trabalho or 'este ambiente'}"
                       " (só no KDE). Mouse, cliques, rolagem e zoom funcionam.")
