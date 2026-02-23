"""
projecao_iso.py — Projeção isométrica para o CoCGame.

Converte coordenadas de grid cartesiano (col, row) para pixels isométricos
e vice-versa.  Toda a lógica de jogo (colisão, chunks, eventos) continua
usando coordenadas cartesianas — apenas a renderização usa este módulo.

Convenção dos tiles Kenney (medido nos pixels reais do PNG):
  - Tile base (chão):  100 × 65 px  →  losango visível: 100 × 48 px
  - Vértice topo em x=49, vértice direito em (99, 24) → ISO_DX=50, ISO_DY=24
  - Tiles altos (edifícios) têm altura extra acima da base

Sistema de coordenadas:
  - (col=0, row=0)  →  tile mais ao NORTE (topo do diamante)
  - col aumenta para leste (direita-baixo)
  - row aumenta para sul  (esquerda-baixo)

Origem da câmera:
  - iso_origem_x = tela_w // 2   (centro horizontal da tela)
  - iso_origem_y = ISO_H_BASE     (margem superior)
"""
from __future__ import annotations

# ── Dimensões base dos tiles Kenney roads/buildings ──────────
ISO_W       = 100   # largura total do tile de chão
ISO_H_BASE  = 65    # altura total do tile de chão (inclui borda inferior ~17px)
ISO_H_TOPO  = 48    # altura real do losango: vértice direito está em y=24 → 2×24=48
ISO_DX      = ISO_W // 2         # 50 — passo horizontal por col/row
ISO_DY      = ISO_H_TOPO // 2   # 24 — passo vertical (medido nos pixels reais do PNG)


def cart_para_iso(col: int, row: int,
                  origem_x: int = 0, origem_y: int = 0) -> tuple[int, int]:
    """
    Converte coordenadas de grid (col, row) para pixels isométricos.

    A origem (0,0) do grid resulta em (origem_x, origem_y) na tela.
    O tile é posicionado pelo seu canto SUPERIOR-ESQUERDO.

    Args:
        col:      coluna no grid cartesiano
        row:      linha no grid cartesiano
        origem_x: deslocamento horizontal da câmera (px)
        origem_y: deslocamento vertical da câmera (px)

    Returns:
        (x, y) — canto superior-esquerdo do tile na tela
    """
    x = (col - row) * ISO_DX + origem_x
    y = (col + row) * ISO_DY + origem_y
    return x, y


def iso_para_cart(sx: int, sy: int,
                  origem_x: int = 0, origem_y: int = 0) -> tuple[int, int]:
    """
    Converte posição de pixel na tela para coordenadas de grid (col, row).
    Usado para detectar qual tile o mouse está sobre.

    Args:
        sx: posição X do mouse na tela
        sy: posição Y do mouse na tela
        origem_x: deslocamento horizontal da câmera (px)
        origem_y: deslocamento vertical da câmera (px)

    Returns:
        (col, row) — coordenadas no grid cartesiano (sem arredondamento)
    """
    # Remove offset da câmera
    rx = sx - origem_x
    ry = sy - origem_y

    # Inverso da projeção:
    #   rx = (col - row) * ISO_DX   →  col - row = rx / ISO_DX
    #   ry = (col + row) * ISO_DY   →  col + row = ry / ISO_DY
    col = (rx / ISO_DX + ry / ISO_DY) / 2
    row = (ry / ISO_DY - rx / ISO_DX) / 2
    return int(col), int(row)


def mundo_para_iso_origem(cam_x: float, cam_y: float,
                           tela_w: int, tela_h: int,
                           tile_w: int = 32) -> tuple[int, int]:
    """
    Calcula a origem isométrica (offset de câmera) para que o ponto
    (cam_x, cam_y) em pixels de mundo cartesiano fique centrado na tela.

    O motor armazena posição do player em pixels cartesianos (px = col*tile_w).
    Este método converte esse offset para o sistema isométrico.

    Args:
        cam_x:  posição X da câmera em pixels cartesianos (centro do player)
        cam_y:  posição Y da câmera em pixels cartesianos
        tela_w: largura da tela em pixels
        tela_h: altura da tela em pixels
        tile_w: tamanho do tile cartesiano (padrão 32px)

    Returns:
        (origem_x, origem_y) — offset a passar para cart_para_iso
    """
    # Converte câmera cartesiana para col/row fracionário
    col = cam_x / tile_w
    row = cam_y / tile_w   # tile é quadrado

    # Posição isométrica do ponto da câmera sem offset
    iso_x = (col - row) * ISO_DX
    iso_y = (col + row) * ISO_DY

    # Centraliza na tela
    origem_x = tela_w  // 2 - iso_x
    origem_y = tela_h  // 4 - iso_y   # 1/4 do topo dá margem para edifícios altos
    return int(origem_x), int(origem_y)


def ordem_render(cols: int, rows: int) -> list[tuple[int, int]]:
    """
    Retorna a lista de (col, row) na ordem correta para o painter's algorithm.
    Tiles com menor (col + row) são desenhados primeiro (mais ao fundo).
    Tiles com maior (col + row) são desenhados por cima (mais à frente).

    Args:
        cols: número de colunas do chunk (CHUNK_W)
        rows: número de linhas do chunk (CHUNK_H)

    Returns:
        lista de (col, row) em ordem de profundidade crescente
    """
    pares = [(c, r) for r in range(rows) for c in range(cols)]
    return sorted(pares, key=lambda cr: cr[0] + cr[1])


def rect_iso_tile(col: int, row: int,
                  origem_x: int = 0, origem_y: int = 0,
                  tile_h_total: int = ISO_H_BASE) -> tuple[int, int, int, int]:
    """
    Retorna o bounding rect (x, y, w, h) do tile isométrico na tela.
    Útil para detecção de clique e culling.

    Args:
        col, row:       posição no grid
        origem_x/y:     offset da câmera
        tile_h_total:   altura total do sprite (ISO_H_BASE para chão, mais para edifícios)

    Returns:
        (x, y, w, h)
    """
    x, y = cart_para_iso(col, row, origem_x, origem_y)
    return x, y, ISO_W, tile_h_total


# ── Utilidade: visibilidade de frustum ───────────────────────

def tiles_visiveis(cam_x: float, cam_y: float,
                   tela_w: int, tela_h: int,
                   chunk_w: int, chunk_h: int,
                   tile_w: int = 32,
                   margem: int = 2) -> tuple[int, int, int, int]:
    """
    Calcula o range de tiles (col, row) visíveis na tela com uma margem extra.
    Evita renderizar tiles fora da tela (culling).

    Returns:
        (col0, row0, col1, row1) — intervalo a renderizar
    """
    col_cam = cam_x / tile_w
    row_cam = cam_y / tile_w

    # Tiles visíveis aproximados pela largura/altura da tela
    vis_cols = tela_w // ISO_DX + margem * 2
    vis_rows = tela_h // ISO_DY + margem * 2

    col0 = max(0, int(col_cam) - vis_cols // 2)
    row0 = max(0, int(row_cam) - vis_rows // 2)
    col1 = min(chunk_w, col0 + vis_cols)
    row1 = min(chunk_h, row0 + vis_rows)
    return col0, row0, col1, row1
