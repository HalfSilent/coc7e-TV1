"""
ui/tela_selecionar_local.py — Seletor do local de início.

Exibido após a criação de personagem.
O jogador escolhe em qual distrito de Arkham começa a aventura.

.run() → str (local_id escolhido)
Pressionar Esc ou clicar no botão padrão → "rua_central"
"""
from __future__ import annotations

import math
import os
import sys

import pygame

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import gerenciador_assets as _ga

# ══════════════════════════════════════════════════════════════
# DADOS DOS LOCAIS DE INÍCIO
# ══════════════════════════════════════════════════════════════

_LOCAIS: list[dict] = [
    {
        "id":        "rua_central",
        "nome":      "Rua Central",
        "subtitulo": "O coração de Arkham",
        "descricao": (
            "O hub central da cidade — todas as rotas partem daqui.\n"
            "Comece com tempo para observar e escolher seu primeiro destino.\n"
            "Ideal para um início mais calmo e planejado."
        ),
        "dica":   "Para qualquer arquétipo  ·  Começo neutro",
        "cor":    (40, 45, 55),
        "icone":  "⊕",
    },
    {
        "id":        "biblioteca",
        "nome":      "Biblioteca Orne",
        "subtitulo": "Pesquisa e tomos antigos",
        "descricao": (
            "Onde os segredos de Arkham estão registrados.\n"
            "Acesso imediato a pesquisas e ao 'De Vermis Mysteriis'.\n"
            "A Sra. Marsh sabe mais do que aparenta."
        ),
        "dica":   "Ideal para Escritores e Arqueólogos",
        "cor":    (50, 40, 28),
        "icone":  "≡",
    },
    {
        "id":        "estalagem",
        "nome":      "Estalagem 'A Âncora'",
        "subtitulo": "Rumores e descanso",
        "descricao": (
            "Boatos circulam livremente entre os frequentadores bêbados.\n"
            "Descanse antes de começar a investigação.\n"
            "Os clientes sabem de coisas que a polícia ignora."
        ),
        "dica":   "Ideal para Detetives  ·  Descanso disponível",
        "cor":    (52, 40, 20),
        "icone":  "⚓",
    },
    {
        "id":        "delegacia",
        "nome":      "Delegacia",
        "subtitulo": "Autoridade e registros",
        "descricao": (
            "O Det. Malone tem arquivos sobre os desaparecidos.\n"
            "Acesso a informações oficiais antes de qualquer outra pista.\n"
            "Mas ele só compartilha com quem merece confiança."
        ),
        "dica":   "Ideal para Detetives e Soldados",
        "cor":    (50, 46, 34),
        "icone":  "★",
    },
    {
        "id":        "porto",
        "nome":      "Porto de Arkham",
        "subtitulo": "Investigação perigosa",
        "descricao": (
            "Os rastros mais frescos dos desaparecimentos levam até cá.\n"
            "Início mais arriscado — mas rico em evidências concretas.\n"
            "As docas escondem a entrada para as catacumbas."
        ),
        "dica":   "Ideal para Soldados  ·  PERIGO IMEDIATO",
        "cor":    (26, 42, 52),
        "icone":  "◈",
    },
    {
        "id":        "universidade",
        "nome":      "Universidade Miskatonic",
        "subtitulo": "Conhecimento e tomos proibidos",
        "descricao": (
            "O Prof. Armitage sabe tudo sobre Walter Corbitt.\n"
            "Acesso a conhecimento oculto antes de arriscar o pescoço.\n"
            "Ideal para quem quer entender antes de agir."
        ),
        "dica":   "Ideal para Médicos e Arqueólogos",
        "cor":    (34, 34, 56),
        "icone":  "⊙",
    },
]


# ══════════════════════════════════════════════════════════════
# LAYOUT — GRID 3×2
# ══════════════════════════════════════════════════════════════

_W, _H = 1280, 720
_CARD_W, _CARD_H = 350, 140
_GAP_X, _GAP_Y   = 24,  18
_COLS             = 3

# Grid starts x
_GRID_W = _COLS * _CARD_W + (_COLS - 1) * _GAP_X  # 1098
_GRID_X = (_W - _GRID_W) // 2                       # 91
_GRID_Y = 148


def _card_rect(idx: int) -> pygame.Rect:
    col = idx % _COLS
    row = idx // _COLS
    x   = _GRID_X + col * (_CARD_W + _GAP_X)
    y   = _GRID_Y + row * (_CARD_H + _GAP_Y)
    return pygame.Rect(x, y, _CARD_W, _CARD_H)


# ══════════════════════════════════════════════════════════════
# TELA
# ══════════════════════════════════════════════════════════════

class TelaSelecionarLocal:
    """
    Tela de seleção do local de início após criar o personagem.

    .run() retorna o local_id escolhido (default "rua_central").
    """

    C_FUNDO  = ( 10,   8,  18)
    C_PAINEL = ( 22,  33,  62)
    C_TEXTO  = (238, 226, 220)
    C_DIM    = (154, 140, 152)
    C_OURO   = (212, 168,  67)
    C_VERDE  = ( 78, 204, 163)
    C_ACENTO = (233,  69,  96)

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock,
                 nome_jogador: str = ""):
        self.screen        = screen
        self.clock         = clock
        self.nome_jogador  = nome_jogador
        _ga.garantir_fontes(verbose=False)

        self.f_titulo = _ga.get_font("titulo", 28)
        self.f_subtit = _ga.get_font("titulo", 16)
        self.f_normal = _ga.get_font("hud",    14)
        self.f_small  = _ga.get_font("hud",    11)

        self.sel = 0   # selected card index (0-5)
        self._card_rects = [_card_rect(i) for i in range(len(_LOCAIS))]

        # Description panel y
        self._desc_y = _GRID_Y + 2 * (_CARD_H + _GAP_Y) + 14

    # ── Loop ─────────────────────────────────────────────────

    def run(self) -> str:
        while True:
            self.clock.tick(60)
            mx, my = pygame.mouse.get_pos()

            # Hover → update sel
            for i, r in enumerate(self._card_rects):
                if r.collidepoint(mx, my):
                    self.sel = i
                    break

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        return "rua_central"
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                  pygame.K_SPACE):
                        return _LOCAIS[self.sel]["id"]
                    if ev.key == pygame.K_LEFT:
                        self.sel = max(0, self.sel - 1)
                    if ev.key == pygame.K_RIGHT:
                        self.sel = min(len(_LOCAIS) - 1, self.sel + 1)
                    if ev.key == pygame.K_UP:
                        self.sel = max(0, self.sel - _COLS)
                    if ev.key == pygame.K_DOWN:
                        self.sel = min(len(_LOCAIS) - 1, self.sel + _COLS)

                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for i, r in enumerate(self._card_rects):
                        if r.collidepoint(mx, my):
                            return _LOCAIS[i]["id"]
                    # Click on default button
                    if self._btn_default_rect().collidepoint(mx, my):
                        return "rua_central"

            self._draw(mx, my)

    # ── Botão padrão ─────────────────────────────────────────

    def _btn_default_rect(self) -> pygame.Rect:
        return pygame.Rect(_W - 230, _H - 52, 210, 38)

    # ── Desenho ───────────────────────────────────────────────

    def _draw(self, mx: int, my: int):
        s = self.screen
        s.fill(self.C_FUNDO)

        # Partículas de fundo suaves
        t = pygame.time.get_ticks() / 1000.0
        for i in range(40):
            px = (i * 173 + int(t * 6 * (i % 3 + 1))) % _W
            py = (i * 131 + int(t * 3 * (i % 4 + 1))) % _H
            alfa = int(30 + abs(math.sin(t + i)) * 40)
            pygame.draw.circle(s, (alfa, alfa, alfa + 20), (px, py), 1)

        # Título
        suf = f"  —  {self.nome_jogador}" if self.nome_jogador else ""
        tit = self.f_titulo.render(
            f"ONDE COMEÇA A AVENTURA{suf}?", True, self.C_OURO)
        s.blit(tit, tit.get_rect(centerx=_W // 2, y=24))

        sub = self.f_small.render(
            "Clique num distrito de Arkham para começar ali  ·  "
            "[↑↓←→] navegar  ·  [Enter] confirmar  ·  [Esc] Rua Central",
            True, self.C_DIM)
        s.blit(sub, sub.get_rect(centerx=_W // 2, y=70))

        pygame.draw.line(s, (50, 45, 30), (36, 100), (_W - 36, 100), 1)

        # Rótulo do grid
        grid_lbl = self.f_small.render("DISTRITOS DE ARKHAM  —  1923",
                                       True, self.C_DIM)
        s.blit(grid_lbl, (_GRID_X, _GRID_Y - 24))

        # Cards
        for i, loc in enumerate(_LOCAIS):
            r   = self._card_rects[i]
            sel = (i == self.sel)
            hov = r.collidepoint(mx, my)

            base    = loc["cor"]
            cor_bg  = tuple(min(255, c + 55) for c in base) if sel else (
                      tuple(min(255, c + 25) for c in base) if hov else base)
            cor_brd = self.C_OURO if sel else (
                      tuple(min(255, c + 60) for c in base) if hov else
                      tuple(min(255, c + 20) for c in base))
            brd_w   = 2 if sel else 1

            pygame.draw.rect(s, cor_bg,  r, border_radius=8)
            pygame.draw.rect(s, cor_brd, r, brd_w, border_radius=8)

            # Barra de destaque lateral (selecionado)
            if sel:
                pygame.draw.rect(s, self.C_OURO,
                                 pygame.Rect(r.x, r.y, 4, r.h),
                                 border_radius=3)

            # Ícone + nome
            ic = self.f_subtit.render(
                f"{loc['icone']}  {loc['nome']}",
                True, self.C_OURO if sel else self.C_TEXTO)
            s.blit(ic, (r.x + 16, r.y + 12))

            # Subtítulo
            sub_s = self.f_small.render(loc["subtitulo"], True,
                                        self.C_TEXTO if sel else self.C_DIM)
            s.blit(sub_s, (r.x + 16, r.y + 40))

            # Separador
            pygame.draw.line(s, cor_brd,
                             (r.x + 16, r.y + 60),
                             (r.x + r.w - 16, r.y + 60), 1)

            # Dica
            dica_s = self.f_small.render(loc["dica"], True,
                                         self.C_OURO if sel else self.C_DIM)
            s.blit(dica_s, (r.x + 16, r.y + 70))

            # Indicador de seleção (Enter)
            if sel:
                sel_s = self.f_small.render("[ Enter ] Começar aqui",
                                            True, self.C_VERDE)
                s.blit(sel_s, (r.x + 16, r.y + 94))

        # Painel de descrição (do card selecionado)
        loc_sel = _LOCAIS[self.sel]
        desc_y  = self._desc_y
        desc_r  = pygame.Rect(_GRID_X, desc_y, _GRID_W, 80)
        pygame.draw.rect(s, (18, 22, 38), desc_r, border_radius=6)
        pygame.draw.rect(s, (50, 50, 70), desc_r, 1, border_radius=6)

        cy = desc_y + 8
        for linha in loc_sel["descricao"].split("\n"):
            d = self.f_small.render(linha, True, self.C_TEXTO)
            s.blit(d, (_GRID_X + 14, cy))
            cy += d.get_height() + 2

        # Botão padrão (Esc / Rua Central)
        btn_d = self._btn_default_rect()
        hov_d = btn_d.collidepoint(mx, my)
        pygame.draw.rect(s, (45, 28, 28) if hov_d else (30, 18, 18),
                         btn_d, border_radius=6)
        pygame.draw.rect(s, self.C_ACENTO, btn_d, 1, border_radius=6)
        esc_s = self.f_small.render("[Esc]  Rua Central (padrão)",
                                    True, self.C_ACENTO)
        s.blit(esc_s, esc_s.get_rect(center=btn_d.center))

        pygame.display.flip()
