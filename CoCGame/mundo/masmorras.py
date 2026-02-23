"""
mundo/masmorras.py — Definição das masmorras acessíveis pelo mundo.

Cada masmorra tem: nome, mapa (grid), lista de inimigos e objetos.
Importado por tela_mundo.py ao lançar TelaMasmorra.

Inclui também os INTERIORES dos locais TORN (biblioteca, hospital, etc.)
acessados via ação "explorar" em TelaLocal.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from engine.entidade import Inimigo, Engendro


# ══════════════════════════════════════════════════════════════
# MAPAS
# ══════════════════════════════════════════════════════════════

# Catacumbas do Porto (abaixo das docas)
MAPA_CATACUMBAS_PORTO = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 2],
    [2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 2],
    [2, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 3, 3, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 2, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 4, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Mansão Corbitt — Térreo
MAPA_MANSAO_TERREO = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 1, 1, 2, 1, 1, 1, 1, 3, 1, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2],
    [2, 2, 2, 1, 2, 2, 1, 1, 2, 2, 1, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Mansão Corbitt — Porão (mais ameaçador)
MAPA_MANSAO_PORAO = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 2, 1, 1, 1, 2, 2, 1, 1, 1, 2],
    [2, 1, 2, 1, 1, 1, 1, 1, 1, 3, 1, 2],
    [2, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Cemitério à noite
MAPA_CEMITERIO_NOITE = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 3, 1, 1, 1, 3, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 1, 1, 3, 1, 1, 1, 3, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 3, 1, 1, 1, 3, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]


# ══════════════════════════════════════════════════════════════
# REGISTRO DE MASMORRAS
# ══════════════════════════════════════════════════════════════

MASMORRAS: Dict[str, dict] = {
    "catacumbas_porto": {
        "nome": "Catacumbas do Porto",
        "mapa": MAPA_CATACUMBAS_PORTO,
        "inimigos": [
            Inimigo("Cultista",  col=8,  linha=2),
            Inimigo("Cultista",  col=12, linha=4),
            Inimigo("Cultista",  col=10, linha=7),
            Engendro("Guardião", col=14, linha=9,
                     hp=18, forca=75, tamanho=85,
                     perda_san_avistamento=3),
        ],
        "descricao": (
            "Pedra úmida e musgosa. Tochas penduradas na parede revelam "
            "símbolos entalhados. A Irmandade da Pele usa este lugar há séculos."
        ),
    },

    "mansao_terreo": {
        "nome": "Mansão Corbitt — Térreo",
        "mapa": MAPA_MANSAO_TERREO,
        "inimigos": [
            Inimigo("Cultista Corbitt",  col=8, linha=2,
                    hp=10, forca=55, destreza=50),
            Inimigo("Cultista Corbitt",  col=10, linha=7),
        ],
        "descricao": "Pó e penumbra. Móveis cobertos com lençóis. O assoalho range a cada passo.",
    },

    "mansao_porao": {
        "nome": "Porão da Mansão Corbitt",
        "mapa": MAPA_MANSAO_PORAO,
        "inimigos": [
            Inimigo("Cultista",   col=6, linha=2),
            Inimigo("Cultista",   col=8, linha=5),
            Engendro("Walter Corbitt", col=8, linha=6,
                     hp=25, forca=85, tamanho=90, destreza=20,
                     perda_san_avistamento=5),
        ],
        "descricao": (
            "O porão da mansão. O ar é denso e gelado. "
            "Uma pedra negra no centro do chão pulsa com luz sinistra. "
            "E ele está aqui. Esperando."
        ),
    },

    "cemiterio_noite": {
        "nome": "Cemitério Silver Gate — Noite",
        "mapa": MAPA_CEMITERIO_NOITE,
        "inimigos": [
            Inimigo("Cultista Ritualista", col=6, linha=3,
                    hp=9, forca=50),
            Inimigo("Cultista Ritualista", col=10, linha=5),
            Engendro("Servo das Pedras",   col=12, linha=7,
                     hp=15, forca=70, tamanho=80,
                     perda_san_avistamento=4),
        ],
        "descricao": "O ritual começa. Figuras encapuzadas dançam entre as lápides.",
    },
}


def get_masmorra(masmorra_id: str) -> Optional[dict]:
    return MASMORRAS.get(masmorra_id)


# ══════════════════════════════════════════════════════════════
# MAPAS INTERIORES — LOCAIS TORN
# Acessados via ação "explorar" em TelaLocal.
# ══════════════════════════════════════════════════════════════

# Biblioteca Orne — salão principal
MAPA_BIBLIOTECA_INTERIOR = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 3, 1, 1, 1, 2, 1, 1, 1, 3, 1, 1, 1, 1, 2],
    [2, 3, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 3, 2],
    [2, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 1, 2, 2, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]
# tile 3 = estante (elevado/bloqueio); tile 4 = saída

# Hospital St. Mary's — enfermaria
MAPA_HOSPITAL_INTERIOR = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 3, 1, 2, 1, 3, 1, 3, 1, 3, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 3, 1, 2, 1, 3, 1, 3, 1, 3, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Delegacia — salão de registros
MAPA_DELEGACIA_INTERIOR = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 3, 1, 1, 2, 1, 1, 3, 3, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Porto — armazéns
MAPA_PORTO_INTERIOR = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 3, 1, 1, 1, 3, 3, 1, 1, 3, 3, 1, 1, 1, 3, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 3, 1, 1, 1, 3, 3, 1, 1, 3, 3, 1, 1, 1, 3, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Universidade Miskatonic — corredor
MAPA_UNIVERSIDADE_INTERIOR = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2],
    [2, 1, 3, 1, 2, 1, 3, 1, 1, 3, 1, 2, 1, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 1, 2, 2, 2, 1, 2, 2, 1, 2, 2, 2, 1, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 3, 1, 2, 1, 3, 1, 1, 3, 1, 2, 1, 3, 1, 2],
    [2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 4, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

MASMORRAS.update({
    "biblioteca_interior": {
        "nome": "Biblioteca Orne — Salão Principal",
        "mapa": MAPA_BIBLIOTECA_INTERIOR,
        "inimigos": [
            Inimigo("Cultista Encoberto", col=12, linha=3,
                    hp=8, forca=45, destreza=55,
                    tipo="humano", disposicao="Hostil"),
        ],
        "descricao": (
            "O salão principal da Biblioteca Orne está silencioso. "
            "Estantes altas bloqueiam a visão. Você ouve passos cuidadosos "
            "entre as prateleiras — alguém que não deveria estar aqui."
        ),
    },
    "hospital_interior": {
        "nome": "Hospital St. Mary's — Enfermaria",
        "mapa": MAPA_HOSPITAL_INTERIOR,
        "inimigos": [],
        "descricao": (
            "A enfermaria cheira a éter e desinfetante. Leitos vazios alinham "
            "as paredes. Um dos pacientes parece estar... acordado. "
            "E te olhando com olhos que não deveriam ser humanos."
        ),
    },
    "delegacia_interior": {
        "nome": "Delegacia de Arkham — Registros",
        "mapa": MAPA_DELEGACIA_INTERIOR,
        "inimigos": [],
        "descricao": (
            "O salão de registros está escuro. Arquivos e pastas empilhados. "
            "Você precisa encontrar as fichas dos desaparecidos antes que alguém perceba."
        ),
    },
    "porto_armazem": {
        "nome": "Porto de Arkham — Armazém",
        "mapa": MAPA_PORTO_INTERIOR,
        "inimigos": [
            Inimigo("Contrabandista",  col=12, linha=3,
                    hp=9, forca=60, destreza=50,
                    tipo="humano", disposicao="Hostil"),
            Inimigo("Contrabandista",  col=16, linha=5,
                    hp=9, forca=55, destreza=45,
                    tipo="humano", disposicao="Hostil"),
        ],
        "descricao": (
            "O armazém está cheio de caixas sem identificação. "
            "Homens armados vigiam a carga. A Irmandade usa este lugar "
            "para trazer 'materiais' de além-mar."
        ),
    },
    "universidade_interior": {
        "nome": "Universidade Miskatonic — Corredor dos Tomos",
        "mapa": MAPA_UNIVERSIDADE_INTERIOR,
        "inimigos": [
            Inimigo("Assistente Corrompido", col=12, linha=2,
                    hp=7, forca=40, destreza=60,
                    tipo="humano", disposicao="Hostil"),
        ],
        "descricao": (
            "Os corredores da biblioteca da Miskatonic. "
            "Tomos proibidos guardam segredos que destroem mentes. "
            "Um assistente te observa com suspeita — ou será que ele já não é ele mesmo?"
        ),
    },
})
