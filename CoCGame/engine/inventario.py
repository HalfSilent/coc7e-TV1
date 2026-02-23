"""
engine/inventario.py — Sistema de inventário para CoC 7e.

📖 Referência: Livro do Guardião CoC 7e, cap. 3 (Criando Investigadores)
   — seção "Equipamento e Posse": itens são listados na ficha do investigador
   com valor em dólares (1920s). Armas têm: perícia, dano, alcance, tiros,
   HP da arma e nível de mau funcionamento. Tomos têm custo de SAN, tempo
   de estudo e ganho de Conhecimento dos Mitos.

Tipos de item:
    ARMA       — Revólver, faca, cassetete…
    CONSUMIVEL — Curativo, morfina, comida…
    PISTA      — Documentos, fotos, cartas…  (não "usáveis", apenas lidos)
    TOME       — Grimórios e livros dos Mitos (custo SAN + tempo de estudo)
    MISC       — Objetos utilitários (lanterna, corda, binóculo…)
"""
from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from engine.entidade import Jogador


# ══════════════════════════════════════════════════════════════
# TIPOS
# ══════════════════════════════════════════════════════════════

class TipoItem(Enum):
    ARMA       = "arma"
    CONSUMIVEL = "consumivel"
    PISTA      = "pista"
    TOME       = "tome"
    MISC       = "misc"


# ══════════════════════════════════════════════════════════════
# ITEM
# ══════════════════════════════════════════════════════════════

@dataclass
class Item:
    """
    Representa um item do inventário do investigador.

    📖 CoC 7e, pág. 57-60: cada item tem nome, valor (US$), peso implícito
    e descrição. Armas incluem perícia associada, dano e capacidade.
    """

    id:          str          # identificador único, ex: "revolver_38"
    nome:        str          # display, ex: "Revólver .38"
    tipo:        TipoItem

    descricao:   str  = ""
    peso:        float = 0.5   # kg (aproximado — CoC não é rígido aqui)
    valor:       float = 0.0   # US$ dos anos 1920
    quantidade:  int   = 1
    empilhavel:  bool  = False  # True para munição, bandagens, etc.
    icone_id:    str   = ""     # nome do sprite DENZI/Kenney (sem extensão)

    # ── Armas (CoC 7e pág. 105-108) ──────────────────────────
    pericia:           str = ""    # ex: "Armas de Fogo (.38)"
    dano:              str = ""    # ex: "1D10+2"
    alcance:           str = ""    # ex: "15m" / "Toque" / "10m"
    tiros:             int = 0     # capacidade total do cartucho/magazine
    tiros_restantes:   int = -1    # -1 → inicializa como tiros na __post_init__
    mal_funcionamento: int = 100   # fumble em 96-100 (padrão CoC 7e)

    # ── Consumíveis ───────────────────────────────────────────
    cura_hp:  str = ""    # expressão de dados: "1D3", "2D6+2"
    cura_san: int = 0

    # ── Tomos dos Mitos (CoC 7e cap. 4) ──────────────────────
    idioma:         str       = ""    # idioma necessário para ler
    tempo_estudo:   int       = 0     # semanas de estudo
    custo_san:      int       = 0     # SAN perdida durante a leitura
    ganho_mitos:    int       = 0     # pontos de Conhecimento dos Mitos
    magias:         List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.tiros_restantes == -1:
            self.tiros_restantes = self.tiros

    # ── Conveniências ─────────────────────────────────────────

    @property
    def descricao_curta(self) -> str:
        """Uma linha para o painel de detalhes do inventário."""
        if self.tipo == TipoItem.ARMA:
            partes = [self.dano]
            if self.tiros > 0:
                partes.append(f"{self.tiros_restantes}/{self.tiros} tiros")
            if self.alcance:
                partes.append(self.alcance)
            return "  ".join(partes)

        if self.tipo == TipoItem.CONSUMIVEL:
            partes = []
            if self.cura_hp:  partes.append(f"+{self.cura_hp} HP")
            if self.cura_san: partes.append(f"+{self.cura_san} SAN")
            return "  ".join(partes) if partes else self.descricao[:60]

        if self.tipo == TipoItem.TOME:
            return (f"Idioma: {self.idioma or 'Qualquer'}  "
                    f"SAN: -{self.custo_san}  Mitos: +{self.ganho_mitos}")

        return self.descricao[:60]

    @property
    def esta_equipado(self) -> bool:
        return False   # definido pelo Inventario; aqui só estrutura

    def clonar(self) -> "Item":
        return copy.copy(self)


# ══════════════════════════════════════════════════════════════
# HELPER DE DADOS
# ══════════════════════════════════════════════════════════════

def rolar_expressao(expr: str) -> int:
    """
    Rola expressão de dados: '1D3', '2D6+2', '1D10', '3'.
    Usado para cura_hp, dano, etc.
    """
    expr = expr.upper().strip().replace(" ", "")
    m = re.match(r'^(\d+)D(\d+)([+-]\d+)?$', expr)
    if m:
        qtd   = int(m.group(1))
        faces = int(m.group(2))
        mod   = int(m.group(3)) if m.group(3) else 0
        return sum(random.randint(1, faces) for _ in range(qtd)) + mod
    try:
        return int(expr)
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════
# INVENTÁRIO
# ══════════════════════════════════════════════════════════════

class Inventario:
    """
    Gerencia os itens carregados pelo investigador.

    📖 CoC 7e não tem sistema formal de peso, mas adotamos uma capacidade
    suave (aviso ao sobrecarregar, sem bloqueio rígido) para coerência.
    Capacidade base: 20 kg, ajustada pela FOR do investigador.
    """

    CAPACIDADE_BASE = 20.0  # kg com FOR 50

    def __init__(self, forca: int = 50):
        self.itens:          List[Item]    = []
        self.arma_equipada:  Optional[Item] = None
        self.dinheiro:       float          = 0.0   # US$ anos 1920
        # FOR > 50 dá mais capacidade (cada 10 pts = +2 kg)
        self.capacidade: float = self.CAPACIDADE_BASE + (forca - 50) * 0.2

    # ── Propriedades ──────────────────────────────────────────

    @property
    def peso_total(self) -> float:
        return round(sum(i.peso * i.quantidade for i in self.itens), 2)

    @property
    def sobrecarregado(self) -> bool:
        """
        📖 CoC 7e pág. 40: sobrecarga reduz MOV à metade.
        Aqui só marcamos o flag — a penalidade é aplicada na movimentação.
        """
        return self.peso_total > self.capacidade

    @property
    def arma_id(self) -> str:
        return self.arma_equipada.id if self.arma_equipada else ""

    @property
    def arma_nome(self) -> str:
        return self.arma_equipada.nome if self.arma_equipada else ""

    # ── Operações ─────────────────────────────────────────────

    def adicionar(self, item: Item) -> Tuple[bool, str]:
        """
        Adiciona item ao inventário.
        Retorna (sucesso, mensagem_feedback).
        """
        # Aviso de sobrecarga (não bloqueia)
        aviso = ""
        if self.peso_total + item.peso * item.quantidade > self.capacidade:
            aviso = " [!] Sobrecarregado"

        # Empilhamento
        if item.empilhavel:
            existente = next((i for i in self.itens if i.id == item.id), None)
            if existente:
                existente.quantidade += item.quantidade
                return True, f"+{item.quantidade}× {item.nome}{aviso}"

        self.itens.append(item)
        return True, f"Obteve: {item.nome}{aviso}"

    def remover(self, item_id: str, quantidade: int = 1) -> Optional[Item]:
        """Remove e retorna o item (ou None se não encontrado)."""
        for idx, item in enumerate(self.itens):
            if item.id == item_id:
                if item.empilhavel and item.quantidade > quantidade:
                    item.quantidade -= quantidade
                    removido = item.clonar()
                    removido.quantidade = quantidade
                    return removido
                else:
                    if item is self.arma_equipada:
                        self.arma_equipada = None
                    return self.itens.pop(idx)
        return None

    def equipar(self, item_id: str) -> Tuple[bool, str]:
        """
        Equipa uma arma no slot principal.
        📖 CoC 7e: investigador usa a perícia associada à arma equipada.
        """
        item = self.get(item_id)
        if not item:
            return False, "Item não encontrado."
        if item.tipo != TipoItem.ARMA:
            return False, f"{item.nome} não é uma arma."
        self.arma_equipada = item
        return True, f"Equipou: {item.nome}"

    def usar(self, item_id: str, jogador: "Jogador") -> Tuple[bool, str]:
        """
        Usa um item consumível diretamente.
        📖 CoC 7e, pág. 90: Primeiros Socorros restaura 1D3 HP;
            Medicina pode restaurar mais se bem-sucedida.
        Aqui resolvemos de forma simplificada sem rolar perícia.
        """
        item = self.get(item_id)
        if not item:
            return False, "Item não encontrado."

        if item.tipo == TipoItem.CONSUMIVEL:
            resultados = []
            if item.cura_hp:
                cura  = rolar_expressao(item.cura_hp)
                real  = min(cura, jogador.hp_max - jogador.hp)
                jogador.hp = min(jogador.hp_max, jogador.hp + cura)
                resultados.append(f"+{real} HP")
            if item.cura_san:
                real  = min(item.cura_san, jogador.san_max - jogador.sanidade)
                jogador.sanidade = min(jogador.san_max, jogador.sanidade + item.cura_san)
                resultados.append(f"+{real} SAN")

            # Consome
            if item.empilhavel:
                item.quantidade -= 1
                if item.quantidade <= 0:
                    self.itens.remove(item)
            else:
                self.itens.remove(item)

            return True, " | ".join(resultados) if resultados else f"Usou {item.nome}."

        if item.tipo == TipoItem.TOME:
            return False, "Tomos exigem tempo de estudo — não podem ser usados assim."

        if item.tipo == TipoItem.PISTA:
            return False, "Pistas são para ler, não para usar."

        return False, f"{item.nome} não tem uso direto."

    def descartar(self, item_id: str) -> Tuple[bool, str]:
        """Remove permanentemente o item do inventário."""
        item = self.remover(item_id)
        if item:
            return True, f"Descartou: {item.nome}"
        return False, "Item não encontrado."

    # ── Consultas ─────────────────────────────────────────────

    def tem(self, item_id: str) -> bool:
        return any(i.id == item_id for i in self.itens)

    def get(self, item_id: str) -> Optional[Item]:
        return next((i for i in self.itens if i.id == item_id), None)

    def itens_por_tipo(self, tipo: TipoItem) -> List[Item]:
        return [i for i in self.itens if i.tipo == tipo]

    def armas(self) -> List[Item]:
        return self.itens_por_tipo(TipoItem.ARMA)

    def consumiveis(self) -> List[Item]:
        return self.itens_por_tipo(TipoItem.CONSUMIVEL)

    def pistas(self) -> List[Item]:
        return self.itens_por_tipo(TipoItem.PISTA)

    def tomes(self) -> List[Item]:
        return self.itens_por_tipo(TipoItem.TOME)
