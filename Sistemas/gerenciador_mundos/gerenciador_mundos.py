"""
gerenciador_mundos.py — Gerencia mundos de campanha.

Um "mundo" é um conjunto de chunks + metadados associado a uma campanha.
Cada mundo reside em  Mundos/{id}/  e contém:

  mundo.json   → metadados (dimensões, tileset, spawn, bairros…)
  chunks/      → arquivos .npy com os tiles procedurais
  locais/      → chunks handmade (.tmj) específicos da campanha
  save.json    → estado salvo do jogador e NPCs
  temporal.db  → estado temporal (hora, dia, clima…)

Uma campanha aponta para um mundo via um arquivo ponteiro no seu
próprio diretório:

  Modulos de Campanha/Degraus para o abismo/mundo.json → {"mundo": "Rio1923"}

API pública
-----------
  listar()                    → list[str]  — ids de mundos disponíveis
  carregar(id)                → dict       — metadados de um mundo
  criar(id, **kwargs)         → dict       — cria novo mundo em Mundos/{id}/
  paths(mundo_ou_id)          → dict       — caminhos absolutos do mundo
  mundo_da_campanha(camp_dir) → str        — id do mundo de uma campanha
  salvar_meta(id, meta)       → None       — persiste mudanças em mundo.json
  bairro_em(mundo, cx, cy)    → str        — nome do bairro no chunk (cx,cy)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


# ── Raiz do projeto ───────────────────────────────────────────────────
_RAIZ   = Path(os.path.dirname(os.path.abspath(__file__)))
_MUNDOS = _RAIZ / "Mundos"

# ── Valores padrão para campos de mundo.json ─────────────────────────
_DEFAULTS: dict[str, Any] = {
    "largura":     8,
    "altura":      6,
    "chunk_w":    20,
    "chunk_h":    15,
    "tile_w":     32,
    "tile_h":     32,
    "fps":        60,
    "vel_normal": 128,
    "vel_corrida": 240,
    "spawn_chunk": [1, 1],
    "spawn_tile":  [10, 7],
    "tileset":     "",
    "bairros":     {},
}


# ══════════════════════════════════════════════════════════════════════
# Funções públicas
# ══════════════════════════════════════════════════════════════════════

def listar() -> list[str]:
    """Retorna lista de ids de todos os mundos em Mundos/."""
    if not _MUNDOS.exists():
        return []
    return [
        d.name
        for d in sorted(_MUNDOS.iterdir())
        if d.is_dir() and (d / "mundo.json").exists()
    ]


def carregar(id_mundo: str) -> dict:
    """
    Carrega e retorna os metadados de  Mundos/{id}/mundo.json.
    Valores ausentes são preenchidos com os defaults.
    Lança FileNotFoundError se o mundo não existir.
    """
    meta_path = _MUNDOS / id_mundo / "mundo.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"Mundo '{id_mundo}' não encontrado em {meta_path}"
        )
    with meta_path.open(encoding="utf-8") as f:
        data: dict = json.load(f)
    # Garante que id esteja presente
    data.setdefault("id", id_mundo)
    # Preenche defaults para campos ausentes
    for k, v in _DEFAULTS.items():
        data.setdefault(k, v)
    return data


def criar(
    id_mundo: str,
    *,
    nome: str = "",
    campanha: str = "",
    **kwargs: Any,
) -> dict:
    """
    Cria a estrutura de diretórios e mundo.json para um novo mundo.
    Retorna o dict de metadados criado.
    Lança FileExistsError se o mundo já existir.
    """
    mundo_dir = _MUNDOS / id_mundo
    if (mundo_dir / "mundo.json").exists():
        raise FileExistsError(f"Mundo '{id_mundo}' já existe em {mundo_dir}")

    # Cria subdiretórios obrigatórios
    (mundo_dir / "chunks").mkdir(parents=True, exist_ok=True)
    (mundo_dir / "locais").mkdir(parents=True, exist_ok=True)

    # Monta metadados: defaults → kwargs → campos obrigatórios
    meta: dict[str, Any] = {**_DEFAULTS, **kwargs}
    meta["id"]       = id_mundo
    meta["nome"]     = nome or id_mundo
    meta["campanha"] = campanha

    _salvar_json(mundo_dir / "mundo.json", meta)
    return meta


def paths(mundo_ou_id: str | dict) -> dict[str, str]:
    """
    Retorna um dict com todos os caminhos absolutos do mundo::

        {
          "raiz":     Mundos/{id}/
          "chunks":   Mundos/{id}/chunks/
          "locais":   Mundos/{id}/locais/
          "save":     Mundos/{id}/save.json
          "temporal": Mundos/{id}/temporal.db
          "meta":     Mundos/{id}/mundo.json
        }

    Aceita o id como string ou o dict retornado por ``carregar()``.
    """
    if isinstance(mundo_ou_id, dict):
        id_mundo = mundo_ou_id["id"]
    else:
        id_mundo = str(mundo_ou_id)

    raiz = _MUNDOS / id_mundo
    return {
        "raiz":     str(raiz),
        "chunks":   str(raiz / "chunks"),
        "locais":   str(raiz / "locais"),
        "save":     str(raiz / "save.json"),
        "temporal": str(raiz / "temporal.db"),
        "meta":     str(raiz / "mundo.json"),
    }


def mundo_da_campanha(camp_dir: str | Path) -> str:
    """
    Lê  {camp_dir}/mundo.json  (arquivo ponteiro) e retorna o id do mundo.

    O ponteiro tem o formato mínimo::

        {"mundo": "Rio1923"}

    Lança ``FileNotFoundError`` se o ponteiro não existir.
    Lança ``KeyError`` se o ponteiro não contiver a chave "mundo".
    """
    ponteiro = Path(camp_dir) / "mundo.json"
    if not ponteiro.exists():
        raise FileNotFoundError(
            f"Ponteiro de mundo não encontrado: {ponteiro}\n"
            'Crie um arquivo mundo.json com {"mundo": "<id>"} na pasta da campanha.'
        )
    with ponteiro.open(encoding="utf-8") as f:
        data = json.load(f)
    if "mundo" not in data:
        raise KeyError(f"Chave 'mundo' ausente em {ponteiro}")
    return str(data["mundo"])


def salvar_meta(id_mundo: str, meta: dict) -> None:
    """Persiste alterações no  Mundos/{id}/mundo.json."""
    meta_path = _MUNDOS / id_mundo / "mundo.json"
    if not meta_path.parent.exists():
        raise FileNotFoundError(
            f"Diretório do mundo não encontrado: {meta_path.parent}"
        )
    meta["id"] = id_mundo  # garante consistência
    _salvar_json(meta_path, meta)


def bairro_em(mundo: dict, cx: int, cy: int) -> str:
    """
    Retorna o nome do bairro no chunk (cx, cy).
    Retorna string vazia se não houver registro em mundo["bairros"].
    """
    return str(mundo.get("bairros", {}).get(f"{cx},{cy}", ""))


# ══════════════════════════════════════════════════════════════════════
# Helpers internos
# ══════════════════════════════════════════════════════════════════════

def _salvar_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════
# CLI de diagnóstico  →  python gerenciador_mundos.py
# ══════════════════════════════════════════════════════════════════════

def _cli() -> None:
    mundos = listar()
    if not mundos:
        print(f"Nenhum mundo encontrado em {_MUNDOS}")
        print("Use  gerenciador_mundos.criar(id, ...)  para criar o primeiro mundo.")
        return

    print(f"Mundos disponíveis em {_MUNDOS}:\n")
    for id_mundo in mundos:
        try:
            m = carregar(id_mundo)
            p = paths(m)
            nx, ny = m["largura"], m["altura"]
            cw, ch = m["chunk_w"], m["chunk_h"]
            sc = m["spawn_chunk"]
            st = m["spawn_tile"]

            print(f"  [{id_mundo}]")
            print(f"    nome     : {m['nome']}")
            print(f"    campanha : {m['campanha']}")
            print(f"    tamanho  : {nx}×{ny} chunks  ({cw}×{ch} tiles/chunk  →  {nx*cw}×{ny*ch} tiles)")
            print(f"    spawn    : chunk {sc}  tile {st}")
            print(f"    tileset  : {m['tileset'] or '(não definido)'}")

            # existência de subdiretórios
            ok_chunks = "✓" if os.path.isdir(p["chunks"]) else "✗ não criado"
            ok_locais = "✓" if os.path.isdir(p["locais"]) else "✗ não criado"
            ok_save   = "✓" if os.path.isfile(p["save"])   else "—"
            ok_temp   = "✓" if os.path.isfile(p["temporal"]) else "—"
            print(f"    chunks/  : {ok_chunks}")
            print(f"    locais/  : {ok_locais}")
            print(f"    save     : {ok_save}")
            print(f"    temporal : {ok_temp}")

            bairros = m.get("bairros", {})
            if bairros:
                print(f"    bairros  : {len(bairros)}")
                for coord, nome in bairros.items():
                    cx, cy = coord.split(",")
                    print(f"               ({cx},{cy}) {nome}")
        except Exception as exc:
            print(f"  [{id_mundo}] ERRO: {exc}")
        print()


if __name__ == "__main__":
    _cli()
