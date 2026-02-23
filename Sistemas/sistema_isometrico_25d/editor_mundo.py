"""
editor_mundo.py — Editor visual de chunks para o mundo aberto.
Rio de Janeiro, 1923 — Call of Cthulhu 7e

Modos:
    MAPA   → visão geral dos 8×6 chunks; clique para selecionar e entrar
    CHUNK  → edição tile a tile do chunk selecionado (20×15)

Ferramentas:
    [Q] / LMB        Pincel — pinta o tile selecionado
    [W] / RMB        Apagar — substitui por Vazio
    [E] / MMB        Pegar  — copia o tile sob o cursor
    [F]              Preencher (flood fill)
    [1-9,0]          Atalhos de tile

Navegação (modo CHUNK):
    Setas / WASD     panning
    Scroll           zoom (0.5× – 4×, centralizado no cursor)
    [TAB]            alterna MAPA ↔ CHUNK

Ações:
    [F5]             salva todos os chunks modificados
    [F9]             recarrega o chunk atual do disco
    [G]              regenera o chunk atual com geração procedural
    [ESC]            salva e volta ao menu
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from enum import Enum, auto
from typing import Optional

import numpy as np
import pygame

import gerenciador_mundos as _gm
import gerenciador_assets as _ga
import projecao_iso as _iso
import loader_tiles_iso as _ltiso

# ── Caminhos ──────────────────────────────────────────────────────────
_RAIZ = os.path.dirname(os.path.abspath(__file__))
_UI   = os.path.join(_RAIZ, "ui")
_CAMP = os.path.join(_RAIZ, "Campanhas", "Degraus para o Abismo")
_MENU = os.path.join(_UI, "menu_pygame.py")

for _p in (_RAIZ, _UI, _CAMP):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Importa motor de chunks ────────────────────────────────────────────
from mundo_aberto import (
    T,
    CHUNK_W, CHUNK_H, MUNDO_W, MUNDO_H, TILE_W, TILE_H,
    Chunk, _gerar_chunk, _CHUNKS,
    COR_TILE, BLOQUEIO, make_tile_surface,
)

# ── Carregamento dinâmico de tileset ─────────────────────────────────

def _carregar_tileset(meta: dict) -> tuple[dict, bool]:
    """
    Carrega o tileset descrito em meta['tileset'] (caminho relativo à raiz
    do projeto).  Retorna (surfaces_dict, ok).
    """
    ts_path = meta.get("tileset", "")
    if not ts_path:
        return {}, False
    ts_abs = os.path.join(_RAIZ, ts_path)
    if not os.path.isfile(ts_abs):
        print(f"[editor_mundo] Tileset não encontrado: {ts_abs}")
        return {}, False
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_tileset_mod", ts_abs)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)   # type: ignore[union-attr]
        return mod.carregar_surfaces(), True
    except Exception as e:
        print(f"[editor_mundo] Tileset não carregado: {e}")
        return {}, False

# ── Constantes de layout ───────────────────────────────────────────────
W,    H     = 1440, 900
PANEL_W     = 260       # painel lateral direito
AREA_W      = W - PANEL_W
AREA_H      = H
FPS         = 60

# Tamanho de cada chunk na visão geral (modo MAPA)
CBOX_W = 88
CBOX_H = 66

# Cores
C_FUNDO  = ( 10,  14,  28)
C_PAINEL = ( 18,  26,  50)
C_BORDA  = ( 45,  65, 105)
C_OURO   = (212, 168,  67)
C_TEXTO  = (238, 226, 220)
C_DIM    = (100,  90,  85)
C_ACENTO = (233,  69,  96)
C_VERDE  = ( 78, 204, 163)
C_SEL    = (255, 215,  55)
C_GRADE  = ( 28,  36,  60)
C_TITULO = ( 22,  32,  65)

def _f(size: int, estilo: str = "hud") -> pygame.font.Font:
    return _ga.get_font(estilo, size)


# ── Modo e ferramentas ─────────────────────────────────────────────────
class Modo(Enum):
    MAPA  = auto()
    CHUNK = auto()


class Ferr(Enum):
    PINCEL    = auto()
    APAGAR    = auto()
    PEGAR     = auto()
    PREENCHER = auto()


_FERR_LABEL = {
    Ferr.PINCEL:    "Pincel    [Q]",
    Ferr.APAGAR:    "Apagar    [W]",
    Ferr.PEGAR:     "Pegar     [E]",
    Ferr.PREENCHER: "Preencher [F]",
}

# Paleta de tiles (id, nome_display, tecla)
PALETA: list[tuple[int, str, str]] = [
    (int(T.GRAMA),    "Grama",    "1"),
    (int(T.CALCADA),  "Calçada",  "2"),
    (int(T.RUA),      "Rua",      "3"),
    (int(T.TERRA),    "Terra",    "4"),
    (int(T.AGUA),     "Água",     "5"),
    (int(T.PAREDE),   "Parede",   "6"),
    (int(T.EDIFICIO), "Edifício", "7"),
    (int(T.PORTA),    "Porta",    "8"),
    (int(T.ARVORE),   "Árvore",   "9"),
    (int(T.LAMPIAO),  "Lampião",  "0"),
    (int(T.ESCADA),   "Escada",   "-"),
    (int(T.VAZIO),    "Vazio",    "="),
]

_KEY_TO_TILE = {
    pygame.K_1: int(T.GRAMA),
    pygame.K_2: int(T.CALCADA),
    pygame.K_3: int(T.RUA),
    pygame.K_4: int(T.TERRA),
    pygame.K_5: int(T.AGUA),
    pygame.K_6: int(T.PAREDE),
    pygame.K_7: int(T.EDIFICIO),
    pygame.K_8: int(T.PORTA),
    pygame.K_9: int(T.ARVORE),
    pygame.K_0: int(T.LAMPIAO),
    pygame.K_MINUS:  int(T.ESCADA),
    pygame.K_EQUALS: int(T.VAZIO),
}


# ══════════════════════════════════════════════════════════════════════
#  SELETOR DE MUNDO
# ══════════════════════════════════════════════════════════════════════

class SeletorMundo:
    """Tela inicial: seleciona qual mundo abrir no editor."""

    def __init__(self, tela: pygame.Surface, clock: pygame.time.Clock):
        self.tela  = tela
        self.clock = clock
        self.fn_ui  = _f(14)
        self.fn_big = _f(22)
        self.fn_sm  = _f(11)

        self.mundos:       list[str]          = _gm.listar()
        self.sel_idx:      int                = 0
        self._item_rects:  list[pygame.Rect]  = []

    def executar(self) -> Optional[str]:
        """Roda o loop e retorna o id do mundo selecionado, ou None (sair)."""
        while True:
            self.clock.tick(60)
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.mundos:
                            return self.mundos[self.sel_idx]
                    elif event.key == pygame.K_UP:
                        self.sel_idx = (self.sel_idx - 1) % max(1, len(self.mundos))
                    elif event.key == pygame.K_DOWN:
                        self.sel_idx = (self.sel_idx + 1) % max(1, len(self.mundos))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(self._item_rects):
                        if r.collidepoint(mx, my):
                            if i == self.sel_idx:
                                return self.mundos[i]
                            self.sel_idx = i

            self._render(mx, my)
            pygame.display.flip()

    def _render(self, mx: int, my: int):
        self.tela.fill(C_FUNDO)

        # Cabeçalho
        tit = self.fn_big.render(
            "\u25a0  Editor de Mundo \u2014 Selecione um mundo", True, C_OURO)
        self.tela.blit(tit, tit.get_rect(centerx=W // 2, y=38))
        pygame.draw.line(self.tela, C_BORDA, (60, 82), (W - 60, 82), 1)

        self._item_rects = []

        if not self.mundos:
            msg  = self.fn_ui.render(
                "Nenhum mundo encontrado em  Mundos/", True, C_ACENTO)
            dica = self.fn_sm.render(
                "Use  gerenciador_mundos.criar(id, ...)  para criar um novo mundo.",
                True, C_DIM)
            self.tela.blit(msg,  msg.get_rect(centerx=W // 2, y=H // 2 - 24))
            self.tela.blit(dica, dica.get_rect(centerx=W // 2, y=H // 2 + 10))
            d2 = self.fn_sm.render("[ESC] sair", True, C_DIM)
            self.tela.blit(d2, d2.get_rect(centerx=W // 2, y=H - 35))
            return

        y = 106
        for i, id_mundo in enumerate(self.mundos):
            try:
                meta = _gm.carregar(id_mundo)
                nome = meta.get("nome",     id_mundo)
                camp = meta.get("campanha", "")
                lw   = meta["largura"]
                lh   = meta["altura"]
                nb   = len(meta.get("bairros", {}))
            except Exception:
                nome, camp, lw, lh, nb = id_mundo, "", "?", "?", 0

            sel    = (i == self.sel_idx)
            bg_col = (22, 40, 78)  if sel else (14, 22, 44)
            bd_col = C_SEL         if sel else C_BORDA
            bd_sz  = 2             if sel else 1

            r = pygame.Rect(W // 2 - 320, y, 640, 72)
            self._item_rects.append(r)
            pygame.draw.rect(self.tela, bg_col, r, border_radius=6)
            pygame.draw.rect(self.tela, bd_col, r, bd_sz, border_radius=6)

            s_id   = self.fn_sm.render(f"[{id_mundo}]",                     True, C_DIM)
            s_nome = self.fn_ui.render(nome,                                 True, C_SEL if sel else C_OURO)
            s_camp = self.fn_sm.render(camp,                                 True, C_DIM)
            s_info = self.fn_sm.render(
                f"{lw}\u00d7{lh} chunks  \u00b7  {nb} bairros",
                True, C_VERDE if sel else C_DIM)

            self.tela.blit(s_id,   (r.x + 14, r.y +  6))
            self.tela.blit(s_nome, (r.x + 14, r.y + 24))
            self.tela.blit(s_camp, (r.x + 14 + s_nome.get_width() + 10, r.y + 28))
            self.tela.blit(s_info, (r.x + 14, r.y + 50))

            y += 84

        dica = self.fn_sm.render(
            "\u2191\u2193 navegar  |  Enter selecionar  |  ESC sair", True, C_DIM)
        self.tela.blit(dica, dica.get_rect(centerx=W // 2, y=H - 30))


# ══════════════════════════════════════════════════════════════════════
#  EDITOR
# ══════════════════════════════════════════════════════════════════════

class EditorMundo:
    def __init__(self, tela: pygame.Surface, clock: pygame.time.Clock,
                 mundo_id: str = "Rio1923"):
        self.tela  = tela
        self.clock = clock

        # Mundo selecionado — carrega meta e aponta Chunk.carregar/salvar
        # para o diretório correto via mundo_aberto._CHUNKS
        self._mundo_id    = mundo_id
        self._mundo_meta  = _gm.carregar(mundo_id)
        self._mundo_paths = _gm.paths(self._mundo_meta)

        import mundo_aberto as _ma
        _ma._CHUNKS = self._mundo_paths["chunks"]
        os.makedirs(_ma._CHUNKS, exist_ok=True)

        self.modo      = Modo.MAPA
        self.ferr      = Ferr.PINCEL
        self.tile_sel  = int(T.CALCADA)
        self.sel_cx    = 0
        self.sel_cy    = 0

        # Câmera (modo CHUNK)
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.zoom  = 1.5

        # Todos os chunks carregados/gerados
        self.chunks: dict[tuple[int, int], Chunk] = {}
        self._carregar_todos()

        # Tileset (carregado do path definido em mundo.json["tileset"])
        ts, ok = _carregar_tileset(self._mundo_meta)
        self.tileset: dict[int, pygame.Surface] = (
            ts if ok else self._tileset_fallback()
        )

        # Caches
        self._scaled_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._thumb_cache:  dict[tuple[int, int], pygame.Surface] = {}

        # Fontes
        self.fn_sm  = _f(10)
        self.fn_ui  = _f(12)
        self.fn_hud = _f(13)
        self.fn_big = _f(17)

        # Estado de pintura
        self._pintando   = False
        self._ultimo: Optional[tuple[int, int]] = None

        # Mensagem temporária
        self._msg   = ""
        self._msg_t = 0

        # Rects clicáveis do painel (populados durante draw)
        self._pal_rects: list[tuple[pygame.Rect, int]] = []
        self._ferr_rects: list[tuple[pygame.Rect, Ferr]] = []

    # ── Carregamento ──────────────────────────────────────────────────

    def _carregar_todos(self):
        for cy in range(MUNDO_H):
            for cx in range(MUNDO_W):
                c = Chunk.carregar(cx, cy)
                if c is None:
                    c = _gerar_chunk(cx, cy)
                    c.salvar()
                self.chunks[(cx, cy)] = c

    def _tileset_fallback(self) -> dict[int, pygame.Surface]:
        """Usa tiles isométricos Kenney do loader como tileset do editor."""
        return {int(tid): _ltiso.get_tile(int(tid)).surface for tid in COR_TILE}

    # ── Cache de tiles escalados ──────────────────────────────────────

    def _scaled_tile(self, tid: int, tz: int) -> pygame.Surface:
        key = (tid, tz)
        if key not in self._scaled_cache:
            src = self.tileset.get(int(tid))
            if src:
                self._scaled_cache[key] = pygame.transform.scale(src, (tz, tz))
            else:
                self._scaled_cache[key] = pygame.transform.scale(
                    make_tile_surface(int(tid)), (tz, tz)
                )
        return self._scaled_cache[key]

    def _thumb_chunk(self, cx: int, cy: int) -> pygame.Surface:
        """Miniatura do chunk para a visão geral (4px por tile)."""
        key = (cx, cy)
        c   = self.chunks.get(key)
        if c is None:
            s = pygame.Surface((CHUNK_W * 4, CHUNK_H * 4))
            s.fill(C_FUNDO)
            return s
        if key in self._thumb_cache and not c.modificado:
            return self._thumb_cache[key]

        s = pygame.Surface((CHUNK_W * 4, CHUNK_H * 4))
        for ty in range(CHUNK_H):
            for tx in range(CHUNK_W):
                tid = int(c.dados[ty, tx])
                cor = COR_TILE.get(tid, (80, 80, 80))
                s.fill(cor, (tx * 4, ty * 4, 4, 4))
        self._thumb_cache[key] = s
        return s

    def _inval_chunk(self, cx: int, cy: int):
        """Invalida caches do chunk."""
        self._thumb_cache.pop((cx, cy), None)
        # Limpa scaled cache inteiro (zoom pode mudar)
        # Só tiles do chunk alterado seriam relevantes,
        # mas o cache é pequeno — resetar completo é seguro.

    # ── Coordenadas ───────────────────────────────────────────────────

    def _tile_em_mouse(self, mx: int, my: int) -> tuple[int, int]:
        """Converte posição de mouse (já ajustada pela topbar) em (col, row) iso."""
        if mx >= AREA_W:
            return -1, -1
        dx = _iso.ISO_DX * self.zoom
        dy = _iso.ISO_DY * self.zoom
        rx = mx + self.cam_x
        ry = my + self.cam_y
        col = round((rx / dx + ry / dy) / 2)
        row = round((ry / dy - rx / dx) / 2)
        return int(col), int(row)

    def _chunk_em_mouse(self, mx: int, my: int) -> tuple[int, int]:
        total_w = MUNDO_W * CBOX_W
        total_h = MUNDO_H * CBOX_H
        ox = (AREA_W - total_w) // 2
        oy = (H - total_h) // 2
        cx = (mx - ox) // CBOX_W
        cy = (my - oy) // CBOX_H
        if 0 <= cx < MUNDO_W and 0 <= cy < MUNDO_H:
            return cx, cy
        return -1, -1

    def _centralizar_cam(self):
        """Centraliza a câmera isométrica no centro do chunk em edição."""
        mid_col = CHUNK_W / 2
        mid_row = CHUNK_H / 2
        dx = _iso.ISO_DX * self.zoom
        dy = _iso.ISO_DY * self.zoom
        iso_x = (mid_col - mid_row) * dx
        iso_y = (mid_col + mid_row) * dy
        self.cam_x = iso_x - AREA_W // 2
        self.cam_y = iso_y - (H - 28) // 2

    # ── Projeção isométrica (editor) ──────────────────────────────────

    def _iso_pos(self, col: int, row: int) -> tuple[int, int]:
        """cart→iso com zoom e câmera do editor.  Sem offset de topbar."""
        dx = int(_iso.ISO_DX * self.zoom)
        dy = int(_iso.ISO_DY * self.zoom)
        return ((col - row) * dx - int(self.cam_x),
                (col + row) * dy - int(self.cam_y))

    def _scaled_tile_iso(self, tid: int, tw: int, th: int) -> pygame.Surface:
        """Surface do tile Kenney escalada pelo zoom (cache por (tid, tw, th))."""
        key = (tid, tw, th)
        if key not in self._scaled_cache:
            ti = _ltiso.get_tile(tid)
            self._scaled_cache[key] = (
                ti.surface if (tw == ti.w and th == ti.h)
                else pygame.transform.scale(ti.surface, (tw, th))
            )
        return self._scaled_cache[key]

    # ── Ferramentas ───────────────────────────────────────────────────

    def _pintar(self, tx: int, ty: int, tid: int):
        c = self.chunks.get((self.sel_cx, self.sel_cy))
        if c and 0 <= tx < CHUNK_W and 0 <= ty < CHUNK_H:
            if c.get(tx, ty) != tid:
                c.set(tx, ty, tid)
                self._inval_chunk(self.sel_cx, self.sel_cy)

    def _flood_fill(self, tx: int, ty: int, novo: int):
        c = self.chunks.get((self.sel_cx, self.sel_cy))
        if not c or not (0 <= tx < CHUNK_W and 0 <= ty < CHUNK_H):
            return
        orig = c.get(tx, ty)
        if orig == novo:
            return
        stack = [(tx, ty)]
        while stack:
            x, y = stack.pop()
            if not (0 <= x < CHUNK_W and 0 <= y < CHUNK_H):
                continue
            if c.get(x, y) != orig:
                continue
            c.set(x, y, novo)
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        self._inval_chunk(self.sel_cx, self.sel_cy)

    # ── Persistência ──────────────────────────────────────────────────

    def _salvar_todos(self):
        n = sum(1 for c in self.chunks.values() if c.modificado)
        for c in self.chunks.values():
            if c.modificado:
                c.salvar()
        self._mostrar_msg(f"✓  {n} chunk(s) salvo(s).")

    def _recarregar(self):
        cx, cy = self.sel_cx, self.sel_cy
        c = Chunk.carregar(cx, cy)
        if c:
            self.chunks[(cx, cy)] = c
            self._inval_chunk(cx, cy)
            self._mostrar_msg(f"Chunk [{cx},{cy}] recarregado do disco.")
        else:
            self._mostrar_msg(f"Nenhum arquivo para [{cx},{cy}].")

    def _regenerar(self):
        cx, cy = self.sel_cx, self.sel_cy
        c = _gerar_chunk(cx, cy)
        c.modificado = True
        self.chunks[(cx, cy)] = c
        self._inval_chunk(cx, cy)
        self._mostrar_msg(f"Chunk [{cx},{cy}] regenerado proceduralmente.")

    def _mostrar_msg(self, txt: str, ms: int = 3000):
        self._msg   = txt
        self._msg_t = ms

    # ── Renderização: barra de título ─────────────────────────────────

    def _render_topbar(self):
        pygame.draw.rect(self.tela, C_TITULO, (0, 0, W, 28))
        pygame.draw.line(self.tela, C_BORDA, (0, 28), (W, 28), 1)

        modo_s = "MAPA  (TAB)" if self.modo == Modo.MAPA else "CHUNK (TAB)"
        _nome_mundo = self._mundo_meta.get("nome", self._mundo_id)
        partes = [
            (f"\u25a0 Editor \u2014 {_nome_mundo}", C_OURO),
            ("  |  ", C_DIM),
            (modo_s, C_VERDE),
            ("  |  ", C_DIM),
            (f"Chunk [{self.sel_cx},{self.sel_cy}]", C_TEXTO),
        ]
        if self.modo == Modo.CHUNK:
            c = self.chunks.get((self.sel_cx, self.sel_cy))
            if c and c.modificado:
                partes += [("  |  ", C_DIM), ("⚑ não salvo", C_ACENTO)]
        x = 10
        for txt, cor in partes:
            s = self.fn_hud.render(txt, True, cor)
            self.tela.blit(s, (x, 6))
            x += s.get_width()

    # ── Renderização: modo MAPA ───────────────────────────────────────

    def _render_mapa(self, mx: int, my: int):
        total_w = MUNDO_W * CBOX_W
        total_h = MUNDO_H * CBOX_H
        ox = (AREA_W - total_w) // 2
        oy = (H - total_h) // 2 + 14   # +14 pela topbar

        hover_cx, hover_cy = self._chunk_em_mouse(mx, my - 28)

        for cy in range(MUNDO_H):
            for cx in range(MUNDO_W):
                bx = ox + cx * CBOX_W
                by = oy + cy * CBOX_H
                rect = pygame.Rect(bx + 1, by + 1, CBOX_W - 3, CBOX_H - 3)

                # Thumbnail
                thumb  = self._thumb_chunk(cx, cy)
                scaled = pygame.transform.scale(thumb, (CBOX_W - 3, CBOX_H - 3))
                self.tela.blit(scaled, rect.topleft)

                # Borda
                c    = self.chunks.get((cx, cy))
                mod  = c.modificado if c else False
                sel  = (cx, cy) == (self.sel_cx, self.sel_cy)
                hov  = (cx, cy) == (hover_cx, hover_cy)
                col  = (C_SEL if sel else
                        C_TEXTO if hov else
                        C_ACENTO if mod else
                        C_BORDA)
                thick = 3 if sel else 2 if hov else 1
                pygame.draw.rect(self.tela, col, rect, thick)

                # Label
                lbl = self.fn_sm.render(f"{cx},{cy}", True,
                                         C_OURO if sel else C_DIM)
                self.tela.blit(lbl, (bx + 3, by + 3))

        # Dica inferior
        dica = self.fn_ui.render(
            "Clique → selecionar  |  Duplo clique → editar chunk  |  [TAB] alternar modo",
            True, C_DIM)
        self.tela.blit(dica, dica.get_rect(centerx=AREA_W // 2, y=H - 20))

    # ── Renderização: modo CHUNK (isométrico) ──────────────────────────

    def _render_chunk(self, mx: int, my: int):
        c = self.chunks.get((self.sel_cx, self.sel_cy))
        if c is None:
            return

        IWz  = max(1, int(_iso.ISO_W      * self.zoom))
        IHBz = max(1, int(_iso.ISO_H_BASE * self.zoom))
        IDYz = max(1, int(_iso.ISO_DY     * self.zoom))

        clip = pygame.Rect(0, 28, AREA_W, H - 28)
        self.tela.set_clip(clip)

        # Painter's algorithm: menor (col+row) = mais ao fundo
        ordem = sorted(
            ((col + row, col, row)
             for row in range(CHUNK_H)
             for col in range(CHUNK_W))
        )

        my_adj   = my - 28
        tx_h, ty_h = self._tile_em_mouse(mx, my_adj)

        ti_chao = _ltiso.get_tile(int(T.CALCADA))
        tchw    = max(1, int(ti_chao.w * self.zoom))
        tchh    = max(1, int(ti_chao.h * self.zoom))
        chao_sf = self._scaled_tile_iso(int(T.CALCADA), tchw, tchh)

        for _, col, row in ordem:
            sx, sy = self._iso_pos(col, row)
            sy += 28  # topbar

            # Frustum culling
            if sx + IWz < 0 or sx > AREA_W:
                continue
            if sy + IHBz + int(130 * self.zoom) < 28 or sy > H + 10:
                continue

            tid = int(c.dados[row, col])
            if tid == int(T.VAZIO):
                continue

            ti  = _ltiso.get_tile(tid)
            tw  = max(1, int(ti.w  * self.zoom))
            th  = max(1, int(ti.h  * self.zoom))
            sf  = self._scaled_tile_iso(tid, tw, th)

            if ti.tipo == "objeto":
                self.tela.blit(chao_sf, (sx, sy))

            self.tela.blit(sf, (sx + (IWz - tw) // 2 + int(ti.offset_x * self.zoom),
                               sy + int(ti.offset_y * self.zoom)))

        # Cursor — diamante isométrico no tile hover
        if 0 <= tx_h < CHUNK_W and 0 <= ty_h < CHUNK_H:
            hsx, hsy = self._iso_pos(tx_h, ty_h)
            hsy += 28
            pts = [
                (hsx + IWz // 2, hsy),
                (hsx + IWz,      hsy + IDYz),
                (hsx + IWz // 2, hsy + IDYz * 2),
                (hsx,            hsy + IDYz),
            ]
            pygame.draw.polygon(self.tela, C_SEL, pts, 2)
            tid_h = c.get(tx_h, ty_h)
            nome  = next((n for i, n, _ in PALETA if i == tid_h), str(tid_h))
            hint  = self.fn_sm.render(f"[{tx_h},{ty_h}] {nome}", True, C_SEL)
            bg    = pygame.Surface((hint.get_width() + 8, hint.get_height() + 4),
                                   pygame.SRCALPHA)
            bg.fill((8, 14, 28, 200))
            bx = min(hsx + 4, AREA_W - hint.get_width() - 16)
            by = max(30, hsy - 20)
            self.tela.blit(bg,   (bx - 4, by - 2))
            self.tela.blit(hint, (bx, by))

        self.tela.set_clip(None)

        # Barra de status inferior
        pygame.draw.rect(self.tela, C_TITULO, (0, H - 22, AREA_W, 22))
        pygame.draw.line(self.tela, C_BORDA,  (0, H - 22), (AREA_W, H - 22), 1)
        stat = (f"Chunk [{self.sel_cx},{self.sel_cy}]  "
                f"| Zoom {self.zoom:.1f}×  "
                f"| {_FERR_LABEL[self.ferr]}  "
                f"| Tile: {next((n for i,n,_ in PALETA if i==self.tile_sel), '?')}")
        s_stat = self.fn_sm.render(stat, True, C_DIM)
        self.tela.blit(s_stat, s_stat.get_rect(centerx=AREA_W // 2, y=H - 17))

    # ── Renderização: painel lateral ──────────────────────────────────

    def _render_painel(self):
        px = AREA_W
        pygame.draw.rect(self.tela, C_PAINEL, (px, 0, PANEL_W, H))
        pygame.draw.line(self.tela, C_BORDA, (px, 0), (px, H), 2)

        self._pal_rects  = []
        self._ferr_rects = []

        y   = 36
        PAD = 10

        def sep():
            nonlocal y
            pygame.draw.line(self.tela, C_BORDA,
                             (px + PAD, y), (px + PANEL_W - PAD, y), 1)
            y += 8

        def txt(s: str, cor=C_TEXTO, fn=None):
            nonlocal y
            f  = fn or self.fn_ui
            surf = f.render(s, True, cor)
            self.tela.blit(surf, (px + PAD, y))
            y += surf.get_height() + 3

        # ── Ferramenta ────────────────────────────────────────────────
        txt("FERRAMENTA", C_DIM, self.fn_sm)
        for ferr, label in _FERR_LABEL.items():
            ativo = ferr == self.ferr
            r = pygame.Rect(px + PAD, y, PANEL_W - PAD * 2, 18)
            self._ferr_rects.append((r, ferr))
            if ativo:
                pygame.draw.rect(self.tela, (28, 48, 88), r, border_radius=3)
                pygame.draw.rect(self.tela, C_BORDA, r, 1, border_radius=3)
            s = self.fn_sm.render(("► " if ativo else "  ") + label, True,
                                   C_SEL if ativo else C_DIM)
            self.tela.blit(s, (px + PAD + 2, y + 1))
            y += 20

        sep()

        # ── Paleta de tiles ───────────────────────────────────────────
        txt("TILES", C_DIM, self.fn_sm)
        ITEM_H = 22
        for tid, nome, tecla in PALETA:
            ativo = tid == self.tile_sel
            r = pygame.Rect(px + PAD, y, PANEL_W - PAD * 2, ITEM_H)
            self._pal_rects.append((r, tid))

            if ativo:
                pygame.draw.rect(self.tela, (28, 48, 88), r, border_radius=3)
                pygame.draw.rect(self.tela, C_SEL, r, 2, border_radius=3)

            # Miniatura do tile
            mini = self.tileset.get(tid)
            if mini:
                m16 = pygame.transform.scale(mini, (16, 16))
                self.tela.blit(m16, (px + PAD + 2, y + 3))

            # Nome
            nome_s = self.fn_sm.render(
                f"[{tecla}] {nome}", True, C_SEL if ativo else C_TEXTO)
            self.tela.blit(nome_s, (px + PAD + 22, y + 4))
            y += ITEM_H

        sep()

        # ── Ações ─────────────────────────────────────────────────────
        txt("AÇÕES", C_DIM, self.fn_sm)
        acoes = [
            ("[F5] Salvar tudo",    C_VERDE),
            ("[F9] Recarregar",     C_DIM),
            ("[G]  Gerar proc.",    C_DIM),
            ("[TAB] Modo",          C_DIM),
            ("[ESC] Menu",          C_ACENTO),
        ]
        for label, cor in acoes:
            txt(label, cor, self.fn_sm)

        sep()

        # ── Miniatura do mundo (visão geral em miniatura) ─────────────
        if self.modo == Modo.CHUNK:
            mini_w = PANEL_W - PAD * 2
            mini_h = int(mini_w * MUNDO_H / MUNDO_W)
            if y + mini_h + 4 < H - 10:
                txt("MAPA GERAL", C_DIM, self.fn_sm)
                for cy in range(MUNDO_H):
                    for cx in range(MUNDO_W):
                        bw = mini_w // MUNDO_W
                        bh = mini_h // MUNDO_H
                        bx = px + PAD + cx * bw
                        by = y + cy * bh
                        c  = self.chunks.get((cx, cy))
                        base_c = COR_TILE.get(int(T.CALCADA), (128, 118, 108))
                        if c is not None:
                            # Cor dominante do chunk (tile central)
                            mid_tid = int(c.dados[CHUNK_H // 2, CHUNK_W // 2])
                            base_c  = COR_TILE.get(mid_tid, base_c)
                        pygame.draw.rect(self.tela, base_c, (bx, by, bw - 1, bh - 1))
                        if (cx, cy) == (self.sel_cx, self.sel_cy):
                            pygame.draw.rect(self.tela, C_SEL,
                                             (bx, by, bw - 1, bh - 1), 2)
                y += mini_h + 4

        # ── Mensagem temporária ───────────────────────────────────────
        if self._msg:
            my_msg = H - 42
            s_msg  = self.fn_ui.render(self._msg, True, C_OURO)
            bg     = pygame.Surface((PANEL_W - 8, s_msg.get_height() + 8),
                                    pygame.SRCALPHA)
            bg.fill((10, 20, 40, 220))
            pygame.draw.rect(bg, C_OURO, bg.get_rect(), 1, border_radius=3)
            self.tela.blit(bg,    (px + 4, my_msg))
            self.tela.blit(s_msg, (px + 8, my_msg + 4))

    # ── Eventos de mouse ──────────────────────────────────────────────

    def _mouse_down(self, btn: int, mx: int, my: int):
        # Click no painel
        if mx >= AREA_W:
            for r, tid in self._pal_rects:
                if r.collidepoint(mx, my):
                    self.tile_sel = tid
                    return
            for r, ferr in self._ferr_rects:
                if r.collidepoint(mx, my):
                    self.ferr = ferr
                    return
            return

        my_adj = my - 28   # desconta topbar

        if self.modo == Modo.MAPA:
            cx, cy = self._chunk_em_mouse(mx, my_adj)
            if cx < 0:
                return
            if btn == 1:
                if (cx, cy) == (self.sel_cx, self.sel_cy):
                    # Segundo clique = entrar no chunk
                    self.modo = Modo.CHUNK
                    self._centralizar_cam()
                    self._mostrar_msg(f"Editando chunk [{cx},{cy}]")
                else:
                    self.sel_cx, self.sel_cy = cx, cy
                    self._mostrar_msg(f"Chunk [{cx},{cy}] selecionado — clique novamente para editar")

        elif self.modo == Modo.CHUNK:
            tx, ty = self._tile_em_mouse(mx, my_adj)
            if btn == 1:
                if self.ferr == Ferr.PREENCHER:
                    self._flood_fill(tx, ty, self.tile_sel)
                elif self.ferr == Ferr.PEGAR:
                    c = self.chunks.get((self.sel_cx, self.sel_cy))
                    if c and 0 <= tx < CHUNK_W and 0 <= ty < CHUNK_H:
                        self.tile_sel = c.get(tx, ty)
                else:
                    self._pintando = True
                    self._pintar(tx, ty, self.tile_sel)
            elif btn == 2:   # meio
                c = self.chunks.get((self.sel_cx, self.sel_cy))
                if c and 0 <= tx < CHUNK_W and 0 <= ty < CHUNK_H:
                    self.tile_sel = c.get(tx, ty)
            elif btn == 3:   # direito
                self._pintando = True
                self._pintar(tx, ty, int(T.VAZIO))

    def _key_down(self, key: int):
        # Ferramentas
        if   key == pygame.K_q: self.ferr = Ferr.PINCEL
        elif key == pygame.K_w: self.ferr = Ferr.APAGAR
        elif key == pygame.K_e: self.ferr = Ferr.PEGAR
        elif key == pygame.K_f: self.ferr = Ferr.PREENCHER

        # Seleção de tile por número
        elif key in _KEY_TO_TILE:
            self.tile_sel = _KEY_TO_TILE[key]

        # Ações
        elif key == pygame.K_F5:
            self._salvar_todos()
        elif key == pygame.K_F9:
            self._recarregar()
        elif key == pygame.K_g:
            self._regenerar()

        elif key == pygame.K_TAB:
            if self.modo == Modo.CHUNK:
                self.modo = Modo.MAPA
            else:
                self.modo = Modo.CHUNK
                self._centralizar_cam()

        elif key == pygame.K_ESCAPE:
            self._salvar_todos()
            pygame.time.wait(300)
            subprocess.Popen([sys.executable, _MENU])
            pygame.quit()
            sys.exit()

    # ── Loop principal ────────────────────────────────────────────────

    def executar(self):
        while True:
            dt_ms  = self.clock.tick(FPS)
            dt     = dt_ms / 1000.0
            mouse  = pygame.mouse.get_pos()
            mx, my = mouse
            teclas = pygame.key.get_pressed()

            # ── Panning via teclado (modo CHUNK) ──────────────────────
            if self.modo == Modo.CHUNK:
                spd = 220.0 * dt / self.zoom
                if teclas[pygame.K_LEFT]  or teclas[pygame.K_a]:
                    self.cam_x -= spd
                if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                    self.cam_x += spd
                if teclas[pygame.K_UP]:
                    self.cam_y -= spd
                if teclas[pygame.K_DOWN]:
                    self.cam_y += spd
                # Clamp suave: mantém o chunk iso na área visível
                _reach = (CHUNK_W + CHUNK_H) * int(_iso.ISO_DX * self.zoom)
                self.cam_x = max(-AREA_W, min(self.cam_x, _reach))
                self.cam_y = max(-H,      min(self.cam_y, _reach))

            # ── Pintura contínua ──────────────────────────────────────
            if self._pintando and self.modo == Modo.CHUNK:
                tx, ty = self._tile_em_mouse(mx, my - 28)
                if (tx, ty) != self._ultimo:
                    self._ultimo = (tx, ty)
                    if self.ferr == Ferr.PINCEL:
                        self._pintar(tx, ty, self.tile_sel)
                    elif self.ferr == Ferr.APAGAR:
                        self._pintar(tx, ty, int(T.VAZIO))

            # ── Eventos pygame ────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._salvar_todos()
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    self._key_down(event.key)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._mouse_down(event.button, mx, my)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button in (1, 3):
                        self._pintando = False
                        self._ultimo   = None

                elif event.type == pygame.MOUSEWHEEL:
                    if self.modo == Modo.CHUNK and mx < AREA_W:
                        fator = 1.15 if event.y > 0 else (1 / 1.15)
                        novo  = max(0.5, min(4.0, self.zoom * fator))
                        # Zoom centrado no cursor — mantém col/row fracionário sob o mouse
                        dx_old = _iso.ISO_DX * self.zoom
                        dy_old = _iso.ISO_DY * self.zoom
                        rx     = mx + self.cam_x
                        ry     = (my - 28) + self.cam_y
                        col_f  = (rx / dx_old + ry / dy_old) / 2
                        row_f  = (ry / dy_old - rx / dx_old) / 2
                        self.zoom  = novo
                        dx_new = _iso.ISO_DX * novo
                        dy_new = _iso.ISO_DY * novo
                        self.cam_x = (col_f - row_f) * dx_new - mx
                        self.cam_y = (col_f + row_f) * dy_new - (my - 28)
                        self._scaled_cache.clear()

                elif event.type == pygame.VIDEORESIZE:
                    pass   # janela redimensionável por padrão

            # ── Timer mensagem ────────────────────────────────────────
            if self._msg_t > 0:
                self._msg_t = max(0, self._msg_t - dt_ms)
                if self._msg_t == 0:
                    self._msg = ""

            # ── Render ────────────────────────────────────────────────
            self.tela.fill(C_FUNDO)
            if self.modo == Modo.MAPA:
                self._render_mapa(mx, my - 28)
            else:
                self._render_chunk(mx, my)
            self._render_painel()
            self._render_topbar()

            pygame.display.flip()


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    # Nearest-neighbor scaling — evita blur quando a janela é redimensionada
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"

    pygame.init()
    tela  = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    _ltiso.inicializar()    # define caminho base dos Assets Kenney
    _ltiso.pre_carregar()   # pré-carrega todos os 12 tiles (requer tela)
    pygame.display.set_caption("Editor de Mundo — Call of Cthulhu 7e")
    clock = pygame.time.Clock()

    # Tela de seleção de mundo
    mundo_id = SeletorMundo(tela, clock).executar()
    if mundo_id is None:
        pygame.quit()
        sys.exit()

    meta = _gm.carregar(mundo_id)
    pygame.display.set_caption(
        f"Editor \u2014 {meta.get('nome', mundo_id)}")
    EditorMundo(tela, clock, mundo_id).executar()


if __name__ == "__main__":
    main()
