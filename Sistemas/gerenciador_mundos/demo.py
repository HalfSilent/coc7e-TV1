"""
demo.py — Demonstração standalone do gerenciador_mundos.
Cria um mundo temporário, lista mundos e acessa paths.

  python demo.py
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

# Monkey-patch _MUNDOS antes de importar para usar diretório temporário
import gerenciador_mundos as gm
from pathlib import Path
_tmp = Path(tempfile.mkdtemp())
gm._MUNDOS = _tmp / "Mundos"
gm._MUNDOS.mkdir(parents=True)

print("=" * 55)
print("  Gerenciador de Mundos")
print("=" * 55)

# Cria mundo de demonstração
meta = gm.criar("DemoCity", tile_w=32, tile_h=32, chunk_w=20, chunk_h=15,
                  mundo_w=4, mundo_h=3)
print(f"\n  Mundo criado: {meta['id']}")
print(f"  Tiles:  {meta['tile_w']}×{meta['tile_h']} px")
print(f"  Chunks: {meta['chunk_w']}×{meta['chunk_h']} tiles")
print(f"  Mundo:  {meta['mundo_w']}×{meta['mundo_h']} chunks")

# Lista mundos
mundos = gm.listar()
print(f"\n  Mundos disponíveis: {mundos}")

# Paths
p = gm.paths("DemoCity")
print("\n  Paths:")
for k, v in p.items():
    existe = "✓" if os.path.exists(v) else "—"
    print(f"    {existe} {k}: .../{os.path.relpath(v, _tmp)}")

print("\n" + "=" * 55)
print("Gerenciador de mundos funcionando!")

shutil.rmtree(_tmp)
