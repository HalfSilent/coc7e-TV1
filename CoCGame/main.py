"""
main.py — Ponto de entrada único do jogo.

Loop:  Intro estúdio → Tela título → Menu principal
         ├─ Novo Jogo   → TelaCriarPersonagem → TelaMundo
         ├─ Continuar   → TelaMundo (ficha salva)
         ├─ Masmorra    → TelaMasmorra (acesso rápido)
         ├─ Combate     → TelaCombate (acesso rápido)
         └─ Sair        → pygame.quit()

Tudo corre no mesmo processo pygame — sem subprocess.
A janela é criada aqui e passada para cada tela.
"""
from __future__ import annotations

import math
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "x11"

import pygame
import gerenciador_assets as _ga

LARGURA, ALTURA = 1280, 720

C_PRETO  = (  0,   0,   0)
C_OURO   = (212, 168,  67)
C_OURO_E = (255, 210,  90)
C_DIM    = (100,  90,  70)
C_FUNDO  = ( 10,   8,  18)


# ══════════════════════════════════════════════════════════════
# UTILITÁRIOS DE CENA
# ══════════════════════════════════════════════════════════════

def _fade(surf, alpha):
    copia = surf.copy()
    copia.set_alpha(max(0, min(255, alpha)))
    return copia


def _checar_skip(events):
    for e in events:
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if e.type == pygame.KEYDOWN and e.key in (
            pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER
        ):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN:
            return True
    return False


def _cena_negro(tela, clock, duracao_ms):
    inicio = pygame.time.get_ticks()
    while pygame.time.get_ticks() - inicio < duracao_ms:
        if _checar_skip(pygame.event.get()):
            return False
        tela.fill(C_PRETO)
        pygame.display.flip()
        clock.tick(60)
    return True


def _cena_estudio(tela, clock):
    fn_logo = _ga.get_font("titulo", 18)
    fn_nome = _ga.get_font("hud", 11)
    fn_tag  = _ga.get_font("hud", 12)

    LOGO = [
        " ██████╗ ██████╗ ██████╗ ",
        "██╔════╝ ██╔══██╗██╔══██╗",
        "██║  ███╗██║  ██║██████╔╝",
        "██║   ██║██║  ██║██╔═══╝ ",
        "╚██████╔╝██████╔╝██║     ",
        " ╚═════╝ ╚═════╝ ╚═╝     ",
    ]
    renders = [fn_logo.render(l, True, C_OURO) for l in LOGO]
    lh = sum(r.get_height() + 2 for r in renders)
    lw = max(r.get_width() for r in renders)
    logo_s = pygame.Surface((lw, lh), pygame.SRCALPHA)
    y = 0
    for r in renders:
        logo_s.blit(r, ((lw - r.get_width()) // 2, y)); y += r.get_height() + 2

    nome_s = fn_nome.render(
        "G A S P O L I R O   C R O C R O D R I L L O   P R O D U C T I O N S",
        True, C_OURO,
    )
    tag_s = fn_tag.render(
        "Miau, croc, croc, croc...  |  Mrrr, croc, croc...  |  Mrrr, miau, croc...",
        True, C_DIM,
    )

    cx, cy = LARGURA // 2, ALTURA // 2
    FADE_IN, HOLD, FADE_OUT = 1400, 2200, 1000
    total  = FADE_IN + HOLD + FADE_OUT
    inicio = pygame.time.get_ticks()

    while True:
        clock.tick(60)
        if _checar_skip(pygame.event.get()): return False
        elapsed = pygame.time.get_ticks() - inicio
        if elapsed > total: break
        alpha = (
            int(255 * elapsed / FADE_IN) if elapsed < FADE_IN else
            255 if elapsed < FADE_IN + HOLD else
            int(255 * (1.0 - (elapsed - FADE_IN - HOLD) / FADE_OUT))
        )
        tela.fill(C_PRETO)
        for off in (-120, 120):
            pygame.draw.line(tela, C_OURO, (cx - 280, cy + off), (cx + 280, cy + off), 1)
        tela.blit(_fade(logo_s, alpha), logo_s.get_rect(center=(cx, cy - 60)))
        tela.blit(_fade(nome_s, alpha), nome_s.get_rect(center=(cx, cy + 62)))
        tela.blit(_fade(tag_s, max(0, alpha - 60)), tag_s.get_rect(center=(cx, cy + 84)))
        pygame.display.flip()
    return True


def _cena_titulo(tela, clock):
    fn_tit  = _ga.get_font("titulo", 46)
    fn_sub  = _ga.get_font("hud", 15)
    fn_pres = _ga.get_font("hud", 13)
    fn_ver  = _ga.get_font("hud", 10)

    FADE_IN = 1800
    inicio  = pygame.time.get_ticks()
    pronto  = False

    tit_s = fn_tit.render("CALL OF CTHULHU", True, C_OURO_E)
    sub_s = fn_sub.render("7a Edicao  —  Fan Made", True, C_DIM)
    ver_s = fn_ver.render(
        "v0.1  |  Gaspoliro Crocrodrillo Productions  |  2026", True, (60, 55, 50)
    )

    random.seed(42)
    particulas = [
        (random.randint(0, LARGURA), random.randint(0, ALTURA),
         random.uniform(0.2, 1.0), random.uniform(0.0, math.pi * 2))
        for _ in range(120)
    ]

    while True:
        clock.tick(60)
        events  = pygame.event.get()
        elapsed = pygame.time.get_ticks() - inicio
        alpha   = min(255, int(255 * elapsed / FADE_IN))
        t       = elapsed / 1000.0

        if alpha >= 255:
            pronto = True
        if pronto and _checar_skip(events):
            return
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        tela.fill(C_FUNDO)
        for px, py, br, fase in particulas:
            pulso = 0.5 + 0.5 * math.sin(t * br * 2.0 + fase)
            cor   = (int(C_OURO[0] * br * 0.4 * pulso),
                     int(C_OURO[1] * br * 0.4 * pulso),
                     int(C_OURO[2] * br * 0.3 * pulso))
            pygame.draw.circle(tela, cor, (px, py), 1 if br < 0.5 else 2)

        cx, cy = LARGURA // 2, ALTURA // 2
        for sinal, base_y in ((1, 60), (-1, ALTURA - 60)):
            pts = [(x, base_y + 3 * math.sin(x * 0.02 + sinal * t * 1.5))
                   for x in range(0, LARGURA + 20, 20)]
            a = min(alpha, 80)
            pygame.draw.lines(
                tela, (C_OURO[0]*a//255, C_OURO[1]*a//255, C_OURO[2]*a//255),
                False, pts, 1,
            )

        tela.blit(_fade(tit_s, alpha),            tit_s.get_rect(center=(cx, cy - 60)))
        tela.blit(_fade(sub_s, max(0, alpha - 40)), sub_s.get_rect(center=(cx, cy + 10)))

        pulso_sep = int(100 + 80 * math.sin(t * 2.0))
        a_sep = min(alpha, pulso_sep)
        pygame.draw.line(
            tela, (C_OURO[0]*a_sep//255, C_OURO[1]*a_sep//255, C_OURO[2]*a_sep//255),
            (cx - 200, cy + 34), (cx + 200, cy + 34), 1,
        )
        if alpha >= 200:
            pisca = int(180 + 75 * math.sin(t * 3.0))
            cor_p = (C_OURO[0]*pisca//255, C_OURO[1]*pisca//255, C_OURO[2]*pisca//255)
            press = fn_pres.render("[ Pressione qualquer tecla ]", True, cor_p)
            tela.blit(press, press.get_rect(center=(cx, cy + 80)))

        tela.blit(_fade(ver_s, max(0, alpha - 80)),
                  ver_s.get_rect(bottomright=(LARGURA - 12, ALTURA - 12)))
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════
# HELPERS DE TELAS
# ══════════════════════════════════════════════════════════════

def _carregar_jogador():
    from dados.investigador_loader import carregar_jogador, ficha_existe
    if not ficha_existe():
        return None, {}
    return carregar_jogador()


def _set_local_inicial(local_id: str):
    """Grava o local de início no investigador.json antes de abrir o mundo."""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investigador.json")
    try:
        with open(path, encoding="utf-8") as f:
            dados = json.load(f)
        dados.setdefault("campanha", {})["local_id"] = local_id
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _iniciar_mundo(tela, jogador):
    from mundo.tela_mundo import TelaMundo
    from dados.investigador_loader import carregar_estado_campanha, CAMINHO_PADRAO
    mundo = TelaMundo(tela, jogador)
    camp  = carregar_estado_campanha(CAMINHO_PADRAO)
    if camp:
        e = mundo.estado
        for k in ("dinheiro", "hora", "dia", "arma_equipada", "inventario", "local_id"):
            if k in camp:
                setattr(e, k, camp[k])
    mundo.run()


# ══════════════════════════════════════════════════════════════
# FLUXO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    pygame.init()
    pygame.mixer.init()
    tela  = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Call of Cthulhu 7e")

    _RAIZ = os.path.dirname(os.path.abspath(__file__))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

    _ga.garantir_fontes(verbose=False)

    # ── Intros (todo pulável) ─────────────────────────────────
    _cena_negro(tela, clock, 400)
    _cena_estudio(tela, clock)
    _cena_negro(tela, clock, 300)
    _cena_titulo(tela, clock)
    _cena_negro(tela, clock, 200)

    # ── Áudio ─────────────────────────────────────────────────
    from engine.audio_manager import audio

    # ── Game loop ─────────────────────────────────────────────
    from ui.menu_pygame import MenuPrincipal

    while True:
        audio.play_music("menu")   # toca Hellraiser; sem-op se já tocando
        acao = MenuPrincipal(tela, clock).run()

        if acao == "sair":
            audio.stop_music(fade_ms=800)
            break

        elif acao == "novo_jogo":
            audio.stop_music()
            from ui.tela_criar_personagem import TelaCriarPersonagem
            from ui.tela_selecionar_local import TelaSelecionarLocal
            jogador = TelaCriarPersonagem(tela, clock).run()
            if jogador:
                local_id = TelaSelecionarLocal(
                    tela, clock, getattr(jogador, "nome", "")
                ).run()
                _set_local_inicial(local_id)
                _iniciar_mundo(tela, jogador)

        elif acao == "continuar":
            audio.stop_music()
            jogador, _ = _carregar_jogador()
            if jogador:
                _iniciar_mundo(tela, jogador)

        elif acao == "masmorra":
            # Acesso rápido — garante que existe ficha
            audio.stop_music()
            jogador, _ = _carregar_jogador()
            if not jogador:
                from ui.tela_criar_personagem import TelaCriarPersonagem
                jogador = TelaCriarPersonagem(tela, clock).run()
            if jogador:
                from masmorra.tela_masmorra import TelaMasmorra
                TelaMasmorra(tela, jogador).run()

        elif acao == "combate":
            audio.stop_music()
            jogador, pericias = _carregar_jogador()
            if jogador:
                from engine.entidade import Inimigo
                from combate.tela_combate import TelaCombate
                TelaCombate(
                    tela, jogador,
                    inimigos=[
                        Inimigo("Cultista", col=8, linha=2),
                        Inimigo("Cultista", col=9, linha=5),
                    ],
                    pericias=pericias,
                ).run()

        elif acao == "criador_legado":
            # DearPyGui standalone — mantido para Campanhas/
            import subprocess
            ficha_path = os.path.join(_RAIZ, "ui", "ficha.py")
            if os.path.exists(ficha_path):
                subprocess.run([sys.executable, ficha_path])

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
