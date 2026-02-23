"""
ui/tela_criar_personagem.py — Criação de personagem pygame-nativo (CoC 7e).

Passo 1 — Escolha de ocupação + nome.
Passo 2 — Rolagem de características (3d6×5 / 2d6+6×5).
Passo 3 — Distribuição de pontos de perícia (EDU×4 + INT×2).

.run() retorna Jogador se confirmado, None se Esc no passo 1.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import pygame

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# Adiciona ui/ ao path para importar dados.py e pericias.py
_UI = os.path.dirname(os.path.abspath(__file__))
if _UI not in sys.path:
    sys.path.insert(0, _UI)

import gerenciador_assets as _ga
from dados_coc import (
    rolar_3d6x5, rolar_2d6_mais6_x5,
    calcular_pontos_vida, calcular_pontos_magia,
    calcular_taxa_movimento, calcular_corpo_a_corpo,
)
from pericias import PERICIAS_DISPONIVEIS, calcular_pontos_pericias, base_efetiva


# ══════════════════════════════════════════════════════════════
# OCUPAÇÕES (arquétipos de partida)
# ══════════════════════════════════════════════════════════════

OCUPACOES = [
    {
        "id":    "detetive",
        "nome":  "Detetive Particular",
        "descr": (
            "As ruas de Arkham escondem mais do que crimes comuns.\n"
            "Instinto aguçado e uma .38 são ferramentas de sobrevivência."
        ),
        "bonus_pericias": {
            "Detectar": 40, "Psicologia": 35, "Intimidação": 30,
            "Armas de Fogo (Pistola)": 45, "Furtividade": 25,
        },
        "inventario": ["revolver_38"],
        "arma":  "revolver_38",
        "cor":   (60, 35, 12),
    },
    {
        "id":    "medico",
        "nome":  "Médico",
        "descr": (
            "A ciência explica o mundo... até algo transcender qualquer\n"
            "diagnóstico. Você é o último recurso dos que sobrevivem."
        ),
        "bonus_pericias": {
            "Medicina": 55, "Primeiros Socorros": 45,
            "Ciências Naturais": 35, "Psicologia": 30,
        },
        "inventario": ["kit_medico"],
        "arma":  "",
        "cor":   (15, 60, 55),
    },
    {
        "id":    "arqueologo",
        "nome":  "Arqueólogo",
        "descr": (
            "Civilizações antigas guardam segredos que a humanidade\n"
            "preferia deixar enterrados. Você os desenterrou."
        ),
        "bonus_pericias": {
            "Arqueologia": 55, "História": 40,
            "Escalar": 30, "Ocultismo": 20,
        },
        "inventario": [],
        "arma":  "",
        "cor":   (50, 35, 10),
    },
    {
        "id":    "escritor",
        "nome":  "Escritor / Jornalista",
        "descr": (
            "A verdade está lá fora e você a persegue sem descanso.\n"
            "Algumas verdades, porém, deveriam permanecer ocultas."
        ),
        "bonus_pericias": {
            "Biblioteconomia": 50, "Psicologia": 40,
            "Charme": 35, "Ocultismo": 25,
        },
        "inventario": [],
        "arma":  "",
        "cor":   (30, 25, 60),
    },
    {
        "id":    "soldado",
        "nome":  "Veterano da Grande Guerra",
        "descr": (
            "Sobreviveu às trincheiras da Europa. O horror de Arkham\n"
            "dificilmente pode ser pior... ou pode?"
        ),
        "bonus_pericias": {
            "Lutar (Soco)": 40, "Armas de Fogo (Rifle)": 55,
            "Primeiros Socorros": 25, "Intimidação": 30,
        },
        "inventario": [],
        "arma":  "",
        "cor":   (30, 45, 20),
    },
]


# ══════════════════════════════════════════════════════════════
# CARACTERÍSTICAS CoC 7e
# ══════════════════════════════════════════════════════════════

CARAC_LISTA = [
    # (abrev, chave, formula_label, fn_rolar)
    ("FOR", "forca",        "3d6 × 5",    rolar_3d6x5),
    ("CON", "constituicao", "3d6 × 5",    rolar_3d6x5),
    ("APA", "aparencia",    "3d6 × 5",    rolar_3d6x5),
    ("DES", "destreza",     "3d6 × 5",    rolar_3d6x5),
    ("TAM", "tamanho",      "2d6+6 × 5",  rolar_2d6_mais6_x5),
    ("INT", "inteligencia", "2d6+6 × 5",  rolar_2d6_mais6_x5),
    ("POD", "poder",        "3d6 × 5",    rolar_3d6x5),
    ("EDU", "educacao",     "2d6+6 × 5",  rolar_2d6_mais6_x5),
    ("SOR", "sorte",        "3d6 × 5",    rolar_3d6x5),
]


def _rolar_todas() -> dict:
    return {chave: fn()[0] for _, chave, _, fn in CARAC_LISTA}


def _derivados(c: dict) -> dict:
    pv  = calcular_pontos_vida(c["tamanho"], c["constituicao"])
    pm  = calcular_pontos_magia(c["poder"])
    mov = calcular_taxa_movimento(c["forca"], c["destreza"], c["tamanho"])
    bd, cac = calcular_corpo_a_corpo(c["forca"], c["tamanho"])
    san = c["poder"]
    return {"pv_max": pv, "pm": pm, "sanidade": san,
            "mov": mov, "bonus_dano": bd, "corpo_a_corpo": cac}


def _montar_json(nome: str, ocup: dict, carac: dict,
                 investido: dict[str, int]) -> dict:
    der = _derivados(carac)
    pericias_out: dict[str, int] = {}
    for p in PERICIAS_DISPONIVEIS:
        base = base_efetiva(p, carac)
        inv  = investido.get(p["nome"], 0)
        bonus = ocup["bonus_pericias"].get(p["nome"], 0)
        pericias_out[p["nome"]] = min(99, base + inv + bonus)

    return {
        "dados_pessoais": {
            "nome":       nome,
            "ocupacao":   ocup["nome"],
            "nascimento": "01/01/1895",
            "residencia": "Arkham, MA",
            "idade":      "28 anos",
        },
        "caracteristicas": {**carac, **der},
        "pericias": pericias_out,
        "campanha": {
            "dinheiro":      15,
            "hora":          10,
            "dia":           1,
            "arma_equipada": ocup.get("arma", ""),
            "inventario":    list(ocup.get("inventario", [])),
            "local_id":      "rua_central",
        },
    }


# ══════════════════════════════════════════════════════════════
# TELA
# ══════════════════════════════════════════════════════════════

class TelaCriarPersonagem:
    W, H = 1280, 720

    C_FUNDO  = ( 10,   8,  18)
    C_PAINEL = ( 22,  33,  62)
    C_TEXTO  = (238, 226, 220)
    C_DIM    = (154, 140, 152)
    C_OURO   = (212, 168,  67)
    C_VERDE  = ( 78, 204, 163)
    C_ACENTO = (233,  69,  96)
    C_AZUL   = ( 80, 140, 220)
    C_ROXO   = (107,  45, 139)

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock
        _ga.garantir_fontes(verbose=False)

        self.f_titulo = _ga.get_font("titulo", 28)
        self.f_subtit = _ga.get_font("titulo", 16)
        self.f_normal = _ga.get_font("hud",    14)
        self.f_small  = _ga.get_font("hud",    11)
        self.f_input  = _ga.get_font("titulo", 22)

        self.passo = 1

        # ── Passo 1 ───────────────────────────────────────────
        self.ocup_sel   = 0
        self.nome       = ""
        self.cursor_vis = True
        self._cursor_t  = 0

        cw, ch = 290, 80
        cx, cy0, cg = 36, 136, 8
        self.cards_rects = [
            pygame.Rect(cx, cy0 + i * (ch + cg), cw, ch)
            for i in range(len(OCUPACOES))
        ]
        bot = cy0 + len(OCUPACOES) * (ch + cg) + 16
        self.input_rect = pygame.Rect(cx, bot,            cw, 46)
        self.btn_p1     = pygame.Rect(cx, bot + 46 + 12,  cw, 48)
        self.p1_px = cx + cw + 24
        self.p1_pw = self.W - self.p1_px - 36

        # ── Passo 2 (rolagem) ─────────────────────────────────
        self.carac: dict[str, int] = {}
        self._p2_sel = 0   # linha selecionada (0-8)

        # layout passo 2
        self._p2_lx  = 60
        self._p2_lw  = 480
        self._p2_row = 46
        self._p2_y0  = 148
        self._p2_rx  = 580
        self._p2_rw  = self.W - 580 - 36  # 664

        # botões passo 2
        by = self._p2_y0 + len(CARAC_LISTA) * self._p2_row + 20
        self._btn_rolar_todos = pygame.Rect(self._p2_lx, by, 200, 42)
        self._btn_p2_voltar   = pygame.Rect(self._p2_lx, self.H - 62, 160, 44)
        self._btn_p2_avancar  = pygame.Rect(self.W - 260, self.H - 62, 224, 44)

        # ── Passo 3 (perícias) ────────────────────────────────
        self.pontos_restantes = 0
        self.investido: dict[str, int] = {}
        self._p3_grupos  = self._grupos_pericias()
        self._p3_grupo   = 0          # aba activa
        self._p3_lista: list[dict] = []
        self._p3_scroll  = 0
        self._p3_sel     = 0

        self._p3_row = 28
        self._p3_lx  = 36
        self._p3_lw  = 560
        self._p3_y0  = 148
        self._p3_vis = (self.H - self._p3_y0 - 80) // self._p3_row  # linhas visíveis
        self._p3_rx  = 620
        self._p3_rw  = self.W - 620 - 36

        self._btn_p3_voltar   = pygame.Rect(self._p3_lx, self.H - 62, 160, 44)
        self._btn_p3_confirmar= pygame.Rect(self.W - 280, self.H - 62, 244, 44)

    # ── Grupos de perícias ────────────────────────────────────

    def _grupos_pericias(self) -> list[str]:
        vistos: list[str] = []
        for p in PERICIAS_DISPONIVEIS:
            g = p.get("grupo", "Geral")
            if g not in vistos:
                vistos.append(g)
        return vistos

    def _lista_do_grupo(self, grupo: str) -> list[dict]:
        return [p for p in PERICIAS_DISPONIVEIS if p.get("grupo", "Geral") == grupo]

    # ── Passo 2 helpers ───────────────────────────────────────

    def _init_p2(self):
        """Rola todos os atributos ao entrar no passo 2."""
        self.carac = _rolar_todas()

    def _rolar_linha(self, idx: int):
        _, chave, _, fn = CARAC_LISTA[idx]
        self.carac[chave] = fn()[0]

    def _pontos_totais(self) -> int:
        if not self.carac:
            return 0
        return calcular_pontos_pericias(
            self.carac.get("educacao", 0),
            self.carac.get("inteligencia", 0),
        )

    # ── Passo 3 helpers ───────────────────────────────────────

    def _init_p3(self):
        """Inicializa passo 3 com a lista do grupo activo."""
        self.investido = {}
        self.pontos_restantes = self._pontos_totais()
        self._p3_grupo  = 0
        self._p3_lista  = self._lista_do_grupo(self._p3_grupos[0])
        self._p3_scroll = 0
        self._p3_sel    = 0

    def _trocar_grupo(self, idx: int):
        self._p3_grupo  = idx
        self._p3_lista  = self._lista_do_grupo(self._p3_grupos[idx])
        self._p3_scroll = 0
        self._p3_sel    = 0

    def _base_pericia(self, p: dict) -> int:
        return base_efetiva(p, self.carac)

    def _total_pericia(self, p: dict) -> int:
        base   = self._base_pericia(p)
        inv    = self.investido.get(p["nome"], 0)
        ocup   = OCUPACOES[self.ocup_sel]
        bonus  = ocup["bonus_pericias"].get(p["nome"], 0)
        return min(99, base + inv + bonus)

    def _ajustar_pericia(self, nome: str, delta: int):
        inv = self.investido.get(nome, 0)
        novo = inv + delta
        if delta > 0 and self.pontos_restantes <= 0:
            return
        if delta > 0 and novo > 90:   # teto de investimento
            return
        if delta < 0 and novo < 0:
            return
        diff = novo - inv
        self.pontos_restantes -= diff
        self.investido[nome] = novo

    # ── Confirmar ─────────────────────────────────────────────

    def _confirmar(self) -> Optional[object]:
        nome = self.nome.strip()
        ocup = OCUPACOES[self.ocup_sel]
        dados = _montar_json(nome, ocup, self.carac, self.investido)

        _RAIZ_J = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        path = os.path.join(_RAIZ_J, "investigador.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AVISO] Não salvou investigador.json: {e}")
            return None

        try:
            from dados.investigador_loader import carregar_jogador
            jogador, _ = carregar_jogador()
            return jogador
        except Exception as e:
            print(f"[AVISO] carregar_jogador: {e}")
            return None

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def run(self) -> Optional[object]:
        while True:
            self.clock.tick(60)
            mx, my = pygame.mouse.get_pos()
            events = pygame.event.get()

            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit(); import sys; sys.exit()

            if self.passo == 1:
                sig = self._ev1(events, mx, my)
                if sig == "cancel":
                    return None
                if sig == "proximo":
                    self._init_p2()
                    self.passo = 2
                self._draw1(mx, my)

            elif self.passo == 2:
                sig = self._ev2(events, mx, my)
                if sig == "voltar":
                    self.passo = 1
                if sig == "proximo":
                    self._init_p3()
                    self.passo = 3
                self._draw2(mx, my)

            elif self.passo == 3:
                sig = self._ev3(events, mx, my)
                if sig == "voltar":
                    self.passo = 2
                if sig == "confirmar":
                    jogador = self._confirmar()
                    if jogador:
                        return jogador
                self._draw3(mx, my)

    # ══════════════════════════════════════════════════════════
    # EVENTOS PASSO 1
    # ══════════════════════════════════════════════════════════

    def _ev1(self, events, mx, my) -> str:
        self._cursor_t += self.clock.get_time()
        if self._cursor_t > 500:
            self._cursor_t = 0
            self.cursor_vis = not self.cursor_vis

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return "cancel"
                if ev.key == pygame.K_UP:
                    self.ocup_sel = max(0, self.ocup_sel - 1)
                if ev.key == pygame.K_DOWN:
                    self.ocup_sel = min(len(OCUPACOES) - 1, self.ocup_sel + 1)
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.nome.strip():
                        return "proximo"
                if ev.key == pygame.K_BACKSPACE:
                    self.nome = self.nome[:-1]
                elif ev.unicode and len(self.nome) < 30:
                    self.nome += ev.unicode

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(self.cards_rects):
                    if r.collidepoint(mx, my):
                        self.ocup_sel = i
                if self.btn_p1.collidepoint(mx, my) and self.nome.strip():
                    return "proximo"

        return ""

    # ══════════════════════════════════════════════════════════
    # EVENTOS PASSO 2
    # ══════════════════════════════════════════════════════════

    def _ev2(self, events, mx, my) -> str:
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return "voltar"
                if ev.key == pygame.K_UP:
                    self._p2_sel = max(0, self._p2_sel - 1)
                if ev.key == pygame.K_DOWN:
                    self._p2_sel = min(len(CARAC_LISTA) - 1, self._p2_sel + 1)
                if ev.key == pygame.K_r:
                    self._rolar_linha(self._p2_sel)
                if ev.key == pygame.K_SPACE:
                    self.carac = _rolar_todas()
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.carac:
                        return "proximo"

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._btn_rolar_todos.collidepoint(mx, my):
                    self.carac = _rolar_todas()
                if self._btn_p2_voltar.collidepoint(mx, my):
                    return "voltar"
                if self._btn_p2_avancar.collidepoint(mx, my) and self.carac:
                    return "proximo"
                # Clique em linha individual → rolar aquela característica
                for i in range(len(CARAC_LISTA)):
                    r = self._linha_carac_rect(i)
                    if r.collidepoint(mx, my):
                        self._p2_sel = i
                        self._rolar_linha(i)

        return ""

    def _linha_carac_rect(self, idx: int) -> pygame.Rect:
        return pygame.Rect(
            self._p2_lx, self._p2_y0 + idx * self._p2_row,
            self._p2_lw, self._p2_row - 4,
        )

    # ══════════════════════════════════════════════════════════
    # EVENTOS PASSO 3
    # ══════════════════════════════════════════════════════════

    def _ev3(self, events, mx, my) -> str:
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return "voltar"
                if ev.key == pygame.K_UP:
                    if self._p3_sel > 0:
                        self._p3_sel -= 1
                        if self._p3_sel < self._p3_scroll:
                            self._p3_scroll = self._p3_sel
                if ev.key == pygame.K_DOWN:
                    if self._p3_sel < len(self._p3_lista) - 1:
                        self._p3_sel += 1
                        if self._p3_sel >= self._p3_scroll + self._p3_vis:
                            self._p3_scroll = self._p3_sel - self._p3_vis + 1
                if ev.key == pygame.K_LEFT:
                    if self._p3_lista:
                        self._ajustar_pericia(self._p3_lista[self._p3_sel]["nome"], -5)
                if ev.key == pygame.K_RIGHT:
                    if self._p3_lista:
                        self._ajustar_pericia(self._p3_lista[self._p3_sel]["nome"], +5)
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "confirmar"
                # Teclas 1-6 trocam grupo
                for i in range(min(9, len(self._p3_grupos))):
                    if ev.key == getattr(pygame, f"K_{i+1}", None):
                        self._trocar_grupo(i)

                # Tab avança grupo
                if ev.key == pygame.K_TAB:
                    nxt = (self._p3_grupo + 1) % len(self._p3_grupos)
                    self._trocar_grupo(nxt)

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._btn_p3_voltar.collidepoint(mx, my):
                    return "voltar"
                if self._btn_p3_confirmar.collidepoint(mx, my):
                    return "confirmar"
                # Abas de grupo
                for i, gr in enumerate(self._p3_grupos):
                    r = self._aba_rect(i)
                    if r.collidepoint(mx, my):
                        self._trocar_grupo(i)
                # Clique em linha de perícia
                for vi in range(self._p3_vis):
                    idx = self._p3_scroll + vi
                    if idx >= len(self._p3_lista):
                        break
                    ry = self._p3_y0 + vi * self._p3_row
                    row_r = pygame.Rect(self._p3_lx, ry, self._p3_lw, self._p3_row - 2)
                    if row_r.collidepoint(mx, my):
                        self._p3_sel = idx
                        # btn − e +
                        btn_minus = pygame.Rect(self._p3_lx + self._p3_lw - 70, ry + 4, 28, 20)
                        btn_plus  = pygame.Rect(self._p3_lx + self._p3_lw - 36, ry + 4, 28, 20)
                        nome = self._p3_lista[idx]["nome"]
                        if btn_minus.collidepoint(mx, my):
                            self._ajustar_pericia(nome, -5)
                        elif btn_plus.collidepoint(mx, my):
                            self._ajustar_pericia(nome, +5)

            if ev.type == pygame.MOUSEWHEEL:
                self._p3_scroll = max(
                    0, min(self._p3_scroll - ev.y,
                           max(0, len(self._p3_lista) - self._p3_vis)))

        return ""

    def _aba_rect(self, idx: int) -> pygame.Rect:
        aw = 100
        ax = self._p3_lx + idx * (aw + 4)
        return pygame.Rect(ax, 108, aw, 28)

    # ══════════════════════════════════════════════════════════
    # DESENHO PASSO 1
    # ══════════════════════════════════════════════════════════

    def _draw1(self, mx, my):
        s = self.screen
        s.fill(self.C_FUNDO)

        # Título
        t = self.f_titulo.render("CRIAR INVESTIGADOR  —  Passo 1: Ocupação", True, self.C_OURO)
        s.blit(t, t.get_rect(centerx=self.W // 2, y=22))
        sub = self.f_small.render(
            "[↑↓] escolher  ·  [Enter] avançar  ·  [Esc] cancelar",
            True, self.C_DIM)
        s.blit(sub, sub.get_rect(centerx=self.W // 2, y=64))
        pygame.draw.line(s, (40, 38, 25), (36, 96), (self.W - 36, 96), 1)

        ocup = OCUPACOES[self.ocup_sel]

        for i, ocp in enumerate(OCUPACOES):
            r   = self.cards_rects[i]
            sel = (i == self.ocup_sel)
            hov = r.collidepoint(mx, my)
            base = ocp["cor"]
            bg  = tuple(min(255, c + 60) for c in base) if sel else (
                  tuple(min(255, c + 30) for c in base) if hov else base)
            brd = self.C_OURO if sel else tuple(min(255, c + 40) for c in base)
            pygame.draw.rect(s, bg,  r, border_radius=6)
            pygame.draw.rect(s, brd, r, 2 if sel else 1, border_radius=6)
            if sel:
                pygame.draw.rect(s, self.C_OURO,
                                 pygame.Rect(r.x, r.y, 4, r.h), border_radius=3)
            lbl = self.f_normal.render(ocp["nome"], True,
                                       self.C_OURO if sel else self.C_TEXTO)
            s.blit(lbl, (r.x + 14, r.y + r.h // 2 - lbl.get_height() // 2))

        # Input nome
        ir = self.input_rect
        pygame.draw.rect(s, (30, 28, 50), ir, border_radius=6)
        pygame.draw.rect(s, self.C_OURO if self.nome else self.C_DIM, ir, 1, border_radius=6)
        hint = self.f_small.render("Nome do investigador", True, self.C_DIM)
        s.blit(hint, (ir.x + 10, ir.y + 5))
        txt = self.nome + ("|" if self.cursor_vis else " ")
        inp_s = self.f_input.render(txt, True, self.C_TEXTO)
        s.blit(inp_s, (ir.x + 10, ir.y + 18))

        # Botão próximo
        pode = bool(self.nome.strip())
        br = self.btn_p1
        pygame.draw.rect(s, (50, 90, 50) if pode else (40, 40, 40), br, border_radius=6)
        pygame.draw.rect(s, self.C_VERDE if pode else self.C_DIM, br, 1, border_radius=6)
        bt = self.f_normal.render(
            "PRÓXIMO → ROLAR ATRIBUTOS" if pode else "(insira um nome)",
            True, self.C_VERDE if pode else self.C_DIM)
        s.blit(bt, bt.get_rect(center=br.center))

        # Painel direito — preview da ocupação
        px, py, pw = self.p1_px, 116, self.p1_pw
        pygame.draw.rect(s, (18, 20, 40), pygame.Rect(px, py, pw, self.H - py - 20), border_radius=8)
        pygame.draw.rect(s, (40, 38, 25), pygame.Rect(px, py, pw, self.H - py - 20), 1, border_radius=8)

        cy = py + 16
        t2 = self.f_subtit.render(ocup["nome"].upper(), True, self.C_OURO)
        s.blit(t2, (px + 16, cy)); cy += t2.get_height() + 8
        pygame.draw.line(s, (50, 45, 30), (px + 16, cy), (px + pw - 16, cy), 1)
        cy += 10

        for linha in ocup["descr"].split("\n"):
            d = self.f_small.render(linha, True, self.C_TEXTO)
            s.blit(d, (px + 16, cy)); cy += d.get_height() + 3

        cy += 14
        bonus_lbl = self.f_small.render("BÔNUS DE OCUPAÇÃO:", True, self.C_OURO)
        s.blit(bonus_lbl, (px + 16, cy)); cy += bonus_lbl.get_height() + 6

        for pnome, pval in ocup["bonus_pericias"].items():
            row = self.f_small.render(f"  +{pval:>3}  {pnome}", True, self.C_VERDE)
            s.blit(row, (px + 16, cy)); cy += row.get_height() + 2

        pygame.display.flip()

    # ══════════════════════════════════════════════════════════
    # DESENHO PASSO 2
    # ══════════════════════════════════════════════════════════

    def _draw2(self, mx, my):
        s = self.screen
        s.fill(self.C_FUNDO)

        # Título
        t = self.f_titulo.render("CRIAR INVESTIGADOR  —  Passo 2: Características", True, self.C_OURO)
        s.blit(t, t.get_rect(centerx=self.W // 2, y=22))
        sub = self.f_small.render(
            "[↑↓] selecionar  ·  [R] rolar linha  ·  [Espaço] rolar tudo  ·  [Enter] avançar",
            True, self.C_DIM)
        s.blit(sub, sub.get_rect(centerx=self.W // 2, y=64))
        pygame.draw.line(s, (40, 38, 25), (36, 96), (self.W - 36, 96), 1)

        # Cabeçalho da tabela
        hx, hy = self._p2_lx, self._p2_y0 - 28
        self._col_texto(s, "CARACTERÍSTICA", hx + 10, hy, self.C_DIM)
        self._col_texto(s, "FÓRMULA",        hx + 175, hy, self.C_DIM)
        self._col_texto(s, "VALOR",          hx + 290, hy, self.C_DIM)
        self._col_texto(s, "METADE",         hx + 350, hy, self.C_DIM)
        self._col_texto(s, "QUINTO",         hx + 420, hy, self.C_DIM)

        for i, (abrev, chave, formula, _) in enumerate(CARAC_LISTA):
            r   = self._linha_carac_rect(i)
            sel = (i == self._p2_sel)
            hov = r.collidepoint(mx, my)
            bg  = (35, 45, 80) if sel else ((25, 32, 55) if hov else (18, 22, 40))
            brd = self.C_OURO if sel else (self.C_AZUL if hov else (30, 35, 55))
            pygame.draw.rect(s, bg,  r, border_radius=4)
            pygame.draw.rect(s, brd, r, 1, border_radius=4)

            val  = self.carac.get(chave, 0)
            cor_v = self.C_VERDE if val else self.C_DIM
            ry = r.y + (r.h - self.f_small.get_height()) // 2

            nome_completo = {
                "forca": "FOR — Força", "constituicao": "CON — Constituição",
                "aparencia": "APA — Aparência", "destreza": "DES — Destreza",
                "tamanho": "TAM — Tamanho", "inteligencia": "INT — Inteligência",
                "poder": "POD — Poder", "educacao": "EDU — Educação",
                "sorte": "SOR — Sorte",
            }
            self._col_texto(s, nome_completo[chave], r.x + 10, ry,
                            self.C_OURO if sel else self.C_TEXTO)
            self._col_texto(s, formula, r.x + 175, ry, self.C_DIM)
            if val:
                self._col_texto(s, str(val),        r.x + 290, ry, cor_v)
                self._col_texto(s, str(val // 2),   r.x + 350, ry, self.C_DIM)
                self._col_texto(s, str(val // 5) if chave != "sorte" else "—",
                                r.x + 420, ry, self.C_DIM)
            else:
                self._col_texto(s, "—", r.x + 290, ry, self.C_DIM)

            if sel:
                tip = self.f_small.render("[R] rolar", True, self.C_AZUL)
                s.blit(tip, (r.x + self._p2_lw - tip.get_width() - 8, ry))

        # Botão rolar todos
        br = self._btn_rolar_todos
        hov = br.collidepoint(mx, my)
        pygame.draw.rect(s, (40, 60, 100) if hov else (28, 42, 70), br, border_radius=6)
        pygame.draw.rect(s, self.C_AZUL, br, 1, border_radius=6)
        bl = self.f_normal.render("⟳  Rolar Todos  [Espaço]", True, self.C_TEXTO)
        s.blit(bl, bl.get_rect(center=br.center))

        # Painel direito — derivados
        if self.carac:
            der = _derivados(self.carac)
            px, py2 = self._p2_rx, 108
            ph = self.H - py2 - 20
            pygame.draw.rect(s, (18, 22, 40), pygame.Rect(px, py2, self._p2_rw, ph), border_radius=8)
            pygame.draw.rect(s, (40, 38, 25), pygame.Rect(px, py2, self._p2_rw, ph), 1, border_radius=8)

            cy = py2 + 14
            lbl_der = self.f_subtit.render("DERIVADOS", True, self.C_OURO)
            s.blit(lbl_der, (px + 16, cy)); cy += lbl_der.get_height() + 10

            DERIVADOS_LABELS = [
                ("Pontos de Vida",    str(der["pv_max"])),
                ("Pontos de Magia",   str(der["pm"])),
                ("Sanidade Inicial",  str(der["sanidade"])),
                ("Taxa de Movimento", str(der["mov"])),
                ("Bônus de Dano",     der["bonus_dano"]),
                ("Corpo-a-corpo",     der["corpo_a_corpo"]),
            ]
            for lbl, val2 in DERIVADOS_LABELS:
                ls = self.f_small.render(lbl, True, self.C_DIM)
                vs = self.f_normal.render(val2, True, self.C_VERDE)
                s.blit(ls, (px + 16, cy))
                s.blit(vs, (px + self._p2_rw - vs.get_width() - 16, cy))
                cy += max(ls.get_height(), vs.get_height()) + 6

            cy += 14
            pygame.draw.line(s, (50, 45, 30), (px + 16, cy), (px + self._p2_rw - 16, cy), 1)
            cy += 12

            # Pontos de perícia
            total = self._pontos_totais()
            pt_lbl = self.f_small.render("Pontos de perícia (EDU×4 + INT×2):", True, self.C_DIM)
            pt_val = self.f_subtit.render(str(total), True, self.C_OURO)
            s.blit(pt_lbl, (px + 16, cy)); cy += pt_lbl.get_height() + 4
            s.blit(pt_val, (px + 16, cy))

        # Botões nav
        self._draw_btn(s, self._btn_p2_voltar,  "← Voltar",  self.C_DIM,    mx, my)
        ok = bool(self.carac)
        self._draw_btn(s, self._btn_p2_avancar,
                       "PRÓXIMO → PERÍCIAS" if ok else "(role os atributos)",
                       self.C_VERDE if ok else self.C_DIM, mx, my)

        pygame.display.flip()

    # ══════════════════════════════════════════════════════════
    # DESENHO PASSO 3
    # ══════════════════════════════════════════════════════════

    def _draw3(self, mx, my):
        s = self.screen
        s.fill(self.C_FUNDO)

        total = self._pontos_totais()
        cor_pts = (
            self.C_VERDE  if self.pontos_restantes == 0 else
            self.C_ACENTO if self.pontos_restantes < 0  else
            self.C_OURO
        )

        # Título
        t = self.f_titulo.render("CRIAR INVESTIGADOR  —  Passo 3: Perícias", True, self.C_OURO)
        s.blit(t, t.get_rect(centerx=self.W // 2, y=18))
        pts_s = self.f_normal.render(
            f"Pontos: {self.pontos_restantes} / {total}  "
            f"({'OK' if self.pontos_restantes >= 0 else 'EXCEDIDO!'})",
            True, cor_pts)
        s.blit(pts_s, pts_s.get_rect(centerx=self.W // 2, y=56))
        pygame.draw.line(s, (40, 38, 25), (36, 88), (self.W - 36, 88), 1)

        # Abas de grupo
        for i, gr in enumerate(self._p3_grupos):
            ar = self._aba_rect(i)
            sel = (i == self._p3_grupo)
            pygame.draw.rect(s, (35, 45, 80) if sel else (20, 25, 45), ar, border_radius=4)
            pygame.draw.rect(s, self.C_OURO if sel else (40, 40, 60), ar, 1, border_radius=4)
            ls = self.f_small.render(gr, True, self.C_OURO if sel else self.C_DIM)
            s.blit(ls, ls.get_rect(center=ar.center))

        sub = self.f_small.render(
            "[↑↓] navegar  ·  [←→] -5/+5  ·  [Tab] próximo grupo  ·  [1-6] grupo  ·  [Enter] confirmar",
            True, self.C_DIM)
        s.blit(sub, sub.get_rect(x=self._p3_lx, y=140))

        # Lista de perícias (scroll)
        ocup = OCUPACOES[self.ocup_sel]
        for vi in range(self._p3_vis):
            idx = self._p3_scroll + vi
            if idx >= len(self._p3_lista):
                break
            p    = self._p3_lista[idx]
            nome = p["nome"]
            base  = self._base_pericia(p)
            inv   = self.investido.get(nome, 0)
            bonus = ocup["bonus_pericias"].get(nome, 0)
            tot   = self._total_pericia(p)
            sel   = (idx == self._p3_sel)

            ry = self._p3_y0 + vi * self._p3_row
            rr = pygame.Rect(self._p3_lx, ry, self._p3_lw, self._p3_row - 2)
            bg = (35, 45, 80) if sel else (22, 26, 44)
            pygame.draw.rect(s, bg, rr, border_radius=3)
            if sel:
                pygame.draw.rect(s, self.C_OURO, rr, 1, border_radius=3)

            # Nome
            cor_n = self.C_OURO if bonus > 0 else (self.C_TEXTO if inv > 0 else self.C_DIM)
            ns = self.f_small.render(nome, True, cor_n if sel else cor_n)
            s.blit(ns, (self._p3_lx + 8, ry + 7))

            # Base
            bs_s = self.f_small.render(str(base), True, self.C_DIM)
            s.blit(bs_s, (self._p3_lx + 230, ry + 7))

            # Investido
            inv_s = self.f_small.render(
                f"+{inv}" if inv > 0 else "—", True,
                self.C_AZUL if inv > 0 else self.C_DIM)
            s.blit(inv_s, (self._p3_lx + 280, ry + 7))

            # Bonus ocupação
            if bonus > 0:
                bon_s = self.f_small.render(f"+{bonus}✦", True, self.C_VERDE)
                s.blit(bon_s, (self._p3_lx + 330, ry + 7))

            # Total
            tot_s = self.f_normal.render(f"{tot}%", True, self.C_VERDE if tot > base else self.C_TEXTO)
            s.blit(tot_s, (self._p3_lx + 395, ry + 5))

            # Botões − +
            btn_m = pygame.Rect(self._p3_lx + self._p3_lw - 70, ry + 4, 28, 20)
            btn_p = pygame.Rect(self._p3_lx + self._p3_lw - 36, ry + 4, 28, 20)
            for brect, lbl in ((btn_m, "−"), (btn_p, "+")):
                hov = brect.collidepoint(mx, my)
                pygame.draw.rect(s, (50, 60, 90) if hov else (30, 36, 60), brect, border_radius=3)
                pygame.draw.rect(s, self.C_DIM, brect, 1, border_radius=3)
                ls2 = self.f_small.render(lbl, True, self.C_TEXTO)
                s.blit(ls2, ls2.get_rect(center=brect.center))

        # Scrollbar
        total_p = len(self._p3_lista)
        if total_p > self._p3_vis:
            sb_h = (self.H - self._p3_y0 - 80)
            th   = max(20, sb_h * self._p3_vis // total_p)
            ty   = self._p3_y0 + sb_h * self._p3_scroll // total_p
            pygame.draw.rect(s, (30, 35, 55),
                             pygame.Rect(self._p3_lx + self._p3_lw + 4, self._p3_y0, 6, sb_h))
            pygame.draw.rect(s, self.C_DIM,
                             pygame.Rect(self._p3_lx + self._p3_lw + 4, ty, 6, th),
                             border_radius=3)

        # Painel direito — resumo da ficha
        self._draw_preview(s, mx, my)

        # Botões nav
        self._draw_btn(s, self._btn_p3_voltar, "← Voltar", self.C_DIM, mx, my)
        self._draw_btn(s, self._btn_p3_confirmar,
                       "▶ CONFIRMAR INVESTIGADOR", self.C_VERDE, mx, my)

        pygame.display.flip()

    def _draw_preview(self, s, mx, my):
        """Painel direito do passo 3 — características + perícias boosted."""
        px, py, pw = self._p3_rx, 100, self._p3_rw
        ph = self.H - py - 20
        pygame.draw.rect(s, (14, 17, 34), pygame.Rect(px, py, pw, ph), border_radius=8)
        pygame.draw.rect(s, (40, 38, 25), pygame.Rect(px, py, pw, ph), 1, border_radius=8)

        cy = py + 12
        tit = self.f_subtit.render(
            f"{self.nome.strip() or '???'}  —  {OCUPACOES[self.ocup_sel]['nome']}",
            True, self.C_OURO)
        s.blit(tit, tit.get_rect(centerx=px + pw // 2, y=cy)); cy += tit.get_height() + 8

        pygame.draw.line(s, (50, 45, 30), (px + 12, cy), (px + pw - 12, cy), 1); cy += 8

        # Atributos em 3 colunas
        pares = [
            ("FOR", self.carac.get("forca", 0)),
            ("CON", self.carac.get("constituicao", 0)),
            ("APA", self.carac.get("aparencia", 0)),
            ("DES", self.carac.get("destreza", 0)),
            ("TAM", self.carac.get("tamanho", 0)),
            ("INT", self.carac.get("inteligencia", 0)),
            ("POD", self.carac.get("poder", 0)),
            ("EDU", self.carac.get("educacao", 0)),
            ("SOR", self.carac.get("sorte", 0)),
        ]
        col_w = pw // 3
        for i, (ab, vl) in enumerate(pares):
            cx2 = px + 12 + (i % 3) * col_w
            ry  = cy + (i // 3) * 22
            ls = self.f_small.render(f"{ab}: {vl}", True,
                                     self.C_VERDE if vl else self.C_DIM)
            s.blit(ls, (cx2, ry))
        cy += 3 * 22 + 10

        # Derivados
        if self.carac:
            der = _derivados(self.carac)
            der_line = (f"PV:{der['pv_max']}  PM:{der['pm']}  "
                        f"SAN:{der['sanidade']}  MOV:{der['mov']}")
            dl = self.f_small.render(der_line, True, self.C_DIM)
            s.blit(dl, dl.get_rect(centerx=px + pw // 2, y=cy)); cy += dl.get_height() + 8

        pygame.draw.line(s, (50, 45, 30), (px + 12, cy), (px + pw - 12, cy), 1); cy += 8

        # Perícias com investimento
        lbl2 = self.f_small.render("PERÍCIAS COM PONTOS INVESTIDOS:", True, self.C_DIM)
        s.blit(lbl2, (px + 12, cy)); cy += lbl2.get_height() + 4

        for p in PERICIAS_DISPONIVEIS:
            if cy > self.H - 80:
                break
            nome = p["nome"]
            inv  = self.investido.get(nome, 0)
            base = self._base_pericia(p)
            bonus = OCUPACOES[self.ocup_sel]["bonus_pericias"].get(nome, 0)
            if inv == 0 and bonus == 0:
                continue
            tot = min(99, base + inv + bonus)
            cor = self.C_OURO if bonus > 0 else self.C_AZUL
            ls  = self.f_small.render(
                f"  {nome[:24]:<24}  {tot}%", True, cor)
            s.blit(ls, (px + 12, cy)); cy += ls.get_height() + 2

    # ── Helpers de desenho ────────────────────────────────────

    def _col_texto(self, s, txt, x, y, cor):
        ls = self.f_small.render(txt, True, cor)
        s.blit(ls, (x, y))

    def _draw_btn(self, s, r, txt, cor, mx, my):
        hov = r.collidepoint(mx, my)
        pygame.draw.rect(s, (40, 60, 40) if hov else (22, 32, 22), r, border_radius=6)
        pygame.draw.rect(s, cor, r, 1, border_radius=6)
        ls = self.f_normal.render(txt, True, cor)
        s.blit(ls, ls.get_rect(center=r.center))
