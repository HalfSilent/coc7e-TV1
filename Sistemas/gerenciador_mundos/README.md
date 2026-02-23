# gerenciador_mundos

Cria e gerencia mundos de jogo. Cada mundo fica em `Mundos/{id}/` com seus chunks,
locais e save.

## Uso

```python
import gerenciador_mundos as gm

# Criar novo mundo
meta = gm.criar("Rio1923", tile_w=32, tile_h=32, chunk_w=20, chunk_h=15,
                 mundo_w=8, mundo_h=6)

# Listar mundos existentes
ids = gm.listar()   # ["Rio1923"]

# Acessar paths do mundo
p = gm.paths("Rio1923")
# {
#   "raiz":    "Mundos/Rio1923/",
#   "chunks":  "Mundos/Rio1923/chunks/",
#   "locais":  "Mundos/Rio1923/locais/",
#   "save":    "Mundos/Rio1923/save.json",
#   "temporal":"Mundos/Rio1923/temporal.db",
#   "meta":    "Mundos/Rio1923/mundo.json",
# }

# Descobrir qual mundo uma campanha usa
mundo_id = gm.mundo_da_campanha("/path/to/campanha/")
```

## Demo

```
python demo.py
```
