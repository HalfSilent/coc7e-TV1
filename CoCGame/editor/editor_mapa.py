"""
editor/editor_mapa.py — Editor visual de mapas para CoC 7e.

Abre a partir do menu principal ([E] Editor) ou standalone:
    python CoCGame/editor/editor_mapa.py

Controles:
    LMB drag           → pinta tile selecionado
    RMB drag           → apaga (vira CHÃO)
    Scroll             → zoom in / out
    Espaço + LMB drag  → pan (arrastar câmera)
    Ctrl+Z             → desfazer
    Ctrl+Y / Ctrl+Shift+Z → refazer
    Ctrl+S             → salvar JSON
    Ctrl+N             → novo mapa (pede dimensões)
    Ctrl+O             → abrir JSON existente
    Ctrl+E             → exportar código Python
    [1–5]              → selecionar tile (Vazio/Chão/Parede/Elevado/Saída)
    [P]                → ferramenta Pincel
    [B]                → ferramenta Borracha
    [F]                → ferramenta Balde (flood fill)
    [L]                → ferramenta Linha
    [R]                → ferramenta Retângulo
    [I]                → ferramenta Inimigo (clique para colocar/remover)
    [O]                → ferramenta Objeto  (clique para colocar/editar)
    [ESC]              → voltar / cancelar ação
"""
from __future__ import annotations

import copy
import json
import os
import sys
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

os.environ.setdefault("SDL_VIDEODRIVER", "x11")
import pygame

# ── path ──────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

try:
    from gerenciador_assets import get_font, garantir_fontes
    _tem_fontes = True
except ImportError:
    _tem_fontes = False
    def get_font(_tipo, tamanho):
        return pygame.font.SysFont("monospace", tamanho)
    def garantir_fontes(**_): pass


# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

W, H            = 1920, 1080
PAL_W           = 200       # largura painel esquerdo (paleta)
PROP_W          = 260       # largura painel direito (propriedades)
TOPO_H          = 44        # altura barra superior
STATUS_H        = 24        # altura barra inferior
GRID_X          = PAL_W
GRID_Y          = TOPO_H
GRID_W          = W - PAL_W - PROP_W
GRID_H          = H - TOPO_H - STATUS_H

ZOOM_MIN, ZOOM_MAX = 8, 64
ZOOM_PAD        = 4         # padding interno de célula ao desenhar

TILE_NOMES  = {0: "Vazio", 1: "Chão", 2: "Parede", 3: "Elevado", 4: "Saída"}
TILE_CORES  = {
    0: (12,  12,  18),
    1: (88,  77,  66),
    2: (48,  48,  58),
    3: (96,  66,  36),
    4: (36, 150,  70),
}
TILE_BORDA  = {
    0: (30,  30,  40),
    1: (120, 108, 96),
    2: (80,  80,  95),
    3: (140, 100, 58),
    4: (56,  200, 100),
}

COR_BG          = (22,  20,  36)
COR_PAINEL      = (18,  16,  30)
COR_PAINEL2     = (26,  24,  42)
COR_BORDA       = (60,  55,  90)
COR_TOPO        = (14,  12,  24)
COR_STATUS      = (14,  12,  24)
COR_TEXTO       = (220, 210, 200)
COR_TEXTO_DIM   = (120, 110, 105)
COR_DESTAQUE    = (200, 168,  70)
COR_HOVER       = (60,  55,  90)
COR_SEL         = (200, 168,  70)
COR_INIMIGO     = (220,  60,  60)
COR_OBJETO      = (100, 180, 240)
COR_GRID_LINE   = (35,  33,  52)

TEMAS = ["catacumbas", "mansao", "cemiterio", "biblioteca", "hospital",
         "delegacia", "porto", "floresta", "cidade"]


# ══════════════════════════════════════════════════════════════
# FERRAMENTA
# ══════════════════════════════════════════════════════════════

class Ferramenta(Enum):
    PINCEL    = auto()
    BORRACHA  = auto()
    BALDE     = auto()
    LINHA     = auto()
    RETANGULO = auto()
    INIMIGO   = auto()
    OBJETO    = auto()


# ══════════════════════════════════════════════════════════════
# MODELO DO MAPA
# ══════════════════════════════════════════════════════════════

class MapaEditor:
    """Modelo puro do mapa em edição (sem pygame)."""

    def __init__(self, nome: str = "mapa_novo", cols: int = 18, linhas: int = 13):
        self.nome    = nome
        self.tema    = "catacumbas"
        self.cols    = cols
        self.linhas  = linhas
        self.tiles: List[List[int]] = self._gerar_vazio(cols, linhas)
        self.inimigos: List[Dict] = []
        self.objetos:  List[Dict] = []
        self.arquivo:  Optional[str] = None
        self.modificado = False

    # ── criação ───────────────────────────────────────────────

    @staticmethod
    def _gerar_vazio(cols: int, linhas: int) -> List[List[int]]:
        """Cria grid preenchido com CHÃO e bordas de PAREDE."""
        return [
            [
                2 if (r == 0 or r == linhas - 1 or c == 0 or c == cols - 1)
                else 1
                for c in range(cols)
            ]
            for r in range(linhas)
        ]

    # ── acesso ────────────────────────────────────────────────

    def get(self, col: int, linha: int) -> int:
        if 0 <= linha < self.linhas and 0 <= col < self.cols:
            return self.tiles[linha][col]
        return -1

    def set(self, col: int, linha: int, valor: int):
        if 0 <= linha < self.linhas and 0 <= col < self.cols:
            if self.tiles[linha][col] != valor:
                self.tiles[linha][col] = valor
                self.modificado = True

    def inimigo_em(self, col: int, linha: int) -> Optional[Dict]:
        return next((e for e in self.inimigos
                     if e["col"] == col and e["linha"] == linha), None)

    def objeto_em(self, col: int, linha: int) -> Optional[Dict]:
        return next((o for o in self.objetos
                     if o["col"] == col and o["linha"] == linha), None)

    def remover_inimigo(self, col: int, linha: int):
        self.inimigos = [e for e in self.inimigos
                         if not (e["col"] == col and e["linha"] == linha)]
        self.modificado = True

    def remover_objeto(self, col: int, linha: int):
        self.objetos = [o for o in self.objetos
                        if not (o["col"] == col and o["linha"] == linha)]
        self.modificado = True

    # ── flood fill ────────────────────────────────────────────

    def flood_fill(self, col: int, linha: int, novo: int):
        antigo = self.get(col, linha)
        if antigo == novo or antigo < 0:
            return
        fila = [(col, linha)]
        visitados: set = set()
        while fila:
            c, l = fila.pop()
            if (c, l) in visitados:
                continue
            if self.get(c, l) != antigo:
                continue
            visitados.add((c, l))
            self.set(c, l, novo)
            for dc, dl in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nl = c + dc, l + dl
                if (nc, nl) not in visitados:
                    fila.append((nc, nl))

    # ── serialização ──────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "versao":   "1.0",
            "nome":     self.nome,
            "tema":     self.tema,
            "tiles":    self.tiles,
            "inimigos": self.inimigos,
            "objetos":  self.objetos,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MapaEditor":
        m        = cls.__new__(cls)
        m.nome   = d.get("nome", "mapa")
        m.tema   = d.get("tema", "catacumbas")
        m.tiles  = d["tiles"]
        m.linhas = len(m.tiles)
        m.cols   = len(m.tiles[0]) if m.tiles else 0
        m.inimigos = d.get("inimigos", [])
        m.objetos  = d.get("objetos", [])
        m.arquivo  = None
        m.modificado = False
        return m

    def exportar_python(self) -> str:
        """Gera código Python para colar em masmorras.py."""
        var = "MAPA_" + self.nome.upper().replace(" ", "_").replace("-", "_")
        linhas = [f"# Gerado por editor_mapa.py", f"{var} = ["]
        for row in self.tiles:
            linhas.append("    " + repr(row) + ",")
        linhas += ["]", "# tile 0=VAZIO  1=CHÃO  2=PAREDE  3=ELEVADO  4=SAÍDA"]

        if self.inimigos:
            linhas += ["", f"INIMIGOS_{var[5:]} = ["]
            for e in self.inimigos:
                n    = e.get("nome", "Cultista")
                tipo = e.get("tipo_ia", "humano")
                hp   = e.get("hp", 8)
                linhas.append(
                    f'    Inimigo("{n}", col={e["col"]}, linha={e["linha"]},'
                    f' tipo="{tipo}", hp={hp}),'
                )
            linhas.append("]")

        if self.objetos:
            linhas += ["", f"OBJETOS_{var[5:]} = ["]
            for o in self.objetos:
                n    = o.get("nome", "Objeto")
                tipo = o.get("tipo", "nota")
                desc = o.get("descricao", "").replace('"', "'")
                item = o.get("item_concedido", "")
                item_s = f', item_concedido="{item}"' if item else ""
                linhas.append(
                    f'    ObjetoMasmorra(col={o["col"]}, linha={o["linha"]},'
                    f' tipo="{tipo}", nome="{n}", descricao="{desc}"{item_s}),'
                )
            linhas.append("]")

        return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════
# CAMPO DE TEXTO SIMPLES
# ══════════════════════════════════════════════════════════════

class CampoTexto:
    """Input field simples em pygame."""

    def __init__(self, rect: pygame.Rect, valor: str = "", placeholder: str = ""):
        self.rect        = rect
        self.valor       = valor
        self.placeholder = placeholder
        self.ativo       = False
        self.cursor_tick = 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True se mudou."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.ativo = self.rect.collidepoint(event.pos)
        if not self.ativo:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.valor = self.valor[:-1]
                return True
            elif event.key == pygame.K_DELETE:
                self.valor = ""
                return True
            elif event.unicode and event.unicode.isprintable():
                self.valor += event.unicode
                return True
        return False

    def draw(self, surf: pygame.Surface, fn: pygame.font.Font):
        cor_borda = COR_DESTAQUE if self.ativo else COR_BORDA
        pygame.draw.rect(surf, (28, 26, 44), self.rect, border_radius=4)
        pygame.draw.rect(surf, cor_borda, self.rect, 1, border_radius=4)
        txt = self.valor if self.valor else self.placeholder
        cor = COR_TEXTO if self.valor else COR_TEXTO_DIM
        s   = fn.render(txt[:32], True, cor)
        surf.blit(s, (self.rect.x + 6, self.rect.y + (self.rect.h - s.get_height()) // 2))
        # cursor piscante
        if self.ativo:
            self.cursor_tick = (self.cursor_tick + 1) % 60
            if self.cursor_tick < 30:
                cx = self.rect.x + 6 + fn.size(self.valor[:32])[0] + 2
                cy1 = self.rect.y + 4
                cy2 = self.rect.y + self.rect.h - 4
                pygame.draw.line(surf, COR_TEXTO, (cx, cy1), (cx, cy2), 1)


# ══════════════════════════════════════════════════════════════
# EDITOR PRINCIPAL
# ══════════════════════════════════════════════════════════════

class EditorMapa:
    """Editor visual de mapas. Retorna ao fechar."""

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock
        garantir_fontes(verbose=False)

        self.fn_titulo = get_font("titulo", 15)
        self.fn_hud    = get_font("hud",    13)
        self.fn_small  = get_font("hud",    11)
        self.fn_mini   = get_font("hud",     9)

        # Modelo
        self.mapa = MapaEditor()

        # Viewport
        self.zoom  = 32
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._pan_ativo    = False
        self._pan_inicio   = (0, 0)
        self._pan_base     = (0.0, 0.0)

        # Ferramentas
        self.ferramenta   = Ferramenta.PINCEL
        self.tile_sel     = 2
        self._pintando    = False
        self._apagando    = False
        self._lin_inicio: Optional[Tuple[int, int]] = None
        self._ret_inicio: Optional[Tuple[int, int]] = None
        self._lin_preview: List[Tuple[int, int]] = []
        self._ret_preview: List[Tuple[int, int]] = []

        # Cursor
        self.cursor_grid: Optional[Tuple[int, int]] = None

        # Histórico de undo
        self._historico: List[List[List[int]]] = []
        self._hist_idx  = -1
        self._salvar_historico()

        # Entidade selecionada no painel de propriedades
        self._entidade_sel: Optional[Dict] = None
        self._tipo_sel: str = ""          # "inimigo" ou "objeto"

        # Campos de texto para o painel de propriedades
        self._campos: Dict[str, CampoTexto] = {}
        self._montar_campos_prop()

        # Campos de texto para o painel superior (nome do mapa)
        self._campo_nome = CampoTexto(
            pygame.Rect(TOPO_H + 4, 6, 240, 32), self.mapa.nome, "nome do mapa"
        )

        # Diálogo "Novo Mapa"
        self._dlg_novo     = False
        self._dlg_cols_txt = CampoTexto(pygame.Rect(0, 0, 80, 30), "18", "cols")
        self._dlg_lin_txt  = CampoTexto(pygame.Rect(0, 0, 80, 30), "13", "linhas")
        self._dlg_nome_txt = CampoTexto(pygame.Rect(0, 0, 200, 30), "mapa_novo", "nome")

        # Mensagem flash
        self._flash_msg  = ""
        self._flash_tick = 0

        # Áreas de layout
        self.area_grid = pygame.Rect(GRID_X, GRID_Y, GRID_W, GRID_H)
        self.area_pal  = pygame.Rect(0, TOPO_H, PAL_W, GRID_H)
        self.area_prop = pygame.Rect(W - PROP_W, TOPO_H, PROP_W, GRID_H)

    # ══════════════════════════════════════════════════════════
    # HISTÓRICO
    # ══════════════════════════════════════════════════════════

    def _salvar_historico(self):
        snapshot = copy.deepcopy(self.mapa.tiles)
        # Descarta estados futuros
        self._historico = self._historico[:self._hist_idx + 1]
        self._historico.append(snapshot)
        if len(self._historico) > 50:
            self._historico.pop(0)
        self._hist_idx = len(self._historico) - 1

    def _desfazer(self):
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self.mapa.tiles    = copy.deepcopy(self._historico[self._hist_idx])
            self.mapa.linhas   = len(self.mapa.tiles)
            self.mapa.cols     = len(self.mapa.tiles[0]) if self.mapa.tiles else 0
            self.mapa.modificado = True
            self._flash("Desfeito")

    def _refazer(self):
        if self._hist_idx < len(self._historico) - 1:
            self._hist_idx += 1
            self.mapa.tiles  = copy.deepcopy(self._historico[self._hist_idx])
            self.mapa.linhas = len(self.mapa.tiles)
            self.mapa.cols   = len(self.mapa.tiles[0]) if self.mapa.tiles else 0
            self.mapa.modificado = True
            self._flash("Refeito")

    # ══════════════════════════════════════════════════════════
    # CONVERSÃO PIXEL ↔ GRID
    # ══════════════════════════════════════════════════════════

    def _grid_para_pixel(self, col: int, linha: int) -> Tuple[int, int]:
        x = GRID_X + int(col * self.zoom - self.pan_x)
        y = GRID_Y + int(linha * self.zoom - self.pan_y)
        return x, y

    def _pixel_para_grid(self, px: int, py: int) -> Tuple[int, int]:
        col   = int((px - GRID_X + self.pan_x) // self.zoom)
        linha = int((py - GRID_Y + self.pan_y) // self.zoom)
        return col, linha

    def _grid_valido(self, col: int, linha: int) -> bool:
        return 0 <= col < self.mapa.cols and 0 <= linha < self.mapa.linhas

    # ══════════════════════════════════════════════════════════
    # FERRAMENTAS
    # ══════════════════════════════════════════════════════════

    def _aplicar_tile(self, col: int, linha: int, valor: int):
        if self._grid_valido(col, linha):
            self.mapa.set(col, linha, valor)

    def _celulas_linha(self, c0: int, l0: int,
                       c1: int, l1: int) -> List[Tuple[int, int]]:
        """Bresenham line."""
        cels = []
        dc, dl = abs(c1 - c0), abs(l1 - l0)
        sc = 1 if c1 > c0 else -1
        sl = 1 if l1 > l0 else -1
        err = dc - dl
        c, l = c0, l0
        while True:
            cels.append((c, l))
            if c == c1 and l == l1:
                break
            e2 = 2 * err
            if e2 > -dl:
                err -= dl; c += sc
            if e2 < dc:
                err += dc; l += sl
        return cels

    def _celulas_retangulo(self, c0: int, l0: int,
                           c1: int, l1: int) -> List[Tuple[int, int]]:
        cmin, cmax = min(c0, c1), max(c0, c1)
        lmin, lmax = min(l0, l1), max(l0, l1)
        cels = []
        for l in range(lmin, lmax + 1):
            for c in range(cmin, cmax + 1):
                if c in (cmin, cmax) or l in (lmin, lmax):
                    cels.append((c, l))
        return cels

    # ══════════════════════════════════════════════════════════
    # PAINEL DE PROPRIEDADES
    # ══════════════════════════════════════════════════════════

    def _montar_campos_prop(self):
        bx = W - PROP_W + 10
        by = TOPO_H + 10
        lh = 28
        self._campos = {
            "nome":    CampoTexto(pygame.Rect(bx, by,      PROP_W - 20, 26), "", "nome"),
            "tipo":    CampoTexto(pygame.Rect(bx, by + lh, PROP_W - 20, 26), "", "tipo"),
            "desc":    CampoTexto(pygame.Rect(bx, by + lh * 2, PROP_W - 20, 26), "", "descricao"),
            "item":    CampoTexto(pygame.Rect(bx, by + lh * 3, PROP_W - 20, 26), "", "item_concedido"),
            "hp":      CampoTexto(pygame.Rect(bx, by + lh * 4, PROP_W - 20, 26), "", "hp"),
            "tipo_ia": CampoTexto(pygame.Rect(bx, by + lh * 5, PROP_W - 20, 26), "", "tipo_ia"),
        }

    def _selecionar_entidade(self, col: int, linha: int):
        e = self.mapa.inimigo_em(col, linha)
        if e:
            self._entidade_sel = e
            self._tipo_sel     = "inimigo"
            self._campos["nome"].valor    = e.get("nome", "Cultista")
            self._campos["tipo"].valor    = e.get("tipo", "humano")
            self._campos["hp"].valor      = str(e.get("hp", 8))
            self._campos["tipo_ia"].valor = e.get("tipo_ia", "agressivo")
            self._campos["desc"].valor    = ""
            self._campos["item"].valor    = ""
            return
        o = self.mapa.objeto_em(col, linha)
        if o:
            self._entidade_sel = o
            self._tipo_sel     = "objeto"
            self._campos["nome"].valor    = o.get("nome", "Objeto")
            self._campos["tipo"].valor    = o.get("tipo", "nota")
            self._campos["desc"].valor    = o.get("descricao", "")
            self._campos["item"].valor    = o.get("item_concedido", "")
            self._campos["hp"].valor      = ""
            self._campos["tipo_ia"].valor = ""
            return
        self._entidade_sel = None
        self._tipo_sel     = ""

    def _aplicar_campos_para_entidade(self):
        if not self._entidade_sel:
            return
        if self._tipo_sel == "inimigo":
            self._entidade_sel["nome"]    = self._campos["nome"].valor or "Cultista"
            self._entidade_sel["tipo"]    = self._campos["tipo"].valor or "humano"
            self._entidade_sel["tipo_ia"] = self._campos["tipo_ia"].valor or "agressivo"
            try:
                self._entidade_sel["hp"] = int(self._campos["hp"].valor or "8")
            except ValueError:
                self._entidade_sel["hp"] = 8
        elif self._tipo_sel == "objeto":
            self._entidade_sel["nome"]           = self._campos["nome"].valor or "Objeto"
            self._entidade_sel["tipo"]           = self._campos["tipo"].valor or "nota"
            self._entidade_sel["descricao"]      = self._campos["desc"].valor
            self._entidade_sel["item_concedido"] = self._campos["item"].valor
        self.mapa.modificado = True

    # ══════════════════════════════════════════════════════════
    # SALVAR / CARREGAR / EXPORTAR
    # ══════════════════════════════════════════════════════════

    def _pasta_mapas(self) -> str:
        p = os.path.join(_BASE, "Mundos", "mapas")
        os.makedirs(p, exist_ok=True)
        return p

    def _salvar(self):
        self._aplicar_campos_para_entidade()
        self.mapa.nome = self._campo_nome.valor or self.mapa.nome
        if not self.mapa.arquivo:
            nome_seg = self.mapa.nome.replace(" ", "_").lower()
            self.mapa.arquivo = os.path.join(self._pasta_mapas(), f"{nome_seg}.json")
        with open(self.mapa.arquivo, "w", encoding="utf-8") as f:
            json.dump(self.mapa.to_dict(), f, ensure_ascii=False, indent=2)
        self.mapa.modificado = False
        self._flash(f"Salvo: {os.path.basename(self.mapa.arquivo)}")

    def _abrir_dialogo_arquivo(self):
        """Abre o mapa mais recente da pasta (sem GUI de arquivo — lista simplificada)."""
        pasta = self._pasta_mapas()
        arquivos = sorted(
            [f for f in os.listdir(pasta) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(pasta, f)),
            reverse=True,
        )
        if not arquivos:
            self._flash("Nenhum mapa salvo encontrado")
            return
        # Abre o mais recente
        path = os.path.join(pasta, arquivos[0])
        self._carregar(path)

    def _carregar(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            self.mapa = MapaEditor.from_dict(d)
            self.mapa.arquivo = path
            self._campo_nome.valor = self.mapa.nome
            self._historico.clear()
            self._hist_idx = -1
            self._salvar_historico()
            self._entidade_sel = None
            self._centralizar_mapa()
            self._flash(f"Aberto: {os.path.basename(path)}")
        except Exception as e:
            self._flash(f"Erro ao abrir: {e}")

    def _exportar_python(self):
        self._aplicar_campos_para_entidade()
        self.mapa.nome = self._campo_nome.valor or self.mapa.nome
        codigo = self.mapa.exportar_python()
        # Salva em arquivo .py
        nome_seg = self.mapa.nome.replace(" ", "_").lower()
        path = os.path.join(self._pasta_mapas(), f"{nome_seg}_export.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(codigo)
        # Tenta colocar na área de transferência
        try:
            pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, codigo.encode())
        except Exception:
            pass
        self._flash(f"Exportado: {os.path.basename(path)}")

    # ══════════════════════════════════════════════════════════
    # CÂMERA
    # ══════════════════════════════════════════════════════════

    def _centralizar_mapa(self):
        mapa_w = self.mapa.cols  * self.zoom
        mapa_h = self.mapa.linhas * self.zoom
        self.pan_x = max(0, (mapa_w - GRID_W) / 2)
        self.pan_y = max(0, (mapa_h - GRID_H) / 2)

    def _clampar_pan(self):
        mapa_w = self.mapa.cols  * self.zoom
        mapa_h = self.mapa.linhas * self.zoom
        max_x = max(0, mapa_w - GRID_W)
        max_y = max(0, mapa_h - GRID_H)
        self.pan_x = max(0, min(self.pan_x, max_x + self.zoom))
        self.pan_y = max(0, min(self.pan_y, max_y + self.zoom))

    # ══════════════════════════════════════════════════════════
    # FLASH MESSAGE
    # ══════════════════════════════════════════════════════════

    def _flash(self, msg: str):
        self._flash_msg  = msg
        self._flash_tick = 120

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def run(self) -> str:
        """Executa o editor. Retorna 'sair' ao fechar."""
        self._centralizar_mapa()
        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                resultado = self._processar_evento(event)
                if resultado:
                    return resultado

            self._atualizar()
            self._renderizar()

    # ══════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════

    def _processar_evento(self, event: pygame.event.Event) -> Optional[str]:
        # Fechar janela
        if event.type == pygame.QUIT:
            return "sair"

        # F11 alterna fullscreen
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            flags = self.screen.get_flags()
            if flags & pygame.FULLSCREEN:
                self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
            else:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            return None

        # Diálogo Novo Mapa
        if self._dlg_novo:
            return self._evento_dlg_novo(event)

        # Campos de texto do painel de propriedades
        for campo in self._campos.values():
            if campo.handle_event(event):
                self._aplicar_campos_para_entidade()

        # Campo de nome do mapa (topo)
        self._campo_nome.handle_event(event)
        if self._campo_nome.valor != self.mapa.nome:
            self.mapa.nome = self._campo_nome.valor
            self.mapa.modificado = True

        # Teclado
        if event.type == pygame.KEYDOWN:
            return self._teclado(event)

        # Scroll (zoom)
        if event.type == pygame.MOUSEWHEEL:
            if self.area_grid.collidepoint(pygame.mouse.get_pos()):
                self._zoom_em(event.y, pygame.mouse.get_pos())

        # Mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._mouse_down(event)
        if event.type == pygame.MOUSEBUTTONUP:
            self._mouse_up(event)
        if event.type == pygame.MOUSEMOTION:
            self._mouse_mover(event)

        return None

    def _evento_dlg_novo(self, event: pygame.event.Event) -> Optional[str]:
        self._dlg_cols_txt.handle_event(event)
        self._dlg_lin_txt.handle_event(event)
        self._dlg_nome_txt.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._confirmar_novo()
                return None
            if event.key == pygame.K_ESCAPE:
                self._dlg_novo = False
                return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Botão OK
            btn = pygame.Rect(W // 2 - 50, H // 2 + 80, 100, 34)
            if btn.collidepoint(event.pos):
                self._confirmar_novo()
        return None

    def _confirmar_novo(self):
        try:
            cols   = max(4, min(64, int(self._dlg_cols_txt.valor or "18")))
            linhas = max(4, min(64, int(self._dlg_lin_txt.valor or "13")))
        except ValueError:
            cols, linhas = 18, 13
        nome = self._dlg_nome_txt.valor or "mapa_novo"
        self.mapa = MapaEditor(nome=nome, cols=cols, linhas=linhas)
        self._campo_nome.valor = nome
        self._historico.clear()
        self._hist_idx = -1
        self._salvar_historico()
        self._entidade_sel = None
        self._centralizar_mapa()
        self._dlg_novo = False
        self._flash(f"Novo mapa: {cols}×{linhas}")

    def _teclado(self, event: pygame.event.Event) -> Optional[str]:
        ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL

        # Qualquer campo ativo → não processar atalhos
        todos_campos = list(self._campos.values()) + [self._campo_nome]
        if any(c.ativo for c in todos_campos):
            return None

        if event.key == pygame.K_ESCAPE:
            # Cancela linha/retângulo em andamento
            if self._lin_inicio or self._ret_inicio:
                self._lin_inicio = self._ret_inicio = None
                self._lin_preview = self._ret_preview = []
                return None
            return "menu"   # ESC sem ação em andamento = voltar ao menu

        if ctrl:
            if event.key == pygame.K_z:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self._refazer()
                else:
                    self._desfazer()
            elif event.key == pygame.K_y:
                self._refazer()
            elif event.key == pygame.K_s:
                self._salvar()
            elif event.key == pygame.K_n:
                self._dlg_novo = True
                self._dlg_cols_txt.valor = str(self.mapa.cols)
                self._dlg_lin_txt.valor  = str(self.mapa.linhas)
                self._dlg_nome_txt.valor = self.mapa.nome
            elif event.key == pygame.K_o:
                self._abrir_dialogo_arquivo()
            elif event.key == pygame.K_e:
                self._exportar_python()
            return None

        # Atalhos de ferramentas
        _mapa_tecla_ferr = {
            pygame.K_p: Ferramenta.PINCEL,
            pygame.K_b: Ferramenta.BORRACHA,
            pygame.K_f: Ferramenta.BALDE,
            pygame.K_l: Ferramenta.LINHA,
            pygame.K_r: Ferramenta.RETANGULO,
            pygame.K_i: Ferramenta.INIMIGO,
            pygame.K_o: Ferramenta.OBJETO,
        }
        if event.key in _mapa_tecla_ferr:
            self.ferramenta = _mapa_tecla_ferr[event.key]
            self._lin_inicio = self._ret_inicio = None
            self._flash(f"Ferramenta: {self.ferramenta.name.lower().capitalize()}")
            return None

        # Selecionar tile por tecla 1-5
        if pygame.K_1 <= event.key <= pygame.K_5:
            self.tile_sel = event.key - pygame.K_1
            self._flash(f"Tile: {TILE_NOMES[self.tile_sel]}")
            return None

        # Zoom com + e -
        if event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            self._zoom_em(1, (W // 2, H // 2))
        if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._zoom_em(-1, (W // 2, H // 2))

        return None

    def _zoom_em(self, delta: int, pos: Tuple[int, int]):
        fator = 1.2 if delta > 0 else 1 / 1.2
        novo  = int(self.zoom * fator)
        novo  = max(ZOOM_MIN, min(ZOOM_MAX, novo))
        if novo == self.zoom:
            return
        # Zoom centralizado no cursor
        px, py = pos
        gx = (px - GRID_X + self.pan_x) / self.zoom
        gy = (py - GRID_Y + self.pan_y) / self.zoom
        self.zoom  = novo
        self.pan_x = gx * novo - (px - GRID_X)
        self.pan_y = gy * novo - (py - GRID_Y)
        self._clampar_pan()

    def _mouse_down(self, event: pygame.event.Event) -> Optional[str]:
        mx, my = event.pos

        # Clique nos botões da barra superior
        if my < TOPO_H:
            return self._click_topo(mx, my, event.button)

        if not self.area_grid.collidepoint(mx, my):
            return None

        col, linha = self._pixel_para_grid(mx, my)

        # Pan com botão do meio ou Espaço+LMB
        if event.button == 2 or (event.button == 1 and
                                  pygame.key.get_pressed()[pygame.K_SPACE]):
            self._pan_ativo   = True
            self._pan_inicio  = (mx, my)
            self._pan_base    = (self.pan_x, self.pan_y)
            return None

        if event.button == 1:
            self._salvar_historico()
            self._executar_ferramenta(col, linha, apagar=False)
            self._pintando = True

        if event.button == 3:
            self._salvar_historico()
            self._executar_ferramenta(col, linha, apagar=True)
            self._apagando = True

        return None

    def _mouse_up(self, event: pygame.event.Event):
        if event.button == 2:
            self._pan_ativo = False
        if event.button == 1:
            self._pintando = False
            # Finaliza linha / retângulo
            col, linha = self._pixel_para_grid(*event.pos)
            if self.ferramenta == Ferramenta.LINHA and self._lin_inicio:
                c0, l0 = self._lin_inicio
                for c, l in self._celulas_linha(c0, l0, col, linha):
                    self._aplicar_tile(c, l, self.tile_sel)
                self._lin_inicio  = None
                self._lin_preview = []
                self.mapa.modificado = True
            if self.ferramenta == Ferramenta.RETANGULO and self._ret_inicio:
                c0, l0 = self._ret_inicio
                for c, l in self._celulas_retangulo(c0, l0, col, linha):
                    self._aplicar_tile(c, l, self.tile_sel)
                self._ret_inicio  = None
                self._ret_preview = []
                self.mapa.modificado = True
        if event.button == 3:
            self._apagando = False

    def _mouse_mover(self, event: pygame.event.Event):
        mx, my = event.pos

        # Pan
        if self._pan_ativo:
            dx = mx - self._pan_inicio[0]
            dy = my - self._pan_inicio[1]
            self.pan_x = self._pan_base[0] - dx
            self.pan_y = self._pan_base[1] - dy
            self._clampar_pan()
            return

        if not self.area_grid.collidepoint(mx, my):
            self.cursor_grid = None
            return

        col, linha = self._pixel_para_grid(mx, my)
        self.cursor_grid = (col, linha)

        # Preview de linha/retângulo
        if self.ferramenta == Ferramenta.LINHA and self._lin_inicio:
            c0, l0 = self._lin_inicio
            self._lin_preview = self._celulas_linha(c0, l0, col, linha)
        if self.ferramenta == Ferramenta.RETANGULO and self._ret_inicio:
            c0, l0 = self._ret_inicio
            self._ret_preview = self._celulas_retangulo(c0, l0, col, linha)

        # Pintura contínua com botão pressionado
        if self._pintando and self.ferramenta in (Ferramenta.PINCEL, Ferramenta.BORRACHA):
            self._aplicar_tile(col, linha,
                               1 if self.ferramenta == Ferramenta.BORRACHA else self.tile_sel)
            self.mapa.modificado = True
        if self._apagando:
            self._aplicar_tile(col, linha, 1)
            self.mapa.modificado = True

    def _executar_ferramenta(self, col: int, linha: int, apagar: bool):
        valor = 1 if apagar else self.tile_sel

        if self.ferramenta in (Ferramenta.PINCEL, Ferramenta.BORRACHA):
            self._aplicar_tile(col, linha, valor if not apagar else 1)

        elif self.ferramenta == Ferramenta.BALDE:
            self.mapa.flood_fill(col, linha, valor if not apagar else 1)

        elif self.ferramenta == Ferramenta.LINHA:
            if self._lin_inicio is None:
                self._lin_inicio = (col, linha)
                self._flash("Linha: clique no destino")
            # O commit da linha acontece no mouse_up

        elif self.ferramenta == Ferramenta.RETANGULO:
            if self._ret_inicio is None:
                self._ret_inicio = (col, linha)
                self._flash("Retângulo: clique no canto oposto")

        elif self.ferramenta == Ferramenta.INIMIGO and not apagar:
            if self.mapa.inimigo_em(col, linha):
                self.mapa.remover_inimigo(col, linha)
                self._entidade_sel = None
                self._flash("Inimigo removido")
            else:
                novo = {"col": col, "linha": linha, "nome": "Cultista",
                        "tipo": "humano", "tipo_ia": "agressivo", "hp": 8}
                self.mapa.inimigos.append(novo)
                self._selecionar_entidade(col, linha)
                self._flash("Inimigo colocado — edite propriedades →")

        elif self.ferramenta == Ferramenta.OBJETO and not apagar:
            if self.mapa.objeto_em(col, linha):
                self._selecionar_entidade(col, linha)
                self._flash("Objeto selecionado — edite propriedades →")
            else:
                novo = {"col": col, "linha": linha, "nome": "Objeto",
                        "tipo": "nota", "descricao": "", "item_concedido": ""}
                self.mapa.objetos.append(novo)
                self._selecionar_entidade(col, linha)
                self._flash("Objeto colocado — edite propriedades →")

        elif apagar and self.ferramenta in (Ferramenta.INIMIGO, Ferramenta.OBJETO):
            self.mapa.remover_inimigo(col, linha)
            self.mapa.remover_objeto(col, linha)
            if self._entidade_sel and \
               self._entidade_sel.get("col") == col and \
               self._entidade_sel.get("linha") == linha:
                self._entidade_sel = None

    def _click_topo(self, mx: int, my: int, btn: int) -> Optional[str]:
        """Processa cliques na barra superior."""
        for label, acao, rect in self._botoes_topo():
            if rect.collidepoint(mx, my) and btn == 1:
                if acao == "novo":
                    self._dlg_novo = True
                    self._dlg_cols_txt.valor = str(self.mapa.cols)
                    self._dlg_lin_txt.valor  = str(self.mapa.linhas)
                    self._dlg_nome_txt.valor = self.mapa.nome
                elif acao == "abrir":
                    self._abrir_dialogo_arquivo()
                elif acao == "salvar":
                    self._salvar()
                elif acao == "exportar":
                    self._exportar_python()
                elif acao == "sair":
                    return "menu"
        return None

    def _botoes_topo(self) -> List[Tuple[str, str, pygame.Rect]]:
        x = W - 360
        h = TOPO_H - 8
        y = 4
        bw = 68
        pad = 6
        return [
            ("Novo",     "novo",     pygame.Rect(x,             y, bw, h)),
            ("Abrir",    "abrir",    pygame.Rect(x + bw + pad,   y, bw, h)),
            ("Salvar",   "salvar",   pygame.Rect(x + bw*2+pad*2, y, bw, h)),
            ("Export",   "exportar", pygame.Rect(x + bw*3+pad*3, y, bw, h)),
            ("◀ Menu",   "sair",     pygame.Rect(x + bw*4+pad*4, y, bw, h)),
        ]

    # ══════════════════════════════════════════════════════════
    # ATUALIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _atualizar(self):
        if self._flash_tick > 0:
            self._flash_tick -= 1

    # ══════════════════════════════════════════════════════════
    # RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self):
        self.screen.fill(COR_BG)

        # Clip na área do grid e desenha
        self.screen.set_clip(self.area_grid)
        self._desenhar_grid()
        self.screen.set_clip(None)

        # Painéis
        self._desenhar_painel_paleta()
        self._desenhar_painel_propriedades()
        self._desenhar_barra_topo()
        self._desenhar_status()

        # Diálogo Novo Mapa (sobrepõe tudo)
        if self._dlg_novo:
            self._desenhar_dlg_novo()

        pygame.display.flip()

    # ── grid ──────────────────────────────────────────────────

    def _desenhar_grid(self):
        surf = self.screen
        z    = self.zoom

        # Fundo
        surf.fill((8, 8, 14), self.area_grid)

        # Tiles
        for l in range(self.mapa.linhas):
            for c in range(self.mapa.cols):
                px, py = self._grid_para_pixel(c, l)
                if px + z < GRID_X or px > GRID_X + GRID_W:
                    continue
                if py + z < GRID_Y or py > GRID_Y + GRID_H:
                    continue
                v   = self.mapa.get(c, l)
                cor = TILE_CORES.get(v, TILE_CORES[1])
                brd = TILE_BORDA.get(v, TILE_BORDA[1])
                rect = pygame.Rect(px, py, z, z)
                pygame.draw.rect(surf, cor, rect)
                if z >= 10:
                    pygame.draw.rect(surf, brd, rect, 1)

                # Ícone de tile no centro (quando zoom é suficiente)
                if z >= 20:
                    char = {0: "·", 1: " ", 2: "█", 3: "▪", 4: "⊙"}.get(v, "?")
                    if char and char != " ":
                        s = self.fn_small.render(char, True, brd)
                        surf.blit(s, (px + (z - s.get_width()) // 2,
                                      py + (z - s.get_height()) // 2))

        # Preview de linha/retângulo
        for c, l in self._lin_preview + self._ret_preview:
            px, py = self._grid_para_pixel(c, l)
            r = pygame.Rect(px + 2, py + 2, z - 4, z - 4)
            s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            s.fill((*TILE_CORES.get(self.tile_sel, TILE_CORES[1]), 140))
            surf.blit(s, r.topleft)

        # Inimigos
        for e in self.mapa.inimigos:
            px, py = self._grid_para_pixel(e["col"], e["linha"])
            if GRID_X <= px < GRID_X + GRID_W and GRID_Y <= py < GRID_Y + GRID_H:
                pad = max(2, z // 6)
                r = pygame.Rect(px + pad, py + pad, z - pad*2, z - pad*2)
                pygame.draw.rect(surf, COR_INIMIGO, r, border_radius=3)
                if z >= 20:
                    s = self.fn_small.render("I", True, (255, 255, 255))
                    surf.blit(s, (px + (z - s.get_width()) // 2,
                                  py + (z - s.get_height()) // 2))

        # Objetos
        for o in self.mapa.objetos:
            px, py = self._grid_para_pixel(o["col"], o["linha"])
            if GRID_X <= px < GRID_X + GRID_W and GRID_Y <= py < GRID_Y + GRID_H:
                pad = max(2, z // 6)
                r = pygame.Rect(px + pad, py + pad, z - pad*2, z - pad*2)
                pygame.draw.rect(surf, COR_OBJETO, r, border_radius=3)
                if z >= 20:
                    s = self.fn_small.render("O", True, (10, 10, 30))
                    surf.blit(s, (px + (z - s.get_width()) // 2,
                                  py + (z - s.get_height()) // 2))

        # Cursor hover
        if self.cursor_grid:
            c, l = self.cursor_grid
            if self._grid_valido(c, l):
                px, py = self._grid_para_pixel(c, l)
                r = pygame.Rect(px, py, z, z)
                s = pygame.Surface((z, z), pygame.SRCALPHA)
                s.fill((255, 255, 255, 40))
                surf.blit(s, r.topleft)
                pygame.draw.rect(surf, COR_DESTAQUE, r, 2)

        # Início de linha/retângulo
        for pt in ([self._lin_inicio] if self._lin_inicio else []) + \
                   ([self._ret_inicio] if self._ret_inicio else []):
            if pt:
                px, py = self._grid_para_pixel(pt[0], pt[1])
                pygame.draw.circle(surf, COR_DESTAQUE, (px + z // 2, py + z // 2), 5)

        # Grade (linhas muito finas)
        if z >= 14:
            mapa_pw = self.mapa.cols  * z
            mapa_ph = self.mapa.linhas * z
            ox = GRID_X - int(self.pan_x)
            oy = GRID_Y - int(self.pan_y)
            for c in range(self.mapa.cols + 1):
                lx = ox + c * z
                if GRID_X <= lx <= GRID_X + GRID_W:
                    pygame.draw.line(surf, COR_GRID_LINE,
                                     (lx, max(GRID_Y, oy)),
                                     (lx, min(GRID_Y + GRID_H, oy + mapa_ph)))
            for l in range(self.mapa.linhas + 1):
                ly = oy + l * z
                if GRID_Y <= ly <= GRID_Y + GRID_H:
                    pygame.draw.line(surf, COR_GRID_LINE,
                                     (max(GRID_X, ox), ly),
                                     (min(GRID_X + GRID_W, ox + mapa_pw), ly))

        # Seleção da entidade selecionada
        if self._entidade_sel:
            c = self._entidade_sel.get("col", 0)
            l = self._entidade_sel.get("linha", 0)
            px, py = self._grid_para_pixel(c, l)
            r = pygame.Rect(px, py, z, z)
            pygame.draw.rect(surf, COR_DESTAQUE, r, 2)

    # ── paleta ────────────────────────────────────────────────

    def _desenhar_painel_paleta(self):
        surf = self.screen
        pygame.draw.rect(surf, COR_PAINEL, self.area_pal)
        pygame.draw.line(surf, COR_BORDA,
                         (PAL_W - 1, TOPO_H), (PAL_W - 1, H - STATUS_H))

        y  = TOPO_H + 10
        fn = self.fn_hud

        # ── Tiles ─────────────────────────────────────────────
        s = fn.render("TILES  [1-5]", True, COR_DESTAQUE)
        surf.blit(s, (10, y)); y += 22

        SZ = 28
        for idx in range(5):
            r = pygame.Rect(10, y, SZ, SZ)
            pygame.draw.rect(surf, TILE_CORES[idx], r, border_radius=3)
            pygame.draw.rect(surf, TILE_BORDA[idx], r, 1, border_radius=3)
            if idx == self.tile_sel:
                pygame.draw.rect(surf, COR_DESTAQUE, r.inflate(4, 4), 2, border_radius=4)
            label = fn.render(f"[{idx+1}] {TILE_NOMES[idx]}", True,
                              COR_TEXTO if idx == self.tile_sel else COR_TEXTO_DIM)
            surf.blit(label, (10 + SZ + 8, y + (SZ - label.get_height()) // 2))
            y += SZ + 4

        # ── Ferramentas ───────────────────────────────────────
        y += 10
        s = fn.render("FERRAMENTAS", True, COR_DESTAQUE)
        surf.blit(s, (10, y)); y += 22

        ferramentas = [
            (Ferramenta.PINCEL,    "[P] Pincel"),
            (Ferramenta.BORRACHA,  "[B] Borracha"),
            (Ferramenta.BALDE,     "[F] Balde (fill)"),
            (Ferramenta.LINHA,     "[L] Linha"),
            (Ferramenta.RETANGULO, "[R] Retângulo"),
            (Ferramenta.INIMIGO,   "[I] Inimigo"),
            (Ferramenta.OBJETO,    "[O] Objeto"),
        ]
        for ferr, label in ferramentas:
            sel  = ferr == self.ferramenta
            cor  = COR_DESTAQUE if sel else COR_TEXTO_DIM
            bg   = (40, 36, 64) if sel else COR_PAINEL
            r    = pygame.Rect(6, y, PAL_W - 12, 24)
            pygame.draw.rect(surf, bg, r, border_radius=4)
            if sel:
                pygame.draw.rect(surf, COR_DESTAQUE, r, 1, border_radius=4)
            s = fn.render(label, True, cor)
            surf.blit(s, (12, y + (24 - s.get_height()) // 2))
            y += 26

        # ── Atalhos ───────────────────────────────────────────
        y += 10
        dicas = [
            "Scroll → zoom",
            "Espaço+drag → pan",
            "Ctrl+Z desfazer",
            "Ctrl+S salvar",
            "Ctrl+E exportar",
            "ESC → menu",
        ]
        fn2 = self.fn_mini
        for d in dicas:
            s = fn2.render(d, True, COR_TEXTO_DIM)
            surf.blit(s, (10, y)); y += 16

    # ── propriedades ──────────────────────────────────────────

    def _desenhar_painel_propriedades(self):
        surf = self.screen
        pygame.draw.rect(surf, COR_PAINEL2, self.area_prop)
        pygame.draw.line(surf, COR_BORDA,
                         (W - PROP_W, TOPO_H), (W - PROP_W, H - STATUS_H))

        fn = self.fn_hud
        bx = W - PROP_W + 10
        y  = TOPO_H + 10

        s = fn.render("PROPRIEDADES", True, COR_DESTAQUE)
        surf.blit(s, (bx, y)); y += 24

        if not self._entidade_sel:
            s = self.fn_small.render("Clique em [I] ou [O] no grid", True, COR_TEXTO_DIM)
            surf.blit(s, (bx, y)); y += 18
            s = self.fn_small.render("para colocar / editar", True, COR_TEXTO_DIM)
            surf.blit(s, (bx, y)); y += 28

            # Info do mapa
            pygame.draw.line(surf, COR_BORDA, (bx, y), (W - 10, y)); y += 8
            s = fn.render("MAPA", True, COR_DESTAQUE)
            surf.blit(s, (bx, y)); y += 22

            s = self.fn_small.render(f"Tamanho: {self.mapa.cols}×{self.mapa.linhas}", True, COR_TEXTO)
            surf.blit(s, (bx, y)); y += 18
            s = self.fn_small.render(f"Inimigos: {len(self.mapa.inimigos)}", True, COR_INIMIGO)
            surf.blit(s, (bx, y)); y += 18
            s = self.fn_small.render(f"Objetos: {len(self.mapa.objetos)}", True, COR_OBJETO)
            surf.blit(s, (bx, y)); y += 18

            # Tema
            y += 8
            s = fn.render("Tema:", True, COR_TEXTO_DIM)
            surf.blit(s, (bx, y)); y += 20
            for tema in TEMAS:
                sel = tema == self.mapa.tema
                cor = COR_DESTAQUE if sel else COR_TEXTO_DIM
                r   = pygame.Rect(bx, y, PROP_W - 20, 20)
                if sel:
                    pygame.draw.rect(surf, (36, 34, 58), r, border_radius=3)
                s   = self.fn_small.render(f"{'▶ ' if sel else '  '}{tema}", True, cor)
                surf.blit(s, (bx + 4, y + 2))
                # Clique para selecionar tema
                if pygame.mouse.get_pressed()[0] and r.collidepoint(pygame.mouse.get_pos()):
                    self.mapa.tema = tema
                y += 21
            return

        # ── Edição de entidade ─────────────────────────────────
        tipo_label = "INIMIGO" if self._tipo_sel == "inimigo" else "OBJETO"
        cor_label  = COR_INIMIGO if self._tipo_sel == "inimigo" else COR_OBJETO
        s = fn.render(tipo_label, True, cor_label)
        surf.blit(s, (bx, y)); y += 26

        lh = 30
        labels_inimigo = ["Nome:", "Tipo:", "HP:", "IA:"]
        labels_objeto  = ["Nome:", "Tipo:", "Descrição:", "Item:"]
        labels = labels_inimigo if self._tipo_sel == "inimigo" else labels_objeto

        campos_ord = (["nome", "tipo", "hp", "tipo_ia"] if self._tipo_sel == "inimigo"
                      else ["nome", "tipo", "desc", "item"])

        for i, (lbl, key) in enumerate(zip(labels, campos_ord)):
            # Reposiciona o campo
            self._campos[key].rect = pygame.Rect(bx, y + 14, PROP_W - 20, 24)
            s = self.fn_small.render(lbl, True, COR_TEXTO_DIM)
            surf.blit(s, (bx, y))
            self._campos[key].draw(surf, self.fn_small)
            y += lh + 8

        # Botão Remover
        y += 6
        btn = pygame.Rect(bx, y, PROP_W - 20, 28)
        pygame.draw.rect(surf, (80, 30, 30), btn, border_radius=4)
        s = fn.render("Remover", True, (255, 150, 150))
        surf.blit(s, s.get_rect(center=btn.center))
        if pygame.mouse.get_pressed()[0] and btn.collidepoint(pygame.mouse.get_pos()):
            c = self._entidade_sel.get("col", 0)
            l = self._entidade_sel.get("linha", 0)
            if self._tipo_sel == "inimigo":
                self.mapa.remover_inimigo(c, l)
            else:
                self.mapa.remover_objeto(c, l)
            self._entidade_sel = None
            self._flash("Removido")

    # ── barra superior ────────────────────────────────────────

    def _desenhar_barra_topo(self):
        surf = self.screen
        pygame.draw.rect(surf, COR_TOPO, pygame.Rect(0, 0, W, TOPO_H))
        pygame.draw.line(surf, COR_BORDA, (0, TOPO_H - 1), (W, TOPO_H - 1))

        # Nome do mapa (campo editável)
        s = self.fn_hud.render("🗺", True, COR_DESTAQUE)
        surf.blit(s, (8, (TOPO_H - s.get_height()) // 2))
        self._campo_nome.rect = pygame.Rect(32, 6, 240, 32)
        self._campo_nome.draw(surf, self.fn_hud)

        # Indicador de modificado
        if self.mapa.modificado:
            s = self.fn_hud.render("●", True, (220, 100, 60))
            surf.blit(s, (280, (TOPO_H - s.get_height()) // 2))

        # Botões
        mouse = pygame.mouse.get_pos()
        for label, acao, rect in self._botoes_topo():
            hover = rect.collidepoint(mouse)
            cor_bg = (60, 50, 90) if hover else (35, 32, 56)
            cor_t  = COR_DESTAQUE if hover else COR_TEXTO
            if acao == "sair":
                cor_bg = (70, 30, 30) if hover else (45, 22, 22)
                cor_t  = (255, 180, 180) if hover else (200, 130, 130)
            pygame.draw.rect(surf, cor_bg, rect, border_radius=5)
            pygame.draw.rect(surf, COR_BORDA, rect, 1, border_radius=5)
            s = self.fn_hud.render(label, True, cor_t)
            surf.blit(s, s.get_rect(center=rect.center))

    # ── status bar ────────────────────────────────────────────

    def _desenhar_status(self):
        surf = self.screen
        y = H - STATUS_H
        pygame.draw.rect(surf, COR_STATUS, pygame.Rect(0, y, W, STATUS_H))
        pygame.draw.line(surf, COR_BORDA, (0, y), (W, y))

        partes = []
        if self.cursor_grid:
            c, l = self.cursor_grid
            v = self.mapa.get(c, l)
            partes.append(f"({c}, {l})")
            if v >= 0:
                partes.append(f"tile: {TILE_NOMES.get(v, str(v))}")
            e = self.mapa.inimigo_em(c, l) or self.mapa.objeto_em(c, l)
            if e:
                partes.append(f"→ {e.get('nome', '?')}")

        partes.append(f"zoom: {self.zoom}px")
        partes.append(f"mapa: {self.mapa.cols}×{self.mapa.linhas}")

        fn = self.fn_mini
        x  = 10
        for p in partes:
            s = fn.render(p, True, COR_TEXTO_DIM)
            surf.blit(s, (x, y + (STATUS_H - s.get_height()) // 2))
            x += s.get_width() + 20

        # Flash message (à direita)
        if self._flash_tick > 0:
            alpha = min(255, self._flash_tick * 4)
            cor   = (int(COR_DESTAQUE[0] * alpha / 255),
                     int(COR_DESTAQUE[1] * alpha / 255),
                     int(COR_DESTAQUE[2] * alpha / 255))
            s = fn.render(self._flash_msg, True, cor)
            surf.blit(s, (W - s.get_width() - 15, y + (STATUS_H - s.get_height()) // 2))

    # ── diálogo novo mapa ─────────────────────────────────────

    def _desenhar_dlg_novo(self):
        surf = self.screen
        DW, DH = 340, 250
        DX = (W - DW) // 2
        DY = (H - DH) // 2

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        dlg = pygame.Rect(DX, DY, DW, DH)
        pygame.draw.rect(surf, (24, 22, 40), dlg, border_radius=10)
        pygame.draw.rect(surf, COR_BORDA, dlg, 2, border_radius=10)

        fn = self.fn_hud
        y  = DY + 16
        s  = self.fn_titulo.render("Novo Mapa", True, COR_DESTAQUE)
        surf.blit(s, s.get_rect(centerx=W//2, y=y)); y += 36

        for label, campo in [("Nome:", self._dlg_nome_txt),
                              ("Colunas:", self._dlg_cols_txt),
                              ("Linhas:", self._dlg_lin_txt)]:
            s = fn.render(label, True, COR_TEXTO_DIM)
            surf.blit(s, (DX + 20, y))
            campo.rect = pygame.Rect(DX + 110, y - 2, DW - 130, 26)
            campo.draw(surf, fn)
            y += 36

        # Botão OK
        btn = pygame.Rect(W//2 - 50, DY + DH - 50, 100, 34)
        hover = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, (60, 100, 60) if hover else (40, 70, 40), btn, border_radius=6)
        s = fn.render("OK [Enter]", True, COR_TEXTO)
        surf.blit(s, s.get_rect(center=btn.center))

        s = self.fn_small.render("[ESC] cancelar", True, COR_TEXTO_DIM)
        surf.blit(s, s.get_rect(centerx=W//2, y=DY + DH - 15))


# ══════════════════════════════════════════════════════════════
# STANDALONE
# ══════════════════════════════════════════════════════════════

def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
    clock  = pygame.time.Clock()
    pygame.display.set_caption("Editor de Mapas — CoC 7e")
    garantir_fontes(verbose=False)
    EditorMapa(screen, clock).run()
    pygame.quit()


if __name__ == "__main__":
    main()
