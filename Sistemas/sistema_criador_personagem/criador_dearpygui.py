"""
Call of Cthulhu 7e - Criador de Investigador
Interface construída com DearPyGui 2.x
"""

import random
import json
import os
import sys
import dearpygui.dearpygui as dpg

# ── Importa lógica do projeto ──────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from dados import (
    rolar_3d6x5, rolar_2d6_mais6_x5,
    calcular_pontos_vida, calcular_pontos_magia,
    calcular_taxa_movimento, calcular_corpo_a_corpo,
    calcular_idade,
)
from pericias import PERICIAS_DISPONIVEIS, calcular_pontos_pericias


# ══════════════════════════════════════════════════════════════
# CONSTANTES DE LAYOUT
# ══════════════════════════════════════════════════════════════

LARGURA  = 980
ALTURA   = 720
TITULO   = "Call of Cthulhu 7e -- Investigador"

# Paleta de cores (RGBA)
C_FUNDO      = (26,  26,  46,  255)
C_PAINEL     = (22,  33,  62,  255)
C_DESTAQUE   = (15,  52,  96,  255)
C_ACENTO     = (233, 69,  96,  255)
C_TEXTO      = (238, 226, 220, 255)
C_DIM        = (154, 140, 152, 255)
C_OURO       = (212, 168, 67,  255)
C_VERDE      = (78,  204, 163, 255)
C_ROXO       = (107, 45,  139, 255)
C_VERMELHO   = (200, 50,  50,  255)
C_AMARELO    = (230, 200, 60,  255)
C_BRANCO     = (255, 255, 255, 255)

# ══════════════════════════════════════════════════════════════
# ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════

_estado = {
    "carac": {},           # valores das características roladas
    "pericias": {},        # {nome: valor_investido}
    "pontos_totais": 0,
    "pontos_gastos": 0,
    "log_linhas": [],
}

# Modo campanha: ativado pelo argumento --para-campanha
# (setado em main() e usado em _aba_investigador)
_MODO_CAMPANHA: bool = False

# IDs DPG — características
CARAC_LISTA = [
    ("FOR", "forca",        "3d6 x 5"),
    ("CON", "constituicao", "3d6 x 5"),
    ("APA", "aparencia",    "3d6 x 5"),
    ("DES", "destreza",     "3d6 x 5"),
    ("TAM", "tamanho",      "(2d6+6) x 5"),
    ("INT", "inteligencia", "(2d6+6) x 5"),
    ("POD", "poder",        "3d6 x 5"),
    ("EDU", "educacao",     "(2d6+6) x 5"),
    ("SOR", "sorte",        "3d6 x 5"),
]

# Agrupa as pericias por grupo (usa campo "grupo" se existir, senão "Geral")
def _grupos_pericias():
    grupos = {}
    for p in PERICIAS_DISPONIVEIS:
        g = p.get("grupo", "Geral")
        grupos.setdefault(g, []).append(p)
    return grupos


# ══════════════════════════════════════════════════════════════
# HELPERS DE LOG
# ══════════════════════════════════════════════════════════════

def _log_add(texto, cor=C_DIM):
    _estado["log_linhas"].append((texto, cor))
    if dpg.does_item_exist("log_child"):
        _atualizar_log_widget()


def _atualizar_log_widget():
    dpg.delete_item("log_child", children_only=True)
    for txt, cor in _estado["log_linhas"]:
        dpg.add_text(txt, color=cor, parent="log_child")


# ══════════════════════════════════════════════════════════════
# CALLBACKS — CARACTERÍSTICAS
# ══════════════════════════════════════════════════════════════

def cb_rolar(sender, app_data):
    _estado["log_linhas"].clear()
    _log_add("=" * 55, C_OURO)
    _log_add("  >> ROLANDO CARACTERISTICAS", C_OURO)
    _log_add("=" * 55, C_OURO)

    # 3d6 × 5
    for abrev, chave, _ in CARAC_LISTA:
        if chave in ("tamanho", "inteligencia", "educacao"):
            continue
        valor, dados = rolar_3d6x5()
        _estado["carac"][chave] = valor
        dpg.set_value(f"val_{chave}", str(valor))
        dpg.set_value(f"met_{chave}", str(valor // 2))
        dpg.set_value(f"qui_{chave}", str(valor // 5) if chave != "sorte" else "-")
        dpg.configure_item(f"val_{chave}", color=C_VERDE)
        _log_add(f"  {abrev:>3} : {str(dados):<22} = {sum(dados)} x5 = {valor}", C_TEXTO)

    # (2d6+6) × 5
    for abrev, chave, _ in CARAC_LISTA:
        if chave not in ("tamanho", "inteligencia", "educacao"):
            continue
        valor, dados = rolar_2d6_mais6_x5()
        _estado["carac"][chave] = valor
        dpg.set_value(f"val_{chave}", str(valor))
        dpg.set_value(f"met_{chave}", str(valor // 2))
        dpg.set_value(f"qui_{chave}", str(valor // 5))
        dpg.configure_item(f"val_{chave}", color=C_VERDE)
        soma = sum(dados)
        _log_add(
            f"  {abrev:>3} : {str(dados):<16} = {soma}+6={soma+6} x5 = {valor}",
            C_TEXTO,
        )

    # Sanidade = POD
    san = _estado["carac"].get("poder", 0)
    _estado["carac"]["sanidade"] = san
    _log_add(f"\n  [SAN] Sanidade = POD = {san}", C_VERDE)

    _atualizar_derivados()
    _atualizar_pontos()

    _log_add("", C_DIM)
    _log_add(
        f"  [*] Pontos de pericia: {_estado['pontos_totais']}",
        C_OURO,
    )


def _atualizar_derivados():
    c = _estado["carac"]
    if not c:
        return

    pv  = calcular_pontos_vida(c.get("tamanho", 0), c.get("constituicao", 0))
    pm  = calcular_pontos_magia(c.get("poder", 0))
    mov = calcular_taxa_movimento(c.get("forca", 0), c.get("destreza", 0), c.get("tamanho", 0))
    bd, cac = calcular_corpo_a_corpo(c.get("forca", 0), c.get("tamanho", 0))
    san = c.get("sanidade", c.get("poder", 0))

    _estado["carac"].update({"pv_max": pv, "pm": pm, "mov": mov,
                              "bonus_dano": bd, "corpo_a_corpo": cac})

    dpg.set_value("der_pv",   str(pv))
    dpg.set_value("der_pm",   str(pm))
    dpg.set_value("der_san",  str(san))
    dpg.set_value("der_mov",  str(mov))
    dpg.set_value("der_bd",   bd)
    dpg.set_value("der_cac",  cac)

    # Atualizar base dinâmica da Esquivar = DES / 2
    des = c.get("destreza", 0)
    for p in PERICIAS_DISPONIVEIS:
        if p.get("base_attr") == "destreza" and dpg.does_item_exist(f"spn_{p['nome']}"):
            nova_base = des // 2
            dpg.set_value(f"base_{p['nome']}", str(nova_base))
            _recalc_pericia(p["nome"], nova_base)


def _atualizar_pontos():
    c = _estado["carac"]
    if not c:
        return
    _estado["pontos_totais"] = calcular_pontos_pericias(
        c.get("educacao", 0), c.get("inteligencia", 0)
    )
    _recalc_pontos_gastos()


def _recalc_pontos_gastos():
    total = 0
    for p in PERICIAS_DISPONIVEIS:
        tag = f"spn_{p['nome']}"
        if dpg.does_item_exist(tag):
            total += max(0, int(dpg.get_value(tag)))
    _estado["pontos_gastos"] = total
    restantes = _estado["pontos_totais"] - total

    if _estado["pontos_totais"] == 0:
        dpg.set_value("label_pontos", "- (role as caracteristicas primeiro)")
        dpg.configure_item("label_pontos", color=C_OURO)
    elif restantes < 0:
        dpg.set_value("label_pontos", f"{restantes}  [!] EXCEDIDO!")
        dpg.configure_item("label_pontos", color=C_ACENTO)
    elif restantes == 0:
        dpg.set_value("label_pontos", "0  [OK] todos distribuidos")
        dpg.configure_item("label_pontos", color=C_VERDE)
    else:
        dpg.set_value(
            "label_pontos",
            f"{restantes} de {_estado['pontos_totais']} disponiveis",
        )
        dpg.configure_item("label_pontos", color=C_OURO)


def _recalc_pericia(nome, base_override=None):
    tag_spn  = f"spn_{nome}"
    tag_tot  = f"tot_{nome}"
    tag_met  = f"pmet_{nome}"
    tag_qui  = f"pqui_{nome}"
    tag_base = f"base_{nome}"

    if not dpg.does_item_exist(tag_spn):
        return

    investido = max(0, int(dpg.get_value(tag_spn)))
    if base_override is not None:
        base = base_override
    else:
        try:
            base = int(dpg.get_value(tag_base))
        except Exception:
            base = next(
                (p["base_fixa"] for p in PERICIAS_DISPONIVEIS if p["nome"] == nome), 0
            )

    total = base + investido
    total = min(total, 99)

    dpg.set_value(tag_tot, str(total))
    dpg.set_value(tag_met, str(total // 2))
    dpg.set_value(tag_qui, str(total // 5))
    _recalc_pontos_gastos()


def cb_pericia_changed(sender, app_data, user_data):
    _recalc_pericia(user_data)


def cb_testar_pericia(sender, app_data, user_data):
    nome = user_data
    if not _estado["carac"]:
        _log_add("  [!] Role as caracteristicas primeiro!", C_ACENTO)
        dpg.set_value("tab_bar", "tab_log")
        return

    tag_base = f"base_{nome}"
    tag_spn  = f"spn_{nome}"
    try:
        base     = int(dpg.get_value(tag_base))
        investido = max(0, int(dpg.get_value(tag_spn)))
    except Exception:
        return

    total   = base + investido
    metade  = total // 2
    quinto  = total // 5
    rolagem = random.randint(1, 100)
    fumble_lim = 96 if total < 50 else 100

    if rolagem == 1 or rolagem <= quinto:
        resultado, cor = "ACERTO EXTREMO", C_OURO
    elif rolagem <= metade:
        resultado, cor = "Acerto Dificil", C_VERDE
    elif rolagem <= total:
        resultado, cor = "Sucesso",        C_TEXTO
    elif rolagem >= fumble_lim:
        resultado, cor = "FUMBLE",         C_VERMELHO
    else:
        resultado, cor = "Falha",          C_DIM

    _log_add(
        f"  [d] [{nome}]  {rolagem:02d} vs {total}  "
        f"(1/2:{metade} 1/5:{quinto})  ->  {resultado}",
        cor,
    )
    dpg.set_value("tab_bar", "tab_log")


# ══════════════════════════════════════════════════════════════
# CALLBACKS — DADOS PESSOAIS
# ══════════════════════════════════════════════════════════════

def cb_nascimento_changed(sender, app_data):
    texto = dpg.get_value("inp_nascimento").strip()
    if len(texto) == 10:
        try:
            idade = calcular_idade(texto)
            dpg.set_value("lbl_idade", f"{idade} anos")
            dpg.configure_item("lbl_idade", color=C_VERDE)
        except Exception as e:
            dpg.set_value("lbl_idade", str(e)[:30])
            dpg.configure_item("lbl_idade", color=C_ACENTO)
    else:
        dpg.set_value("lbl_idade", "-")
        dpg.configure_item("lbl_idade", color=C_DIM)


# ══════════════════════════════════════════════════════════════
# CALLBACKS — SALVAR / CARREGAR
# ══════════════════════════════════════════════════════════════

def cb_salvar(sender, app_data):
    if not _estado["carac"]:
        _log_add("  [!] Role as caracteristicas antes de salvar!", C_ACENTO)
        dpg.set_value("tab_bar", "tab_log")
        return
    dpg.show_item("dlg_salvar")


def cb_salvar_rapido(sender, app_data):
    """Salva como investigador.json na mesma pasta — usado pelo combate.py."""
    if not _estado["carac"]:
        _log_add("  [!] Role as caracteristicas antes de salvar!", C_ACENTO)
        dpg.set_value("tab_bar", "tab_log")
        return

    base    = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(base, "investigador.json")

    pericias_out = {}
    for p in PERICIAS_DISPONIVEIS:
        tag = f"spn_{p['nome']}"
        if dpg.does_item_exist(tag):
            pericias_out[p["nome"]] = max(0, int(dpg.get_value(tag)))

    ficha = {
        "dados_pessoais": {
            "nome":       dpg.get_value("inp_nome"),
            "ocupacao":   dpg.get_value("inp_ocupacao"),
            "nascimento": dpg.get_value("inp_nascimento"),
            "residencia": dpg.get_value("inp_residencia"),
            "idade":      dpg.get_value("lbl_idade"),
        },
        "caracteristicas": _estado["carac"],
        "pericias": pericias_out,
    }

    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(ficha, f, ensure_ascii=False, indent=2)
        _log_add(f"  [OK] Ficha salva -> investigador.json", C_VERDE)
        _log_add(f"       {caminho}", C_DIM)
        _log_add("  [*] Combate carregara esta ficha automaticamente!", C_OURO)
        dpg.configure_item("btn_salvar_rapido", label=" Ficha Salva! ")
        dpg.set_value("tab_bar", "tab_log")
    except Exception as e:
        _log_add(f"  [ERR] Erro ao salvar: {e}", C_ACENTO)
        dpg.set_value("tab_bar", "tab_log")


def cb_salvar_confirm(sender, app_data):
    caminho = app_data["file_path_name"]
    if not caminho:
        return
    if not caminho.endswith(".json"):
        caminho += ".json"

    pericias_out = {}
    for p in PERICIAS_DISPONIVEIS:
        tag = f"spn_{p['nome']}"
        if dpg.does_item_exist(tag):
            pericias_out[p["nome"]] = max(0, int(dpg.get_value(tag)))

    ficha = {
        "dados_pessoais": {
            "nome":       dpg.get_value("inp_nome"),
            "ocupacao":   dpg.get_value("inp_ocupacao"),
            "nascimento": dpg.get_value("inp_nascimento"),
            "residencia": dpg.get_value("inp_residencia"),
            "idade":      dpg.get_value("lbl_idade"),
        },
        "caracteristicas": _estado["carac"],
        "pericias": pericias_out,
    }

    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(ficha, f, ensure_ascii=False, indent=2)
        _log_add(f"  [OK] Ficha salva -> {caminho}", C_VERDE)
    except Exception as e:
        _log_add(f"  [ERR] Erro ao salvar: {e}", C_ACENTO)
    dpg.set_value("tab_bar", "tab_log")


def cb_iniciar_campanha(sender, app_data):
    """Salva ficha na campanha e lança intro_campanha.py."""
    if not _estado["carac"]:
        _log_add("  [!] Role as caracteristicas antes de iniciar!", C_ACENTO)
        dpg.set_value("tab_bar", "tab_log")
        return

    pericias_out = {}
    for p in PERICIAS_DISPONIVEIS:
        tag = f"spn_{p['nome']}"
        if dpg.does_item_exist(tag):
            pericias_out[p["nome"]] = max(0, int(dpg.get_value(tag)))

    ficha = {
        "dados_pessoais": {
            "nome":       dpg.get_value("inp_nome"),
            "ocupacao":   dpg.get_value("inp_ocupacao"),
            "nascimento": dpg.get_value("inp_nascimento"),
            "residencia": dpg.get_value("inp_residencia"),
            "idade":      dpg.get_value("lbl_idade"),
        },
        "caracteristicas": _estado["carac"],
        "pericias": pericias_out,
    }

    _base = os.path.dirname(os.path.abspath(__file__))
    _raiz = os.path.dirname(_base)
    _camp = os.path.join(_raiz, "Modulos de Campanha", "Degraus para o abismo")

    # Salva investigador.json (para combate.py)
    try:
        with open(os.path.join(_base, "investigador.json"), "w",
                  encoding="utf-8") as f:
            json.dump(ficha, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log_add(f"  [ERR] Nao foi possivel salvar investigador.json: {e}", C_ACENTO)
        return

    # Salva na campanha (TinyDB) para o mundo aberto carregar
    try:
        from tinydb import TinyDB, Query as TQ
        _db = TinyDB(os.path.join(_camp, "campanha.json"))
        _Q  = TQ()
        _db.upsert(
            {"slot": "investigador", "ficha": ficha},
            _Q.slot == "investigador",
        )
        _db.close()
    except Exception as e:
        _log_add(f"  [AVISO] Nao salvou na campanha: {e}", C_OURO)

    _intro = os.path.join(_camp, "intro_campanha.py")
    import subprocess, sys
    subprocess.Popen([sys.executable, _intro])
    dpg.destroy_context()
    sys.exit()


def cb_carregar(sender, app_data):
    dpg.show_item("dlg_carregar")


def cb_carregar_confirm(sender, app_data):
    caminho = app_data["file_path_name"]
    if not caminho or not os.path.isfile(caminho):
        return

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            ficha = json.load(f)
    except Exception as e:
        _log_add(f"  [ERR] Arquivo invalido: {e}", C_ACENTO)
        return

    cb_limpar(None, None)

    dp = ficha.get("dados_pessoais", {})
    dpg.set_value("inp_nome",       dp.get("nome", ""))
    dpg.set_value("inp_ocupacao",   dp.get("ocupacao", ""))
    dpg.set_value("inp_nascimento", dp.get("nascimento", ""))
    dpg.set_value("inp_residencia", dp.get("residencia", ""))
    dpg.set_value("lbl_idade",      dp.get("idade", "-"))

    _estado["carac"] = ficha.get("caracteristicas", {})
    c = _estado["carac"]

    for _, chave, _ in CARAC_LISTA:
        if chave in c:
            v = c[chave]
            dpg.set_value(f"val_{chave}", str(v))
            dpg.set_value(f"met_{chave}", str(v // 2))
            if chave == "sorte":
                dpg.set_value(f"qui_{chave}", "-")
            else:
                dpg.set_value(f"qui_{chave}", str(v // 5))
            dpg.configure_item(f"val_{chave}", color=C_VERDE)

    _atualizar_derivados()

    for nome, inv in ficha.get("pericias", {}).items():
        tag = f"spn_{nome}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, inv)
            _recalc_pericia(nome)

    _atualizar_pontos()
    _log_add(f"  [OK] Ficha carregada -> {caminho}", C_VERDE)
    dpg.set_value("tab_bar", "tab_investigador")


def cb_limpar(sender, app_data):
    for campo in ("inp_nome", "inp_ocupacao", "inp_nascimento", "inp_residencia"):
        if dpg.does_item_exist(campo):
            dpg.set_value(campo, "")
    dpg.set_value("lbl_idade", "-")
    dpg.configure_item("lbl_idade", color=C_DIM)

    for _, chave, _ in CARAC_LISTA:
        for tag in (f"val_{chave}", f"met_{chave}", f"qui_{chave}"):
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, "-")
                dpg.configure_item(tag, color=C_DIM)

    for der in ("der_pv", "der_pm", "der_san", "der_mov", "der_bd", "der_cac"):
        if dpg.does_item_exist(der):
            dpg.set_value(der, "-")

    for p in PERICIAS_DISPONIVEIS:
        tag = f"spn_{p['nome']}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, 0)
            _recalc_pericia(p["nome"])

    _estado["carac"].clear()
    _estado["pontos_totais"] = 0
    _estado["pontos_gastos"] = 0
    dpg.set_value("label_pontos", "- (role as caracteristicas primeiro)")
    dpg.configure_item("label_pontos", color=C_OURO)

    _estado["log_linhas"].clear()
    if dpg.does_item_exist("log_child"):
        dpg.delete_item("log_child", children_only=True)


# ══════════════════════════════════════════════════════════════
# CONSTRUÇÃO DA INTERFACE
# ══════════════════════════════════════════════════════════════

def _aplicar_tema():
    with dpg.theme() as tema_global:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,      C_FUNDO)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,       C_PAINEL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,       (35, 45, 75, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,(50, 65, 100, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (60, 80, 120, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_ACENTO)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  (180, 50, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C_TEXTO)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,       C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, C_ROXO)
            dpg.add_theme_color(dpg.mvThemeCol_Tab,           C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,    C_ROXO)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,     C_ROXO)
            dpg.add_theme_color(dpg.mvThemeCol_Header,        C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, C_ROXO)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,  C_ACENTO)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,   C_FUNDO)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_Border,        C_DESTAQUE)
            dpg.add_theme_color(dpg.mvThemeCol_Separator,     C_DESTAQUE)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,   4)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,     4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,    6, 4)
    dpg.bind_theme(tema_global)


def _aba_investigador():
    """Aba 1 - Dados pessoais + Características + Derivados."""
    with dpg.tab(label="  Investigador  ", tag="tab_investigador"):

        # ── Dados pessoais ───────────────────────────────────
        dpg.add_text("DADOS DO INVESTIGADOR", color=C_OURO)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("Nome:", color=C_DIM)
                dpg.add_input_text(
                    tag="inp_nome", width=240,
                    hint="Ex: Henry Armitage",
                )
            dpg.add_spacer(width=16)
            with dpg.group():
                dpg.add_text("Ocupação:", color=C_DIM)
                dpg.add_input_text(
                    tag="inp_ocupacao", width=220,
                    hint="Ex: Professor, Detetive...",
                )
            dpg.add_spacer(width=16)
            with dpg.group():
                dpg.add_text("Residência:", color=C_DIM)
                dpg.add_input_text(
                    tag="inp_residencia", width=200,
                    hint="Ex: Arkham, MA",
                )

        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("Data de Nascimento:", color=C_DIM)
                dpg.add_input_text(
                    tag="inp_nascimento", width=130,
                    hint="DD/MM/AAAA",
                    callback=cb_nascimento_changed,
                )
            dpg.add_spacer(width=20)
            with dpg.group():
                dpg.add_text("Idade (calculada):", color=C_DIM)
                dpg.add_text("-", tag="lbl_idade", color=C_DIM)

        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=6)

        # ── Características ──────────────────────────────────
        dpg.add_text("CARACTERÍSTICAS", color=C_OURO)
        dpg.add_spacer(height=4)

        with dpg.table(
            tag="tab_carac",
            header_row=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            row_background=True,
            resizable=False,
            width=-1,
        ):
            dpg.add_table_column(label="Característica", width_fixed=True, init_width_or_weight=170)
            dpg.add_table_column(label="Fórmula",        width_fixed=True, init_width_or_weight=110)
            dpg.add_table_column(label="Valor",          width_fixed=True, init_width_or_weight=70)
            dpg.add_table_column(label="Metade",         width_fixed=True, init_width_or_weight=70)
            dpg.add_table_column(label="Quinto",         width_fixed=True, init_width_or_weight=70)

            nomes_completos = {
                "forca":        "FOR - Força",
                "constituicao": "CON - Constituição",
                "aparencia":    "APA - Aparência",
                "destreza":     "DES - Destreza",
                "tamanho":      "TAM - Tamanho",
                "inteligencia": "INT - Inteligência",
                "poder":        "POD - Poder",
                "educacao":     "EDU - Educação",
                "sorte":        "SOR - Sorte",
            }

            for abrev, chave, formula in CARAC_LISTA:
                with dpg.table_row():
                    dpg.add_text(nomes_completos[chave], color=C_TEXTO)
                    dpg.add_text(formula, color=C_DIM)
                    dpg.add_text("-", tag=f"val_{chave}", color=C_DIM)
                    dpg.add_text("-", tag=f"met_{chave}", color=C_DIM)
                    dpg.add_text("-", tag=f"qui_{chave}", color=C_DIM)

        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=6)

        # ── Atributos derivados ──────────────────────────────
        dpg.add_text("ATRIBUTOS DERIVADOS", color=C_OURO)
        dpg.add_spacer(height=6)

        with dpg.group(horizontal=True):
            _derivado("PV",    "der_pv")
            dpg.add_spacer(width=16)
            _derivado("PM",    "der_pm")
            dpg.add_spacer(width=16)
            _derivado("SAN",   "der_san")
            dpg.add_spacer(width=16)
            _derivado("MOV",   "der_mov")
            dpg.add_spacer(width=16)
            _derivado("B.Dano", "der_bd")
            dpg.add_spacer(width=16)
            _derivado("C.a.C.", "der_cac")

        dpg.add_spacer(height=14)

        # ── Botões de ação ───────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_button(
                label=" Rolar ", callback=cb_rolar,
                width=110, height=34,
            )
            dpg.add_spacer(width=8)
            dpg.add_button(
                label=" Limpar ", callback=cb_limpar,
                width=110, height=34,
            )
            dpg.add_spacer(width=8)
            dpg.add_button(
                label=" Salvar Como... ", callback=cb_salvar,
                width=140, height=34,
            )
            dpg.add_spacer(width=8)
            dpg.add_button(
                label=" Carregar ", callback=cb_carregar,
                width=120, height=34,
            )

        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            dpg.add_button(
                tag="btn_salvar_rapido",
                label=" Salvar Ficha (investigador.json) ",
                callback=cb_salvar_rapido,
                width=280, height=34,
            )
            dpg.add_spacer(width=12)
            dpg.add_text(
                "[Salva direto para o Combate carregar]",
                color=C_DIM,
            )

        # ── Botão de campanha (só em modo --para-campanha) ──
        if _MODO_CAMPANHA:
            dpg.add_spacer(height=14)
            dpg.add_separator()
            dpg.add_spacer(height=10)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    tag="btn_iniciar_campanha",
                    label=" ▶  Salvar Ficha e Iniciar Degraus para o Abismo ",
                    callback=cb_iniciar_campanha,
                    width=430, height=42,
                )
                dpg.add_spacer(width=14)
                dpg.add_text(
                    "Rio de Janeiro, 1923  —  a investigação começa agora!",
                    color=C_OURO,
                )


def _derivado(rotulo, tag):
    with dpg.group():
        dpg.add_text(rotulo, color=C_DIM)
        dpg.add_text("-", tag=tag, color=C_ACENTO)


def _aba_pericias():
    """Aba 2 - Perícias organizadas por grupo."""
    with dpg.tab(label="  Pericias  ", tag="tab_pericias"):

        # Barra de pontos disponíveis
        with dpg.group(horizontal=True):
            dpg.add_text("Pontos:", color=C_DIM)
            dpg.add_spacer(width=6)
            dpg.add_text(
                "- (role as caracteristicas primeiro)",
                tag="label_pontos",
                color=C_OURO,
            )

        dpg.add_separator()
        dpg.add_spacer(height=4)

        grupos = _grupos_pericias()

        with dpg.tab_bar():
            for grupo, pericias in grupos.items():
                with dpg.tab(label=f"  {grupo}  "):
                    with dpg.child_window(border=False, height=-1):
                        # Cabeçalho
                        with dpg.table(
                            header_row=True,
                            borders_innerH=True, borders_outerH=True,
                            borders_innerV=True, borders_outerV=True,
                            row_background=True,
                            resizable=False,
                            width=-1,
                        ):
                            dpg.add_table_column(label="Perícia",   width_fixed=True, init_width_or_weight=200)
                            dpg.add_table_column(label="Base",      width_fixed=True, init_width_or_weight=55)
                            dpg.add_table_column(label="Investido", width_fixed=True, init_width_or_weight=90)
                            dpg.add_table_column(label="Total",     width_fixed=True, init_width_or_weight=60)
                            dpg.add_table_column(label="Metade",    width_fixed=True, init_width_or_weight=60)
                            dpg.add_table_column(label="Quinto",    width_fixed=True, init_width_or_weight=60)
                            dpg.add_table_column(label="",          width_fixed=True, init_width_or_weight=44)

                            for p in pericias:
                                nome = p["nome"]
                                base = p.get("base_fixa", 0)

                                with dpg.table_row():
                                    dpg.add_text(nome, color=C_TEXTO)
                                    dpg.add_text(str(base), tag=f"base_{nome}", color=C_DIM)
                                    dpg.add_input_int(
                                        tag=f"spn_{nome}",
                                        default_value=0,
                                        min_value=0, max_value=99,
                                        min_clamped=True, max_clamped=True,
                                        width=80,
                                        callback=cb_pericia_changed,
                                        user_data=nome,
                                        step=1,
                                    )
                                    dpg.add_text(str(base), tag=f"tot_{nome}", color=C_VERDE)
                                    dpg.add_text(str(base // 2), tag=f"pmet_{nome}", color=C_DIM)
                                    dpg.add_text(str(base // 5), tag=f"pqui_{nome}", color=C_DIM)
                                    dpg.add_button(
                                        label="[d]",
                                        width=38,
                                        callback=cb_testar_pericia,
                                        user_data=nome,
                                    )


def _aba_log():
    """Aba 3 - Log de rolagens."""
    with dpg.tab(label="  Log  ", tag="tab_log"):
        dpg.add_text("Histórico de rolagens", color=C_DIM)
        dpg.add_separator()
        dpg.add_spacer(height=4)
        with dpg.child_window(tag="log_child", border=True, height=-1, autosize_x=True):
            pass


def _dialogs():
    """Diálogos de arquivo."""
    with dpg.file_dialog(
        tag="dlg_salvar",
        directory_selector=False,
        show=False,
        width=620, height=420,
        default_filename="investigador",
        callback=cb_salvar_confirm,
    ):
        dpg.add_file_extension(".json", color=C_VERDE)
        dpg.add_file_extension(".*")

    with dpg.file_dialog(
        tag="dlg_carregar",
        directory_selector=False,
        show=False,
        width=620, height=420,
        callback=cb_carregar_confirm,
    ):
        dpg.add_file_extension(".json", color=C_VERDE)
        dpg.add_file_extension(".*")


# ══════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════

def _carregar_fonte():
    """Carrega fonte monoespaçada; busca caminhos comuns em Fedora/Ubuntu/Arch.
    Cria o font_registry SOMENTE se encontrar um arquivo válido — um registry
    vazio causa segfault no DearPyGui 2.x.
    """
    candidatos = [
        # Fedora / Nobara / RHEL
        "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
        "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf",
        "/usr/share/fonts/adwaita-mono-fonts/AdwaitaMono-Regular.ttf",
        # Ubuntu / Debian
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        # Arch
        "/usr/share/fonts/TTF/LiberationMono-Regular.ttf",
    ]
    caminho = next((c for c in candidatos if os.path.isfile(c)), None)
    if caminho is None:
        return   # sem fonte encontrada — NÃO cria registry vazio
    with dpg.font_registry():
        dpg.bind_font(dpg.add_font(caminho, 14))


def main():
    global _MODO_CAMPANHA
    import argparse
    _ap = argparse.ArgumentParser(add_help=False)
    _ap.add_argument("--para-campanha", action="store_true")
    _args, _ = _ap.parse_known_args()
    _MODO_CAMPANHA = _args.para_campanha

    dpg.create_context()
    _aplicar_tema()

    dpg.create_viewport(
        title=TITULO,
        width=LARGURA, height=ALTURA,
        min_width=800, min_height=600,
        resizable=True,
    )
    dpg.setup_dearpygui()

    _carregar_fonte()

    with dpg.window(
        tag="janela_principal",
        label=TITULO,
        no_title_bar=True,
        no_move=True,
        no_resize=True,
        no_scrollbar=True,
        no_close=True,
    ):
        dpg.add_text(
            "CALL OF CTHULHU 7e  --  Criador de Investigador",
            color=C_ACENTO,
        )
        dpg.add_separator()
        dpg.add_spacer(height=6)

        with dpg.tab_bar(tag="tab_bar"):
            _aba_investigador()
            _aba_pericias()
            _aba_log()

    _dialogs()

    dpg.set_primary_window("janela_principal", True)
    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
