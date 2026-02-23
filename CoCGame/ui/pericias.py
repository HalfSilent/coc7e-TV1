# ======================================
#   🎯 Call of Cthulhu 7e - Perícias
#        Lista completa (CoC 7e)
# ======================================

# Cada perícia tem:
#   - nome       : nome exibido na ficha
#   - base_fixa  : valor base padrão do CoC 7e
#   - grupo      : categoria para organização na UI
#   - base_attr  : (opcional) atributo que define a base dinamicamente
#                  ex: "destreza" faz base = DES // 2

PERICIAS_DISPONIVEIS = [
    # ── Combate ──────────────────────────────────────────────
    {"nome": "Lutar (Soco)",         "base_fixa": 25, "grupo": "Combate"},
    {"nome": "Arremessar",           "base_fixa": 20, "grupo": "Combate"},
    {"nome": "Armas de Fogo (Pistola)", "base_fixa": 20, "grupo": "Combate"},
    {"nome": "Armas de Fogo (Rifle)", "base_fixa": 25, "grupo": "Combate"},
    {"nome": "Armas de Fogo (Espingarda)", "base_fixa": 25, "grupo": "Combate"},
    {"nome": "Armas Brancas",        "base_fixa": 20, "grupo": "Combate"},
    {"nome": "Esquivar",             "base_fixa": 0,  "grupo": "Combate",
     "base_attr": "destreza"},  # base = DES // 2, calculado dinamicamente

    # ── Investigação ─────────────────────────────────────────
    {"nome": "Biblioteconomia",      "base_fixa": 20, "grupo": "Investigação"},
    {"nome": "Detectar",             "base_fixa": 25, "grupo": "Investigação"},
    {"nome": "Fotografia",           "base_fixa": 10, "grupo": "Investigação"},
    {"nome": "Rastrear",             "base_fixa": 10, "grupo": "Investigação"},
    {"nome": "Navegação",            "base_fixa": 10, "grupo": "Investigação"},
    {"nome": "Ouvir",                "base_fixa": 20, "grupo": "Investigação"},

    # ── Social ───────────────────────────────────────────────
    {"nome": "Charme",               "base_fixa": 15, "grupo": "Social"},
    {"nome": "Intimidação",          "base_fixa": 15, "grupo": "Social"},
    {"nome": "Lábia",                "base_fixa": 5,  "grupo": "Social"},
    {"nome": "Persuasão",            "base_fixa": 10, "grupo": "Social"},
    {"nome": "Psicologia",           "base_fixa": 10, "grupo": "Social"},

    # ── Acadêmico ────────────────────────────────────────────
    {"nome": "Antropologia",         "base_fixa": 1,  "grupo": "Acadêmico"},
    {"nome": "Arqueologia",          "base_fixa": 1,  "grupo": "Acadêmico"},
    {"nome": "Ciências Naturais",    "base_fixa": 10, "grupo": "Acadêmico"},
    {"nome": "História",             "base_fixa": 5,  "grupo": "Acadêmico"},
    {"nome": "Medicina",             "base_fixa": 1,  "grupo": "Acadêmico"},
    {"nome": "Ocultismo",            "base_fixa": 5,  "grupo": "Acadêmico"},
    {"nome": "Direito",              "base_fixa": 5,  "grupo": "Acadêmico"},

    # ── Técnico ──────────────────────────────────────────────
    {"nome": "Primeiros Socorros",   "base_fixa": 30, "grupo": "Técnico"},
    {"nome": "Dirigir Automóvel",    "base_fixa": 20, "grupo": "Técnico"},
    {"nome": "Eletricidade",         "base_fixa": 10, "grupo": "Técnico"},
    {"nome": "Mecânica",             "base_fixa": 10, "grupo": "Técnico"},
    {"nome": "Escalar",              "base_fixa": 20, "grupo": "Técnico"},
    {"nome": "Nadar",                "base_fixa": 20, "grupo": "Técnico"},
    {"nome": "Saltar",               "base_fixa": 20, "grupo": "Técnico"},
    {"nome": "Furtividade",          "base_fixa": 20, "grupo": "Técnico"},
    {"nome": "Disfarce",             "base_fixa": 5,  "grupo": "Técnico"},

    # ── Idiomas ──────────────────────────────────────────────
    {"nome": "Idioma Próprio",       "base_fixa": 0,  "grupo": "Idiomas",
     "base_attr": "educacao"},  # base = EDU
    {"nome": "Inglês",               "base_fixa": 1,  "grupo": "Idiomas"},
    {"nome": "Francês",              "base_fixa": 1,  "grupo": "Idiomas"},
    {"nome": "Latim",                "base_fixa": 1,  "grupo": "Idiomas"},
    {"nome": "Árabe",                "base_fixa": 1,  "grupo": "Idiomas"},
]


def calcular_pontos_pericias(educacao, inteligencia):
    """Calcula pontos de perícia disponíveis (CoC 7e).

    Ocupacionais = EDU × 4
    Pessoais     = INT × 2
    """
    return educacao * 4 + inteligencia * 2


def base_efetiva(pericia, caracteristicas):
    """Retorna a base efetiva de uma perícia, considerando base_attr."""
    if pericia.get("base_attr"):
        attr = pericia["base_attr"]
        val  = caracteristicas.get(attr, 0)
        if attr == "educacao":
            return val        # Idioma Próprio = EDU
        return val // 2       # Esquivar = DES/2
    return pericia.get("base_fixa", 0)


def grupos_pericias():
    """Retorna a lista ordenada de grupos únicos."""
    vistos = []
    for p in PERICIAS_DISPONIVEIS:
        g = p.get("grupo", "Geral")
        if g not in vistos:
            vistos.append(g)
    return vistos