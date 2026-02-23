"""
engine/grid/objeto.py — ObjetoMasmorra: objeto interativo no grid de exploração.

Suporta dois modos de interação:
  1. Simples (legado): mostra um texto ao apertar [E]
  2. Menu  (novo)   : abre popup com lista de opções → pode exigir perícia

Cada opção do menu pode:
  - Conceder uma *pista* (texto narrativo)
  - Dar um *item* ao inventário
  - Exigir uma *perícia* (rola d100 contra valor na ficha)
  - Não fazer nada além de descrever

Uso em masmorras.py:
    ObjetoMasmorra(
        col=2, linha=1,
        tipo="estante",
        nome="Estante de Ocultismo",
        descricao="Livros velhos sobre rituais e entidades.",
        sprite_tipo="estante",
        opcoes_menu=[
            {
                "tecla": "A",
                "texto": "Investigar Ocultismo",
                "pericia": "ocultismo",
                "pista": "Você encontra referências a 'O Portal do Rei Amarelo'.",
            },
            {
                "tecla": "B",
                "texto": "Pegar um livro ao acaso",
                "item": "livro_misterioso",
                "pista": "Um tomo sem título cai em suas mãos.",
            },
        ],
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OpcaoMenu:
    """Uma opção dentro do menu de interação de um objeto."""
    tecla:       str            # tecla de ativação, ex: "A", "B", "C"
    texto:       str            # descrição curta exibida no menu
    pericia:     str  = ""      # nome da perícia exigida (vazio = sem rolagem)
    dificuldade: str  = "normal" # "normal" | "dificil" | "extremo"
    pista:       str  = ""      # texto de pista concedida no sucesso (ou sempre)
    item:        str  = ""      # id do item concedido no sucesso (ou sempre)
    sem_check:   bool = False   # True = concede pista/item sem rolar perícia


@dataclass
class ObjetoMasmorra:
    """
    Objeto interativo no grid de exploração.

    Modos:
      - opcoes_menu vazio → comportamento legado (mostra descricao como msg)
      - opcoes_menu preenchido → abre popup de escolhas com rolagem de perícia
    """

    col:       int
    linha:     int
    tipo:      str   = "item"   # "nota"|"item"|"estante"|"arquivo"|"altar"|"porta"|"armadilha"
    nome:      str   = "Objeto"
    descricao: str   = ""
    sprite_tipo: str = ""       # hint visual: "estante"|"caixa"|"mesa"|"bau"|""

    # Legado: item simples concedido ao interagir
    item_concedido: Optional[str] = None

    # Novo: lista de opções de menu
    opcoes_menu: List[OpcaoMenu] = field(default_factory=list)

    # Estado
    usado: bool = False

    # ──────────────────────────────────────────────────────────

    @property
    def tem_menu(self) -> bool:
        """True se o objeto tem menu de opções (novo modo)."""
        return len(self.opcoes_menu) > 0

    def interagir_simples(self) -> str:
        """
        Modo legado: retorna texto descritivo e marca como usado.
        Usado pelo sistema antigo quando opcoes_menu está vazio.
        """
        if self.usado:
            return f"[{self.nome}] já foi examinado."
        self.usado = True
        return self.descricao
