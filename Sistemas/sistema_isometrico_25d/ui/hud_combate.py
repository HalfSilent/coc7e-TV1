"""
ui/hud_combate.py — HUD de combate por turnos.

Painel lateral direito:  ordem de turnos, AP, log de eventos.
Barra inferior:          botões de ação (Mover, Atacar, Recarregar…).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import pygame

if TYPE_CHECKING:
    from engine.combate.gerenciador import GerenciadorCombate, Acao

# ── Paleta (consistente com menu_pygame.py) ────────────────────────────
C_FUNDO   = (15,  12,  25, 210)
C_OURO    = (212, 168,  67)
C_OURO_E  = (255, 210,  90)
C_DIM     = ( 70,  62,  50)
C_VERDE   = ( 78, 204, 163)
C_VERMELHO= (220,  80,  80)
C_BRANCO  = (220, 215, 200)
C_BORDA   = ( 50,  44,  35)


class HudCombate:
    def __init__(self, tela: pygame.Surface,
                 largura_tela: int, altura_tela: int,
                 gerenciador_assets=None):
        self.tela  = tela
        self.larg  = largura_tela
        self.alt   = altura_tela

        self.painel_w = 250
        self.painel_x = largura_tela - self.painel_w - 8
        self.painel_y = 8

        # Fontes — reutiliza gerenciador_assets se disponível
        if gerenciador_assets:
            self.fn_titulo  = gerenciador_assets.get_font("titulo", 14)
            self.fn_texto   = gerenciador_assets.get_font("hud",    14)
            self.fn_pequeno = gerenciador_assets.get_font("hud",    12)
        else:
            pygame.font.init()
            self.fn_titulo  = pygame.font.SysFont("monospace", 13, bold=True)
            self.fn_texto   = pygame.font.SysFont("monospace", 13)
            self.fn_pequeno = pygame.font.SysFont("monospace", 11)

        self.log_msgs: List[str] = []
        self.max_log   = 7
        self._botoes:  List[dict] = []

    # ── Log ───────────────────────────────────────────────────

    def adicionar_log(self, msg: str):
        self.log_msgs.append(msg)
        if len(self.log_msgs) > self.max_log:
            self.log_msgs.pop(0)

    # ── Desenho principal ─────────────────────────────────────

    def desenhar(self, gerenciador: "GerenciadorCombate"):
        from engine.combate.gerenciador import (
            EstadoCombate, ACOES_PADRAO, TipoAcao
        )
        if not gerenciador.em_combate:
            return

        self._desenhar_painel(gerenciador)
        if gerenciador.estado in (EstadoCombate.TURNO_JOGADOR,
                                   EstadoCombate.ESCOLHENDO_ALVO):
            self._desenhar_botoes(gerenciador)

    def _desenhar_painel(self, gerenciador):
        h_painel = min(460, self.alt - 20)
        painel   = pygame.Surface((self.painel_w, h_painel), pygame.SRCALPHA)
        painel.fill(C_FUNDO)
        pygame.draw.rect(painel, C_BORDA, painel.get_rect(), 1)

        y = 10

        # Título
        t = self.fn_titulo.render("⚔  COMBATE", True, C_OURO_E)
        painel.blit(t, (self.painel_w // 2 - t.get_width() // 2, y))
        y += t.get_height() + 3
        pygame.draw.line(painel, C_DIM, (8, y), (self.painel_w - 8, y))
        y += 7

        # Rodada
        r = self.fn_texto.render(f"Rodada {gerenciador.turno_atual}", True, C_BRANCO)
        painel.blit(r, (10, y))
        y += r.get_height() + 8

        # Participante ativo + AP
        p = gerenciador.participante_ativo
        if p:
            nome_t = self.fn_texto.render(f"Vez de: {p.nome}", True, C_VERDE)
            painel.blit(nome_t, (10, y))
            y += nome_t.get_height() + 4

            ap_t = self.fn_pequeno.render(f"AP: {p.ap_atual}/{p.ap_maximo}", True, C_OURO)
            painel.blit(ap_t, (10, y))
            y += ap_t.get_height() + 2

            # Quadradinhos de AP
            for i in range(p.ap_maximo):
                cor = C_VERDE if i < p.ap_atual else C_DIM
                pygame.draw.rect(painel, cor, (10 + i * 22, y, 18, 12), border_radius=2)
            y += 18

        pygame.draw.line(painel, C_DIM, (8, y), (self.painel_w - 8, y))
        y += 7

        # Ordem de turnos
        ot = self.fn_pequeno.render("INICIATIVA:", True, C_DIM)
        painel.blit(ot, (10, y))
        y += ot.get_height() + 2

        for i, part in enumerate(gerenciador.participantes):
            if not part.vivo:
                continue
            ativo  = (i == gerenciador.idx_ativo)
            prefx  = "▶ " if ativo else "  "
            hp_txt = f"HP {part.entidade.hp}/{part.entidade.hp_max}"
            linha  = self.fn_pequeno.render(
                f"{prefx}{part.nome:<12} {hp_txt}", True,
                C_OURO_E if ativo else C_BRANCO
            )
            painel.blit(linha, (10, y))
            y += linha.get_height() + 1

        y += 6
        pygame.draw.line(painel, C_DIM, (8, y), (self.painel_w - 8, y))
        y += 7

        # Log
        log_t = self.fn_pequeno.render("LOG:", True, C_DIM)
        painel.blit(log_t, (10, y))
        y += log_t.get_height() + 2

        for msg in self.log_msgs:
            # Trunca se muito longo
            if len(msg) > 32:
                msg = msg[:30] + "…"
            l = self.fn_pequeno.render(msg, True, (150, 140, 120))
            painel.blit(l, (10, y))
            y += l.get_height() + 1
            if y > h_painel - 10:
                break

        self.tela.blit(painel, (self.painel_x, self.painel_y))

    # ── Botões de ação ────────────────────────────────────────

    def _desenhar_botoes(self, gerenciador):
        from engine.combate.gerenciador import ACOES_PADRAO, EstadoCombate

        self._botoes = []
        p       = gerenciador.participante_ativo
        n       = len(ACOES_PADRAO)
        btn_w   = 110
        btn_h   = 42
        gap     = 8
        total_w = n * btn_w + (n - 1) * gap
        sx      = (self.larg - total_w) // 2
        by      = self.alt - btn_h - 12

        # Fundo da barra
        barra = pygame.Surface((total_w + 24, btn_h + 18), pygame.SRCALPHA)
        barra.fill((10, 8, 20, 190))
        pygame.draw.rect(barra, C_BORDA, barra.get_rect(), 1)
        self.tela.blit(barra, (sx - 12, by - 8))

        for i, acao in enumerate(ACOES_PADRAO):
            x    = sx + i * (btn_w + gap)
            pode = p and p.ap_atual >= acao.custo_ap
            ativo = (gerenciador.estado == EstadoCombate.ESCOLHENDO_ALVO
                     and gerenciador.acao_selecionada
                     and gerenciador.acao_selecionada.tipo == acao.tipo)

            cor_fundo = (35, 28, 55, 200) if ativo else (20, 16, 35, 200)
            cor_borda = C_OURO_E if ativo else (C_OURO if pode else C_DIM)
            cor_texto = C_BRANCO if pode else C_DIM

            btn = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            btn.fill(cor_fundo)
            pygame.draw.rect(btn, cor_borda, btn.get_rect(), 1, border_radius=4)

            label = self.fn_pequeno.render(acao.tipo.value, True, cor_texto)
            ap_l  = self.fn_pequeno.render(
                f"({acao.custo_ap} AP)", True, C_OURO if pode else C_DIM
            )
            btn.blit(label, (btn_w // 2 - label.get_width() // 2, 7))
            btn.blit(ap_l,  (btn_w // 2 - ap_l.get_width()  // 2, 22))

            self.tela.blit(btn, (x, by))
            self._botoes.append({
                "rect": pygame.Rect(x, by, btn_w, btn_h),
                "acao": acao,
            })

        # Dica de teclado
        dica = self.fn_pequeno.render(
            "ESPAÇO: passar turno  |  ESC: cancelar", True, C_DIM
        )
        self.tela.blit(dica, (
            self.larg // 2 - dica.get_width() // 2,
            by + btn_h + 4
        ))

    def checar_clique(self, pos: tuple) -> "Optional[Acao]":
        """Retorna Acao clicada ou None."""
        for btn in self._botoes:
            if btn["rect"].collidepoint(pos):
                return btn["acao"]
        return None

    # ── Overlay de estado fora de combate ─────────────────────

    def desenhar_status_exploracao(self, jogador,
                                    fonte: Optional[pygame.font.Font] = None):
        """Barra mínima de HP/SAN durante exploração."""
        fn = fonte or self.fn_pequeno
        txt = (f"HP {jogador.hp}/{jogador.hp_max}  "
               f"SAN {jogador.sanidade}/{jogador.san_max}")
        surf = fn.render(txt, True, C_OURO)
        self.tela.blit(surf, (10, self.alt - surf.get_height() - 10))
