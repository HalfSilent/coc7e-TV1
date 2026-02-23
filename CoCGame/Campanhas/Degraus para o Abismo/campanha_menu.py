"""
campanha_menu.py — Tela de entrada da campanha Degraus para o Abismo.

Fluxo:
    [Nova Partida] → ficha.py --para-campanha → intro_campanha.py → mundo_aberto.py
    [Continuar]    → mundo_aberto.py  (exige save em Mapas/Rio1923/save.json)
    [Voltar]       → menu_pygame.py
"""
from __future__ import annotations

import math
import os
import subprocess
import sys

# SDL_VIDEODRIVER deve ser definido ANTES de qualquer import pygame.
os.environ["SDL_VIDEODRIVER"] = "x11"

import pygame
from tinydb import TinyDB, Query

# ── Caminhos ──────────────────────────────────────────────────
_DIR    = os.path.dirname(os.path.abspath(__file__))
_RAIZ   = os.path.normpath(os.path.join(_DIR, "..", ".."))  # CoCGame/

if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import gerenciador_mundos as _gm
import gerenciador_assets as _ga
_MUNDO_ID   = _gm.mundo_da_campanha(_DIR)
_MUNDO_PATHS = _gm.paths(_MUNDO_ID)

_FICHA  = os.path.join(_RAIZ, "ui", "ficha.py")
_MENU   = os.path.join(_RAIZ, "ui", "menu_pygame.py")
_MUNDO  = os.path.join(_RAIZ, "mundo_aberto.py")
_INTRO  = os.path.join(_DIR,  "intro_campanha.py")
_SAVE_MUNDO = _MUNDO_PATHS["save"]
_SAVE_NAR   = os.path.join(_DIR,  "campanha.json")

# ── Dimensões ─────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60

# ── Paleta ────────────────────────────────────────────────────
FUNDO   = (  5,   6,  15)
PAINEL  = ( 16,  20,  42)
BORDA   = ( 48,  60,  98)
TEXTO   = (238, 226, 220)
DIM     = (120, 110, 105)
OURO    = (212, 168,  67)
ACENTO  = (233,  69,  96)
VERDE   = ( 78, 204, 163)
HOVER   = ( 32,  52, 102)
CINZA   = ( 38,  38,  55)
CINZA_T = ( 58,  58,  75)


def _fonte(size: int, estilo: str = "titulo") -> pygame.font.Font:
    return _ga.get_font(estilo, size)


# ── Verificações de save ───────────────────────────────────────

def _tem_save() -> bool:
    """True se existe partida salva no mundo aberto."""
    if not os.path.exists(_SAVE_MUNDO):
        return False
    try:
        db = TinyDB(_SAVE_MUNDO)
        Q  = Query()
        r  = db.search(Q.slot == "auto")
        db.close()
        return bool(r)
    except Exception:
        return False


def _nome_investigador() -> str:
    """Retorna nome do investigador salvo na campanha, ou ''."""
    for path in (_SAVE_NAR, _SAVE_MUNDO):
        if not os.path.exists(path):
            continue
        try:
            db = TinyDB(path)
            Q  = Query()
            r  = db.search(Q.slot == "investigador")
            db.close()
            if r:
                return r[0].get("ficha", {}) \
                             .get("dados_pessoais", {}) \
                             .get("nome", "")
        except Exception:
            pass
    return ""


# ── Partículas ────────────────────────────────────────────────

def _draw_particles(tela: pygame.Surface, t: int):
    for i in range(55):
        px = (i * 163 + int(t * 0.005 * ((i % 3) + 1))) % W
        py = (i * 127 + int(t * 0.003 * ((i % 4) + 1))) % H
        a  = 15 + int(25 * abs(math.sin(t * 0.001 + i * 0.4)))
        pygame.draw.circle(tela, (a, a // 2, a // 4), (px, py), 1)


# ── Loop principal ────────────────────────────────────────────

def main():
    pygame.init()
    tela  = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Degraus para o Abismo — Call of Cthulhu 7e")
    clock = pygame.time.Clock()

    fn_tit  = _fonte(30)
    fn_sub  = _fonte(13)
    fn_btn  = _fonte(16)
    fn_dim  = _fonte(11)
    fn_hint = _fonte(12)

    save_ok  = _tem_save()
    investig = _nome_investigador()

    # ── Botões ────────────────────────────────────────────────
    BOTOES = [
        {"id": "nova",   "label": "[ N ]  Nova Partida",    "cor": ACENTO, "ativo": True},
        {"id": "contin", "label": "[ C ]  Continuar",       "cor": VERDE,  "ativo": save_ok},
        {"id": "voltar", "label": "[ ESC ]  Voltar ao Menu","cor": DIM,    "ativo": True},
    ]

    BW, BH   = 340, 52
    BY_START = 315
    BY_STEP  = 72

    def _btn_rect(i: int) -> pygame.Rect:
        return pygame.Rect((W - BW) // 2, BY_START + i * BY_STEP, BW, BH)

    def _acao(btn_id: str):
        if btn_id == "nova":
            subprocess.Popen([sys.executable, _FICHA, "--para-campanha"])
        elif btn_id == "contin":
            subprocess.Popen([sys.executable, _MUNDO, "--mundo", _MUNDO_ID])
        elif btn_id == "voltar":
            subprocess.Popen([sys.executable, _MENU])
        os._exit(0)

    while True:
        t    = pygame.time.get_ticks()
        clock.tick(FPS)
        mpos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _acao("voltar")
                elif event.key == pygame.K_n:
                    _acao("nova")
                elif event.key == pygame.K_c and save_ok:
                    _acao("contin")
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, b in enumerate(BOTOES):
                    if b["ativo"] and _btn_rect(i).collidepoint(mpos):
                        _acao(b["id"])

        # ── Renderização ──────────────────────────────────────
        tela.fill(FUNDO)
        _draw_particles(tela, t)

        # Painel central
        panel = pygame.Rect(W // 2 - 360, 55, 720, 510)
        pygame.draw.rect(tela, PAINEL, panel, border_radius=14)
        pygame.draw.rect(tela, BORDA,  panel, 1, border_radius=14)

        # Ornamento superior
        ox = W // 2
        for dx in (-220, -110, 0, 110, 220):
            pygame.draw.circle(tela, BORDA, (ox + dx, 75), 2)
        pygame.draw.line(tela, BORDA, (ox - 260, 75), (ox + 260, 75), 1)

        # Título
        titulo = fn_tit.render("DEGRAUS PARA O ABISMO", True, OURO)
        tela.blit(titulo, titulo.get_rect(centerx=W // 2, y=90))

        sub = fn_sub.render("Call of Cthulhu 7e  —  Módulo de Campanha", True, DIM)
        tela.blit(sub, sub.get_rect(centerx=W // 2, y=138))

        # Separador com data
        pygame.draw.line(tela, BORDA, (W // 2 - 230, 165), (W // 2 + 230, 165), 1)
        data_surf = fn_hint.render("Rio de Janeiro, Junho de 1923", True, (90, 82, 70))
        tela.blit(data_surf, data_surf.get_rect(centerx=W // 2, y=172))
        pygame.draw.line(tela, BORDA, (W // 2 - 230, 192), (W // 2 + 230, 192), 1)

        # Sinopse
        sinopse = [
            "O Prof. Malheiros desapareceu.",
            "Nas paredes do Catumbi, um símbolo que você não consegue",
            "tirar da cabeça. Os Filhos do Degrau já estão na cidade.",
        ]
        for j, linha in enumerate(sinopse):
            surf = fn_dim.render(linha, True, (145, 132, 118))
            tela.blit(surf, surf.get_rect(centerx=W // 2, y=205 + j * 20))

        # Investigador carregado
        if investig:
            sep_y = 260
            pygame.draw.line(tela, (35, 40, 60), (W // 2 - 180, sep_y),
                             (W // 2 + 180, sep_y), 1)
            inv_s = fn_hint.render(f"Investigador: {investig}", True, VERDE)
            tela.blit(inv_s, inv_s.get_rect(centerx=W // 2, y=sep_y + 5))

        # Botões
        for i, b in enumerate(BOTOES):
            rect  = _btn_rect(i)
            hover = b["ativo"] and rect.collidepoint(mpos)

            if not b["ativo"]:
                pygame.draw.rect(tela, CINZA,   rect, border_radius=8)
                pygame.draw.rect(tela, CINZA_T, rect, 1, border_radius=8)
                surf = fn_btn.render(b["label"], True, CINZA_T)
                tela.blit(surf, surf.get_rect(center=rect.center))
                if b["id"] == "contin":
                    h = fn_dim.render("(sem partida salva — inicie uma Nova Partida)",
                                      True, CINZA_T)
                    tela.blit(h, h.get_rect(centerx=W // 2, y=rect.bottom + 4))
            else:
                bg  = HOVER if hover else PAINEL
                brd = b["cor"]
                pygame.draw.rect(tela, bg,  rect, border_radius=8)
                pygame.draw.rect(tela, brd, rect, 2 if hover else 1, border_radius=8)
                cor_t = b["cor"] if hover else TEXTO
                surf  = fn_btn.render(b["label"], True, cor_t)
                tela.blit(surf, surf.get_rect(center=rect.center))

        # Dica de teclado
        hint = fn_dim.render("[N] Nova Partida   [C] Continuar   [ESC] Voltar",
                             True, (50, 48, 55))
        tela.blit(hint, hint.get_rect(centerx=W // 2, y=H - 22))

        pygame.display.flip()


if __name__ == "__main__":
    main()
