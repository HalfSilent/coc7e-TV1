"""
engine/grid/tiles.py — Carregador e cache de sprites tile para o grid.

Usa dois grupos de assets (ambos CC0):
  - DENZI CC0 individual sprites (32×32): floor/ wall/ features/
  - Kenney Retro Textures (PNG tileable): floor_wood_planks, wall_brick_stone…

Cada localização define um *tema* que mapeia para um conjunto de sprites.
Os sprites são escalados lazy para CELL×CELL e cacheados por (path, cell).

Uso:
    loader = TileLoader(tema="biblioteca", cell=40)
    surf   = loader.get_floor(col, linha)   # varia por posição
    surf   = loader.get_wall(col, linha)
    surf   = loader.get_objeto()
    surf   = loader.get_saida()
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import pygame

# ══════════════════════════════════════════════════════════════
# CAMINHOS BASE
# ══════════════════════════════════════════════════════════════

# tela_masmorra.py está em CoCGame/masmorra/ — o projeto raiz é CoCGame/
# engine/grid/tiles.py está em CoCGame/engine/grid/
_GAME_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ASSETS   = os.path.normpath(os.path.join(_GAME_DIR, "..", "Assets"))

_DENZI  = os.path.join(
    _ASSETS,
    "DENZI_CC0_individual_organized_tiles_sprites",
    "DENZI_CC0_individual_organized_tiles_sprites",
)
_KENNEY = os.path.join(_ASSETS, "kenney_retro-textures-1", "PNG")


def _dp(*sub) -> str:
    """Constrói caminho dentro da pasta DENZI."""
    return os.path.join(_DENZI, *sub)


def _kp(nome: str) -> str:
    """Constrói caminho dentro da pasta Kenney."""
    return os.path.join(_KENNEY, nome)


# ══════════════════════════════════════════════════════════════
# CATÁLOGO DE TEMAS
# ══════════════════════════════════════════════════════════════
# Cada tema tem listas de caminhos para floor/wall/objeto/saida.
# Variantes de floor/wall são distribuídas deterministicamente por posição.

_TEMAS: Dict[str, Dict[str, list]] = {

    "catacumbas": {
        "floor": [
            _dp("floor", "cobblestone", f"floor_cobblestone_{c}.png")
            for c in "abcdefgh"
        ],
        "wall": [
            _dp("wall", "brick", "style 1", f"wall_brick1_{c}.png")
            for c in "abcde"
        ],
        "objeto": [
            _dp("features", "sarcophagus", "features_sarcophagus_a.png"),
            _dp("features", "sarcophagus", "features_sarcophagus_b.png"),
        ],
        "saida": [_kp("door_wood.png")],
    },

    "biblioteca": {
        "floor": [
            _kp("floor_wood_planks.png"),
            _kp("floor_wood_planks_wide.png"),
            _kp("floor_wood_planks_depth.png"),
        ],
        "wall": [
            _kp("wall_brick_stone_center.png"),
            _kp("wall_brick_stone_center_depth.png"),
        ],
        "objeto": [
            _kp("wall_brick_stone_center_depth.png"),   # estante de livros
            _kp("wall_brick_small_stone_depth.png"),
        ],
        "saida": [_kp("door_wood.png")],
    },

    "hospital": {
        "floor": [
            _kp("floor_tiles_blue_small.png"),
            _kp("floor_stone_pattern_small.png"),
        ],
        "wall": [
            _kp("wall_brick_small_stone.png"),
            _kp("wall_brick_small_stone_depth.png"),
        ],
        "objeto": [
            _kp("wall_brick_small_stone_depth.png"),   # cama/armário
        ],
        "saida": [_kp("door_metal_gate.png")],
    },

    "delegacia": {
        "floor": [
            _kp("floor_stone_pattern.png"),
            _kp("floor_stone_pattern_small.png"),
        ],
        "wall": [
            _kp("wall_brick_stone_center.png"),
            _kp("wall_brick_stone_both.png"),
        ],
        "objeto": [
            _kp("wall_brick_stone_center_depth.png"),  # arquivo/mesa
        ],
        "saida": [_kp("door_wood.png")],
    },

    "porto": {
        "floor": [
            _dp("floor", "cinder", f"floor_cinder_{c}.png")
            for c in "abcde"
        ],
        "wall": [
            _kp("wall_brick_sand_center.png"),
            _kp("wall_brick_sand_center_depth.png"),
        ],
        "objeto": [
            _kp("wall_timber.png"),                    # caixote/barril
            _kp("timber_square_planks.png"),
        ],
        "saida": [_kp("door_wood_handle.png")],
    },

    "mansao": {
        "floor": [
            _kp("floor_wood_planks.png"),
            _kp("floor_wood_planks_damaged.png"),
        ],
        "wall": [
            _kp("wall_timber.png"),
            _kp("wall_timber_structure.png"),
            _kp("wall_timber_structure_cross.png"),
        ],
        "objeto": [
            _kp("timber_square_planks_cross.png"),     # móvel/armário
            _kp("wall_timber_structure_diagonal.png"),
        ],
        "saida": [_kp("door_wood_handle.png")],
    },

    "cemiterio": {
        "floor": [
            _kp("floor_ground_dirt.png"),
            _kp("floor_stone.png"),
        ],
        "wall": [
            _kp("wall_rock.png"),
            _kp("wall_rock_structure.png"),
        ],
        "objeto": [
            _kp("wall_rock_structure.png"),            # lápide/altar
        ],
        "saida": [_kp("door_metal_gate.png")],
    },

    "universidade": {
        "floor": [
            _kp("floor_stone_pattern.png"),
            _kp("floor_tiles_tan_small.png"),
        ],
        "wall": [
            _kp("wall_brick_stone_center.png"),
            _kp("wall_brick_sand_center.png"),
        ],
        "objeto": [
            _kp("wall_brick_stone_center_depth.png"),  # estante/vitrine
        ],
        "saida": [_kp("door_wood.png")],
    },
}

# Tema padrão = catacumbas
_TEMAS["padrao"] = _TEMAS["catacumbas"]


# ══════════════════════════════════════════════════════════════
# TILE LOADER
# ══════════════════════════════════════════════════════════════

class TileLoader:
    """
    Carrega, escala e cacheia sprites para o grid de exploração.

    Params:
        tema   — nome do tema ("biblioteca", "porto", "catacumbas", …)
        cell   — tamanho alvo em pixels (padrão 40 = CELL da masmorra)
    """

    def __init__(self, tema: str = "padrao", cell: int = 40):
        self.tema  = tema if tema in _TEMAS else "padrao"
        self.cell  = cell
        self._cache: Dict[str, Optional[pygame.Surface]] = {}

    # ── API pública ────────────────────────────────────────────

    def get_floor(self, col: int = 0, linha: int = 0) -> Optional[pygame.Surface]:
        """Sprite de chão — varia deterministicamente por posição."""
        paths = _TEMAS[self.tema]["floor"]
        idx   = (col * 7 + linha * 13) % len(paths)
        return self._load(paths[idx])

    def get_wall(self, col: int = 0, linha: int = 0) -> Optional[pygame.Surface]:
        """Sprite de parede — varia deterministicamente por posição."""
        paths = _TEMAS[self.tema]["wall"]
        idx   = (col * 5 + linha * 11) % len(paths)
        return self._load(paths[idx])

    def get_objeto(self, col: int = 0, linha: int = 0) -> Optional[pygame.Surface]:
        """Sprite de objeto interativo (estante, caixa, altar…)."""
        paths = _TEMAS[self.tema]["objeto"]
        idx   = (col * 3 + linha * 7) % len(paths)
        return self._load(paths[idx])

    def get_saida(self) -> Optional[pygame.Surface]:
        """Sprite de saída/porta."""
        paths = _TEMAS[self.tema].get("saida", [])
        return self._load(paths[0]) if paths else None

    def tem_sprites(self) -> bool:
        """Retorna True se ao menos um sprite de chão carregou com sucesso."""
        paths = _TEMAS[self.tema]["floor"]
        return self._load(paths[0]) is not None

    # ── Internos ───────────────────────────────────────────────

    def _load(self, path: str) -> Optional[pygame.Surface]:
        """Carrega, escala e cacheia o sprite. Retorna None se falhar."""
        key = f"{path}@{self.cell}"
        if key in self._cache:
            return self._cache[key]

        if not pygame.get_init():
            self._cache[key] = None
            return None

        try:
            raw    = pygame.image.load(path).convert_alpha()
            scaled = pygame.transform.scale(raw, (self.cell, self.cell))
            self._cache[key] = scaled
            return scaled
        except Exception:
            # Arquivo não encontrado ou erro de decodificação — usa fallback rect
            self._cache[key] = None
            return None
