"""
sistema_campanha.py — Esquema de dados e serialização JSON para campanhas CoC 7e.

Define todas as estruturas de uma campanha (mapas, personagens, diálogos,
triggers) e provê carga/gravação em JSON. Independente de pygame — pode ser
importado em qualquer contexto (editor, motor de jogo, scripts externos).

Estrutura em disco:
    <pasta_campanha>/
        campanha.json           ← metadados e lista de IDs
        personagens.json        ← todos os personagens (dict id→dados)
        dialogos.json           ← todos os diálogos
        mapas/
            <mapa_id>.json      ← um arquivo por mapa

Uso rápido:
    c = Campanha.nova("Minha Campanha", autor="Keeper")
    c.salvar("/path/para/pasta")
    c2 = Campanha.carregar("/path/para/pasta")
    print(c2.validar())   # lista de avisos
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ── Versão do schema ───────────────────────────────────────────────────
VERSAO_SCHEMA = "1.0"


# ══════════════════════════════════════════════════════════════
# STATS (atributos do investigador / NPC)
# ══════════════════════════════════════════════════════════════

@dataclass
class Stats:
    hp:           int = 10
    san:          int = 50
    forca:        int = 50
    destreza:     int = 50
    inteligencia: int = 50
    constituicao: int = 50
    educacao:     int = 50
    aparencia:    int = 50
    poder:        int = 50

    @property
    def san_max(self) -> int:
        return self.poder


# ══════════════════════════════════════════════════════════════
# ITEM DE INVENTÁRIO
# ══════════════════════════════════════════════════════════════

@dataclass
class ItemInventario:
    id:        str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nome:      str = "Item"
    descricao: str = ""
    usos:      int = 1


# ══════════════════════════════════════════════════════════════
# PERSONAGEM
# ══════════════════════════════════════════════════════════════

class TipoPersonagem:
    INVESTIGADOR = "investigador"
    NPC_ALIADO   = "npc_aliado"
    CULTISTA     = "cultista"
    ENGENDRO     = "engendro"
    NEUTRO       = "neutro"
    TODOS = [INVESTIGADOR, NPC_ALIADO, CULTISTA, ENGENDRO, NEUTRO]


class TipoIA:
    NENHUMA   = "nenhuma"    # investigador / NPC passivo
    AGRESSIVO = "agressivo"  # atacar ao avistar o jogador
    PATRULHA  = "patrulha"   # patrulhar área
    REATIVO   = "reativo"    # só reagir se atacado
    FUGA      = "fuga"       # tentar escapar
    TODOS = [NENHUMA, AGRESSIVO, PATRULHA, REATIVO, FUGA]


@dataclass
class Personagem:
    id:          str
    nome:        str
    tipo:        str  = TipoPersonagem.CULTISTA
    sprite_id:   int  = 0             # índice do skin Male_0…Male_7
    ia:          str  = TipoIA.AGRESSIVO
    stats:       Stats = field(default_factory=Stats)
    inventario:  List[ItemInventario] = field(default_factory=list)
    background:  str  = ""
    spawn_col:   float = 1.0
    spawn_linha: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":          self.id,
            "nome":        self.nome,
            "tipo":        self.tipo,
            "sprite_id":   self.sprite_id,
            "ia":          self.ia,
            "stats":       asdict(self.stats),
            "inventario":  [asdict(it) for it in self.inventario],
            "background":  self.background,
            "spawn_col":   self.spawn_col,
            "spawn_linha": self.spawn_linha,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Personagem":
        return cls(
            id=d["id"],
            nome=d["nome"],
            tipo=d.get("tipo", TipoPersonagem.CULTISTA),
            sprite_id=d.get("sprite_id", 0),
            ia=d.get("ia", TipoIA.AGRESSIVO),
            stats=Stats(**d.get("stats", {})),
            inventario=[ItemInventario(**it) for it in d.get("inventario", [])],
            background=d.get("background", ""),
            spawn_col=d.get("spawn_col", 1.0),
            spawn_linha=d.get("spawn_linha", 1.0),
        )


# ══════════════════════════════════════════════════════════════
# ELEMENTOS DO MAPA
# ══════════════════════════════════════════════════════════════

@dataclass
class EfeitoMapa:
    """Efeito ambiental pré-colocado em uma célula do mapa."""
    col:     int
    linha:   int
    tipo:    str   # ex: "OLEO" | "FOGO" | "NEVOA" | "ARBUSTO" | "AGUA_BENTA" | "SANGUE"
    duracao: int = 99

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EfeitoMapa":
        return cls(**d)


@dataclass
class ObjetoMapa:
    """Objeto interativo (porta, item, altar, alavanca…)."""
    id:    str
    col:   int
    linha: int
    tipo:  str   # "porta" | "item" | "alavanca" | "altar" | "baú" | "corpo" | …
    props: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "col": self.col, "linha": self.linha,
                "tipo": self.tipo, "props": self.props}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ObjetoMapa":
        return cls(id=d["id"], col=d["col"], linha=d["linha"],
                   tipo=d["tipo"], props=d.get("props", {}))


@dataclass
class Trigger:
    """
    Zona ou evento que dispara uma ação no jogo.

    tipo:    "zona"           → player entra na area
             "item_coletado"  → item específico coletado
             "dialogo_inicio" → inicia diálogo automático
             "combate"        → inicia combate com grupo
             "transicao"      → teleporta para outro mapa

    condicao: "sempre" | "evento:<ev_id>" | "flag:<nome>"
    acao:     "dialogo:<id>" | "combate:<grupo>" | "mapa:<id>:<col>:<linha>"
              "flag:<nome>" | "san:<delta>" | "evento:<nome>"
    """
    id:       str
    tipo:     str
    area:     List[Tuple[int, int]] = field(default_factory=list)
    condicao: str = "sempre"
    acao:     str = ""
    params:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "tipo": self.tipo,
            "area": [list(p) for p in self.area],
            "condicao": self.condicao, "acao": self.acao,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trigger":
        return cls(
            id=d["id"], tipo=d["tipo"],
            area=[tuple(p) for p in d.get("area", [])],
            condicao=d.get("condicao", "sempre"),
            acao=d.get("acao", ""),
            params=d.get("params", {}),
        )


@dataclass
class Conexao:
    """Transição entre mapas (portal/porta de saída)."""
    col:           int
    linha:         int
    destino_mapa:  str
    destino_col:   int
    destino_linha: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Conexao":
        return cls(**d)


# ══════════════════════════════════════════════════════════════
# DADOS DO MAPA
# ══════════════════════════════════════════════════════════════

@dataclass
class DadosMapa:
    id:      str
    nome:    str
    largura: int = 12
    altura:  int = 10
    # tiles[linha][col] → int:  0=VAZIO  1=CHÃO  2=PAREDE  3=ELEVADO
    tiles:             List[List[int]]    = field(default_factory=list)
    efeitos:           List[EfeitoMapa]   = field(default_factory=list)
    objetos:           List[ObjetoMapa]   = field(default_factory=list)
    triggers:          List[Trigger]      = field(default_factory=list)
    conexoes:          List[Conexao]      = field(default_factory=list)
    personagens_spawn: List[str]          = field(default_factory=list)  # IDs

    def __post_init__(self):
        if not self.tiles:
            self._gerar_tiles_padrao()

    def _gerar_tiles_padrao(self):
        """Cria sala com bordas de parede e interior de chão."""
        self.tiles = []
        for l in range(self.altura):
            row = []
            for c in range(self.largura):
                borda = (l == 0 or l == self.altura - 1
                         or c == 0 or c == self.largura - 1)
                row.append(2 if borda else 1)
            self.tiles.append(row)

    def redimensionar(self, nova_largura: int, nova_altura: int):
        """Redimensiona preservando tiles existentes (preenche com 1=CHÃO)."""
        novo = []
        for l in range(nova_altura):
            row = []
            for c in range(nova_largura):
                borda = (l == 0 or l == nova_altura - 1
                         or c == 0 or c == nova_largura - 1)
                if l < len(self.tiles) and c < len(self.tiles[l]):
                    row.append(self.tiles[l][c])
                else:
                    row.append(2 if borda else 1)
            novo.append(row)
        self.tiles   = novo
        self.largura = nova_largura
        self.altura  = nova_altura

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "nome": self.nome,
            "largura": self.largura, "altura": self.altura,
            "tiles":    self.tiles,
            "efeitos":  [e.to_dict() for e in self.efeitos],
            "objetos":  [o.to_dict() for o in self.objetos],
            "triggers": [t.to_dict() for t in self.triggers],
            "conexoes": [c.to_dict() for c in self.conexoes],
            "personagens_spawn": self.personagens_spawn,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DadosMapa":
        return cls(
            id=d["id"], nome=d["nome"],
            largura=d["largura"], altura=d["altura"],
            tiles=d.get("tiles", []),
            efeitos=[EfeitoMapa.from_dict(e) for e in d.get("efeitos", [])],
            objetos=[ObjetoMapa.from_dict(o) for o in d.get("objetos", [])],
            triggers=[Trigger.from_dict(t) for t in d.get("triggers", [])],
            conexoes=[Conexao.from_dict(c) for c in d.get("conexoes", [])],
            personagens_spawn=d.get("personagens_spawn", []),
        )


# ══════════════════════════════════════════════════════════════
# DIÁLOGO
# ══════════════════════════════════════════════════════════════

@dataclass
class EscolhaDialogo:
    texto:   str
    proximo: Optional[str] = None  # ID do próximo nó (None = fim do diálogo)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EscolhaDialogo":
        return cls(**d)


@dataclass
class NoDialogo:
    id:            str
    personagem_id: str   # ID do Personagem que fala
    texto:         str
    efeito:        str = ""   # ex: "san:-3" | "evento:saber_segredo" | "item:revolver"
    escolhas:      List[EscolhaDialogo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "personagem_id": self.personagem_id,
            "texto": self.texto, "efeito": self.efeito,
            "escolhas": [e.to_dict() for e in self.escolhas],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NoDialogo":
        return cls(
            id=d["id"], personagem_id=d["personagem_id"],
            texto=d["texto"], efeito=d.get("efeito", ""),
            escolhas=[EscolhaDialogo.from_dict(e) for e in d.get("escolhas", [])],
        )


@dataclass
class Dialogo:
    id:         str
    titulo:     str
    no_inicial: str = ""
    nos:        Dict[str, NoDialogo] = field(default_factory=dict)

    def adicionar_no(self, no: NoDialogo):
        self.nos[no.id] = no
        if not self.no_inicial:
            self.no_inicial = no.id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "titulo": self.titulo,
            "no_inicial": self.no_inicial,
            "nos": {k: v.to_dict() for k, v in self.nos.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Dialogo":
        nos = {k: NoDialogo.from_dict(v) for k, v in d.get("nos", {}).items()}
        return cls(
            id=d["id"], titulo=d["titulo"],
            no_inicial=d.get("no_inicial", ""),
            nos=nos,
        )


# ══════════════════════════════════════════════════════════════
# CAMPANHA
# ══════════════════════════════════════════════════════════════

@dataclass
class Campanha:
    nome:                  str
    versao:                str = VERSAO_SCHEMA
    autor:                 str = ""
    descricao:             str = ""
    mapa_inicial:          str = ""
    personagem_jogador_id: str = ""
    mapas:       Dict[str, DadosMapa]  = field(default_factory=dict)
    personagens: Dict[str, Personagem] = field(default_factory=dict)
    dialogos:    Dict[str, Dialogo]    = field(default_factory=dict)

    # ── factory ───────────────────────────────────────────────

    @classmethod
    def nova(cls, nome: str, autor: str = "") -> "Campanha":
        """Cria campanha vazia com mapa inicial e investigador padrões."""
        c = cls(nome=nome, autor=autor)

        mapa_id = "mapa_01"
        c.mapas[mapa_id] = DadosMapa(id=mapa_id, nome="Cena Inicial",
                                      largura=12, altura=10)
        c.mapa_inicial = mapa_id

        j = Personagem(
            id="jogador", nome="Investigador",
            tipo=TipoPersonagem.INVESTIGADOR,
            ia=TipoIA.NENHUMA,
            sprite_id=0,
            spawn_col=2.0, spawn_linha=2.0,
        )
        c.personagens[j.id] = j
        c.personagem_jogador_id = j.id
        c.mapas[mapa_id].personagens_spawn.append(j.id)

        return c

    # ── persistência ──────────────────────────────────────────

    def salvar(self, pasta: str):
        """Serializa campanha em `pasta/`."""
        os.makedirs(pasta, exist_ok=True)
        os.makedirs(os.path.join(pasta, "mapas"), exist_ok=True)

        _salvar_json(os.path.join(pasta, "campanha.json"), {
            "versao_schema":         VERSAO_SCHEMA,
            "nome":                  self.nome,
            "versao":                self.versao,
            "autor":                 self.autor,
            "descricao":             self.descricao,
            "mapa_inicial":          self.mapa_inicial,
            "personagem_jogador_id": self.personagem_jogador_id,
            "mapas_ids":             list(self.mapas.keys()),
        })

        _salvar_json(os.path.join(pasta, "personagens.json"),
                     {k: v.to_dict() for k, v in self.personagens.items()})

        _salvar_json(os.path.join(pasta, "dialogos.json"),
                     {k: v.to_dict() for k, v in self.dialogos.items()})

        for mid, mapa in self.mapas.items():
            _salvar_json(os.path.join(pasta, "mapas", f"{mid}.json"),
                         mapa.to_dict())

    @classmethod
    def carregar(cls, pasta: str) -> "Campanha":
        """Carrega campanha de `pasta/`."""
        meta = _carregar_json(os.path.join(pasta, "campanha.json"))
        c = cls(
            nome=meta["nome"],
            versao=meta.get("versao", VERSAO_SCHEMA),
            autor=meta.get("autor", ""),
            descricao=meta.get("descricao", ""),
            mapa_inicial=meta.get("mapa_inicial", ""),
            personagem_jogador_id=meta.get("personagem_jogador_id", ""),
        )

        for k, v in _carregar_json(
                os.path.join(pasta, "personagens.json")).items():
            c.personagens[k] = Personagem.from_dict(v)

        dial_path = os.path.join(pasta, "dialogos.json")
        if os.path.exists(dial_path):
            for k, v in _carregar_json(dial_path).items():
                c.dialogos[k] = Dialogo.from_dict(v)

        for mid in meta.get("mapas_ids", []):
            p = os.path.join(pasta, "mapas", f"{mid}.json")
            if os.path.exists(p):
                c.mapas[mid] = DadosMapa.from_dict(_carregar_json(p))

        return c

    def validar(self) -> List[str]:
        """Retorna lista de avisos/erros de consistência."""
        warns: List[str] = []

        if not self.nome.strip():
            warns.append("Campanha sem nome.")
        if not self.mapa_inicial:
            warns.append("Nenhum mapa inicial definido.")
        elif self.mapa_inicial not in self.mapas:
            warns.append(f"Mapa inicial '{self.mapa_inicial}' não encontrado.")
        if not self.personagem_jogador_id:
            warns.append("Nenhum personagem jogador definido.")
        elif self.personagem_jogador_id not in self.personagens:
            warns.append(f"Personagem jogador '{self.personagem_jogador_id}' não encontrado.")

        for did, dial in self.dialogos.items():
            if dial.no_inicial and dial.no_inicial not in dial.nos:
                warns.append(f"Diálogo '{did}': nó inicial '{dial.no_inicial}' não existe.")
            for nid, no in dial.nos.items():
                for esc in no.escolhas:
                    if esc.proximo and esc.proximo not in dial.nos:
                        warns.append(
                            f"Diálogo '{did}', nó '{nid}': "
                            f"escolha aponta para nó inexistente '{esc.proximo}'."
                        )

        return warns

    # ── utilitários ───────────────────────────────────────────

    def novo_mapa(self, nome: str = "Novo Mapa",
                  largura: int = 12, altura: int = 10) -> DadosMapa:
        """Cria e registra um novo mapa vazio."""
        mid = f"mapa_{len(self.mapas) + 1:02d}"
        while mid in self.mapas:
            mid = f"mapa_{str(uuid.uuid4())[:6]}"
        m = DadosMapa(id=mid, nome=nome, largura=largura, altura=altura)
        self.mapas[mid] = m
        return m

    def novo_personagem(self, nome: str = "NPC",
                        tipo: str = TipoPersonagem.CULTISTA) -> Personagem:
        """Cria e registra um novo personagem."""
        pid = f"p_{str(uuid.uuid4())[:8]}"
        p = Personagem(id=pid, nome=nome, tipo=tipo)
        self.personagens[pid] = p
        return p

    def novo_dialogo(self, titulo: str = "Novo Diálogo") -> Dialogo:
        """Cria e registra um novo diálogo."""
        did = f"d_{str(uuid.uuid4())[:6]}"
        d = Dialogo(id=did, titulo=titulo)
        self.dialogos[did] = d
        return d


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════

def _salvar_json(caminho: str, data: Any):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _carregar_json(caminho: str) -> Any:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)
