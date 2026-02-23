"""
engine/mundo.py — Grid isométrico com suporte a efeitos ambientais.

Cada célula guarda: tipo de terreno, efeito ambiental, cobertura e ocupante.
Toda lógica de jogo (colisão, efeitos, cobertura) fica aqui — o renderer
só consulta este módulo para saber o que desenhar.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Tuple


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class TipoTile(Enum):
    VAZIO   = 0
    CHAO    = 1   # pedra, madeira — caminhável
    PAREDE  = 2   # bloqueio total
    ELEVADO = 3   # half-wall / caixote — cobertura parcial


class EfeitoAmbiental(Enum):
    NENHUM     = auto()
    OLEO       = auto()   # escorregadio, combustível
    FOGO       = auto()   # dano/turno, propaga em óleo
    NEVOA      = auto()   # penalidade de mira
    ARBUSTO    = auto()   # oculta, penalidade de mira inimigo
    AGUA_BENTA = auto()   # bônus vs. criaturas sobrenaturais
    SANGUE     = auto()   # teste de sanidade ao passar


class Cobertura(Enum):
    NENHUMA = 0
    MEIA    = 1   # −20 % acerto
    TOTAL   = 2   # sem linha de visão


# ══════════════════════════════════════════════════════════════
# CÉLULA
# ══════════════════════════════════════════════════════════════

@dataclass
class Celula:
    col:    int
    linha:  int
    tipo:   TipoTile        = TipoTile.CHAO
    efeito: EfeitoAmbiental = EfeitoAmbiental.NENHUM
    duracao_efeito: int     = 0
    ocupante: Optional[object] = None   # referência à entidade

    # ── propriedades de conveniência ──────────────────────────

    @property
    def bloqueada(self) -> bool:
        return self.tipo in (TipoTile.PAREDE, TipoTile.VAZIO)

    @property
    def passavel(self) -> bool:
        return not self.bloqueada and self.ocupante is None

    @property
    def custo_movimento(self) -> float:
        """Custo em AP para entrar nesta célula."""
        if self.tipo == TipoTile.ELEVADO:
            return 2.0
        if self.efeito == EfeitoAmbiental.OLEO:
            return 1.5
        return 1.0

    # ── efeitos ───────────────────────────────────────────────

    def aplicar_efeito(self, efeito: EfeitoAmbiental, duracao: int = 3):
        if self.efeito == EfeitoAmbiental.OLEO and efeito == EfeitoAmbiental.FOGO:
            duracao += 2   # óleo alimenta fogo
        self.efeito = efeito
        self.duracao_efeito = duracao

    def tick_efeito(self) -> Optional[str]:
        """Avança 1 turno. Retorna mensagem de log se o efeito dissipou."""
        if self.efeito == EfeitoAmbiental.NENHUM:
            return None
        self.duracao_efeito -= 1
        if self.duracao_efeito <= 0:
            nome = self.efeito.name
            self.efeito = EfeitoAmbiental.NENHUM
            return f"Efeito {nome} em ({self.col},{self.linha}) dissipou."
        return None


# ══════════════════════════════════════════════════════════════
# MUNDO
# ══════════════════════════════════════════════════════════════

_MAPA_TIPO = {
    0: TipoTile.VAZIO,
    1: TipoTile.CHAO,
    2: TipoTile.PAREDE,
    3: TipoTile.ELEVADO,
}


class Mundo:
    """Grade 2-D de Celulas. Lógica pura — sem pygame."""

    @classmethod
    def from_dados(cls, dados_mapa) -> "Mundo":
        """
        Cria Mundo a partir de um DadosMapa (dados/campanha_schema.py).
        Aplica automaticamente os efeitos ambientais salvos.
        """
        mundo = cls(dados_mapa.tiles)
        for ef in dados_mapa.efeitos:
            try:
                tipo_ef = EfeitoAmbiental[ef.tipo]
            except KeyError:
                continue
            cel = mundo.celula(ef.col, ef.linha)
            if cel:
                cel.aplicar_efeito(tipo_ef, ef.duracao)
        return mundo

    def __init__(self, mapa_raw: List[List[int]]):
        self.linhas  = len(mapa_raw)
        self.colunas = len(mapa_raw[0]) if self.linhas else 0
        self.grid: List[List[Celula]] = [
            [
                Celula(col=c, linha=l, tipo=_MAPA_TIPO.get(v, TipoTile.CHAO))
                for c, v in enumerate(row)
            ]
            for l, row in enumerate(mapa_raw)
        ]

    # ── acesso ────────────────────────────────────────────────

    def celula(self, col: int, linha: int) -> Optional[Celula]:
        if 0 <= linha < self.linhas and 0 <= col < self.colunas:
            return self.grid[linha][col]
        return None

    def vizinhos(self, col: int, linha: int,
                 diagonal: bool = False) -> List[Celula]:
        dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if diagonal:
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        return [c for dc, dl in dirs
                if (c := self.celula(col + dc, linha + dl)) and not c.bloqueada]

    # ── linha de visão / cobertura ────────────────────────────

    def calcular_cobertura(self, origem: Tuple[int, int],
                           alvo: Tuple[int, int]) -> Cobertura:
        """
        Raycasting no grid. Retorna Cobertura entre dois pontos.
        Paredes = total; tiles ELEVADO ou efeitos de névoa/arbusto = parcial.
        """
        oc, ol = origem
        ac, al = alvo
        passos = max(abs(ac - oc), abs(al - ol))
        if passos == 0:
            return Cobertura.NENHUMA

        parcial = 0
        for i in range(1, passos):
            t  = i / passos
            ic = round(oc + t * (ac - oc))
            il = round(ol + t * (al - ol))
            cel = self.celula(ic, il)
            if cel is None:
                continue
            if cel.tipo == TipoTile.PAREDE:
                return Cobertura.TOTAL
            if cel.tipo == TipoTile.ELEVADO:
                parcial += 1
            if cel.efeito in (EfeitoAmbiental.NEVOA, EfeitoAmbiental.ARBUSTO):
                parcial += 1

        if parcial >= 2:
            return Cobertura.TOTAL
        if parcial == 1:
            return Cobertura.MEIA
        return Cobertura.NENHUMA

    # ── tick de turno ─────────────────────────────────────────

    def tick_turno(self) -> List[str]:
        """
        Avança efeitos ambientais 1 turno.
        Retorna lista de mensagens para o log de combate.
        """
        logs: List[str] = []
        for row in self.grid:
            for cel in row:
                msg = cel.tick_efeito()
                if msg:
                    logs.append(msg)
                # fogo propaga para vizinhos com óleo
                if cel.efeito == EfeitoAmbiental.FOGO:
                    for viz in self.vizinhos(cel.col, cel.linha):
                        if viz.efeito == EfeitoAmbiental.OLEO:
                            viz.aplicar_efeito(EfeitoAmbiental.FOGO, 3)
                            logs.append(
                                f"🔥 Fogo propagou para ({viz.col},{viz.linha})!"
                            )
        return logs

    # ── alcance Manhattan ─────────────────────────────────────

    def celulas_em_alcance(self, col: int, linha: int,
                           raio: int,
                           so_passaveis: bool = False) -> List[Tuple[int, int]]:
        result = []
        for dl in range(-raio, raio + 1):
            for dc in range(-raio, raio + 1):
                if abs(dc) + abs(dl) <= raio:
                    cel = self.celula(col + dc, linha + dl)
                    if cel and (not so_passaveis or not cel.bloqueada):
                        result.append((col + dc, linha + dl))
        return result
