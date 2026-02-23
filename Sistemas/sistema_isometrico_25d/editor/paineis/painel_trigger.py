"""
editor/paineis/painel_trigger.py — Editor de triggers (zonas/eventos).

Layout:
    Esquerda (0..320)  — lista de triggers do mapa atual + botões
    Direita (330..fim) — formulário do trigger selecionado:
        ID (readonly) · Tipo (ciclo) · Condição · Ação
        Área (lista de coordenadas) com miniatura do mapa
"""
from __future__ import annotations

import os
import sys
from typing import Optional, List

import pygame

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dados.campanha_schema import Campanha, DadosMapa, Trigger
from editor.widgets import (
    CaixaTexto, Botao, ListaSelecao, Ciclico,
    label, _C, _fonte_padrao,
)

_LISTA_W = 320
_FORM_X  = 334

_TIPOS_TRIGGER = [
    "zona",
    "dialogo_inicio",
    "combate",
    "transicao",
    "item_coletado",
    "evento",
]

_CONDICOES_PADRAO = [
    "sempre",
    "evento:",
    "flag:",
]


class PainelTrigger:

    def __init__(self, tela: pygame.Surface, largura: int, altura: int,
                 campanha: Campanha, mapa_id: str,
                 fonte_ui: Optional[pygame.font.Font] = None):
        self.tela     = tela
        self.largura  = largura
        self.altura   = altura
        self.campanha = campanha
        self.mapa_id  = mapa_id

        self._fn   = fonte_ui or _fonte_padrao(13)
        self._fn_sm = _fonte_padrao(11)

        self._sel_idx: Optional[int] = None

        # Lista
        self._lista = ListaSelecao(
            pygame.Rect(4, 40, _LISTA_W, self.altura - 80),
            fonte=self._fn,
            on_selecao=self._on_selecionar,
        )
        self._btn_novo   = Botao(
            pygame.Rect(4, self.altura - 36, _LISTA_W // 2 - 4, 28),
            "+ Trigger", cor=(40, 100, 60), fonte=self._fn,
            callback=self._novo_trigger,
        )
        self._btn_del    = Botao(
            pygame.Rect(4 + _LISTA_W // 2 + 4, self.altura - 36,
                        _LISTA_W // 2 - 12, 28),
            "🗑", cor=(100, 35, 35), fonte=self._fn,
            callback=self._remover_trigger,
        )

        # Form widgets
        self._ciclo_tipo:  Optional[Ciclico]   = None
        self._cx_cond:     Optional[CaixaTexto] = None
        self._cx_acao:     Optional[CaixaTexto] = None
        self._cx_area:     Optional[CaixaTexto] = None
        self._form_widgets: list = []

        # Mapa selector
        self._mapa_ids  = list(campanha.mapas.keys())
        self._mapa_nomes = [m.nome for m in campanha.mapas.values()]
        mapa_idx = self._mapa_ids.index(mapa_id) if mapa_id in self._mapa_ids else 0
        self._ciclo_mapa = Ciclico(
            pygame.Rect(4, 8, _LISTA_W, 26),
            self._mapa_nomes, mapa_idx, fonte=self._fn_sm,
            on_mudanca=self._on_mapa_mudanca,
        )

        self._atualizar_lista()

    # ── Mapa ──────────────────────────────────────────────────

    @property
    def _dados_mapa(self) -> Optional[DadosMapa]:
        return self.campanha.mapas.get(self.mapa_id)

    def _on_mapa_mudanca(self, nome: str):
        if nome in self._mapa_nomes:
            self.mapa_id = self._mapa_ids[self._mapa_nomes.index(nome)]
            self._sel_idx = None
            self._form_widgets = []
            self._atualizar_lista()

    # ── Lista ─────────────────────────────────────────────────

    def _triggers(self) -> List[Trigger]:
        dm = self._dados_mapa
        return dm.triggers if dm else []

    def _atualizar_lista(self):
        ts = self._triggers()
        self._lista.itens = [
            f"[{t.tipo}] {t.id}  → {t.acao[:24]}"
            for t in ts
        ]

    def _on_selecionar(self, idx: int):
        if 0 <= idx < len(self._triggers()):
            self._sel_idx = idx
            self._criar_form()

    # ── Operações ─────────────────────────────────────────────

    def _novo_trigger(self):
        dm = self._dados_mapa
        if dm is None:
            return
        import uuid as _uuid
        tid = f"t_{str(_uuid.uuid4())[:6]}"
        t = Trigger(id=tid, tipo="zona", condicao="sempre", acao="")
        dm.triggers.append(t)
        self._atualizar_lista()
        idx = len(dm.triggers) - 1
        self._lista.selecionado = idx
        self._on_selecionar(idx)

    def _remover_trigger(self):
        dm = self._dados_mapa
        if dm is None or self._sel_idx is None:
            return
        if 0 <= self._sel_idx < len(dm.triggers):
            dm.triggers.pop(self._sel_idx)
        self._sel_idx = None
        self._form_widgets = []
        self._atualizar_lista()

    # ── Formulário ────────────────────────────────────────────

    def _trigger_sel(self) -> Optional[Trigger]:
        ts = self._triggers()
        if self._sel_idx is not None and 0 <= self._sel_idx < len(ts):
            return ts[self._sel_idx]
        return None

    def _criar_form(self):
        t = self._trigger_sel()
        if not t:
            return

        fn  = self._fn
        fns = self._fn_sm
        x   = _FORM_X
        W   = self.largura - x - 10
        y   = 10

        self._form_widgets = []

        # Tipo
        idx_tipo = _TIPOS_TRIGGER.index(t.tipo) if t.tipo in _TIPOS_TRIGGER else 0
        self._ciclo_tipo = Ciclico(
            pygame.Rect(x, y + 18, W, 28),
            _TIPOS_TRIGGER, idx_tipo, fonte=fn,
            on_mudanca=lambda v: setattr(t, "tipo", v),
        )
        self._form_widgets.append(self._ciclo_tipo)
        y += 56

        # Condição
        self._cx_cond = CaixaTexto(
            pygame.Rect(x, y + 18, W, 26),
            texto=t.condicao, placeholder="sempre | evento:xyz | flag:nome",
            fonte=fns,
        )
        self._form_widgets.append(self._cx_cond)
        y += 52

        # Ação
        self._cx_acao = CaixaTexto(
            pygame.Rect(x, y + 18, W, 26),
            texto=t.acao,
            placeholder="dialogo:d_01 | mapa:m2:5:3 | san:-3 | evento:nome",
            fonte=fns,
        )
        self._form_widgets.append(self._cx_acao)
        y += 52

        # Área (coords como texto "col,linha;col,linha;...")
        area_txt = ";".join(f"{c},{l}" for c, l in t.area)
        self._cx_area = CaixaTexto(
            pygame.Rect(x, y + 18, W, 26),
            texto=area_txt,
            placeholder="col,linha;col,linha;...",
            fonte=fns,
        )
        self._form_widgets.append(self._cx_area)

    def _sincronizar(self):
        t = self._trigger_sel()
        if not t:
            return
        if self._cx_cond:
            t.condicao = self._cx_cond.texto.strip() or "sempre"
        if self._cx_acao:
            t.acao = self._cx_acao.texto.strip()
        if self._cx_area:
            # Parse "col,linha;col,linha"
            try:
                partes = [p.strip() for p in self._cx_area.texto.split(";") if p.strip()]
                t.area = [
                    (int(p.split(",")[0]), int(p.split(",")[1]))
                    for p in partes if "," in p
                ]
            except (ValueError, IndexError):
                pass
        self._atualizar_lista()

    # ── Mini-mapa ─────────────────────────────────────────────

    def _desenhar_minimapa(self, t: Optional[Trigger], x: int, y: int, w: int, h: int):
        dm = self._dados_mapa
        if dm is None:
            return

        pygame.draw.rect(self.tela, (20, 22, 36),
                         pygame.Rect(x, y, w, h))
        pygame.draw.rect(self.tela, _C["borda"],
                         pygame.Rect(x, y, w, h), width=1)

        cw = w / dm.largura
        ch = h / dm.altura
        cw = ch = min(cw, ch)

        for l in range(dm.altura):
            for c in range(dm.largura):
                tile = dm.tiles[l][c] if l < len(dm.tiles) and c < len(dm.tiles[l]) else 0
                if tile == 0:
                    continue
                cor = {1: (70, 90, 70), 2: (90, 75, 60), 3: (110, 95, 75)}.get(tile, (50, 50, 50))
                r = pygame.Rect(x + c * cw, y + l * ch, max(1, cw - 1), max(1, ch - 1))
                pygame.draw.rect(self.tela, cor, r)

        # Tiles da área do trigger
        if t:
            for (tc, tl) in t.area:
                r = pygame.Rect(x + tc * cw, y + tl * ch, max(1, cw - 1), max(1, ch - 1))
                pygame.draw.rect(self.tela, (220, 180, 50), r)

    # ── Loop ──────────────────────────────────────────────────

    def processar_evento(self, e: pygame.event.Event):
        self._ciclo_mapa.processar_evento(e)
        for w in self._form_widgets:
            w.processar_evento(e)
        self._lista.processar_evento(e)
        self._btn_novo.processar_evento(e)
        self._btn_del.processar_evento(e)
        self._sincronizar()

    def atualizar(self, dt: int):
        pass

    def desenhar(self):
        tela = self.tela
        tela.fill(_C["fundo"])

        fn  = self._fn
        fns = self._fn_sm

        # ── Mapa selector ──────────────────────────────────────
        self._ciclo_mapa.rect = pygame.Rect(4, 8, _LISTA_W, 26)
        self._mapa_ids   = list(self.campanha.mapas.keys())
        self._mapa_nomes = [m.nome for m in self.campanha.mapas.values()]
        self._ciclo_mapa.opcoes = self._mapa_nomes
        self._ciclo_mapa.desenhar(tela)

        # ── Lista ──────────────────────────────────────────────
        label(tela, f"TRIGGERS — {self.mapa_id}", (4, 38), fns, cor=(130, 120, 100))
        self._lista.rect = pygame.Rect(4, 56, _LISTA_W, self.altura - 96)
        self._lista.desenhar(tela)
        self._btn_novo.desenhar(tela)
        self._btn_del.desenhar(tela)

        pygame.draw.line(tela, _C["borda"],
                         (_LISTA_W + 8, 0), (_LISTA_W + 8, self.altura), 1)

        # ── Formulário ─────────────────────────────────────────
        t = self._trigger_sel()
        if t is None:
            s = fn.render("← Selecione ou crie um trigger", True, _C["texto_dim"])
            tela.blit(s, s.get_rect(center=((_FORM_X + self.largura) // 2,
                                              self.altura // 2)))
            return

        x = _FORM_X
        W = self.largura - x - 10

        label(tela, f"ID: {t.id}", (x, 0), fns, cor=_C["texto_dim"])
        y = 10
        label(tela, "Tipo:",     (x, y),      fns, cor=_C["texto_dim"])
        label(tela, "Condição:", (x, y + 56), fns, cor=_C["texto_dim"])
        label(tela, "Ação:",     (x, y + 108),fns, cor=_C["texto_dim"])
        label(tela, "Área (col,linha;…):", (x, y + 160), fns, cor=_C["texto_dim"])

        for w in self._form_widgets:
            w.desenhar(tela)

        # Mini-mapa + area highlight
        mini_y = y + 200
        mini_h = min(180, self.altura - mini_y - 10)
        mini_w = W
        label(tela, "Visualização:", (x, mini_y - 14), fns, cor=_C["texto_dim"])
        self._desenhar_minimapa(t, x, mini_y, mini_w, mini_h)

        # Contagem de tiles na área
        s = fns.render(f"{len(t.area)} tiles na zona", True, (180, 200, 120))
        tela.blit(s, (x, mini_y + mini_h + 4))
