"""
ui/dados.py — Funções de dados e cálculos CoC 7e.

Usadas por ficha.py (DearPyGui) e tela_criar_personagem.py (pygame).
"""
from __future__ import annotations

import random
from datetime import date


# ══════════════════════════════════════════════════════════════
# ROLAGENS
# ══════════════════════════════════════════════════════════════

def rolar_3d6x5() -> tuple[int, list[int]]:
    """Rola 3d6 e multiplica por 5. Retorna (valor, [d1, d2, d3])."""
    dados = [random.randint(1, 6) for _ in range(3)]
    return sum(dados) * 5, dados


def rolar_2d6_mais6_x5() -> tuple[int, list[int]]:
    """Rola 2d6+6 e multiplica por 5. Retorna (valor, [d1, d2])."""
    dados = [random.randint(1, 6) for _ in range(2)]
    return (sum(dados) + 6) * 5, dados


# ══════════════════════════════════════════════════════════════
# DERIVADOS
# ══════════════════════════════════════════════════════════════

def calcular_pontos_vida(tamanho: int, constituicao: int) -> int:
    """PV = (TAM + CON) // 10."""
    return (tamanho + constituicao) // 10


def calcular_pontos_magia(poder: int) -> int:
    """PM = POD // 5."""
    return poder // 5


def calcular_taxa_movimento(forca: int, destreza: int, tamanho: int) -> int:
    """MOV CoC 7e:  7 se DES < FOR e DES < TAM,  9 se FOR >= TAM e DES >= TAM,  8 demais."""
    if destreza < forca and destreza < tamanho:
        return 7
    if forca >= tamanho and destreza >= tamanho:
        return 9
    return 8


def calcular_corpo_a_corpo(forca: int, tamanho: int) -> tuple[str, str]:
    """Retorna (bonus_dano, dano_corpo_a_corpo) conforme tabela CoC 7e."""
    soma = forca + tamanho
    if soma <= 64:    return "-2",   "1d3-2"
    if soma <= 84:    return "-1",   "1d3-1"
    if soma <= 124:   return "0",    "1d3"
    if soma <= 164:   return "+1d4", "1d3+1d4"
    if soma <= 204:   return "+1d6", "1d3+1d6"
    return "+2d6", "1d3+2d6"


# ══════════════════════════════════════════════════════════════
# IDADE
# ══════════════════════════════════════════════════════════════

def calcular_idade(data_nascimento: str) -> int:
    """Calcula idade a partir de DD/MM/AAAA (data de nascimento)."""
    dd, mm, yyyy = map(int, data_nascimento.split("/"))
    nasc = date(yyyy, mm, dd)
    hoje = date.today()
    idade = hoje.year - nasc.year
    if (hoje.month, hoje.day) < (nasc.month, nasc.day):
        idade -= 1
    return idade
