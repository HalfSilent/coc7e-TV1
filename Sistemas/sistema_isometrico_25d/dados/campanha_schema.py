"""
dados/campanha_schema.py — Bridge entre o motor CoC e o sistema_campanha standalone.

Re-exporta todas as dataclasses do sistema_campanha.
Use este módulo dentro do motor de jogo em vez de importar diretamente
de Sistemas/ (que pode estar fora do sys.path).
"""
from __future__ import annotations

import sys
import os

# Garante que Sistemas/sistema_campanha esteja no path
_SISTEMA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "Sistemas", "sistema_campanha")
)
if _SISTEMA_DIR not in sys.path:
    sys.path.insert(0, _SISTEMA_DIR)

from sistema_campanha import (           # noqa: F401, E402
    VERSAO_SCHEMA,
    Stats,
    ItemInventario,
    TipoPersonagem,
    TipoIA,
    Personagem,
    EfeitoMapa,
    ObjetoMapa,
    Trigger,
    Conexao,
    DadosMapa,
    EscolhaDialogo,
    NoDialogo,
    Dialogo,
    Campanha,
)

__all__ = [
    "VERSAO_SCHEMA",
    "Stats", "ItemInventario",
    "TipoPersonagem", "TipoIA", "Personagem",
    "EfeitoMapa", "ObjetoMapa", "Trigger", "Conexao", "DadosMapa",
    "EscolhaDialogo", "NoDialogo", "Dialogo",
    "Campanha",
]
