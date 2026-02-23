# Sistemas — Call of Cthulhu TTRPG Engine

Cada pasta contém um sistema isolado do motor do jogo com um demo rodável
independentemente. Útil para consulta, testes e reutilização em outros projetos.

## Sistemas disponíveis

| Sistema | O que faz | Como testar |
|---|---|---|
| `sistema_chunks` | Gera e salva chunks do mapa em `.npy` | `python demo.py` |
| `sistema_temporal` | Controla dia/noite, hora, lua e período | `python demo.py` |
| `sistema_pericia` | Testes de perícia CoC 7e (Regular/Difícil/Extremo) | `python demo.py` |
| `gerenciador_mundos` | Cria, lista e acessa mundos por campanha | `python demo.py` |
| `sistema_campanha` | Schema JSON de campanhas: mapas, personagens, diálogos, triggers | `python demo.py` |

## Dependências

```
pip install numpy tinydb
```

## Jogo completo

O jogo completo está em `../CoCGame/`.
Para rodar: `python ../CoCGame/main.py`
