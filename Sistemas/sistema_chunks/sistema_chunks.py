"""
sistema_chunks.py — Chunks semi-procedurais.

Locais importantes da campanha (casarão, faculdade, catumbi…)
são definidos em arquivos .tmj (Tiled Map JSON), editáveis no
Tiled Editor.  O restante do mundo usa geração procedural.

Registro:
    LOCAIS: dict[(cx, cy) → "nome.tmj"]

Convenção GID ↔ tile:
    GID 0  = transparente (usa tile procedural do .npy)
    GID N  = T enum value N-1
    (GID 1 → T.VAZIO=0, GID 2 → T.GRAMA=1, GID 4 → T.RUA=3 …)

Carregamento:
    1. tenta pytiled_parser (parse nativo)
    2. fallback para json.load() direto

Os .tmj são compatíveis com Tiled Editor — basta abrir,
editar e salvar; o jogo usa a versão nova no próximo boot.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np

# ── Caminhos ──────────────────────────────────────────────────

_RAIZ       = os.path.dirname(os.path.abspath(__file__))
_LOCAIS_DIR = os.path.join(_RAIZ, "Mundos", "Rio1923", "locais")
os.makedirs(_LOCAIS_DIR, exist_ok=True)

# ── Registro de locais ────────────────────────────────────────

# (chunk_x, chunk_y) → arquivo .tmj em _LOCAIS_DIR
LOCAIS: dict[tuple[int, int], str] = {
    (1, 1): "casa_investigador.tmj",
    (2, 2): "faculdade_malheiros.tmj",
    (2, 3): "bairro_catumbi.tmj",
    (3, 3): "casarao_rua_almas.tmj",
    (3, 4): "camara_subterranea.tmj",
    (6, 4): "centro_prefeitura.tmj",
}


def configurar_campanha(locais_dir: str, locais: dict):
    """
    Redireciona _LOCAIS_DIR e LOCAIS para uma campanha específica.
    Deve ser chamado antes de qualquer operação de carregamento de chunk.
    Permite que módulos de campanha armazenem seus .tmj localmente.
    """
    global _LOCAIS_DIR, LOCAIS
    _LOCAIS_DIR = locais_dir
    os.makedirs(_LOCAIS_DIR, exist_ok=True)
    LOCAIS = locais

# ══════════════════════════════════════════════════════════════
#  CARREGAMENTO
# ══════════════════════════════════════════════════════════════

def local_existe(cx: int, cy: int) -> bool:
    if (cx, cy) not in LOCAIS:
        return False
    return os.path.exists(os.path.join(_LOCAIS_DIR, LOCAIS[(cx, cy)]))


def carregar_local(cx: int, cy: int,
                   chunk_w: int, chunk_h: int) -> Optional[np.ndarray]:
    """
    Carrega chunk handmade de arquivo .tmj.
    Retorna numpy uint16 ou None se não existir.
    """
    if (cx, cy) not in LOCAIS:
        return None
    path = os.path.join(_LOCAIS_DIR, LOCAIS[(cx, cy)])
    if not os.path.exists(path):
        return None
    try:
        return _tmj_para_numpy(path, chunk_w, chunk_h)
    except Exception as e:
        print(f"[sistema_chunks] Erro ao carregar {path}: {e}")
        return None


def _tmj_para_numpy(path: str, w: int, h: int) -> np.ndarray:
    """Tenta pytiled_parser; fallback para JSON direto."""
    try:
        return _carregar_pytiled(path, w, h)
    except ImportError:
        pass
    except Exception as e:
        print(f"[sistema_chunks] pytiled falhou ({e}), usando JSON")
    return _carregar_json(path, w, h)


def _carregar_pytiled(path: str, w: int, h: int) -> np.ndarray:
    import pytiled_parser
    from pytiled_parser import TileLayer
    tmap = pytiled_parser.parse_map(Path(path))
    arr  = np.zeros((h, w), dtype=np.uint16)
    for layer in tmap.layers:
        if isinstance(layer, TileLayer) and layer.data:
            for row_i, row in enumerate(layer.data):
                if row_i >= h:
                    break
                for col_i, gid in enumerate(row):
                    if col_i >= w:
                        break
                    if gid and gid > 0:
                        arr[row_i, col_i] = max(0, gid - 1)
            break   # só primeira tilelayer
    return arr


def _carregar_json(path: str, w: int, h: int) -> np.ndarray:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    arr = np.zeros((h, w), dtype=np.uint16)
    for layer in data.get("layers", []):
        if layer.get("type") == "tilelayer":
            flat = layer.get("data", [])
            for idx, gid in enumerate(flat[: w * h]):
                ty, tx = divmod(idx, w)
                if ty < h and gid > 0:
                    arr[ty, tx] = max(0, gid - 1)
            break
    return arr


# ══════════════════════════════════════════════════════════════
#  PERSISTÊNCIA .tmj
# ══════════════════════════════════════════════════════════════

def salvar_tmj(path: str, dados: np.ndarray):
    """
    Salva array numpy como .tmj compatível com Tiled Editor.
    GID = T_value + 1  (GID 0 = vazio no Tiled).
    """
    h, w = dados.shape
    flat = [int(dados[ty, tx]) + 1 for ty in range(h) for tx in range(w)]
    tmj = {
        "compressionlevel": -1,
        "height": h,
        "infinite": False,
        "layers": [{
            "data":    flat,
            "height":  h,
            "width":   w,
            "id":      1,
            "name":    "base",
            "opacity": 1,
            "type":    "tilelayer",
            "visible": True,
            "x": 0, "y": 0,
        }],
        "nextlayerid":  2,
        "nextobjectid": 1,
        "orientation":  "orthogonal",
        "renderorder":  "right-down",
        "tiledversion": "1.10.2",
        "tileheight":   32,
        "tilewidth":    32,
        "tilesets":     [],
        "type":         "map",
        "version":      "1.10",
        "width":        w,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tmj, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
#  GERAÇÃO DOS LOCAIS PADRÃO
# ══════════════════════════════════════════════════════════════

def gerar_locais_padrao():
    """Cria os .tmj dos locais principais se ainda não existirem."""
    _gerar_se_novo("casa_investigador.tmj",   _layout_casa_investigador)
    _gerar_se_novo("faculdade_malheiros.tmj", _layout_faculdade)
    _gerar_se_novo("bairro_catumbi.tmj",      _layout_catumbi)
    _gerar_se_novo("casarao_rua_almas.tmj",   _layout_casarao)
    _gerar_se_novo("camara_subterranea.tmj",  _layout_camara)
    _gerar_se_novo("centro_prefeitura.tmj",   _layout_prefeitura)


def _gerar_se_novo(nome: str, func):
    path = os.path.join(_LOCAIS_DIR, nome)
    if not os.path.exists(path):
        dados = func()
        salvar_tmj(path, dados)
        print(f"[sistema_chunks] Local gerado: {nome}")


# ══════════════════════════════════════════════════════════════
#  LAYOUTS  (20 colunas × 15 linhas de tiles)
# ══════════════════════════════════════════════════════════════

# T enum – referência rápida
_V, _G, _C, _R, _P, _E, _A, _T, _D, _AR, _L, _SC = range(12)
# VAZIO GRAMA CALCADA RUA PAREDE EDIFICIO AGUA TERRA PORTA ARVORE LAMPIAO ESCADA


def _base(tile: int = _C) -> np.ndarray:
    """Array base preenchido com um tile."""
    return np.full((15, 20), tile, dtype=np.uint16)


# ── (1, 1) Casa do Investigador ───────────────────────────────

def _layout_casa_investigador() -> np.ndarray:
    d = _base(_C)
    # Ruas de borda
    d[0, :] = _R;  d[14, :] = _R
    d[:, 0] = _R;  d[:, 19] = _R
    # Casa principal (NO)
    for ty in range(2, 7):
        for tx in range(2, 9):
            d[ty, tx] = _P if (ty in (2, 6) or tx in (2, 8)) else _E
    d[6, 5] = _D   # porta sul
    # Casa vizinha (NE)
    for ty in range(2, 7):
        for tx in range(11, 18):
            d[ty, tx] = _P if (ty in (2, 6) or tx in (11, 17)) else _E
    d[6, 14] = _D
    # Jardim
    for tx in (4, 14):
        d[8, tx] = _AR;  d[9, tx] = _AR
    # Lampiões nas esquinas
    d[0, 0] = _L;  d[0, 19] = _L
    d[14, 0] = _L; d[14, 19] = _L
    return d


# ── (2, 2) Faculdade / Escritório de Malheiros ────────────────

def _layout_faculdade() -> np.ndarray:
    d = _base(_C)
    d[0, :] = _R;  d[14, :] = _R
    d[:, 0] = _R;  d[:, 19] = _R
    # Edifício principal
    for ty in range(2, 12):
        for tx in range(3, 17):
            d[ty, tx] = _P if (ty in (2, 11) or tx in (3, 16)) else _E
    d[11, 9] = _D;  d[11, 10] = _D   # porta de entrada
    d[4, 9]  = _SC; d[4, 10]  = _SC  # escada para o escritório
    # Jardim frontal
    for tx in (5, 8, 11, 14):
        d[12, tx] = _AR
    return d


# ── (2, 3) Bairro do Catumbi + Botequim de Benedito ──────────

def _layout_catumbi() -> np.ndarray:
    d = _base(_C)
    # Grade de ruas
    d[0, :] = _R;  d[7, :] = _R;  d[14, :] = _R
    d[:, 0] = _R;  d[:, 10] = _R; d[:, 19] = _R
    # Lampiões nas interseções
    for tx, ty in [
        (0, 0), (10, 0), (19, 0),
        (0, 7), (10, 7), (19, 7),
        (0, 14),(10,14), (19,14),
    ]:
        d[ty, tx] = _L
    # Botequim de Benedito (quadrante NO)
    for ty in range(1, 6):
        for tx in range(1, 9):
            d[ty, tx] = _P if (ty in (1, 5) or tx in (1, 8)) else _E
    d[5, 4] = _D   # porta do botequim
    # Residências (quadrante NE)
    for ty in range(1, 6):
        for tx in range(11, 19):
            d[ty, tx] = _P if (ty in (1, 5) or tx in (11, 18)) else _E
    d[5, 14] = _D
    # Praça central
    d[8:14, 2:8] = _G
    d[10, 4] = _AR;  d[11, 5] = _AR;  d[9, 6] = _AR
    return d


# ── (3, 3) Casarão da Rua das Almas ──────────────────────────

def _layout_casarao() -> np.ndarray:
    d = _base(_C)
    d[0, :] = _R;  d[14, :] = _R
    d[:, 0] = _R;  d[:, 19] = _R
    # Grande casarão central
    for ty in range(2, 13):
        for tx in range(3, 17):
            d[ty, tx] = _P if (ty in (2, 12) or tx in (3, 16)) else _E
    d[12, 9] = _D;  d[12, 10] = _D   # porta sul (entrada principal)
    d[2, 9]  = _D                     # porta norte (acesso à câmara)
    # Escada para a câmara subterrânea (interior do casarão)
    # Começa como EDIFICIO — o sistema temporal revela ESCADA após ev:casarao_noite
    d[5, 9]  = _E;  d[5, 10] = _E
    # Árvores mortas no jardim
    for tx in (2, 17):
        d[1, tx] = _AR;  d[13, tx] = _AR
    return d


# ── (3, 4) Câmara Subterrânea de Valverde ─────────────────────

def _layout_camara() -> np.ndarray:
    d = _base(_V)   # vazio = escuridão subterrânea
    # Câmara principal
    for ty in range(3, 12):
        for tx in range(4, 16):
            d[ty, tx] = _P if (ty in (3, 11) or tx in (4, 15)) else _T
    # Corredor de entrada (vindo do norte / casarão)
    d[0:3, 9] = _T;  d[0:3, 10] = _T
    # Escada de subida (volta ao casarão)
    d[4, 9] = _SC;   d[4, 10] = _SC
    # Altar central
    d[6:9, 8:12] = _P
    d[7, 9] = _SC    # ponto de interação com o ritual
    # Pilares
    for ty2, tx2 in ((5, 6), (5, 13), (9, 6), (9, 13)):
        d[ty2, tx2] = _P
    return d


# ── (6, 4) Centro / Prefeitura ────────────────────────────────

def _layout_prefeitura() -> np.ndarray:
    d = _base(_C)
    d[0, :] = _R;  d[14, :] = _R
    d[:, 0] = _R;  d[:, 19] = _R
    # Edifício da prefeitura
    for ty in range(1, 10):
        for tx in range(2, 18):
            d[ty, tx] = _P if (ty in (1, 9) or tx in (2, 17)) else _E
    d[9, 9] = _D;  d[9, 10] = _D     # porta principal
    # Arquivo público (sala interna)
    for ty in range(3, 7):
        for tx in range(4, 10):
            d[ty, tx] = _P if (ty in (3, 6) or tx in (4, 9)) else _E
    d[6, 6] = _D   # entrada do arquivo
    # Praça em frente
    d[11:13, 5:15] = _G
    d[11, 7] = _AR;  d[11, 12] = _AR
    return d
