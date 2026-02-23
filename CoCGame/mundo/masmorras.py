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
from engine.grid.objeto import ObjetoMasmorra, OpcaoMenu


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
        "tema": "biblioteca",
        "mapa": MAPA_BIBLIOTECA_INTERIOR,
        "inimigos": [
            Inimigo("Cultista Encoberto", col=12, linha=3,
                    hp=8, forca=45, destreza=55,
                    tipo="humano", disposicao="Hostil"),
        ],
        "objetos": [
            ObjetoMasmorra(
                col=4, linha=1, tipo="estante",
                nome="Estante — Ocultismo",
                descricao="Fileiras de livros encadernados em couro escuro. "
                           "Títulos em latim e árabe brilham nas lombadas.",
                sprite_tipo="estante",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Pesquisar rituais e invocações",
                        pericia="ocultismo",
                        pista=(
                            "Você encontra 'De Vermis Mysteriis'. Uma passagem sublinhada: "
                            "'O Portal só se abre quando três velas negras iluminam a pedra angular'."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Procurar história local de Arkham",
                        pericia="historia",
                        pista=(
                            "Um panfleto de 1899 descreve desaparecimentos perto do cais — "
                            "os mesmos locais mencionados nos jornais de hoje."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="C",
                        texto="Pegar um livro ao acaso",
                        sem_check=True,
                        item="livro_misterioso",
                        pista="Um tomo sem título cai em suas mãos. As páginas estão em branco… por enquanto.",
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=12, linha=1, tipo="estante",
                nome="Estante — Ciências Proibidas",
                descricao="Uma seção trancada com corrente. A corrente parece enfraquecida.",
                sprite_tipo="estante",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Forçar a corrente [Força]",
                        pericia="forca",
                        pista=(
                            "A corrente cede. Dentro: uma cópia do Necronomicon com anotações "
                            "à mão — 'Reunião na Pedreira — 3a feira, lua nova'."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Examinar o lacre sem abrir [Furtividade]",
                        pericia="furtividade",
                        pista="O lacre tem um símbolo da Irmandade da Pele. Alguém colocou isto aqui recentemente.",
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=7, linha=6, tipo="nota",
                nome="Mesa de Pesquisa — Notas Abandonadas",
                descricao="Papéis espalhados de forma apressada. Alguém foi interrompido.",
                sprite_tipo="mesa",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Ler os papéis",
                        sem_check=True,
                        pista=(
                            "Rascunhos sobre coordenadas geográficas e datas. "
                            "Uma linha repetida: 'Quando as estrelas se alinham, o Grande Sonhador desperta'."
                        ),
                    ),
                ],
            ),
        ],
        "descricao": (
            "O salão principal da Biblioteca Orne está silencioso. "
            "Estantes altas bloqueiam a visão. Você ouve passos cuidadosos "
            "entre as prateleiras — alguém que não deveria estar aqui."
        ),
    },

    "hospital_interior": {
        "nome": "Hospital St. Mary's — Enfermaria",
        "tema": "hospital",
        "mapa": MAPA_HOSPITAL_INTERIOR,
        "inimigos": [],
        "objetos": [
            ObjetoMasmorra(
                col=2, linha=2, tipo="estante",
                nome="Leito 03 — Paciente Misterioso",
                descricao="O paciente tem olhos abertos, fixos no teto. Não pisca.",
                sprite_tipo="cama",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Examinar o paciente [Medicina]",
                        pericia="medicina",
                        pista=(
                            "As pupilas estão totalmente dilatadas. O pulso é lento demais. "
                            "Na nuca: um símbolo gravado na pele com instrumento cirúrgico."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Verificar o prontuário",
                        sem_check=True,
                        pista=(
                            "Nome: Thomas Whateley. Internado por 'crise nervosa aguda'. "
                            "Endereço: Rua Pickman, 14 — a mesma rua dos desaparecimentos."
                        ),
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=8, linha=2, tipo="estante",
                nome="Armário de Medicamentos",
                descricao="Trancado com cadeado. Através do vidro vê-se morfina e bandagens.",
                sprite_tipo="armario",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Forçar o cadeado [Conserto Mecânico]",
                        pericia="conserto_mecanico",
                        item="kit_medico",
                        pista="Você consegue abrir sem barulho. Leva morfina e bandagens.",
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Quebrar o vidro [Barulhento — sem check]",
                        sem_check=True,
                        item="kit_medico",
                        pista="O vidro quebra com estrondo. Você pega o kit, mas alguém certamente ouviu.",
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=3, linha=7, tipo="nota",
                nome="Pasta de Arquivos — Mesa da Enfermeira",
                descricao="Fichas de admissão empilhadas. Datas dos últimos 3 dias.",
                sprite_tipo="mesa",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Revisar as fichas de admissão",
                        sem_check=True,
                        pista=(
                            "Seis admissões na última semana com o mesmo diagnóstico: "
                            "'dissociação severa'. Todos moravam perto do cais."
                        ),
                    ),
                ],
            ),
        ],
        "descricao": (
            "A enfermaria cheira a éter e desinfetante. Leitos vazios alinham "
            "as paredes. Um dos pacientes parece estar... acordado. "
            "E te olhando com olhos que não deveriam ser humanos."
        ),
    },

    "delegacia_interior": {
        "nome": "Delegacia de Arkham — Registros",
        "tema": "delegacia",
        "mapa": MAPA_DELEGACIA_INTERIOR,
        "inimigos": [],
        "objetos": [
            ObjetoMasmorra(
                col=2, linha=2, tipo="arquivo",
                nome="Arquivos de Casos Abertos",
                descricao="Pastas cinzentas abarrotadas de papéis. Algumas têm carimbos CONFIDENCIAL.",
                sprite_tipo="arquivo",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Procurar fichas de desaparecidos [Biblioteca]",
                        pericia="biblioteca",
                        pista=(
                            "Você encontra seis fichas de pessoas desaparecidas em 30 dias. "
                            "Todos trabalhavam no porto. Último avistamento: Armazém 7."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Fotografar documentos [Furtividade]",
                        pericia="furtividade",
                        item="fotografia",
                        pista="Você tira fotos de registros comprometedores sem ser notado.",
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=9, linha=2, tipo="arquivo",
                nome="Arquivo Secreto — Gaveta Trancada",
                descricao="Uma gaveta com fechadura diferente das outras. Parece mais nova.",
                sprite_tipo="arquivo",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Arrombar a gaveta [Conserto Mecânico]",
                        pericia="conserto_mecanico",
                        pista=(
                            "Dentro: relatórios de investigação suprimidos. "
                            "O delegado Harden está em contato com a Irmandade desde 1918."
                        ),
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=2, linha=6, tipo="nota",
                nome="Mural de Evidências",
                descricao="Fotos e papéis pregados na parede com barbante vermelho.",
                sprite_tipo="mural",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Analisar o mural [Inteligência]",
                        pericia="inteligencia",
                        pista=(
                            "Os barbantes ligam os desaparecimentos a datas de lua nova. "
                            "A próxima é em dois dias."
                        ),
                    ),
                ],
            ),
        ],
        "descricao": (
            "O salão de registros está escuro. Arquivos e pastas empilhados. "
            "Você precisa encontrar as fichas dos desaparecidos antes que alguém perceba."
        ),
    },

    "porto_armazem": {
        "nome": "Porto de Arkham — Armazém",
        "tema": "porto",
        "mapa": MAPA_PORTO_INTERIOR,
        "inimigos": [
            Inimigo("Contrabandista",  col=12, linha=3,
                    hp=9, forca=60, destreza=50,
                    tipo="humano", disposicao="Hostil"),
            Inimigo("Contrabandista",  col=16, linha=5,
                    hp=9, forca=55, destreza=45,
                    tipo="humano", disposicao="Hostil"),
        ],
        "objetos": [
            ObjetoMasmorra(
                col=2, linha=2, tipo="estante",
                nome="Caixotes Sem Identificação",
                descricao="Madeira reforçada. Sem etiquetas. Um cheiro metálico vaza por entre as tábuas.",
                sprite_tipo="caixa",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Arrombar um caixote [Força]",
                        pericia="forca",
                        pista=(
                            "Dentro: armas de fogo e estátuas de pedra negra com símbolos estranhos. "
                            "Este carregamento veio de Innsmouth."
                        ),
                        item="revolver",
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Examinar os símbolos externamente [Ocultismo]",
                        pericia="ocultismo",
                        pista=(
                            "Os símbolos nas tampas são selos de transporte da Irmandade — "
                            "indicam conteúdo 'para o Ritual da Convergência'."
                        ),
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=7, linha=2, tipo="estante",
                nome="Barris de Substância Escura",
                descricao="Óleo viscoso e de coloração estranha. Não é alcatrão.",
                sprite_tipo="barril",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Coletar amostra [Ciências]",
                        pericia="ciencias",
                        item="amostra_quimica",
                        pista=(
                            "Análise visual: a substância reage à luz da lanterna de forma "
                            "anômala. Não é orgânica. Não deveria existir."
                        ),
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=5, linha=5, tipo="nota",
                nome="Manifesto de Carga — Prancheta",
                descricao="Papéis presos com grampo. Escrita cursiva apressada.",
                sprite_tipo="mesa",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Ler o manifesto",
                        sem_check=True,
                        pista=(
                            "Entrega para 'W.H.' — inicial que aparece nos outros documentos. "
                            "Endereço de entrega: Mansão Corbitt, Rua Pickman."
                        ),
                    ),
                ],
            ),
        ],
        "descricao": (
            "O armazém está cheio de caixas sem identificação. "
            "Homens armados vigiam a carga. A Irmandade usa este lugar "
            "para trazer 'materiais' de além-mar."
        ),
    },

    "universidade_interior": {
        "nome": "Universidade Miskatonic — Corredor dos Tomos",
        "tema": "universidade",
        "mapa": MAPA_UNIVERSIDADE_INTERIOR,
        "inimigos": [
            Inimigo("Assistente Corrompido", col=12, linha=2,
                    hp=7, forca=40, destreza=60,
                    tipo="humano", disposicao="Hostil"),
        ],
        "objetos": [
            ObjetoMasmorra(
                col=2, linha=2, tipo="estante",
                nome="Vitrine de Artefatos",
                descricao="Objetos pré-colombianos e egípcios em exposição. Um deles parece pulsar.",
                sprite_tipo="estante",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Examinar o artefato pulsante [Ocultismo]",
                        pericia="ocultismo",
                        pista=(
                            "É um fragmento de pedra estelar — material não-terrestre. "
                            "Usado em rituais de invocação. O Prof. Armitage o catalogou como 'perigoso'."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Quebrar o vidro e pegar o artefato [Furtividade]",
                        pericia="furtividade",
                        item="fragmento_estelar",
                        pista="Você leva o fragmento. Ele está frio ao toque — frio demais.",
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=6, linha=2, tipo="estante",
                nome="Tomos Proibidos — Sala Armitage",
                descricao="Prateleiras com livros de acesso restrito. A porta está entreaberta.",
                sprite_tipo="estante",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Pesquisar o Grande Sonhador [Ocultismo]",
                        pericia="ocultismo",
                        pista=(
                            "Nas anotações do Prof. Armitage: 'Cthulhu não está morto — "
                            "dorme em R'lyeh. Quando as estrelas se alinharem, vai despertar'."
                        ),
                    ),
                    OpcaoMenu(
                        tecla="B",
                        texto="Buscar registros de alunos desaparecidos [Biblioteca]",
                        pericia="biblioteca",
                        pista=(
                            "Três estudantes desapareceram após frequentar estas salas. "
                            "Todos membros do Clube de Estudos Esotéricos — presidido pelo Prof. Walters."
                        ),
                    ),
                ],
            ),
            ObjetoMasmorra(
                col=2, linha=6, tipo="nota",
                nome="Diário do Prof. Walters",
                descricao="Caído debaixo de uma mesa. As últimas páginas estão molhadas de algo.",
                sprite_tipo="mesa",
                opcoes_menu=[
                    OpcaoMenu(
                        tecla="A",
                        texto="Ler as últimas entradas",
                        sem_check=True,
                        pista=(
                            "Última entrada, 3 dias atrás: 'Eles sabem que eu sei. "
                            "Se algo me acontecer, procure na câmara abaixo da pedreira de Arkham'."
                        ),
                    ),
                ],
            ),
        ],
        "descricao": (
            "Os corredores da biblioteca da Miskatonic. "
            "Tomos proibidos guardam segredos que destroem mentes. "
            "Um assistente te observa com suspeita — ou será que ele já não é ele mesmo?"
        ),
    },
})
