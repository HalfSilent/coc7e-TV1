"""
gerenciador_assets.py — Gerenciador centralizado de assets do projeto.

Baixa automaticamente as fontes tipográficas necessárias (Google Fonts,
licença OFL/Apache 2.0) e fornece uma API unificada para carregar fontes
pygame com cache em memória.

Fontes disponíveis (estilos):
    "titulo"    → SpecialElite-Regular    (máquina de escrever, anos 1920)
    "hud"       → VT323-Regular           (pixel retro, legível em tamanhos pequenos)
    "narrativa" → IMFellEnglish-Regular   (gótica atmosférica, texto corrido)
    "mono"      → LiberationMono-Regular  (monospace — fallback de sistema)

API pública:
    garantir_fontes()               → baixa fontes ausentes (chame uma vez no boot)
    get_font(estilo, tamanho)       → pygame.font.Font (cacheado em memória)
    fonte_path(estilo)              → str — caminho absoluto do .ttf
    pre_aquecer(estilos_sizes)      → aquece o cache de fontes antes da tela principal
"""

from __future__ import annotations

import os
import sys
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple

# ── Diretório de fontes ────────────────────────────────────────────────────────
_RAIZ       = os.path.dirname(os.path.abspath(__file__))
FONTES_DIR  = os.path.join(_RAIZ, "assets", "fontes")

# ── Registro de fontes ─────────────────────────────────────────────────────────
# (nome_arquivo, url_download, timeout_s)
_REGISTRO: Dict[str, Tuple[str, Optional[str]]] = {
    "titulo": (
        "SpecialElite-Regular.ttf",
        "https://github.com/google/fonts/raw/main/apache/specialelite/SpecialElite-Regular.ttf",
    ),
    "hud": (
        "VT323-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/vt323/VT323-Regular.ttf",
    ),
    "narrativa": (
        "CrimsonText-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/crimsontext/CrimsonText-Regular.ttf",
    ),
    "mono": (
        "LiberationMono-Regular.ttf",
        None,  # buscamos no sistema; sem download
    ),
}

# ── Caminhos de sistema onde o LiberationMono pode estar ──────────────────────
_LIBERATION_CANDIDATES = [
    "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
]

# ── Cache em memória: (estilo, tamanho) → pygame.font.Font ───────────────────
_cache: Dict[Tuple[str, int], object] = {}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════

def _liberation_path() -> Optional[str]:
    """Tenta encontrar LiberationMono no sistema."""
    for p in _LIBERATION_CANDIDATES:
        if os.path.isfile(p):
            return p
    # tenta fc-list se disponível
    try:
        import subprocess
        out = subprocess.check_output(
            ["fc-list", ":family=Liberation Mono:style=Regular", "--format=%{file}\n"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()
        for linha in out.splitlines():
            if os.path.isfile(linha):
                return linha
    except Exception:
        pass
    return None


def _download(url: str, destino: str, timeout: int = 15) -> bool:
    """Baixa url para destino. Retorna True em sucesso."""
    try:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        headers = {"User-Agent": "Mozilla/5.0 TTRPG-FontFetcher/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp, \
             open(destino, "wb") as fh:
            fh.write(resp.read())
        return True
    except Exception as exc:
        print(f"[assets] AVISO: falha ao baixar {url}: {exc}", file=sys.stderr)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ══════════════════════════════════════════════════════════════════════════════

def fonte_path(estilo: str) -> Optional[str]:
    """
    Retorna o caminho absoluto do .ttf para o estilo solicitado,
    ou None se não encontrado.
    Ordem: assets/fontes/ → sistema (apenas 'mono').
    """
    estilo = estilo if estilo in _REGISTRO else "hud"
    nome_arquivo, _ = _REGISTRO[estilo]

    # 1. Em assets/fontes/ (baixadas)
    caminho_local = os.path.join(FONTES_DIR, nome_arquivo)
    if os.path.isfile(caminho_local):
        return caminho_local

    # 2. Para 'mono', tenta localização no sistema
    if estilo == "mono":
        return _liberation_path()

    return None


def garantir_fontes(verbose: bool = True) -> Dict[str, bool]:
    """
    Verifica cada fonte e baixa as ausentes.

    Retorna dict {estilo: True/False} indicando se cada fonte ficou disponível.
    A fonte 'mono' nunca é baixada — usa o sistema.
    Chame esta função uma vez no boot, antes de pygame.init() ou logo depois.
    """
    os.makedirs(FONTES_DIR, exist_ok=True)
    resultado: Dict[str, bool] = {}

    for estilo, (nome_arquivo, url) in _REGISTRO.items():
        caminho_local = os.path.join(FONTES_DIR, nome_arquivo)

        # Mono — busca no sistema, não baixa
        if estilo == "mono":
            resultado[estilo] = _liberation_path() is not None or True  # SysFont existe sempre
            continue

        # Já existe localmente?
        if os.path.isfile(caminho_local):
            resultado[estilo] = True
            continue

        # Tenta baixar
        if url:
            if verbose:
                print(f"[assets] Baixando fonte '{estilo}': {nome_arquivo} ...", flush=True)
            ok = _download(url, caminho_local)
            if ok and verbose:
                print(f"[assets] ✓ {nome_arquivo} salva em assets/fontes/")
            resultado[estilo] = ok
        else:
            resultado[estilo] = False

    return resultado


def get_font(estilo: str = "hud", tamanho: int = 16) -> "pygame.font.Font":
    """
    Retorna um pygame.font.Font para o estilo e tamanho dados.

    O resultado é cacheado em memória — chamadas repetidas com os mesmos
    argumentos não recarregam o arquivo .ttf.

    Fallback em cascata:
        1. assets/fontes/{arquivo}.ttf
        2. Sistema (LiberationMono, para 'mono')
        3. pygame.font.SysFont("monospace", tamanho)
    """
    chave = (estilo, tamanho)
    if chave in _cache:
        return _cache[chave]  # type: ignore[return-value]

    import pygame  # import local: pode ser chamado antes de pygame.init()

    caminho = fonte_path(estilo)
    try:
        if caminho:
            f = pygame.font.Font(caminho, tamanho)
        else:
            f = pygame.font.SysFont("monospace", tamanho)
    except Exception:
        f = pygame.font.SysFont("monospace", tamanho)

    _cache[chave] = f
    return f  # type: ignore[return-value]


def pre_aquecer(estilos_sizes: list) -> None:
    """
    Aquece o cache de fontes antes da tela principal para evitar
    engasgos durante o jogo.

    Exemplo:
        pre_aquecer([("titulo", 46), ("hud", 14), ("narrativa", 17)])
    """
    for estilo, tamanho in estilos_sizes:
        get_font(estilo, tamanho)


def limpar_cache() -> None:
    """Descarta o cache em memória (raramente necessário)."""
    _cache.clear()


# ── Quando executado diretamente: verifica/baixa fontes ───────────────────────
if __name__ == "__main__":
    print("=== gerenciador_assets — Verificação de fontes ===")
    resultado = garantir_fontes(verbose=True)
    print()
    for est, ok in resultado.items():
        status = "✓ OK" if ok else "✗ FALHA"
        path   = fonte_path(est) or "(fallback SysFont)"
        print(f"  [{status}] {est:12s} → {path}")
