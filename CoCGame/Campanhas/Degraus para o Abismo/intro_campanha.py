"""
intro_campanha.py — Tela de introdução atmosférica da campanha.

Exibe o texto de abertura com efeito typewriter, iluminação de vela
e partículas de névoa. Ao final lança mundo_aberto.py.

Se existir investigador.json, exibe uma tela intermediária com o
nome, ocupação e instruções antes de abrir o mapa.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

# SDL_VIDEODRIVER deve ser definido ANTES de qualquer import pygame.
os.environ["SDL_VIDEODRIVER"] = "x11"

import pygame

# ── Caminhos ──────────────────────────────────────────────────
_DIR      = os.path.dirname(os.path.abspath(__file__))
_RAIZ     = os.path.normpath(os.path.join(_DIR, "..", ".."))
_MUNDO    = os.path.join(_RAIZ, "mundo_aberto.py")
_FICHA    = os.path.join(_RAIZ, ".github", "investigador.json")
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import gerenciador_mundos as _gm
import gerenciador_assets as _ga
_MUNDO_ID = _gm.mundo_da_campanha(_DIR)

# ── Dimensões ─────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60

# ── Paleta ────────────────────────────────────────────────────
FUNDO   = (  4,   4,  10)
TEXTO   = (232, 218, 210)
DIM     = (140, 128, 115)
OURO    = (212, 168,  67)
CINABRE = (180,  55,  35)
SEPIA   = (100,  85,  60)


def _fonte(size: int, estilo: str = "narrativa") -> pygame.font.Font:
    return _ga.get_font(estilo, size)


# ── Texto de introdução ───────────────────────────────────────

INTRO: list[tuple[str, str]] = [
    ("Rio de Janeiro, Junho de 1923.",                                            "destaque"),
    ("",                                                                          "vazio"),
    ("A cidade fervilha sob um calor úmido que não cede nem à noite.",            "normal"),
    ("O bairro do Catumbi dorme entre sobrados coloniais e vielas",               "normal"),
    ("que guardam segredos mais antigos do que qualquer mapa oficial.",           "normal"),
    ("",                                                                          "vazio"),
    ("Há três dias, o Prof. Ernesto Malheiros — historiador renomado",           "normal"),
    ("da Faculdade de Arqueologia — não aparece para dar aulas.",                 "normal"),
    ("Seu Benedito, do botequim da esquina, jura que o viu",                      "normal"),
    ("sair às três da manhã carregando uma caixa de madeira.",                    "normal"),
    ("",                                                                          "vazio"),
    ("Esta manhã você recebeu um bilhete sem assinatura:",                        "normal"),
    ("",                                                                          "vazio"),
    ("  \"Ele encontrou o Fragmento.",                                            "citacao"),
    ("   Eles já sabem.",                                                         "citacao"),
    ("   Venha antes que os Filhos do Degrau cheguem.\"",                        "citacao"),
    ("",                                                                          "vazio"),
    ("                              — Seu Benedito,",                             "assinatura"),
    ("                                Botequim do Catumbi.",                      "assinatura"),
    ("",                                                                          "vazio"),
    ("",                                                                          "vazio"),
    ("[ ESPAÇO ] para continuar...",                                              "dica"),
]

_ESTILO_COR = {
    "normal":     (222, 208, 198),
    "destaque":   (212, 168,  67),
    "vazio":      None,
    "citacao":    (170, 155, 130),
    "assinatura": (140, 125, 100),
    "dica":       None,
}


# ══════════════════════════════════════════════════════════════
#  TELA DE APRESENTAÇÃO DO INVESTIGADOR
# ══════════════════════════════════════════════════════════════

def _tela_investigador(tela: pygame.Surface, clock: pygame.time.Clock):
    """
    Exibe o investigador criado e as instruções de controle.
    Retorna quando o jogador pressiona ESPAÇO/ENTER/clique.
    """
    ficha: dict = {}
    if os.path.exists(_FICHA):
        try:
            with open(_FICHA, encoding="utf-8") as f:
                ficha = json.load(f)
        except Exception:
            pass

    dados   = ficha.get("dados_pessoais",  {})
    caract  = ficha.get("caracteristicas", {})
    nome    = dados.get("nome",     "Investigador Desconhecido")
    ocup    = dados.get("ocupacao", "")
    idade   = dados.get("idade",    "")
    san     = caract.get("sanidade", 0)
    hp      = caract.get("pv_max",   0)

    fn_big  = _fonte(28)
    fn_med  = _fonte(17)
    fn_sml  = _fonte(14)
    fn_hint = _fonte(13)

    # Linhas de instrução (sempre visíveis)
    INSTRUCOES = [
        ("CONTROLES", "destaque"),
        ("", ""),
        ("WASD  /  ←↑↓→    Mover",           "normal"),
        ("SHIFT               Correr",         "normal"),
        ("E                   Interagir / Dialogar", "normal"),
        ("P                   Pausar o tempo", "normal"),
        ("F5                  Salvar",          "normal"),
        ("ESC                 Menu principal",  "normal"),
        ("", ""),
        ("Encontre o Botequim do Catumbi.", "dica"),
        ("Fale com Seu Benedito.",          "dica"),
    ]

    done = False
    while not done:
        t = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                done = True

        tela.fill(FUNDO)

        # Vinheta lateral (luz de vela)
        for lado_x in (22, W - 22):
            for i in range(14):
                py_v = 40 + i * 40
                flk  = int(55 + 45 * abs(math.sin(t * 0.003 + i * 0.7 + lado_x)))
                ov_v = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(ov_v, (flk, flk // 3, 0, 35), (10, 10), 9)
                tela.blit(ov_v, (lado_x - 10, py_v - 10))

        # ── Cabeçalho ─────────────────────────────────────────
        pygame.draw.line(tela, (55, 45, 25), (60, 38), (W - 60, 38), 1)
        hdr = fn_sml.render("DEGRAUS PARA O ABISMO  ·  Call of Cthulhu 7e",
                             True, (80, 70, 50))
        tela.blit(hdr, hdr.get_rect(centerx=W // 2, y=16))
        pygame.draw.line(tela, (55, 45, 25), (60, 48), (W - 60, 48), 1)

        # ── Coluna esquerda: investigador ─────────────────────
        CX = 90
        y  = 80

        # Marcador decorativo
        marca = fn_sml.render("── O Investigador ──", True, (80, 68, 45))
        tela.blit(marca, (CX, y));  y += 30

        # Nome
        s = fn_big.render(nome, True, OURO)
        tela.blit(s, (CX, y));  y += s.get_height() + 6

        # Ocupação + Idade
        if ocup:
            s2 = fn_med.render(ocup + (f"  ·  {idade}" if idade else ""),
                                True, (200, 185, 165))
            tela.blit(s2, (CX, y));  y += s2.get_height() + 18

        # Separador
        pygame.draw.line(tela, (55, 45, 30), (CX, y), (CX + 300, y), 1)
        y += 14

        # Barras SAN / HP
        def _barra_intro(label: str, atual: int, maximo: int,
                         yy: int, cor: tuple):
            lb = fn_sml.render(f"{label}  {atual}/{maximo}", True, DIM)
            tela.blit(lb, (CX, yy))
            BW, BH = 200, 11
            bx = CX + 80
            pygame.draw.rect(tela, (30, 35, 30), (bx, yy, BW, BH), border_radius=3)
            frac = max(0.0, min(1.0, atual / maximo)) if maximo > 0 else 0.0
            if frac > 0:
                pygame.draw.rect(tela, cor,
                                 (bx, yy, int(BW * frac), BH),
                                 border_radius=3)

        if san > 0:
            _barra_intro("SAN", san, san, y, (78, 180, 140));  y += 22
        if hp > 0:
            _barra_intro("HP ", hp,  hp,  y, (200, 70, 70));   y += 22

        y += 12
        # Citação de ambientação
        cit = fn_sml.render("\"O que não pode ser nomeado não pode ser derrotado.\"",
                             True, (110, 98, 78))
        tela.blit(cit, (CX, y));  y += cit.get_height() + 4
        aut = fn_hint.render("— Fragmentos de Valverde, p.7", True, (72, 62, 45))
        tela.blit(aut, (CX + 20, y))

        # ── Divisor vertical ──────────────────────────────────
        pygame.draw.line(tela, (45, 38, 28), (W // 2 + 20, 70), (W // 2 + 20, H - 55), 1)

        # ── Coluna direita: controles ─────────────────────────
        RX = W // 2 + 42
        ry = 80

        for txt, estilo in INSTRUCOES:
            if not txt:
                ry += 10; continue
            if estilo == "destaque":
                s = fn_med.render(txt, True, OURO)
            elif estilo == "dica":
                pulso = int(130 + 90 * math.sin(t * 0.003))
                s = fn_hint.render(txt, True,
                                   (pulso, int(pulso * 0.8), int(pulso * 0.55)))
            else:
                s = fn_hint.render(txt, True, (185, 172, 155))
            tela.blit(s, (RX, ry))
            ry += s.get_height() + 5

        # ── Dica de início ────────────────────────────────────
        pulso2 = int(160 + 80 * math.sin(t * 0.003))
        c_hint = (int(OURO[0]*pulso2//255),
                  int(OURO[1]*pulso2//255),
                  int(OURO[2]*pulso2//255))
        hint = fn_sml.render("[ ESPAÇO ] para entrar no Rio de 1923...", True, c_hint)
        tela.blit(hint, hint.get_rect(centerx=W // 2, y=H - 32))

        pygame.display.flip()
        clock.tick(FPS)


# ══════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL DA INTRO
# ══════════════════════════════════════════════════════════════

def main():
    pygame.init()
    tela  = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Degraus para o Abismo — Introdução")
    clock = pygame.time.Clock()

    fn_tit  = _fonte(18)
    fn_txt  = _fonte(15)
    fn_dim  = _fonte(12)

    MARGEM  = 85
    MAX_W   = W - 2 * MARGEM
    LH      = fn_txt.get_linesize() + 3
    CHARS_S = 28
    TOP_Y   = 58
    BOTTOM  = H - 38

    reveal = 0.0
    done   = False

    total_chars = sum(
        len(txt) + 1 if estilo != "vazio" else 1
        for txt, estilo in INTRO
    )

    import random
    random.seed(7)
    nevoa = [(random.randint(0, W), random.randint(0, H),
              random.uniform(0.2, 0.8), random.uniform(0, math.pi * 2))
             for _ in range(40)]

    def _avancar():
        """Após a intro, mostra a tela do investigador e lança o mundo."""
        _tela_investigador(tela, clock)
        subprocess.Popen([sys.executable, _MUNDO, "--mundo", _MUNDO_ID])
        os._exit(0)

    while True:
        dt = clock.tick(FPS)
        t  = pygame.time.get_ticks()

        if not done:
            reveal += CHARS_S * dt / 1000.0
            if reveal >= total_chars:
                reveal = float(total_chars)
                done   = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _avancar()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                   pygame.K_KP_ENTER):
                    if done:
                        _avancar()
                    else:
                        reveal = float(total_chars)
                        done   = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if done:
                    _avancar()
                else:
                    reveal = float(total_chars)
                    done   = True

        # ── Fundo e névoa ─────────────────────────────────────
        tela.fill(FUNDO)

        for nx, ny, brilho, fase in nevoa:
            pulso = 0.4 + 0.3 * math.sin(t * 0.0005 * brilho + fase)
            a     = int(10 * pulso)
            r     = int(3 + brilho * 4)
            if a > 0:
                nv = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(nv, (a, a, a, a * 3),
                                   (r + 1, r + 1), r)
                tela.blit(nv, (nx - r, ny - r))

        # Velas laterais
        for lado_x in (28, W - 28):
            for i in range(12):
                py_v = 50 + i * 45
                flk  = int(55 + 45 * abs(math.sin(t * 0.003 + i * 0.9 + lado_x)))
                ov_v = pygame.Surface((22, 22), pygame.SRCALPHA)
                pygame.draw.circle(ov_v, (flk, flk // 3, 0, 40), (11, 11), 10)
                tela.blit(ov_v, (lado_x - 11, py_v - 11))
                pygame.draw.circle(tela, (min(255, flk + 60), flk // 2, 0),
                                   (lado_x, py_v), 1)

        # Cabeçalho
        pygame.draw.line(tela, (45, 38, 22), (MARGEM, 34), (W - MARGEM, 34), 1)
        hdr = fn_dim.render("DEGRAUS PARA O ABISMO  ·  Call of Cthulhu 7e",
                            True, (80, 70, 50))
        tela.blit(hdr, hdr.get_rect(centerx=W // 2, y=18))
        pygame.draw.line(tela, (45, 38, 22), (MARGEM, 42), (W - MARGEM, 42), 1)

        # ── Typewriter ────────────────────────────────────────
        chars_restante = int(reveal)
        y = TOP_Y

        for txt, estilo in INTRO:
            if y >= BOTTOM:
                break

            if estilo == "vazio":
                y += LH // 2
                chars_restante -= 1
                continue

            if chars_restante <= 0 and estilo != "dica":
                break

            cor = _ESTILO_COR.get(estilo, TEXTO)

            if estilo == "dica":
                if done:
                    pulso = int(160 + 95 * math.sin(t * 0.003))
                    c = (int(OURO[0] * pulso / 255),
                         int(OURO[1] * pulso / 255),
                         int(OURO[2] * pulso / 255))
                    surf = fn_dim.render(txt, True, c)
                    tela.blit(surf, surf.get_rect(centerx=W // 2, y=y))
                y += LH
                continue

            mostr = txt[:chars_restante] if chars_restante < len(txt) else txt
            chars_restante -= len(txt) + 1

            fn = fn_tit if estilo == "destaque" else fn_txt
            surf = fn.render(mostr, True, cor)

            if estilo in ("citacao", "assinatura"):
                tela.blit(surf, (MARGEM + 20, y))
            elif estilo == "destaque":
                tela.blit(surf, surf.get_rect(centerx=W // 2, y=y))
            else:
                tela.blit(surf, (MARGEM, y))

            y += (fn_tit.get_linesize() + 3
                  if estilo == "destaque" else LH)

        if not done:
            pular = fn_dim.render("[ ESPAÇO ] pular", True, (42, 38, 30))
            tela.blit(pular, pular.get_rect(right=W - MARGEM, y=H - 22))

        pygame.display.flip()


if __name__ == "__main__":
    main()

