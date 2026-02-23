"""
editor/paineis/painel_mapa.py — Editor de mapa isométrico.

Usa o Renderer do motor para exibir o mapa em tempo real conforme
o usuário pinta tiles. Interface:

    Área esquerda (80 %):  visualização isométrica
        LMB          = pintar tile / efeito selecionado
        RMB          = apagar → CHÃO
        Scroll       = zoom (aproximado via câmera)
        WASD / setas = mover câmera

    Painel direito (20 %):
        Seção TILES    — escolhe tipo de tile
        Seção EFEITOS  — escolhe efeito ambiental
        Seção SPAWN    — coloca / remove spawn de personagem
        Botões resize  — [+col] [-col] [+lin] [-lin]
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import pygame

# Path setup
_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from engine.mundo   import Mundo, TipoTile, EfeitoAmbiental
from engine.renderer import (
    Renderer, grid_para_tela, tela_para_grid, TILE_W, TILE_H
)
from dados.campanha_schema import Campanha, DadosMapa, EfeitoMapa

# ── Cores ──────────────────────────────────────────────────────
_C = {
    "fundo":     (14,  18,  32),
    "painel":    (22,  28,  48),
    "borda":     (50,  65, 100),
    "texto":     (215, 210, 195),
    "texto_dim": (100,  98,  88),
    "sel":       ( 55,  90, 155),
    "hover":     ( 35,  50,  85),
    "ok":        ( 60, 190, 110),
    "erro":      (210,  70,  70),
}

# ── Mapeamento tile int → TipoTile / cor ──────────────────────
_TIPO_INFO = [
    (1, TipoTile.CHAO,    "CHÃO",    ( 80, 160,  80)),
    (2, TipoTile.PAREDE,  "PAREDE",  (110,  90,  70)),
    (3, TipoTile.ELEVADO, "ELEVADO", (140, 120,  90)),
    (0, TipoTile.VAZIO,   "VAZIO",   ( 30,  30,  40)),
]

_EFEITO_INFO = [
    (EfeitoAmbiental.NENHUM,     "Nenhum",     (60, 60, 60)),
    (EfeitoAmbiental.OLEO,       "Óleo",       (20, 18, 15)),
    (EfeitoAmbiental.FOGO,       "Fogo",       (220, 100, 20)),
    (EfeitoAmbiental.NEVOA,      "Névoa",      (160, 165, 200)),
    (EfeitoAmbiental.ARBUSTO,    "Arbusto",    (35, 110, 35)),
    (EfeitoAmbiental.AGUA_BENTA, "Água Benta", (60, 130, 220)),
    (EfeitoAmbiental.SANGUE,     "Sangue",     (160, 20, 20)),
]

_FERRAMENTA_INFO = [
    ("tile",   "Pintar Tile"),
    ("efeito", "Pintar Efeito"),
    ("apagar", "Apagar (CHÃO)"),
    ("spawn",  "Spawn Personagem"),
]

PAINEL_L = 980   # separação mapa | palette


class PainelMapa:
    """
    Painel de edição de mapas.
    `campanha` e `mapa_id` podem ser trocados pelo editor principal.
    """

    def __init__(self, tela: pygame.Surface, largura: int, altura: int,
                 campanha: Campanha, mapa_id: str,
                 fonte_hud: Optional[pygame.font.Font] = None,
                 fonte_ui: Optional[pygame.font.Font] = None):
        self.tela     = tela
        self.largura  = largura
        self.altura   = altura
        self.campanha = campanha
        self.mapa_id  = mapa_id

        self._fonte_hud = fonte_hud or pygame.font.SysFont("monospace", 12)
        self._fonte_ui  = fonte_ui  or pygame.font.SysFont("monospace", 13)
        self._fonte_sm  = pygame.font.SysFont("monospace", 11)

        # Área do mapa (subsurface esquerda)
        self._MAP_Y   = 0     # relativo ao painel (tab bar é gerenciada pelo editor)
        self._map_sub = None  # criado em _reconstruir()

        # Estado do editor
        self._ferramenta  = "tile"      # "tile" | "efeito" | "apagar" | "spawn"
        self._tile_sel    = 1           # int tile selecionado
        self._efeito_sel  = EfeitoAmbiental.NENHUM
        self._spawn_sel   = ""          # id do personagem a spawnar

        # Mundo e Renderer (construídos a partir do DadosMapa)
        self._mundo: Optional[Mundo]    = None
        self._renderer: Optional[Renderer] = None
        self._reconstruir()

        # Velocidade de pan de câmera
        self._PAN = 1.5

    # ── Mapa corrente ─────────────────────────────────────────

    @property
    def _dados_mapa(self) -> Optional[DadosMapa]:
        return self.campanha.mapas.get(self.mapa_id)

    def trocar_mapa(self, novo_mapa_id: str):
        self.mapa_id = novo_mapa_id
        self._reconstruir()

    def _reconstruir(self):
        dm = self._dados_mapa
        if dm is None:
            return

        self._mundo = Mundo(dm.tiles)

        # Aplicar efeitos salvos
        for ef in dm.efeitos:
            cel = self._mundo.celula(ef.col, ef.linha)
            if cel:
                try:
                    tipo_ef = EfeitoAmbiental[ef.tipo]
                except KeyError:
                    continue
                cel.aplicar_efeito(tipo_ef, ef.duracao)

        # Subsurface da área do mapa
        self._map_sub = self.tela.subsurface(
            pygame.Rect(0, 0, PAINEL_L, self.altura)
        )

        # Renderer aponta para o subsurface
        self._renderer = Renderer(self._map_sub, PAINEL_L, self.altura)
        # Centraliza câmera no meio do mapa
        mc = dm.largura  // 2
        ml = dm.altura   // 2
        self._renderer.cam_x = (mc - ml) * (TILE_W // 2)
        self._renderer.cam_y = (mc + ml) * (TILE_H // 2) - self.altura // 4

    # ── Processamento de eventos ──────────────────────────────

    def processar_evento(self, e: pygame.event.Event):
        if self._renderer is None:
            return

        # Cliques na área do mapa
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            mx, my = pygame.mouse.get_pos()
            if mx < PAINEL_L:
                self._handle_mapa_click(mx, my, e)

        # Cliques no painel direito
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            if mx >= PAINEL_L:
                self._handle_palette_click(mx, my)

    def _handle_mapa_click(self, mx: int, my: int,
                            e: pygame.event.Event):
        btns = pygame.mouse.get_pressed()
        lmb  = btns[0]
        rmb  = btns[2]

        if not (lmb or rmb):
            return

        col, linha = tela_para_grid(
            mx - self._renderer.offset_x,
            my - self._renderer.offset_y,
            self._renderer.cam_x,
            self._renderer.cam_y,
        )

        dm = self._dados_mapa
        if dm is None:
            return

        if not (0 <= linha < dm.altura and 0 <= col < dm.largura):
            return

        if rmb or self._ferramenta == "apagar":
            self._pintar_tile(col, linha, 1)
            self._limpar_efeito(col, linha)
            return

        if self._ferramenta == "tile":
            self._pintar_tile(col, linha, self._tile_sel)
        elif self._ferramenta == "efeito":
            self._pintar_efeito(col, linha, self._efeito_sel)
        elif self._ferramenta == "spawn":
            self._toggle_spawn(col, linha)

    def _handle_palette_click(self, mx: int, my: int):
        # Calcula itens do painel direito
        px = PAINEL_L + 10
        py = 10
        lh = 28

        # Ferramentas
        for i, (fid, _) in enumerate(_FERRAMENTA_INFO):
            r = pygame.Rect(px, py + i * lh, self.largura - PAINEL_L - 20, 24)
            if r.collidepoint(mx, my):
                self._ferramenta = fid
                return
        py += len(_FERRAMENTA_INFO) * lh + 14

        # Tiles
        for i, (tid, _, _, _) in enumerate(_TIPO_INFO):
            r = pygame.Rect(px, py + i * lh, self.largura - PAINEL_L - 20, 24)
            if r.collidepoint(mx, my):
                self._tile_sel   = tid
                self._ferramenta = "tile"
                return
        py += len(_TIPO_INFO) * lh + 14

        # Efeitos
        for i, (eid, _, _) in enumerate(_EFEITO_INFO):
            r = pygame.Rect(px, py + i * lh, self.largura - PAINEL_L - 20, 24)
            if r.collidepoint(mx, my):
                self._efeito_sel = eid
                self._ferramenta = "efeito"
                return
        py += len(_EFEITO_INFO) * lh + 14

        # Personagens para spawn
        dm = self._dados_mapa
        if dm:
            for i, (pid, p) in enumerate(self.campanha.personagens.items()):
                r = pygame.Rect(px, py + i * lh, self.largura - PAINEL_L - 20, 24)
                if r.collidepoint(mx, my):
                    self._spawn_sel   = pid
                    self._ferramenta  = "spawn"
                    return

    # ── Operações de pintura ──────────────────────────────────

    def _pintar_tile(self, col: int, linha: int, tipo_int: int):
        dm = self._dados_mapa
        if dm is None:
            return
        dm.tiles[linha][col] = tipo_int
        # Sincroniza Mundo em memória
        if self._mundo:
            _MAPA = {0: TipoTile.VAZIO, 1: TipoTile.CHAO,
                     2: TipoTile.PAREDE, 3: TipoTile.ELEVADO}
            cel = self._mundo.celula(col, linha)
            if cel:
                cel.tipo = _MAPA.get(tipo_int, TipoTile.CHAO)

    def _pintar_efeito(self, col: int, linha: int, ef: EfeitoAmbiental):
        dm = self._dados_mapa
        if dm is None:
            return
        # Remove efeito existente nessa célula
        dm.efeitos = [e for e in dm.efeitos
                      if not (e.col == col and e.linha == linha)]
        if ef != EfeitoAmbiental.NENHUM:
            dm.efeitos.append(EfeitoMapa(col=col, linha=linha,
                                          tipo=ef.name, duracao=99))
        if self._mundo:
            cel = self._mundo.celula(col, linha)
            if cel:
                cel.aplicar_efeito(ef, 99)

    def _limpar_efeito(self, col: int, linha: int):
        dm = self._dados_mapa
        if dm:
            dm.efeitos = [e for e in dm.efeitos
                          if not (e.col == col and e.linha == linha)]
        if self._mundo:
            cel = self._mundo.celula(col, linha)
            if cel:
                cel.efeito = EfeitoAmbiental.NENHUM

    def _toggle_spawn(self, col: int, linha: int):
        dm = self._dados_mapa
        if dm is None or not self._spawn_sel:
            return
        pid = self._spawn_sel
        # Atualiza spawn position do personagem
        if pid in self.campanha.personagens:
            self.campanha.personagens[pid].spawn_col   = float(col)
            self.campanha.personagens[pid].spawn_linha = float(linha)
        # Adiciona ao lista de spawn do mapa
        if pid not in dm.personagens_spawn:
            dm.personagens_spawn.append(pid)

    # ── Atualização de câmera por teclado ─────────────────────

    def atualizar(self, dt: int):
        if self._renderer is None:
            return
        keys = pygame.key.get_pressed()
        spd  = self._PAN * max(1, dt // 8)

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self._renderer.cam_x -= spd
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self._renderer.cam_x += spd
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self._renderer.cam_y -= spd
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self._renderer.cam_y += spd

    # ── Renderização ──────────────────────────────────────────

    def desenhar(self):
        tela = self.tela
        tela.fill(_C["fundo"], pygame.Rect(0, 0, PAINEL_L, self.altura))
        tela.fill(_C["painel"], pygame.Rect(PAINEL_L, 0,
                                             self.largura - PAINEL_L, self.altura))

        if self._renderer and self._mundo:
            self._renderer.renderizar_mapa(self._mundo)
            self._renderer.renderizar_efeitos(self._mundo)
            self._desenhar_spawn_markers()
            self._desenhar_cursor_mapa()

        self._desenhar_palette()
        self._desenhar_info_rodape()

    def _desenhar_spawn_markers(self):
        dm = self._dados_mapa
        if not dm or not self._renderer:
            return
        fn = self._fonte_sm
        for pid in dm.personagens_spawn:
            p = self.campanha.personagens.get(pid)
            if not p:
                continue
            cx, cy = grid_para_tela(
                p.spawn_col, p.spawn_linha,
                self._renderer.cam_x, self._renderer.cam_y,
            )
            cx += self._renderer.offset_x
            cy += self._renderer.offset_y
            pygame.draw.circle(self._map_sub, (255, 200, 50),
                               (int(cx), int(cy)), 6)
            s = fn.render(p.nome[:6], True, (255, 240, 150))
            self._map_sub.blit(s, (int(cx) - s.get_width() // 2, int(cy) - 18))

    def _desenhar_cursor_mapa(self):
        mx, my = pygame.mouse.get_pos()
        if mx >= PAINEL_L or not self._renderer:
            return
        col, linha = tela_para_grid(
            mx - self._renderer.offset_x,
            my - self._renderer.offset_y,
            self._renderer.cam_x, self._renderer.cam_y,
        )
        dm = self._dados_mapa
        if dm and 0 <= linha < dm.altura and 0 <= col < dm.largura:
            self._renderer.renderizar_highlights(
                [(col, linha)], (255, 255, 100, 110)
            )
            txt = self._fonte_sm.render(f"({col},{linha})", True, (255, 255, 150))
            self._map_sub.blit(txt, (mx + 8, my - 14))

    def _desenhar_palette(self):
        tela  = self.tela
        fn    = self._fonte_ui
        fn_sm = self._fonte_sm
        px    = PAINEL_L + 10
        py    = 10
        lh    = 28
        W     = self.largura - PAINEL_L - 20

        def _titulo(txt: str, y: int):
            s = fn_sm.render(txt, True, (140, 130, 110))
            tela.blit(s, (px, y))
            pygame.draw.line(tela, (60, 70, 100),
                             (px, y + 14), (px + W, y + 14), 1)

        def _item(label: str, cor: tuple, y: int, sel: bool):
            r = pygame.Rect(px, y, W, 24)
            if sel:
                pygame.draw.rect(tela, _C["sel"], r, border_radius=4)
            elif r.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(tela, _C["hover"], r, border_radius=4)
            pygame.draw.rect(tela, (40, 40, 40),
                             pygame.Rect(px + 2, y + 4, 16, 16), border_radius=3)
            pygame.draw.rect(tela, cor,
                             pygame.Rect(px + 2, y + 4, 16, 16), border_radius=3)
            s = fn.render(label, True, _C["texto"])
            tela.blit(s, (px + 22, y + 3))

        # ── Ferramentas ────────────────────────────────────────
        _titulo("FERRAMENTA", py)
        py += 16
        _FICONS = {"tile": "◆", "efeito": "●", "apagar": "✕", "spawn": "★"}
        _FCORE  = {"tile": (80, 140, 220), "efeito": (220, 130, 30),
                   "apagar": (200, 70, 70), "spawn":  (240, 200, 50)}
        for fid, fname in _FERRAMENTA_INFO:
            sel = (self._ferramenta == fid)
            _item(f"{_FICONS[fid]} {fname}", _FCORE[fid], py, sel)
            py += lh
        py += 8

        # ── Tiles ─────────────────────────────────────────────
        _titulo("TILES", py)
        py += 16
        for tid, _, tnome, tcor in _TIPO_INFO:
            sel = (self._ferramenta == "tile" and self._tile_sel == tid)
            _item(tnome, tcor, py, sel)
            py += lh
        py += 8

        # ── Efeitos ───────────────────────────────────────────
        _titulo("EFEITOS", py)
        py += 16
        for eid, enome, ecor in _EFEITO_INFO:
            sel = (self._ferramenta == "efeito" and self._efeito_sel == eid)
            _item(enome, ecor, py, sel)
            py += lh
        py += 8

        # ── Spawns ────────────────────────────────────────────
        _titulo("SPAWN PERSONAGENS", py)
        py += 16
        dm = self._dados_mapa
        for pid, p in list(self.campanha.personagens.items()):
            in_map = dm and pid in dm.personagens_spawn
            cor = (240, 200, 50) if in_map else (80, 80, 80)
            sel = (self._ferramenta == "spawn" and self._spawn_sel == pid)
            nome = p.nome[:14]
            _item(nome, cor, py, sel)
            py += lh
            if py > self.altura - 30:
                break

    def _desenhar_info_rodape(self):
        dm = self._dados_mapa
        if dm is None:
            return
        info = (f"Mapa: {dm.nome}  [{dm.largura}×{dm.altura}]  "
                f"Tiles: {sum(1 for r in dm.tiles for v in r if v > 0)}  "
                f"Efeitos: {len(dm.efeitos)}  "
                f"Triggers: {len(dm.triggers)}")
        s = self._fonte_sm.render(info, True, (120, 115, 100))
        self.tela.blit(s, (8, self.altura - 18))


