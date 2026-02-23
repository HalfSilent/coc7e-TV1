"""
editor/editor_campanha.py — Criador visual de campanhas CoC 7e.

Abas:
    [1] MAPA          — pintar tiles, efeitos, spawns
    [2] PERSONAGENS   — criar / editar fichas
    [3] DIÁLOGOS      — árvores de conversa
    [4] TRIGGERS      — zonas e eventos

Atalhos:
    Ctrl+S   — salvar
    Ctrl+N   — nova campanha
    Ctrl+O   — abrir campanha existente
    ESC      — voltar ao menu

Uso:
    python editor/editor_campanha.py
    python editor/editor_campanha.py caminho/da/campanha
"""
from __future__ import annotations

import os
import sys
import subprocess
from typing import Optional

os.environ["SDL_VIDEODRIVER"] = "x11"

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import pygame
import gerenciador_assets as _ga

from dados.campanha_schema import Campanha

# ── Resolução ─────────────────────────────────────────────────
LARGURA, ALTURA = 1280, 720
FPS = 60

TAB_H   = 46   # altura da barra de abas
CONT_H  = ALTURA - TAB_H  # altura da área de conteúdo

# ── Cores ──────────────────────────────────────────────────────
CF  = (14,  18,  32)
CP  = (22,  28,  48)
CB  = (50,  65, 100)
CT  = (215, 210, 195)
CD  = (100,  98,  88)
CS  = ( 55,  90, 155)
CHL = ( 90, 140, 220)
CA  = (220,  80,  90)
COK = ( 60, 190, 110)

# ── Abas ──────────────────────────────────────────────────────
_ABAS = ["[1] MAPA", "[2] PERSONAGENS", "[3] DIÁLOGOS", "[4] TRIGGERS"]

# Pasta padrão de campanhas
_CAMPANHAS_DIR = os.path.join(_RAIZ, "Campanhas")


def _campanhas_disponiveis() -> list:
    """Lista pastas em CoCGame/Campanhas/ que contenham campanha.json."""
    if not os.path.isdir(_CAMPANHAS_DIR):
        return []
    result = []
    for nome in sorted(os.listdir(_CAMPANHAS_DIR)):
        pasta = os.path.join(_CAMPANHAS_DIR, nome)
        if os.path.isdir(pasta) and os.path.exists(
                os.path.join(pasta, "campanha.json")):
            result.append((nome, pasta))
    return result


# ══════════════════════════════════════════════════════════════
# TELA DE SELEÇÃO / INÍCIO
# ══════════════════════════════════════════════════════════════

class TelaInicio:
    """Mostra campanhas existentes e permite criar uma nova."""

    def __init__(self, tela: pygame.Surface, fn, fn_big, fn_sm):
        self.tela   = tela
        self._fn    = fn
        self._fn_big = fn_big
        self._fn_sm = fn_sm
        self._lista = _campanhas_disponiveis()
        self._hover = -1
        self._cx_nome: Optional[str] = None
        self._criando = False
        self._nome_buf = ""

        self.resultado: Optional[tuple] = None  # ("abrir", pasta) | ("nova", nome)

    def processar_evento(self, e: pygame.event.Event) -> bool:
        """Retorna True quando uma escolha é feita."""
        if e.type == pygame.KEYDOWN:
            if self._criando:
                if e.key == pygame.K_RETURN:
                    if self._nome_buf.strip():
                        self.resultado = ("nova", self._nome_buf.strip())
                        return True
                    self._criando = False
                elif e.key == pygame.K_ESCAPE:
                    self._criando = False
                elif e.key == pygame.K_BACKSPACE:
                    self._nome_buf = self._nome_buf[:-1]
                elif e.unicode and ord(e.unicode) >= 32:
                    self._nome_buf += e.unicode
            else:
                if e.key == pygame.K_n:
                    self._criando = True
                    self._nome_buf = ""

        if e.type == pygame.MOUSEMOTION:
            self._hover = self._idx_hover(e.pos)

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            # Clique em "Nova"
            if pygame.Rect(LARGURA // 2 - 100, ALTURA - 70, 200, 36).collidepoint(mx, my):
                self._criando = True
                self._nome_buf = ""
                return False
            # Clique em campanha existente
            idx = self._idx_hover((mx, my))
            if idx >= 0:
                self.resultado = ("abrir", self._lista[idx][1])
                return True

        return False

    def _idx_hover(self, pos) -> int:
        mx, my = pos
        base_y = 180
        lh = 48
        for i in range(len(self._lista)):
            r = pygame.Rect(LARGURA // 2 - 250, base_y + i * lh, 500, 40)
            if r.collidepoint(mx, my):
                return i
        return -1

    def desenhar(self):
        tela = self.tela
        tela.fill(CF)

        # Título
        s = self._fn_big.render("EDITOR DE CAMPANHAS", True, (220, 80, 90))
        tela.blit(s, s.get_rect(centerx=LARGURA // 2, y=40))
        s2 = self._fn_sm.render("Call of Cthulhu 7ª Edição", True, (140, 130, 100))
        tela.blit(s2, s2.get_rect(centerx=LARGURA // 2, y=82))

        pygame.draw.line(tela, CB, (LARGURA // 2 - 250, 106), (LARGURA // 2 + 250, 106), 1)

        # Lista de campanhas
        if not self._lista:
            s = self._fn.render("Nenhuma campanha encontrada.", True, CD)
            tela.blit(s, s.get_rect(centerx=LARGURA // 2, y=160))
        else:
            s = self._fn_sm.render("Campanhas existentes  (clique para abrir):", True, CD)
            tela.blit(s, s.get_rect(centerx=LARGURA // 2, y=150))

            base_y = 180
            lh = 48
            for i, (nome, pasta) in enumerate(self._lista):
                r = pygame.Rect(LARGURA // 2 - 250, base_y + i * lh, 500, 40)
                cor = CS if i == self._hover else CP
                pygame.draw.rect(tela, cor, r, border_radius=6)
                pygame.draw.rect(tela, CB,  r, width=1, border_radius=6)
                s = self._fn.render(nome, True, CT)
                tela.blit(s, s.get_rect(center=r.center))

        # Botão Nova
        btn = pygame.Rect(LARGURA // 2 - 100, ALTURA - 70, 200, 36)
        pygame.draw.rect(tela, (40, 100, 60), btn, border_radius=6)
        pygame.draw.rect(tela, CB, btn, width=1, border_radius=6)
        s = self._fn.render("[N] Nova Campanha", True, CT)
        tela.blit(s, s.get_rect(center=btn.center))

        # Input de nome
        if self._criando:
            overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            tela.blit(overlay, (0, 0))

            box = pygame.Rect(LARGURA // 2 - 220, ALTURA // 2 - 50, 440, 100)
            pygame.draw.rect(tela, CP, box, border_radius=8)
            pygame.draw.rect(tela, CB, box, width=1, border_radius=8)

            s = self._fn_sm.render("Nome da nova campanha:", True, CD)
            tela.blit(s, s.get_rect(centerx=LARGURA // 2, y=box.y + 10))

            s2 = self._fn.render(self._nome_buf + "│", True, CT)
            tela.blit(s2, s2.get_rect(centerx=LARGURA // 2, y=box.y + 34))

            s3 = self._fn_sm.render("[Enter] confirmar  [Esc] cancelar", True, CD)
            tela.blit(s3, s3.get_rect(centerx=LARGURA // 2, y=box.bottom - 20))

        s_esc = self._fn_sm.render("[ESC] Sair", True, CD)
        tela.blit(s_esc, (10, ALTURA - 22))


# ══════════════════════════════════════════════════════════════
# EDITOR PRINCIPAL
# ══════════════════════════════════════════════════════════════

class EditorCampanha:

    def __init__(self, tela: pygame.Surface, campanha: Campanha,
                 pasta_campanha: str):
        self.tela           = tela
        self.campanha       = campanha
        self.pasta_campanha = pasta_campanha
        self._aba           = 0      # aba ativa (0..3)
        self._dirty         = False  # mudanças não salvas

        _ga.garantir_fontes(verbose=False)
        self._fn     = _ga.get_font("hud",    14)
        self._fn_big = _ga.get_font("titulo", 16)
        self._fn_sm  = _ga.get_font("hud",    11)

        # Determina mapa inicial para as abas que precisam
        mapa_id = campanha.mapa_inicial or (
            next(iter(campanha.mapas), None)
        )

        # Carrega paineis lazily ao trocar de aba
        self._paineis: dict = {}
        self._mapa_id_atual = mapa_id
        self._criar_painel(0)   # cria o painel de mapa imediatamente

        # Tab rects
        self._tab_rects: list = []

    # ── Paineis ───────────────────────────────────────────────

    def _criar_painel(self, aba: int):
        if aba in self._paineis:
            return

        # Subsurface para a área de conteúdo
        sub = self.tela.subsurface(
            pygame.Rect(0, TAB_H, LARGURA, CONT_H)
        )

        if aba == 0:
            from editor.paineis.painel_mapa import PainelMapa
            self._paineis[0] = PainelMapa(
                sub, LARGURA, CONT_H,
                self.campanha, self._mapa_id_atual,
                fonte_hud=self._fn_sm, fonte_ui=self._fn,
            )
        elif aba == 1:
            from editor.paineis.painel_personagem import PainelPersonagem
            self._paineis[1] = PainelPersonagem(
                sub, LARGURA, CONT_H,
                self.campanha, fonte_ui=self._fn,
            )
        elif aba == 2:
            from editor.paineis.painel_dialogo import PainelDialogo
            self._paineis[2] = PainelDialogo(
                sub, LARGURA, CONT_H,
                self.campanha, fonte_ui=self._fn,
            )
        elif aba == 3:
            from editor.paineis.painel_trigger import PainelTrigger
            self._paineis[3] = PainelTrigger(
                sub, LARGURA, CONT_H,
                self.campanha, self._mapa_id_atual,
                fonte_ui=self._fn,
            )

    def _painel_ativo(self):
        return self._paineis.get(self._aba)

    # ── Salvar ────────────────────────────────────────────────

    def salvar(self):
        os.makedirs(self.pasta_campanha, exist_ok=True)
        self.campanha.salvar(self.pasta_campanha)
        self._dirty = False
        print(f"[Editor] Campanha salva: {self.pasta_campanha}")

    # ── Loop ──────────────────────────────────────────────────

    def processar_evento(self, e: pygame.event.Event) -> bool:
        """Retorna True para sinalizar que o editor deve fechar."""
        if e.type == pygame.KEYDOWN:
            # Ctrl+S
            if e.key == pygame.K_s and (e.mod & pygame.KMOD_CTRL):
                self.salvar()
                return False
            # ESC
            if e.key == pygame.K_ESCAPE:
                return True
            # Teclas de aba (1..4)
            aba_keys = {pygame.K_1: 0, pygame.K_2: 1,
                        pygame.K_3: 2, pygame.K_4: 3}
            if e.key in aba_keys:
                self._trocar_aba(aba_keys[e.key])
                return False

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            # Verifica clique nas abas
            for i, r in enumerate(self._tab_rects):
                if r.collidepoint(e.pos):
                    self._trocar_aba(i)
                    return False

        # Marca mudança
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self._dirty = True

        # Delega para o painel ativo
        # Ajusta pos do evento para coordenadas do painel (y -= TAB_H)
        e_painel = _remap_event_y(e, -TAB_H)
        p = self._painel_ativo()
        if p and e_painel:
            p.processar_evento(e_painel)

        return False

    def _trocar_aba(self, nova: int):
        if 0 <= nova <= 3:
            self._aba = nova
            self._criar_painel(nova)

    def atualizar(self, dt: int):
        p = self._painel_ativo()
        if p:
            p.atualizar(dt)

    def desenhar(self):
        tela = self.tela
        tela.fill(CF)

        # ── Barra de abas ──────────────────────────────────────
        self._tab_rects = []
        tab_w = 180
        tab_gap = 2
        for i, nome in enumerate(_ABAS):
            r = pygame.Rect(i * (tab_w + tab_gap), 0, tab_w, TAB_H)
            self._tab_rects.append(r)
            ativo = (i == self._aba)
            cor   = CS if ativo else CP
            pygame.draw.rect(tela, cor, r)
            pygame.draw.rect(tela, CB, r, width=1)
            cor_t = (220, 200, 80) if ativo else CT
            s = self._fn.render(nome, True, cor_t)
            tela.blit(s, s.get_rect(center=r.center))

        # Botão Salvar
        btn_s = pygame.Rect(LARGURA - 140, 6, 130, TAB_H - 12)
        cor_btn = COK if not self._dirty else CA
        pygame.draw.rect(tela, cor_btn, btn_s, border_radius=5)
        pygame.draw.rect(tela, CB, btn_s, width=1, border_radius=5)
        s = self._fn_sm.render("💾 Ctrl+S" if not self._dirty else "💾 Salvar *",
                                True, CF)
        tela.blit(s, s.get_rect(center=btn_s.center))

        # Nome da campanha
        s2 = self._fn_sm.render(
            f"  {self.campanha.nome}  │  {os.path.basename(self.pasta_campanha)}",
            True, CD,
        )
        tela.blit(s2, (len(_ABAS) * (tab_w + tab_gap) + 8,
                       TAB_H // 2 - s2.get_height() // 2))

        pygame.draw.line(tela, CB, (0, TAB_H), (LARGURA, TAB_H), 1)

        # ── Painel ativo ───────────────────────────────────────
        p = self._painel_ativo()
        if p:
            p.desenhar()


# ══════════════════════════════════════════════════════════════
# UTILITÁRIO DE EVENTOS
# ══════════════════════════════════════════════════════════════

def _remap_event_y(e: pygame.event.Event, dy: int):
    """Cria cópia do evento com pos.y deslocado em dy (para subsurfaces)."""
    if hasattr(e, "pos"):
        new_pos = (e.pos[0], e.pos[1] + dy)
        # Cria novo evento com pos ajustada
        new_e = pygame.event.Event(e.type, {**e.__dict__, "pos": new_pos})
        return new_e
    return e


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def _voltar_menu():
    _menu = os.path.join(_RAIZ, "ui", "menu_pygame.py")
    if os.path.exists(_menu):
        subprocess.Popen([sys.executable, _menu])
    os._exit(0)


def main():
    pygame.init()
    pygame.display.set_caption("Editor de Campanhas — CoC 7e")
    tela  = pygame.display.set_mode((LARGURA, ALTURA),
                                    pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()

    _ga.garantir_fontes(verbose=False)
    fn     = _ga.get_font("hud",    14)
    fn_big = _ga.get_font("titulo", 20)
    fn_sm  = _ga.get_font("hud",    11)

    # ── Argumento de linha de comando (pasta de campanha) ──────
    pasta_arg = sys.argv[1] if len(sys.argv) > 1 else None

    # Estado: "inicio" | "editor"
    estado = "inicio"
    editor: Optional[EditorCampanha] = None
    tela_inicio = TelaInicio(tela, fn, fn_big, fn_sm)

    if pasta_arg and os.path.exists(pasta_arg):
        try:
            c = Campanha.carregar(pasta_arg)
            editor = EditorCampanha(tela, c, pasta_arg)
            estado = "editor"
        except Exception as ex:
            print(f"[Editor] Erro ao carregar '{pasta_arg}': {ex}")

    while True:
        dt = clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if estado == "inicio":
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    _voltar_menu()
                pronto = tela_inicio.processar_evento(e)
                if pronto and tela_inicio.resultado:
                    tipo, valor = tela_inicio.resultado
                    if tipo == "abrir":
                        try:
                            c = Campanha.carregar(valor)
                            pasta = valor
                        except Exception as ex:
                            print(f"[Editor] Erro: {ex}")
                            continue
                    else:  # nova
                        c = Campanha.nova(valor)
                        pasta = os.path.join(_CAMPANHAS_DIR, valor)
                        os.makedirs(pasta, exist_ok=True)
                        c.salvar(pasta)
                    editor = EditorCampanha(tela, c, pasta)
                    estado = "editor"

            elif estado == "editor" and editor is not None:
                fechar = editor.processar_evento(e)
                if fechar:
                    # Volta para tela de início
                    estado = "inicio"
                    editor = None
                    tela_inicio = TelaInicio(tela, fn, fn_big, fn_sm)

        # ── Atualização ───────────────────────────────────────
        if estado == "editor" and editor:
            editor.atualizar(dt)

        # ── Render ────────────────────────────────────────────
        if estado == "inicio":
            tela_inicio.desenhar()
        elif estado == "editor" and editor:
            editor.desenhar()

        pygame.display.flip()


if __name__ == "__main__":
    main()


