# sistema_isometrico_25d — Arquivo

Engine isométrica 2.5D completa construída para CoC 7e (fevereiro/2026).
Arquivada em 22/02/2026 ao mudar para arquitetura top-down 2D + TORN.

## Conteúdo

| Pasta | O que contém |
|-------|-------------|
| `engine/renderer.py` | Renderizador isométrico Kenney, câmera lerp, paredes direcionais |
| `engine/mundo.py` | Grid isométrico com efeitos ambientais (óleo, fogo, névoa…) |
| `engine/entidade.py` | Jogador, Inimigo, Engendro com stats CoC |
| `engine/combate/gerenciador.py` | State machine de combate por turnos com AP |
| `cenas/cena_exploracao.py` | Loop principal — exploração + combate + triggers + diálogos |
| `editor/` | Editor visual de campanhas (4 abas: mapa, personagem, diálogo, trigger) |
| `ui/hud_combate.py` | HUD de combate com log, botões de ação, barras de status |
| `dados/campanha_schema.py` | Bridge para sistema_campanha standalone |

## Dependências externas

- `Assets/kenney_isometric-miniature-dungeon/` — tiles e sprites
- `Sistemas/sistema_campanha/` — schema de campanha JSON
- `gerenciador_assets.py` — fontes e assets do projeto

## Para restaurar

Copiar o conteúdo desta pasta de volta para `CoCGame/` e recriar as
entradas no `menu_pygame.py` apontando para `cenas/cena_exploracao.py`.
