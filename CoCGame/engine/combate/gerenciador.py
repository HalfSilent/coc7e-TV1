"""
engine/combate/gerenciador.py — Máquina de estados do combate por turnos.

Funciona integrado ao loop de exploração — sem troca de cena.
O renderer continua o mesmo; apenas o input e o HUD mudam de modo.

Regras adaptadas de CoC 7e:
    AP por turno: Investigador = 3, Cultista = 2, Engendro = 2
    Mover 1 tile: 1 AP  (óleo = 2 AP)
    Ataque corpo: 2 AP
    Atirar:       2 AP  (+1 AP para recarregar)
    Usar item:    1 AP
    Esperar:      0 AP  → +1 AP no próximo turno (máx = maximo)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

from engine.mundo import Mundo, Cobertura, EfeitoAmbiental, TipoTile
from engine.entidade import Entidade, rolar_bonus_dano


# ══════════════════════════════════════════════════════════════
# ENUMS / TIPOS
# ══════════════════════════════════════════════════════════════

class EstadoCombate(Enum):
    FORA_DE_COMBATE  = auto()
    TURNO_JOGADOR    = auto()
    ESCOLHENDO_ALVO  = auto()   # cursor ativo, esperando clique no mapa
    TURNO_INIMIGO    = auto()
    FIM_COMBATE      = auto()


class TipoAcao(Enum):
    MOVER      = "Mover"
    ATACAR     = "Atacar"
    RECARREGAR = "Recarregar"
    USAR_ITEM  = "Usar Item"
    ESPERAR    = "Esperar"


@dataclass
class Acao:
    tipo:      TipoAcao
    custo_ap:  int
    alcance:   int = 1
    descricao: str = ""


# Ações disponíveis para o jogador
ACOES_PADRAO: List[Acao] = [
    Acao(TipoAcao.MOVER,      custo_ap=1, alcance=3,  descricao="Move até 3 tiles"),
    Acao(TipoAcao.ATACAR,     custo_ap=2, alcance=1,  descricao="Ataque corpo a corpo"),
    Acao(TipoAcao.RECARREGAR, custo_ap=1, alcance=0,  descricao="Recarrega arma"),
    Acao(TipoAcao.USAR_ITEM,  custo_ap=1, alcance=0,  descricao="Usa item"),
    Acao(TipoAcao.ESPERAR,    custo_ap=0, alcance=0,  descricao="Passa o turno"),
]


# ══════════════════════════════════════════════════════════════
# PARTICIPANTE
# ══════════════════════════════════════════════════════════════

@dataclass
class Participante:
    entidade:    Entidade
    ap_maximo:   int = 3
    ap_atual:    int = field(init=False)
    iniciativa:  int = 0
    bonus_ap:    int = 0   # AP extra acumulado de Esperar

    def __post_init__(self):
        self.ap_atual = self.ap_maximo

    @property
    def nome(self) -> str:
        return self.entidade.nome

    @property
    def vivo(self) -> bool:
        return self.entidade.vivo

    def resetar_turno(self):
        extra = min(self.bonus_ap, 1)          # máx +1 AP de Esperar
        self.ap_atual = min(self.ap_maximo + extra, self.ap_maximo + 1)
        self.bonus_ap = 0

    def gastar_ap(self, custo: int) -> bool:
        if self.ap_atual >= custo:
            self.ap_atual -= custo
            return True
        return False


# ══════════════════════════════════════════════════════════════
# GERENCIADOR DE COMBATE
# ══════════════════════════════════════════════════════════════

class GerenciadorCombate:
    """
    Controla o fluxo de combate por turnos.
    Integra-se ao loop de exploração via estado + callbacks.
    """

    def __init__(self, mundo: Mundo,
                 on_log: Optional[Callable[[str], None]] = None):
        self.mundo  = mundo
        self.estado = EstadoCombate.FORA_DE_COMBATE

        self.participantes:  List[Participante] = []
        self.turno_atual:    int  = 0
        self.idx_ativo:      int  = 0
        self.acao_selecionada: Optional[Acao] = None
        self.celulas_highlight: List[Tuple[int, int]] = []

        self._on_log = on_log or (lambda msg: print(f"[CoC] {msg}"))

    # ── Propriedades ──────────────────────────────────────────

    @property
    def em_combate(self) -> bool:
        return self.estado not in (EstadoCombate.FORA_DE_COMBATE,
                                   EstadoCombate.FIM_COMBATE)

    @property
    def participante_ativo(self) -> Optional[Participante]:
        if 0 <= self.idx_ativo < len(self.participantes):
            return self.participantes[self.idx_ativo]
        return None

    def log(self, msg: str):
        self._on_log(msg)

    # ── Iniciar / encerrar ────────────────────────────────────

    def iniciar_combate(self, jogador: Entidade, inimigos: List[Entidade]):
        self.participantes = []

        p_jogador = Participante(
            entidade=jogador,
            ap_maximo=3,
            iniciativa=random.randint(1, 20) + jogador.destreza // 10,
        )
        self.participantes.append(p_jogador)

        for ini in inimigos:
            ap = 2
            p = Participante(
                entidade=ini,
                ap_maximo=ap,
                iniciativa=random.randint(1, 20) + ini.destreza // 10,
            )
            self.participantes.append(p)

        # Ordena por iniciativa (maior age primeiro)
        self.participantes.sort(key=lambda p: p.iniciativa, reverse=True)

        self.turno_atual = 1
        self.idx_ativo   = 0
        self.log(f"⚔ Combate iniciado! Ordem: "
                 f"{', '.join(p.nome for p in self.participantes)}")
        self._iniciar_turno()

    def _iniciar_turno(self):
        p = self.participante_ativo
        if not p:
            return
        p.resetar_turno()
        self.log(f"Vez de {p.nome} — {p.ap_atual} AP")

        # Verifica se é turno do jogador (sempre o primeiro da lista)
        if self.participantes and p.entidade is self.participantes[0].entidade:
            self.estado = EstadoCombate.TURNO_JOGADOR
        else:
            self.estado = EstadoCombate.TURNO_INIMIGO

    # ── Ações do jogador ──────────────────────────────────────

    def selecionar_acao(self, acao: Acao):
        """Jogador escolheu uma ação — calcula e destaca células válidas."""
        p = self.participante_ativo
        if not p or self.estado != EstadoCombate.TURNO_JOGADOR:
            return
        if p.ap_atual < acao.custo_ap:
            self.log(f"AP insuficiente! ({p.ap_atual}/{acao.custo_ap})")
            return

        if acao.tipo == TipoAcao.ESPERAR:
            self._executar_esperar(p)
            return

        if acao.tipo in (TipoAcao.RECARREGAR, TipoAcao.USAR_ITEM):
            if p.gastar_ap(acao.custo_ap):
                self.log(f"{p.nome}: {acao.tipo.value}")
            return

        self.acao_selecionada   = acao
        self.estado             = EstadoCombate.ESCOLHENDO_ALVO
        ent = p.entidade
        self.celulas_highlight  = self.mundo.celulas_em_alcance(
            int(ent.col), int(ent.linha), acao.alcance,
            so_passaveis=(acao.tipo == TipoAcao.MOVER)
        )
        self.log(f"{acao.tipo.value} — selecione o alvo")

    def confirmar_alvo(self, col: int, linha: int) -> bool:
        """Jogador confirmou alvo no mapa. Retorna True se executado."""
        if (col, linha) not in self.celulas_highlight:
            self.log("Alvo inválido.")
            return False

        p   = self.participante_ativo
        acao = self.acao_selecionada
        if not p or not acao:
            return False
        if not p.gastar_ap(acao.custo_ap):
            return False

        cel = self.mundo.celula(col, linha)
        if cel:
            self._executar_acao(p, acao, cel)

        self.acao_selecionada   = None
        self.celulas_highlight  = []

        if p.ap_atual <= 0:
            self.proximo_turno()
        else:
            self.estado = EstadoCombate.TURNO_JOGADOR
        return True

    def cancelar_acao(self):
        self.acao_selecionada   = None
        self.celulas_highlight  = []
        self.estado = EstadoCombate.TURNO_JOGADOR

    def proximo_turno(self):
        """Avança para o próximo participante vivo."""
        # Remove mortos
        self.participantes = [p for p in self.participantes if p.vivo]
        if self._verificar_fim():
            return

        self.idx_ativo = (self.idx_ativo + 1) % len(self.participantes)
        if self.idx_ativo == 0:
            self.turno_atual += 1
            self.log(f"── Rodada {self.turno_atual} ──")
            logs = self.mundo.tick_turno()
            for l in logs:
                self.log(l)

        self._iniciar_turno()

        # Se for turno de inimigo, executa IA automaticamente
        if self.estado == EstadoCombate.TURNO_INIMIGO:
            self._ia_executar()

    # ── Execução de ações ─────────────────────────────────────

    def _executar_acao(self, p: Participante, acao: Acao, cel_alvo):
        ent = p.entidade
        if acao.tipo == TipoAcao.MOVER:
            self._mover(ent, cel_alvo)
        elif acao.tipo == TipoAcao.ATACAR:
            self._atacar(ent, cel_alvo)

    def _mover(self, ent: Entidade, cel_destino):
        # Libera célula anterior
        cel_ant = self.mundo.celula(int(ent.col), int(ent.linha))
        if cel_ant:
            cel_ant.ocupante = None

        # Efeito de óleo: possível escorregão
        if cel_destino.efeito == EfeitoAmbiental.OLEO:
            if random.random() < 0.40:
                self.log(f"💦 {ent.nome} escorregou no óleo!")
                # desliza 1 tile extra na mesma direção
                dc = cel_destino.col - int(ent.col)
                dl = cel_destino.linha - int(ent.linha)
                extra = self.mundo.celula(
                    cel_destino.col + dc,
                    cel_destino.linha + dl
                )
                if extra and not extra.bloqueada and extra.ocupante is None:
                    cel_destino = extra

        ent.col   = cel_destino.col
        ent.linha = cel_destino.linha
        cel_destino.ocupante = ent
        ent.movendo = True
        self.log(f"🚶 {ent.nome} → ({cel_destino.col},{cel_destino.linha})")

    def _atacar(self, atacante: Entidade, cel_alvo):
        if not cel_alvo.ocupante:
            self.log("Nenhum alvo na célula!")
            return

        alvo = cel_alvo.ocupante
        col_a, lin_a = int(atacante.col), int(atacante.linha)

        # Verifica cobertura
        cobertura = self.mundo.calcular_cobertura(
            (col_a, lin_a), (cel_alvo.col, cel_alvo.linha)
        )
        if cobertura == Cobertura.TOTAL:
            self.log(f"❌ {atacante.nome} não tem linha de visão!")
            return

        # Rolagem de ataque (CoC: d100 vs. Briga/Armas)
        habilidade = 50   # base Briga
        if cobertura == Cobertura.MEIA:
            habilidade -= 20
            self.log("Cobertura parcial: −20 na habilidade")

        rolagem = random.randint(1, 100)
        if rolagem <= habilidade // 5:
            resultado = "CRÍTICO"
        elif rolagem <= habilidade // 2:
            resultado = "EXTREMO"
        elif rolagem <= habilidade:
            resultado = "SUCESSO"
        elif rolagem >= 96:
            resultado = "FUMBLE"
        else:
            resultado = "FALHA"

        if resultado in ("FALHA", "FUMBLE"):
            self.log(f"💨 {atacante.nome} errou! ({rolagem} vs {habilidade})")
            return

        # Dano
        dano_base = random.randint(1, 6)   # 1d6 desarmado
        bd        = rolar_bonus_dano(atacante.bonus_dano)
        dano      = max(1, dano_base + bd)
        if resultado == "CRÍTICO":
            dano *= 2

        real = alvo.sofrer_dano(dano)
        self.log(
            f"⚔ {atacante.nome} → {alvo.nome}: "
            f"{real} dano [{resultado}] (HP: {alvo.hp}/{alvo.hp_max})"
        )

        if not alvo.vivo:
            self.log(f"💀 {alvo.nome} foi derrotado!")
            cel_alvo.ocupante = None

    def _executar_esperar(self, p: Participante):
        p.bonus_ap  += 1
        p.ap_atual   = 0
        self.log(f"⏳ {p.nome} espera — +1 AP no próximo turno")
        self.proximo_turno()

    # ── IA dos inimigos ───────────────────────────────────────

    def _ia_executar(self):
        """IA simples: move em direção ao jogador e ataca se adjacente."""
        p = self.participante_ativo
        if not p or not p.vivo:
            self.proximo_turno()
            return

        jogador_p = self.participantes[0]
        jogador   = jogador_p.entidade

        while p.ap_atual > 0:
            jc, jl = int(jogador.col), int(jogador.linha)
            ec, el = int(p.entidade.col), int(p.entidade.linha)
            dist   = abs(jc - ec) + abs(jl - el)

            if dist <= 1:
                # Ataca (custa 2 AP)
                if not p.gastar_ap(2):
                    break   # AP insuficiente para atacar — encerra turno
                cel = self.mundo.celula(jc, jl)
                if cel:
                    self._atacar(p.entidade, cel)
            else:
                # Move 1 passo em direção ao jogador
                dc = 0 if jc == ec else (1 if jc > ec else -1)
                dl = 0 if jl == el else (1 if jl > el else -1)
                # Preferência: mover só num eixo por vez (Manhattan)
                cel_h = self.mundo.celula(ec + dc, el)
                cel_v = self.mundo.celula(ec,      el + dl)

                destino = None
                if cel_h and cel_h.passavel:
                    destino = cel_h
                elif cel_v and cel_v.passavel:
                    destino = cel_v

                if destino and p.gastar_ap(1):
                    self._mover(p.entidade, destino)
                else:
                    break   # bloqueado

        self.proximo_turno()

    # ── Verificação de fim ────────────────────────────────────

    def _verificar_fim(self) -> bool:
        jogador_p = self.participantes[0] if self.participantes else None
        if not jogador_p or not jogador_p.vivo:
            self.estado = EstadoCombate.FIM_COMBATE
            self.log("💀 Investigador derrotado. Fim de combate.")
            return True

        inimigos_vivos = [p for p in self.participantes[1:] if p.vivo]
        if not inimigos_vivos:
            self.estado = EstadoCombate.FIM_COMBATE
            self.log("✅ Todos os inimigos foram derrotados!")
            return True

        return False
