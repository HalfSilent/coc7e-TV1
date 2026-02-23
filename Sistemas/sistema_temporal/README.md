# sistema_temporal

Controla a passagem do tempo in-game: hora, dia, período do dia, fase da lua e clima.

## Períodos

| Período | Horas |
|---|---|
| Madrugada | 00:00 – 05:59 |
| Manhã | 06:00 – 11:59 |
| Tarde | 12:00 – 17:59 |
| Noite | 18:00 – 23:59 |

## Uso

```python
from sistema_temporal import SistemaTemporal

st = SistemaTemporal("temporal.db", hora_inicial=8)
print(st.hora, st.periodo)   # 8, "manha"
st.avancar(minutos=90)
print(st.hora, st.minuto)    # 9, 30
```

## Demo

```
python demo.py
```
