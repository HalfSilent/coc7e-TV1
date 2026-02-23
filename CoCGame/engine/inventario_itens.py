"""
engine/inventario_itens.py — Catálogo de itens para CoC 7e (Arkham, anos 1920).

📖 Referência: Livro do Guardião CoC 7e, pág. 105-108 (tabela de armas),
   pág. 57-60 (equipamento padrão), cap. 4 (tomos dos Mitos).

Cada item tem:
  - Stats idênticos à tabela oficial (dano, alcance, tiros, perícia)
  - Valor em US$ correto para 1920 (fontes históricas + CoC equipment list)
  - Ícone mapeado dos assets DENZI/Kenney disponíveis

Uso:
    from engine.inventario_itens import CATALOGO, criar_item

    item = criar_item("revolver_38")
    ok, msg = jogador.inventario.adicionar(item)
"""
from __future__ import annotations

from typing import Dict, Optional

from engine.inventario import Item, TipoItem


# ══════════════════════════════════════════════════════════════
# CATÁLOGO PRINCIPAL
# Chave: item_id  →  kwargs para Item()
# ══════════════════════════════════════════════════════════════

_DADOS_CATALOGO: Dict[str, dict] = {

    # ──────────────────────────────────────────────────────────
    # ARMAS DE FOGO
    # 📖 CoC 7e pág. 106 — tabela "Armas de Fogo"
    # ──────────────────────────────────────────────────────────

    "revolver_38": dict(
        nome="Revólver .38",
        tipo=TipoItem.ARMA,
        descricao=(
            "Revólver padrão da polícia americana dos anos 1920. "
            "Confiável e fácil de manter."
        ),
        peso=0.9, valor=12.0,
        pericia="Armas de Fogo (.38)",
        dano="1D10",
        alcance="15m",
        tiros=6,
        mal_funcionamento=100,
        icone_id="shortblades",   # DENZI skills — mais próximo disponível
    ),

    "pistola_45": dict(
        nome="Pistola .45",
        tipo=TipoItem.ARMA,
        descricao=(
            "Colt M1911 — pistola semi-automática de grande calibre, "
            "padrão das forças armadas dos EUA."
        ),
        peso=1.1, valor=20.0,
        pericia="Armas de Fogo (.45)",
        dano="1D10+2",
        alcance="15m",
        tiros=7,
        mal_funcionamento=100,
        icone_id="shortblades",
    ),

    "espingarda_calibre12": dict(
        nome="Espingarda Calibre 12",
        tipo=TipoItem.ARMA,
        descricao=(
            "Escopeta de dois canos — devastadora em curto alcance, "
            "mas barulhenta e difícil de esconder."
        ),
        peso=3.2, valor=15.0,
        pericia="Armas de Fogo (Espingarda)",
        dano="4D6/2D6/1D6",       # curto/médio/longo
        alcance="10m/20m/50m",
        tiros=2,
        mal_funcionamento=100,
        icone_id="bows",           # mais próximo disponível
    ),

    "rifle_springfield": dict(
        nome="Rifle Springfield",
        tipo=TipoItem.ARMA,
        descricao=(
            "Rifle bolt-action M1903 — preciso a longa distância, "
            "favorito de caçadores e ex-militares."
        ),
        peso=3.9, valor=25.0,
        pericia="Armas de Fogo (Rifle)",
        dano="2D6+4",
        alcance="110m",
        tiros=5,
        mal_funcionamento=100,
        icone_id="bows",
    ),

    # ──────────────────────────────────────────────────────────
    # ARMAS CORPO A CORPO
    # 📖 CoC 7e pág. 105 — tabela "Armas de Combate Corpo a Corpo"
    # ──────────────────────────────────────────────────────────

    "faca_cinto": dict(
        nome="Faca de Cinto",
        tipo=TipoItem.ARMA,
        descricao=(
            "Faca utilitária comum — fácil de carregar, "
            "discreta o suficiente para passar despercebida."
        ),
        peso=0.3, valor=1.0,
        pericia="Lutar (Lâmina)",
        dano="1D4+2",
        alcance="Toque",
        tiros=0,
        icone_id="shortblades",
    ),

    "cassetete": dict(
        nome="Cassetete de Borracha",
        tipo=TipoItem.ARMA,
        descricao="Cassetete policial padrão. Eficaz para incapacitar sem matar.",
        peso=0.5, valor=2.0,
        pericia="Lutar (Combate)",
        dano="1D6",
        alcance="Toque",
        tiros=0,
        icone_id="maces-flails",
    ),

    # ──────────────────────────────────────────────────────────
    # CONSUMÍVEIS
    # 📖 CoC 7e pág. 91: Primeiros Socorros restaura 1D3 HP
    # ──────────────────────────────────────────────────────────

    "kit_primeiros_socorros": dict(
        nome="Kit de Primeiros Socorros",
        tipo=TipoItem.CONSUMIVEL,
        descricao=(
            "Bandagens, antisséptico e ataduras. "
            "Primeiros Socorros restaura 1D3 HP."
        ),
        peso=0.8, valor=1.5,
        cura_hp="1D3",
        empilhavel=False,
        icone_id="curing",
    ),

    "bandagem": dict(
        nome="Bandagem",
        tipo=TipoItem.CONSUMIVEL,
        descricao="Bandagem simples de gaze. Estanca sangramento leve.",
        peso=0.1, valor=0.25,
        cura_hp="1",
        empilhavel=True,
        icone_id="curing",
    ),

    "morfina": dict(
        nome="Morfina (ampola)",
        tipo=TipoItem.CONSUMIVEL,
        descricao=(
            "Opioide para dor intensa. Restaura mais HP mas pode causar dependência "
            "(Guardião decide após uso repetido)."
        ),
        peso=0.1, valor=2.0,
        cura_hp="2D6",
        cura_san=0,
        empilhavel=True,
        icone_id="curing",
    ),

    "alcool_para_nervos": dict(
        nome="Whiskey (garrafa)",
        tipo=TipoItem.CONSUMIVEL,
        descricao=(
            "Uma dose de whiskey acalma os nervos. "
            "Restaura 1D3 SAN mas prejudica testes de Inteligência na próxima cena."
        ),
        peso=0.5, valor=0.5,
        cura_san=3,   # 1D3 médio
        icone_id="curing",
    ),

    # ──────────────────────────────────────────────────────────
    # PISTAS / DOCUMENTOS
    # ──────────────────────────────────────────────────────────

    "carta_anonima": dict(
        nome="Carta Anônima",
        tipo=TipoItem.PISTA,
        descricao=(
            'Papel amarelado com escrita apressada: "Não confie em '
            'ninguém do Clube Hermético. Eles sabem onde você mora."'
        ),
        peso=0.01, valor=0.0,
        icone_id="divination_a",
    ),

    "foto_ritual": dict(
        nome="Fotografia do Ritual",
        tipo=TipoItem.PISTA,
        descricao=(
            "Foto desfocada de figuras encapuzadas ao redor de um altar de pedra. "
            "No verso: 'Pedreira Arkham - Lua Nova'."
        ),
        peso=0.01, valor=0.0,
        icone_id="divination_a",
    ),

    "manifesto_do_porto": dict(
        nome="Manifesto de Carga",
        tipo=TipoItem.PISTA,
        descricao=(
            "Documento oficial do Porto de Arkham. "
            "Uma entrada marcada a lápis: 'Entrega para W.H. — Cais 7, meia-noite'."
        ),
        peso=0.05, valor=0.0,
        icone_id="divination_a",
    ),

    "diario_walters": dict(
        nome="Diário do Prof. Walters",
        tipo=TipoItem.PISTA,
        descricao=(
            "Diário encadernado em couro. As últimas entradas falam de "
            "'uma geometria que não deveria existir' e 'o som abaixo das fundações'."
        ),
        peso=0.3, valor=0.0,
        icone_id="divination_b",
    ),

    # ──────────────────────────────────────────────────────────
    # TOMOS DOS MITOS
    # 📖 CoC 7e cap. 4 — "Tomos e Artefatos"
    # ──────────────────────────────────────────────────────────

    "pnakotic_manuscripts": dict(
        nome="Manuscritos Pnakóticos (fragmento)",
        tipo=TipoItem.TOME,
        descricao=(
            "Fragmento de uma das mais antigas compilações do Conhecimento dos Mitos. "
            "O texto narra eventos anteriores à humanidade."
        ),
        peso=0.6, valor=0.0,
        idioma="Inglês (tradução moderna)",
        tempo_estudo=4,    # semanas
        custo_san=1,
        ganho_mitos=3,
        magias=[],
        icone_id="necromancy_a",
    ),

    "cultos_des_goules": dict(
        nome="Cultes des Goules",
        tipo=TipoItem.TOME,
        descricao=(
            "Grimório francês do século XVIII descrevendo rituais de necromancia "
            "e convocação de criaturas noturnas."
        ),
        peso=0.8, valor=0.0,
        idioma="Francês",
        tempo_estudo=6,
        custo_san=2,
        ganho_mitos=5,
        magias=["Convocar/Afastar Ghoul"],
        icone_id="necromancy_b",
    ),

    # ──────────────────────────────────────────────────────────
    # MISC — Equipamento utilitário
    # ──────────────────────────────────────────────────────────

    "lanterna": dict(
        nome="Lanterna Elétrica",
        tipo=TipoItem.MISC,
        descricao=(
            "Lanterna de pilhas — essencial para explorar porões, "
            "catacumbas e locais mal iluminados."
        ),
        peso=0.6, valor=2.0,
        icone_id="explore",
    ),

    "corda_15m": dict(
        nome="Corda (15m)",
        tipo=TipoItem.MISC,
        descricao="Corda de nylon resistente. Útil para escalada, amarrar suspeitos…",
        peso=1.5, valor=1.0,
        icone_id="explore",
    ),

    "camera_fotografica": dict(
        nome="Câmera Fotográfica",
        tipo=TipoItem.MISC,
        descricao=(
            "Kodak Brownie — câmera de caixa simples. "
            "Registrar evidências pode ser a diferença entre acreditar e não acreditar."
        ),
        peso=0.7, valor=8.0,
        icone_id="character_data",
    ),

    "chave_universal": dict(
        nome="Chave Universal",
        tipo=TipoItem.MISC,
        descricao="Conjunto de gazuas. Testes de Fechaduras com bônus.",
        peso=0.2, valor=3.0,
        icone_id="traps_locks",
    ),
}


# ══════════════════════════════════════════════════════════════
# CATÁLOGO PÚBLICO
# ══════════════════════════════════════════════════════════════

CATALOGO: Dict[str, dict] = _DADOS_CATALOGO


def criar_item(item_id: str, quantidade: int = 1) -> Optional[Item]:
    """
    Cria e retorna um Item pelo ID, ou None se não encontrado.

    Uso:
        item = criar_item("revolver_38")
        item = criar_item("bandagem", 3)
    """
    dados = _DADOS_CATALOGO.get(item_id)
    if not dados:
        return None
    kwargs = dict(dados)     # cópia para não mutar o catálogo
    kwargs["id"] = item_id
    if quantidade != 1:
        kwargs["quantidade"] = quantidade
    return Item(**kwargs)


def ids_por_tipo(tipo: TipoItem) -> list[str]:
    """Retorna lista de item_ids filtrados por tipo."""
    return [
        iid for iid, dados in _DADOS_CATALOGO.items()
        if dados.get("tipo") == tipo
    ]
