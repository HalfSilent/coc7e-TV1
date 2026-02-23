"""
mundo/tela_mundo.py — Navegação TORN-style pelo mundo de Arkham.

Controla o fluxo completo de navegação entre locais:
  - Exibe TelaLocal (descrição + ações) do local atual
  - Processa resultado das ações (ir, masmorra, descanso, info)
  - Gerencia o estado do investigador (HP, SAN, dinheiro, hora)
  - Lança TelaMasmorra quando o jogador entra numa masmorra
  - Avança o tempo a cada viagem

Sistema de tempo:
  - Jogo começa às 10h
  - Cada viagem entre locais: +1 hora
  - Algumas ações consomem tempo (pesquisa: +2h, descanso: +8h)
  - Locais fecham à noite (biblioteca fecha às 20h)

Retorna quando o jogador sai do jogo:
  "menu" — voltou ao menu principal
"""
from __future__ import annotations

import sys
import random
from typing import Optional

import pygame

from engine.entidade import Jogador
from mundo.locais import LOCAIS, get_local, LOCAL_INICIAL
from mundo.tela_local import TelaLocal
from gerenciador_assets import get_font, garantir_fontes


# ══════════════════════════════════════════════════════════════
# ESTADO DO INVESTIGADOR
# ══════════════════════════════════════════════════════════════

class EstadoInvestigador:
    """Estado persistente do investigador ao longo da exploração de Arkham."""

    def __init__(self, jogador: Jogador):
        self.jogador   = jogador
        self.dinheiro  = 15
        self.hora      = 10    # começa às 10h
        self.dia       = 1
        self.local_id  = LOCAL_INICIAL
        self.inventario = []
        self.notas: list = []   # pistas coletadas
        self.arma_equipada = ""

    def avancar_tempo(self, horas: int = 1):
        self.hora += horas
        while self.hora >= 24:
            self.hora -= 24
            self.dia  += 1

    def hora_formatada(self) -> str:
        return f"{self.hora:02d}:00"

    def periodo(self) -> str:
        if 6  <= self.hora < 12: return "Manhã"
        if 12 <= self.hora < 18: return "Tarde"
        if 18 <= self.hora < 22: return "Noite"
        return "Madrugada"

    def descansar(self, horas: int = 8, custo: int = 1):
        """Descansa — restaura HP e SAN, avança tempo."""
        if self.dinheiro < custo:
            return False, "Dinheiro insuficiente."
        self.dinheiro -= custo
        hp_ganho  = min(5, self.jogador.hp_max - self.jogador.hp)
        san_ganho = min(3, self.jogador.san_max - self.jogador.sanidade)
        self.jogador.hp       = min(self.jogador.hp_max,  self.jogador.hp       + hp_ganho)
        self.jogador.sanidade = min(self.jogador.san_max, self.jogador.sanidade + san_ganho)
        self.avancar_tempo(horas)
        return True, f"Descansou {horas}h. +{hp_ganho} HP, +{san_ganho} SAN."

    def curar_hp(self, valor: int, custo: int = 0) -> tuple:
        if self.dinheiro < custo:
            return False, "Dinheiro insuficiente."
        self.dinheiro -= custo
        ganho = min(valor, self.jogador.hp_max - self.jogador.hp)
        self.jogador.hp = min(self.jogador.hp_max, self.jogador.hp + valor)
        self.avancar_tempo(1)
        return True, f"+{ganho} HP"

    def curar_san(self, valor: int, custo: int = 0) -> tuple:
        if self.dinheiro < custo:
            return False, "Dinheiro insuficiente."
        self.dinheiro -= custo
        ganho = min(valor, self.jogador.san_max - self.jogador.sanidade)
        self.jogador.sanidade = min(self.jogador.san_max, self.jogador.sanidade + valor)
        self.avancar_tempo(2)
        return True, f"+{ganho} SAN"


# ══════════════════════════════════════════════════════════════
# TELA DE MUNDO
# ══════════════════════════════════════════════════════════════

class TelaMundo:
    """
    Hub de navegação TORN-style entre locais de Arkham.
    
    Uso:
        resultado = TelaMundo(screen, jogador).run()
        # resultado = "menu"
    """

    def __init__(self, screen: pygame.Surface, jogador: Jogador):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.estado = EstadoInvestigador(jogador)

        garantir_fontes()
        self.f_titulo = get_font("titulo", 24)
        self.f_hud    = get_font("hud", 16)
        self.f_normal = get_font("narrativa", 18)

        # Mensagem de feedback (descanso, compra, etc.)
        self._feedback: Optional[str] = None
        self._feedback_timer = 0

        # Flag: acabou de sair de um grid — evita auto-explorar em loop
        self._veio_da_masmorra = False

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def run(self) -> str:
        """Loop de navegação. Retorna 'menu'."""
        while True:
            resultado = self._visitar_local(self.estado.local_id)
            if resultado == "menu":
                # Persiste estado antes de sair
                try:
                    from dados.investigador_loader import salvar_estado
                    salvar_estado(self.estado.jogador, self.estado)
                except Exception:
                    pass
                return "menu"

    # ══════════════════════════════════════════════════════════
    # VISITAR LOCAL
    # ══════════════════════════════════════════════════════════

    def _visitar_local(self, local_id: str) -> str:
        """Exibe TelaLocal e processa resultado. Retorna 'menu' se sair."""
        local = get_local(local_id)
        if not local:
            return "menu"

        self.estado.local_id = local_id

        # ── Auto-explorar ──────────────────────────────────────────
        # Se o local tem ação "explorar" e NÃO viemos de dentro do grid,
        # pula o TelaLocal e abre o grid diretamente.
        # Ao sair do grid (ESC), _veio_da_masmorra=True → mostra TelaLocal.
        if not self._veio_da_masmorra:
            acao_explorar = next(
                (a for a in local.acoes if a.tipo == "explorar"), None
            )
            if acao_explorar:
                from mundo.masmorras import get_masmorra as _gm
                _md = _gm(acao_explorar.destino)
                desc = _md.get("descricao", "") if _md else local.descricao
                return self._processar_resultado({
                    "tipo": "explorar",
                    "destino": acao_explorar.destino,
                    "descricao": desc,
                })

        self._veio_da_masmorra = False  # reset: próxima visita volta a auto-explorar
        # ── TelaLocal normal ───────────────────────────────────────
        tela = TelaLocal(self.screen, local_id)
        resultado = tela.run(
            hp=self.estado.jogador.hp,
            hp_max=self.estado.jogador.hp_max,
            sanidade=self.estado.jogador.sanidade,
            san_max=self.estado.jogador.san_max,
            dinheiro=self.estado.dinheiro,
            hora=self.estado.hora,
        )

        return self._processar_resultado(resultado)

    # ══════════════════════════════════════════════════════════
    # PROCESSAR RESULTADO DA AÇÃO
    # ══════════════════════════════════════════════════════════

    def _processar_resultado(self, resultado: dict) -> str:
        tipo = resultado.get("tipo", "sair")

        if tipo == "sair":
            return "menu"

        elif tipo == "ir":
            destino = resultado.get("destino", LOCAL_INICIAL)
            local_dest = get_local(destino)
            if not local_dest:
                return self.estado.local_id  # local inválido, fica onde está

            # Avança tempo
            self.estado.avancar_tempo(1)

            # Verifica se o local está fechado
            if (local_dest.hora_fechamento and
                    self.estado.hora >= local_dest.hora_fechamento):
                self._mostrar_fechado(local_dest)
                return self.estado.local_id

            self.estado.local_id = destino
            return destino   # entra no loop com novo local_id

        elif tipo == "masmorra":
            destino = resultado.get("destino", "")
            self._iniciar_masmorra(destino, resultado.get("descricao", ""))
            return self.estado.local_id   # volta ao mesmo local após masmorra

        elif tipo == "explorar":
            # Ação TORN → abre grid top-down do interior do local
            destino = resultado.get("destino", "")
            descricao = resultado.get("descricao", "")
            self._iniciar_masmorra(destino, descricao)
            return self.estado.local_id

        elif tipo == "descanso":
            custo = resultado.get("custo", 0)
            descricao = resultado.get("descricao", "")
            ok, msg = self.estado.descansar(custo=custo)
            self._exibir_feedback(msg if ok else f"Sem dinheiro! (precisa ${custo})")
            return self.estado.local_id

        elif tipo == "comprar":
            custo = resultado.get("custo", 0)
            item  = resultado.get("item", "")
            if self.estado.dinheiro >= custo:
                self.estado.dinheiro -= custo
                if item:
                    self.estado.inventario.append(item)
                self._exibir_feedback(f"Comprou: {resultado.get('descricao', item)}")
            else:
                self._exibir_feedback(f"Sem dinheiro! (precisa ${custo})")
            return self.estado.local_id

        return self.estado.local_id

    # ══════════════════════════════════════════════════════════
    # MASMORRA
    # ══════════════════════════════════════════════════════════

    def _iniciar_masmorra(self, masmorra_id: str, descricao_entrada: str = ""):
        """Lança TelaMasmorra e processa resultado."""
        # Mostra tela de transição
        if descricao_entrada:
            self._tela_transicao(descricao_entrada)

        from masmorra.tela_masmorra import TelaMasmorra
        from engine.mundo import Mundo
        from mundo.masmorras import get_masmorra

        masmorra_dados = get_masmorra(masmorra_id)
        mundo = Mundo(masmorra_dados["mapa"]) if masmorra_dados else None

        # Tema visual (para sprites) — usa "padrao" se não definido
        tema = masmorra_dados.get("tema", "padrao") if masmorra_dados else "padrao"

        # Objetos interativos do mapa (novo sistema)
        objetos_mapa = masmorra_dados.get("objetos") if masmorra_dados else None

        tela = TelaMasmorra(
            screen=self.screen,
            jogador=self.estado.jogador,
            mundo=mundo,
            inimigos=masmorra_dados.get("inimigos") if masmorra_dados else None,
            objetos=objetos_mapa,
            nome_local=masmorra_dados.get("nome", masmorra_id) if masmorra_dados else masmorra_id,
            tema=tema,
        )

        # Passa inventário e arma já equipados para a masmorra
        tela.arma_equipada = self.estado.arma_equipada
        tela.itens_inv     = list(self.estado.inventario)

        resultado = tela.run()
        # Ao sair do grid, mostra TelaLocal em vez de auto-explorar de novo
        self._veio_da_masmorra = True

        # Sincroniza HP/SAN de volta (o Jogador é o mesmo objeto, mas garante)
        # (os sistemas de combate já alteram jogador.hp/sanidade diretamente)

        # Atualiza inventário com itens coletados na masmorra
        if hasattr(tela, "itens_inv"):
            for item in tela.itens_inv:
                if item not in self.estado.inventario:
                    self.estado.inventario.append(item)
        if hasattr(tela, "arma_equipada") and tela.arma_equipada:
            self.estado.arma_equipada = tela.arma_equipada

        self.estado.avancar_tempo(2)  # masmorra consome 2h

        # Persiste HP/SAN no JSON após cada masmorra
        try:
            from dados.investigador_loader import salvar_estado
            salvar_estado(self.estado.jogador, self.estado)
        except Exception:
            pass

        if resultado == "derrota":
            self._tela_derrota()
        else:
            self._exibir_feedback(f"Voltou: {resultado}")

    # ══════════════════════════════════════════════════════════
    # TELAS AUXILIARES
    # ══════════════════════════════════════════════════════════

    def _tela_transicao(self, texto: str):
        """Exibe texto de transição por 2 segundos."""
        self.screen.fill((8, 8, 12))
        w, h = self.screen.get_size()
        import textwrap
        linhas = textwrap.wrap(texto, 70)
        y = h // 2 - len(linhas) * 12
        for linha in linhas:
            s = self.f_normal.render(linha, True, (180, 170, 150))
            r = s.get_rect(centerx=w // 2, top=y)
            self.screen.blit(s, r)
            y += 26
        pygame.display.flip()
        pygame.time.wait(2000)

    def _mostrar_fechado(self, local):
        """Mostra mensagem de local fechado."""
        self._exibir_feedback(f"{local.nome} está fechado à esta hora.")

    def _tela_derrota(self):
        """Tela de game over."""
        self.screen.fill((8, 0, 0))
        w, h = self.screen.get_size()
        s = get_font("titulo", 48).render("DERROTA", True, (200, 50, 50))
        r = s.get_rect(center=(w // 2, h // 2 - 30))
        self.screen.blit(s, r)
        sub = self.f_hud.render(
            f"O investigador foi derrotado no Dia {self.estado.dia}.",
            True, (160, 140, 140)
        )
        sr = sub.get_rect(center=(w // 2, h // 2 + 30))
        self.screen.blit(sub, sr)

        dica = self.f_hud.render("Pressione qualquer tecla...", True, (100, 100, 100))
        dr = dica.get_rect(center=(w // 2, h // 2 + 70))
        self.screen.blit(dica, dr)

        pygame.display.flip()
        self._esperar_tecla()

    def _exibir_feedback(self, msg: str):
        """Exibe feedback breve em overlay na tela."""
        print(f"[Mundo] {msg}")
        self._feedback = msg
        self._feedback_timer = 180  # frames

        # Renderiza por um momento
        self.screen.fill((10, 10, 15))
        w, h = self.screen.get_size()
        s = self.f_hud.render(msg, True, (200, 190, 150))
        r = s.get_rect(center=(w // 2, h // 2))
        self.screen.blit(s, r)
        pygame.display.flip()
        pygame.time.wait(1200)

    def _esperar_tecla(self):
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.clock.tick(30)
