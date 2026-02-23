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
from engine.grid.tiles import TileLoader
from engine.grid.objeto import ObjetoMasmorra, OpcaoMenu
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


# ObjetoMasmorra e OpcaoMenu agora vivem em engine/grid/objeto.py
# (importados acima — mantidos aqui para retrocompatibilidade via import *)


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
        tema: str = "padrao",
    ):
        self.screen   = screen
        self.jogador  = jogador
        self.clock    = pygame.time.Clock()
        self.nome_local = nome_local

        # Sprite tile loader (DENZI + Kenney assets)
        self.tiles = TileLoader(tema=tema, cell=CELL)

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

        # CoC 7e: combate acontece no mesmo espaço — sem teleporte para arena separada
        resultado = TelaCombate(
            screen=self.screen,
            jogador=self.jogador,
            inimigos=inimigos_proximos,
            mundo=self.mundo,         # mesmo mapa de exploração
            arma_equipada=self.arma_equipada,
            itens_inv=self.itens_inv,
            pericias=getattr(self.jogador, "pericias", {}),
            manter_posicoes=True,     # preserva posições reais das entidades
        ).run()

        # Remove inimigos derrotados
        self.inimigos = [e for e in self.inimigos if e.vivo]

        if resultado == "derrota":
            self.resultado = "derrota"
            return

        # Jogador permanece onde estava — sem reposicionamento
        self._atualizar_visibilidade()
        self._msg(f"Combate encerrado: {resultado}")

    def _interagir(self):
        """Interage com objeto adjacente ou na mesma célula."""
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        for obj in self.objetos:
            dist = abs(obj.col - jc) + abs(obj.linha - jl)
            if dist <= 1 and not obj.usado:
                if obj.tem_menu:
                    self._menu_interativo(obj)
                else:
                    # Modo legado
                    texto = obj.interagir_simples()
                    self._msg(texto)
                    if obj.item_concedido:
                        self._conceder_item(obj.item_concedido)
                return
        self._msg("Nada por aqui...")

    def _conceder_item(self, item: str):
        """Adiciona item ao inventário e equipa arma se for uma."""
        self.itens_inv.append(item)
        armas = ("revolver", "espingarda", "rifle", "faca",
                 "cacete", "facada", "estilete")
        if item in armas and not self.arma_equipada:
            self.arma_equipada = item
        self._msg(f"+ {item} adicionado ao inventário")

    # ══════════════════════════════════════════════════════════
    # MENU DE INTERAÇÃO [E]
    # ══════════════════════════════════════════════════════════

    def _menu_interativo(self, obj: ObjetoMasmorra):
        """
        Exibe popup de opções para um ObjetoMasmorra com opcoes_menu.
        Processa rolagem de perícia e concede pistas/itens.
        """
        import textwrap
        w, h = self.screen.get_size()

        # Layout do popup
        PW, PH  = min(640, w - 60), min(440, h - 80)
        PX = (w - PW) // 2
        PY = (h - PH) // 2
        CBORDA  = (120, 100,  70)
        CBG     = ( 12,  10,  20, 230)
        CTIT    = (212, 180, 100)
        CDESC   = (160, 155, 145)
        COPCAO  = (140, 140, 165)
        CHOPCAO = (220, 200, 140)
        CESC    = ( 80,  80,  95)

        # Mapeamento tecla → OpcaoMenu
        mapa_teclas = {op.tecla.upper(): op for op in obj.opcoes_menu}
        resultado_texto: list[str] = []
        fase = "escolha"   # "escolha" | "resultado"

        while True:
            # Renderiza o jogo ao fundo (sem flip — o flip ocorre ao final do loop)
            self._desenhar_cena()

            # Overlay semitransparente
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            self.screen.blit(ov, (0, 0))

            # Painel principal
            panel = pygame.Surface((PW, PH), pygame.SRCALPHA)
            panel.fill(CBG)
            pygame.draw.rect(panel, CBORDA, (0, 0, PW, PH), 2, border_radius=6)
            self.screen.blit(panel, (PX, PY))

            # ── Título
            ty = PY + 16
            ts = self.f_titulo.render(obj.nome, True, CTIT)
            self.screen.blit(ts, ts.get_rect(centerx=w // 2, top=ty))
            ty += ts.get_height() + 6

            # ── Descrição (quebra de linha)
            for linha_desc in textwrap.wrap(obj.descricao, 62):
                ds = self.f_normal.render(linha_desc, True, CDESC)
                self.screen.blit(ds, ds.get_rect(centerx=w // 2, top=ty))
                ty += ds.get_height() + 2
            ty += 10

            if fase == "escolha":
                # ── Separador
                pygame.draw.line(self.screen, CBORDA,
                                 (PX + 20, ty), (PX + PW - 20, ty), 1)
                ty += 12

                # ── Opções
                for op in obj.opcoes_menu:
                    pericia_info = ""
                    if op.pericia:
                        val = getattr(self.jogador, "pericias", {}).get(op.pericia, 0)
                        pericia_info = f"  [{op.pericia.capitalize()} {val}%]"
                    linha_op = f"[{op.tecla.upper()}] {op.texto}{pericia_info}"
                    os_s = self.f_hud.render(linha_op, True, COPCAO)
                    self.screen.blit(os_s, os_s.get_rect(centerx=w // 2, top=ty))
                    ty += os_s.get_height() + 8

                ty += 6
                esc_s = self.f_normal.render("[ESC] Fechar", True, CESC)
                self.screen.blit(esc_s, esc_s.get_rect(centerx=w // 2, top=ty))

            else:  # fase == "resultado"
                # ── Texto de resultado
                for linha_r in resultado_texto:
                    rs = self.f_normal.render(linha_r, True, CHOPCAO)
                    self.screen.blit(rs, rs.get_rect(centerx=w // 2, top=ty))
                    ty += rs.get_height() + 4
                ty += 10
                cont_s = self.f_normal.render("[Enter / ESC] Continuar", True, CESC)
                self.screen.blit(cont_s, cont_s.get_rect(centerx=w // 2, top=ty))

            pygame.display.flip()

            # ── Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit()

                if event.type == pygame.KEYDOWN:
                    if fase == "resultado":
                        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                         pygame.K_KP_ENTER, pygame.K_SPACE):
                            return   # fecha menu

                    elif fase == "escolha":
                        if event.key == pygame.K_ESCAPE:
                            return   # fecha sem ação

                        char = pygame.key.name(event.key).upper()
                        if char in mapa_teclas:
                            op = mapa_teclas[char]
                            resultado_texto = self._executar_opcao(obj, op)
                            fase = "resultado"

            self.clock.tick(60)

    def _executar_opcao(self, obj: ObjetoMasmorra,
                        op: OpcaoMenu) -> list[str]:
        """
        Executa a opção escolhida no menu interativo.
        Retorna lista de linhas de texto para exibir como resultado.
        """
        import random
        linhas: list[str] = []

        sucesso = True
        if op.pericia and not op.sem_check:
            val = getattr(self.jogador, "pericias", {}).get(op.pericia, 0)
            rola = random.randint(1, 100)
            if op.dificuldade == "dificil":
                limite = val // 2
            elif op.dificuldade == "extremo":
                limite = val // 5
            else:
                limite = val

            if rola <= limite:
                nivel = "Extremo!" if rola <= val // 5 else \
                        "Difícil!" if rola <= val // 2 else "Sucesso"
                sucesso = True
                linhas.append(f"Rolagem: {rola} / {limite}  →  {nivel}")
            else:
                sucesso = False
                linhas.append(f"Rolagem: {rola} / {limite}  →  Falhou")
            linhas.append("")

        if sucesso:
            if op.pista:
                linhas.append("[PISTA]")
                import textwrap
                for p in textwrap.wrap(op.pista, 55):
                    linhas.append(p)
                # Registra pista no jogador (se tiver atributo)
                if hasattr(self.jogador, "pistas"):
                    self.jogador.pistas.append(op.pista)
                self._msg(f"[Pista] {op.pista[:50]}..." if len(op.pista) > 50 else f"[Pista] {op.pista}")

            if op.item:
                linhas.append("")
                linhas.append(f"+ Item obtido: {op.item}")
                self._conceder_item(op.item)
        else:
            linhas.append("Você não encontrou nada útil.")

        # Objetos com menu podem ser consultados múltiplas vezes (não marca como usado)
        # a menos que o tipo seja "item" (objeto físico que some após pegar)
        if obj.tipo == "item" and sucesso and op.item:
            obj.usado = True

        return linhas

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

    def _desenhar_cena(self):
        """Renderiza tudo na tela SEM chamar display.flip() — usado por submenus/popups."""
        self.screen.fill(COR_BG)
        self._desenhar_mapa()
        self._desenhar_objetos()
        self._desenhar_inimigos()
        self._desenhar_jogador()
        self._desenhar_fog()
        self._desenhar_hud()
        self._desenhar_minimap()
        self._desenhar_mensagens()

    def _renderizar(self):
        self._desenhar_cena()
        pygame.display.flip()

    def _px(self, col: int, linha: int) -> Tuple[int, int]:
        return (col * CELL - self.cam_x, linha * CELL - self.cam_y)

    def _desenhar_mapa(self):
        w, h = self.screen.get_size()
        usar_sprites = self.tiles.tem_sprites()

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

                r = pygame.Rect(x, y, CELL, CELL)

                if usar_sprites and visivel:
                    # ── Modo sprite ──────────────────────────
                    if cel.tipo == TipoTile.PAREDE:
                        spr = self.tiles.get_wall(c, l)
                    elif cel.tipo == TipoTile.ELEVADO:
                        # ELEVADO = objeto bloqueante (estante, caixa…)
                        # desenha floor embaixo + objeto por cima
                        floor_spr = self.tiles.get_floor(c, l)
                        if floor_spr:
                            self.screen.blit(floor_spr, (x, y))
                        spr = self.tiles.get_objeto(c, l)
                    elif (c, l) in self.saidas_especiais:
                        spr = self.tiles.get_saida() or self.tiles.get_floor(c, l)
                    else:
                        spr = self.tiles.get_floor(c, l)

                    if spr:
                        self.screen.blit(spr, (x, y))
                        # Borda sutil para legibilidade do grid
                        pygame.draw.rect(self.screen, (0, 0, 0, 60), r, 1)
                    else:
                        # Fallback para rect se sprite não carregou
                        self._desenhar_tile_rect(r, cel, c, l, visivel)

                elif usar_sprites and visitada:
                    # Visitado mas fora da visão → rect escuro (sem sprite)
                    cor = COR_PAREDE if cel.tipo == TipoTile.PAREDE else COR_CHAO
                    pygame.draw.rect(self.screen, cor, r)
                    pygame.draw.rect(self.screen, COR_BORDA, r, 1)

                else:
                    # ── Modo rect (fallback ou não-visível) ──
                    self._desenhar_tile_rect(r, cel, c, l, visivel)

                # Efeito ambiental overlay (sempre, se visível)
                if visivel and cel.efeito.name != "NENHUM":
                    ef_cor = EFEITO_CORES.get(cel.efeito)
                    if ef_cor:
                        ov = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                        ov.fill(ef_cor)
                        self.screen.blit(ov, (x, y))

    def _desenhar_tile_rect(self, r: pygame.Rect, cel, c: int, l: int, visivel: bool):
        """Renderiza tile como retângulo colorido (fallback)."""
        if cel.tipo == TipoTile.PAREDE:
            cor = COR_PAREDE_V if visivel else COR_PAREDE
        elif cel.tipo == TipoTile.ELEVADO:
            cor = COR_ELEVADO
        else:
            cor = COR_CHAO_VISIT if visivel else COR_CHAO
        if (c, l) in self.saidas_especiais:
            cor = COR_SAIDA
        pygame.draw.rect(self.screen, cor, r)
        pygame.draw.rect(self.screen, COR_BORDA, r, 1)

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
        jc, jl = int(self.jogador.col), int(self.jogador.linha)
        for obj in self.objetos:
            if obj.usado:
                continue
            if (obj.col, obj.linha) not in self.visivel:
                continue
            x, y = self._px(obj.col, obj.linha)
            cx, cy = x + CELL // 2, y + CELL // 2

            # Sprite do objeto (se disponível e não for tile ELEVADO que já foi desenhado)
            cel = self.mundo.celula(obj.col, obj.linha)
            if cel and cel.tipo != TipoTile.ELEVADO:
                # Objeto solto no chão — desenha ícone colorido
                pygame.draw.rect(self.screen, COR_OBJETO,
                                 (x + 8, y + 8, CELL - 16, CELL - 16),
                                 border_radius=3)
                icone = {"nota": "N", "item": "I", "porta": "P",
                         "armadilha": "!", "estante": "L",
                         "arquivo": "A", "altar": "*"}.get(obj.tipo, "?")
                s = self.f_normal.render(icone, True, (30, 30, 30))
                self.screen.blit(s, s.get_rect(center=(cx, cy)))

            # Prompt [E] quando jogador está adjacente
            dist = abs(obj.col - jc) + abs(obj.linha - jl)
            if dist <= 1:
                prompt = self.f_normal.render("[E]", True, (255, 230, 100))
                self.screen.blit(prompt, (x + 2, y + 2))

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
