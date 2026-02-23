"""
CoC 7e -- Rolador de Dados
Interface pygame standalone.
Pressione ESC para sair.
"""

import pygame
import sys
import random
import math
import os

pygame.init()
pygame.display.set_caption("CoC 7e -- Rolador de Dados")

LARGURA, ALTURA = 720, 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
clock = pygame.time.Clock()

# ── Cores ──────────────────────────────────────────────────
COR_FUNDO    = (26,  26,  46)
COR_PAINEL   = (22,  33,  62)
COR_DESTAQUE = (15,  52,  96)
COR_ACENTO   = (233, 69,  96)
COR_TEXTO    = (238, 226, 220)
COR_DIM      = (154, 140, 152)
COR_OURO     = (212, 168, 67)
COR_VERDE    = (78,  204, 163)
COR_ROXO     = (107, 45,  139)
COR_BORDA    = (50,  70,  110)

# ── Fontes ─────────────────────────────────────────────────
fn_titulo  = pygame.font.SysFont("monospace", 20, bold=True)
fn_normal  = pygame.font.SysFont("monospace", 14)
fn_pequena = pygame.font.SysFont("monospace", 12)
fn_grande  = pygame.font.SysFont("monospace", 36, bold=True)
fn_media   = pygame.font.SysFont("monospace", 17, bold=True)
fn_dado    = pygame.font.SysFont("monospace", 15, bold=True)

# ── Estado ─────────────────────────────────────────────────
estado = {
    "dado":       6,
    "qtd":        1,
    "resultados": [],
    "soma":       0,
    "historico":  [],    # lista de strings (max 10)
    "anim":       0,     # frames restantes de animação
    "anim_vals":  [],    # valores temporários durante animação
}

DADOS = [4, 6, 8, 10, 12, 20, 100]

# Presets CoC 7e
PRESETS = [
    ("3d6 x5",    lambda: _preset_3d6x5()),
    ("2d6+6 x5",  lambda: _preset_2d6p6x5()),
    ("d100 %",    lambda: _preset_d100()),
    ("d10 dezena",lambda: _preset_d10_dezena()),
]


# ── Funções de preset ───────────────────────────────────────

def _preset_3d6x5():
    dados = [random.randint(1, 6) for _ in range(3)]
    soma  = sum(dados)
    val   = soma * 5
    _push_resultado(dados, val, f"3d6 x5 = [{','.join(map(str,dados))}] = {soma} x5 = {val}")


def _preset_2d6p6x5():
    dados = [random.randint(1, 6) for _ in range(2)]
    soma  = sum(dados)
    val   = (soma + 6) * 5
    _push_resultado(dados + [6], val,
                    f"(2d6+6) x5 = [{','.join(map(str,dados))}+6] = {soma+6} x5 = {val}")


def _preset_d100():
    val = random.randint(1, 100)
    _push_resultado([val], val, f"d100 = {val:02d}%")


def _preset_d10_dezena():
    val = random.randint(0, 9) * 10
    val = val if val > 0 else 100
    _push_resultado([val], val, f"d10 (dezena) = {val:02d}")


def _rolar_livre():
    n    = estado["qtd"]
    d    = estado["dado"]
    vals = [random.randint(1, d) for _ in range(n)]
    soma = sum(vals)
    _push_resultado(vals, soma, f"{n}d{d} = [{','.join(map(str,vals))}] = {soma}")


def _push_resultado(vals, soma, historico_str):
    estado["resultados"] = vals
    estado["soma"]       = soma
    estado["anim"]       = 18
    estado["anim_vals"]  = [random.randint(1, max(estado["dado"], max(vals, default=1)))
                             for _ in vals]
    hist = estado["historico"]
    hist.insert(0, historico_str)
    if len(hist) > 9:
        hist.pop()


# ── Helpers de desenho ──────────────────────────────────────

def painel(surf, x, y, w, h, cor=COR_PAINEL, borda=COR_BORDA, radius=8):
    pygame.draw.rect(surf, cor,   pygame.Rect(x, y, w, h), border_radius=radius)
    pygame.draw.rect(surf, borda, pygame.Rect(x, y, w, h), width=1, border_radius=radius)


def texto(surf, txt, fonte, cor, x, y, centralizar=False):
    s = fonte.render(str(txt), True, cor)
    if centralizar:
        tela.blit(s, s.get_rect(centerx=x, y=y))
    else:
        tela.blit(s, (x, y))
    return s.get_width()


def botao(surf, rect, label, fonte, cor_base, hover, radius=8):
    cor = tuple(min(255, c + 45) for c in cor_base) if hover else cor_base
    pygame.draw.rect(surf, cor,      rect, border_radius=radius)
    pygame.draw.rect(surf, tuple(min(255, c + 70) for c in cor_base),
                     rect, width=1,  border_radius=radius)
    s = fonte.render(label, True, COR_TEXTO)
    surf.blit(s, s.get_rect(center=rect.center))


# ── Construção dos rects ────────────────────────────────────

def _rects_dados(y0=90):
    """7 botões de seleção de dado numa linha."""
    rects = []
    w, h  = 74, 38
    gap   = 8
    total = len(DADOS) * w + (len(DADOS) - 1) * gap
    x0    = (LARGURA - total) // 2
    for i in range(len(DADOS)):
        rects.append(pygame.Rect(x0 + i * (w + gap), y0, w, h))
    return rects


def _rects_qtd(y0=148):
    """[-] [qtd] [+]"""
    btn_menos = pygame.Rect(LARGURA//2 - 100, y0, 36, 36)
    btn_mais  = pygame.Rect(LARGURA//2 -  10, y0, 36, 36)
    return btn_menos, btn_mais


def _rect_rolar(y0=148):
    return pygame.Rect(LARGURA//2 + 50, y0, 130, 36)


def _rects_presets(y0=430):
    rects = []
    w, h  = 140, 34
    gap   = 10
    total = len(PRESETS) * w + (len(PRESETS) - 1) * gap
    x0    = (LARGURA - total) // 2
    for i in range(len(PRESETS)):
        rects.append(pygame.Rect(x0 + i * (w + gap), y0, w, h))
    return rects


# ── Tela principal ──────────────────────────────────────────

def desenhar(mouse_pos, tempo):
    tela.fill(COR_FUNDO)

    # --- Título
    texto(tela, "ROLADOR DE DADOS", fn_titulo, COR_ACENTO, LARGURA//2, 18, centralizar=True)
    texto(tela, "Call of Cthulhu 7e", fn_pequena, COR_DIM, LARGURA//2, 44, centralizar=True)
    pygame.draw.line(tela, COR_DESTAQUE, (60, 65), (LARGURA - 60, 65), 1)

    # --- Selecao de dado
    texto(tela, "DADO:", fn_normal, COR_DIM, 60, 93)
    rects_d = _rects_dados()
    for i, (rect, d) in enumerate(zip(rects_d, DADOS)):
        selecionado = (d == estado["dado"])
        cor_base = COR_ACENTO if selecionado else COR_DESTAQUE
        botao(tela, rect, f"d{d}", fn_dado, cor_base, rect.collidepoint(mouse_pos))

    # --- Quantidade e botão rolar
    btn_menos, btn_mais = _rects_qtd()
    rect_rolar = _rect_rolar()

    texto(tela, "QTD:", fn_normal, COR_DIM, 60, 154)
    botao(tela, btn_menos, "-", fn_media, COR_DESTAQUE, btn_menos.collidepoint(mouse_pos))
    texto(tela, str(estado["qtd"]), fn_media, COR_OURO, LARGURA//2 - 60, 151)
    botao(tela, btn_mais,  "+", fn_media, COR_DESTAQUE, btn_mais.collidepoint(mouse_pos))
    botao(tela, rect_rolar, f"ROLAR  d{estado['dado']}", fn_normal, COR_ROXO,
          rect_rolar.collidepoint(mouse_pos))

    pygame.draw.line(tela, COR_DESTAQUE, (60, 198), (LARGURA - 60, 198), 1)

    # --- Resultado
    painel(tela, 60, 210, LARGURA - 120, 200, COR_PAINEL)

    if estado["resultados"]:
        # Animação de rolar
        if estado["anim"] > 0:
            vals_show = estado["anim_vals"]
            estado["anim"] -= 1
        else:
            vals_show = estado["resultados"]

        # Caixas de cada dado
        n = len(vals_show)
        cw = min(70, (LARGURA - 140) // max(n, 1))
        gap = min(8, (LARGURA - 140 - n * cw) // max(n - 1, 1))
        total_w = n * cw + max(n - 1, 0) * gap
        x0 = 60 + ((LARGURA - 120) - total_w) // 2
        y0 = 218

        for i, val in enumerate(vals_show):
            rx = x0 + i * (cw + gap)
            ry = y0
            pygame.draw.rect(tela, COR_DESTAQUE, pygame.Rect(rx, ry, cw, 60), border_radius=6)
            pygame.draw.rect(tela, COR_BORDA, pygame.Rect(rx, ry, cw, 60), width=1, border_radius=6)
            s = fn_grande.render(str(val), True, COR_OURO)
            tela.blit(s, s.get_rect(center=(rx + cw//2, ry + 32)))

        # Soma
        texto(tela, f"SOMA:  {estado['soma']}", fn_media, COR_VERDE, LARGURA//2, 298, centralizar=True)

        # Info do dado
        n_real = len(estado["resultados"])
        texto(tela, f"{n_real}d{estado['dado']}", fn_normal, COR_DIM, LARGURA//2, 324, centralizar=True)
    else:
        texto(tela, "Escolha um dado e clique ROLAR", fn_normal, COR_DIM, LARGURA//2, 295, centralizar=True)

    pygame.draw.line(tela, COR_DESTAQUE, (60, 420), (LARGURA - 60, 420), 1)

    # --- Presets CoC
    texto(tela, "PRESETS CoC 7e:", fn_normal, COR_DIM, 60, 400)
    rects_p = _rects_presets()
    for i, (rect, (label, _)) in enumerate(zip(rects_p, PRESETS)):
        botao(tela, rect, label, fn_pequena, COR_DESTAQUE, rect.collidepoint(mouse_pos))

    pygame.draw.line(tela, COR_DESTAQUE, (60, 476), (LARGURA - 60, 476), 1)

    # --- Historico
    texto(tela, "HISTORICO:", fn_normal, COR_DIM, 60, 480)
    for i, h in enumerate(estado["historico"]):
        alfa = 255 - i * 22
        cor  = (max(80, int(COR_TEXTO[0] * alfa / 255)),
                max(80, int(COR_TEXTO[1] * alfa / 255)),
                max(80, int(COR_TEXTO[2] * alfa / 255)))
        texto(tela, h, fn_pequena, cor, 70, 498 + i * 16)

    # Rodapé
    texto(tela, "[ESC] Sair   |   [R] Rolar   |   [C] Limpar",
          fn_pequena, COR_DIM, LARGURA//2, ALTURA - 18, centralizar=True)

    pygame.display.flip()


# ── Loop ────────────────────────────────────────────────────

def main():
    while True:
        mouse_pos = pygame.mouse.get_pos()
        tempo     = pygame.time.get_ticks()

        rects_d  = _rects_dados()
        btn_menos, btn_mais = _rects_qtd()
        rect_rolar = _rect_rolar()
        rects_p  = _rects_presets()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_r:
                    _rolar_livre()
                elif event.key == pygame.K_c:
                    estado["resultados"] = []
                    estado["historico"]  = []
                    estado["soma"]       = 0
                # Atalhos d[numero]
                for d in DADOS:
                    if event.unicode == str(d)[-1]:
                        pass  # difícil mapear d100 etc, skip

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Seleção de dado
                for i, rect in enumerate(rects_d):
                    if rect.collidepoint(mouse_pos):
                        estado["dado"] = DADOS[i]

                # Qtd
                if btn_menos.collidepoint(mouse_pos):
                    estado["qtd"] = max(1, estado["qtd"] - 1)
                if btn_mais.collidepoint(mouse_pos):
                    estado["qtd"] = min(10, estado["qtd"] + 1)

                # Rolar
                if rect_rolar.collidepoint(mouse_pos):
                    _rolar_livre()

                # Presets
                for i, rect in enumerate(rects_p):
                    if rect.collidepoint(mouse_pos):
                        PRESETS[i][1]()

        desenhar(mouse_pos, tempo)
        clock.tick(60)


if __name__ == "__main__":
    main()
