"""
mundo/tela_local.py — Painel de descrição e ações de um local.

Exibe:
  - Imagem/arte do local (futuramente — por agora, painel colorido)
  - Nome do local + hora do dia
  - Texto atmosférico com rolagem se longo
  - Lista de ações com teclas [Letra]
  - Status do investigador no rodapé (HP, SAN, Dinheiro, Hora)

Retorna quando o jogador escolhe uma ação:
    {"tipo": "ir",       "destino": "biblioteca"}
    {"tipo": "masmorra", "destino": "catacumbas_porto"}
    {"tipo": "info",     "texto": "..."}
    {"tipo": "descanso", "custo": 3}
    {"tipo": "sair"}     — Esc/voltar
"""
from __future__ import annotations

import sys
import textwrap
from typing import Optional

import pygame

from mundo.locais import Local, Acao, LOCAIS, get_local
from gerenciador_assets import get_font, garantir_fontes


# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

COR_BG            = (12, 12, 18)
COR_PAINEL_DESC   = (20, 20, 30)
COR_PAINEL_ACOES  = (15, 18, 25)
COR_BORDA         = (60, 60, 90)
COR_TITULO        = (212, 180, 100)
COR_TEXTO         = (180, 175, 165)
COR_ACAO_NORMAL   = (140, 140, 160)
COR_ACAO_HOVER    = (220, 200, 140)
COR_ACAO_BG       = (28, 30, 42)
COR_ACAO_BG_HOVER = (40, 42, 60)
COR_HORA          = (120, 160, 200)
COR_HP_OK         = (80, 200, 80)
COR_HP_BAIXO      = (220, 80, 80)
COR_SAN_OK        = (100, 160, 220)
COR_SAN_BAIXO     = (180, 80, 220)
COR_DINHEIRO      = (200, 180, 80)


# ══════════════════════════════════════════════════════════════
# TELA DE LOCAL
# ══════════════════════════════════════════════════════════════

class TelaLocal:
    """
    Exibe um local com sua descrição e ações disponíveis.
    Estilo TORN — texto-first, menus de letras.
    """

    def __init__(self, screen: pygame.Surface, local_id: str):
        self.screen   = screen
        self.clock    = pygame.time.Clock()
        self.local_id = local_id
        self.local    = get_local(local_id)

        garantir_fontes()
        self.f_titulo  = get_font("titulo", 26)
        self.f_subtit  = get_font("titulo", 18)
        self.f_texto   = get_font("narrativa", 18)
        self.f_acao    = get_font("hud", 17)
        self.f_hud     = get_font("hud", 15)

        w, h = screen.get_size()
        # Painel esquerdo: descrição (60% da largura)
        self.desc_rect  = pygame.Rect(20, 60, int(w * 0.60), h - 110)
        # Painel direito: ações (38% da largura)
        self.acoes_rect = pygame.Rect(int(w * 0.63), 60, int(w * 0.35), h - 110)

        # Texto de resultado de ação
        self._resultado_acao: Optional[str] = None
        self._resultado_scroll = 0

        # Hover sobre ações
        self._hover_idx: Optional[int] = None

    # ══════════════════════════════════════════════════════════
    # LOOP
    # ══════════════════════════════════════════════════════════

    def run(self,
            hp: int = 10, hp_max: int = 10,
            sanidade: int = 60, san_max: int = 60,
            dinheiro: int = 10,
            hora: int = 10) -> dict:
        """
        Exibe o local e espera uma ação do jogador.
        Retorna dict com a ação escolhida.
        """
        self._resultado_acao = None
        self._resultado_scroll = 0

        while True:
            self.clock.tick(60)

            mx, my = pygame.mouse.get_pos()
            self._hover_idx = self._acao_sob_cursor(mx, my)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    resultado = self._processar_tecla(event.key)
                    if resultado:
                        return resultado

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    resultado = self._click_acao(mx, my)
                    if resultado:
                        return resultado

                elif event.type == pygame.MOUSEWHEEL:
                    if self._resultado_acao:
                        self._resultado_scroll -= event.y * 20

            self._renderizar(hp, hp_max, sanidade, san_max, dinheiro, hora)

    # ══════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════

    def _processar_tecla(self, key: int) -> Optional[dict]:
        if not self.local:
            return {"tipo": "sair"}

        if key == pygame.K_ESCAPE:
            if self._resultado_acao:
                # Fecha painel de resultado
                self._resultado_acao = None
                return None
            return {"tipo": "sair"}

        # Tecla de ação
        char = pygame.key.name(key).upper()
        for acao in self.local.acoes:
            if acao.tecla.upper() == char:
                return self._executar_acao(acao)

        return None

    def _click_acao(self, mx: int, my: int) -> Optional[dict]:
        idx = self._acao_sob_cursor(mx, my)
        if idx is not None and self.local and idx < len(self.local.acoes):
            return self._executar_acao(self.local.acoes[idx])

        # Click fora do resultado fecha o painel
        if self._resultado_acao:
            res_rect = self._rect_resultado()
            if not res_rect.collidepoint(mx, my):
                self._resultado_acao = None

        return None

    def _executar_acao(self, acao: Acao) -> Optional[dict]:
        """Processa a ação e retorna dict de resultado ou None se apenas exibe texto."""
        if acao.tipo == "ir":
            return {"tipo": "ir", "destino": acao.destino}

        if acao.tipo == "masmorra":
            return {"tipo": "masmorra", "destino": acao.destino,
                    "descricao": acao.descricao}

        if acao.tipo == "explorar":
            return {"tipo": "explorar", "destino": acao.destino,
                    "descricao": acao.descricao}

        if acao.tipo in ("info", "pericia"):
            self._resultado_acao = acao.descricao
            self._resultado_scroll = 0
            return None  # não sai, mostra texto

        if acao.tipo == "descanso":
            return {"tipo": "descanso", "custo": acao.custo_dinheiro,
                    "descricao": acao.descricao}

        if acao.tipo == "comprar":
            return {"tipo": "comprar", "custo": acao.custo_dinheiro,
                    "descricao": acao.descricao, "item": acao.destino}

        return None

    def _acao_sob_cursor(self, mx: int, my: int) -> Optional[int]:
        if not self.local:
            return None
        y = self.acoes_rect.top + 44
        for i, acao in enumerate(self.local.acoes):
            r = pygame.Rect(self.acoes_rect.left, y, self.acoes_rect.width, 34)
            if r.collidepoint(mx, my):
                return i
            y += 38
        return None

    # ══════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self, hp, hp_max, san, san_max, dinheiro, hora):
        self.screen.fill(COR_BG)
        if not self.local:
            return

        self._desenhar_cabecalho(hora)
        self._desenhar_painel_descricao()
        self._desenhar_painel_acoes()
        self._desenhar_hud_status(hp, hp_max, san, san_max, dinheiro, hora)

        if self._resultado_acao is not None:
            self._desenhar_resultado()

        pygame.display.flip()

    def _desenhar_cabecalho(self, hora: int):
        w, _ = self.screen.get_size()
        pygame.draw.rect(self.screen, (18, 18, 28), (0, 0, w, 55))
        pygame.draw.line(self.screen, COR_BORDA, (0, 55), (w, 55), 1)

        # Nome do local
        nm = self.f_titulo.render(self.local.nome, True, COR_TITULO)
        self.screen.blit(nm, (20, 12))

        # Hora
        sufixo = "h"
        periodo = "Manhã" if 6 <= hora < 12 else "Tarde" if hora < 18 else "Noite" if hora < 22 else "Madrugada"
        hora_txt = self.f_hud.render(f"{hora:02d}:00 — {periodo}", True, COR_HORA)
        self.screen.blit(hora_txt, (w - hora_txt.get_width() - 20, 18))

    def _desenhar_painel_descricao(self):
        r = self.desc_rect
        pygame.draw.rect(self.screen, COR_PAINEL_DESC, r, border_radius=6)
        pygame.draw.rect(self.screen, COR_BORDA, r, 1, border_radius=6)

        # Título da seção
        sub = self.f_subtit.render("◈ Situação", True, (150, 140, 120))
        self.screen.blit(sub, (r.left + 14, r.top + 12))

        # Texto da descrição com quebra de linha
        y = r.top + 44
        max_chars = (r.width - 28) // 10
        linhas = []
        for paragrafo in self.local.descricao.split("\n"):
            linhas.extend(textwrap.wrap(paragrafo, max_chars) or [""])
            linhas.append("")  # linha em branco entre parágrafos

        clip_r = pygame.Rect(r.left + 1, r.top + 44, r.width - 2, r.height - 50)
        self.screen.set_clip(clip_r)

        for linha in linhas:
            if y > r.bottom - 20:
                break
            if linha:
                s = self.f_texto.render(linha, True, COR_TEXTO)
                self.screen.blit(s, (r.left + 14, y))
            y += 22

        self.screen.set_clip(None)

    def _desenhar_painel_acoes(self):
        r = self.acoes_rect
        pygame.draw.rect(self.screen, COR_PAINEL_ACOES, r, border_radius=6)
        pygame.draw.rect(self.screen, COR_BORDA, r, 1, border_radius=6)

        sub = self.f_subtit.render("◈ Ações", True, (150, 140, 120))
        self.screen.blit(sub, (r.left + 14, r.top + 12))

        y = r.top + 44
        for i, acao in enumerate(self.local.acoes):
            is_hover = (i == self._hover_idx)
            bg_cor = COR_ACAO_BG_HOVER if is_hover else COR_ACAO_BG
            txt_cor = COR_ACAO_HOVER   if is_hover else COR_ACAO_NORMAL

            rr = pygame.Rect(r.left + 8, y, r.width - 16, 30)
            pygame.draw.rect(self.screen, bg_cor, rr, border_radius=4)
            if is_hover:
                pygame.draw.rect(self.screen, (80, 80, 120), rr, 1, border_radius=4)

            # Tecla
            tecla_s = self.f_acao.render(f"[{acao.tecla}]", True, (160, 200, 120))
            self.screen.blit(tecla_s, (rr.left + 6, rr.top + 5))

            # Texto
            texto_s = self.f_acao.render(acao.texto, True, txt_cor)
            self.screen.blit(texto_s, (rr.left + 38, rr.top + 5))

            # Custo
            if acao.custo_dinheiro > 0:
                custo_s = self.f_hud.render(f"${acao.custo_dinheiro}", True, COR_DINHEIRO)
                self.screen.blit(custo_s, (rr.right - custo_s.get_width() - 6, rr.top + 7))

            y += 38

        # Dica
        if self.local.dica:
            dica_s = self.f_hud.render(self.local.dica, True, (70, 70, 100))
            self.screen.blit(dica_s, (r.left + 10, r.bottom - 22))

    def _desenhar_hud_status(self, hp, hp_max, san, san_max, dinheiro, hora):
        w, h = self.screen.get_size()
        pygame.draw.rect(self.screen, (18, 18, 28), (0, h - 48, w, 48))
        pygame.draw.line(self.screen, COR_BORDA, (0, h - 48), (w, h - 48), 1)

        # HP
        hp_cor = COR_HP_OK if hp > hp_max * 0.4 else COR_HP_BAIXO
        hp_s = self.f_hud.render(f"♥ HP: {hp}/{hp_max}", True, hp_cor)
        self.screen.blit(hp_s, (20, h - 34))

        # SAN
        san_cor = COR_SAN_OK if san > 20 else COR_SAN_BAIXO
        san_s = self.f_hud.render(f"☽ SAN: {san}/{san_max}", True, san_cor)
        self.screen.blit(san_s, (160, h - 34))

        # Dinheiro
        d_s = self.f_hud.render(f"$ {dinheiro}", True, COR_DINHEIRO)
        self.screen.blit(d_s, (310, h - 34))

        # Dica ESC
        esc_s = self.f_hud.render("[ESC] Voltar", True, (70, 70, 100))
        self.screen.blit(esc_s, (w - esc_s.get_width() - 20, h - 34))

    def _rect_resultado(self) -> pygame.Rect:
        w, h = self.screen.get_size()
        rw, rh = int(w * 0.65), int(h * 0.60)
        return pygame.Rect((w - rw) // 2, (h - rh) // 2, rw, rh)

    def _desenhar_resultado(self):
        """Painel flutuante com o texto de resultado da ação."""
        r = self._rect_resultado()
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, (18, 22, 32), r, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 140), r, 2, border_radius=8)

        # Rolagem de texto
        y = r.top + 16 - self._resultado_scroll
        max_chars = (r.width - 32) // 9
        linhas = []
        for para in (self._resultado_acao or "").split("\n"):
            linhas.extend(textwrap.wrap(para, max_chars) or [""])
            linhas.append("")

        clip_r = pygame.Rect(r.left + 1, r.top + 1, r.width - 2, r.height - 2)
        self.screen.set_clip(clip_r)

        for linha in linhas:
            if linha:
                s = self.f_texto.render(linha, True, (200, 195, 185))
                self.screen.blit(s, (r.left + 16, y))
            y += 22

        self.screen.set_clip(None)

        # Dica
        dica = self.f_hud.render("[ESC] Fechar  |  Scroll para rolar", True, (80, 80, 110))
        dr = dica.get_rect(centerx=r.centerx, bottom=r.bottom - 8)
        self.screen.blit(dica, dr)
