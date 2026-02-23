"""
ui/menu_pygame.py — Menu principal do jogo.

Expõe a classe MenuPrincipal que o main.py instancia e chama .run().
.run() retorna uma das strings:
    "novo_jogo" | "continuar" | "masmorra" | "combate"
  | "editor" | "criador_legado" | "sair"
"""
from __future__ import annotations

import json
import math
import os
import sys

import pygame

# ── caminhos ──────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))   # ui/
_RAIZ = os.path.dirname(_BASE)                       # CoCGame/
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import gerenciador_assets as _ga

try:
    from engine.audio_manager import audio as _audio
except Exception:
    _audio = None  # type: ignore

# ── constantes visuais ─────────────────────────────────────────
LARGURA, ALTURA = 1920, 1080   # default — será sobreposto por screen.get_size() em tempo real

COR_FUNDO     = ( 26,  26,  46)
COR_PAINEL    = ( 22,  33,  62)
COR_DESTAQUE  = ( 15,  52,  96)
COR_ACENTO    = (233,  69,  96)
COR_TEXTO     = (238, 226, 220)
COR_TEXTO_DIM = (154, 140, 152)
COR_OURO      = (212, 168,  67)
COR_VERDE     = ( 78, 204, 163)
COR_ROXO      = (107,  45, 139)
COR_SAIR      = ( 51,  51,  85)
COR_SEP       = ( 40,  55,  90)
COR_NOVO      = ( 20,  80,  40)
COR_CONT      = ( 40,  60,  20)

BOTAO_W  = 400
BOTAO_H  = 44
ESPACO   = 52
BOTAO_Y0 = 230


# ── utilidade ─────────────────────────────────────────────────

def _ficha_existe() -> bool:
    try:
        from dados.investigador_loader import ficha_existe
        return ficha_existe()
    except Exception:
        return False


def _nome_salvo() -> str:
    path = os.path.join(_RAIZ, "investigador.json")
    try:
        with open(path, encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get("dados_pessoais", {}).get("nome", "").strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════
class MenuPrincipal:
    """Menu principal instanciável — reutiliza a janela de main.py."""

    def __init__(self, tela: pygame.Surface, clock: pygame.time.Clock):
        self.tela  = tela
        self.clock = clock
        _ga.garantir_fontes(verbose=False)

        self._fn_tit    = _ga.get_font("titulo", 48)
        self._fn_subtit = _ga.get_font("hud",    15)
        self._fn_botao  = _ga.get_font("titulo", 17)
        self._fn_sep    = _ga.get_font("hud",    11)
        self._fn_rodape = _ga.get_font("hud",     9)

        self._botoes = self._montar_botoes()

    # ── construção dinâmica ────────────────────────────────────

    def _montar_botoes(self) -> list[dict]:
        tem_ficha = _ficha_existe()
        nome      = _nome_salvo()

        lista: list[dict] = []

        if tem_ficha:
            label_jogar = f"[J]  Continuar — {nome}" if nome else "[J]  Continuar"
            lista.append({
                "texto": label_jogar,
                "cor":   COR_CONT,
                "acao":  "continuar",
                "desc":  f"Retomar aventura de {nome} em Arkham" if nome else "Retomar aventura em Arkham",
            })
        else:
            lista.append({
                "texto": "[J]  Novo Jogo",
                "cor":   COR_NOVO,
                "acao":  "novo_jogo",
                "desc":  "Criar investigador e começar em Arkham",
            })

        lista += [
            {"texto": "[M]  Masmorra",       "cor": (45, 35, 60),  "acao": "masmorra",
             "desc": "Exploração top-down · Combate tático por turnos"},
            {"texto": "[C]  Combate Rápido", "cor": COR_ROXO,      "acao": "combate",
             "desc": "Combate tático grid 2D · cartas · efeitos ambientais"},
        ]

        lista.append({"sep": "── Extras ───────────────────────────────────"})

        if tem_ficha:
            lista.append({
                "texto": "[N]  Novo Jogo",  "cor": COR_ACENTO, "acao": "novo_jogo",
                "desc": "Recomeçar — criar novo investigador",
            })
        lista.append({
            "texto": "[E]  Editor de Mapas", "cor": (30, 55, 70),
            "acao": "editor",
            "desc": "Editor visual de mapas · pincel · flood fill · inimigos · objetos",
        })
        lista.append({
            "texto": "[F]  Criador Legado (DearPyGui)", "cor": COR_DESTAQUE,
            "acao": "criador_legado",
            "desc": "Ficha completa via editor externo",
        })

        lista.append({"sep": "─────────────────────────────────────────────"})
        lista.append({"texto": "[ESC]  Sair", "cor": COR_SAIR, "acao": "sair", "desc": ""})

        return lista

    # ── desenho ───────────────────────────────────────────────

    def _calcular_rects(self) -> list[tuple[pygame.Rect, dict]]:
        W, H = self.tela.get_size()
        rects = []
        y = int(H * 0.32)   # 32% da altura
        for b in self._botoes:
            if "sep" in b:
                y += 24
                continue
            bw = min(BOTAO_W, W - 100)
            x = (W - bw) // 2
            rects.append((pygame.Rect(x, y, bw, BOTAO_H), b))
            y += ESPACO
        return rects

    def _draw_botao(self, rect: pygame.Rect, botao: dict, hover: bool):
        cor_base = botao["cor"]
        if hover:
            cor = tuple(min(255, c + 50) for c in cor_base)
            sombra = rect.inflate(6, 6)
            s = pygame.Surface((sombra.width, sombra.height), pygame.SRCALPHA)
            pygame.draw.rect(s, (*cor_base, 80), s.get_rect(), border_radius=12)
            self.tela.blit(s, sombra.topleft)
        else:
            cor = cor_base

        pygame.draw.rect(self.tela, cor, rect, border_radius=8)
        pygame.draw.rect(self.tela, tuple(min(255, c + 70) for c in cor_base),
                         rect, width=1, border_radius=8)

        surf = self._fn_botao.render(botao["texto"], True, COR_TEXTO)
        self.tela.blit(surf, surf.get_rect(center=rect.center))

        desc = botao.get("desc", "")
        if hover and desc:
            ds = self._fn_sep.render(desc, True, COR_TEXTO_DIM)
            self.tela.blit(ds, ds.get_rect(centerx=rect.centerx, y=rect.bottom + 2))

    def _draw_separadores(self):
        W, H = self.tela.get_size()
        y = int(H * 0.32)
        for b in self._botoes:
            if "sep" in b:
                s = self._fn_sep.render(b["sep"], True, COR_SEP)
                self.tela.blit(s, s.get_rect(centerx=W // 2, y=y + 4))
                y += 24
            else:
                y += ESPACO

    def _draw_particulas(self, t: float):
        W, H = self.tela.get_size()
        for i in range(50):
            x = (i * 157 + int(t * 8  * (i % 4 + 1))) % W
            y = (i * 113 + int(t * 4  * (i % 5 + 1))) % H
            alfa = int(60 + abs(math.sin(t + i)) * 80)
            pygame.draw.circle(
                self.tela,
                (min(255, alfa), min(255, alfa), min(255, alfa + 40)),
                (x, y), 1,
            )

    def _draw_titulo(self, t: float):
        W, H = self.tela.get_size()
        cy_base = int(H * 0.12)
        pulso = abs(math.sin(t * 1.5))
        cor   = (int(200 + pulso * 33), int(50 + pulso * 19), int(80 + pulso * 16))

        surf_icon = self._fn_tit.render("~@ ~", True, cor)
        self.tela.blit(surf_icon, surf_icon.get_rect(centerx=W // 2, y=cy_base))

        surf_t = self._fn_tit.render("CALL OF CTHULHU", True, cor)
        self.tela.blit(surf_t, surf_t.get_rect(centerx=W // 2, y=cy_base + 78))

        surf_s = self._fn_subtit.render("7a Edicao  --  Sistema de Jogo", True, COR_OURO)
        self.tela.blit(surf_s, surf_s.get_rect(centerx=W // 2, y=cy_base + 138))

        sep_y = cy_base + 158
        pygame.draw.line(self.tela, COR_DESTAQUE,
                         (W // 2 - 190, sep_y),
                         (W // 2 + 190, sep_y), 1)

    # ── loop ──────────────────────────────────────────────────

    def run(self) -> str:
        """Executa o menu e retorna a ação escolhida como string."""
        _hover_anterior: int = -1   # rastreia hover para sfx de rollover
        _MAPA_TECLAS = {
            pygame.K_j:      "jogar",   # mapeado abaixo
            pygame.K_m:      "masmorra",
            pygame.K_c:      "combate",
            pygame.K_e:      "editor",
            pygame.K_f:      "criador_legado",
            pygame.K_n:      "novo_jogo",
            pygame.K_ESCAPE: "sair",
        }

        # Descobre qual ação o [J] dispara (continuar OU novo_jogo)
        acao_j = "continuar" if _ficha_existe() else "novo_jogo"

        while True:
            t         = pygame.time.get_ticks() / 1000.0
            mouse_pos = pygame.mouse.get_pos()
            rects     = self._calcular_rects()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    flags = self.tela.get_flags()
                    if flags & pygame.FULLSCREEN:
                        self.tela = pygame.display.set_mode(
                            (LARGURA, ALTURA), pygame.RESIZABLE)
                    else:
                        self.tela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, botao in rects:
                        if rect.collidepoint(mouse_pos):
                            if _audio: _audio.play_sfx("menu_select")
                            return botao["acao"]

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_j:
                        if _audio: _audio.play_sfx("menu_select")
                        return acao_j
                    acao = _MAPA_TECLAS.get(event.key)
                    if acao:
                        if _audio: _audio.play_sfx("menu_select")
                        return acao

            # ── desenho ──
            W, H = self.tela.get_size()
            self.tela.fill(COR_FUNDO)
            self._draw_particulas(t)
            self._draw_titulo(t)
            self._draw_separadores()

            # rollover SFX
            hover_idx = next(
                (i for i, (r, _) in enumerate(rects) if r.collidepoint(mouse_pos)), -1
            )
            if hover_idx != _hover_anterior:
                if hover_idx >= 0 and _audio:
                    _audio.play_sfx("menu_open", volume=0.4)
                _hover_anterior = hover_idx

            for rect, botao in rects:
                self._draw_botao(rect, botao, rect.collidepoint(mouse_pos))

            rodape = self._fn_rodape.render(
                "Ph'nglui mglw'nafh Cthulhu R'lyeh wgah'nagl fhtagn",
                True, COR_DESTAQUE,
            )
            self.tela.blit(rodape,
                           rodape.get_rect(centerx=W // 2, y=H - 22))

            pygame.display.flip()
            self.clock.tick(60)


# ── entry-point standalone (compatibilidade) ──────────────────
def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")
    pygame.init()
    tela  = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Call of Cthulhu 7e")
    _ga.garantir_fontes(verbose=False)

    acao = MenuPrincipal(tela, clock).run()
    print(f"[menu_pygame standalone] acao={acao}")
    pygame.quit()


if __name__ == "__main__":
    main()
