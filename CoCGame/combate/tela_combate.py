"""
combate/tela_combate.py — Tela de combate tático top-down (CoC 7e).

Fluxo:
    Masmorra detecta inimigo próximo → chama TelaCombate(screen, mundo, jogador, inimigos).run()
    Retorna: "vitoria" | "derrota" | "fuga"

Layout:
    ┌──────────────────────────┬──────────────────┐
    │                          │                  │
    │   GRID DE COMBATE        │   PAINEL HUD     │
    │   (top-down 2D)          │   (cartas/log)   │
    │                          │                  │
    └──────────────────────────┴──────────────────┘

Controles:
    Mouse sobre grid   → cursor de seleção
    [1–9]             → seleciona carta/ação
    Click no grid     → confirma alvo ou movimento
    [ESC]             → cancela ação em andamento
    [F]               → fuga (testa Esquivar)
    [ENTER]           → passa o turno (Esperar)
"""
from __future__ import annotations

import sys
import random
from typing import List, Optional, Set, Tuple

import pygame

from engine.mundo import Mundo, TipoTile, EfeitoAmbiental
from engine.entidade import Entidade, Jogador, Inimigo, Engendro
from engine.combate.gerenciador import (
    GerenciadorCombate, EstadoCombate, TipoAcao, Acao, ACOES_PADRAO
)
from combate.renderer_combate import RendererCombate, CELL_SIZE
from combate.cards import Card, montar_deck_investigador, rolar_dado, efeito_chao_para_enum
from gerenciador_assets import get_font, garantir_fontes


# ══════════════════════════════════════════════════════════════
# MAPA PADRÃO (fallback se nenhum Mundo for passado)
# ══════════════════════════════════════════════════════════════

MAPA_PADRÃO = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 3, 3, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]


# ══════════════════════════════════════════════════════════════
# TELA DE COMBATE
# ══════════════════════════════════════════════════════════════

class TelaCombate:
    """
    Tela de combate tático top-down.
    
    Exemplo de uso:
        resultado = TelaCombate(
            screen, jogador,
            inimigos=[Inimigo("Cultista", col=8, linha=3)],
            mundo=mundo_atual
        ).run()
    """

    LARGURA_HUD = 260  # pixels do painel lateral direito

    def __init__(
        self,
        screen: pygame.Surface,
        jogador: Jogador,
        inimigos: Optional[List[Entidade]] = None,
        mundo:    Optional[Mundo] = None,
        arma_equipada: str = "",
        itens_inv:     Optional[List[str]] = None,
        pericias:      Optional[dict] = None,
    ):
        self.screen  = screen
        self.jogador = jogador
        self.inimigos = inimigos or []
        self.clock   = pygame.time.Clock()

        # Carrega / cria mundo de combate
        if mundo:
            self.mundo = mundo
        else:
            self.mundo = Mundo(MAPA_PADRÃO)

        # Posiciona jogador e inimigos no grid
        self._posicionar_entidades()

        # Gerenciador de combate
        self.gerenciador = GerenciadorCombate(
            self.mundo,
            on_log=self._adicionar_log
        )
        self.gerenciador.iniciar_combate(self.jogador, self.inimigos)

        # Pericias do investigador (usadas pelo deck e pelos testes CoC 7e)
        _pericias = pericias or getattr(jogador, "pericias", {})

        # Deck de cartas — dinâmico baseado nas pericias reais do investigador
        self.deck: List[Card] = montar_deck_investigador(
            pericias=_pericias,
            inventario=itens_inv or [],
            arma=arma_equipada,
        )
        self.card_selecionado: Optional[int] = None
        self.deck_scroll: int = 0         # offset de scroll do painel de cartas
        self.cursor_grid: Optional[Tuple[int, int]] = None

        # Highlights
        self.celulas_movimento: Set[Tuple[int, int]] = set()
        self.celulas_alcance:   Set[Tuple[int, int]] = set()

        # Layout
        w, h = screen.get_size()
        self.area_grid = pygame.Rect(0, 0, w - self.LARGURA_HUD, h)
        self.area_hud  = pygame.Rect(w - self.LARGURA_HUD, 0, self.LARGURA_HUD, h)

        # Renderer
        self.renderer = RendererCombate(
            screen, get_font("hud", 18),
            offset_x=16, offset_y=16
        )

        # Fontes
        garantir_fontes()
        self.f_titulo  = get_font("titulo", 20)
        self.f_normal  = get_font("hud", 16)
        self.f_grande  = get_font("titulo", 28)

        # Log
        self.log_combate: List[str] = []

        # Estado de fuga
        self._tentativa_fuga = False
        self.resultado = "em_combate"

    # ══════════════════════════════════════════════════════════
    # POSICIONAMENTO
    # ══════════════════════════════════════════════════════════

    def _posicionar_entidades(self):
        """Coloca jogador e inimigos em posições válidas do grid."""
        celulas_livres = [
            (c, l)
            for l in range(self.mundo.linhas)
            for c in range(self.mundo.colunas)
            if self.mundo.grid[l][c].passavel
        ]
        if not celulas_livres:
            return

        # Jogador: canto inferior-esquerdo
        for c, l in sorted(celulas_livres, key=lambda p: (p[1], p[0]), reverse=True):
            cel = self.mundo.celula(c, l)
            if cel and cel.passavel:
                self.jogador.col   = c
                self.jogador.linha = l
                cel.ocupante = self.jogador
                celulas_livres.remove((c, l))
                break

        # Inimigos: distribuídos no canto oposto
        posicoes_ini = sorted(celulas_livres, key=lambda p: (p[1], p[0]))
        for i, ent in enumerate(self.inimigos):
            if i < len(posicoes_ini):
                c, l = posicoes_ini[i]
                ent.col   = c
                ent.linha = l
                cel = self.mundo.celula(c, l)
                if cel:
                    cel.ocupante = ent

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def run(self) -> str:
        """Loop principal. Retorna 'vitoria', 'derrota' ou 'fuga'."""
        while True:
            dt = self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._processar_evento(event)

            # Verifica fim de combate
            if self.gerenciador.estado == EstadoCombate.FIM_COMBATE:
                resultado = self._determinar_resultado()
                self._tela_resultado(resultado)
                return resultado

            # Turno de inimigo: gerenciador resolve automaticamente
            # (já feito dentro de proximo_turno())

            self._renderizar()

    # ══════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════

    def _processar_evento(self, event: pygame.event.Event):
        estado = self.gerenciador.estado

        if event.type == pygame.KEYDOWN:
            self._teclado(event.key, estado)

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.area_grid.collidepoint(mx, my):
                col, linha = self.renderer.pixel_para_grid(mx, my)
                if 0 <= col < self.mundo.colunas and 0 <= linha < self.mundo.linhas:
                    self.cursor_grid = (col, linha)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.area_grid.collidepoint(mx, my):
                col, linha = self.renderer.pixel_para_grid(mx, my)
                self._click_grid(col, linha)

    def _teclado(self, key: int, estado: EstadoCombate):
        if key == pygame.K_ESCAPE:
            if estado == EstadoCombate.ESCOLHENDO_ALVO:
                self.gerenciador.cancelar_acao()
                self._limpar_highlights()
                self.card_selecionado = None

        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            # Esperar (passa turno)
            if estado == EstadoCombate.TURNO_JOGADOR:
                esperar = Acao(TipoAcao.ESPERAR, custo_ap=0, alcance=0, descricao="Esperar")
                self.gerenciador.selecionar_acao(esperar)
                self._limpar_highlights()

        elif key == pygame.K_f:
            # Tentativa de fuga
            if estado == EstadoCombate.TURNO_JOGADOR:
                self._tentar_fuga()

        # Scroll da lista de cartas no HUD [↑ ↓ / PgUp PgDn]
        elif key in (pygame.K_UP, pygame.K_PAGEUP):
            self.deck_scroll = max(0, self.deck_scroll - 1)

        elif key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
            self.deck_scroll = min(max(0, len(self.deck) - 1), self.deck_scroll + 1)

        # Selecionar carta [1-9]  (relativo ao scroll atual)
        elif pygame.K_1 <= key <= pygame.K_9:
            idx = (key - pygame.K_1) + self.deck_scroll
            if idx < len(self.deck):
                self._selecionar_card(idx)

    def _selecionar_card(self, idx: int):
        estado = self.gerenciador.estado
        if estado != EstadoCombate.TURNO_JOGADOR:
            return

        card = self.deck[idx]
        self.card_selecionado = idx
        self._limpar_highlights()

        p = self.gerenciador.participante_ativo
        if not p or p.ap_atual < card.custo_ap:
            self._adicionar_log(f"AP insuficiente para {card.nome}!")
            return

        # Cards de movimento
        if card.tipo == "movimento":
            passos = card.efeito.get("passos", 3)
            ent = self.jogador
            celulas = self.mundo.celulas_em_alcance(
                int(ent.col), int(ent.linha), passos, so_passaveis=True
            )
            self.celulas_movimento = {(c, l) for c, l in celulas}
            # Prepara ação de mover no gerenciador
            acao = Acao(TipoAcao.MOVER, custo_ap=card.custo_ap, alcance=passos)
            self.gerenciador.selecionar_acao(acao)

        # Cards de ataque
        elif card.tipo == "ataque":
            ent = self.jogador
            celulas = self.mundo.celulas_em_alcance(
                int(ent.col), int(ent.linha), card.alcance
            )
            self.celulas_alcance = {(c, l) for c, l in celulas if
                                    self.mundo.celula(c, l) and
                                    self.mundo.celula(c, l).ocupante is not None}
            # Modo escolha de alvo manual
            self._modo_ataque_card = card
            self.gerenciador.estado = EstadoCombate.ESCOLHENDO_ALVO
            self._adicionar_log(f"{card.nome}: selecione o alvo")

        # Cards de ambiente
        elif card.tipo == "ambiente":
            ent = self.jogador
            celulas = self.mundo.celulas_em_alcance(
                int(ent.col), int(ent.linha), card.alcance
            )
            self.celulas_alcance = {(c, l) for c, l in celulas}
            self._modo_ataque_card = card
            self.gerenciador.estado = EstadoCombate.ESCOLHENDO_ALVO
            self._adicionar_log(f"{card.nome}: selecione a célula-alvo")

        # Cards de habilidade / defesa
        elif card.tipo in ("habilidade", "defesa"):
            self._executar_card_habilidade(card)

        self._adicionar_log(f"Selecionado: {card}")

    def _click_grid(self, col: int, linha: int):
        estado = self.gerenciador.estado

        if estado == EstadoCombate.TURNO_JOGADOR:
            # Click direto no grid sem carta selecionada — selecionar inimigo
            cel = self.mundo.celula(col, linha)
            if cel and cel.ocupante and cel.ocupante is not self.jogador:
                self._adicionar_log(f"Inimigo: {cel.ocupante.nome} — HP {cel.ocupante.hp}")

        elif estado == EstadoCombate.ESCOLHENDO_ALVO:
            card = getattr(self, "_modo_ataque_card", None)
            if card:
                self._confirmar_card(card, col, linha)
            else:
                # Usa gerenciador legado
                self.gerenciador.confirmar_alvo(col, linha)
                self._limpar_highlights()

    # ══════════════════════════════════════════════════════════
    # EXECUÇÃO DE CARDS
    # ══════════════════════════════════════════════════════════

    def _confirmar_card(self, card: Card, col: int, linha: int):
        """Executa a carta no alvo selecionado."""
        cel = self.mundo.celula(col, linha)
        if not cel:
            return

        p = self.gerenciador.participante_ativo
        if not p or p.ap_atual < card.custo_ap:
            return
        p.gastar_ap(card.custo_ap)

        # Teste de perícia (d100)
        acerto = True
        if card.pericia:
            habilidade = self._habilidade_investigador(card.pericia)
            rolagem = random.randint(1, 100)
            if rolagem <= habilidade // 5:
                nivel = "CRÍTICO"; multiplicador = 2
            elif rolagem <= habilidade // 2:
                nivel = "EXTREMO"; multiplicador = 1
            elif rolagem <= habilidade:
                nivel = "SUCESSO"; multiplicador = 1
            elif rolagem >= 96:
                nivel = "FUMBLE"; acerto = False; multiplicador = 0
            else:
                nivel = "FALHA"; acerto = False; multiplicador = 0
            self._adicionar_log(f"{card.pericia}: {rolagem} vs {habilidade} → {nivel}")
        else:
            multiplicador = 1

        if not acerto:
            self._adicionar_log(f"❌ {card.nome} falhou!")
            self._pos_acao()
            return

        # Aplica efeitos
        ef = card.efeito

        # Dano
        if "dano" in ef and cel.ocupante and cel.ocupante is not self.jogador:
            dano = rolar_dado(ef["dano"]) * multiplicador
            real = cel.ocupante.sofrer_dano(dano)
            self._adicionar_log(f"⚔ {card.nome} → {cel.ocupante.nome}: {real} dano")
            if not cel.ocupante.vivo:
                self._adicionar_log(f"💀 {cel.ocupante.nome} foi derrotado!")
                cel.ocupante = None

        # Efeito de chão
        if "efeito_chao" in ef:
            raio = ef.get("raio_efeito", 0)
            efeito_enum = efeito_chao_para_enum(ef["efeito_chao"])
            if efeito_enum:
                if raio > 0:
                    for cc, ll in self.mundo.celulas_em_alcance(col, linha, raio):
                        cel_r = self.mundo.celula(cc, ll)
                        if cel_r:
                            cel_r.aplicar_efeito(efeito_enum, 3)
                else:
                    cel.aplicar_efeito(efeito_enum, 3)
                self._adicionar_log(f"🌍 {ef['efeito_chao']} aplicado em ({col},{linha})")

        # Força recuo
        if "forcar_recuo" in ef and cel.ocupante:
            self._aplicar_recuo(cel.ocupante, col, linha, ef["forcar_recuo"])

        self._pos_acao()

    def _executar_card_habilidade(self, card: Card):
        """Executa cards sem alvo de grid (defesa, buff, etc.)"""
        p = self.gerenciador.participante_ativo
        if not p or p.ap_atual < card.custo_ap:
            return
        p.gastar_ap(card.custo_ap)

        ef = card.efeito
        if "cura_hp" in ef:
            cura = rolar_dado(ef["cura_hp"])
            self.jogador.hp = min(self.jogador.hp_max, self.jogador.hp + cura)
            self._adicionar_log(f"💊 {card.nome}: +{cura} HP (agora {self.jogador.hp})")
        if "bonus_ap_prox" in ef:
            p.bonus_ap += ef["bonus_ap_prox"]
            self._adicionar_log(f"⏳ Esperar — +{ef['bonus_ap_prox']} AP no próximo turno")
        if "oculto" in ef:
            self._adicionar_log("🕵 Investigador se ocultou!")
        if "recarregar" in ef:
            self._adicionar_log("🔄 Arma recarregada.")

        self._pos_acao()

    def _habilidade_investigador(self, pericia: str) -> int:
        """Retorna valor de habilidade para a perícia — lê da ficha se disponível."""
        # 1) Tenta buscar da ficha real (carregada em jogador.pericias)
        pericias_ficha = getattr(self.jogador, "pericias", {})
        if pericia in pericias_ficha:
            return max(1, pericias_ficha[pericia])

        # 2) Mapeamento de aliases (nomes usados nas cartas → nomes da ficha)
        _alias = {
            "Briga":               "Lutar (Soco)",
            "Armas de Fogo (.38)": "Armas de Fogo (.38)",
            "Espingarda":          "Armas de Fogo (Espingarda)",
            "Rifle":               "Armas de Fogo (Rifle)",
            "Esquivar":            "Esquivar",
            "Furtividade":         "Furtividade",
            "Primeiros Socorros":  "Primeiros Socorros",
            "Medicina":            "Medicina",
            "Intimidação":         "Intimidação",
            "Arremessar":          "Arremessar",
        }
        nome_ficha = _alias.get(pericia, pericia)
        if nome_ficha in pericias_ficha:
            return max(1, pericias_ficha[nome_ficha])

        # 3) Fallback com valores mínimos padrão CoC
        _fallback = {
            "Briga":               25,
            "Armas de Fogo (.38)": 20,
            "Espingarda":          20,
            "Rifle":               25,
            "Esquivar":            int(getattr(self.jogador, "destreza", 50) / 2),
            "Furtividade":         20,
            "Primeiros Socorros":  30,
            "Medicina":            10,
            "Intimidação":         15,
            "Arremessar":          20,
        }
        return _fallback.get(pericia, 15)

    def _aplicar_recuo(self, ent: Entidade, col_atq: int, lin_atq: int, distancia: int):
        """Empurra entidade para longe do atacante."""
        dc = int(ent.col) - col_atq
        dl = int(ent.linha) - lin_atq
        if dc == 0 and dl == 0:
            return
        # Normaliza
        if dc != 0: dc = dc // abs(dc)
        if dl != 0: dl = dl // abs(dl)

        cel_atual = self.mundo.celula(int(ent.col), int(ent.linha))
        nova_cel  = self.mundo.celula(int(ent.col) + dc * distancia,
                                       int(ent.linha) + dl * distancia)
        if nova_cel and nova_cel.passavel:
            if cel_atual: cel_atual.ocupante = None
            ent.col   = nova_cel.col
            ent.linha = nova_cel.linha
            nova_cel.ocupante = ent
            self._adicionar_log(f"💥 Recuo: {ent.nome} → ({nova_cel.col},{nova_cel.linha})")

    def _pos_acao(self):
        """Após executar uma card: verifica AP e estado."""
        self._limpar_highlights()
        self._modo_ataque_card = None
        self.card_selecionado  = None

        # Verifica vitória/derrota
        inimigos_vivos = [e for e in self.inimigos if e.vivo]
        if not inimigos_vivos:
            self.gerenciador.estado = EstadoCombate.FIM_COMBATE
            self._adicionar_log("✅ Todos os inimigos foram derrotados!")
            return

        p = self.gerenciador.participante_ativo
        if p and p.ap_atual <= 0:
            self.gerenciador.proximo_turno()
        else:
            self.gerenciador.estado = EstadoCombate.TURNO_JOGADOR

    def _tentar_fuga(self):
        roll = random.randint(1, 100)
        hab = 40  # Esquivar base
        if roll <= hab:
            self._adicionar_log(f"🏃 Fuga bem-sucedida! ({roll} vs {hab})")
            self.resultado = "fuga"
            self.gerenciador.estado = EstadoCombate.FIM_COMBATE
        else:
            self._adicionar_log(f"❌ Fuga falhou! ({roll} vs {hab})")
            # Perde AP
            p = self.gerenciador.participante_ativo
            if p:
                p.ap_atual = 0
                self.gerenciador.proximo_turno()

    def _limpar_highlights(self):
        self.celulas_movimento = set()
        self.celulas_alcance   = set()
        self.gerenciador.celulas_highlight = []

    # ══════════════════════════════════════════════════════════
    # RESULTADO
    # ══════════════════════════════════════════════════════════

    def _determinar_resultado(self) -> str:
        if self.resultado == "fuga":
            return "fuga"
        if not self.jogador.vivo:
            return "derrota"
        return "vitoria"

    def _tela_resultado(self, resultado: str):
        cores = {
            "vitoria": (50, 200, 100),
            "derrota": (200, 50, 50),
            "fuga":    (200, 180, 80),
        }
        textos = {
            "vitoria": "VITÓRIA!",
            "derrota": "DERROTA...",
            "fuga":    "FUGIU!",
        }
        cor  = cores.get(resultado, (200, 200, 200))
        txt  = textos.get(resultado, resultado.upper())

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        surf = self.f_grande.render(txt, True, cor)
        r = surf.get_rect(center=(self.screen.get_width() // 2,
                                   self.screen.get_height() // 2))
        self.screen.blit(surf, r)

        sub = self.f_normal.render("Pressione qualquer tecla...", True, (180, 180, 180))
        rs = sub.get_rect(center=(self.screen.get_width() // 2,
                                   self.screen.get_height() // 2 + 50))
        self.screen.blit(sub, rs)
        pygame.display.flip()

        # Espera input
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.clock.tick(30)

    # ══════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self):
        self.screen.fill((10, 10, 15))

        # Clip na área do grid
        self.screen.set_clip(self.area_grid)

        # Todas as entidades (jogador + inimigos)
        todas = [self.jogador] + self.inimigos

        # Combina highlights do gerenciador legado com os do cards
        mov_hl = self.celulas_movimento | {
            (c, l) for c, l in self.gerenciador.celulas_highlight
            if self.gerenciador.acao_selecionada and
               self.gerenciador.acao_selecionada.tipo == TipoAcao.MOVER
        }
        atq_hl = self.celulas_alcance | {
            (c, l) for c, l in self.gerenciador.celulas_highlight
            if self.gerenciador.acao_selecionada and
               self.gerenciador.acao_selecionada.tipo == TipoAcao.ATACAR
        }

        p_ativo = self.gerenciador.participante_ativo
        ent_ativa = p_ativo.entidade if p_ativo else None

        self.renderer.desenhar(
            mundo=self.mundo,
            entidades=todas,
            celulas_movimento=mov_hl,
            celulas_alcance=atq_hl,
            cursor=self.cursor_grid,
            entidade_ativa=ent_ativa,
        )
        self.screen.set_clip(None)

        # Painel HUD
        self._desenhar_painel_hud()

        # Info do cursor
        self._desenhar_info_cursor()

        pygame.display.flip()

    def _desenhar_painel_hud(self):
        # Fundo do HUD
        pygame.draw.rect(self.screen, (20, 20, 30), self.area_hud)
        pygame.draw.line(self.screen, (60, 60, 90),
                         (self.area_hud.left, 0),
                         (self.area_hud.left, self.screen.get_height()), 2)

        p = self.gerenciador.participante_ativo
        ent_ativa = p.entidade if p else None

        # AP indicator
        if p:
            ap_txt = self.f_titulo.render(
                f"AP: {'●' * p.ap_atual}{'○' * (p.ap_maximo - p.ap_atual)}",
                True, (200, 200, 80)
            )
            self.screen.blit(ap_txt, (self.area_hud.left + 10, 10))

        self.renderer.desenhar_painel_hud(
            superficie=self.screen,
            x=self.area_hud.left,
            y=40,
            largura=self.LARGURA_HUD,
            entidade_ativa=ent_ativa,
            cards_disponiveis=self.deck,
            card_selecionado=self.card_selecionado,
            log_combate=self.log_combate,
            turno_num=self.gerenciador.turno_atual,
            font_titulo=self.f_titulo,
            font_normal=self.f_normal,
            deck_scroll=self.deck_scroll,
        )

        # Dica de controles
        dicas = ["[1-9] Carta  [F] Fuga", "[Enter] Esperar  [Esc] Cancelar"]
        for i, d in enumerate(dicas):
            s = self.f_normal.render(d, True, (100, 100, 130))
            self.screen.blit(s, (self.area_hud.left + 8,
                                  self.screen.get_height() - 40 + i * 18))

    def _desenhar_info_cursor(self):
        if not self.cursor_grid:
            return
        col, linha = self.cursor_grid
        cel = self.mundo.celula(col, linha)
        if not cel:
            return

        partes = [f"({col},{linha}) {cel.tipo.name}"]
        if cel.efeito.name != "NENHUM":
            partes.append(cel.efeito.name)
        if cel.ocupante:
            ent = cel.ocupante
            partes.append(f"| {ent.nome} HP:{ent.hp}")

        txt = self.f_normal.render("  ".join(partes), True, (200, 200, 180))
        self.screen.blit(txt, (8, self.screen.get_height() - 22))

    def _adicionar_log(self, msg: str):
        print(f"[Combate] {msg}")
        self.log_combate.append(msg)
        if len(self.log_combate) > 50:
            self.log_combate.pop(0)


# ══════════════════════════════════════════════════════════════
# FUNÇÃO DE CONVENIÊNCIA
# ══════════════════════════════════════════════════════════════

def iniciar_combate_rapido(
    screen: pygame.Surface,
    jogador: Jogador,
    inimigos: Optional[List[Entidade]] = None,
    mundo: Optional[Mundo] = None,
) -> str:
    """
    Atalho para iniciar combate com configuração padrão.
    Retorna 'vitoria', 'derrota' ou 'fuga'.
    """
    if inimigos is None:
        inimigos = [
            Inimigo("Cultista", col=8, linha=2),
            Inimigo("Cultista", col=8, linha=5),
        ]
    tela = TelaCombate(screen, jogador, inimigos, mundo)
    return tela.run()
