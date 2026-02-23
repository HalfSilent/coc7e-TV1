# sistema_pericia

Sistema de testes de perícia do **Call of Cthulhu 7ª Edição**.

## Mecânica

Dado d100. Resultado menor ou igual ao valor da perícia = sucesso.

| Resultado | Condição |
|---|---|
| ≤ valor ÷ 5 | **Extremo** (melhor possível) |
| ≤ valor ÷ 2 | **Difícil** |
| ≤ valor | **Regular** |
| > valor, ≤ 95 | **Falha** |
| 96–100 | **Fumble** (falha crítica) |

## Uso

```python
from sistema_pericia import SistemaPericia

investigador = {"pericias": {"Furtividade": 45}}
sp = SistemaPericia(investigador)
resultado = sp.testar("Furtividade")
# {"grau": "regular", "rolagem": 32, "pericia": "Furtividade", "valor": 45}
```

## Demo

```
python demo.py
```
