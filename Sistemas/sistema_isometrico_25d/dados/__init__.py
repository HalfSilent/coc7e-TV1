"""
dados/__init__.py — Pacote de dados estruturados para o motor CoC.
Re-exporta o sistema_campanha para uso direto no motor de jogo.
"""
from dados.campanha_schema import (  # noqa: F401
    Campanha, DadosMapa, Personagem, Dialogo, NoDialogo, EscolhaDialogo,
    Trigger, EfeitoMapa, ObjetoMapa, Conexao,
    TipoPersonagem, TipoIA, Stats, ItemInventario,
    VERSAO_SCHEMA,
)
