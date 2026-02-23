# sistema_chunks

Gerencia o mapa do mundo em chunks (blocos de tiles) carregados sob demanda.

## Estrutura

```
Mundos/Rio1923/
├── chunks/
│   ├── 0_0.npy     ← cada arquivo = 1 chunk (20×15 tiles)
│   ├── 0_1.npy
│   └── ...
└── locais/
    └── casa_investigador.tmj
```

## Dimensões

| Constante | Valor | Descrição |
|---|---|---|
| `CHUNK_W` | 20 | tiles por linha |
| `CHUNK_H` | 15 | tiles por coluna |
| `MUNDO_W` | 8 | chunks horizontais |
| `MUNDO_H` | 6 | chunks verticais |

## Uso

```python
from sistema_chunks import Chunk, carregar_chunk, salvar_chunk
import numpy as np

dados = np.full((15, 20), T_CALCADA, dtype=np.uint16)
chunk = Chunk(0, 0, dados)
salvar_chunk(chunk, "Mundos/Rio1923/chunks/")
```

## Demo

```
python demo.py
```
