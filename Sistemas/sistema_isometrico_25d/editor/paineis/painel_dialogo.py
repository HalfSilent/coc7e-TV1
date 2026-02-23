"""
editor/paineis/painel_dialogo.py — Editor de árvores de diálogo.

Layout em 3 colunas:
    [0..220]   Lista de diálogos (+ botões Novo / Remover)
    [230..500] Lista de nós do diálogo selecionado (+ Novo / Remover)
    [510..fim] Editor do nó selecionado:
                 - Personagem (ciclo), Texto (multilinhas), Efeito
                 - Escolhas (lista com texto + alvo)
"""
from __future__ import annotations

import os
import sys
from typing import Optional
import uuid

import pygame

_RAIZ = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from dados.campanha_schema import (
    Campanha, Dialogo, NoDialogo, EscolhaDialogo,
)
from editor.widgets import (
    CaixaTexto, CaixaTextoMulti, Botao, ListaSelecao, Ciclico,
    label, _C, _fonte_padrao,
)

_COL1_W = 220
_COL2_X = _COL1_W + 10
_COL2_W = 270
_COL3_X = _COL2_X + _COL2_W + 10


class PainelDialogo:

    def __init__(self, tela: pygame.Surface, largura: int, altura: int,
                 campanha: Campanha,
                 fonte_ui: Optional[pygame.font.Font] = None):
        self.tela     = tela
        self.largura  = largura
        self.altura   = altura
        self.campanha = campanha
        self._fn   = fonte_ui or _fonte_padrao(13)
        self._fn_sm = _fonte_padrao(11)

        self._sel_did: Optional[str] = None   # diálogo selecionado
        self._sel_nid: Optional[str] = None   # nó selecionado

        # ── Coluna 1: lista de diálogos ────────────────────────
        self._lista_dial = ListaSelecao(
            pygame.Rect(4, 40, _COL1_W, self.altura - 80),
            fonte=self._fn,
            on_selecao=self._on_sel_dialogo,
        )
        self._btn_novo_d   = Botao(
            pygame.Rect(4, self.altura - 36, _COL1_W // 2 - 2, 28),
            "+ Diálogo", cor=(40, 100, 60), fonte=self._fn,
            callback=self._novo_dialogo,
        )
        self._btn_del_d    = Botao(
            pygame.Rect(4 + _COL1_W // 2 + 2, self.altura - 36,
                        _COL1_W // 2 - 6, 28),
            "🗑", cor=(100, 35, 35), fonte=self._fn,
            callback=self._remover_dialogo,
        )

        # ── Coluna 2: lista de nós ─────────────────────────────
        self._lista_nos = ListaSelecao(
            pygame.Rect(_COL2_X, 40, _COL2_W, self.altura - 80),
            fonte=self._fn,
            on_selecao=self._on_sel_no,
        )
        self._btn_novo_n = Botao(
            pygame.Rect(_COL2_X, self.altura - 36, _COL2_W // 2 - 2, 28),
            "+ Nó", cor=(40, 80, 120), fonte=self._fn,
            callback=self._novo_no,
        )
        self._btn_del_n  = Botao(
            pygame.Rect(_COL2_X + _COL2_W // 2 + 2, self.altura - 36,
                        _COL2_W // 2 - 6, 28),
            "🗑", cor=(100, 35, 35), fonte=self._fn,
            callback=self._remover_no,
        )

        # ── Coluna 3: editor de nó ─────────────────────────────
        self._form_widgets: list = []
        self._caixa_titulo_d: Optional[CaixaTexto] = None   # título do diálogo
        self._ciclo_pers:     Optional[Ciclico]    = None
        self._caixa_texto:    Optional[CaixaTextoMulti] = None
        self._caixa_efeito:   Optional[CaixaTexto] = None
        # lista de (caixa_texto_escolha, ciclo_proximo)
        self._escolhas_widgets: list = []

        self._atualizar_lista_dial()

    # ── Dados ──────────────────────────────────────────────────

    @property
    def _dialogo(self) -> Optional[Dialogo]:
        if self._sel_did:
            return self.campanha.dialogos.get(self._sel_did)
        return None

    @property
    def _no(self) -> Optional[NoDialogo]:
        d = self._dialogo
        if d and self._sel_nid:
            return d.nos.get(self._sel_nid)
        return None

    def _dids(self):
        return list(self.campanha.dialogos.keys())

    def _nids(self) -> list:
        d = self._dialogo
        return list(d.nos.keys()) if d else []

    # ── Atualização de listas ──────────────────────────────────

    def _atualizar_lista_dial(self):
        self._lista_dial.itens = [
            self.campanha.dialogos[did].titulo
            for did in self._dids()
        ]

    def _atualizar_lista_nos(self):
        d = self._dialogo
        if not d:
            self._lista_nos.itens = []
            return
        self._lista_nos.itens = [
            f"[{nid}] {no.texto[:30]}…" if len(no.texto) > 30 else f"[{nid}] {no.texto}"
            for nid, no in d.nos.items()
        ]

    # ── Seleção ────────────────────────────────────────────────

    def _on_sel_dialogo(self, idx: int):
        dids = self._dids()
        if 0 <= idx < len(dids):
            self._sel_did = dids[idx]
            self._sel_nid = None
            self._form_widgets = []
            self._atualizar_lista_nos()
            # Cria caixa de título do diálogo
            d = self._dialogo
            if d:
                self._caixa_titulo_d = CaixaTexto(
                    pygame.Rect(_COL3_X, 12, self.largura - _COL3_X - 10, 26),
                    texto=d.titulo, fonte=self._fn,
                )
            else:
                self._caixa_titulo_d = None

    def _on_sel_no(self, idx: int):
        nids = self._nids()
        if 0 <= idx < len(nids):
            self._sel_nid = nids[idx]
            self._criar_form_no()

    # ── Operações de diálogo ───────────────────────────────────

    def _novo_dialogo(self):
        d = self.campanha.novo_dialogo(f"Diálogo {len(self.campanha.dialogos)+1}")
        self._atualizar_lista_dial()
        idx = self._dids().index(d.id)
        self._lista_dial.selecionado = idx
        self._on_sel_dialogo(idx)

    def _remover_dialogo(self):
        if self._sel_did:
            self.campanha.dialogos.pop(self._sel_did, None)
            self._sel_did = None
            self._sel_nid = None
            self._form_widgets = []
            self._atualizar_lista_dial()
            self._lista_nos.itens = []

    # ── Operações de nó ───────────────────────────────────────

    def _novo_no(self):
        d = self._dialogo
        if not d:
            return
        nid = f"n{len(d.nos) + 1}"
        while nid in d.nos:
            nid = f"n{str(uuid.uuid4())[:4]}"
        personagem_ids = list(self.campanha.personagens.keys())
        pid = personagem_ids[0] if personagem_ids else "jogador"
        no  = NoDialogo(id=nid, personagem_id=pid, texto="...")
        d.adicionar_no(no)
        self._atualizar_lista_nos()
        idx = self._nids().index(nid)
        self._lista_nos.selecionado = idx
        self._on_sel_no(idx)

    def _remover_no(self):
        d = self._dialogo
        if d and self._sel_nid:
            d.nos.pop(self._sel_nid, None)
            if d.no_inicial == self._sel_nid:
                d.no_inicial = next(iter(d.nos), "")
            self._sel_nid = None
            self._form_widgets = []
            self._atualizar_lista_nos()

    # ── Formulário do nó ──────────────────────────────────────

    def _criar_form_no(self):
        no = self._no
        if not no:
            return
        fn  = self._fn
        fns = self._fn_sm
        x   = _COL3_X
        W   = self.largura - x - 10
        y   = 45

        self._form_widgets = []
        self._escolhas_widgets = []

        # Personagem
        pids = list(self.campanha.personagens.keys())
        pnomes = [self.campanha.personagens[p].nome for p in pids]
        idx_p = pids.index(no.personagem_id) if no.personagem_id in pids else 0
        self._ciclo_pers = Ciclico(
            pygame.Rect(x, y + 18, W, 28), pnomes, idx_p, fonte=fn,
            on_mudanca=lambda v: setattr(no, "personagem_id",
                                         pids[pnomes.index(v)]),
        )
        self._form_widgets.append(self._ciclo_pers)
        y += 56

        # Texto
        self._caixa_texto = CaixaTextoMulti(
            pygame.Rect(x, y + 18, W, 80), texto=no.texto, fonte=fns,
        )
        self._form_widgets.append(self._caixa_texto)
        y += 108

        # Efeito
        self._caixa_efeito = CaixaTexto(
            pygame.Rect(x, y + 18, W, 26), texto=no.efeito,
            placeholder="ex: san:-3 | evento:saber_segredo", fonte=fns,
        )
        self._form_widgets.append(self._caixa_efeito)
        y += 52

        # Escolhas (até 4)
        nos_ids  = ["(fim)"] + self._nids()
        for i, esc in enumerate(no.escolhas[:4]):
            # Texto da escolha
            ct = CaixaTexto(
                pygame.Rect(x, y, W - 120, 26),
                texto=esc.texto, placeholder=f"Escolha {i+1}", fonte=fns,
            )
            # Próximo nó
            prox_opts = nos_ids
            idx_prox  = prox_opts.index(esc.proximo) if esc.proximo in prox_opts else 0
            cp = Ciclico(
                pygame.Rect(x + W - 115, y, 110, 26),
                prox_opts, idx_prox, fonte=fns,
            )
            self._form_widgets.append(ct)
            self._form_widgets.append(cp)
            self._escolhas_widgets.append((ct, cp, i))
            y += 32

        # Botões adicionar/remover escolha
        self._btn_add_esc = Botao(
            pygame.Rect(x, y + 4, 100, 24),
            "+ Escolha", cor=(40, 80, 100), fonte=fns,
            callback=self._adicionar_escolha,
        )
        self._btn_rem_esc = Botao(
            pygame.Rect(x + 106, y + 4, 90, 24),
            "- Escolha", cor=(90, 40, 40), fonte=fns,
            callback=self._remover_escolha,
        )
        self._form_widgets.append(self._btn_add_esc)
        self._form_widgets.append(self._btn_rem_esc)

    def _adicionar_escolha(self):
        no = self._no
        if no and len(no.escolhas) < 4:
            no.escolhas.append(EscolhaDialogo(texto="Nova escolha", proximo=None))
            self._criar_form_no()

    def _remover_escolha(self):
        no = self._no
        if no and no.escolhas:
            no.escolhas.pop()
            self._criar_form_no()

    def _sincronizar_no(self):
        no = self._no
        if not no:
            return
        if self._caixa_texto:
            no.texto = self._caixa_texto.texto
        if self._caixa_efeito:
            no.efeito = self._caixa_efeito.texto
        # Sincroniza escolhas
        nids_com_fim = ["(fim)"] + self._nids()
        for ct, cp, i in self._escolhas_widgets:
            if i < len(no.escolhas):
                no.escolhas[i].texto  = ct.texto
                prox = cp.valor
                no.escolhas[i].proximo = None if prox == "(fim)" else prox

        # Sincroniza título do diálogo
        d = self._dialogo
        if d and self._caixa_titulo_d:
            if self._caixa_titulo_d.texto.strip():
                d.titulo = self._caixa_titulo_d.texto.strip()
            self._atualizar_lista_dial()

    # ── Loop ──────────────────────────────────────────────────

    def processar_evento(self, e: pygame.event.Event):
        if self._caixa_titulo_d:
            self._caixa_titulo_d.processar_evento(e)
        for w in self._form_widgets:
            w.processar_evento(e)
        self._lista_dial.processar_evento(e)
        self._lista_nos.processar_evento(e)
        self._btn_novo_d.processar_evento(e)
        self._btn_del_d.processar_evento(e)
        self._btn_novo_n.processar_evento(e)
        self._btn_del_n.processar_evento(e)
        self._sincronizar_no()

    def atualizar(self, dt: int):
        pass

    def desenhar(self):
        tela = self.tela
        tela.fill(_C["fundo"])

        fn  = self._fn
        fns = self._fn_sm

        # ── Col 1: Diálogos ────────────────────────────────────
        label(tela, "DIÁLOGOS", (4, 12), fns, cor=(130, 120, 100))
        self._lista_dial.desenhar(tela)
        self._btn_novo_d.desenhar(tela)
        self._btn_del_d.desenhar(tela)
        pygame.draw.line(tela, _C["borda"],
                         (_COL1_W + 4, 0), (_COL1_W + 4, self.altura), 1)

        # ── Col 2: Nós ─────────────────────────────────────────
        label(tela, "NÓS", (_COL2_X, 12), fns, cor=(130, 120, 100))
        self._lista_nos.desenhar(tela)
        self._btn_novo_n.desenhar(tela)
        self._btn_del_n.desenhar(tela)
        pygame.draw.line(tela, _C["borda"],
                         (_COL3_X - 6, 0), (_COL3_X - 6, self.altura), 1)

        # ── Col 3: Editor ──────────────────────────────────────
        if not self._sel_did:
            s = fn.render("← Selecione ou crie um diálogo", True, _C["texto_dim"])
            tela.blit(s, s.get_rect(center=((_COL3_X + self.largura) // 2,
                                              self.altura // 2)))
            return

        # Título do diálogo
        x = _COL3_X
        W = self.largura - x - 10
        label(tela, "Título do diálogo:", (x, 0), fns, cor=_C["texto_dim"])
        if self._caixa_titulo_d:
            self._caixa_titulo_d.desenhar(tela)

        if not self._sel_nid:
            s = fn.render("← Selecione ou crie um nó", True, _C["texto_dim"])
            tela.blit(s, s.get_rect(center=((_COL3_X + self.largura) // 2,
                                              self.altura // 2)))
        else:
            # Labels dos campos
            y = 45
            label(tela, "Personagem:",        (x, y),         fns, cor=_C["texto_dim"])
            label(tela, "Texto:",             (x, y + 56),    fns, cor=_C["texto_dim"])
            label(tela, "Efeito:",            (x, y + 164),   fns, cor=_C["texto_dim"])
            label(tela, "Escolhas → Próximo:",(x, y + 216),   fns, cor=_C["texto_dim"])

            # Widgets
            for w in self._form_widgets:
                w.desenhar(tela)

            # Indicador de nó inicial
            d = self._dialogo
            if d and d.no_inicial == self._sel_nid:
                s = fns.render("★ NÓ INICIAL", True, (220, 200, 60))
                tela.blit(s, (x + W - 90, 0))
