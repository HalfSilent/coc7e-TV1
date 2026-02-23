"""
combate/renderer_combate.py — Renderer 2D top-down para o combate tático.

Renderiza o grid do Mundo usando pygame.draw.rect() simples.
Cada célula = CELL_SIZE × CELL_SIZE pixels. Sem isometria.

Camadas (ordem de desenho):
    1. Chão (tile base)
    2. Efeito ambiental (overlay colorido semi-transparente)
    3. Cobertura (borda grossa)
    4. Células em destaque (movimento / alcance)
    5. Entidades (retângulos coloridos com ícone de letra)
    6. Cursor do jogador
    7. HP bars em cima das entidades
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pygame

from engine.mundo import (
    Celula, Cobertura, EfeitoAmbiental, Mundo, TipoTile
)
from engine.entidade import Entidade, Jogador, Inimigo


# ══════════════════════════════════════════════════════════════
# CONSTANTES VISUAIS
# ══════════════════════════════════════════════════════════════

CELL_SIZE  = 48          # pixels por célula
BORDA_MAPA = 8           # pixels de margem no topo/esquerda

# Paleta de cores dos tiles
COR_VAZIO   = (15,  15,  20)
COR_CHAO    = (55,  55,  65)
COR_PAREDE  = (30,  30,  40)
COR_ELEVADO = (80,  70,  60)
COR_BORDA_TILE = (35, 35, 45)

# Paleta de efeitos ambientais (overlay RGBA)
EFEITO_CORES: Dict[EfeitoAmbiental, Tuple[int, int, int, int]] = {
    EfeitoAmbiental.OLEO:       (40,  30,   5, 120),
    EfeitoAmbiental.FOGO:       (220, 80,   0, 160),
    EfeitoAmbiental.NEVOA:      (180, 180, 200, 100),
    EfeitoAmbiental.ARBUSTO:    (30,  100,  20, 130),
    EfeitoAmbiental.AGUA_BENTA: (50,  150, 255, 100),
    EfeitoAmbiental.SANGUE:     (140,  10,  10, 130),
}

# Destaque de células
COR_MOVIMENTO  = (60,  120, 200, 80)   # azul fraco
COR_ALCANCE    = (200,  60,  60, 80)   # vermelho fraco
COR_CURSOR     = (255, 255,   0, 180)  # amarelo

# Cores de entidades
COR_JOGADOR = (212, 168,  67)   # dourado
COR_INIMIGO = (200,  60,  60)   # vermelho
COR_ENGENDRO= (140,  60, 200)   # roxo


# ══════════════════════════════════════════════════════════════
# RENDERER
# ══════════════════════════════════════════════════════════════

class RendererCombate:
    """
    Renderiza o campo de batalha top-down em uma Surface pygame.
    
    Uso:
        renderer = RendererCombate(screen, font_hud)
        renderer.desenhar(mundo, entidades, estado)
    """

    def __init__(self, screen: pygame.Surface, font_hud: pygame.font.Font,
                 offset_x: int = BORDA_MAPA, offset_y: int = BORDA_MAPA):
        self.screen   = screen
        self.font     = font_hud
        self.offset_x = offset_x
        self.offset_y = offset_y

    # ── conversões de coordenadas ──────────────────────────────

    def grid_para_pixel(self, col: int, linha: int) -> Tuple[int, int]:
        """Retorna o pixel (x, y) do canto superior-esquerdo da célula."""
        return (
            self.offset_x + col * CELL_SIZE,
            self.offset_y + linha * CELL_SIZE,
        )

    def pixel_para_grid(self, px: int, py: int) -> Tuple[int, int]:
        """Converte posição do mouse para célula do grid."""
        return (
            (px - self.offset_x) // CELL_SIZE,
            (py - self.offset_y) // CELL_SIZE,
        )

    # ── tamanho da área de combate em pixels ──────────────────

    def tamanho_mapa_px(self, mundo: Mundo) -> Tuple[int, int]:
        return (mundo.colunas * CELL_SIZE, mundo.linhas * CELL_SIZE)

    # ══════════════════════════════════════════════════════════
    # DESENHO PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def desenhar(
        self,
        mundo: Mundo,
        entidades: List[Entidade],
        celulas_movimento: Optional[Set[Tuple[int, int]]] = None,
        celulas_alcance:   Optional[Set[Tuple[int, int]]] = None,
        cursor:            Optional[Tuple[int, int]] = None,
        entidade_ativa:    Optional[Entidade] = None,
    ):
        """
        Desenha o campo de batalha completo.
        
        Args:
            mundo:             Objeto Mundo com o grid.
            entidades:         Lista de todas as entidades no campo.
            celulas_movimento: Células destacadas para movimento.
            celulas_alcance:   Células destacadas para alcance de ataque.
            cursor:            Posição (col, linha) do cursor de seleção.
            entidade_ativa:    Entidade cujo turno está ativo.
        """
        celulas_movimento = celulas_movimento or set()
        celulas_alcance   = celulas_alcance   or set()

        # 1. Tiles de chão
        self._desenhar_tiles(mundo)

        # 2. Efeitos ambientais
        self._desenhar_efeitos(mundo)

        # 3. Destaque de células (movimento / alcance)
        self._desenhar_destaques(celulas_movimento, celulas_alcance)

        # 4. Entidades
        self._desenhar_entidades(entidades, entidade_ativa)

        # 5. Cursor de seleção
        if cursor:
            self._desenhar_cursor(cursor)

    # ── tiles ─────────────────────────────────────────────────

    def _desenhar_tiles(self, mundo: Mundo):
        for linha in range(mundo.linhas):
            for col in range(mundo.colunas):
                cel = mundo.grid[linha][col]
                cor = self._cor_tile(cel)
                x, y = self.grid_para_pixel(col, linha)
                r = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, cor, r)
                pygame.draw.rect(self.screen, COR_BORDA_TILE, r, 1)

                # Ícone para elevado (caixote)
                if cel.tipo == TipoTile.ELEVADO:
                    inner = r.inflate(-12, -12)
                    pygame.draw.rect(self.screen, (100, 90, 75), inner)
                    pygame.draw.rect(self.screen, (120, 105, 85), inner, 2)

    def _cor_tile(self, cel: Celula) -> tuple:
        match cel.tipo:
            case TipoTile.VAZIO:   return COR_VAZIO
            case TipoTile.CHAO:    return COR_CHAO
            case TipoTile.PAREDE:  return COR_PAREDE
            case TipoTile.ELEVADO: return COR_ELEVADO
            case _:                return COR_CHAO

    # ── efeitos ambientais ────────────────────────────────────

    def _desenhar_efeitos(self, mundo: Mundo):
        overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        for linha in range(mundo.linhas):
            for col in range(mundo.colunas):
                cel = mundo.grid[linha][col]
                if cel.efeito == EfeitoAmbiental.NENHUM:
                    continue
                cor_rgba = EFEITO_CORES.get(cel.efeito)
                if not cor_rgba:
                    continue
                overlay.fill(cor_rgba)
                x, y = self.grid_para_pixel(col, linha)
                self.screen.blit(overlay, (x, y))

                # Ícone de efeito (texto pequeno)
                icones = {
                    EfeitoAmbiental.FOGO:       "🔥",
                    EfeitoAmbiental.OLEO:       "💧",
                    EfeitoAmbiental.NEVOA:      "☁",
                    EfeitoAmbiental.ARBUSTO:    "🌿",
                    EfeitoAmbiental.AGUA_BENTA: "✝",
                    EfeitoAmbiental.SANGUE:     "✦",
                }
                icone = icones.get(cel.efeito, "?")
                try:
                    surf = self.font.render(icone, True, (255, 255, 255))
                    self.screen.blit(surf, (x + 4, y + 4))
                except Exception:
                    pass

    # ── destaques ─────────────────────────────────────────────

    def _desenhar_destaques(self,
                             celulas_movimento: Set[Tuple[int, int]],
                             celulas_alcance:   Set[Tuple[int, int]]):
        hl = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        for (col, linha) in celulas_movimento:
            hl.fill(COR_MOVIMENTO)
            x, y = self.grid_para_pixel(col, linha)
            self.screen.blit(hl, (x, y))
        for (col, linha) in celulas_alcance:
            hl.fill(COR_ALCANCE)
            x, y = self.grid_para_pixel(col, linha)
            self.screen.blit(hl, (x, y))

    # ── entidades ─────────────────────────────────────────────

    def _desenhar_entidades(self, entidades: List[Entidade],
                             entidade_ativa: Optional[Entidade]):
        for ent in entidades:
            if not ent.vivo:
                continue
            col, linha = int(ent.col), int(ent.linha)
            x, y = self.grid_para_pixel(col, linha)

            # Sombra
            shadow_r = pygame.Rect(x + 4, y + 4, CELL_SIZE - 8, CELL_SIZE - 8)
            pygame.draw.ellipse(self.screen, (0, 0, 0, 100), shadow_r)

            # Corpo (circulo colorido)
            cx, cy = x + CELL_SIZE // 2, y + CELL_SIZE // 2
            raio = CELL_SIZE // 2 - 6
            cor = self._cor_entidade(ent)
            pygame.draw.circle(self.screen, cor, (cx, cy), raio)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), raio, 2)

            # Anel de turno ativo
            if entidade_ativa and ent is entidade_ativa:
                pygame.draw.circle(self.screen, (255, 255, 0), (cx, cy), raio + 4, 3)

            # Inicial do nome
            inicial = self.font.render(ent.nome[0].upper(), True, (255, 255, 255))
            ir = inicial.get_rect(center=(cx, cy))
            self.screen.blit(inicial, ir)

            # HP bar
            self._desenhar_hp_bar(x, y, ent)

    def _cor_entidade(self, ent: Entidade) -> tuple:
        from engine.entidade import Jogador, Inimigo, Engendro
        if isinstance(ent, Jogador):  return COR_JOGADOR
        if isinstance(ent, Engendro): return COR_ENGENDRO
        if isinstance(ent, Inimigo):  return COR_INIMIGO
        return ent.cor

    def _desenhar_hp_bar(self, x: int, y: int, ent: Entidade):
        bw = CELL_SIZE - 8
        bh = 5
        bx = x + 4
        by = y + CELL_SIZE - 10

        # Fundo
        pygame.draw.rect(self.screen, (50, 0, 0), (bx, by, bw, bh))
        # HP atual
        pct = max(0, ent.hp / ent.hp_max)
        cor_hp = (0, 200, 0) if pct > 0.5 else (255, 200, 0) if pct > 0.25 else (220, 0, 0)
        pygame.draw.rect(self.screen, cor_hp, (bx, by, int(bw * pct), bh))

    # ── cursor ────────────────────────────────────────────────

    def _desenhar_cursor(self, cursor: Tuple[int, int]):
        col, linha = cursor
        x, y = self.grid_para_pixel(col, linha)
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        surf.fill((255, 255, 0, 80))
        pygame.draw.rect(surf, (255, 255, 0, 220), surf.get_rect(), 3)
        self.screen.blit(surf, (x, y))

    # ══════════════════════════════════════════════════════════
    # PAINEL LATERAL (HUD do combate)
    # ══════════════════════════════════════════════════════════

    def desenhar_painel_hud(
        self,
        superficie: pygame.Surface,
        x: int, y: int, largura: int,
        entidade_ativa: Optional[Entidade],
        cards_disponiveis: list,
        card_selecionado: Optional[int],
        log_combate: List[str],
        turno_num: int,
        font_titulo: pygame.font.Font,
        font_normal: pygame.font.Font,
        deck_scroll: int = 0,
    ):
        """
        Desenha o painel lateral direito com:
        - Nome + stats da entidade ativa
        - Lista de cartas disponíveis (scrollável, com % de perícia colorido)
        - Log de combate (últimas 8 linhas)
        """
        pad = 10
        cy = y + pad
        h_tela = superficie.get_height()

        # ── Título do turno ──────────────────────────────────
        txt = font_titulo.render(f"TURNO {turno_num}", True, (200, 180, 120))
        superficie.blit(txt, (x + pad, cy))
        cy += txt.get_height() + 6

        # ── Stats da entidade ativa ──────────────────────────
        if entidade_ativa:
            cor_nome = (212, 168, 67) if isinstance(entidade_ativa, Jogador) else (200, 80, 80)
            nome_surf = font_titulo.render(entidade_ativa.nome, True, cor_nome)
            superficie.blit(nome_surf, (x + pad, cy))
            cy += nome_surf.get_height() + 2

            stats = [
                f"HP:  {entidade_ativa.hp}/{entidade_ativa.hp_max}",
                f"SAN: {entidade_ativa.sanidade}/{entidade_ativa.san_max}",
            ]
            for s in stats:
                st = font_normal.render(s, True, (180, 180, 180))
                superficie.blit(st, (x + pad, cy))
                cy += st.get_height() + 1

        cy += 8
        pygame.draw.line(superficie, (80, 80, 100), (x + pad, cy), (x + largura - pad, cy), 1)
        cy += 8

        # ── Cartas disponíveis (scrollável) ──────────────────
        header = font_normal.render("AÇÕES  [↑↓ rolar]", True, (150, 150, 170))
        superficie.blit(header, (x + pad, cy))
        cy += header.get_height() + 4

        # Quantas cartas cabem antes de precisar log
        # Reserva ~130px para o log embaixo
        espaco_cards = h_tela - cy - 140
        altura_card  = 28
        max_vis      = max(1, espaco_cards // altura_card)

        total = len(cards_disponiveis)
        inicio = max(0, min(deck_scroll, total - max_vis))
        fim    = min(total, inicio + max_vis)

        # Indicador de scroll acima
        if inicio > 0:
            seta = font_normal.render("▲ mais acima", True, (120, 120, 160))
            superficie.blit(seta, (x + pad, cy))
            cy += seta.get_height()

        for i in range(inicio, fim):
            card = cards_disponiveis[i]
            selecionado = (i == card_selecionado)
            bg_cor    = (80, 80, 120) if selecionado else (45, 45, 60)
            borda_cor = (200, 200, 60) if selecionado else (80, 80, 100)

            r = pygame.Rect(x + pad, cy, largura - pad * 2, altura_card - 2)
            pygame.draw.rect(superficie, bg_cor, r, border_radius=3)
            pygame.draw.rect(superficie, borda_cor, r, 1, border_radius=3)

            # Tecla de atalho [1-9]
            hotkey = f"[{i+1}]" if i < 9 else "[ ]"
            tecla = font_normal.render(hotkey, True, (150, 200, 150))
            superficie.blit(tecla, (r.x + 4, r.y + 5))

            # Nome da carta + custo AP
            nome_label = f"[{card.custo_ap}AP] {card.nome}"
            label = font_normal.render(nome_label, True, (220, 220, 220))
            superficie.blit(label, (r.x + 30, r.y + 5))

            # Percentagem da perícia (canto direito da carta, colorida)
            if card.valor_pericia > 0:
                pct = card.valor_pericia
                if pct >= 90:   cor_pct = (80,  160, 255)   # azul — especialista
                elif pct >= 50: cor_pct = (80,  200,  80)   # verde — competente
                elif pct >= 25: cor_pct = (200, 200,  80)   # amarelo — básico
                else:           cor_pct = (220,  60,  60)   # vermelho — fraco
                pct_surf = font_normal.render(f"{pct}%", True, cor_pct)
                superficie.blit(pct_surf, (r.right - pct_surf.get_width() - 4, r.y + 5))

            cy += altura_card

        # Indicador de scroll abaixo
        if fim < total:
            seta = font_normal.render(f"▼ +{total - fim} mais", True, (120, 120, 160))
            superficie.blit(seta, (x + pad, cy))
            cy += seta.get_height()

        cy += 8
        pygame.draw.line(superficie, (80, 80, 100), (x + pad, cy), (x + largura - pad, cy), 1)
        cy += 8

        # ── Log de combate ───────────────────────────────────
        log_header = font_normal.render("LOG:", True, (150, 150, 170))
        superficie.blit(log_header, (x + pad, cy))
        cy += log_header.get_height() + 4

        for linha_log in log_combate[-8:]:
            if cy + 16 > h_tela - 46:
                break
            cor = (180, 180, 180)
            if "CRÍTICO" in linha_log:       cor = (255, 220, 0)
            if "🔥" in linha_log:            cor = (255, 100, 20)
            if "FUMBLE" in linha_log:        cor = (220, 60, 60)
            if "morr" in linha_log.lower():  cor = (180, 50, 50)
            if "cura" in linha_log.lower():  cor = (80, 200, 80)

            # Quebra linha longa
            max_chars = max(1, (largura - pad * 2) // 7)
            while len(linha_log) > max_chars:
                parte, linha_log = linha_log[:max_chars], linha_log[max_chars:]
                tl = font_normal.render(parte, True, cor)
                superficie.blit(tl, (x + pad, cy))
                cy += tl.get_height()
            tl = font_normal.render(linha_log, True, cor)
            superficie.blit(tl, (x + pad, cy))
            cy += tl.get_height() + 1
