# sistema_criador_personagem

**`criador_dearpygui.py`** — Criador de investigador CoC 7e com interface DearPyGui 2.x.

Ferramenta standalone completa com:
- Rolagem manual de atributos (3d6×5 / 2d6+6×5)
- Alocação de pontos de perícia por ocupação
- Salva `investigador.json` compatível com CoCGame

## Uso
```bash
pip install dearpygui
python criador_dearpygui.py
# ou com integração de campanha:
python criador_dearpygui.py --para-campanha
```

## Nota de arquivamento
Arquivado em 23/02/2026. O CoCGame usa agora `ui/tela_criar_personagem.py`
(pygame nativo) para a criação inline durante o fluxo do jogo.
O DearPyGui ainda é usado pelo sistema de campanhas legacy em `Campanhas/`.
