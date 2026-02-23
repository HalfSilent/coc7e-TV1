"""
ui/tela_inventario.py — Tela de inventário (overlay fullscreen).

Aberta com [I] durante exploração ou combate.

Layout:
    ┌──────────────────────────────────────────────────┐
    │  [ INVENTÁRIO ]  ● Itens  ● Pistas  ● Dinheiro   │
    ├────────────────────────┬─────────────────────────┤
    │                        │  DETALHES                │
    │   GRADE DE ITENS       │  Nome / Tipo             │
    │   (6 colunas)          │  Descrição               │
    │                        │  Stats                   │
    │                        │─────────────────────────│
    │                        │  [U] Usar / [E] Equipar  │
    │                        │  [D] Descartar           │
    ├────────────────────────┴─────────────────────────┤
    │  Arma equipada: [   ]   Peso: X.X / Y.Y kg       │
    │  [I / ESC] Fechar                                 │
    └──────────────────────────────────────────────────┘

Controles:
    ←↑↓→ / WASD   navegar na grade
    [U]            usar item selecionado (consumíveis)
    [E]            equipar arma selecionada
    [D]            descartar item
    [1][2][3]      trocar aba (Itens / Pistas / Dinheiro)
    [I] / [ESC]    fechar
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List, Optional, Tuple

import pygame

from engine.inventario import Inventario, Item, TipoItem
from gerenciador_assets import get_font, garantir_fontes

if TYPE_CHECKING:
    from engine.entidade import Jogador


# ══════════════════════════════════════════════════════════════
# PALETA
# ══════════════════════════════════════════════════════════════

COR_BG          = (10,  10,  18)
COR_PAINEL      = (18,  16,  28)
COR_BORDA       = (80,  70,  50)
COR_BORDA_ATIVA = (180, 150, 80)
COR_SLOT_BG     = (28,  26,  40)
COR_SLOT_HOVER  = (50,  45,  65)
COR_SLOT_ATIVO  = (70,  60,  90)
COR_EQUIPADO    = (30,  60,  30)

COR_TITULO      = (212, 180, 100)
COR_NORMAL      = (180, 175, 165)
COR_DIMM        = (100, 95,  85)
COR_DESTAQUE    = (220, 200, 140)
COR_CUSTO_SAN   = (160, 80,  220)
COR_AVISO       = (220, 120, 60)

COR_TIPO = {
    TipoItem.ARMA:       (220, 80,   60),
    TipoItem.CONSUMIVEL: (80,  200,  80),
    TipoItem.PISTA:      (80,  160,  220),
    TipoItem.TOME:       (180, 80,   220),
    TipoItem.MISC:       (150, 150,  150),
}

LABEL_TIPO = {
    TipoItem.ARMA:       "ARMA",
    TipoItem.CONSUMIVEL: "CONSUMÍVEL",
    TipoItem.PISTA:      "PISTA",
    TipoItem.TOME:       "TOMO",
    TipoItem.MISC:       "MISC",
}


# ══════════════════════════════════════════════════════════════
# ABA
# ══════════════════════════════════════════════════════════════

ABAS = ["Itens", "Pistas", "Dinheiro"]
ABA_TIPOS = {
    "Itens":    [TipoItem.ARMA, TipoItem.CONSUMIVEL, TipoItem.MISC, TipoItem.TOME],
    "Pistas":   [TipoItem.PISTA],
    "Dinheiro": [],
}


# ══════════════════════════════════════════════════════════════
# TELA
# ══════════════════════════════════════════════════════════════

class TelaInventario:
    """
    Overlay de inventário. Renderiza sobre o frame atual da tela,
    não apaga o background (chame-a depois de desenhar a cena).

    Uso:
        tela_inv = TelaInventario(screen, jogador)
        resultado = tela_inv.run()   # "fechou" ou "usou:<item_id>"
    """

    COLUNAS  = 6    # colunas da grade de slots
    SLOT_SZ  = 52   # pixels por slot (quadrado)
    SLOT_PAD = 4    # padding entre slots

    def __init__(self, screen: pygame.Surface, jogador: "Jogador"):
        self.screen  = screen
        self.jogador = jogador
        self.inv:    Inventario = getattr(jogador, "inventario", Inventario())
        self.clock   = pygame.time.Clock()

        garantir_fontes()
        self.f_titulo  = get_font("titulo", 22)
        self.f_normal  = get_font("hud", 16)
        self.f_small   = get_font("hud", 13)
        self.f_grande  = get_font("titulo", 28)

        # Estado de navegação
        self.aba_atual: int = 0         # 0=Itens  1=Pistas  2=Dinheiro
        self.sel_idx:   int = 0         # índice do item selecionado na lista atual

        # Feedback
        self.msg: str  = ""
        self.msg_timer: int = 0

        # Layout (calculado em _layout())
        w, h = screen.get_size()
        self.w, self.h = w, h

    # ══════════════════════════════════════════════════════════
    # LOOP
    # ══════════════════════════════════════════════════════════

    def run(self) -> str:
        """Abre o overlay. Retorna 'fechou' ou 'usou:<item_id>'."""
        while True:
            self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                resultado = self._processar_evento(event)
                if resultado:
                    return resultado

            self._renderizar()

    # ══════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════

    def _processar_evento(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None

        key = event.key

        # Fechar
        if key in (pygame.K_i, pygame.K_ESCAPE):
            return "fechou"

        # Trocar aba
        if key == pygame.K_1: self.aba_atual = 0; self.sel_idx = 0
        if key == pygame.K_2: self.aba_atual = 1; self.sel_idx = 0
        if key == pygame.K_3: self.aba_atual = 2; self.sel_idx = 0

        lista = self._lista_atual()

        # Navegar
        if key in (pygame.K_DOWN, pygame.K_s):
            self.sel_idx = min(self.sel_idx + 1, max(0, len(lista) - 1))
        if key in (pygame.K_UP, pygame.K_w):
            self.sel_idx = max(self.sel_idx - 1, 0)
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.sel_idx = min(self.sel_idx + self.COLUNAS,
                               max(0, len(lista) - 1))
        if key in (pygame.K_LEFT, pygame.K_a):
            self.sel_idx = max(self.sel_idx - self.COLUNAS, 0)

        if not lista or self.sel_idx >= len(lista):
            return None

        item = lista[self.sel_idx]

        # Ações
        if key == pygame.K_u:
            ok, msg = self.inv.usar(item.id, self.jogador)
            self._set_msg(msg if ok else f"[!] {msg}")
            if ok:
                # Ajusta índice se item foi consumido
                nova_lista = self._lista_atual()
                self.sel_idx = min(self.sel_idx, max(0, len(nova_lista) - 1))
                return f"usou:{item.id}"

        if key == pygame.K_e:
            ok, msg = self.inv.equipar(item.id)
            self._set_msg(msg if ok else f"[!] {msg}")

        if key == pygame.K_f:   # [F] = descartar (D já é movimento)
            ok, msg = self.inv.descartar(item.id)
            self._set_msg(msg if ok else f"[!] {msg}")
            if ok:
                nova_lista = self._lista_atual()
                self.sel_idx = min(self.sel_idx, max(0, len(nova_lista) - 1))

        return None

    # ══════════════════════════════════════════════════════════
    # DADOS
    # ══════════════════════════════════════════════════════════

    def _lista_atual(self) -> List[Item]:
        nome_aba = ABAS[self.aba_atual]
        tipos = ABA_TIPOS[nome_aba]
        if not tipos:
            return []
        return [i for i in self.inv.itens if i.tipo in tipos]

    def _set_msg(self, texto: str, frames: int = 180):
        self.msg       = texto
        self.msg_timer = frames

    # ══════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self):
        # Overlay escuro sobre o jogo
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 8, 210))
        self.screen.blit(overlay, (0, 0))

        # Painel principal
        PAD   = 30
        pw    = self.w - PAD * 2
        ph    = self.h - PAD * 2
        px    = PAD
        py    = PAD

        painel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        painel.fill((*COR_PAINEL, 245))
        pygame.draw.rect(painel, COR_BORDA, (0, 0, pw, ph), 2, border_radius=6)
        self.screen.blit(painel, (px, py))

        cy = py + 12

        # ── Título ───────────────────────────────────────────
        tit = self.f_grande.render("INVENTÁRIO", True, COR_TITULO)
        self.screen.blit(tit, tit.get_rect(centerx=self.w // 2, top=cy))
        cy += tit.get_height() + 8

        # ── Abas ─────────────────────────────────────────────
        aba_w = 130
        aba_total = aba_w * len(ABAS) + 8 * (len(ABAS) - 1)
        ax = (self.w - aba_total) // 2
        for i, nome in enumerate(ABAS):
            ativo = (i == self.aba_atual)
            bg    = COR_SLOT_ATIVO if ativo else COR_SLOT_BG
            borda = COR_BORDA_ATIVA if ativo else COR_BORDA
            pygame.draw.rect(self.screen, bg,
                             (ax, cy, aba_w, 28), border_radius=4)
            pygame.draw.rect(self.screen, borda,
                             (ax, cy, aba_w, 28), 2, border_radius=4)
            txt = self.f_normal.render(f"[{i+1}] {nome}", True,
                                       COR_DESTAQUE if ativo else COR_DIMM)
            self.screen.blit(txt, txt.get_rect(centerx=ax + aba_w // 2,
                                                centery=cy + 14))
            ax += aba_w + 8
        cy += 36

        # ── Conteúdo da aba ──────────────────────────────────
        lista = self._lista_atual()

        nome_aba = ABAS[self.aba_atual]
        if nome_aba == "Dinheiro":
            self._desenhar_aba_dinheiro(px + 20, cy, pw - 40)
        elif nome_aba == "Pistas":
            self._desenhar_aba_pistas(px + 20, cy, pw - 40, lista)
        else:
            # Divide em grade esquerda + painel direito
            grade_w = self.COLUNAS * (self.SLOT_SZ + self.SLOT_PAD)
            det_x   = px + grade_w + 30
            det_w   = pw - grade_w - 50
            self._desenhar_grade(px + 20, cy, lista)
            if lista and self.sel_idx < len(lista):
                self._desenhar_detalhes(det_x, cy, det_w,
                                        lista[self.sel_idx])

        # ── Barra de status (rodapé) ──────────────────────────
        rodape_y = py + ph - 48
        pygame.draw.line(self.screen, COR_BORDA,
                         (px + 10, rodape_y), (px + pw - 10, rodape_y), 1)

        arma_txt = (f"Arma: {self.inv.arma_nome}"
                    if self.inv.arma_equipada else "Arma: —")
        peso_txt = (f"Peso: {self.inv.peso_total:.1f}/{self.inv.capacidade:.0f} kg"
                    + (" [!] SOBRECARREGADO" if self.inv.sobrecarregado else ""))
        controles = "[U] Usar  [E] Equipar  [F] Descartar  [I/ESC] Fechar"

        cor_peso = COR_AVISO if self.inv.sobrecarregado else COR_DIMM
        for texto, cor, aln in [
            (arma_txt,    COR_NORMAL, px + 20),
            (peso_txt,    cor_peso,   self.w // 2 - 80),
        ]:
            s = self.f_normal.render(texto, True, cor)
            self.screen.blit(s, (aln, rodape_y + 8))

        ctrl_s = self.f_small.render(controles, True, COR_DIMM)
        self.screen.blit(ctrl_s,
                         ctrl_s.get_rect(centerx=self.w // 2,
                                         bottom=py + ph - 6))

        # ── Mensagem de feedback ─────────────────────────────
        if self.msg_timer > 0:
            self.msg_timer -= 1
            alpha = min(255, self.msg_timer * 4)
            cor_msg = COR_AVISO if "[!]" in self.msg else COR_DESTAQUE
            ms = self.f_normal.render(self.msg, True, cor_msg)
            ms.set_alpha(alpha)
            self.screen.blit(ms, ms.get_rect(centerx=self.w // 2,
                                              bottom=rodape_y - 4))

        pygame.display.flip()

    # ── Grade de slots ────────────────────────────────────────

    def _desenhar_grade(self, x: int, y: int, lista: List[Item]):
        """Renderiza grade de slots de inventário."""
        sz  = self.SLOT_SZ
        pad = self.SLOT_PAD

        if not lista:
            vazio = self.f_normal.render("(vazio)", True, COR_DIMM)
            self.screen.blit(vazio, (x, y + 20))
            return

        for idx, item in enumerate(lista):
            col = idx % self.COLUNAS
            row = idx // self.COLUNAS
            sx  = x + col * (sz + pad)
            sy  = y + row * (sz + pad)

            # Fundo do slot
            ativo    = (idx == self.sel_idx)
            equipado = (item is self.inv.arma_equipada)
            bg = COR_EQUIPADO if equipado else (COR_SLOT_ATIVO if ativo else COR_SLOT_BG)
            pygame.draw.rect(self.screen, bg, (sx, sy, sz, sz), border_radius=4)
            borda = COR_BORDA_ATIVA if ativo else COR_BORDA
            pygame.draw.rect(self.screen, borda,
                             (sx, sy, sz, sz), 2, border_radius=4)

            # Ícone de cor por tipo (fallback visual)
            cor_tipo = COR_TIPO.get(item.tipo, COR_DIMM)
            dot_r = sz // 6
            pygame.draw.circle(self.screen, cor_tipo,
                               (sx + sz - dot_r - 4, sy + dot_r + 4), dot_r)

            # Inicial do nome (ícone textual até ter sprites)
            inicial = item.nome[0].upper()
            si = self.f_titulo.render(inicial, True, COR_NORMAL)
            self.screen.blit(si, si.get_rect(center=(sx + sz // 2, sy + sz // 2 - 4)))

            # Quantidade (se empilhável > 1)
            if item.empilhavel and item.quantidade > 1:
                qt = self.f_small.render(str(item.quantidade), True, COR_DESTAQUE)
                self.screen.blit(qt, (sx + sz - qt.get_width() - 3,
                                      sy + sz - qt.get_height() - 1))

    # ── Painel de detalhes ────────────────────────────────────

    def _desenhar_detalhes(self, x: int, y: int, w: int, item: Item):
        """Painel direito com informações do item selecionado."""
        cy = y

        # Nome
        nome_s = self.f_titulo.render(item.nome, True, COR_TITULO)
        self.screen.blit(nome_s, (x, cy))
        cy += nome_s.get_height() + 4

        # Tag de tipo colorida
        cor_tipo  = COR_TIPO.get(item.tipo, COR_DIMM)
        label_str = LABEL_TIPO.get(item.tipo, "")
        tag_s     = self.f_small.render(f"[ {label_str} ]", True, cor_tipo)
        self.screen.blit(tag_s, (x, cy))
        cy += tag_s.get_height() + 10

        # Stats principais
        stats_desc = item.descricao_curta
        if stats_desc:
            st = self.f_normal.render(stats_desc, True, COR_DESTAQUE)
            self.screen.blit(st, (x, cy))
            cy += st.get_height() + 10

        # Linha separadora
        pygame.draw.line(self.screen, COR_BORDA,
                         (x, cy), (x + w, cy), 1)
        cy += 8

        # Descrição (quebra de linha)
        import textwrap
        max_chars = max(1, w // 9)
        for linha in textwrap.wrap(item.descricao, max_chars):
            ds = self.f_small.render(linha, True, COR_NORMAL)
            self.screen.blit(ds, (x, cy))
            cy += ds.get_height() + 2
        cy += 10

        # Stats específicos por tipo
        if item.tipo == TipoItem.ARMA:
            for label, val in [
                ("Perícia",  item.pericia),
                ("Dano",     item.dano),
                ("Alcance",  item.alcance),
                ("Munição",  f"{item.tiros_restantes}/{item.tiros}" if item.tiros else "—"),
                ("Peso",     f"{item.peso:.1f} kg"),
                ("Valor",    f"${item.valor:.2f}"),
            ]:
                if val:
                    s = self.f_small.render(f"{label}: {val}", True, COR_DIMM)
                    self.screen.blit(s, (x, cy))
                    cy += s.get_height() + 2

            cy += 12
            eq_cor = (COR_EQUIPADO[0] + 100, 200, COR_EQUIPADO[2] + 80)
            if item is self.inv.arma_equipada:
                eq_s = self.f_normal.render("★ EQUIPADA", True, (80, 220, 80))
                self.screen.blit(eq_s, (x, cy)); cy += eq_s.get_height() + 4
                hint = self.f_small.render("[E] Desequipar", True, COR_DIMM)
            else:
                hint = self.f_small.render("[E] Equipar", True, COR_DESTAQUE)
            self.screen.blit(hint, (x, cy))

        elif item.tipo == TipoItem.CONSUMIVEL:
            for label, val in [
                ("Cura HP",  item.cura_hp or "—"),
                ("Cura SAN", str(item.cura_san) if item.cura_san else "—"),
                ("Qtd",      str(item.quantidade) if item.empilhavel else "1"),
                ("Peso",     f"{item.peso:.1f} kg"),
                ("Valor",    f"${item.valor:.2f}"),
            ]:
                s = self.f_small.render(f"{label}: {val}", True, COR_DIMM)
                self.screen.blit(s, (x, cy)); cy += s.get_height() + 2

            cy += 12
            hint = self.f_small.render("[U] Usar agora", True, COR_DESTAQUE)
            self.screen.blit(hint, (x, cy))

        elif item.tipo == TipoItem.TOME:
            for label, val in [
                ("Idioma",       item.idioma or "—"),
                ("Estudo",       f"{item.tempo_estudo} semanas"),
                ("Custo SAN",    f"-{item.custo_san}"),
                ("Ganho Mitos",  f"+{item.ganho_mitos}"),
                ("Magias",       ", ".join(item.magias) or "—"),
            ]:
                cor = COR_CUSTO_SAN if "SAN" in label else COR_DIMM
                s = self.f_small.render(f"{label}: {val}", True, cor)
                self.screen.blit(s, (x, cy)); cy += s.get_height() + 2

        cy += 16
        # Descartar
        df = self.f_small.render("[F] Descartar", True, (200, 80, 60))
        self.screen.blit(df, (x, cy))

    # ── Aba Pistas ────────────────────────────────────────────

    def _desenhar_aba_pistas(self, x: int, y: int, w: int, lista: List[Item]):
        """Lista rolável de pistas — ênfase em leitura/narrativa."""
        cy = y

        if not lista:
            s = self.f_normal.render("Nenhuma pista encontrada ainda.", True, COR_DIMM)
            self.screen.blit(s, (x, cy))
            return

        import textwrap
        max_chars = max(1, w // 9)

        for idx, item in enumerate(lista):
            ativo = (idx == self.sel_idx)
            bg    = COR_SLOT_ATIVO if ativo else COR_SLOT_BG

            # Estima altura do bloco
            wrapped = textwrap.wrap(item.descricao, max_chars)
            bh = 20 + len(wrapped) * 16 + 12

            pygame.draw.rect(self.screen, bg,
                             (x - 4, cy - 2, w + 8, bh), border_radius=4)
            if ativo:
                pygame.draw.rect(self.screen, COR_BORDA_ATIVA,
                                 (x - 4, cy - 2, w + 8, bh), 2, border_radius=4)

            nome_s = self.f_normal.render(item.nome, True, COR_TITULO)
            self.screen.blit(nome_s, (x, cy))
            cy += nome_s.get_height() + 2

            for linha in wrapped:
                ds = self.f_small.render(linha, True, COR_NORMAL)
                self.screen.blit(ds, (x + 10, cy))
                cy += ds.get_height() + 1

            cy += 10

    # ── Aba Dinheiro ──────────────────────────────────────────

    def _desenhar_aba_dinheiro(self, x: int, y: int, w: int):
        """Exibe saldo e informações de valor 1920."""
        cy = y + 20

        saldo = self.f_grande.render(f"${self.inv.dinheiro:.2f}", True, COR_DESTAQUE)
        self.screen.blit(saldo, saldo.get_rect(centerx=x + w // 2, top=cy))
        cy += saldo.get_height() + 8

        sub = self.f_small.render("Dólares americanos — Arkham, 1920s", True, COR_DIMM)
        self.screen.blit(sub, sub.get_rect(centerx=x + w // 2, top=cy))
        cy += sub.get_height() + 30

        # Referência de preços
        ref_titulo = self.f_normal.render("Referência de preços (1920):", True, COR_NORMAL)
        self.screen.blit(ref_titulo, (x, cy)); cy += ref_titulo.get_height() + 6

        refs = [
            ("Revólver .38",              "$12.00"),
            ("Kit de Primeiros Socorros", " $1.50"),
            ("Quarto de hotel (1 noite)", " $0.50"),
            ("Refeição no restaurante",   " $0.25"),
            ("Jornal de Arkham",          " $0.02"),
        ]
        for nome, preco in refs:
            s = self.f_small.render(f"  {nome:35s} {preco}", True, COR_DIMM)
            self.screen.blit(s, (x, cy)); cy += s.get_height() + 2
