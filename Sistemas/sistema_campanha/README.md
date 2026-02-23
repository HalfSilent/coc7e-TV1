# Sistema de Campanha — CoC 7e

Módulo standalone para criar, editar e serializar campanhas completas do
Chamado de Cthulhu 7ª Edição. Independente de pygame — pode ser importado
pelo motor de jogo, pelo editor gráfico ou por scripts externos.

```
python demo.py
```

---

## Estrutura em disco

```
<pasta_campanha>/
    campanha.json           ← metadados + lista de IDs
    personagens.json        ← dict id → Personagem
    dialogos.json           ← dict id → Dialogo
    mapas/
        mapa_01.json        ← um arquivo por DadosMapa
        mapa_02.json
        …
```

---

## API principal

### `Campanha`

| Método / Atributo | Descrição |
|---|---|
| `Campanha.nova(nome, autor)` | Cria campanha vazia com mapa e jogador padrões |
| `c.salvar(pasta)` | Serializa todos os dados em JSON |
| `Campanha.carregar(pasta)` | Carrega campanha de pasta existente |
| `c.validar()` | Retorna `List[str]` com avisos de inconsistência |
| `c.novo_mapa(nome, w, h)` | Cria e registra `DadosMapa` |
| `c.novo_personagem(nome, tipo)` | Cria e registra `Personagem` |
| `c.novo_dialogo(titulo)` | Cria e registra `Dialogo` |
| `c.mapas` | `Dict[str, DadosMapa]` |
| `c.personagens` | `Dict[str, Personagem]` |
| `c.dialogos` | `Dict[str, Dialogo]` |

---

### `DadosMapa`

| Campo | Tipo | Descrição |
|---|---|---|
| `tiles` | `List[List[int]]` | 0=vazio 1=chão 2=parede 3=elevado |
| `efeitos` | `List[EfeitoMapa]` | efeitos ambientais posicionados |
| `objetos` | `List[ObjetoMapa]` | objetos interativos |
| `triggers` | `List[Trigger]` | eventos e zonas |
| `conexoes` | `List[Conexao]` | transições entre mapas |
| `personagens_spawn` | `List[str]` | IDs dos personagens que aparecem aqui |

`mapa.redimensionar(nova_w, nova_h)` — preserva tiles existentes.

---

### `Personagem`

| Campo | Valores possíveis |
|---|---|
| `tipo` | `investigador` · `npc_aliado` · `cultista` · `engendro` · `neutro` |
| `ia` | `nenhuma` · `agressivo` · `patrulha` · `reativo` · `fuga` |
| `sprite_id` | 0–7 (pele Male Kenney) |
| `stats` | `Stats(hp, san, forca, destreza, inteligencia, constituicao, …)` |

---

### `Trigger`

| Campo | Exemplos |
|---|---|
| `tipo` | `"zona"` · `"dialogo_inicio"` · `"combate"` · `"transicao"` · `"item_coletado"` |
| `condicao` | `"sempre"` · `"evento:cultista_morto"` · `"flag:ritual_sabido"` |
| `acao` | `"dialogo:d_01"` · `"mapa:mapa_02:5:3"` · `"san:-3"` · `"evento:nome"` |

---

### `Dialogo` / `NoDialogo` / `EscolhaDialogo`

```python
dial = c.novo_dialogo("Título")
no   = NoDialogo(id="n1", personagem_id="cultista_01",
                 texto="...", efeito="san:-2",
                 escolhas=[EscolhaDialogo("Resposta A", proximo="n2"),
                            EscolhaDialogo("Sair",       proximo=None)])
dial.adicionar_no(no)
```

---

## Exemplo rápido

```python
from sistema_campanha import Campanha, Personagem, TipoPersonagem, TipoIA

c = Campanha.nova("Minha Campanha", autor="Keeper")
p = c.novo_personagem("Cultista Misterioso", TipoPersonagem.CULTISTA)
p.ia = TipoIA.REATIVO
c.salvar("/tmp/minha_campanha")

c2 = Campanha.carregar("/tmp/minha_campanha")
print(c2.validar())  # []
```
