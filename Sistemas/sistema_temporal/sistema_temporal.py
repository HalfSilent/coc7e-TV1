"""
sistema_temporal.py — Chunks que mudam com o tempo, lua e eventos.

Cada chunk pode ter "overlays" de tiles ativados por contexto:
    - periodo do dia  → "manha" | "tarde" | "noite" | "madrugada"
    - fase da lua     → "lua:nova" | "lua:crescente" | "lua:cheia" | "lua:minguante"
    - evento ocorrido → "ev:<ev_id>"
    - sempre          → "sempre"

O overlay é um dict {(tx, ty): tile_id} que se sobrepõe ao
array numpy base do chunk durante a renderização E colisão.

Armazenamento: SQLite (Mapas/Rio1923/temporal.db)
Cache em memória por (cx, cy, frozenset_tags) — invalidado ao
registrar novos eventos.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

import numpy as np

# ── Constantes ────────────────────────────────────────────────

_LUA_CICLO = 29.5 * 3600   # segundos de jogo por ciclo lunar


def _periodo(hora: int) -> str:
    if 6  <= hora < 12: return "manha"
    if 12 <= hora < 18: return "tarde"
    if 18 <= hora < 24: return "noite"
    return "madrugada"


def _fase_lua(tempo_jogo: float) -> str:
    fase = (tempo_jogo % _LUA_CICLO) / _LUA_CICLO
    if fase < 0.25: return "lua:nova"
    if fase < 0.50: return "lua:crescente"
    if fase < 0.75: return "lua:cheia"
    return "lua:minguante"


# ══════════════════════════════════════════════════════════════
#  SISTEMA TEMPORAL
# ══════════════════════════════════════════════════════════════

class SistemaTemporal:
    """
    Gerencia overlays temporais para chunks.

    Cada overlay é armazenado com uma única *tag* de contexto:
        "manha" | "tarde" | "noite" | "madrugada"
        "lua:nova" | "lua:crescente" | "lua:cheia" | "lua:minguante"
        "ev:<ev_id>"   — ativado após um evento de campanha
        "sempre"       — sempre aplicado

    Um overlay se aplica quando sua tag estiver no conjunto de
    tags ativas do momento atual.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._criar_tabelas()
        self._popular_defaults()
        # Cache: (cx, cy, frozenset_tags) → dict{(tx,ty): tile_id}
        self._cache: dict[tuple, dict] = {}

    # ── Tabelas ───────────────────────────────────────────────

    def _criar_tabelas(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS overlays (
                cx       INTEGER NOT NULL,
                cy       INTEGER NOT NULL,
                tag      TEXT    NOT NULL,
                tx       INTEGER NOT NULL,
                ty       INTEGER NOT NULL,
                tile_id  INTEGER NOT NULL,
                PRIMARY KEY (cx, cy, tag, tx, ty)
            );
            CREATE TABLE IF NOT EXISTS eventos_log (
                ev_id  TEXT PRIMARY KEY,
                tempo  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ov
                ON overlays (cx, cy, tag);
        """)
        self._conn.commit()

    def _popular_defaults(self):
        n = self._conn.execute("SELECT COUNT(*) FROM overlays").fetchone()[0]
        if n == 0:
            self._registrar_overlays_campanha()
            self._conn.commit()

    # ── API pública ───────────────────────────────────────────

    def tags_atuais(self, hora: int, tempo_jogo: float) -> frozenset:
        """Conjunto de tags ativas no contexto atual."""
        tags: set[str] = {"sempre", _periodo(hora), _fase_lua(tempo_jogo)}
        for ev_id in self._eventos_ids():
            tags.add(f"ev:{ev_id}")
        return frozenset(tags)

    def buscar_overlay(self,
                       cx: int, cy: int,
                       tags: frozenset) -> dict[tuple, int]:
        """
        Retorna dict {(tx, ty): tile_id} para o chunk (cx, cy)
        e as tags ativas. Resultado em cache até o próximo evento.
        """
        key = (cx, cy, tags)
        if key not in self._cache:
            self._cache[key] = self._query_overlay(cx, cy, tags)
        return self._cache[key]

    def registrar_evento(self, ev_id: str, tempo: float):
        """Marca evento como ocorrido e invalida cache de overlays."""
        self._conn.execute(
            "INSERT OR IGNORE INTO eventos_log (ev_id, tempo) VALUES (?, ?)",
            (ev_id, tempo),
        )
        self._conn.commit()
        self._cache.clear()

    def evento_ocorreu(self, ev_id: str) -> bool:
        return bool(
            self._conn.execute(
                "SELECT 1 FROM eventos_log WHERE ev_id=?", (ev_id,)
            ).fetchone()
        )

    def adicionar_overlay(self,
                          cx: int, cy: int, tag: str,
                          alteracoes: list[tuple[int, int, int]]):
        """
        Registra overlay manualmente.
        alteracoes = lista de (tx, ty, tile_id).
        """
        self._conn.executemany(
            "INSERT OR REPLACE INTO overlays "
            "(cx, cy, tag, tx, ty, tile_id) VALUES (?, ?, ?, ?, ?, ?)",
            [(cx, cy, tag, tx, ty, tid) for tx, ty, tid in alteracoes],
        )
        self._conn.commit()
        self._cache.clear()

    def aplicar(self,
                dados: np.ndarray,
                cx: int, cy: int,
                hora: int, tempo_jogo: float) -> np.ndarray:
        """
        Aplica overlays ao array numpy de um chunk.
        Retorna novo array (não modifica o original).
        """
        tags    = self.tags_atuais(hora, tempo_jogo)
        overlay = self.buscar_overlay(cx, cy, tags)
        if not overlay:
            return dados
        resultado = dados.copy()
        for (tx, ty), tile_id in overlay.items():
            if 0 <= tx < resultado.shape[1] and 0 <= ty < resultado.shape[0]:
                resultado[ty, tx] = tile_id
        return resultado

    def fechar(self):
        self._conn.close()

    # ── Internos ──────────────────────────────────────────────

    def _eventos_ids(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT ev_id FROM eventos_log ORDER BY ev_id"
        ).fetchall()
        return [r[0] for r in rows]

    def _query_overlay(self,
                       cx: int, cy: int,
                       tags: frozenset) -> dict[tuple, int]:
        if not tags:
            return {}
        ph   = ",".join("?" * len(tags))
        rows = self._conn.execute(
            f"SELECT tx, ty, tile_id FROM overlays "
            f"WHERE cx=? AND cy=? AND tag IN ({ph}) ORDER BY rowid",
            (cx, cy, *tags),
        ).fetchall()
        # Último write ganha para o mesmo (tx, ty)
        result: dict[tuple, int] = {}
        for r in rows:
            result[(r[0], r[1])] = r[2]
        return result

    def _registrar_batch(self,
                         cx: int, cy: int, tag: str,
                         alteracoes: list[tuple[int, int, int]]):
        self._conn.executemany(
            "INSERT OR IGNORE INTO overlays "
            "(cx, cy, tag, tx, ty, tile_id) VALUES (?, ?, ?, ?, ?, ?)",
            [(cx, cy, tag, tx, ty, tid) for tx, ty, tid in alteracoes],
        )

    def _registrar_overlays_campanha(self):
        """Overlays padrão da campanha Degraus para o Abismo.

        IDs de tile (T enum):
            VAZIO=0  GRAMA=1  CALCADA=2  RUA=3  PAREDE=4  EDIFICIO=5
            AGUA=6   TERRA=7  PORTA=8    ARVORE=9 LAMPIAO=10 ESCADA=11
        """
        LAMP   = 10   # T.LAMPIAO
        TERRA  = 7    # T.TERRA
        PAREDE = 4    # T.PAREDE
        ESCADA = 11   # T.ESCADA
        CALCADA = 2   # T.CALCADA

        # ── Catumbi (2, 3) à noite: lampiões nas esquinas ─────
        # Os cruzamentos de rua ficam com lampiões acesos
        lamps = [
            (tx, ty, LAMP)
            for tx in range(0, 20, 10)   # colunas de rua
            for ty in range(0, 15, 7)    # linhas de rua
        ]
        self._registrar_batch(2, 3, "noite",     lamps)
        self._registrar_batch(2, 3, "madrugada", lamps)

        # ── Catumbi após casarao_noite: marcas sinistras no chão
        self._registrar_batch(2, 3, "ev:casarao_noite", [
            (10, 7, TERRA), (11, 7, TERRA),
            (10, 8, TERRA), (11, 8, TERRA),
        ])

        # ── Casarão (3, 3) após casarao_noite: escada revelada ─
        # As escadas para a câmara ficam visíveis após a visita
        self._registrar_batch(3, 3, "ev:casarao_noite", [
            (9,  5, ESCADA),
            (10, 5, ESCADA),
        ])

        # ── Centro/Prefeitura (6, 4): fecha à noite ───────────
        fechado = [(9, 9, PAREDE), (10, 9, PAREDE)]   # porta → parede
        self._registrar_batch(6, 4, "noite",     fechado)
        self._registrar_batch(6, 4, "madrugada", fechado)

        # ── Câmara (3, 4) na lua cheia: altar pulsante ─────────
        # Escadas de entrada ficam claramente iluminadas
        self._registrar_batch(3, 4, "lua:cheia", [
            (9,  4, ESCADA),
            (10, 4, ESCADA),
        ])
