"""
engine/renderer.py — Renderizador isométrico para CoC 7e.

Usa os assets Kenney Isometric Miniature Dungeon (256×512 px por tile).
A projeção segue o mesmo padrão de projecao_iso.py já existente no projeto.

Tamanhos reais dos PNGs Kenney (medidos):
    Tile base:  256×512 px  — mas o losango visível ocupa ~256×128 px no topo
    Sprites:    256×512 px  — personagem ocupa a metade inferior

Dimensões lógicas adotadas (escala 1/4):
    TILE_W = 64   (largura do losango visível)
    TILE_H = 32   (altura do losango visível)
    Escala de blit: 0.25× do original
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import pygame

from engine.mundo import Mundo, TipoTile, EfeitoAmbiental, Cobertura
from engine.entidade import Entidade, Direcao

# ── Paths ──────────────────────────────────────────────────────────────
_RAIZ_PROJETO = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
_DUNGEON_ISO  = os.path.join(_RAIZ_PROJETO, "Assets",
                              "kenney_isometric-miniature-dungeon", "Isometric")
_DUNGEON_CHAR = os.path.join(_RAIZ_PROJETO, "Assets",
                              "kenney_isometric-miniature-dungeon",
                              "Characters", "Male")

# ── Dimensões lógicas do tile (após escala) ────────────────────────────
# Os PNGs Kenney têm 256×512. Aplicamos ESCALA = 0.25 → 64×128.
# O losango visível do chão ocupa os primeiros ~128px (metade vertical),
# depois de escalar: 64×64, mas o losango em si tem 64px de largura e 32px
# de altura (razão 2:1 isométrica padrão).
ESCALA   = 0.25
TILE_W   = 64    # largura do losango após escala
TILE_H   = 32    # altura do losango após escala (metade da largura)

# Offset vertical para alinhar o losango do tile com a grade:
# O tile PNG Kenney tem o losango no CENTRO-TOPO da imagem escalada.
# Empiricamente: blit em (sx - TILE_W//2, sy - TILE_H//2 - 32)
TILE_OFFSET_Y = -16   # ajuste fino de alinhamento vertical


# ══════════════════════════════════════════════════════════════
# CACHE DE SURFACES
# ══════════════════════════════════════════════════════════════

_cache_tiles:   Dict[str, pygame.Surface] = {}
_cache_sprites: Dict[str, pygame.Surface] = {}


def _carregar_tile(nome_arquivo: str) -> Optional[pygame.Surface]:
    """Carrega e escala tile isométrico do dungeon pack."""
    if nome_arquivo in _cache_tiles:
        return _cache_tiles[nome_arquivo]
    caminho = os.path.join(_DUNGEON_ISO, nome_arquivo)
    if not os.path.exists(caminho):
        return None
    surf = pygame.image.load(caminho).convert_alpha()
    w = int(surf.get_width()  * ESCALA)
    h = int(surf.get_height() * ESCALA)
    surf = pygame.transform.scale(surf, (w, h))
    _cache_tiles[nome_arquivo] = surf
    return surf


def _carregar_sprite(nome_arquivo: str) -> Optional[pygame.Surface]:
    """Carrega e escala sprite de personagem."""
    if nome_arquivo in _cache_sprites:
        return _cache_sprites[nome_arquivo]
    caminho = os.path.join(_DUNGEON_CHAR, nome_arquivo)
    if not os.path.exists(caminho):
        return None
    surf = pygame.image.load(caminho).convert_alpha()
    w = int(surf.get_width()  * ESCALA)
    h = int(surf.get_height() * ESCALA)
    surf = pygame.transform.scale(surf, (w, h))
    _cache_sprites[nome_arquivo] = surf
    return surf


# ══════════════════════════════════════════════════════════════
# MAPEAMENTO: TipoTile → nome de arquivo
# ══════════════════════════════════════════════════════════════

_TILE_ARQUIVO: Dict[TipoTile, str] = {
    TipoTile.CHAO:    "stoneTile_S.png",
    TipoTile.PAREDE:  "stoneWall_S.png",   # fallback; _escolher_tile_parede() é usado normalmente
    TipoTile.ELEVADO: "woodenCrate_S.png",  # caixa de madeira = cobertura/obstáculo
    TipoTile.VAZIO:   "",
}

# Sufixos de direção para sprites de personagem
_DIR_SUFIXO: Dict[Direcao, int] = {
    Direcao.SE: 0,
    Direcao.SO: 2,
    Direcao.NE: 4,
    Direcao.NO: 6,
}


# ══════════════════════════════════════════════════════════════
# PROJEÇÃO ISO ↔ TELA
# ══════════════════════════════════════════════════════════════

def grid_para_tela(col: float, linha: float,
                   cam_x: float = 0, cam_y: float = 0) -> Tuple[int, int]:
    """Centro do tile na tela."""
    x = int((col - linha) * (TILE_W // 2) - cam_x)
    y = int((col + linha) * (TILE_H // 2) - cam_y)
    return x, y


def tela_para_grid(sx: int, sy: int,
                   cam_x: float = 0, cam_y: float = 0) -> Tuple[int, int]:
    """Converte posição de pixel na tela para coordenada de grid."""
    rx = sx + cam_x
    ry = sy + cam_y
    col  = int((rx / (TILE_W // 2) + ry / (TILE_H // 2)) / 2)
    linha = int((ry / (TILE_H // 2) - rx / (TILE_W // 2)) / 2)
    return col, linha


# ══════════════════════════════════════════════════════════════
# RENDERER PRINCIPAL
# ══════════════════════════════════════════════════════════════

class Renderer:
    def __init__(self, tela: pygame.Surface, largura: int, altura: int):
        self.tela    = tela
        self.largura = largura
        self.altura  = altura

        # Offset para centralizar mapa na tela
        self.offset_x = largura  // 2
        self.offset_y = altura   // 4

        # Câmera (float para suavidade)
        self.cam_x: float = 0.0
        self.cam_y: float = 0.0

        # Surface de highlight (reutilizada a cada frame)
        self._hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

        # Placeholder gerado em código (fallback sem PNG)
        self._placeholder_chao   = self._gerar_tile_placeholder((55, 50, 45), (80, 72, 60))
        self._placeholder_parede = self._gerar_tile_placeholder((40, 36, 32), (70, 60, 50), altura_3d=24)
        self._placeholder_elev   = self._gerar_tile_placeholder((50, 44, 38), (75, 65, 55), altura_3d=12)

    # ── Placeholders ──────────────────────────────────────────

    def _gerar_tile_placeholder(self, cor_topo, cor_borda,
                                 altura_3d: int = 0) -> pygame.Surface:
        """Tile losango colorido para uso quando o PNG não é encontrado."""
        h = TILE_H + altura_3d
        surf = pygame.Surface((TILE_W, h), pygame.SRCALPHA)
        pts_topo = [
            (TILE_W // 2, 0),
            (TILE_W,      TILE_H // 2),
            (TILE_W // 2, TILE_H),
            (0,           TILE_H // 2),
        ]
        pygame.draw.polygon(surf, cor_topo,  pts_topo)
        pygame.draw.polygon(surf, cor_borda, pts_topo, 1)
        if altura_3d > 0:
            pts_esq = [
                (0,           TILE_H // 2),
                (TILE_W // 2, TILE_H),
                (TILE_W // 2, TILE_H + altura_3d),
                (0,           TILE_H // 2 + altura_3d),
            ]
            pts_dir = [
                (TILE_W,      TILE_H // 2),
                (TILE_W // 2, TILE_H),
                (TILE_W // 2, TILE_H + altura_3d),
                (TILE_W,      TILE_H // 2 + altura_3d),
            ]
            esc = tuple(max(0, c - 20) for c in cor_topo)
            esc2 = tuple(max(0, c - 10) for c in cor_topo)
            pygame.draw.polygon(surf, esc,  pts_esq)
            pygame.draw.polygon(surf, esc2, pts_dir)
        return surf

    # ── Seleção direcional de parede ─────────────────────────

    def _escolher_tile_parede(self, cel, mundo: "Mundo") -> str:
        """
        Seleciona o sprite de parede correto analisando os vizinhos:
          Sul  (linha+1) passável → face S visível   → stoneWall_S
          Este (col+1)  passável → face E visível   → stoneWall_E
          Norte(linha-1) passável → face N visível  → stoneWall_N
          Oeste(col-1)  passável → face O visível   → stoneWall_W
          Sul+Este juntos         → stoneWallCorner_S (canto NW da sala)
          Norte+Oeste juntos      → stoneWallCorner_N (canto SE)
          Sem vizinho passável    → stoneWallTop_S  (pilar isolado)
        """
        c, l = cel.col, cel.linha

        def passavel(dc: int, dl: int) -> bool:
            v = mundo.celula(c + dc, l + dl)
            return v is not None and not v.bloqueada

        sul   = passavel(0, +1)
        este  = passavel(+1, 0)
        norte = passavel(0, -1)
        oeste = passavel(-1, 0)

        if sul and este:    return "stoneWallCorner_S.png"
        if norte and oeste: return "stoneWallCorner_N.png"
        if sul:             return "stoneWall_S.png"
        if este:            return "stoneWall_E.png"
        if norte:           return "stoneWall_N.png"
        if oeste:           return "stoneWall_W.png"
        return "stoneWallTop_S.png"

    # ── Blit de tile ──────────────────────────────────────────

    def _blit_tile(self, surf: pygame.Surface, col: float, linha: float,
                   offset_y_extra: int = 0):
        """Blit centralizado no ponto isométrico da célula."""
        cx, cy = grid_para_tela(col, linha, self.cam_x, self.cam_y)
        cx += self.offset_x
        cy += self.offset_y + TILE_OFFSET_Y + offset_y_extra
        # Alinha pelo centro horizontal e pela base do losango
        x = cx - surf.get_width()  // 2
        y = cy - surf.get_height() + TILE_H // 2
        self.tela.blit(surf, (x, y))

    # ── Renderização do mapa ──────────────────────────────────

    def renderizar_mapa(self, mundo: Mundo):
        """
        Painter's algorithm: renderiza linha por linha, col por col,
        do canto NW para SE, para garantir ordenação de profundidade correta.
        """
        for l in range(mundo.linhas):
            for c in range(mundo.colunas):
                cel = mundo.celula(c, l)
                if cel is None or cel.tipo == TipoTile.VAZIO:
                    continue
                self._renderizar_celula(cel, mundo)

    def _renderizar_celula(self, cel, mundo: "Mundo"):
        if cel.tipo == TipoTile.PAREDE:
            arquivo = self._escolher_tile_parede(cel, mundo)
        else:
            arquivo = _TILE_ARQUIVO.get(cel.tipo, "")
        surf = _carregar_tile(arquivo) if arquivo else None

        if surf is None:
            # fallback para placeholder colorido
            if cel.tipo == TipoTile.PAREDE:
                surf = self._placeholder_parede
            elif cel.tipo == TipoTile.ELEVADO:
                surf = self._placeholder_elev
            else:
                surf = self._placeholder_chao

        self._blit_tile(surf, cel.col, cel.linha)

    # ── Efeitos ambientais ────────────────────────────────────

    _COR_EFEITO = {
        EfeitoAmbiental.OLEO:      (20,  18,  15,  140),
        EfeitoAmbiental.FOGO:      (220, 100, 20,  160),
        EfeitoAmbiental.NEVOA:     (160, 165, 200, 110),
        EfeitoAmbiental.ARBUSTO:   (35,  110, 35,  120),
        EfeitoAmbiental.AGUA_BENTA:(60,  130, 220, 100),
        EfeitoAmbiental.SANGUE:    (160, 20,  20,  130),
    }

    def renderizar_efeitos(self, mundo: Mundo):
        """Overlay colorido semitransparente para cada efeito ambiental."""
        pts_losango = [
            (TILE_W // 2, 0),
            (TILE_W,      TILE_H // 2),
            (TILE_W // 2, TILE_H),
            (0,           TILE_H // 2),
        ]
        for row in mundo.grid:
            for cel in row:
                cor = self._COR_EFEITO.get(cel.efeito)
                if not cor:
                    continue
                cx, cy = grid_para_tela(cel.col, cel.linha,
                                        self.cam_x, self.cam_y)
                cx += self.offset_x
                cy += self.offset_y + TILE_OFFSET_Y
                sx = cx - TILE_W // 2
                sy = cy - TILE_H // 2

                self._hl.fill((0, 0, 0, 0))
                pygame.draw.polygon(self._hl, cor, pts_losango)
                self.tela.blit(self._hl, (sx, sy))

    # ── Highlights de combate ─────────────────────────────────

    def renderizar_highlights(self, celulas: List[Tuple[int, int]],
                               cor: Tuple):
        pts = [
            (TILE_W // 2, 0),
            (TILE_W,      TILE_H // 2),
            (TILE_W // 2, TILE_H),
            (0,           TILE_H // 2),
        ]
        for (hc, hl) in celulas:
            cx, cy = grid_para_tela(hc, hl, self.cam_x, self.cam_y)
            cx += self.offset_x
            cy += self.offset_y + TILE_OFFSET_Y
            sx = cx - TILE_W // 2
            sy = cy - TILE_H // 2
            self._hl.fill((0, 0, 0, 0))
            pygame.draw.polygon(self._hl, cor, pts)
            # borda mais sólida
            pygame.draw.polygon(self._hl, (*cor[:3], 220), pts, 1)
            self.tela.blit(self._hl, (sx, sy))

    # ── Entidades ─────────────────────────────────────────────

    def renderizar_entidade(self, ent: Entidade):
        """
        Renderiza sprite Kenney da entidade. Se não houver sprite carregado,
        usa um losango colorido como placeholder.
        """
        sprite = self._obter_sprite_entidade(ent)
        cx, cy = grid_para_tela(ent.col, ent.linha, self.cam_x, self.cam_y)
        cx += self.offset_x
        cy += self.offset_y + TILE_OFFSET_Y

        if sprite:
            # Posiciona pela base do sprite no centro do tile
            x = cx - sprite.get_width()  // 2
            y = cy - sprite.get_height() + TILE_H // 2
            self.tela.blit(sprite, (x, y))
        else:
            # Placeholder: losango colorido pequeno
            pts = [
                (cx,      cy - 18),
                (cx + 10, cy - 8),
                (cx,      cy + 2),
                (cx - 10, cy - 8),
            ]
            pygame.draw.polygon(self.tela, ent.cor, pts)
            pygame.draw.polygon(self.tela, (255, 255, 255, 180), pts, 1)

    def _obter_sprite_entidade(self, ent: Entidade) -> Optional[pygame.Surface]:
        """Retorna sprite atual da entidade (idle ou run, frame atual)."""
        skin_id = getattr(ent, 'skin_id', 0)
        if ent.movendo:
            nome = f"Male_{skin_id}_Run{ent.frame_atual % 10}.png"
        else:
            nome = f"Male_{skin_id}_Idle0.png"
        return _carregar_sprite(nome)

    # ── Câmera ────────────────────────────────────────────────

    def seguir_entidade(self, ent: Entidade, suavidade: float = 0.08):
        """
        Lerp suave da câmera para centralizar a entidade na tela.

        A posição isométrica "crua" da entidade (sem câmera) é:
            iso_x = (col - linha) * (TILE_W // 2)
            iso_y = (col + linha) * (TILE_H // 2)
        Para que isso apareça no centro da tela, a câmera precisa ser:
            cam_x = iso_x          (offset_x já centraliza horizontalmente)
            cam_y = iso_y - altura//4  (offset_y=altura//4, queremos centro vertical)
        """
        iso_x = (ent.col - ent.linha) * (TILE_W // 2)
        iso_y = (ent.col + ent.linha) * (TILE_H // 2)
        alvo_cam_x = iso_x
        alvo_cam_y = iso_y - self.altura // 4
        self.cam_x += (alvo_cam_x - self.cam_x) * suavidade
        self.cam_y += (alvo_cam_y - self.cam_y) * suavidade

    # ── Barra de HP / SAN sobre entidade ─────────────────────

    def renderizar_barra_status(self, ent: Entidade,
                                 fonte: Optional[pygame.font.Font] = None):
        cx, cy = grid_para_tela(ent.col, ent.linha, self.cam_x, self.cam_y)
        cx += self.offset_x
        cy += self.offset_y + TILE_OFFSET_Y - 28

        # HP
        hp_pct = ent.hp / max(1, ent.hp_max)
        bw, bh = 36, 4
        pygame.draw.rect(self.tela, (60, 20, 20),
                         (cx - bw // 2, cy, bw, bh))
        pygame.draw.rect(self.tela, (200, 60, 60),
                         (cx - bw // 2, cy, int(bw * hp_pct), bh))

        # SAN (se tiver sanidade)
        if hasattr(ent, 'san_max') and ent.san_max > 0:
            san_pct = ent.sanidade / max(1, ent.san_max)
            pygame.draw.rect(self.tela, (20, 20, 60),
                             (cx - bw // 2, cy + bh + 1, bw, bh))
            pygame.draw.rect(self.tela, (60, 90, 200),
                             (cx - bw // 2, cy + bh + 1, int(bw * san_pct), bh))
