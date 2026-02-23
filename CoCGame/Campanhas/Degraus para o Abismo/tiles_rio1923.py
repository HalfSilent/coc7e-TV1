"""
tiles_rio1923.py — Tilesets do Rio de Janeiro, 1923.
Pertence à campanha "Degraus para o Abismo".

Gera texturas 32×32 com Pillow (arte colonial portuguesa) e exporta
pygame.Surface para uso em mundo_aberto.py e editor_mundo.py.

API pública:
    carregar_surfaces() -> dict[int, pygame.Surface]
        Converte tiles em pygame.Surface (requer pygame inicializado).
    gerar_todos_png()
        Salva os tiles como PNG em tilesets/ (para inspeção).

Nota: Espelha os IDs de mundo_aberto.T para evitar import circular.
"""
from __future__ import annotations

import io
import math
import os
import random
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter

# ── Caminhos ──────────────────────────────────────────────────────────
_AQUI     = Path(os.path.dirname(os.path.abspath(__file__)))
_TILESETS = _AQUI / "tilesets"
_TILESETS.mkdir(exist_ok=True)

# ── IDs de tile (espelha mundo_aberto.T) ──────────────────────────────
T_VAZIO    = 0
T_GRAMA    = 1
T_CALCADA  = 2
T_RUA      = 3
T_PAREDE   = 4
T_EDIFICIO = 5
T_AGUA     = 6
T_TERRA    = 7
T_PORTA    = 8
T_ARVORE   = 9
T_LAMPIAO  = 10
T_ESCADA   = 11

W = H = 32      # tamanho do tile em pixels
SEED = 1923


def _rng(tile_id: int, extra: int = 0) -> random.Random:
    return random.Random(tile_id * 9999 + extra * 31 + SEED)


def _pnoise(x: float, y: float, scale: float = 0.3) -> float:
    """Simplex/Perlin noise normalizado 0→1. Prioridade: opensimplex → noise → fallback."""
    try:
        from opensimplex import noise2
        return (noise2(x * scale, y * scale) + 1) / 2
    except ImportError:
        pass
    try:
        from noise import pnoise2
        return (pnoise2(x * scale, y * scale, octaves=3) + 1) / 2
    except ImportError:
        pass
    r = _rng(int(x * 100 + y * 7))
    return r.random()


# ══════════════════════════════════════════════════════════════════════
#  GERADORES DE TILE
# ══════════════════════════════════════════════════════════════════════

def _vazio() -> Image.Image:
    return Image.new("RGBA", (W, H), (10, 14, 28, 255))


def _grama() -> Image.Image:
    """Gramado tropical com variação orgânica (Perlin noise)."""
    img = Image.new("RGBA", (W, H))
    pixels = img.load()
    for py in range(H):
        for px in range(W):
            n = _pnoise(px + 0.5, py + 0.5, 0.25)
            r = int(32 + n * 22)
            g = int(72 + n * 38)
            b = int(32 + n * 12)
            pixels[px, py] = (r, g, b, 255)

    draw = ImageDraw.Draw(img)
    rng  = _rng(T_GRAMA)
    # Hastes de grama
    for _ in range(10):
        bx = rng.randint(2, W - 3)
        by = rng.randint(6, H - 2)
        alt = rng.randint(3, 7)
        lean = rng.randint(-2, 2)
        g_dark = (20, 55, 20, 255)
        draw.line([(bx, by), (bx + lean, by - alt)], fill=g_dark, width=1)
        draw.line([(bx+1, by), (bx + lean + 1, by - alt + 1)], fill=(28, 65, 28, 180), width=1)
    return img


def _calcada() -> Image.Image:
    """Calçada portuguesa — mosaico de pedras irregulares claras e escuras."""
    img = Image.new("RGBA", (W, H), (148, 138, 126, 255))
    draw = ImageDraw.Draw(img)
    rng  = _rng(T_CALCADA)

    # Grade de pedras deslocadas por linha (offset alternado)
    for row in range(H // 7 + 1):
        y0 = row * 7
        off = 4 if row % 2 else 0
        for col in range(-1, W // 8 + 2):
            x0 = col * 8 + off
            # Varia levemente a cor da pedra
            v  = rng.randint(-14, 14)
            bc = max(100, min(255, 148 + v))
            gc = max(92, min(255, 138 + v))
            rc = max(86, min(255, 126 + v))
            draw.rectangle(
                [x0 + 1, y0 + 1, x0 + 6, y0 + 5],
                fill=(bc, gc, rc),
                outline=(88, 80, 72),
            )
    # Bordas luminosas
    draw.line([(0, 0), (W - 1, 0)], fill=(168, 158, 146), width=1)
    draw.line([(0, 0), (0, H - 1)], fill=(168, 158, 146), width=1)
    return img


def _rua() -> Image.Image:
    """Rua de paralelepípedos — pavimento de pedra típico do Rio de 1923."""
    img = Image.new("RGBA", (W, H), (78, 68, 56, 255))
    draw = ImageDraw.Draw(img)
    rng  = _rng(T_RUA)

    # Paralelepípedos (pedras menores, mais escuras)
    for row in range(H // 5 + 1):
        y0  = row * 5
        off = 5 if row % 2 else 0
        for col in range(-1, W // 9 + 2):
            x0 = col * 9 + off
            v  = rng.randint(-10, 10)
            c  = max(60, min(200, 80 + v))
            draw.rectangle(
                [x0 + 1, y0 + 1, x0 + 7, y0 + 3],
                fill=(c, c - 10, c - 18),
                outline=(55, 46, 36),
            )
    # Linha central pontilhada (marcação de bonde)
    for i in range(1, H, 5):
        draw.rectangle([W // 2 - 1, i, W // 2 + 1, i + 2],
                       fill=(130, 112, 30))
    return img


def _parede() -> Image.Image:
    """Parede de tijolos coloniais — tijolos vermelhos com rejunte."""
    img = Image.new("RGBA", (W, H), (52, 32, 22, 255))   # rejunte
    draw = ImageDraw.Draw(img)
    rng  = _rng(T_PAREDE)

    for row in range(H // 6 + 1):
        y0  = row * 6
        off = 8 if row % 2 else 0
        for col in range(-1, W // 14 + 2):
            x0 = col * 14 + off
            v  = rng.randint(-18, 18)
            r  = max(100, min(220, 168 + v))
            g  = max(50,  min(120, 72  + v // 3))
            b  = max(30,  min(80,  48  + v // 5))
            draw.rectangle(
                [x0 + 1, y0 + 1, x0 + 12, y0 + 4],
                fill=(r, g, b),
            )
            # Luz na borda superior do tijolo
            draw.line([(x0 + 1, y0 + 1), (x0 + 12, y0 + 1)],
                      fill=(min(255, r + 30), min(255, g + 18), min(255, b + 10)), width=1)
    return img


def _edificio() -> Image.Image:
    """Fachada de reboco de cal — parede colonial brancacenta."""
    img = Image.new("RGBA", (W, H))
    pixels = img.load()
    for py in range(H):
        for px in range(W):
            n  = _pnoise(px * 0.9, py * 0.9, 0.18)
            c  = int(190 + n * 30)
            cr = max(0, min(255, c - 6))
            pixels[px, py] = (c, c - 4, cr, 255)

    draw = ImageDraw.Draw(img)
    rng  = _rng(T_EDIFICIO)
    # Trincas/fissuras
    for _ in range(4):
        x0 = rng.randint(3, W - 4)
        y0 = rng.randint(2, H - 10)
        pts = [(x0, y0)]
        for _ in range(rng.randint(3, 6)):
            pts.append((pts[-1][0] + rng.randint(-2, 2),
                        pts[-1][1] + rng.randint(1, 3)))
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=(155, 148, 132, 200), width=1)
    # Moldura inferior (rodapé de azulejo)
    draw.rectangle([0, H - 5, W - 1, H - 1], fill=(160, 170, 185))
    draw.line([(0, H - 5), (W - 1, H - 5)], fill=(120, 130, 145), width=1)
    return img


def _agua() -> Image.Image:
    """Baía de Guanabara — azul profundo com ondas."""
    img = Image.new("RGBA", (W, H))
    pixels = img.load()
    for py in range(H):
        for px in range(W):
            n  = _pnoise(px * 1.2, py * 0.8, 0.3)
            r  = int(18  + n * 20)
            g  = int(60  + n * 30)
            b  = int(128 + n * 40)
            pixels[px, py] = (r, g, b, 255)

    draw = ImageDraw.Draw(img)
    # Cristas de onda
    for row in range(H // 5):
        y = row * 5 + 3
        for x in range(0, W, 10):
            dx = int(math.sin((x + row * 3) * 0.6) * 2)
            draw.arc([x, y + dx - 2, x + 7, y + dx + 2],
                     180, 360, fill=(60, 120, 200, 160), width=1)
    # Reflexo de luz
    draw.line([(W // 3, 2), (W // 3 + 5, 2)],
              fill=(140, 190, 240, 120), width=1)
    return img


def _terra() -> Image.Image:
    """Chão de terra batida."""
    img = Image.new("RGBA", (W, H))
    pixels = img.load()
    for py in range(H):
        for px in range(W):
            n  = _pnoise(px * 1.1, py * 0.9, 0.22)
            r  = int(98  + n * 30)
            g  = int(68  + n * 20)
            b  = int(42  + n * 12)
            pixels[px, py] = (r, g, b, 255)

    draw = ImageDraw.Draw(img)
    rng  = _rng(T_TERRA)
    # Seixos
    for _ in range(5):
        sx = rng.randint(3, W - 4)
        sy = rng.randint(3, H - 4)
        a  = rng.randint(2, 4)
        b2 = rng.randint(1, 3)
        draw.ellipse([sx - a, sy - b2, sx + a, sy + b2],
                     fill=(118, 90, 60), outline=(82, 58, 36))
    return img


def _porta() -> Image.Image:
    """Porta colonial com arco em ogiva e duas folhas de madeira."""
    img = _calcada().copy()     # base = calçada
    draw = ImageDraw.Draw(img)

    aw = 20          # largura do arco
    ax = W // 2
    ay_arco = 4      # topo do arco
    ah = 13          # altura do arco (semicírculo)
    ay_base = ay_arco + ah

    # Batentes laterais
    draw.rectangle([ax - aw // 2 - 2, ay_base - 2, ax - aw // 2,     H - 1],
                   fill=(88, 58, 32))
    draw.rectangle([ax + aw // 2,     ay_base - 2, ax + aw // 2 + 2, H - 1],
                   fill=(88, 58, 32))

    # Arco (semicircular)
    draw.arc([ax - aw // 2, ay_arco, ax + aw // 2, ay_arco + ah * 2],
             180, 360, fill=(88, 58, 32), width=3)

    # Folhas da porta (madeira escura)
    for side, x0, x1 in [("L", ax - aw // 2 + 1, ax - 1),
                          ("R", ax + 1, ax + aw // 2 - 1)]:
        draw.rectangle([x0, ay_base - 1, x1, H - 2], fill=(148, 98, 42))
        # Prancha central
        mid = (x0 + x1) // 2
        draw.line([(mid, ay_base), (mid, H - 3)], fill=(108, 72, 28), width=1)
        # Moldura
        draw.rectangle([x0, ay_base - 1, x1, H - 2], outline=(100, 68, 28), width=1)

    # Maçaneta
    draw.ellipse([ax - 3, H // 2 - 1, ax, H // 2 + 2], fill=(210, 168, 40))

    # Lintel (pedra sobre a porta)
    draw.rectangle([ax - aw // 2 - 2, ay_base - 3, ax + aw // 2 + 2, ay_base - 1],
                   fill=(108, 98, 88))
    return img


def _arvore() -> Image.Image:
    """Árvore tropical — copa exuberante sobre tronco."""
    img = _grama().copy()    # base = grama
    draw = ImageDraw.Draw(img)

    cx = W // 2
    cy = H // 2

    # Tronco
    draw.rectangle([cx - 2, cy + 2, cx + 2, H - 2], fill=(80, 52, 24))
    draw.line([(cx - 1, cy + 2), (cx - 1, H - 3)], fill=(100, 68, 32), width=1)

    # Camadas de copa (de trás para frente)
    camadas = [
        (13, -2,  (22, 68, 22,  230)),
        (11, -5,  (28, 85, 28,  220)),
        ( 9, -8,  (36, 100, 36, 210)),
        ( 7, -10, (44, 118, 44, 200)),
    ]
    for r, dy, cor in camadas:
        draw.ellipse([cx - r, cy + dy - r, cx + r, cy + dy + r], fill=cor)

    # Brilho de luz solar
    draw.ellipse([cx - 4, cy - 13, cx + 2, cy - 8],
                 fill=(80, 160, 80, 140))
    return img


def _lampiao() -> Image.Image:
    """Lampião a gás colonial — poste de ferro fundido com halo."""
    img = _calcada().copy()    # base = calçada
    draw = ImageDraw.Draw(img)

    px_c = W // 2
    py_top = 5       # topo da lanterna

    # Halo de luz (camadas concêntricas transparentes)
    for r in range(11, 0, -2):
        alpha = int(8 + (11 - r) * 9)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ovd = ImageDraw.Draw(ov)
        ovd.ellipse([px_c - r, py_top - r + 4, px_c + r, py_top + r + 4],
                    fill=(220, 200, 80, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), ov)

    draw = ImageDraw.Draw(img)

    # Poste
    draw.rectangle([px_c - 1, py_top + 12, px_c + 1, H - 2], fill=(62, 54, 44))
    # Base
    draw.rectangle([px_c - 5, H - 3, px_c + 5, H - 1], fill=(52, 44, 34))
    # Cabeça do poste
    draw.rectangle([px_c - 5, py_top + 2, px_c + 5, py_top + 12],
                   fill=(50, 44, 36))
    # Vidro da lanterna (âmbar)
    draw.rectangle([px_c - 4, py_top + 3, px_c + 4, py_top + 11],
                   fill=(240, 218, 90))
    # Detalhe de ferro
    draw.line([(px_c - 5, py_top + 7), (px_c + 5, py_top + 7)],
              fill=(40, 34, 28), width=1)
    return img


def _escada() -> Image.Image:
    """Escada de pedra — degraus coloniais em perspectiva."""
    img = Image.new("RGBA", (W, H), (88, 72, 52, 255))
    draw = ImageDraw.Draw(img)

    # 4 degraus em perspectiva frontal, cada um mais estreito e alto
    step_h = H // 4
    for i in range(4):
        y0     = i * step_h
        indent = i * 3
        x0     = indent
        x1     = W - 1 - indent
        # Face do degrau
        draw.rectangle([x0, y0, x1, y0 + step_h - 2],
                       fill=(max(68, 108 - i * 8), max(52, 88 - i * 8),
                              max(36, 62 - i * 6)))
        # Borda de luz (topo do degrau)
        draw.line([(x0, y0), (x1, y0)],
                  fill=(min(255, 148 - i * 6), min(255, 120 - i * 5),
                         min(255, 88 - i * 4)), width=2)
        # Sombra lateral
        draw.line([(x1, y0), (x1, y0 + step_h - 2)],
                  fill=(60, 48, 32), width=1)
    return img


# ══════════════════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════════════════

NOMES: dict[int, str] = {
    T_VAZIO:    "Vazio",
    T_GRAMA:    "Grama",
    T_CALCADA:  "Calcada",
    T_RUA:      "Rua",
    T_PAREDE:   "Parede",
    T_EDIFICIO: "Edificio",
    T_AGUA:     "Agua",
    T_TERRA:    "Terra",
    T_PORTA:    "Porta",
    T_ARVORE:   "Arvore",
    T_LAMPIAO:  "Lampiao",
    T_ESCADA:   "Escada",
}

_GERADORES: dict[int, Callable[[], Image.Image]] = {
    T_VAZIO:    _vazio,
    T_GRAMA:    _grama,
    T_CALCADA:  _calcada,
    T_RUA:      _rua,
    T_PAREDE:   _parede,
    T_EDIFICIO: _edificio,
    T_AGUA:     _agua,
    T_TERRA:    _terra,
    T_PORTA:    _porta,
    T_ARVORE:   _arvore,
    T_LAMPIAO:  _lampiao,
    T_ESCADA:   _escada,
}


# ══════════════════════════════════════════════════════════════════════
#  API PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def gerar_imagem(tile_id: int) -> Image.Image:
    """Retorna a imagem Pillow para um tile_id."""
    gen = _GERADORES.get(tile_id)
    if gen is None:
        return _vazio()
    return gen()


def gerar_todos_png() -> None:
    """Salva todos os tiles como PNG em tilesets/."""
    for tid, gen in _GERADORES.items():
        nome    = NOMES.get(tid, str(tid)).lower()
        caminho = _TILESETS / f"{tid:02d}_{nome}.png"
        img     = gen()
        img.save(str(caminho))
        print(f"  ✓  {caminho.name}")


def carregar_surfaces(forcar_regerar: bool = False) -> "dict[int, pygame.Surface]":
    """
    Converte todos os tiles em pygame.Surface (RGBA).
    Requer pygame.init() chamado antes.

    Cache em disco: na primeira execução gera as imagens com Pillow e
    salva como PNG em tilesets/. Nas execuções seguintes carrega direto
    do PNG (muito mais rápido). Use forcar_regerar=True para regenerar.
    """
    try:
        import pygame
    except ImportError as exc:
        raise RuntimeError("pygame não disponível") from exc

    result: dict[int, pygame.Surface] = {}

    for tid, gen in _GERADORES.items():
        nome  = NOMES.get(tid, str(tid)).lower()
        cache = _TILESETS / f"{tid:02d}_{nome}.png"

        img: "Image.Image | None" = None

        # Tenta carregar do cache
        if not forcar_regerar and cache.exists():
            try:
                surf = pygame.image.load(str(cache)).convert_alpha()
                result[tid] = surf
                continue
            except Exception:
                pass   # cache corrompido — regenera

        # Gera com Pillow
        img  = gen()
        data = img.tobytes("raw", "RGBA")
        surf = pygame.image.frombuffer(data, (W, H), "RGBA").convert_alpha()
        result[tid] = surf

        # Salva para cache
        try:
            img.save(str(cache))
        except Exception:
            pass

    return result


# ══════════════════════════════════════════════════════════════════════
#  __main__ — gera PNGs e mostra uma prévia
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Gerando tilesets do Rio de Janeiro, 1923...")
    gerar_todos_png()
    print(f"\n{len(_GERADORES)} tiles salvos em: {_TILESETS}")

    # Opcional: prévia via pygame
    try:
        import pygame
        pygame.init()
        n   = len(_GERADORES)
        cols = 6
        rows = (n + cols - 1) // cols
        scale = 4
        tela = pygame.display.set_mode((cols * W * scale + 12,
                                        rows * H * scale + 40))
        pygame.display.set_caption("Tileset — Rio de Janeiro 1923")
        surfs = carregar_surfaces()
        clock = pygame.time.Clock()
        fn    = pygame.font.SysFont("monospace", 9)

        while True:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                    pygame.quit()
                    raise SystemExit

            tela.fill((10, 14, 28))
            for i, (tid, surf) in enumerate(surfs.items()):
                col = i % cols
                row = i // cols
                sx  = 6 + col * W * scale
                sy  = 6 + row * H * scale + 10
                tela.blit(pygame.transform.scale(surf, (W * scale, H * scale)),
                           (sx, sy))
                lbl = fn.render(f"{tid} {NOMES.get(tid,'')[:8]}", True,
                                (200, 190, 170))
                tela.blit(lbl, (sx, sy + H * scale + 1))
            pygame.display.flip()
            clock.tick(30)

    except ImportError:
        print("(pygame não disponível para prévia)")
