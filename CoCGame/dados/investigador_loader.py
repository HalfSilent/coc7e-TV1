"""
dados/investigador_loader.py — Ponte entre investigador.json e o motor do jogo.

Funções:
    carregar_jogador(path)  → (Jogador, pericias_dict)
    salvar_estado(jogador, estado, path)  → grava HP/SAN de volta no JSON

Uso típico:
    from dados.investigador_loader import carregar_jogador, salvar_estado

    jogador, pericias = carregar_jogador()
    # ... jogo roda ...
    salvar_estado(jogador, estado)   # persiste HP/SAN no final
"""
from __future__ import annotations

import json
import os
from typing import Optional

# Caminho padrão: CoCGame/investigador.json (um nível acima de dados/)
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_PADRAO = os.path.join(_RAIZ, "investigador.json")


def ficha_existe(path: str = CAMINHO_PADRAO) -> bool:
    """Retorna True se há uma ficha salva."""
    return os.path.isfile(path)


def carregar_ficha_raw(path: str = CAMINHO_PADRAO) -> Optional[dict]:
    """Lê o JSON bruto. Retorna None em caso de erro."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[investigador_loader] Erro ao ler '{path}': {e}")
        return None


def carregar_jogador(path: str = CAMINHO_PADRAO):
    """
    Carrega investigador.json e retorna (Jogador, pericias_dict).

    Se o arquivo não existir ou estiver corrompido, retorna um
    Jogador com stats padrão e um dicionário de perícias vazio.
    """
    from engine.entidade import Jogador  # import tardio para evitar ciclo

    ficha = carregar_ficha_raw(path)

    if ficha is None:
        # Fallback — investigador sem ficha
        jogador = Jogador(nome="Investigador", col=1, linha=1,
                          hp=12, sanidade=70, destreza=65)
        jogador.pericias = {}
        return jogador, {}

    dp = ficha.get("dados_pessoais", {})
    c  = ficha.get("caracteristicas", {})
    p  = ficha.get("pericias", {})

    # — Valores derivados presentes no JSON —
    pv_max  = c.get("pv_max",  _calcular_pv(c))
    san_ini = c.get("sanidade", c.get("poder", 50))

    jogador = Jogador(
        nome         = dp.get("nome", "Investigador"),
        col          = 1.0,
        linha        = 1.0,
        hp           = pv_max,
        sanidade     = san_ini,
        forca        = c.get("forca",        55),
        tamanho      = c.get("tamanho",      60),
        destreza     = c.get("destreza",     65),
        constituicao = c.get("constituicao", 60),
    )

    # Atributos extras não presentes no construtor base
    jogador.pericias     = dict(p)               # cópia das perícias totais
    jogador.aparencia    = c.get("aparencia",   50)
    jogador.poder        = c.get("poder",       50)
    jogador.inteligencia = c.get("inteligencia",80)
    jogador.educacao     = c.get("educacao",    80)
    jogador.sorte        = c.get("sorte",       50)
    jogador.pm           = c.get("pm",          10)
    jogador.mov          = c.get("mov",          7)
    jogador.bonus_dano_str = c.get("bonus_dano", "0")
    jogador.ocupacao     = dp.get("ocupacao",  "")
    jogador.hp_max       = pv_max  # garante sincronismo

    return jogador, dict(p)


def _calcular_pv(c: dict) -> int:
    """PV = (CON + TAM) // 10  (regra CoC 7e)."""
    return (c.get("constituicao", 60) + c.get("tamanho", 60)) // 10


def salvar_estado(jogador, estado=None, path: str = CAMINHO_PADRAO):
    """
    Persiste HP e Sanidade atuais de volta no JSON.

    Se 'estado' (EstadoInvestigador) for fornecido, também atualiza
    dinheiro, hora e arma_equipada no JSON.
    """
    ficha = carregar_ficha_raw(path)
    if ficha is None:
        print("[investigador_loader] Nada para salvar — arquivo inexistente.")
        return

    # Atualiza stats vivos
    c = ficha.setdefault("caracteristicas", {})
    c["sanidade"] = jogador.sanidade
    c["pv_max"]   = jogador.hp  # salva HP atual (não max, para continuar onde parou)

    if estado is not None:
        ficha.setdefault("campanha", {})
        ficha["campanha"]["dinheiro"]       = getattr(estado, "dinheiro",      15)
        ficha["campanha"]["hora"]           = getattr(estado, "hora",          10)
        ficha["campanha"]["dia"]            = getattr(estado, "dia",            1)
        ficha["campanha"]["arma_equipada"]  = getattr(estado, "arma_equipada", "")
        ficha["campanha"]["inventario"]     = getattr(estado, "inventario",    [])
        ficha["campanha"]["local_id"]       = getattr(estado, "local_id",      "rua_central")

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ficha, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[investigador_loader] Erro ao salvar '{path}': {e}")


def carregar_estado_campanha(path: str = CAMINHO_PADRAO) -> dict:
    """
    Lê seção 'campanha' do JSON para restaurar hora/dia/inventário/arma/local.
    Retorna dict vazio se não existir.
    """
    ficha = carregar_ficha_raw(path)
    if ficha is None:
        return {}
    return ficha.get("campanha", {})
