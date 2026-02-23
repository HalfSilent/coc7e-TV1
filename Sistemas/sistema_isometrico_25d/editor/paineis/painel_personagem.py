"""
editor/paineis/painel_personagem.py — Editor de personagens da campanha.

Layout:
    Esquerda (0..300)  — lista de personagens + botões [+ Novo] [🗑]
    Direita (310..fim) — formulário do personagem selecionado:
        Nome · Tipo · Sprite · IA · Stats (HP/SAN/STR/DEX/INT/CON)
        Background · Posição de spawn
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import pygame

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dados.campanha_schema import Campanha, Personagem, TipoPersonagem, TipoIA, Stats
from editor.widgets import (
    CaixaTexto, CaixaTextoMulti, Botao, ListaSelecao,
    Ciclico, SliderInt, label, _C, _fonte_padrao,
)

_LISTA_W = 290
_FORM_X  = 310
_ROW_H   = 32


class PainelPersonagem:

    def __init__(self, tela: pygame.Surface, largura: int, altura: int,
                 campanha: Campanha,
                 fonte_ui: Optional[pygame.font.Font] = None):
        self.tela     = tela
        self.largura  = largura
        self.altura   = altura
        self.campanha = campanha
        self._fn      = fonte_ui or _fonte_padrao(13)
        self._fn_sm   = _fonte_padrao(11)
        self._fn_big  = _fonte_padrao(15)

        self._sel_idx: Optional[int] = None  # índice na lista
        self._sel_pid: Optional[str] = None  # ID do personagem

        # Widgets da lista
        self._lista = ListaSelecao(
            pygame.Rect(8, 40, _LISTA_W, self.altura - 80),
            fonte=self._fn,
            on_selecao=self._on_selecionar,
        )
        self._btn_novo    = Botao(
            pygame.Rect(8, self.altura - 36, _LISTA_W // 2 - 4, 28),
            "+ Novo", cor=(40, 100, 60), fonte=self._fn,
            callback=self._novo_personagem,
        )
        self._btn_deletar = Botao(
            pygame.Rect(8 + _LISTA_W // 2 + 4, self.altura - 36,
                        _LISTA_W // 2 - 12, 28),
            "🗑 Remover", cor=(100, 35, 35), fonte=self._fn,
            callback=self._remover_personagem,
        )

        # Widgets do formulário (recriados em _criar_form)
        self._form_widgets: list = []
        self._caixa_nome:   Optional[CaixaTexto] = None
        self._caixa_bg:     Optional[CaixaTextoMulti] = None
        self._ciclo_tipo:   Optional[Ciclico] = None
        self._ciclo_ia:     Optional[Ciclico] = None
        self._ciclo_sprite: Optional[Ciclico] = None
        self._sliders:      dict = {}   # nome → SliderInt
        self._caixa_spawn_c: Optional[CaixaTexto] = None
        self._caixa_spawn_l: Optional[CaixaTexto] = None

        self._atualizar_lista()

    # ── Lista ─────────────────────────────────────────────────

    def _atualizar_lista(self):
        self._pids = list(self.campanha.personagens.keys())
        self._lista.itens = [
            self.campanha.personagens[pid].nome
            for pid in self._pids
        ]

    def _on_selecionar(self, idx: int):
        if 0 <= idx < len(self._pids):
            self._sel_idx = idx
            self._sel_pid = self._pids[idx]
            self._criar_form()

    # ── Operações de personagem ───────────────────────────────

    def _novo_personagem(self):
        p = self.campanha.novo_personagem("Novo Personagem")
        self._atualizar_lista()
        idx = self._pids.index(p.id)
        self._lista.selecionado = idx
        self._on_selecionar(idx)

    def _remover_personagem(self):
        if not self._sel_pid:
            return
        pid = self._sel_pid
        # Não remove o jogador principal
        if pid == self.campanha.personagem_jogador_id:
            return
        del self.campanha.personagens[pid]
        # Remove de spawns
        for mapa in self.campanha.mapas.values():
            if pid in mapa.personagens_spawn:
                mapa.personagens_spawn.remove(pid)
        self._sel_idx = None
        self._sel_pid = None
        self._form_widgets = []
        self._atualizar_lista()

    # ── Formulário ────────────────────────────────────────────

    def _criar_form(self):
        pid = self._sel_pid
        if not pid or pid not in self.campanha.personagens:
            return
        p   = self.campanha.personagens[pid]
        fn  = self._fn
        x   = _FORM_X
        y   = 10
        W   = self.largura - _FORM_X - 20

        self._form_widgets = []

        # Nome
        self._caixa_nome = CaixaTexto(
            pygame.Rect(x, y + 20, W, 28), texto=p.nome,
            placeholder="Nome do personagem", fonte=fn,
        )
        self._form_widgets.append(self._caixa_nome)
        y += 60

        # Tipo
        idx_tipo = TipoPersonagem.TODOS.index(p.tipo) if p.tipo in TipoPersonagem.TODOS else 0
        self._ciclo_tipo = Ciclico(
            pygame.Rect(x, y + 20, W, 28),
            TipoPersonagem.TODOS, idx_tipo, fonte=fn,
            on_mudanca=lambda v: setattr(p, "tipo", v),
        )
        self._form_widgets.append(self._ciclo_tipo)
        y += 60

        # IA
        idx_ia = TipoIA.TODOS.index(p.ia) if p.ia in TipoIA.TODOS else 0
        self._ciclo_ia = Ciclico(
            pygame.Rect(x, y + 20, W, 28),
            TipoIA.TODOS, idx_ia, fonte=fn,
            on_mudanca=lambda v: setattr(p, "ia", v),
        )
        self._form_widgets.append(self._ciclo_ia)
        y += 60

        # Sprite
        self._ciclo_sprite = Ciclico(
            pygame.Rect(x, y + 20, W, 28),
            list(range(8)), p.sprite_id, fonte=fn,
            on_mudanca=lambda v: setattr(p, "sprite_id", v),
        )
        self._form_widgets.append(self._ciclo_sprite)
        y += 60

        # Stats (sliders)
        self._sliders = {}
        STAT_CAMPOS = [
            ("hp",           "HP",           1,  20,  p.stats.hp),
            ("san",          "SAN",          0,  99,  p.stats.san),
            ("forca",        "Força",        1,  99,  p.stats.forca),
            ("destreza",     "Destreza",     1,  99,  p.stats.destreza),
            ("inteligencia", "Inteligência", 1,  99,  p.stats.inteligencia),
            ("constituicao", "Constituição", 1,  99,  p.stats.constituicao),
        ]
        slider_w = (W - 10) // 2
        col_x = [x, x + slider_w + 10]
        for i, (campo, nome, mn, mx_, val) in enumerate(STAT_CAMPOS):
            sx = col_x[i % 2]
            sy = y + (i // 2) * 44 + 20

            def make_cb(c):
                def cb(v):
                    if self._sel_pid in self.campanha.personagens:
                        setattr(self.campanha.personagens[self._sel_pid].stats, c, v)
                return cb

            sl = SliderInt(
                pygame.Rect(sx, sy, slider_w - 50, 20),
                min_val=mn, max_val=mx_, valor=val,
                fonte=self._fn_sm,
                on_mudanca=make_cb(campo),
            )
            self._sliders[campo] = (nome, sl)
            self._form_widgets.append(sl)

        y += (len(STAT_CAMPOS) // 2 + 1) * 44 + 10

        # Background
        self._caixa_bg = CaixaTextoMulti(
            pygame.Rect(x, y + 20, W, 72),
            texto=p.background, fonte=self._fn_sm,
        )
        self._form_widgets.append(self._caixa_bg)
        y += 100

        # Spawn position
        sw = (W - 10) // 2
        self._caixa_spawn_c = CaixaTexto(
            pygame.Rect(x, y + 20, sw, 26),
            texto=str(int(p.spawn_col)), fonte=fn,
        )
        self._caixa_spawn_l = CaixaTexto(
            pygame.Rect(x + sw + 10, y + 20, sw, 26),
            texto=str(int(p.spawn_linha)), fonte=fn,
        )
        self._form_widgets.append(self._caixa_spawn_c)
        self._form_widgets.append(self._caixa_spawn_l)

    def _sincronizar_form(self):
        """Copia valores dos widgets de texto de volta ao personagem."""
        pid = self._sel_pid
        if not pid or pid not in self.campanha.personagens:
            return
        p = self.campanha.personagens[pid]

        if self._caixa_nome and self._caixa_nome.texto.strip():
            p.nome = self._caixa_nome.texto.strip()
        if self._ciclo_tipo:
            p.tipo = self._ciclo_tipo.valor
        if self._ciclo_ia:
            p.ia = self._ciclo_ia.valor
        if self._ciclo_sprite:
            p.sprite_id = int(self._ciclo_sprite.valor)
        if self._caixa_bg:
            p.background = self._caixa_bg.texto
        if self._caixa_spawn_c:
            try:
                p.spawn_col = float(self._caixa_spawn_c.texto)
            except ValueError:
                pass
        if self._caixa_spawn_l:
            try:
                p.spawn_linha = float(self._caixa_spawn_l.texto)
            except ValueError:
                pass

        # Atualiza nome na lista
        self._lista.itens = [
            self.campanha.personagens[p2].nome for p2 in self._pids
        ]

    # ── Loop ──────────────────────────────────────────────────

    def processar_evento(self, e: pygame.event.Event):
        consumed = False
        for w in self._form_widgets:
            if w.processar_evento(e):
                consumed = True
        if not consumed:
            self._lista.processar_evento(e)
            self._btn_novo.processar_evento(e)
            self._btn_deletar.processar_evento(e)

        self._sincronizar_form()

    def atualizar(self, dt: int):
        pass

    def desenhar(self):
        tela = self.tela
        tela.fill(_C["fundo"])

        # ── Lista ──────────────────────────────────────────────
        label(tela, "PERSONAGENS", (8, 12), self._fn_sm,
              cor=(130, 120, 100))
        self._lista.desenhar(tela)
        self._btn_novo.desenhar(tela)
        self._btn_deletar.desenhar(tela)

        # Linha separadora
        pygame.draw.line(tela, _C["borda"],
                         (_LISTA_W + 8, 0), (_LISTA_W + 8, self.altura), 1)

        # ── Formulário ─────────────────────────────────────────
        if not self._sel_pid or self._sel_pid not in self.campanha.personagens:
            s = self._fn.render("← Selecione ou crie um personagem", True,
                                _C["texto_dim"])
            tela.blit(s, s.get_rect(center=((_FORM_X + self.largura) // 2,
                                              self.altura // 2)))
            return

        p   = self.campanha.personagens[self._sel_pid]
        fn  = self._fn
        fns = self._fn_sm
        x   = _FORM_X
        y   = 10
        W   = self.largura - _FORM_X - 20

        # ── Cabeçalho ──
        eh_jogador = (self._sel_pid == self.campanha.personagem_jogador_id)
        header_cor = (200, 170, 60) if eh_jogador else _C["texto"]
        tipo_badge = "[JOGADOR]" if eh_jogador else f"[{p.tipo.upper()}]"
        label(tela, f"{p.nome}  {tipo_badge}", (x, y), self._fn_big, cor=header_cor)
        y += 24
        pygame.draw.line(tela, _C["borda"], (x, y), (x + W, y), 1)
        y += 6

        # Labels dos campos
        labels_y = [
            ("Nome", y),
            ("Tipo", y + 60),
            ("IA", y + 120),
            ("Sprite (skin)", y + 180),
        ]
        for lbl, ly in labels_y:
            label(tela, lbl, (x, ly), fns, cor=_C["texto_dim"])

        y += 240
        label(tela, "Stats", (x, y), fns, cor=_C["texto_dim"])
        y += 16

        # Sliders com labels
        slider_w = (W - 10) // 2
        col_x = [x, x + slider_w + 10]
        for i, (campo, (nome, sl)) in enumerate(self._sliders.items()):
            sx = col_x[i % 2]
            sy = y + (i // 2) * 44
            label(tela, nome, (sx, sy), fns, cor=_C["texto_dim"])

        y += (len(self._sliders) // 2 + 1) * 44 + 10
        label(tela, "Background / Notas", (x, y), fns, cor=_C["texto_dim"])
        y += 100
        label(tela, "Spawn Col / Linha", (x, y), fns, cor=_C["texto_dim"])

        # Todos os widgets
        for w in self._form_widgets:
            w.desenhar(tela)

        # Preview sprite (caixa colorida)
        skin  = p.sprite_id
        cores = [
            (200, 160,  80), (160, 130, 210), (210, 100, 100),
            (100, 180, 100), (100, 160, 210), (210, 160, 100),
            (160, 100, 160), (100, 200, 180),
        ]
        cor_skin = cores[skin % len(cores)]
        pr = pygame.Rect(x + W - 50, 256, 40, 60)
        pygame.draw.rect(tela, cor_skin,     pr, border_radius=4)
        pygame.draw.rect(tela, _C["borda"], pr, width=1, border_radius=4)
        s = fns.render(f"M{skin}", True, (30, 30, 30))
        tela.blit(s, s.get_rect(center=pr.center))
