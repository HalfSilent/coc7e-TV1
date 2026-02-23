"""
editor/widgets.py — Widgets mínimos de UI para o editor de campanhas.

Todos os widgets recebem a `tela` principal (ou um subsurface) e desenham
diretamente nela. Nenhuma dependência além de pygame.

Widgets disponíveis:
    CaixaTexto     — input de uma linha com cursor e seleção básica
    TextoMultilinha — texto dividido em linhas (read-only ou edição simples)
    Botao          — botão retangular clicável
    ListaSelecao   — lista vertical de itens clicáveis
    Ciclico        — valor com setas ◀ ▶ para escolha entre opções
    SliderInt      — barra deslizante para inteiros
    MiniMapa       — visualização 2-D simples de tiles (sem iso)
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import pygame


# ── Paleta padrão ─────────────────────────────────────────────
_C = {
    "fundo":      (18,  22,  38),
    "painel":     (26,  32,  56),
    "borda":      (55,  70, 110),
    "borda_ativa":(100, 140, 220),
    "texto":      (220, 215, 200),
    "texto_dim":  (110, 108,  98),
    "destaque":   ( 80, 140, 220),
    "hover":      ( 40,  55,  90),
    "sel":        ( 55,  90, 155),
    "erro":       (220,  70,  70),
    "ok":         ( 70, 200, 120),
    "acento":     (220,  80,  90),
}


def _fonte_padrao(size: int = 14) -> pygame.font.Font:
    return pygame.font.SysFont("monospace", size)


# ══════════════════════════════════════════════════════════════
# CAIXA DE TEXTO — input de uma linha
# ══════════════════════════════════════════════════════════════

class CaixaTexto:
    """
    Input de texto de uma linha.

    Uso:
        cx = CaixaTexto(rect, placeholder="Nome...", fonte=fn)
        # No loop de eventos:
        cx.processar_evento(event)
        # No render:
        cx.desenhar(tela)
        valor = cx.texto
    """

    def __init__(self, rect: pygame.Rect,
                 texto: str = "",
                 placeholder: str = "",
                 fonte: Optional[pygame.font.Font] = None,
                 max_len: int = 120):
        self.rect        = pygame.Rect(rect)
        self.texto       = texto
        self.placeholder = placeholder
        self.fonte       = fonte or _fonte_padrao(13)
        self.max_len     = max_len
        self.ativa       = False
        self._cursor     = len(texto)
        self._tick       = 0

    def processar_evento(self, e: pygame.event.Event) -> bool:
        """Retorna True se o evento foi consumido."""
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ativa = self.rect.collidepoint(e.pos)
            if self.ativa:
                self._cursor = len(self.texto)
            return self.ativa

        if not self.ativa:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                if self._cursor > 0:
                    self.texto   = self.texto[:self._cursor-1] + self.texto[self._cursor:]
                    self._cursor = max(0, self._cursor - 1)
            elif e.key == pygame.K_DELETE:
                self.texto = self.texto[:self._cursor] + self.texto[self._cursor+1:]
            elif e.key == pygame.K_LEFT:
                self._cursor = max(0, self._cursor - 1)
            elif e.key == pygame.K_RIGHT:
                self._cursor = min(len(self.texto), self._cursor + 1)
            elif e.key == pygame.K_HOME:
                self._cursor = 0
            elif e.key == pygame.K_END:
                self._cursor = len(self.texto)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.ativa = False
            elif e.unicode and len(self.texto) < self.max_len:
                ch = e.unicode
                if ord(ch) >= 32:  # imprimível
                    self.texto   = self.texto[:self._cursor] + ch + self.texto[self._cursor:]
                    self._cursor += 1
            return True

        return False

    def desenhar(self, tela: pygame.Surface):
        cor_borda = _C["borda_ativa"] if self.ativa else _C["borda"]
        pygame.draw.rect(tela, _C["painel"], self.rect, border_radius=4)
        pygame.draw.rect(tela, cor_borda,   self.rect, width=1, border_radius=4)

        if self.texto:
            surf = self.fonte.render(self.texto, True, _C["texto"])
        else:
            surf = self.fonte.render(self.placeholder, True, _C["texto_dim"])
        tela.blit(surf, (self.rect.x + 6, self.rect.centery - surf.get_height() // 2))

        # Cursor piscante
        self._tick = (self._tick + 1) % 60
        if self.ativa and self._tick < 30:
            pre  = self.fonte.render(self.texto[:self._cursor], True, _C["texto"])
            cx   = self.rect.x + 6 + pre.get_width()
            cy1  = self.rect.y + 4
            cy2  = self.rect.bottom - 4
            pygame.draw.line(tela, _C["borda_ativa"], (cx, cy1), (cx, cy2), 1)


# ══════════════════════════════════════════════════════════════
# TEXTO MULTILINHAS
# ══════════════════════════════════════════════════════════════

class CaixaTextoMulti:
    """
    Área de edição de texto multilinhas simples.
    Linhas separadas por '\\n'. Navegação com Enter, Backspace.
    """

    def __init__(self, rect: pygame.Rect,
                 texto: str = "",
                 fonte: Optional[pygame.font.Font] = None,
                 max_chars: int = 500):
        self.rect      = pygame.Rect(rect)
        self.texto     = texto
        self.fonte     = fonte or _fonte_padrao(12)
        self.max_chars = max_chars
        self.ativa     = False
        self._tick     = 0

    @property
    def linhas(self) -> List[str]:
        return self.texto.split("\n")

    def processar_evento(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ativa = self.rect.collidepoint(e.pos)
            return self.ativa

        if not self.ativa:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if len(self.texto) < self.max_chars:
                    self.texto += "\n"
            elif e.unicode and len(self.texto) < self.max_chars:
                ch = e.unicode
                if ord(ch) >= 32:
                    self.texto += ch
            return True

        return False

    def desenhar(self, tela: pygame.Surface):
        cor_borda = _C["borda_ativa"] if self.ativa else _C["borda"]
        pygame.draw.rect(tela, _C["painel"], self.rect, border_radius=4)
        pygame.draw.rect(tela, cor_borda,   self.rect, width=1, border_radius=4)

        lh = self.fonte.get_height() + 2
        y  = self.rect.y + 5
        for linha in self.linhas:
            if y + lh > self.rect.bottom:
                break
            surf = self.fonte.render(linha, True, _C["texto"])
            tela.blit(surf, (self.rect.x + 6, y))
            y += lh

        # Cursor simples no final
        self._tick = (self._tick + 1) % 60
        if self.ativa and self._tick < 30:
            last = self.linhas[-1] if self.linhas else ""
            pre  = self.fonte.render(last, True, _C["texto"])
            num_linhas = len(self.linhas)
            cx = self.rect.x + 6 + pre.get_width()
            cy = self.rect.y + 5 + (num_linhas - 1) * lh
            pygame.draw.line(tela, _C["borda_ativa"],
                             (cx, cy), (cx, cy + self.fonte.get_height()), 1)


# ══════════════════════════════════════════════════════════════
# BOTÃO
# ══════════════════════════════════════════════════════════════

class Botao:
    def __init__(self, rect: pygame.Rect, texto: str,
                 cor: Tuple = _C["destaque"],
                 fonte: Optional[pygame.font.Font] = None,
                 callback: Optional[Callable] = None):
        self.rect     = pygame.Rect(rect)
        self.texto    = texto
        self.cor      = cor
        self.fonte    = fonte or _fonte_padrao(13)
        self.callback = callback
        self._hover   = False

    def processar_evento(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def desenhar(self, tela: pygame.Surface):
        cor = tuple(min(255, c + 35) for c in self.cor) if self._hover else self.cor
        pygame.draw.rect(tela, cor,        self.rect, border_radius=5)
        pygame.draw.rect(tela, _C["borda"], self.rect, width=1, border_radius=5)
        surf = self.fonte.render(self.texto, True, _C["texto"])
        tela.blit(surf, surf.get_rect(center=self.rect.center))


# ══════════════════════════════════════════════════════════════
# LISTA DE SELEÇÃO
# ══════════════════════════════════════════════════════════════

class ListaSelecao:
    """
    Lista vertical de strings. Clique seleciona item (índice).
    `on_selecao(idx)` chamado ao selecionar.
    """

    def __init__(self, rect: pygame.Rect,
                 itens: Optional[List[str]] = None,
                 altura_item: int = 26,
                 fonte: Optional[pygame.font.Font] = None,
                 on_selecao: Optional[Callable[[int], None]] = None):
        self.rect        = pygame.Rect(rect)
        self.itens       = itens or []
        self.altura_item = altura_item
        self.fonte       = fonte or _fonte_padrao(13)
        self.on_selecao  = on_selecao
        self.selecionado: Optional[int] = None
        self._scroll     = 0
        self._hover      = -1

    def processar_evento(self, e: pygame.event.Event) -> bool:
        if not self.rect.collidepoint(getattr(e, "pos", (-1, -1))):
            return False

        if e.type == pygame.MOUSEMOTION:
            idx = self._pos_para_idx(e.pos[1])
            self._hover = idx if idx is not None else -1

        if e.type == pygame.MOUSEWHEEL:
            max_scroll = max(0, len(self.itens) - self._itens_visiveis())
            self._scroll = max(0, min(max_scroll, self._scroll - e.y))
            return True

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            idx = self._pos_para_idx(e.pos[1])
            if idx is not None:
                self.selecionado = idx
                if self.on_selecao:
                    self.on_selecao(idx)
                return True

        return False

    def _itens_visiveis(self) -> int:
        return self.rect.height // self.altura_item

    def _pos_para_idx(self, y: int) -> Optional[int]:
        ry = y - self.rect.y
        if ry < 0:
            return None
        idx = self._scroll + ry // self.altura_item
        if 0 <= idx < len(self.itens):
            return idx
        return None

    def desenhar(self, tela: pygame.Surface):
        pygame.draw.rect(tela, _C["painel"], self.rect)
        pygame.draw.rect(tela, _C["borda"],  self.rect, width=1)

        vis = self._itens_visiveis()
        for i in range(vis):
            idx = self._scroll + i
            if idx >= len(self.itens):
                break
            ry = self.rect.y + i * self.altura_item
            item_rect = pygame.Rect(self.rect.x, ry, self.rect.width, self.altura_item)

            if idx == self.selecionado:
                pygame.draw.rect(tela, _C["sel"], item_rect)
            elif idx == self._hover:
                pygame.draw.rect(tela, _C["hover"], item_rect)

            surf = self.fonte.render(str(self.itens[idx]), True, _C["texto"])
            tela.blit(surf, (item_rect.x + 8, item_rect.centery - surf.get_height() // 2))

        # Barra de scroll
        total = len(self.itens)
        if total > vis:
            bar_h  = max(20, self.rect.height * vis // total)
            bar_y  = self.rect.y + self._scroll * (self.rect.height - bar_h) // max(1, total - vis)
            bar_r  = pygame.Rect(self.rect.right - 5, bar_y, 4, bar_h)
            pygame.draw.rect(tela, _C["borda"], bar_r, border_radius=2)


# ══════════════════════════════════════════════════════════════
# CICLICO — ◀ valor ▶
# ══════════════════════════════════════════════════════════════

class Ciclico:
    """Widget ◀ opção ▶ para navegar por uma lista de opções."""

    def __init__(self, rect: pygame.Rect,
                 opcoes: List[Any],
                 indice: int = 0,
                 fonte: Optional[pygame.font.Font] = None,
                 on_mudanca: Optional[Callable[[Any], None]] = None):
        self.rect      = pygame.Rect(rect)
        self.opcoes    = opcoes
        self.indice    = indice % max(1, len(opcoes))
        self.fonte     = fonte or _fonte_padrao(13)
        self.on_mudanca = on_mudanca
        bw = 22
        self._btn_esq = pygame.Rect(rect.x, rect.y, bw, rect.height)
        self._btn_dir = pygame.Rect(rect.right - bw, rect.y, bw, rect.height)

    @property
    def valor(self) -> Any:
        return self.opcoes[self.indice] if self.opcoes else None

    def processar_evento(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self._btn_esq.collidepoint(e.pos):
                self.indice = (self.indice - 1) % len(self.opcoes)
                if self.on_mudanca:
                    self.on_mudanca(self.valor)
                return True
            if self._btn_dir.collidepoint(e.pos):
                self.indice = (self.indice + 1) % len(self.opcoes)
                if self.on_mudanca:
                    self.on_mudanca(self.valor)
                return True
        return False

    def desenhar(self, tela: pygame.Surface):
        pygame.draw.rect(tela, _C["painel"], self.rect, border_radius=4)
        pygame.draw.rect(tela, _C["borda"],  self.rect, width=1, border_radius=4)

        for btn, txt in ((self._btn_esq, "◀"), (self._btn_dir, "▶")):
            s = self.fonte.render(txt, True, _C["destaque"])
            tela.blit(s, s.get_rect(center=btn.center))

        if self.opcoes:
            label = str(self.opcoes[self.indice])
            s = self.fonte.render(label, True, _C["texto"])
            tela.blit(s, s.get_rect(center=self.rect.center))


# ══════════════════════════════════════════════════════════════
# SLIDER INT
# ══════════════════════════════════════════════════════════════

class SliderInt:
    """Barra deslizante para valores inteiros [min_val, max_val]."""

    def __init__(self, rect: pygame.Rect,
                 min_val: int = 0, max_val: int = 100, valor: int = 50,
                 fonte: Optional[pygame.font.Font] = None,
                 on_mudanca: Optional[Callable[[int], None]] = None):
        self.rect      = pygame.Rect(rect)
        self.min_val   = min_val
        self.max_val   = max_val
        self.valor     = max(min_val, min(max_val, valor))
        self.fonte     = fonte or _fonte_padrao(12)
        self.on_mudanca = on_mudanca
        self._arrastando = False

    def _valor_de_x(self, x: int) -> int:
        rel = (x - self.rect.x) / max(1, self.rect.width)
        v   = int(self.min_val + rel * (self.max_val - self.min_val))
        return max(self.min_val, min(self.max_val, v))

    def processar_evento(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                self._arrastando = True
                self.valor = self._valor_de_x(e.pos[0])
                if self.on_mudanca:
                    self.on_mudanca(self.valor)
                return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self._arrastando = False
        if e.type == pygame.MOUSEMOTION and self._arrastando:
            self.valor = self._valor_de_x(e.pos[0])
            if self.on_mudanca:
                self.on_mudanca(self.valor)
            return True
        return False

    def desenhar(self, tela: pygame.Surface):
        # Trilha
        trilha = pygame.Rect(self.rect.x, self.rect.centery - 3,
                             self.rect.width, 6)
        pygame.draw.rect(tela, _C["borda"], trilha, border_radius=3)

        # Preenchimento
        pct  = (self.valor - self.min_val) / max(1, self.max_val - self.min_val)
        fill = pygame.Rect(self.rect.x, self.rect.centery - 3,
                           int(self.rect.width * pct), 6)
        pygame.draw.rect(tela, _C["destaque"], fill, border_radius=3)

        # Polegar
        thumb_x = self.rect.x + int(self.rect.width * pct)
        pygame.draw.circle(tela, _C["texto"], (thumb_x, self.rect.centery), 7)
        pygame.draw.circle(tela, _C["borda"],  (thumb_x, self.rect.centery), 7, 1)

        # Valor
        s = self.fonte.render(str(self.valor), True, _C["texto"])
        tela.blit(s, (self.rect.right + 5, self.rect.centery - s.get_height() // 2))


# ══════════════════════════════════════════════════════════════
# LABEL
# ══════════════════════════════════════════════════════════════

def label(tela: pygame.Surface, texto: str, pos: Tuple[int, int],
          fonte: Optional[pygame.font.Font] = None,
          cor: Tuple = _C["texto"],
          alinha: str = "left"):
    """Renderiza texto simples. alinha: 'left' | 'center' | 'right'."""
    fn = fonte or _fonte_padrao(13)
    surf = fn.render(texto, True, cor)
    if alinha == "center":
        tela.blit(surf, surf.get_rect(centerx=pos[0], y=pos[1]))
    elif alinha == "right":
        tela.blit(surf, surf.get_rect(right=pos[0], y=pos[1]))
    else:
        tela.blit(surf, pos)
