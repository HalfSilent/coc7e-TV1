"""
sistema_pericia.py — Painel de teste de perícia inline (CoC 7e).

Uso básico:
    from sistema_pericia import PainelTeste

    resultado = PainelTeste(
        tela        = pygame_surface,
        pericia     = "Biblioteca",
        valor       = 60,
        dificuldade = "normal",          # "normal" | "dificil" | "extremo"
        contexto    = "Você examina os documentos...",
        texto_ok    = "Encontrou referências ao ritual de 1887.",
        texto_fail  = "Os documentos não revelam nada útil.",
    ).rodar(fundo_surface)

    resultado.sucesso     → bool
    resultado.dado        → int (1-100)
    resultado.grau        → "extremo"|"dificil"|"sucesso"|"falha"|"fumble"

Para teste de SAN:
    resultado = PainelTeste(
        tela          = pygame_surface,
        pericia       = "san",
        valor         = 65,
        contexto      = "Geometrias impossíveis nos relevos da câmara...",
        perda_sucesso = "1",       # -1 SAN se passar
        perda_falha   = "1d6",     # -1d6 SAN se falhar
        san_atual     = 65,
    ).rodar(fundo_surface)

    resultado.san_delta   → int (≤ 0)
    resultado.san_final   → int
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

import pygame

# ── Fonte ──────────────────────────────────────────────────────
_FONTE = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf"


def _f(size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(_FONTE, size)
    except Exception:
        return pygame.font.SysFont("monospace", size)


# ── Paleta ─────────────────────────────────────────────────────
_C: dict[str, tuple] = {
    "fundo":   (  8,  12,  26),
    "painel":  ( 14,  20,  44),
    "borda":   ( 45,  65, 105),
    "ouro":    (212, 168,  67),
    "texto":   (238, 226, 220),
    "dim":     (130, 118, 112),
    "verde":   ( 78, 204, 163),
    "acento":  (233,  69,  96),
    "extremo": (255, 215,   0),
    "dificil": ( 78, 204, 163),
    "sucesso": (120, 220, 120),
    "falha":   (233,  69,  96),
    "fumble":  (200,  30,  30),
}

# ── Dimensões do painel ────────────────────────────────────────
_PW = 540
_PH = 380

# ── Aliases de perícias ────────────────────────────────────────
# Normaliza strings do twee (sem acento, lowercase) → nome exato da ficha
_ALIASES: dict[str, str] = {
    "biblioteca":          "Biblioteca",
    "ocultismo":           "Ocultismo",
    "psicologia":          "Psicologia",
    "escutar":             "Escutar",
    "localizar":           "Localizar",
    "medicina":            "Medicina",
    "persuasao":           "Persuasão",
    "persuasão":           "Persuasão",
    "furtividade":         "Furtividade",
    "historia":            "História",
    "história":            "História",
    "mitos":               "Mitos de Cthulhu",
    "mitos de cthulhu":    "Mitos de Cthulhu",
    "arqueologia":         "Arqueologia",
    "primeiros socorros":  "Primeiros Socorros",
    "intimidacao":         "Intimidação",
    "intimidação":         "Intimidação",
    "forca":               "Forca",
    "sorte":               "Sorte",
    "san":                 "san",
}


def normalizar_pericia(nome: str) -> str:
    return _ALIASES.get(nome.lower().strip(), nome)


# ══════════════════════════════════════════════════════════════
#  FUNÇÕES AUXILIARES CoC 7e
# ══════════════════════════════════════════════════════════════

def rolar_dado(expr: str) -> int:
    """Avalia expressão de dado: '1d6', '2d6', '1d8+1', '3', etc."""
    expr  = str(expr).strip().lower()
    total = 0
    for parte in expr.split("+"):
        parte = parte.strip()
        if "d" in parte:
            n, d  = parte.split("d", 1)
            n     = int(n) if n else 1
            d     = int(d) if d else 6
            total += sum(random.randint(1, d) for _ in range(n))
        elif parte:
            total += int(parte)
    return total


def grau_sucesso(dado: int, valor_efetivo: int, valor_base: int) -> str:
    """Calcula grau do teste CoC 7e."""
    if dado <= max(1, valor_efetivo // 5):
        return "extremo"
    if dado <= max(1, valor_efetivo // 2):
        return "dificil"
    if dado <= valor_efetivo:
        return "sucesso"
    limiar_fumble = 96 if valor_base < 50 else 100
    if dado >= limiar_fumble:
        return "fumble"
    return "falha"


# ══════════════════════════════════════════════════════════════
#  RESULTADO
# ══════════════════════════════════════════════════════════════

@dataclass
class ResultadoTeste:
    pericia:   str
    valor:     int
    dado:      int
    grau:      str   # "extremo"|"dificil"|"sucesso"|"falha"|"fumble"
    sucesso:   bool
    san_delta: int   # 0 para testes normais; negativo para testes de SAN
    san_final: int   # SAN atual após o teste

    @property
    def label(self) -> str:
        return {
            "extremo": "SUCESSO EXTREMO",
            "dificil": "SUCESSO DIFÍCIL",
            "sucesso": "SUCESSO",
            "falha":   "FALHA",
            "fumble":  "FALHA CRÍTICA",
        }.get(self.grau, self.grau.upper())

    @property
    def cor(self) -> tuple:
        return _C.get(self.grau, _C["texto"])


# ══════════════════════════════════════════════════════════════
#  PAINEL DE TESTE
# ══════════════════════════════════════════════════════════════

class PainelTeste:
    """
    Exibe painel animado de teste de perícia por cima do mapa.
    Fases:
        ANUNCIO   → mostra perícia, contexto e "ESPAÇO para rolar"
        ROLANDO   → dado animado girando por 1.5s
        RESULTADO → grau (SUCESSO / FALHA) + texto de consequência
    """

    _ANUNCIO   = "anuncio"
    _ROLANDO   = "rolando"
    _RESULTADO = "resultado"
    _ANIM_DUR  = 1.5   # segundos de animação do dado

    def __init__(self,
                 tela:          pygame.Surface,
                 pericia:       str,
                 valor:         int,
                 dificuldade:   str = "normal",
                 contexto:      str = "",
                 texto_ok:      str = "",
                 texto_fail:    str = "",
                 perda_sucesso: str = "1",
                 perda_falha:   str = "1d6",
                 san_atual:     int = 0):

        self.tela        = tela
        self.pericia     = normalizar_pericia(pericia)
        self.eh_san      = (self.pericia == "san")
        self.dificuldade = dificuldade.lower()
        self.contexto    = contexto
        self.texto_ok    = texto_ok
        self.texto_fail  = texto_fail
        self.perda_suc   = perda_sucesso
        self.perda_fail  = perda_falha
        self.san_atual   = san_atual

        self._valor_base = valor
        self._valor_ef   = {
            "normal":  valor,
            "dificil": max(1, valor // 2),
            "extremo": max(1, valor // 5),
        }.get(self.dificuldade, valor)

        # Fontes
        self._fn_title  = _f(20)
        self._fn_normal = _f(15)
        self._fn_small  = _f(12)
        self._fn_big    = _f(38)

        # Posição do painel (centralizado)
        W, H            = tela.get_size()
        self._px        = (W - _PW) // 2
        self._py        = (H - _PH) // 2

        # Estado interno
        self._fase:    str                       = self._ANUNCIO
        self._dado_f:  int                       = 0       # dado final
        self._dado_a:  int                       = 0       # dado animado
        self._anim_t:  float                     = 0.0
        self._res:     Optional[ResultadoTeste]  = None
        self._msg_san: str                       = ""

    # ── Loop ──────────────────────────────────────────────────

    def rodar(self, fundo: pygame.Surface) -> ResultadoTeste:
        """Bloqueia até o jogador confirmar; retorna ResultadoTeste."""
        clock = pygame.time.Clock()

        while True:
            dt = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._avancar()
                    elif event.key == pygame.K_ESCAPE:
                        if self._fase == self._ANUNCIO:
                            self._avancar()   # pula para rolar

            # Animação do dado
            if self._fase == self._ROLANDO:
                self._anim_t += dt
                if self._anim_t < self._ANIM_DUR:
                    self._dado_a = random.randint(1, 100)
                else:
                    self._dado_a = self._dado_f
                    self._fase   = self._RESULTADO
                    self._calcular()

            # Saída quando resultado confirmado
            if self._fase == self._RESULTADO and self._res is not None:
                # Aguarda confirmação do ESPAÇO
                pass

            # Render
            self.tela.blit(fundo, (0, 0))
            self._render_overlay()
            self._render_painel()
            pygame.display.flip()

            # Sai do loop só após resultado E ESPAÇO confirmado
            # (controlado pelo _avancar() quando _fase==RESULTADO não avança
            # mais — o while verifica _res e RESULTADO)
            if self._fase == self._RESULTADO and self._res is not None:
                # Espera mais um ESPAÇO/RETURN para sair
                # Vira para um estado final
                if self._fase == "_SAINDO":
                    break

        return self._res  # type: ignore

    def _avancar(self):
        if self._fase == self._ANUNCIO:
            self._dado_f = random.randint(1, 100)
            self._anim_t = 0.0
            self._fase   = self._ROLANDO

        elif self._fase == self._RESULTADO:
            self._fase = "_SAINDO"

    def _calcular(self):
        dado  = self._dado_f
        grau  = grau_sucesso(dado, self._valor_ef, self._valor_base)
        suc   = grau in ("extremo", "dificil", "sucesso")

        san_delta = 0
        san_final = self.san_atual
        if self.eh_san:
            expr       = self.perda_suc if suc else self.perda_fail
            san_delta  = -rolar_dado(expr)
            san_final  = max(0, self.san_atual + san_delta)
            self._msg_san = (
                f"Perda: {-san_delta} SAN  "
                f"({self.san_atual} → {san_final})"
            )

        self._res = ResultadoTeste(
            pericia   = self.pericia,
            valor     = self._valor_base,
            dado      = dado,
            grau      = grau,
            sucesso   = suc,
            san_delta = san_delta,
            san_final = san_final,
        )

    # ── Renderização ──────────────────────────────────────────

    def _render_overlay(self):
        W, H = self.tela.get_size()
        ov   = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 165))
        self.tela.blit(ov, (0, 0))

    def _render_painel(self):
        surf = pygame.Surface((_PW, _PH), pygame.SRCALPHA)
        surf.fill((*_C["painel"], 248))
        pygame.draw.rect(surf, _C["borda"], (0, 0, _PW, _PH), 2, border_radius=6)

        # ── Cabeçalho ──────────────────────────────────────────
        cab_h = 44
        pygame.draw.rect(surf, _C["fundo"],
                         (2, 2, _PW - 4, cab_h - 2), border_radius=5)
        pygame.draw.line(surf, _C["borda"], (0, cab_h), (_PW, cab_h), 1)

        if self.eh_san:
            cab_txt = "TESTE DE SANIDADE"
            cab_cor = _C["acento"]
        else:
            nivel = {
                "normal":  "",
                "dificil": "  [DIFÍCIL]",
                "extremo": "  [EXTREMO]",
            }.get(self.dificuldade, "")
            cab_txt = f"TESTE DE {self.pericia.upper()}{nivel}"
            cab_cor = _C["ouro"]

        s = self._fn_title.render(cab_txt, True, cab_cor)
        surf.blit(s, s.get_rect(centerx=_PW // 2, y=11))

        # ── Corpo por fase ─────────────────────────────────────
        corpo_y = cab_h + 14
        if self._fase == self._ANUNCIO:
            self._fase_anuncio(surf, corpo_y)
        elif self._fase == self._ROLANDO:
            self._fase_rolando(surf, corpo_y)
        else:
            self._fase_resultado(surf, corpo_y)

        self.tela.blit(surf, (self._px, self._py))

    # ── Fase 1: Anúncio ────────────────────────────────────────

    def _fase_anuncio(self, surf: pygame.Surface, y: int):
        cx = _PW // 2

        # Contexto (texto descritivo da situação)
        if self.contexto:
            linhas = self._quebrar(self.contexto, _PW - 48)
            for linha in linhas:
                s = self._fn_normal.render(linha, True, _C["dim"])
                surf.blit(s, (24, y))
                y += 21
            y += 10

        pygame.draw.line(surf, _C["borda"], (20, y), (_PW - 20, y), 1)
        y += 16

        # Valor da perícia
        if self.eh_san:
            label_v = f"SAN atual:  {self._valor_base}"
        else:
            label_v = f"Valor na perícia:  {self._valor_base}%"
        s = self._fn_normal.render(label_v, True, _C["texto"])
        surf.blit(s, s.get_rect(centerx=cx, y=y))
        y += 30

        # Dificuldade (só para perícias normais)
        if not self.eh_san:
            dif_cor = {
                "normal":  _C["sucesso"],
                "dificil": _C["ouro"],
                "extremo": _C["acento"],
            }.get(self.dificuldade, _C["texto"])
            dif_lbl = {
                "normal":  "Normal",
                "dificil": f"Difícil  (rolar ≤ {self._valor_ef})",
                "extremo": f"Extremo  (rolar ≤ {self._valor_ef})",
            }.get(self.dificuldade, self.dificuldade.capitalize())
            s = self._fn_normal.render(f"Dificuldade:  {dif_lbl}", True, dif_cor)
            surf.blit(s, s.get_rect(centerx=cx, y=y))

        # Rodapé
        pygame.draw.line(surf, _C["borda"],
                         (20, _PH - 38), (_PW - 20, _PH - 38), 1)
        hint = self._fn_small.render(
            "[ ESPAÇO — Rolar dado ]  [ ESC — Rolar automaticamente ]",
            True, _C["dim"])
        surf.blit(hint, hint.get_rect(centerx=cx, y=_PH - 26))

    # ── Fase 2: Rolando ────────────────────────────────────────

    def _fase_rolando(self, surf: pygame.Surface, y: int):
        cx = _PW // 2
        cy = _PH // 2

        # Número grande animado
        s = self._fn_big.render(f"{self._dado_a:02d}", True, _C["ouro"])
        surf.blit(s, s.get_rect(center=(cx, cy)))

        # Alvo abaixo
        s2 = self._fn_small.render(
            f"Rolando 1d100...  alvo ≤ {self._valor_ef}",
            True, _C["dim"])
        surf.blit(s2, s2.get_rect(centerx=cx, y=cy + 44))

    # ── Fase 3: Resultado ──────────────────────────────────────

    def _fase_resultado(self, surf: pygame.Surface, y: int):
        if self._res is None:
            return
        cx = _PW // 2
        r  = self._res

        # Dado e alvo
        s = self._fn_normal.render(
            f"Dado: {r.dado:02d}    Alvo: ≤ {self._valor_ef}",
            True, _C["dim"])
        surf.blit(s, s.get_rect(centerx=cx, y=y))
        y += 32

        # Grau em letras grandes
        s_big = self._fn_big.render(r.label, True, r.cor)
        surf.blit(s_big, s_big.get_rect(centerx=cx, y=y))
        y += s_big.get_height() + 12

        pygame.draw.line(surf, _C["borda"], (20, y), (_PW - 20, y), 1)
        y += 14

        # Texto de consequência narrativa
        txt = self.texto_ok if r.sucesso else self.texto_fail
        if txt:
            cor_txt = _C["verde"] if r.sucesso else _C["acento"]
            for linha in self._quebrar(txt, _PW - 48):
                s = self._fn_normal.render(linha, True, cor_txt)
                surf.blit(s, (24, y))
                y += 21
            y += 6

        # Perda de SAN (exclusivo do teste de sanidade)
        if self.eh_san and self._msg_san:
            cor_san = _C["acento"] if r.san_delta < 0 else _C["sucesso"]
            s = self._fn_normal.render(self._msg_san, True, cor_san)
            surf.blit(s, s.get_rect(centerx=cx, y=y))

        # Rodapé
        pygame.draw.line(surf, _C["borda"],
                         (20, _PH - 38), (_PW - 20, _PH - 38), 1)
        hint = self._fn_small.render("[ ESPAÇO — Continuar ]", True, _C["dim"])
        surf.blit(hint, hint.get_rect(centerx=cx, y=_PH - 26))

    # ── Word-wrap ──────────────────────────────────────────────

    def _quebrar(self, texto: str, max_w: int) -> list[str]:
        palavras     = texto.split()
        linhas: list[str] = []
        atual        = ""
        for p in palavras:
            candidato = (atual + " " + p).strip()
            if self._fn_normal.size(candidato)[0] <= max_w:
                atual = candidato
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas
