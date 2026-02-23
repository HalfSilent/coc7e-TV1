"""
engine/entidade.py — Jogador, inimigos e NPCs para CoC 7e.

Stats inspirados no sistema CoC 7e:
    HP, Sanidade, Destreza, Força, Constituição, Tamanho
    Bônus de Dano calculado automaticamente.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

import pygame

from engine.inventario import Inventario


# ══════════════════════════════════════════════════════════════
# BÔNUS DE DANO (regra CoC 7e)
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# GERAÇÃO CoC 7e — dados para NPCs humanos
# ══════════════════════════════════════════════════════════════

_AUTO = object()   # sentinela — "auto-gerar conforme CoC 7e"


def _r3d6x5() -> int:
    """3D6 × 5  (FOR, CON, DES, POD, APA)  → 15–90."""
    return sum(random.randint(1, 6) for _ in range(3)) * 5


def _r2d6p6x5() -> int:
    """(2D6+6) × 5  (TAM, INT, EDU)  → 40–90."""
    return (sum(random.randint(1, 6) for _ in range(2)) + 6) * 5


def _gerar_pericias_humano(des: int, pod: int) -> dict:
    """
    Gera perícias básicas de combate/social para um NPC humano genérico.
    Valores baseados em DES (combate) e POD (social), com variação aleatória.
    """
    r = random.randint
    lutar    = max(25, min(75, des // 2 + r(-5, 20)))
    esquivar = max(15, min(50, des // 2 + r(-5, 10)))
    armas    = max(15, min(65, des // 2 + r(-5, 20)))
    intim    = max(15, min(60, pod // 2 + r(-10, 20)))
    charme   = max(10, min(50, pod // 2 + r(-10, 15)))
    persuasao = max(10, min(45, pod // 2 + r(-10, 15)))
    return {
        "Lutar (Soco)":          lutar,
        "Esquivar":              esquivar,
        "Armas de Fogo (Pistola)": armas,
        "Intimidação":           intim,
        "Charme":                charme,
        "Persuasão":             persuasao,
    }


def calcular_bonus_dano(forca: int, tamanho: int) -> str:
    total = forca + tamanho
    if total <= 64:  return "-2"
    if total <= 84:  return "-1"
    if total <= 124: return "0"
    if total <= 164: return "+1d4"
    if total <= 204: return "+1d6"
    return "+2d6"


def rolar_bonus_dano(bd: str) -> int:
    if bd == "0":    return 0
    if bd == "-1":   return -1
    if bd == "-2":   return -2
    if bd == "+1d4": return random.randint(1, 4)
    if bd == "+1d6": return random.randint(1, 6)
    if bd == "+2d6": return random.randint(1, 6) + random.randint(1, 6)
    return 0


# ══════════════════════════════════════════════════════════════
# DIRECOES ISOMETRICAS
# ══════════════════════════════════════════════════════════════

class Direcao(Enum):
    SE = auto()   # Sul-Leste  (frente padrão)
    SO = auto()   # Sul-Oeste
    NE = auto()   # Norte-Leste
    NO = auto()   # Norte-Oeste


def direcao_de_delta(dc: float, dl: float) -> Direcao:
    """Retorna direção isométrica a partir do delta de movimento."""
    if dc >= 0 and dl >= 0: return Direcao.SE
    if dc <  0 and dl >= 0: return Direcao.SO
    if dc >= 0 and dl <  0: return Direcao.NE
    return Direcao.NO


# ══════════════════════════════════════════════════════════════
# ENTIDADE BASE
# ══════════════════════════════════════════════════════════════

@dataclass
class Entidade:
    nome:      str
    col:       float
    linha:     float

    # ── Stats CoC ────────────────────────────────────────────
    hp:         int = 10
    hp_max:     int = 10
    sanidade:   int = 60
    san_max:    int = 60
    forca:      int = 50
    tamanho:    int = 55
    destreza:   int = 50
    constituicao: int = 50

    # ── Visual ───────────────────────────────────────────────
    sprite_idle: Optional[pygame.Surface] = field(default=None, repr=False)
    sprite_run:  Optional[pygame.Surface] = field(default=None, repr=False)
    direcao:     Direcao = Direcao.SE
    cor:         tuple   = (212, 168, 67)

    # ── Animação ─────────────────────────────────────────────
    frame_atual:  int   = 0
    tempo_frame:  float = 0.0
    fps_anim:     int   = 8
    movendo:      bool  = False

    def __post_init__(self):
        self.hp_max = self.hp
        self.san_max = self.sanidade
        self._bonus_dano = calcular_bonus_dano(self.forca, self.tamanho)

    @property
    def vivo(self) -> bool:
        return self.hp > 0

    @property
    def pos_grid(self) -> tuple:
        return (int(self.col), int(self.linha))

    @property
    def bonus_dano(self) -> str:
        return self._bonus_dano

    def sofrer_dano(self, dano: int) -> int:
        """Aplica dano; retorna dano real sofrido."""
        real = min(dano, self.hp)
        self.hp = max(0, self.hp - dano)
        return real

    def perder_sanidade(self, valor: int) -> int:
        """Aplica perda de sanidade; retorna valor real perdido."""
        real = min(valor, self.sanidade)
        self.sanidade = max(0, self.sanidade - valor)
        return real

    def atualizar_animacao(self, dt_ms: float):
        """Avança animação de sprite. Chame a cada frame."""
        self.tempo_frame += dt_ms
        intervalo = 1000 / self.fps_anim
        if self.tempo_frame >= intervalo:
            self.tempo_frame -= intervalo
            self.frame_atual = (self.frame_atual + 1) % 10


# ══════════════════════════════════════════════════════════════
# JOGADOR
# ══════════════════════════════════════════════════════════════

class Jogador(Entidade):
    def __init__(self, nome: str = "Investigador",
                 col: float = 0.0, linha: float = 0.0,
                 hp: int = 12, sanidade: int = 70,
                 forca: int = 55, tamanho: int = 60,
                 destreza: int = 65, constituicao: int = 60,
                 skin_id: int = 0,
                 pericias: Optional[dict] = None,
                 dinheiro: float = 0.0,
                 **kwargs):
        super().__init__(
            nome=nome, col=col, linha=linha,
            hp=hp, sanidade=sanidade, forca=forca, tamanho=tamanho,
            destreza=destreza, constituicao=constituicao,
            cor=(212, 168, 67), **kwargs
        )
        self.skin_id = skin_id
        # Dicionário de perícias carregado da ficha (nome → valor total)
        self.pericias: dict = pericias if pericias is not None else {}
        # Inventário do investigador
        self.inventario: Inventario = Inventario(forca=forca)
        self.inventario.dinheiro = dinheiro

    # ── Propriedades de compat. legada ─────────────────────────────────
    @property
    def arma_equipada(self) -> str:
        """Legado: retorna ID da arma equipada como string."""
        return self.inventario.arma_id

    @property
    def itens_inv(self) -> List[str]:
        """Legado: retorna lista de IDs dos itens no inventário."""
        return [i.id for i in self.inventario.itens]

    @property
    def pistas(self) -> List[str]:
        """Legado: retorna descrições das pistas como strings."""
        from engine.inventario import TipoItem
        return [i.descricao for i in self.inventario.itens
                if i.tipo == TipoItem.PISTA]


# ══════════════════════════════════════════════════════════════
# INIMIGOS
# ══════════════════════════════════════════════════════════════

class Inimigo(Entidade):
    def __init__(self, nome: str = "Cultista",
                 col: float = 0.0, linha: float = 0.0,
                 hp=_AUTO, sanidade=_AUTO,
                 forca=_AUTO, tamanho=_AUTO,
                 destreza=_AUTO, constituicao=_AUTO,
                 poder=_AUTO, inteligencia=_AUTO,
                 ia_raio: int = 6, skin_id: int = 3,
                 tipo: str = "humano",
                 disposicao: str = "Hostil",
                 pericias: Optional[dict] = None,
                 **kwargs):
        """
        Se tipo == "humano" e um atributo não for passado explicitamente,
        ele é gerado via dados CoC 7e (3D6×5 ou (2D6+6)×5), igual ao jogador.
        Monstros e criaturas mantêm valores fixos padrão.
        """
        if tipo == "humano":
            # ── Atributos físicos: 3D6×5 ───────────────────────
            _for = forca       if forca       is not _AUTO else _r3d6x5()
            _con = constituicao if constituicao is not _AUTO else _r3d6x5()
            _des = destreza    if destreza    is not _AUTO else _r3d6x5()
            _pod = poder       if poder       is not _AUTO else _r3d6x5()
            # ── Atributos mentais/corporais: (2D6+6)×5 ─────────
            _tam = tamanho     if tamanho     is not _AUTO else _r2d6p6x5()
            _int = inteligencia if inteligencia is not _AUTO else _r2d6p6x5()
            # ── Derivados ───────────────────────────────────────
            _hp  = hp          if hp          is not _AUTO else (_con + _tam) // 10
            _san = sanidade    if sanidade    is not _AUTO else min(_pod * 5, 99)
        else:
            # Monstros / criaturas — defaults fixos, sem rolagem
            _for = forca       if forca       is not _AUTO else 50
            _con = constituicao if constituicao is not _AUTO else 45
            _des = destreza    if destreza    is not _AUTO else 45
            _pod = poder       if poder       is not _AUTO else 50
            _tam = tamanho     if tamanho     is not _AUTO else 55
            _int = inteligencia if inteligencia is not _AUTO else 50
            _hp  = hp          if hp          is not _AUTO else 8
            _san = sanidade    if sanidade    is not _AUTO else 0

        super().__init__(
            nome=nome, col=col, linha=linha,
            hp=_hp, sanidade=_san, forca=_for, tamanho=_tam,
            destreza=_des, constituicao=_con,
            cor=(160, 50, 50), **kwargs
        )
        self.poder        = _pod
        self.inteligencia = _int
        self.ia_raio    = ia_raio
        self.ia_alerta  = False
        self.skin_id    = skin_id
        # "humano" → recebe opções de diálogo
        # "criatura" | "sobrenatural" → vai direto ao combate
        self.tipo       = tipo
        # Mood exibido na tela de diálogo
        self.disposicao = disposicao
        # Perícias para combate e social — auto-geradas para humanos
        if pericias is not None:
            self.pericias = pericias
        elif tipo == "humano":
            self.pericias = _gerar_pericias_humano(_des, _pod)
        else:
            self.pericias = {}


class Engendro(Entidade):
    """Criatura sobrenatural — maior, mais lenta, mais resistente."""
    def __init__(self, nome: str = "Engendro",
                 col: float = 0.0, linha: float = 0.0,
                 hp: int = 20, sanidade: int = 0,
                 forca: int = 80, tamanho: int = 90,
                 destreza: int = 30, constituicao: int = 50,
                 ia_raio: int = 8, skin_id: int = 6,
                 perda_san_avistamento: int = 4, **kwargs):
        super().__init__(
            nome=nome, col=col, linha=linha,
            hp=hp, sanidade=sanidade, forca=forca, tamanho=tamanho,
            destreza=destreza, constituicao=constituicao,
            cor=(100, 50, 160), **kwargs
        )
        self.ia_raio   = ia_raio
        self.ia_alerta = False
        self.skin_id   = skin_id
        self.perda_san_avistamento = perda_san_avistamento
        # Engendros nunca dialogam
        self.tipo       = "sobrenatural"
        self.disposicao = "Hostil"
        self.pericias   = {}
        self.poder        = 0
        self.inteligencia = 20
