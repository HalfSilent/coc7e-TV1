"""
engine/combate/gerenciador.py — Sistema de combate CoC 7e fiel ao livro.

Sistema: Movimento + Acao Principal + Reacao
============================================================
  TURNO DO PERSONAGEM:
    - Movimento livre: ate MOV tiles (gratis, a qualquer momento do turno)
    - Acao Principal: 1x por turno — Atacar | Recarregar | Usar Item | Conjurar
    - Sem acao: pode "Passar" (equivale a Esperar)

  NA VEZ DO INIMIGO (quando o jogador e atacado):
    - Reacao automatica — popup pede escolha:
        [E] Esquivar     -> teste resistido Esquivar vs Lutar do atacante
        [C] Contra-atacar -> teste resistido Lutar vs Lutar
        [N] Absorver     -> recebe dano sem resistencia

  Ordem de turno: DES decrescente (desempate: pericia de combate mais alta)
  Dano desarmado: 1D3 + bonus_dano
  Dano extremo (Extremo/Critico): dano maximo + 1 rolagem extra

Referencia: CoC 7e Livro Basico, Capitulo 6, pp. 100-125
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
    FORA_DE_COMBATE      = auto()
    TURNO_JOGADOR        = auto()    # jogador pode mover e/ou agir
    ESCOLHENDO_ALVO      = auto()    # cursor ativo, esperando clique no mapa
    ESCOLHENDO_MOVIMENTO = auto()    # cursor de movimento ativo
    AGUARDANDO_REACAO    = auto()    # jogador sendo atacado — escolhe reacao
    TURNO_INIMIGO        = auto()
    FIM_COMBATE          = auto()


class TipoAcao(Enum):
    MOVER      = "Mover"
    ATACAR     = "Atacar"
    RECARREGAR = "Recarregar"
    USAR_ITEM  = "Usar Item"
    ESPERAR    = "Esperar"


class TipoReacao(Enum):
    ESQUIVAR      = "Esquivar"
    CONTRA_ATACAR = "Contra-atacar"
    ABSORVER      = "Absorver"


@dataclass
class Acao:
    tipo:      TipoAcao
    custo_ap:  int = 0      # mantido para compat com cards existentes
    alcance:   int = 1
    descricao: str = ""


# Acoes basicas disponiveis ao jogador
ACOES_PADRAO: List[Acao] = [
    Acao(TipoAcao.MOVER,      custo_ap=0, alcance=4,  descricao="Move ate MOV tiles"),
    Acao(TipoAcao.ATACAR,     custo_ap=0, alcance=1,  descricao="Ataque corpo a corpo"),
    Acao(TipoAcao.RECARREGAR, custo_ap=0, alcance=0,  descricao="Recarrega arma"),
    Acao(TipoAcao.USAR_ITEM,  custo_ap=0, alcance=0,  descricao="Usa item do inventario"),
    Acao(TipoAcao.ESPERAR,    custo_ap=0, alcance=0,  descricao="Passa o turno"),
]


# ══════════════════════════════════════════════════════════════
# PARTICIPANTE
# ══════════════════════════════════════════════════════════════

@dataclass
class Participante:
    entidade:    Entidade
    ap_maximo:   int = 1       # sempre 1 acao principal por turno
    ap_atual:    int = field(init=False)
    iniciativa:  int = 0

    # Slots de turno CoC 7e
    ja_agiu:           bool = False   # usou a Acao Principal
    reacao_disponivel: bool = True    # usavel 1x por turno, na vez do inimigo
    mov_restante:      int  = 0       # tiles de movimento restantes

    def __post_init__(self):
        self.ap_atual = self.ap_maximo

    @property
    def nome(self) -> str:
        return self.entidade.nome

    @property
    def vivo(self) -> bool:
        return self.entidade.vivo

    def resetar_turno(self):
        self.ap_atual          = self.ap_maximo
        self.ja_agiu           = False
        self.reacao_disponivel = True
        self.mov_restante      = getattr(self.entidade, "movimento", 4)

    def gastar_ap(self, custo: int) -> bool:
        """Mantido para compatibilidade com cards existentes."""
        if self.ap_atual >= custo:
            self.ap_atual -= custo
            return True
        return False


# ══════════════════════════════════════════════════════════════
# GERENCIADOR DE COMBATE
# ══════════════════════════════════════════════════════════════

class GerenciadorCombate:
    """
    Controla o fluxo de combate por turnos (CoC 7e fiel).

    Sistema: 1 Acao Principal + Movimento livre + Reacao automatica.
    O on_pedir_reacao e chamado quando o jogador e atacado;
    a tela deve chamar resolver_reacao(TipoReacao) para continuar.
    """

    def __init__(self, mundo: Mundo,
                 on_log: Optional[Callable[[str], None]] = None,
                 on_pedir_reacao: Optional[Callable[[], None]] = None):
        self.mundo  = mundo
        self.estado = EstadoCombate.FORA_DE_COMBATE

        self.participantes:     List[Participante]    = []
        self.turno_atual:       int                   = 0
        self.idx_ativo:         int                   = 0
        self.acao_selecionada:  Optional[Acao]        = None
        self.celulas_highlight: List[Tuple[int, int]] = []

        # Callbacks
        self._on_log          = on_log or (lambda msg: print(f"[CoC] {msg}"))
        # on_pedir_reacao: chamado quando jogador e atacado (estado => AGUARDANDO_REACAO)
        # A tela deve mostrar o popup e chamar self.resolver_reacao(escolha)
        self._on_pedir_reacao = on_pedir_reacao

        # Estado interno de reacao pendente
        self._reacao_pendente: Optional[dict] = None

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

    @property
    def participante_jogador(self) -> Optional[Participante]:
        """Sempre o primeiro participante (o jogador)."""
        return self.participantes[0] if self.participantes else None

    def log(self, msg: str):
        self._on_log(msg)

    # ── Iniciar ───────────────────────────────────────────────

    def iniciar_combate(self, jogador: Entidade, inimigos: List[Entidade]):
        self.participantes = []

        p_jogador = Participante(
            entidade=jogador,
            ap_maximo=1,
            iniciativa=jogador.destreza,
        )
        p_jogador.mov_restante = getattr(jogador, "movimento", 4)
        self.participantes.append(p_jogador)

        for ini in inimigos:
            p = Participante(
                entidade=ini,
                ap_maximo=1,
                # Pequena variacao para desempate
                iniciativa=ini.destreza + random.randint(-5, 5),
            )
            p.mov_restante = getattr(ini, "movimento", 3)
            self.participantes.append(p)

        # Ordena por DES decrescente (CoC 7e p.103)
        self.participantes.sort(key=lambda p: p.iniciativa, reverse=True)

        self.turno_atual = 1
        self.idx_ativo   = 0
        self.log("Combate! Ordem: " +
                 ", ".join(f"{p.nome}(DES:{p.iniciativa})" for p in self.participantes))
        self._iniciar_turno()

    def _iniciar_turno(self):
        p = self.participante_ativo
        if not p:
            return
        p.resetar_turno()

        eh_jogador = (p.entidade is self.participantes[0].entidade)
        if eh_jogador:
            self.estado = EstadoCombate.TURNO_JOGADOR
            self.log(f"Seu turno | MOV:{p.mov_restante} | Acao: disponivel")
        else:
            self.estado = EstadoCombate.TURNO_INIMIGO
            self._ia_executar()

    # ══════════════════════════════════════════════════════════
    # ACOES DO JOGADOR
    # ══════════════════════════════════════════════════════════

    def selecionar_acao(self, acao: Acao):
        """Compatibilidade legada — redireciona para os novos metodos."""
        if acao.tipo == TipoAcao.MOVER:
            self.iniciar_movimento()
        elif acao.tipo == TipoAcao.ATACAR:
            self.iniciar_ataque(acao.alcance)
        elif acao.tipo == TipoAcao.ESPERAR:
            self.passar_turno()
        else:
            self.usar_acao_secundaria(acao.tipo)

    def iniciar_movimento(self):
        """Jogador quer mover — calcula tiles alcancaveis."""
        p = self.participante_ativo
        if not p or self.estado != EstadoCombate.TURNO_JOGADOR:
            return
        if p.mov_restante <= 0:
            self.log("Sem movimento restante!")
            return
        ent = p.entidade
        self.celulas_highlight = self.mundo.celulas_em_alcance(
            int(ent.col), int(ent.linha), p.mov_restante, so_passaveis=True
        )
        self.acao_selecionada = Acao(TipoAcao.MOVER, alcance=p.mov_restante)
        self.estado = EstadoCombate.ESCOLHENDO_MOVIMENTO
        self.log(f"Mover — escolha o destino (ate {p.mov_restante} tiles)")

    def iniciar_ataque(self, alcance: int = 1):
        """Jogador quer atacar — calcula celulas com inimigos no alcance."""
        p = self.participante_ativo
        if not p or self.estado != EstadoCombate.TURNO_JOGADOR:
            return
        if p.ja_agiu:
            self.log("Acao principal ja usada neste turno!")
            return
        ent = p.entidade
        todas = self.mundo.celulas_em_alcance(int(ent.col), int(ent.linha), alcance)
        self.celulas_highlight = [
            (c, l) for c, l in todas
            if self.mundo.celula(c, l) and
               self.mundo.celula(c, l).ocupante is not None and
               self.mundo.celula(c, l).ocupante is not ent
        ]
        self.acao_selecionada = Acao(TipoAcao.ATACAR, alcance=alcance)
        self.estado = EstadoCombate.ESCOLHENDO_ALVO
        self.log("Atacar — escolha o alvo")

    def confirmar_alvo(self, col: int, linha: int) -> bool:
        """Jogador clicou em alvo. Retorna True se executado."""
        p = self.participante_ativo
        if not p:
            return False

        # Movimento
        if self.estado == EstadoCombate.ESCOLHENDO_MOVIMENTO:
            if (col, linha) not in self.celulas_highlight:
                self.log("Destino invalido.")
                return False
            cel = self.mundo.celula(col, linha)
            if cel:
                distancia = (abs(col - int(p.entidade.col)) +
                             abs(linha - int(p.entidade.linha)))
                self._mover(p.entidade, cel)
                p.mov_restante = max(0, p.mov_restante - distancia)
            self.acao_selecionada  = None
            self.celulas_highlight = []
            self.estado = EstadoCombate.TURNO_JOGADOR
            return True

        # Ataque
        if self.estado == EstadoCombate.ESCOLHENDO_ALVO:
            if (col, linha) not in self.celulas_highlight:
                self.log("Alvo invalido.")
                return False
            cel = self.mundo.celula(col, linha)
            if cel:
                p.ja_agiu = True
                # Desconta 1 AP (compat legada)
                if p.ap_atual > 0:
                    p.ap_atual -= 1
                self._atacar(p.entidade, cel)
            self.acao_selecionada  = None
            self.celulas_highlight = []
            # Nao muda estado aqui — pode ter disparado AGUARDANDO_REACAO
            if self.estado == EstadoCombate.ESCOLHENDO_ALVO:
                self.estado = EstadoCombate.TURNO_JOGADOR
            return True

        return False

    def usar_acao_secundaria(self, tipo: TipoAcao):
        """Recarregar, Usar Item — nao gasta a Acao Principal."""
        p = self.participante_ativo
        if not p or self.estado != EstadoCombate.TURNO_JOGADOR:
            return
        self.log(f"{p.nome}: {tipo.value}")

    def passar_turno(self):
        """Jogador passa o turno."""
        self.acao_selecionada  = None
        self.celulas_highlight = []
        self.estado = EstadoCombate.TURNO_JOGADOR
        self.proximo_turno()

    def cancelar_acao(self):
        self.acao_selecionada  = None
        self.celulas_highlight = []
        self.estado = EstadoCombate.TURNO_JOGADOR

    # ══════════════════════════════════════════════════════════
    # REACAO DO JOGADOR
    # ══════════════════════════════════════════════════════════

    def resolver_reacao(self, tipo: TipoReacao):
        """
        Chamado pela tela quando o jogador escolhe sua reacao.
        Resolve o teste resistido CoC 7e e aplica o resultado.
        """
        dados = self._reacao_pendente
        if not dados:
            return
        self._reacao_pendente = None

        atacante   = dados["atacante"]
        cel_alvo   = dados["cel_alvo"]
        hab_ataque = dados["habilidade"]
        dano_expr  = dados["dano_expr"]
        bonus_dano = dados["bonus_dano"]

        pj      = self.participante_jogador
        jogador = pj.entidade if pj else None
        if not jogador:
            return

        rol_ataque = random.randint(1, 100)
        nivel_atq  = _nivel_sucesso(rol_ataque, hab_ataque)

        if tipo == TipoReacao.ABSORVER or (pj and not pj.reacao_disponivel):
            # Recebe dano sem resistencia
            if nivel_atq in ("SUCESSO", "EXTREMO", "CRITICO"):
                dano = _rolar_dano_coc(dano_expr, bonus_dano, nivel_atq)
                real = jogador.sofrer_dano(dano)
                self.log(f"{atacante.nome} ataca: {rol_ataque} vs {hab_ataque} "
                         f"[{nivel_atq}] -> {real} dano (HP:{jogador.hp}/{jogador.hp_max})")
            else:
                self.log(f"{atacante.nome} errou! ({rol_ataque} vs {hab_ataque})")

        elif tipo == TipoReacao.ESQUIVAR:
            if pj:
                pj.reacao_disponivel = False
            hab_esq = getattr(jogador, "esquivar",
                              getattr(jogador, "destreza", 50) // 2)
            # Tenta ler de pericias
            pericias = getattr(jogador, "pericias", {})
            hab_esq = pericias.get("Esquivar", hab_esq)
            rol_esq = random.randint(1, 100)
            nivel_esq = _nivel_sucesso(rol_esq, hab_esq)
            self.log(f"Esquivar: {rol_esq} vs {hab_esq} [{nivel_esq}] | "
                     f"Ataque: {rol_ataque} vs {hab_ataque} [{nivel_atq}]")
            # Defensor vence empate ao esquivar (CoC 7e p.107)
            if _comparar_nivel(nivel_esq, nivel_atq) >= 0:
                self.log("Esquivou com sucesso!")
            else:
                dano = _rolar_dano_coc(dano_expr, bonus_dano, nivel_atq)
                real = jogador.sofrer_dano(dano)
                self.log(f"Nao conseguiu esquivar -> {real} dano "
                         f"(HP:{jogador.hp}/{jogador.hp_max})")

        elif tipo == TipoReacao.CONTRA_ATACAR:
            if pj:
                pj.reacao_disponivel = False
            pericias  = getattr(jogador, "pericias", {})
            hab_briga = pericias.get("Lutar (Soco)",
                        pericias.get("Briga", 25))
            rol_def   = random.randint(1, 100)
            nivel_def = _nivel_sucesso(rol_def, hab_briga)
            self.log(f"Contra-ataque: {rol_def} vs {hab_briga} [{nivel_def}] | "
                     f"Ataque: {rol_ataque} vs {hab_ataque} [{nivel_atq}]")
            cmp = _comparar_nivel(nivel_def, nivel_atq)
            if cmp > 0:
                # Defensor ganhou — causa dano no atacante
                dano_ca = _rolar_dano_coc("1d3", rolar_bonus_dano(jogador.bonus_dano), nivel_def)
                real = atacante.sofrer_dano(dano_ca)
                self.log(f"Contra-ataque acertou! {atacante.nome} sofre {real} dano")
                if not atacante.vivo:
                    self.log(f"{atacante.nome} foi derrotado pelo contra-ataque!")
                    cel_atk = self.mundo.celula(int(atacante.col), int(atacante.linha))
                    if cel_atk:
                        cel_atk.ocupante = None
            elif cmp == 0:
                # Empate — atacante ganha (regra CoC p.107)
                dano = _rolar_dano_coc(dano_expr, bonus_dano, nivel_atq)
                real = jogador.sofrer_dano(dano)
                self.log(f"Empate (atacante ganha) -> {real} dano "
                         f"(HP:{jogador.hp}/{jogador.hp_max})")
            else:
                dano = _rolar_dano_coc(dano_expr, bonus_dano, nivel_atq)
                real = jogador.sofrer_dano(dano)
                self.log(f"Contra-ataque falhou -> {real} dano "
                         f"(HP:{jogador.hp}/{jogador.hp_max})")

        # Verifica se jogador morreu
        if jogador and not jogador.vivo:
            self.log("Investigador caiu!")

        self._verificar_fim()

        # Continua o turno do inimigo apos a reacao
        if self.estado not in (EstadoCombate.FIM_COMBATE,):
            self.estado = EstadoCombate.TURNO_INIMIGO
            self._ia_continuar()

    # ══════════════════════════════════════════════════════════
    # MOVIMENTACAO E ATAQUE INTERNOS
    # ══════════════════════════════════════════════════════════

    def _mover(self, ent: Entidade, cel_destino):
        cel_ant = self.mundo.celula(int(ent.col), int(ent.linha))
        if cel_ant:
            cel_ant.ocupante = None

        # Efeito de oleo: possivel escorregao
        if cel_destino.efeito == EfeitoAmbiental.OLEO:
            if random.random() < 0.35:
                self.log(f"{ent.nome} escorregou no oleo!")
                dc = cel_destino.col - int(ent.col)
                dl = cel_destino.linha - int(ent.linha)
                extra = self.mundo.celula(cel_destino.col + dc,
                                          cel_destino.linha + dl)
                if extra and not extra.bloqueada and extra.ocupante is None:
                    cel_destino = extra

        ent.col   = cel_destino.col
        ent.linha = cel_destino.linha
        cel_destino.ocupante = ent
        ent.movendo = True
        self.log(f"{ent.nome} -> ({cel_destino.col},{cel_destino.linha})")

    def _atacar(self, atacante: Entidade, cel_alvo,
                habilidade: int = 50, dano_expr: str = "1d3"):
        """
        Inicia um ataque. Se o alvo for o jogador, dispara a reacao.
        Caso contrario, resolve o ataque direto.
        """
        if not cel_alvo.ocupante:
            self.log("Nenhum alvo na celula!")
            return False

        alvo   = cel_alvo.ocupante
        col_a  = int(atacante.col)
        lin_a  = int(atacante.linha)
        bd     = rolar_bonus_dano(atacante.bonus_dano)

        # Verifica cobertura
        cobertura = self.mundo.calcular_cobertura(
            (col_a, lin_a), (cel_alvo.col, cel_alvo.linha)
        )
        if cobertura == Cobertura.TOTAL:
            self.log(f"{atacante.nome} sem linha de visao!")
            return False
        if cobertura == Cobertura.MEIA:
            habilidade = max(1, habilidade - 20)
            self.log("Cobertura parcial: -20 na habilidade")

        # Se alvo e o jogador, dispara popup de reacao
        pj = self.participante_jogador
        if pj and alvo is pj.entidade:
            self._reacao_pendente = {
                "atacante":   atacante,
                "cel_alvo":   cel_alvo,
                "habilidade": habilidade,
                "dano_expr":  dano_expr,
                "bonus_dano": bd,
            }
            self.estado = EstadoCombate.AGUARDANDO_REACAO
            if self._on_pedir_reacao:
                self._on_pedir_reacao()   # tela exibe popup
            else:
                self.resolver_reacao(TipoReacao.ABSORVER)
            return True

        # Alvo nao e o jogador — resolve diretamente
        rol    = random.randint(1, 100)
        nivel  = _nivel_sucesso(rol, habilidade)
        self.log(f"{atacante.nome} ataca {alvo.nome}: {rol} vs {habilidade} [{nivel}]")

        if nivel in ("FALHA", "FUMBLE"):
            self.log(f"{atacante.nome} errou!")
            return True

        dano = _rolar_dano_coc(dano_expr, bd, nivel)
        real = alvo.sofrer_dano(dano)
        self.log(f"  -> {real} dano (HP:{alvo.hp}/{alvo.hp_max})")
        if not alvo.vivo:
            self.log(f"{alvo.nome} foi derrotado!")
            cel_alvo.ocupante = None
        return True

    # ══════════════════════════════════════════════════════════
    # IA DOS INIMIGOS
    # ══════════════════════════════════════════════════════════

    _ia_fase: str = "mover"   # "mover" | "atacar" | "fim"

    def _ia_executar(self):
        """Inicia o turno do inimigo ativo."""
        self._ia_fase = "mover"
        self._ia_continuar()

    def _ia_continuar(self):
        """Continua IA — chamado tambem apos reacao do jogador ser resolvida."""
        p = self.participante_ativo
        if not p or not p.vivo:
            self.proximo_turno()
            return

        pj      = self.participante_jogador
        jogador = pj.entidade if pj else None
        if not jogador:
            self.proximo_turno()
            return

        jc, jl = int(jogador.col), int(jogador.linha)
        ec, el = int(p.entidade.col), int(p.entidade.linha)
        dist   = abs(jc - ec) + abs(jl - el)

        # Fase: movimento
        if self._ia_fase == "mover":
            mov = p.mov_restante
            passos = 0
            while passos < mov and dist > 1:
                jc2, jl2 = int(jogador.col), int(jogador.linha)
                ec2, el2 = int(p.entidade.col), int(p.entidade.linha)
                if abs(jc2 - ec2) + abs(jl2 - el2) <= 1:
                    break
                dc = 0 if jc2 == ec2 else (1 if jc2 > ec2 else -1)
                dl = 0 if jl2 == el2 else (1 if jl2 > el2 else -1)
                cel_h = self.mundo.celula(ec2 + dc, el2)
                cel_v = self.mundo.celula(ec2,      el2 + dl)
                destino = None
                if cel_h and cel_h.passavel and cel_h.ocupante is None:
                    destino = cel_h
                elif cel_v and cel_v.passavel and cel_v.ocupante is None:
                    destino = cel_v
                if destino:
                    self._mover(p.entidade, destino)
                    passos += 1
                    dist = abs(int(jogador.col) - int(p.entidade.col)) + \
                           abs(int(jogador.linha) - int(p.entidade.linha))
                else:
                    break
            p.mov_restante = max(0, mov - passos)
            self._ia_fase = "atacar"

        # Fase: ataque
        if self._ia_fase == "atacar":
            self._ia_fase = "fim"
            jc2, jl2 = int(jogador.col), int(jogador.linha)
            dist2 = (abs(jc2 - int(p.entidade.col)) +
                     abs(jl2 - int(p.entidade.linha)))
            if not p.ja_agiu and dist2 <= 1:
                cel = self.mundo.celula(jc2, jl2)
                if cel:
                    p.ja_agiu = True
                    # Busca pericia do inimigo
                    pericias_ini = getattr(p.entidade, "pericias", {})
                    hab = pericias_ini.get("Lutar (Soco)",
                          pericias_ini.get("Briga", 30))
                    self._atacar(p.entidade, cel,
                                 habilidade=hab, dano_expr="1d3")
                    # Se disparou reacao, a IA continua em resolver_reacao()
                    if self.estado == EstadoCombate.AGUARDANDO_REACAO:
                        return

        # Fim do turno do inimigo
        if self.estado not in (EstadoCombate.FIM_COMBATE,
                               EstadoCombate.AGUARDANDO_REACAO):
            self.proximo_turno()

    # ══════════════════════════════════════════════════════════
    # FLUXO DE TURNOS
    # ══════════════════════════════════════════════════════════

    def proximo_turno(self):
        """Avanca para o proximo participante vivo."""
        self.participantes = [p for p in self.participantes if p.vivo]
        if self._verificar_fim():
            return

        self.idx_ativo = (self.idx_ativo + 1) % len(self.participantes)
        if self.idx_ativo == 0:
            self.turno_atual += 1
            self.log(f"-- Rodada {self.turno_atual} --")
            for l in self.mundo.tick_turno():
                self.log(l)

        self._iniciar_turno()

    def _executar_esperar(self, p: Participante):
        """Compatibilidade legada."""
        p.ap_atual = 0
        self.log(f"{p.nome} espera.")
        self.proximo_turno()

    def _verificar_fim(self) -> bool:
        jogador_p = self.participantes[0] if self.participantes else None
        if not jogador_p or not jogador_p.vivo:
            self.estado = EstadoCombate.FIM_COMBATE
            self.log("Investigador derrotado. Fim de combate.")
            return True
        inimigos_vivos = [p for p in self.participantes[1:] if p.vivo]
        if not inimigos_vivos:
            self.estado = EstadoCombate.FIM_COMBATE
            self.log("Todos os inimigos foram derrotados!")
            return True
        return False


# ══════════════════════════════════════════════════════════════
# HELPERS DE DADOS (CoC 7e)
# ══════════════════════════════════════════════════════════════

def _nivel_sucesso(rolagem: int, habilidade: int) -> str:
    """Retorna o nivel de sucesso CoC 7e para uma rolagem d100."""
    if rolagem <= max(1, habilidade // 5):   return "CRITICO"
    if rolagem <= max(1, habilidade // 2):   return "EXTREMO"
    if rolagem <= habilidade:                return "SUCESSO"
    if rolagem >= 96:                        return "FUMBLE"
    return "FALHA"


_NIVEL_ORDEM = {"CRITICO": 4, "EXTREMO": 3, "SUCESSO": 2, "FALHA": 1, "FUMBLE": 0}

def _comparar_nivel(a: str, b: str) -> int:
    """Retorna >0 se a > b, 0 se igual, <0 se a < b."""
    return _NIVEL_ORDEM.get(a, 0) - _NIVEL_ORDEM.get(b, 0)


def _rolar_dano_coc(expr: str, bonus_dano: int, nivel: str) -> int:
    """
    Rola dano conforme CoC 7e:
      SUCESSO:  rola normalmente
      EXTREMO:  dano maximo
      CRITICO:  dano maximo + 1 rolagem extra
      FALHA/FUMBLE: 0
    """
    from combate.cards import rolar_dado  # import local para evitar ciclo

    if nivel in ("FALHA", "FUMBLE"):
        return 0

    bd = int(bonus_dano)

    try:
        partes = expr.lower().split("d")
        num  = int(partes[0]) if partes[0] else 1
        lado = int(partes[1].split("+")[0]) if len(partes) > 1 else 6
    except Exception:
        num, lado = 1, 3

    if nivel == "CRITICO":
        base  = num * lado            # maximo possivel
        extra = rolar_dado(expr)      # rolagem extra (armas perfurantes)
        return max(1, base + extra + bd)

    if nivel == "EXTREMO":
        return max(1, num * lado + bd)  # dano maximo sem extra

    # SUCESSO normal
    base = rolar_dado(expr) if expr else 1
    return max(1, base + bd)
