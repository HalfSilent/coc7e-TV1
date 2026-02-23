"""
masmorra/tela_masmorra.py — Exploração de masmorra top-down em tempo real.

O jogador se move com WASD/setas em um grid 2D visto de cima.
Ao se aproximar de inimigos (raio de alerta), inicia combate por turno.

Características:
  - Movimento tile-a-tile com WASD
  - Detecção de inimigos próximos → dispara TelaCombate
  - Objetos interativos (portas, itens, notas) com [E]
  - Mini-mapa no canto superior direito
  - Saída da masmorra ao pisar em células de saída [SAIDA]
  - Névoa de guerra: só revela o que o jogador já visitou

Layout:
    ┌──────────────────────────┬──────────┐
    │                          │ Minimap  │
    │   MAPA EXPLORAÇÃO        ├──────────┤
    │   (top-down 2D)          │ Status   │
    │                          │ HP / SAN │
    └──────────────────────────┴──────────┘
    [dica de controles]
"""
from __future__ import annotations

import sys
import random
from typing import Dict, List, Optional, Set, Tuple

import pygame

from engine.mundo import Mundo, TipoTile, EfeitoAmbiental
from engine.entidade import Entidade, Jogador, Inimigo, Engendro
from combate.tela_combate import TelaCombate
from dialogo.tela_dialogo import TelaDialogo
from gerenciador_assets import get_font, garantir_fontes


# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

CELL         = 40          # pixels por célula (menor que no combate)
RAIO_ALERTA  = 4           # tiles — distância de detecção de inimigo
RAIO_VISAO   = 6           # tiles — névoa de guerra (raio de visão do jogador)
MINIMAP_CELL = 6           # pixels por célula no minimapa

# Cores do mapa
COR_BG          = (8, 8, 12)
COR_CHAO        = (50, 50, 60)
COR_CHAO_VISIT  = (55, 55, 68)
COR_PAREDE      = (25, 25, 32)
COR_PAREDE_V    = (35, 35, 48)
COR_ELEVADO     = (70, 65, 55)
COR_FOG         = (8, 8, 12, 245)       # névoa não visitada (quase opaco)
COR_SEMIVISTO   = (8, 8, 12, 120)       # fora da visão mas visitado

COR_BORDA       = (30, 30, 42)
COR_JOGADOR     = (212, 168, 67)
COR_INIMIGO     = (200, 60, 60)
COR_ENGENDRO    = (140, 60, 200)
COR_SAIDA       = (60, 200, 80)
COR_OBJETO      = (200, 180, 100)

# Efeitos ambientais (overlay)
EFEITO_CORES = {
    EfeitoAmbiental.FOGO:       (220, 80,   0, 140),
    EfeitoAmbiental.OLEO:       (40,  30,   5, 100),
    EfeitoAmbiental.NEVOA:      (180, 180, 200, 90),
    EfeitoAmbiental.ARBUSTO:    (30,  100,  20, 110),
    EfeitoAmbiental.SANGUE:     (140,  10,  10, 100),
    EfeitoAmbiental.AGUA_BENTA: (50,  150, 255, 80),
}

# Mapa padrão (fallback)
MAPA_MASMORRA_PADRAO = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 1, 2, 1, 1, 2, 2, 2, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 1, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 2],
    [2, 1, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]
# Tile 4 = SAIDA (tratado como CHAO + marcador especial)


# ══════════════════════════════════════════════════════════════
# OBJETO INTERATIVO
# ══════════════════════════════════════════════════════════════

class ObjetoMasmorra:
    """Objeto que o jogador pode interagir com [E]."""

    def __init__(self, col: int, linha: int, tipo: str,
                 nome: str, descricao: str,
                 item_concedido: Optional[str] = None):
        self.col  = col
        self.linha = linha
        self.tipo  = tipo   # "nota" | "item" | "porta" | "armadilha"
        self.nome  = nome
        self.descricao = descricao
        self.item_concedido = item_concedido
        self.usado = False

    def interagir(self) -> str:
        """Retorna texto descritivo da interação."""
        if self.usado:
            return f"[{self.nome}] já foi examinado."
        self.usado = True
        return self.descricao


# ══════════════════════════════════════════════════════════════
# TELA DE MASMORRA
# ══════════════════════════════════════════════════════════════

class TelaMasmorra:
    """
    Exploração de masmorra top-down em tempo real.
    
    Retorna: "saiu" | "derrota" | "voltou_mundo"
    """

    def __init__(
        self,
        screen: pygame.Surface,
        jogador: Jogador,
        mundo: Optional[Mundo] = None,
        inimigos: Optional[List[Entidade]] = None,
        objetos: Optional[List[ObjetoMasmorra]] = None,
        saidas_especiais: Optional[Dict[Tuple[int, int], str]] = None,
        nome_local: str = "Masmorra",
    ):
        self.screen   = screen
        self.jogador  = jogador
        self.clock    = pygame.time.Clock()
        self.nome_local = nome_local

        # Mundo
        if mundo:
            self.mundo = mundo
        else:
            self.mundo = self._mundo_do_mapa(MAPA_MASMORRA_PADRAO)

        # Inimigos e objetos
        self.inimigos: List[Entidade] = inimigos or self._inimigos_padrao()
        self.objetos:  List[ObjetoMasmorra] = objetos or self._objetos_padrao()

        # Saídas especiais: (col, linha) → destino string
        self.saidas_especiais = saidas_especiais or {}

        # Névoa de guerra
        self.visitado: Set[Tuple[int, int]] = set()
        self.visivel:  Set[Tuple[int, int]] = set()

        # Mensagens flutuantes (feedback ao jogador)
        self.mensagens: List[Tuple[str, int]] = []   # (texto, frames restantes)

        # Posiciona jogador
        self._posicionar_jogador()
        self._atualizar_visibilidade()

        # Fontes
        garantir_fontes()
        self.f_hud    = get_font("hud", 16)
        self.f_titulo = get_font("titulo", 20)
        self.f_normal = get_font("hud", 14)

        # Câmera (centraliza no jogador)
        self.cam_x = 0
        self.cam_y = 0

        # Resultado de retorno
        self.resultado = "em_jogo"
        self.destino_saida = ""

        # Arma/itens do jogador (para passar ao combate)
        self.arma_equipada = ""
        self.itens_inv: List[str] = []

    # ── Helpers de inicialização ──────────────────────────────

    def _mundo_do_mapa(self, mapa_raw: List[List[int]]) -> Mundo:
        """Converte mapa raw (com tile 4=saída) para Mundo."""
        mapa_limpo = [[v if v != 4 else 1 for v in row] for row in mapa_raw]
        mundo = Mundo(mapa_limpo)
        # Marca saídas
        for l, row in enumerate(mapa_raw):
            for c, v in enumerate(row):
                if v == 4:
                    cel = mundo.celula(c, l)
                    if cel:
                        cel.tipo = TipoTile.CHAO  # passável
                        self.saidas_especiais = getattr(self, "saidas_especiais", {})
                        self.saidas_especiais[(c, l)] = "saida_principal"
        return mundo

    def _posicionar_jogador(self):
        for l in range(self.mundo.linhas):
            for c in range(self.mundo.colunas):
                cel = self.mundo.celula(c, l)
                if cel and cel.passavel:
                    self.jogador.col   = c
                    self.jogador.linha = l
                    cel.ocupante = self.jogador
                    return

    def _inimigos_padrao(self) -> List[Entidade]:
        return [
            Inimigo("Cultista",  col=10, linha=3),
            Inimigo("Cultista",  col=12, linha=7),
            Engendro("Engendro", col=13, linha=9),
        ]

    def _objetos_padrao(self) -> List[ObjetoMasmorra]:
        return [
            ObjetoMasmorra(3, 2, "nota", "Diário Amarelado",
                           "Páginas manchadas de sangue. Fala de 'O Portal abaixo das pedras...'"),
            ObjetoMasmorra(7, 6, "item", "Revólver .38",
                           "Um revólver enferrujado. Ainda tem 3 balas.",
                           item_concedido="revolver"),
            ObjetoMasmorra(9, 9, "item", "Kit Médico",
                           "Bandagens e morfina. Pode salvar uma vida.",
                           item_concedido="primeiros_socorros"),
        ]

    # ══════════════════════════════════════════════════════════
    # NÉVOA DE GUERRA
    # ══════════════════════════════════════════════════════════

    def _atualizar_visibilidade(self):
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        self.visivel = set()
        for dl in range(-RAIO_VISAO, RAIO_VISAO + 1):
            for dc in range(-RAIO_VISAO, RAIO_VISAO + 1):
                if abs(dc) + abs(dl) <= RAIO_VISAO:
                    tc, tl = jc + dc, jl + dl
                    if 0 <= tc < self.mundo.colunas and 0 <= tl < self.mundo.linhas:
                        self.visivel.add((tc, tl))
                        self.visitado.add((tc, tl))

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def run(self) -> str:
        """Loop de exploração. Retorna 'saiu', 'derrota' ou 'voltou_mundo'."""
        while True:
            dt = self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._processar_evento(event)

            if self.resultado != "em_jogo":
                return self.resultado

            self._atualizar(dt)
            self._renderizar()

    # ══════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════

    def _processar_evento(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP):
                self._mover_jogador(0, -1)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self._mover_jogador(0, 1)
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                self._mover_jogador(-1, 0)
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                self._mover_jogador(1, 0)
            elif event.key == pygame.K_e:
                self._interagir()
            elif event.key == pygame.K_ESCAPE:
                self.resultado = "voltou_mundo"
            elif event.key == pygame.K_TAB:
                # Toggle minimapa grande — por implementar
                pass

    def _mover_jogador(self, dc: int, dl: int):
        nc = int(self.jogador.col) + dc
        nl = int(self.jogador.linha) + dl
        cel = self.mundo.celula(nc, nl)
        if not cel or cel.bloqueada:
            return

        # Libera célula atual
        cel_ant = self.mundo.celula(int(self.jogador.col), int(self.jogador.linha))
        if cel_ant:
            cel_ant.ocupante = None

        self.jogador.col   = nc
        self.jogador.linha = nl
        cel.ocupante = self.jogador

        self._atualizar_visibilidade()

        # Efeito de chão na nova posição
        if cel.efeito == EfeitoAmbiental.FOGO:
            dano = random.randint(1, 4)
            self.jogador.sofrer_dano(dano)
            self._msg(f"🔥 Fogo! -{dano} HP")
        elif cel.efeito == EfeitoAmbiental.SANGUE:
            self.jogador.perder_sanidade(1)
            self._msg("😱 -1 SAN")

        # Checa saída
        pos = (nc, nl)
        if pos in self.saidas_especiais:
            self.destino_saida = self.saidas_especiais[pos]
            self._msg("Saída encontrada! [Continuando...]")
            pygame.time.wait(800)
            self.resultado = "saiu"
            return

        # Checa inimigo próximo
        self._verificar_encontro()

    def _verificar_encontro(self):
        """Verifica se algum inimigo está próximo o suficiente para iniciar combate."""
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        inimigos_proximos = []
        for ent in self.inimigos:
            if not ent.vivo:
                continue
            dist = abs(int(ent.col) - jc) + abs(int(ent.linha) - jl)
            if dist <= RAIO_ALERTA:
                inimigos_proximos.append(ent)

        if inimigos_proximos:
            self._iniciar_combate(inimigos_proximos)

    def _iniciar_combate(self, inimigos_proximos: List[Entidade]):
        """
        Pausa exploração e decide o caminho do encontro.

        Fluxo:
          1. Se TODOS os inimigos próximos são humanos → abre TelaDialogo primeiro.
             - "ignorou"  → encontro resolvido sem briga.
             - "fugiu"    → NPC líder removido; restantes também recuam.
             - "combate"  → segue para TelaCombate normalmente.
             - "combate_furioso" → NPC líder fica enraivecido (+Força) antes do combate.
          2. Se há qualquer Engendro/sobrenatural → vai direto ao TelaCombate
             (engendros sempre causam perda de SAN ao avistamento).
        """
        # ── Sanidade ao avistar engendros ────────────────────
        for ent in inimigos_proximos:
            if hasattr(ent, "perda_san_avistamento"):
                self.jogador.perder_sanidade(ent.perda_san_avistamento)
                self._msg(f"😱 Visão perturbadora! -{ent.perda_san_avistamento} SAN")

        # ── Separa humanos de sobrenaturais ──────────────────
        humanos       = [e for e in inimigos_proximos
                         if getattr(e, "tipo", "humano") == "humano"]
        sobrenaturais = [e for e in inimigos_proximos
                         if getattr(e, "tipo", "humano") != "humano"]

        # ── Diálogo somente se APENAS humanos no encontro ────
        if humanos and not sobrenaturais:
            lider = humanos[0]
            nomes = ", ".join(e.nome for e in humanos)
            self._msg(f"👁 Avistou: {nomes}")
            self._renderizar()
            pygame.time.wait(300)

            resultado_dialogo = TelaDialogo(
                self.screen, self.jogador, lider,
                contexto=f"No corredor escuro: {self.nome_local}.",
            ).run()

            # Restaura bg (a tela de diálogo faz snapshot)
            self._renderizar()

            if resultado_dialogo == "ignorou":
                self._msg(f"✓ {lider.nome} deixou você passar.")
                # Remove todos os humanos do encontro (eles se dispersam)
                self.inimigos = [e for e in self.inimigos if e not in humanos]
                return

            if resultado_dialogo == "fugiu":
                self._msg(f"✓ {lider.nome} correu! Os outros também recuam.")
                # Remove o líder; os outros ficam (mas afastados — mais fácil)
                self.inimigos = [e for e in self.inimigos if e is not lider]
                # Reduz inimigos restantes ao HP pela metade (estão em pânico)
                for e in humanos[1:]:
                    e.hp = max(1, e.hp // 2)
                # Se não sobrou ninguém no grupo, encerra
                restantes = [e for e in humanos if e in self.inimigos and e.vivo]
                if not restantes:
                    return
                inimigos_proximos = restantes  # combate só com os restantes (em pânico)

            elif resultado_dialogo == "combate_furioso":
                # NPC líder enraivecido: +15 Força
                lider.forca = min(99, lider.forca + 15)
                lider.ia_alerta = True
                self._msg(f"⚠ {lider.nome} está em FÚRIA! (+Força)")

        nomes = ", ".join(e.nome for e in inimigos_proximos)
        self._msg(f"⚔ Combate: {nomes}!")
        self._renderizar()
        pygame.time.wait(400)

        mundo_combate = self._criar_mundo_combate(inimigos_proximos)

        resultado = TelaCombate(
            screen=self.screen,
            jogador=self.jogador,
            inimigos=inimigos_proximos,
            mundo=mundo_combate,
            arma_equipada=self.arma_equipada,
            itens_inv=self.itens_inv,
            pericias=getattr(self.jogador, "pericias", {}),
        ).run()

        # Remove inimigos derrotados
        self.inimigos = [e for e in self.inimigos if e.vivo]

        if resultado == "derrota":
            self.resultado = "derrota"
            return

        # Reposiciona jogador após combate
        self._posicionar_jogador_pos_combate()
        self._msg(f"Combate encerrado: {resultado}")

    def _criar_mundo_combate(self, inimigos: List[Entidade]) -> Mundo:
        """
        Extrai uma subárea do mapa ao redor do jogador para usar no combate.
        Se o mapa for pequeno o suficiente, usa ele completo.
        """
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        raio = 6  # tiles de raio para o grid de combate

        c_min = max(0, jc - raio)
        l_min = max(0, jl - raio)
        c_max = min(self.mundo.colunas - 1, jc + raio)
        l_max = min(self.mundo.linhas - 1, jl + raio)

        # Extrai subgrid
        subgrid = []
        for l in range(l_min, l_max + 1):
            row = []
            for c in range(c_min, c_max + 1):
                cel = self.mundo.celula(c, l)
                row.append(cel.tipo.value if cel else 2)
            subgrid.append(row)

        mundo_combate = Mundo(subgrid)

        # Copia efeitos ambientais
        for l in range(l_min, l_max + 1):
            for c in range(c_min, c_max + 1):
                cel_orig = self.mundo.celula(c, l)
                cel_dest = mundo_combate.celula(c - c_min, l - l_min)
                if cel_orig and cel_dest and cel_orig.efeito.name != "NENHUM":
                    cel_dest.aplicar_efeito(cel_orig.efeito, cel_orig.duracao_efeito)

        # Ajusta posições das entidades para o subgrid
        self.jogador.col   -= c_min
        self.jogador.linha -= l_min
        for ent in inimigos:
            ent.col   -= c_min
            ent.linha -= l_min

        return mundo_combate

    def _posicionar_jogador_pos_combate(self):
        """Reposiciona jogador em célula válida após combate."""
        for l in range(self.mundo.linhas):
            for c in range(self.mundo.colunas):
                cel = self.mundo.celula(c, l)
                if cel and cel.passavel:
                    self.jogador.col   = c
                    self.jogador.linha = l
                    cel.ocupante = self.jogador
                    self._atualizar_visibilidade()
                    return

    def _interagir(self):
        """Interage com objeto adjacente ou na mesma célula."""
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        for obj in self.objetos:
            dist = abs(obj.col - jc) + abs(obj.linha - jl)
            if dist <= 1 and not obj.usado:
                texto = obj.interagir()
                self._msg(texto)
                if obj.item_concedido:
                    self.itens_inv.append(obj.item_concedido)
                    if obj.item_concedido in ("revolver", "espingarda", "rifle", "faca"):
                        self.arma_equipada = obj.item_concedido
                    self._msg(f"+ {obj.item_concedido} adicionado ao inventário")
                return
        self._msg("Nada por aqui...")

    # ══════════════════════════════════════════════════════════
    # UPDATE
    # ══════════════════════════════════════════════════════════

    def _atualizar(self, dt: int):
        # Decrementa mensagens
        self.mensagens = [(t, f - 1) for t, f in self.mensagens if f > 1]

        # Câmera: centraliza no jogador
        w, h = self.screen.get_size()
        self.cam_x = int(self.jogador.col) * CELL - w // 2 + CELL // 2
        self.cam_y = int(self.jogador.linha) * CELL - h // 2 + CELL // 2

        # Verifica morte
        if not self.jogador.vivo:
            self.resultado = "derrota"

    # ══════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self):
        self.screen.fill(COR_BG)
        self._desenhar_mapa()
        self._desenhar_objetos()
        self._desenhar_inimigos()
        self._desenhar_jogador()
        self._desenhar_fog()
        self._desenhar_hud()
        self._desenhar_minimap()
        self._desenhar_mensagens()
        pygame.display.flip()

    def _px(self, col: int, linha: int) -> Tuple[int, int]:
        return (col * CELL - self.cam_x, linha * CELL - self.cam_y)

    def _desenhar_mapa(self):
        w, h = self.screen.get_size()
        for l in range(self.mundo.linhas):
            for c in range(self.mundo.colunas):
                cel = self.mundo.celula(c, l)
                if not cel:
                    continue

                visitada = (c, l) in self.visitado
                visivel  = (c, l) in self.visivel

                if not visitada and not visivel:
                    continue  # completamente na névoa

                x, y = self._px(c, l)
                if x + CELL < 0 or x > w or y + CELL < 0 or y > h:
                    continue  # fora da tela

                # Cor base
                if cel.tipo == TipoTile.PAREDE:
                    cor = COR_PAREDE_V if visivel else COR_PAREDE
                elif cel.tipo == TipoTile.ELEVADO:
                    cor = COR_ELEVADO
                else:
                    cor = COR_CHAO_VISIT if visivel else COR_CHAO

                # Saída especial
                if (c, l) in self.saidas_especiais:
                    cor = COR_SAIDA

                r = pygame.Rect(x, y, CELL, CELL)
                pygame.draw.rect(self.screen, cor, r)
                pygame.draw.rect(self.screen, COR_BORDA, r, 1)

                # Efeito ambiental (só se visível)
                if visivel and cel.efeito.name != "NENHUM":
                    ef_cor = EFEITO_CORES.get(cel.efeito)
                    if ef_cor:
                        ov = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                        ov.fill(ef_cor)
                        self.screen.blit(ov, (x, y))

    def _desenhar_fog(self):
        """Overlay de névoa sobre células não visíveis."""
        w, h = self.screen.get_size()
        fog = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        fog_semi = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        fog.fill(COR_FOG)
        fog_semi.fill(COR_SEMIVISTO)

        for l in range(self.mundo.linhas):
            for c in range(self.mundo.colunas):
                x, y = self._px(c, l)
                if x + CELL < 0 or x > w or y + CELL < 0 or y > h:
                    continue
                if (c, l) in self.visivel:
                    continue
                elif (c, l) in self.visitado:
                    self.screen.blit(fog_semi, (x, y))
                else:
                    self.screen.blit(fog, (x, y))

    def _desenhar_objetos(self):
        for obj in self.objetos:
            if obj.usado:
                continue
            if (obj.col, obj.linha) not in self.visivel:
                continue
            x, y = self._px(obj.col, obj.linha)
            cx, cy = x + CELL // 2, y + CELL // 2
            pygame.draw.rect(self.screen, COR_OBJETO,
                             (x + 8, y + 8, CELL - 16, CELL - 16),
                             border_radius=3)
            icone = {"nota": "N", "item": "I", "porta": "P", "armadilha": "!"}.get(obj.tipo, "?")
            s = self.f_normal.render(icone, True, (30, 30, 30))
            sr = s.get_rect(center=(cx, cy))
            self.screen.blit(s, sr)

    def _desenhar_inimigos(self):
        for ent in self.inimigos:
            if not ent.vivo:
                continue
            if (int(ent.col), int(ent.linha)) not in self.visivel:
                continue
            x, y = self._px(int(ent.col), int(ent.linha))
            cx, cy = x + CELL // 2, y + CELL // 2
            cor = COR_ENGENDRO if hasattr(ent, "perda_san_avistamento") else COR_INIMIGO
            pygame.draw.circle(self.screen, cor, (cx, cy), CELL // 2 - 4)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), CELL // 2 - 4, 2)
            s = self.f_normal.render(ent.nome[0], True, (255, 255, 255))
            sr = s.get_rect(center=(cx, cy))
            self.screen.blit(s, sr)

    def _desenhar_jogador(self):
        x, y = self._px(int(self.jogador.col), int(self.jogador.linha))
        cx, cy = x + CELL // 2, y + CELL // 2
        pygame.draw.circle(self.screen, COR_JOGADOR, (cx, cy), CELL // 2 - 3)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), CELL // 2 - 3, 2)
        s = self.f_normal.render(self.jogador.nome[0], True, (30, 30, 30))
        sr = s.get_rect(center=(cx, cy))
        self.screen.blit(s, sr)

    def _desenhar_hud(self):
        w, _ = self.screen.get_size()

        # Barra de fundo
        pygame.draw.rect(self.screen, (15, 15, 22), (0, 0, w, 36))

        # Nome do local
        nm = self.f_titulo.render(self.nome_local, True, (180, 160, 120))
        self.screen.blit(nm, (10, 8))

        # HP
        hp_txt = self.f_hud.render(
            f"HP: {self.jogador.hp}/{self.jogador.hp_max}", True,
            (80, 220, 80) if self.jogador.hp > self.jogador.hp_max * 0.5
            else (220, 80, 80)
        )
        self.screen.blit(hp_txt, (w // 2 - 100, 8))

        # SAN
        san_txt = self.f_hud.render(
            f"SAN: {self.jogador.sanidade}/{self.jogador.san_max}", True,
            (100, 160, 220) if self.jogador.sanidade > 20 else (180, 80, 220)
        )
        self.screen.blit(san_txt, (w // 2 + 20, 8))

        # Dicas
        dica = self.f_normal.render(
            "[WASD] Mover  [E] Interagir  [ESC] Voltar",
            True, (80, 80, 100)
        )
        _, sh = self.screen.get_size()
        self.screen.blit(dica, (10, sh - 20))

    def _desenhar_minimap(self):
        w, _ = self.screen.get_size()
        mm_w = self.mundo.colunas * MINIMAP_CELL
        mm_h = self.mundo.linhas  * MINIMAP_CELL
        mm_x = w - mm_w - 8
        mm_y = 44

        # Fundo
        pygame.draw.rect(self.screen, (10, 10, 18),
                         (mm_x - 2, mm_y - 2, mm_w + 4, mm_h + 4))

        for l in range(self.mundo.linhas):
            for c in range(self.mundo.colunas):
                if (c, l) not in self.visitado:
                    continue
                cel = self.mundo.celula(c, l)
                if not cel:
                    continue
                x = mm_x + c * MINIMAP_CELL
                y = mm_y + l * MINIMAP_CELL

                if (c, l) in self.saidas_especiais:
                    cor = COR_SAIDA
                elif cel.tipo == TipoTile.PAREDE:
                    cor = (30, 30, 45)
                else:
                    cor = (60, 60, 75) if (c, l) in self.visivel else (40, 40, 55)

                pygame.draw.rect(self.screen, cor,
                                 (x, y, MINIMAP_CELL - 1, MINIMAP_CELL - 1))

        # Jogador no minimapa
        jx = mm_x + int(self.jogador.col) * MINIMAP_CELL
        jy = mm_y + int(self.jogador.linha) * MINIMAP_CELL
        pygame.draw.rect(self.screen, COR_JOGADOR,
                         (jx, jy, MINIMAP_CELL, MINIMAP_CELL))

        # Inimigos no minimapa (apenas visitados)
        for ent in self.inimigos:
            if not ent.vivo:
                continue
            if (int(ent.col), int(ent.linha)) in self.visitado:
                ex = mm_x + int(ent.col) * MINIMAP_CELL
                ey = mm_y + int(ent.linha) * MINIMAP_CELL
                pygame.draw.rect(self.screen, COR_INIMIGO,
                                 (ex, ey, MINIMAP_CELL, MINIMAP_CELL))

        # Borda
        pygame.draw.rect(self.screen, (60, 60, 90),
                         (mm_x - 2, mm_y - 2, mm_w + 4, mm_h + 4), 1)

    def _desenhar_mensagens(self):
        _, sh = self.screen.get_size()
        y = sh - 45
        for txt, frames in reversed(self.mensagens[-4:]):
            alpha = min(255, frames * 5)
            s = self.f_hud.render(txt, True, (220, 200, 150))
            s.set_alpha(alpha)
            self.screen.blit(s, (10, y))
            y -= 20

    def _msg(self, texto: str, duracao: int = 120):
        print(f"[Masmorra] {texto}")
        self.mensagens.append((texto, duracao))
