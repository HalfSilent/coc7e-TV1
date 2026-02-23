"""
demo.py — Demonstração standalone do sistema_chunks.
Gera chunks de um mapa 3×3 e mostra estatísticas dos tiles.

  python demo.py
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

# Prepara diretório temporário com estrutura esperada
_tmp = tempfile.mkdtemp()
_locais = os.path.join(_tmp, "Mundos", "Rio1923", "locais")
os.makedirs(_locais, exist_ok=True)

# Monkey-patch _LOCAIS_DIR antes do import
import sistema_chunks as sc
sc._LOCAIS_DIR = _locais

import numpy as np

print("=" * 55)
print("  Sistema de Chunks — Mapa do Rio 1923")
print("=" * 55)

# Gera 9 chunks (3×3)
chunks_gerados = {}
for cy in range(3):
    for cx in range(3):
        dados = np.full((sc.CHUNK_H, sc.CHUNK_W), sc.T_CALCADA, dtype=np.uint16)
        # Simula rua horizontal no centro
        dados[sc.CHUNK_H // 2, :] = sc.T_RUA
        chunk = sc.Chunk(cx, cy, dados)
        chunks_gerados[(cx, cy)] = chunk
        total = sc.CHUNK_W * sc.CHUNK_H
        rua_count = int(np.sum(dados == sc.T_RUA))
        print(f"  Chunk ({cx},{cy})  →  {total} tiles  |  rua: {rua_count}  |  calcada: {total - rua_count}")

print(f"\n  Total chunks: {len(chunks_gerados)}")
print(f"  Tiles por chunk: {sc.CHUNK_W}×{sc.CHUNK_H} = {sc.CHUNK_W * sc.CHUNK_H}")
print(f"  Mundo: {sc.MUNDO_W}×{sc.MUNDO_H} chunks = {sc.MUNDO_W * sc.CHUNK_W}×{sc.MUNDO_H * sc.CHUNK_H} tiles")
print("=" * 55)
print("Sistema de chunks funcionando!")

shutil.rmtree(_tmp)
