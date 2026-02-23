"""
combate/cards.py — Sistema de cartas/habilidades para o combate tático CoC 7e.

Cada Card representa uma ação disponível ao jogador/inimigo durante o combate.
O deck do jogador é construído DINAMICAMENTE a partir das pericias reais do
investigador (investigador.json) — inspirado em Buriedborne mas expandido para
refletir a granularidade de CoC 7e.

Tipos de carta:
    "ataque"     — causa dano a um alvo
    "movimento"  — move a entidade no grid
    "defesa"     — reduz dano / aplica esquiva
    "habilidade" — efeito especial (ocultar, curar, etc.)
    "ambiente"   — aplica efeito ambiental no chão (óleo, fogo, névoa)

Mapeamento de pericias CoC 7e → cards:
    "Lutar (Soco)"         → CARTA_SOCO
    "Lutar (Chute)"        → CARTA_CHUTE
    "Lutar (Agarrar)"      → CARTA_AGARRAR
    "Armas Brancas"        → CARTA_FACA / CARTA_MACHADINHA (se no inventário)
    "Armas de Fogo (.38)"  → CARTA_REVOLVER_38   (se revólver no inventário)
    "Armas de Fogo (.45)"  → CARTA_PISTOLA_45    (se pistola no inventário)
    "Armas de Fogo (.32)"  → CARTA_REVOLVER_32   (se .32 no inventário)
    "Armas de Fogo (Rifle)"→ CARTA_RIFLE         (se rifle no inventário)
    "Espingarda"           → CARTA_ESPINGARDA    (se espingarda no inventário)
    "Arremessar"           → CARTA_ARREMESSO     (se granada/molotov no inventário)
    "Esquivar"             → CARTA_ESQUIVAR
    "Furtividade"          → CARTA_OCULTAR       (se pericia > MIN_UTIL)
    "Intimidação"          → CARTA_INTIMIDAR     (se pericia > MIN_UTIL)
    "Primeiros Socorros"   → CARTA_PRIMEIROS_SOCORROS (se kit no inventário)
    "Medicina"             → CARTA_MEDICINA      (se pericia > MIN_UTIL)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from engine.mundo import EfeitoAmbiental

# Valor mínimo de perícia para aparecer como carta opcional
MIN_UTIL = 20


# ══════════════════════════════════════════════════════════════
# DATACLASS CARD
# ══════════════════════════════════════════════════════════════

@dataclass
class Card:
    nome:     str
    custo_ap: int
    tipo:     str          # "ataque"|"movimento"|"defesa"|"habilidade"|"ambiente"
    efeito:   Dict[str, Any]  # veja abaixo
    pericia:  str = ""     # nome da perícia CoC usada no teste (vazio = sem teste)
    alcance:  int = 1      # tiles (0 = self, 1 = adjacente, 5 = tiro)
    descricao: str = ""
    valor_pericia: int = 0  # % da perícia do investigador (exibido no HUD)
    # Efeitos possíveis no dict:
    #   {"dano": "1d6"}          → dano rolado
    #   {"passos": 3}            → células de movimento
    #   {"cura_hp": "1d4"}       → cura HP
    #   {"esquiva": True}        → próxima esquiva automática
    #   {"oculto": True}         → entidade fica oculta
    #   {"san_dano": 2}          → dano de sanidade
    #   {"efeito_chao": "FOGO"}  → aplica EfeitoAmbiental no alvo
    #   {"forcar_recuo": 2}      → empurra alvo 2 células
    #   {"agarrar": True}        → inimigo fica imobilizado 1 turno

    def __str__(self) -> str:
        pct = f" {self.valor_pericia}%" if self.valor_pericia else ""
        return f"[{self.custo_ap}AP] {self.nome}{pct}"


# ══════════════════════════════════════════════════════════════
# ROLAGEM DE DADO
# ══════════════════════════════════════════════════════════════

def rolar_dado(expressao: str) -> int:
    """Rola uma expressão de dado: '1d6', '2d4+1', '1d8', etc."""
    expressao = expressao.replace(" ", "").lower()
    bonus = 0
    if "+" in expressao:
        partes = expressao.split("+")
        bonus = int(partes[1])
        expressao = partes[0]
    elif "-" in expressao and expressao.index("-") > 0:
        partes = expressao.split("-")
        bonus = -int(partes[1])
        expressao = partes[0]

    if "d" in expressao:
        n, faces = expressao.split("d")
        n = int(n) if n else 1
        faces = int(faces)
        return sum(random.randint(1, faces) for _ in range(n)) + bonus
    return int(expressao) + bonus


# ══════════════════════════════════════════════════════════════
# DECKS PADRÃO
# ══════════════════════════════════════════════════════════════

# Deck base para qualquer investigador
# ══════════════════════════════════════════════════════════════
# CARTAS BASE (sempre disponíveis — sem teste de perícia)
# ══════════════════════════════════════════════════════════════

CARTA_MOVER = Card(
    nome="Mover",
    custo_ap=1, tipo="movimento",
    efeito={"passos": 3},
    alcance=0,
    descricao="Move até 3 casas no grid."
)

CARTA_ESPERAR = Card(
    nome="Esperar",
    custo_ap=0, tipo="habilidade",
    efeito={"bonus_ap_prox": 1},
    alcance=0,
    descricao="Passa o turno. Ganha +1 AP no próximo turno."
)

# Deck base para qualquer investigador
DECK_INVESTIGADOR: List[Card] = [
    CARTA_MOVER,
    Card(
        nome="Soco",
        custo_ap=2, tipo="ataque",
        efeito={"dano": "1d3"},
        pericia="Lutar (Soco)",
        alcance=1,
        descricao="Ataque corpo-a-corpo desarmado."
    ),
    Card(
        nome="Esquivar",
        custo_ap=1, tipo="defesa",
        efeito={"esquiva": True},
        pericia="Esquivar",
        alcance=0,
        descricao="Testa Esquivar. Se passar, próximo ataque erra."
    ),
    CARTA_ESPERAR,
]


# ══════════════════════════════════════════════════════════════
# CARTAS DE COMBATE CORPO-A-CORPO (CoC 7e granular)
# ══════════════════════════════════════════════════════════════

CARTA_SOCO = Card(
    nome="Soco",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d3"},
    pericia="Lutar (Soco)",
    alcance=1,
    descricao="Ataque desarmado — soco. Dano: 1d3 + bônus."
)

CARTA_CHUTE = Card(
    nome="Chute",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d6", "forcar_recuo": 1},
    pericia="Lutar (Chute)",
    alcance=1,
    descricao="Chute — maior dano, pode recuar inimigo 1 tile."
)

CARTA_AGARRAR = Card(
    nome="Agarrar",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d2", "agarrar": True},
    pericia="Lutar (Agarrar)",
    alcance=1,
    descricao="Imobiliza inimigo por 1 turno. Dano menor, mas trava o alvo."
)

CARTA_ESQUIVAR = Card(
    nome="Esquivar",
    custo_ap=1, tipo="defesa",
    efeito={"esquiva": True},
    pericia="Esquivar",
    alcance=0,
    descricao="Testa Esquivar. Se passar, próximo ataque erra."
)


# ══════════════════════════════════════════════════════════════
# CARTAS DE ARMAS DE FOGO
# ══════════════════════════════════════════════════════════════

CARTA_REVOLVER_38 = Card(
    nome=".38 Revólver",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d10"},
    pericia="Armas de Fogo (.38)",
    alcance=8,
    descricao=".38 Revólver — 6 balas. Confiável e mortal."
)

CARTA_REVOLVER_32 = Card(
    nome=".32 Revólver",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d8"},
    pericia="Armas de Fogo (.32)",
    alcance=7,
    descricao=".32 Revólver — menor calibre, mais fácil de carregar."
)

CARTA_PISTOLA_45 = Card(
    nome=".45 Pistola",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d10+2"},
    pericia="Armas de Fogo (.45)",
    alcance=8,
    descricao=".45 Pistola automática — brutal no curto alcance."
)

CARTA_ESPINGARDA = Card(
    nome="Espingarda",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "2d6", "forcar_recuo": 1},
    pericia="Espingarda",
    alcance=5,
    descricao="Disparo de espingarda. Pode recuar o alvo."
)

CARTA_RIFLE = Card(
    nome="Rifle",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "2d6+4"},
    pericia="Armas de Fogo (Rifle)",
    alcance=15,
    descricao="Rifle de longa distância — precisão máxima."
)

CARTA_RECARREGAR = Card(
    nome="Recarregar",
    custo_ap=1, tipo="habilidade",
    efeito={"recarregar": True},
    alcance=0,
    descricao="Recarrega a arma atual."
)


# ══════════════════════════════════════════════════════════════
# CARTAS DE ARMAS BRANCAS / ARREMESSO
# ══════════════════════════════════════════════════════════════

CARTA_FACA = Card(
    nome="Faca",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d4+2"},
    pericia="Armas Brancas",
    alcance=1,
    descricao="Ataque com faca."
)

CARTA_MACHADINHA = Card(
    nome="Machadinha",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d6+2"},
    pericia="Armas Brancas",
    alcance=1,
    descricao="Machadinha — mais dano, menos precisão."
)

CARTA_ARREMESSO = Card(
    nome="Arremessar",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d6", "efeito_chao": "FOGO"},
    pericia="Arremessar",
    alcance=5,
    descricao="Arremessa objeto incendiário. Dano + chamas no chão."
)


# ══════════════════════════════════════════════════════════════
# CARTAS DE SUPORTE / ITENS
# ══════════════════════════════════════════════════════════════

CARTA_PRIMEIROS_SOCORROS = Card(
    nome="Primeiros Socorros",
    custo_ap=2, tipo="habilidade",
    efeito={"cura_hp": "1d4"},
    pericia="Primeiros Socorros",
    alcance=1,
    descricao="Estabiliza ferimento. Só funciona 1x por combate por alvo."
)

CARTA_MEDICINA = Card(
    nome="Medicina",
    custo_ap=3, tipo="habilidade",
    efeito={"cura_hp": "1d3+2"},
    pericia="Medicina",
    alcance=1,
    descricao="Tratamento completo de ferimento grave."
)

CARTA_LANTERNA = Card(
    nome="Lanterna",
    custo_ap=1, tipo="habilidade",
    efeito={"revelar_nevoa": 3},
    alcance=4,
    descricao="Ilumina área removendo névoa em raio 3."
)

CARTA_MOLOTOV = Card(
    nome="Coquetel Molotov",
    custo_ap=2, tipo="ambiente",
    efeito={"efeito_chao": "FOGO", "dano": "1d6"},
    alcance=4,
    descricao="Lança coquetel. Dano imediato + área em chamas por 3 turnos."
)

CARTA_OLEO = Card(
    nome="Derramar Óleo",
    custo_ap=1, tipo="ambiente",
    efeito={"efeito_chao": "OLEO"},
    alcance=2,
    descricao="Derrama óleo no chão. Escorregadio — combustível para fogo."
)

CARTA_FUMACA = Card(
    nome="Granada de Fumaça",
    custo_ap=1, tipo="ambiente",
    efeito={"efeito_chao": "NEVOA", "raio_efeito": 2},
    alcance=5,
    descricao="Cria névoa em raio 2. Penalidade de mira para todos."
)

CARTA_ACIDO = Card(
    nome="Ácido",
    custo_ap=2, tipo="ataque",
    efeito={"dano": "1d6", "efeito_chao": "OLEO"},
    pericia="Arremessar",
    alcance=4,
    descricao="Frasco de ácido. Dano + terreno corrosivo."
)

CARTA_OCULTAR = Card(
    nome="Se Ocultar",
    custo_ap=2, tipo="habilidade",
    efeito={"oculto": True},
    pericia="Furtividade",
    alcance=0,
    descricao="Testa Furtividade. Se passar, inimigos perdem o alvo."
)

CARTA_INTIMIDAR = Card(
    nome="Intimidar",
    custo_ap=2, tipo="habilidade",
    efeito={"san_dano": 2, "recuo_moral": True},
    pericia="Intimidação",
    alcance=2,
    descricao="Testa Intimidação. Inimigo perde SAN e pode recuar."
)

CARTA_GRITO_CTHULHU = Card(
    nome="Grito de Cthulhu",
    custo_ap=3, tipo="habilidade",
    efeito={"san_dano": 5, "raio_efeito": 3},
    pericia="Magia: Grito de Cthulhu",
    alcance=3,
    descricao="Grito sobrenatural. Todos em raio 3 sofrem dano de sanidade."
)

# Cartas de inimigos
DECK_CULTISTA: List[Card] = [
    Card(nome="Mover",  custo_ap=1, tipo="movimento", efeito={"passos": 2}, alcance=0),
    Card(nome="Faca",   custo_ap=2, tipo="ataque",    efeito={"dano": "1d4"}, pericia="Lutar (Soco)", alcance=1),
    Card(nome="Atirar", custo_ap=2, tipo="ataque",    efeito={"dano": "1d8"}, pericia="Armas de Fogo (.38)", alcance=6),
    Card(nome="Esperar", custo_ap=0, tipo="habilidade", efeito={"bonus_ap_prox": 1}, alcance=0),
]

DECK_ENGENDRO: List[Card] = [
    Card(nome="Arrastar", custo_ap=1, tipo="movimento", efeito={"passos": 1}, alcance=0),
    Card(nome="Garras",   custo_ap=2, tipo="ataque",    efeito={"dano": "2d6"}, pericia="Garras", alcance=1,
         descricao="Garras profundas — ignora cobertura parcial."),
    Card(nome="Aura",     custo_ap=1, tipo="habilidade", efeito={"san_dano": 3, "raio_efeito": 2}, alcance=2,
         descricao="Aura de terror — dano de SAN em todos os investigadores próximos."),
]


# ══════════════════════════════════════════════════════════════
# MAPEAMENTO: item no inventário → card de arma + pericia CoC
# ══════════════════════════════════════════════════════════════

# (id_inventario, pericia_coc, card_base)
_ARMAS_INVENTARIO = [
    ("revolver_38",  "Armas de Fogo (.38)",  CARTA_REVOLVER_38),
    (".38",          "Armas de Fogo (.38)",  CARTA_REVOLVER_38),
    ("revolver_32",  "Armas de Fogo (.32)",  CARTA_REVOLVER_32),
    (".32",          "Armas de Fogo (.32)",  CARTA_REVOLVER_32),
    ("pistola_45",   "Armas de Fogo (.45)",  CARTA_PISTOLA_45),
    (".45",          "Armas de Fogo (.45)",  CARTA_PISTOLA_45),
    ("espingarda",   "Espingarda",           CARTA_ESPINGARDA),
    ("rifle",        "Armas de Fogo (Rifle)", CARTA_RIFLE),
    ("faca",         "Armas Brancas",        CARTA_FACA),
    ("arma_branca",  "Armas Brancas",        CARTA_FACA),
    ("machadinha",   "Armas Brancas",        CARTA_MACHADINHA),
    ("molotov",      "Arremessar",           CARTA_MOLOTOV),
    ("acido",        "Arremessar",           CARTA_ACIDO),
]

_ITENS_SUPORTE = {
    "primeiros_socorros": CARTA_PRIMEIROS_SOCORROS,
    "kit_medico":         CARTA_MEDICINA,
    "lanterna":           CARTA_LANTERNA,
    "oleo":               CARTA_OLEO,
    "fumaca":             CARTA_FUMACA,
}


# ══════════════════════════════════════════════════════════════
# FÁBRICA DE DECK — dinâmica baseada em pericias CoC 7e
# ══════════════════════════════════════════════════════════════

def montar_deck_investigador(
        pericias:  Optional[Dict[str, int]] = None,
        inventario: Optional[List[str]] = None,
        # legado: mantido para compatibilidade
        arma: Optional[str] = None,
        itens: Optional[List[str]] = None,
) -> List[Card]:
    """
    Monta o deck do investigador DINAMICAMENTE a partir das péricias CoC 7e.

    Cada carta carrega `valor_pericia` com o % real do investigador,
    exibido no HUD durante o combate.

    Args:
        pericias:   dict nome→valor extraído de investigador.json
        inventario: lista de itens no inventário (ex: ["revolver_38", "lanterna"])
        arma:       (legado) string da arma equipada
        itens:      (legado) lista de itens simples
    """
    p   = pericias  or {}
    inv = list(inventario or [])

    # Suporte legado: converte arma/itens para inventario
    if arma:
        inv.append(arma.lower())
    if itens:
        inv.extend([i.lower() for i in itens])

    deck: List[Card] = [CARTA_MOVER, CARTA_ESPERAR]

    # ── Habilidades de combate desarmado ─────────────────────
    _adicionar_se(deck, p, "Lutar (Soco)",    CARTA_SOCO)
    _adicionar_se(deck, p, "Lutar (Chute)",   CARTA_CHUTE)
    _adicionar_se(deck, p, "Lutar (Agarrar)", CARTA_AGARRAR)

    # Fallback: se nenhuma Lutar/* mas tem Briga genérico (pericias antigas)
    if not any(c.pericia.startswith("Lutar") for c in deck):
        val_briga = p.get("Briga", 0)
        if val_briga > 0:
            c = _clonar_com_valor(CARTA_SOCO, val_briga)
            deck.append(c)

    # ── Defesa ───────────────────────────────────────────────
    _adicionar_se(deck, p, "Esquivar", CARTA_ESQUIVAR)

    # ── Armas (requer item no inventário + pericia) ──────────
    armas_adicionadas: set = set()
    for id_inv, pericia_coc, carta_base in _ARMAS_INVENTARIO:
        if id_inv in inv and pericia_coc not in armas_adicionadas:
            val = p.get(pericia_coc, 1)  # padrão 1% se não treinado
            carta = _clonar_com_valor(carta_base, val)
            deck.append(carta)
            deck.append(CARTA_RECARREGAR)
            armas_adicionadas.add(pericia_coc)

    # ── Itens de suporte ─────────────────────────────────────
    for id_item, carta_suporte in _ITENS_SUPORTE.items():
        if id_item in inv:
            deck.append(carta_suporte)

    # ── Habilidades especiais (pericia acima do limiar) ───────
    if p.get("Furtividade", 0) >= MIN_UTIL:
        deck.append(_clonar_com_valor(CARTA_OCULTAR, p["Furtividade"]))
    if p.get("Intimidação", 0) >= MIN_UTIL:
        deck.append(_clonar_com_valor(CARTA_INTIMIDAR, p["Intimidação"]))

    # Medicina sem kit (perícia alta o suficiente para improvisar)
    if p.get("Medicina", 0) >= MIN_UTIL:
        deck.append(_clonar_com_valor(CARTA_MEDICINA, p["Medicina"]))
    elif p.get("Primeiros Socorros", 0) >= MIN_UTIL:
        deck.append(_clonar_com_valor(CARTA_PRIMEIROS_SOCORROS,
                                      p["Primeiros Socorros"]))

    return deck


# ── Helpers internos ──────────────────────────────────────────

def _adicionar_se(deck: List[Card], pericias: dict,
                  nome_pericia: str, carta_base: Card) -> None:
    """Adiciona carta ao deck se o investigador tem a pericia (valor > 0)."""
    val = pericias.get(nome_pericia, 0)
    if val > 0:
        deck.append(_clonar_com_valor(carta_base, val))


def _clonar_com_valor(carta: Card, valor: int) -> Card:
    """Retorna cópia da carta com valor_pericia preenchido."""
    import dataclasses
    return dataclasses.replace(carta, valor_pericia=valor)


def efeito_chao_para_enum(nome: str) -> Optional[EfeitoAmbiental]:
    """Converte string do efeito de chão para enum."""
    mapa = {
        "FOGO":       EfeitoAmbiental.FOGO,
        "OLEO":       EfeitoAmbiental.OLEO,
        "NEVOA":      EfeitoAmbiental.NEVOA,
        "ARBUSTO":    EfeitoAmbiental.ARBUSTO,
        "AGUA_BENTA": EfeitoAmbiental.AGUA_BENTA,
        "SANGUE":     EfeitoAmbiental.SANGUE,
    }
    return mapa.get(nome.upper())
