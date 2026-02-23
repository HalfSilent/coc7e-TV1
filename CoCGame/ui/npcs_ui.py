"""
CoC 7e -- Gerador de NPCs e Monstros
Interface pygame standalone.
Pressione ESC para sair.
"""

import pygame
import sys
import random
import json
import os

pygame.init()
pygame.display.set_caption("CoC 7e -- NPCs e Monstros")

LARGURA, ALTURA = 820, 640
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
COR_VERMELHO = (200, 50,  50)

# ── Fontes ─────────────────────────────────────────────────
fn_titulo  = pygame.font.SysFont("monospace", 20, bold=True)
fn_normal  = pygame.font.SysFont("monospace", 14)
fn_pequena = pygame.font.SysFont("monospace", 12)
fn_media   = pygame.font.SysFont("monospace", 15, bold=True)
fn_grande  = pygame.font.SysFont("monospace", 22, bold=True)


# ══════════════════════════════════════════════════════════════
# TEMPLATES DE NPCs / MONSTROS
# ══════════════════════════════════════════════════════════════

def _r(low, high, mult=5):
    """Rola um valor aleatorio e arredonda para multiplo de mult."""
    v = random.randint(low, high) * mult
    return max(mult, min(v, 99))


TEMPLATES = {
    # ── Humanos ──────────────────────────────────────────────
    "Cultista":    lambda: _humano("Cultista",    35, 45, "Faca",      "1d4+2",  30),
    "Policial":    lambda: _humano("Policial",    50, 55, "Revolver",  "1d10",   50),
    "Gangster":    lambda: _humano("Gangster",    50, 50, "Pistola",   "1d8",    40),
    "Cientista":   lambda: _humano("Cientista",   35, 70, "Revolver",  "1d10",   25),
    "Guarda":      lambda: _humano("Guarda",      55, 45, "Espingarda","2d6+1",  40),

    # ── Criaturas ────────────────────────────────────────────
    "Ghoul":       lambda: _monstro("Ghoul",
        for_=65, con=65, tam=65, des=60, pod=40, san_npc=0,
        arma="Garras", dano="1d6+1d4", hab=40,
        habilidades=["Visao no Escuro", "Escalar muros"],
        fraqueza="Fogo causa dano dobrado",
    ),
    "Deep One":    lambda: _monstro("Deep One",
        for_=80, con=80, tam=80, des=50, pod=65, san_npc=0,
        arma="Garras+Mordida", dano="1d8+1d6", hab=50,
        habilidades=["Anfibio", "Regeneracao (1HP/rodada)"],
        fraqueza="Fraco a ataques sagrados",
    ),
    "Byakhee":     lambda: _monstro("Byakhee",
        for_=90, con=70, tam=75, des=80, pod=50, san_npc=0,
        arma="Bico+Garras", dano="1d6+1d8", hab=55,
        habilidades=["Voo", "Criatura do Void"],
        fraqueza="Exposta a vacuo",
    ),
    "Mi-Go":       lambda: _monstro("Mi-Go",
        for_=70, con=60, tam=65, des=75, pod=75, san_npc=0,
        arma="Pincas", dano="1d8+1d6", hab=60,
        habilidades=["Tecnologia Alienígena", "Invisibilidade (escuridao)"],
        fraqueza="Luz intensa perturba",
    ),
    "Shoggoth":    lambda: _monstro("Shoggoth",
        for_=250, con=200, tam=200, des=20, pod=60, san_npc=0,
        arma="Pseudopodes", dano="3d6+3d6", hab=50,
        habilidades=["Amorfo", "Engolir (dano x2)", "Regeneracao (2HP/rodada)"],
        fraqueza="Fogo",
    ),
    "Cultista Elite": lambda: _humano("Cultista Elite", 55, 55, "Faca Ritual", "1d6+2", 40,
                                      extra={"Mitos de Cthulhu": 25}),
}

CATEGORIAS = {
    "Humanos":   ["Cultista", "Policial", "Gangster", "Cientista", "Guarda", "Cultista Elite"],
    "Criaturas": ["Ghoul", "Deep One", "Byakhee", "Mi-Go", "Shoggoth"],
}


def _humano(nome, for_base, int_base, arma, dano, hab_arma, extra=None):
    for_ = random.randint(for_base - 10, for_base + 15)
    con  = random.randint(40, 65)
    tam  = random.randint(45, 70)
    des  = random.randint(40, 65)
    int_ = random.randint(int_base - 10, int_base + 15)
    pod  = random.randint(35, 60)
    apl  = random.randint(30, 60)
    edu  = random.randint(40, 70)

    hp   = (con + tam) // 10
    san  = pod
    db   = _calc_db(for_, tam)
    mov  = 8

    pericias = {
        arma:         hab_arma,
        "Esquivar":   des // 2,
        "Furtividade": random.randint(15, 40),
        "Escutar":    random.randint(20, 40),
    }
    if extra:
        pericias.update(extra)

    return {
        "nome": nome,
        "tipo": "humano",
        "FOR": for_, "CON": con, "TAM": tam,
        "DES": des,  "INT": int_, "POD": pod,
        "APL": apl,  "EDU": edu,
        "HP":  hp,   "SAN": san,
        "DB":  db,   "MOV": mov,
        "arma": arma, "dano": dano, "hab_arma": hab_arma,
        "pericias": pericias,
        "habilidades": [],
        "fraqueza": "",
    }


def _monstro(nome, for_, con, tam, des, pod, san_npc,
             arma, dano, hab, habilidades=None, fraqueza=""):
    hp   = (con + tam) // 10
    db   = _calc_db(for_, tam)
    return {
        "nome": nome,
        "tipo": "monstro",
        "FOR": for_, "CON": con, "TAM": tam,
        "DES": des,  "INT": 0,   "POD": pod,
        "APL": 0,    "EDU": 0,
        "HP":  hp,   "SAN": san_npc,
        "DB":  db,   "MOV": 8,
        "arma": arma, "dano": dano, "hab_arma": hab,
        "pericias": {"Esquivar": des // 2},
        "habilidades": habilidades or [],
        "fraqueza": fraqueza,
    }


def _calc_db(for_, tam):
    total = for_ + tam
    if total <= 64:   return "-2"
    if total <= 84:   return "-1"
    if total <= 124:  return "0"
    if total <= 164:  return "+1d4"
    if total <= 204:  return "+1d6"
    return "+2d6"


# ── Estado global ───────────────────────────────────────────

estado = {
    "categoria_sel": "Humanos",
    "tipo_sel":      "Cultista",
    "npc_atual":     None,
    "historico":     [],   # lista de nomes gerados
    "mensagem":      "",
    "msg_timer":     0,
}


# ── Helpers de desenho ──────────────────────────────────────

def painel(surf, x, y, w, h, cor=COR_PAINEL, borda=COR_BORDA, radius=8):
    pygame.draw.rect(surf, cor,   pygame.Rect(x, y, w, h), border_radius=radius)
    pygame.draw.rect(surf, borda, pygame.Rect(x, y, w, h), width=1, border_radius=radius)


def txt(surf, s, fonte, cor, x, y, centralizar=False):
    surf_t = fonte.render(str(s), True, cor)
    if centralizar:
        surf.blit(surf_t, surf_t.get_rect(centerx=x, y=y))
    else:
        surf.blit(surf_t, (x, y))
    return surf_t.get_width()


def botao(surf, rect, label, fonte, cor_base, hover, radius=6):
    cor = tuple(min(255, c + 40) for c in cor_base) if hover else cor_base
    pygame.draw.rect(surf, cor,      rect, border_radius=radius)
    pygame.draw.rect(surf, tuple(min(255, c + 60) for c in cor_base),
                     rect, width=1,  border_radius=radius)
    s = fonte.render(label, True, COR_TEXTO)
    surf.blit(s, s.get_rect(center=rect.center))


# ── Layout ──────────────────────────────────────────────────

PAINEL_ESQ_W = 210
PAINEL_DIR_X = PAINEL_ESQ_W + 20
PAINEL_DIR_W = LARGURA - PAINEL_DIR_X - 16

CAT_Y0   = 76
TIPO_Y0  = 144
ACAO_Y0  = 480


def _rects_categorias():
    rects = {}
    cats  = list(CATEGORIAS.keys())
    w, h  = (PAINEL_ESQ_W - 20) // len(cats) - 4, 30
    for i, c in enumerate(cats):
        rects[c] = pygame.Rect(10 + i * (w + 4), CAT_Y0, w, h)
    return rects


def _rects_tipos():
    cat   = estado["categoria_sel"]
    tipos = CATEGORIAS[cat]
    rects = {}
    bw, bh = PAINEL_ESQ_W - 20, 28
    for i, t in enumerate(tipos):
        rects[t] = pygame.Rect(10, TIPO_Y0 + i * (bh + 4), bw, bh)
    return rects


def _rect_gerar():
    return pygame.Rect(10, ACAO_Y0, PAINEL_ESQ_W - 10, 36)


def _rect_salvar():
    return pygame.Rect(10, ACAO_Y0 + 46, PAINEL_ESQ_W - 10, 36)


# ── Ações ────────────────────────────────────────────────────

def gerar_npc():
    tipo = estado["tipo_sel"]
    if tipo in TEMPLATES:
        npc = TEMPLATES[tipo]()
        estado["npc_atual"] = npc
        estado["historico"].insert(0, f"{npc['nome']} (HP:{npc['HP']} DB:{npc['DB']})")
        if len(estado["historico"]) > 8:
            estado["historico"].pop()
        estado["mensagem"] = f"{npc['nome']} gerado!"
        estado["msg_timer"] = 120


def salvar_npc():
    npc = estado["npc_atual"]
    if not npc:
        estado["mensagem"] = "Gere um NPC primeiro!"
        estado["msg_timer"] = 90
        return
    base = os.path.dirname(os.path.abspath(__file__))
    nome_arquivo = npc["nome"].lower().replace(" ", "_") + "_npc.json"
    caminho = os.path.join(base, nome_arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(npc, f, ensure_ascii=False, indent=2)
    estado["mensagem"] = f"Salvo: {nome_arquivo}"
    estado["msg_timer"] = 120


# ── Desenho ─────────────────────────────────────────────────

def desenhar_painel_esq(mouse_pos):
    painel(tela, 8, 60, PAINEL_ESQ_W, ALTURA - 80, COR_PAINEL)
    txt(tela, "TIPO:", fn_normal, COR_DIM, 14, 64)

    rects_cat  = _rects_categorias()
    rects_tipo = _rects_tipos()
    rect_gerar  = _rect_gerar()
    rect_salvar = _rect_salvar()

    # Categorias
    for c, rect in rects_cat.items():
        sel = (c == estado["categoria_sel"])
        botao(tela, rect, c, fn_pequena,
              COR_ACENTO if sel else COR_DESTAQUE,
              rect.collidepoint(mouse_pos))

    # Tipos
    txt(tela, "NOME:", fn_pequena, COR_DIM, 14, TIPO_Y0 - 16)
    for t, rect in rects_tipo.items():
        sel = (t == estado["tipo_sel"])
        botao(tela, rect, t, fn_pequena,
              COR_ROXO if sel else COR_DESTAQUE,
              rect.collidepoint(mouse_pos))

    # Botões de ação
    botao(tela, rect_gerar,  "[G] Gerar",  fn_normal, COR_VERDE,  rect_gerar.collidepoint(mouse_pos))
    botao(tela, rect_salvar, "[S] Salvar", fn_normal, COR_DESTAQUE, rect_salvar.collidepoint(mouse_pos))

    # Histórico
    txt(tela, "Historico:", fn_pequena, COR_DIM, 14, ACAO_Y0 + 94)
    for i, h in enumerate(estado["historico"]):
        alfa = max(100, 230 - i * 18)
        cor  = (alfa, alfa, alfa)
        txt(tela, h[:22], fn_pequena, cor, 14, ACAO_Y0 + 112 + i * 15)


def desenhar_painel_dir(mouse_pos):
    painel(tela, PAINEL_DIR_X, 60, PAINEL_DIR_W, ALTURA - 80, COR_PAINEL)
    npc = estado["npc_atual"]

    if npc is None:
        txt(tela, "Selecione um tipo e", fn_normal, COR_DIM,
            LARGURA // 2, 240, centralizar=True)
        txt(tela, "clique [G] Gerar", fn_normal, COR_DIM,
            LARGURA // 2, 262, centralizar=True)
        return

    px = PAINEL_DIR_X + 14
    py = 70

    # Nome + tipo
    cor_nome = COR_ACENTO if npc["tipo"] == "monstro" else COR_OURO
    txt(tela, npc["nome"].upper(), fn_grande, cor_nome, px, py)
    txt(tela, f"[{npc['tipo']}]", fn_pequena, COR_DIM, px, py + 28)
    py += 52
    pygame.draw.line(tela, COR_BORDA, (px, py), (PAINEL_DIR_X + PAINEL_DIR_W - 14, py), 1)
    py += 8

    # Stats principais em grid
    stats = [
        ("FOR", npc["FOR"]), ("CON", npc["CON"]), ("TAM", npc["TAM"]),
        ("DES", npc["DES"]), ("INT", npc["INT"]), ("POD", npc["POD"]),
    ]
    col_w = (PAINEL_DIR_W - 28) // 3
    for i, (k, v) in enumerate(stats):
        col = i % 3
        row = i // 3
        sx  = px + col * col_w
        sy  = py + row * 22
        txt(tela, f"{k}:", fn_pequena, COR_DIM,   sx,      sy)
        txt(tela, f"{v}", fn_pequena,  COR_TEXTO, sx + 34, sy)
    py += 52

    # Derivados
    pygame.draw.line(tela, COR_BORDA, (px, py), (PAINEL_DIR_X + PAINEL_DIR_W - 14, py), 1)
    py += 8
    txt(tela, f"HP: {npc['HP']}   DB: {npc['DB']}   MOV: {npc['MOV']}   SAN: {npc['SAN']}",
        fn_normal, COR_VERDE, px, py)
    py += 26

    # Arma
    pygame.draw.line(tela, COR_BORDA, (px, py), (PAINEL_DIR_X + PAINEL_DIR_W - 14, py), 1)
    py += 8
    txt(tela, "COMBATE:", fn_media, COR_OURO, px, py)
    py += 20
    txt(tela, f"Arma:       {npc['arma']}", fn_pequena, COR_TEXTO, px, py);        py += 16
    txt(tela, f"Dano:       {npc['dano']}", fn_pequena, COR_TEXTO, px, py);        py += 16
    txt(tela, f"Habilidade: {npc['hab_arma']}%", fn_pequena, COR_TEXTO, px, py);  py += 16
    txt(tela, f"Esquivar:   {npc['pericias'].get('Esquivar',0)}%",
        fn_pequena, COR_TEXTO, px, py);  py += 20

    # Habilidades especiais (monstros)
    if npc["habilidades"]:
        pygame.draw.line(tela, COR_BORDA, (px, py), (PAINEL_DIR_X + PAINEL_DIR_W - 14, py), 1)
        py += 8
        txt(tela, "HABILIDADES:", fn_media, COR_ROXO, px, py); py += 20
        for h in npc["habilidades"]:
            txt(tela, f"  + {h}", fn_pequena, COR_TEXTO, px, py); py += 16

    if npc["fraqueza"]:
        txt(tela, f"  ! {npc['fraqueza']}", fn_pequena, COR_VERMELHO, px, py); py += 16

    # Perícias extras
    pericias_extra = {k: v for k, v in npc["pericias"].items() if k != "Esquivar"}
    if pericias_extra:
        pygame.draw.line(tela, COR_BORDA, (px, py), (PAINEL_DIR_X + PAINEL_DIR_W - 14, py), 1)
        py += 8
        txt(tela, "PERICIAS:", fn_media, COR_OURO, px, py); py += 20
        for k, v in list(pericias_extra.items())[:6]:
            txt(tela, f"  {k}: {v}%", fn_pequena, COR_DIM, px, py); py += 16


def desenhar(mouse_pos):
    tela.fill(COR_FUNDO)

    # Título
    txt(tela, "NPCs E MONSTROS", fn_titulo, COR_ACENTO, LARGURA // 2, 18, centralizar=True)
    txt(tela, "Call of Cthulhu 7e  --  Gerador", fn_pequena, COR_DIM, LARGURA // 2, 42, centralizar=True)
    pygame.draw.line(tela, COR_DESTAQUE, (8, 60), (LARGURA - 8, 60), 1)

    desenhar_painel_esq(mouse_pos)
    desenhar_painel_dir(mouse_pos)

    # Mensagem de status
    if estado["msg_timer"] > 0:
        estado["msg_timer"] -= 1
        alpha = min(255, estado["msg_timer"] * 4)
        cor_m = (min(255, COR_VERDE[0]), min(255, COR_VERDE[1] * alpha // 255), min(255, COR_VERDE[2]))
        txt(tela, estado["mensagem"], fn_normal, cor_m, LARGURA // 2, ALTURA - 30, centralizar=True)

    # Rodapé
    txt(tela, "[G] Gerar   [S] Salvar   [ESC] Sair",
        fn_pequena, COR_DIM, LARGURA // 2, ALTURA - 16, centralizar=True)

    pygame.display.flip()


# ── Loop ────────────────────────────────────────────────────

def main():
    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_g:
                    gerar_npc()
                elif event.key == pygame.K_s:
                    salvar_npc()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                rects_cat  = _rects_categorias()
                rects_tipo = _rects_tipos()

                for c, rect in rects_cat.items():
                    if rect.collidepoint(mouse_pos):
                        estado["categoria_sel"] = c
                        # Selecionar primeiro tipo da nova categoria
                        estado["tipo_sel"] = CATEGORIAS[c][0]

                for t, rect in rects_tipo.items():
                    if rect.collidepoint(mouse_pos):
                        estado["tipo_sel"] = t

                if _rect_gerar().collidepoint(mouse_pos):
                    gerar_npc()
                if _rect_salvar().collidepoint(mouse_pos):
                    salvar_npc()

        desenhar(mouse_pos)
        clock.tick(60)


if __name__ == "__main__":
    main()
