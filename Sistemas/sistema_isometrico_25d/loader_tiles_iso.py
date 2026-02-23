"""
loader_tiles_iso.py — Carrega tiles isométricos Kenney para o CoCGame.

Mapeia os tile IDs do jogo (mirrors de mundo_aberto.T) para os arquivos
PNG do pack Kenney, armazenando pygame.Surface com metadados de renderização.

Hierarquia de pastas esperada (relativa ao workspace TTRPG/):
    Assets/kenney_isometric-roads/png/
    Assets/kenney_isometric-roads-water/png/
    Assets/kenney_isometric-buildings-1/PNG/

API pública:
    inicializar(assets_base: str | Path | None) -> None
        Deve ser chamado UMA VEZ após pygame.init(). Define o caminho base.

    get_tile(tile_id: int) -> TileInfo
        Retorna TileInfo com surface e metadados (lazy-load + cache).

    pre_carregar() -> None
        Pré-carrega todos os tiles em memória (evita stutter no primeiro frame).

    tile_tipo(tile_id: int) -> str
        "chao", "objeto" ou "vazio".

Tipos de tile:
    "chao"   — tile plano de chão (100×65 ou 100×58px).
               Renderizado na camada base. offset_y = 0.
    "objeto" — tile alto (edifício, parede, árvore).
               Renderizado centralizado no mesmo (col,row).
               offset_y = ISO_H_BASE - tile_h  (normalmente negativo).
    "vazio"  — tile 0 (vazio/escuridão), pode ser ignorado na renderização.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── IDs espelhados de mundo_aberto.T ──────────────────────────────────
T_VAZIO    = 0
T_GRAMA    = 1
T_CALCADA  = 2
T_RUA      = 3
T_PAREDE   = 4
T_EDIFICIO = 5
T_AGUA     = 6
T_TERRA    = 7
T_PORTA    = 8
T_ARVORE   = 9
T_LAMPIAO  = 10
T_ESCADA   = 11

# ── Dimensão base do losango isométrico (Kenney roads) ────────────────
ISO_H_BASE = 65   # altura total do tile de chão (inclui face frontal)

# ── Caminho base dos Assets (definido em inicializar()) ───────────────
_ASSETS_BASE: Path = Path(__file__).parent.parent / "Assets"

# ── Cache de TileInfo ─────────────────────────────────────────────────
_CACHE: dict[int, "TileInfo"] = {}

# ── Indicador de inicialização ────────────────────────────────────────
_INICIALIZADO = False


# ════════════════════════════════════════════════════════════════════
#  Estrutura de dados do tile
# ════════════════════════════════════════════════════════════════════

@dataclass
class TileInfo:
    """
    Metadados de um tile isométrico carregado.

    Attributes:
        tile_id:   ID numérico do tile (T_* constantes acima).
        surface:   pygame.Surface pronta para blit.
        w:         largura em pixels.
        h:         altura em pixels.
        tipo:      "chao", "objeto" ou "vazio".
        offset_x:  deslocamento horizontal de blit em relação a sx.
                   Alinha o centro do losango do tile com sx + ISO_DX.
        offset_y:  deslocamento vertical de blit em relação a sy.
                   Alinha o equador do losango do tile com sy + ISO_DY.
        nome:      nome legível para debug.
    """
    tile_id:  int
    surface:  "pygame.Surface"
    w:        int
    h:        int
    tipo:     str          # "chao" | "objeto" | "vazio"
    offset_x: int = 0
    offset_y: int = 0
    nome:     str = ""


# ════════════════════════════════════════════════════════════════════
#  Mapeamento tile_id → arquivo PNG
# ════════════════════════════════════════════════════════════════════

# Subpastas (relativas a _ASSETS_BASE)
_ROADS    = Path("kenney_isometric-roads") / "png"
_WATER    = Path("kenney_isometric-roads-water") / "png"
_BUILDS   = Path("kenney_isometric-buildings-1") / "PNG"

# Offsets medidos pixel a pixel nos PNGs Kenney (ISO_DX=50, ISO_DY=24)
# Fórmula: offset_x = ISO_DX - top_cx
#          offset_y = ISO_DY - eq_y - top_y
# Onde: top_cx = x do vértice topo, eq_y = y do equador (lado dir/esq), top_y = padding topo
#
#  (caminho_relativo, tipo, offset_x, offset_y)
#
#  grass/road/beach 100×65: top_cx=49, eq_y=24, top_y=0  → ox=+1, oy= 0
#  water/dirt       100×58: top_cx=49, eq_y=25, top_y=0  → ox=+1, oy=-1
#  bld_000/007       99×85: top_cx=49, eq_y=25, top_y=0  → ox=+1, oy=-1
#  bld_001          133×127: top_cx=66, eq_y=59, top_y=0 → ox=-16,oy=-35
#  bld_086          100×55: top_cx=49, eq_y=25, top_y=1  → ox=+1, oy=-2
#  treeTall          12×41: top_cx=5,  eq_y=3,  top_y=0  → ox=+45,oy=+21
#  bld_078           13×24: top_cx=7,  eq_y=3,  top_y=1  → ox=+43,oy=+20
_MAPA_ARQUIVO: dict[int, tuple[Path, str, int, int]] = {
    # ── Chão plano ────────────────────────────────────────────────
    T_VAZIO:    (_ROADS  / "grassWhole.png",        "vazio",  +1,   0),
    T_GRAMA:    (_ROADS  / "grass.png",             "chao",   +1,   0),
    T_CALCADA:  (_ROADS  / "beach.png",             "chao",   +1,   0),
    T_RUA:      (_ROADS  / "road.png",              "chao",   +1,   0),
    T_TERRA:    (_ROADS  / "dirt.png",              "chao",   +1,  -1),
    T_AGUA:     (_ROADS  / "water.png",             "chao",   +1,  -1),
    # ── Objetos altos (edifícios / paredes) ───────────────────────
    T_PAREDE:   (_BUILDS / "buildingTiles_000.png", "objeto", +1,  -1),
    T_EDIFICIO: (_BUILDS / "buildingTiles_001.png", "objeto", -16, -35),
    T_PORTA:    (_BUILDS / "buildingTiles_007.png", "objeto", +1,  -1),
    T_ESCADA:   (_BUILDS / "buildingTiles_086.png", "chao",   +1,  -2),
    # ── Decorações (objetos pequenos sobre chão) ──────────────────
    T_ARVORE:   (_ROADS  / "treeTall.png",          "objeto", +45, +21),
    T_LAMPIAO:  (_BUILDS / "buildingTiles_078.png", "objeto", +43, +20),
}

# Nomes para debug
_NOMES: dict[int, str] = {
    T_VAZIO:    "Vazio",
    T_GRAMA:    "Grama",
    T_CALCADA:  "Calçada",
    T_RUA:      "Rua",
    T_PAREDE:   "Parede",
    T_EDIFICIO: "Edifício",
    T_AGUA:     "Água",
    T_TERRA:    "Terra",
    T_PORTA:    "Porta",
    T_ARVORE:   "Árvore",
    T_LAMPIAO:  "Lampião",
    T_ESCADA:   "Escada",
}


# ════════════════════════════════════════════════════════════════════
#  Funções internas
# ════════════════════════════════════════════════════════════════════

def _surface_fallback(tile_id: int, w: int = 100, h: int = 65) -> "pygame.Surface":
    """
    Cria uma surface de fallback com cor sólida quando o arquivo PNG
    não é encontrado.  Desenha uma grade isométrica simples em cima.
    """
    import pygame

    COR: dict[int, tuple[int, int, int]] = {
        T_VAZIO:    (10,  14,  28),
        T_GRAMA:    (40,  90,  40),
        T_CALCADA:  (160, 148, 128),
        T_RUA:      (70,  60,  50),
        T_PAREDE:   (148, 70,  50),
        T_EDIFICIO: (180, 160, 130),
        T_AGUA:     (20,  70,  140),
        T_TERRA:    (100, 70,  45),
        T_PORTA:    (100, 60,  30),
        T_ARVORE:   (30,  100, 30),
        T_LAMPIAO:  (200, 190, 80),
        T_ESCADA:   (120, 100, 80),
    }
    cor = COR.get(tile_id, (128, 128, 128))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((*cor, 200))

    # Esboço do losango isométrico
    cx = w // 2
    pts_losango = [
        (cx,         2),
        (w - 2,      h // 3),
        (cx,         h - 2),
        (2,          h // 3),
    ]
    pygame.draw.polygon(surf, (*cor, 255), pts_losango)
    pygame.draw.polygon(surf, (255, 255, 255, 60), pts_losango, 1)
    return surf


def _carregar_tile(tile_id: int) -> TileInfo:
    """Carrega um tile do disco (ou cria fallback) e retorna TileInfo."""
    import pygame

    entrada = _MAPA_ARQUIVO.get(tile_id)
    nome    = _NOMES.get(tile_id, f"tile_{tile_id}")
    tipo    = "chao"
    surf:   Optional["pygame.Surface"] = None
    w = h   = 0

    offset_x = 0
    offset_y = 0

    if entrada is not None:
        caminho_rel, tipo, offset_x, offset_y = entrada
        caminho_abs = _ASSETS_BASE / caminho_rel

        if caminho_abs.exists():
            try:
                surf = pygame.image.load(str(caminho_abs)).convert_alpha()
                w, h = surf.get_size()
            except Exception as exc:
                print(f"[loader_tiles_iso] Erro ao carregar {caminho_abs}: {exc}")
                surf = None

        if surf is None:
            # Fallback — avisa no console apenas uma vez
            print(f"[loader_tiles_iso] Fallback para tile {tile_id} ({nome}) "
                  f"— arquivo não encontrado: {caminho_abs}")
            w, h = (100, 65) if tipo in ("chao", "vazio") else (99, 85)
            surf  = _surface_fallback(tile_id, w, h)
    else:
        # tile_id desconhecido
        w, h = 100, 65
        surf  = _surface_fallback(tile_id, w, h)

    return TileInfo(
        tile_id  = tile_id,
        surface  = surf,
        w        = w,
        h        = h,
        tipo     = tipo,
        offset_x = offset_x,
        offset_y = offset_y,
        nome     = nome,
    )


# ════════════════════════════════════════════════════════════════════
#  API PÚBLICA
# ════════════════════════════════════════════════════════════════════

def inicializar(assets_base: "str | Path | None" = None) -> None:
    """
    Configura o caminho base dos Assets e limpa o cache.
    Deve ser chamado UMA VEZ após pygame.init().

    Args:
        assets_base: caminho para a pasta Assets/ (padrão: ../../Assets/
                     relativo a este arquivo, ou seja, TTRPG/Assets/).
    """
    global _ASSETS_BASE, _INICIALIZADO, _CACHE
    if assets_base is not None:
        _ASSETS_BASE = Path(assets_base)
    _CACHE.clear()
    _INICIALIZADO = True


def get_tile(tile_id: int) -> TileInfo:
    """
    Retorna TileInfo para o tile_id.  Lazy-load + cache em memória.

    Args:
        tile_id: ID do tile (T_VAZIO=0 … T_ESCADA=11).

    Returns:
        TileInfo com surface, dimensões, tipo e offset_y.
    """
    if not _INICIALIZADO:
        raise RuntimeError(
            "loader_tiles_iso não foi inicializado. "
            "Chame inicializar() após pygame.init()."
        )
    if tile_id not in _CACHE:
        _CACHE[tile_id] = _carregar_tile(tile_id)
    return _CACHE[tile_id]


def pre_carregar() -> None:
    """
    Pré-carrega todos os tiles mapeados em _MAPA_ARQUIVO.
    Evita micro-stutters no primeiro frame de cada chunk.
    """
    if not _INICIALIZADO:
        raise RuntimeError("Chame inicializar() antes de pre_carregar().")
    for tid in _MAPA_ARQUIVO:
        get_tile(tid)


def tile_tipo(tile_id: int) -> str:
    """
    Retorna o tipo do tile sem carregar a surface.
    Útil para lógica de colisão e camadas de renderização.

    Returns:
        "chao" | "objeto" | "vazio"
    """
    entrada = _MAPA_ARQUIVO.get(tile_id)
    if entrada is None:
        return "chao"
    return entrada[1]


def listar_todos() -> list[TileInfo]:
    """Retorna lista de TileInfo para todos os tiles mapeados (para debug/preview)."""
    if not _INICIALIZADO:
        raise RuntimeError("Chame inicializar() antes de listar_todos().")
    return [get_tile(tid) for tid in sorted(_MAPA_ARQUIVO)]


# ════════════════════════════════════════════════════════════════════
#  __main__ — preview pygame de todos os tiles
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")
    import pygame

    pygame.init()
    inicializar()
    pre_carregar()

    tiles = listar_todos()
    COLS  = 6
    PAD   = 8
    MAX_W = max(t.w for t in tiles)
    MAX_H = max(t.h for t in tiles)
    ROWS  = (len(tiles) + COLS - 1) // COLS

    sw = COLS * (MAX_W + PAD) + PAD
    sh = ROWS * (MAX_H + PAD + 16) + PAD + 20

    tela  = pygame.display.set_mode((sw, sh))
    pygame.display.set_caption("loader_tiles_iso — Preview")
    font  = pygame.font.SysFont("monospace", 10)
    clock = pygame.time.Clock()

    while True:
        for ev in pygame.event.get():
            if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                pygame.quit()
                raise SystemExit

        tela.fill((15, 15, 25))

        for i, ti in enumerate(tiles):
            col = i % COLS
            row = i // COLS
            x   = PAD + col * (MAX_W + PAD)
            y   = PAD + row * (MAX_H + PAD + 16) + 20

            # Fundo cinza para visualizar transparência
            pygame.draw.rect(tela, (40, 40, 50), (x, y, MAX_W, MAX_H))
            # Blit da surface centralizada na célula
            bx  = x + (MAX_W - ti.w) // 2
            by  = y + (MAX_H - ti.h)
            tela.blit(ti.surface, (bx, by))

            # Legenda
            lbl = font.render(
                f"{ti.tile_id} {ti.nome[:10]} [{ti.tipo[0]}] {ti.w}×{ti.h}",
                True, (200, 190, 170)
            )
            tela.blit(lbl, (x, y + MAX_H + 2))

        pygame.display.flip()
        clock.tick(30)
