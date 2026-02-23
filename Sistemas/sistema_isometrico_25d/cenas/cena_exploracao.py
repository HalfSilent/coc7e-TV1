"""
cenas/cena_exploracao.py — Loop principal do jogo.

Estados:
    EXPLORANDO  — Jogador move livremente com WASD/setas.
                  Inimigo dentro do raio de detecção → transição para COMBATE.
    COMBATE     — Turnos por AP no mesmo mapa isométrico.
                  Clique no mapa confirma alvo; botões na barra inferior
                  selecionam ação.

Pode ser lançado diretamente (python cenas/cena_exploracao.py) ou
chamado pelo menu_pygame.py via subprocess.
"""
from __future__ import annotations

import math
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "x11"

# Garante que imports relativos ao projeto funcionem
_RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import pygame
import gerenciador_assets as _ga

from engine.mundo      import Mundo, EfeitoAmbiental, TipoTile
from engine.entidade   import Jogador, Inimigo, Engendro, direcao_de_delta
from engine.renderer   import Renderer, grid_para_tela, tela_para_grid, TILE_W, TILE_H
from engine.combate.gerenciador import (
    GerenciadorCombate, EstadoCombate, TipoAcao
)
from ui.hud_combate import HudCombate

# ── Resolução ──────────────────────────────────────────────────────────
LARGURA, ALTURA = 1280, 720
FPS = 60

# ── Mapa de teste (sala da mansão) ─────────────────────────────────────
# 0=vazio, 1=chão, 2=parede, 3=elevado (half-wall / cobertura)
MAPA = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 3, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 3, 3, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

# Efeitos ambientais pré-colocados
_EFEITOS_INICIAIS = [
    (5,  4, EfeitoAmbiental.OLEO,    99),
    (6,  4, EfeitoAmbiental.OLEO,    99),
    (7,  4, EfeitoAmbiental.OLEO,    99),
    (4,  7, EfeitoAmbiental.ARBUSTO, 99),
    (5,  7, EfeitoAmbiental.ARBUSTO, 99),
    (8,  6, EfeitoAmbiental.NEVOA,   99),
    (8,  7, EfeitoAmbiental.NEVOA,   99),
    (9,  7, EfeitoAmbiental.NEVOA,   99),
]


def _distancia_manhattan(a, b) -> float:
    return abs(a.col - b.col) + abs(a.linha - b.linha)


# ══════════════════════════════════════════════════════════════
# HELPERS DE TRIGGERS E DIÁLOGOS
# ══════════════════════════════════════════════════════════════

def _trigger_condicao_ok(condicao: str, flags: set) -> bool:
    """Retorna True se a condição do trigger está satisfeita."""
    if condicao == "sempre":
        return True
    if condicao.startswith("flag:"):
        return condicao.split(":", 1)[1] in flags
    return True  # condição desconhecida → permitir


def _executar_acao_trigger(acao: str, jogador, inimigos, gerenciador,
                           dialogos: dict, flags: set, on_log) -> object:
    """
    Executa a ação de um trigger.
    Retorna (Dialogo, no_id) se abrir diálogo, None caso contrário.
    """
    if not acao:
        return None
    partes    = acao.split(":", 1)
    tipo_acao = partes[0]
    resto     = partes[1] if len(partes) > 1 else ""

    if tipo_acao == "san":
        try:
            delta = int(resto)
            if delta < 0:
                jogador.perder_sanidade(-delta)
            else:
                jogador.sanidade = min(jogador.san_max, jogador.sanidade + delta)
            on_log(f"😰 Sanidade: {delta:+d}  (atual: {jogador.sanidade})")
        except ValueError:
            pass

    elif tipo_acao == "flag":
        flags.add(resto)
        on_log(f"🏴 Flag ativada: {resto}")

    elif tipo_acao == "dialogo":
        dial = dialogos.get(resto)
        if dial and dial.no_inicial:
            return (dial, dial.no_inicial)
        on_log(f"[Trigger] Diálogo '{resto}' não encontrado.")

    elif tipo_acao == "combate":
        inimigos_vivos = [i for i in inimigos if i.vivo]
        if inimigos_vivos and not gerenciador.em_combate:
            on_log("⚔ Emboscada!")
            gerenciador.iniciar_combate(jogador, inimigos_vivos)

    elif tipo_acao == "evento":
        on_log(f"📌 Evento: {resto}")

    elif tipo_acao == "mapa":
        # formato: "mapa:<mapa_id>:<col>:<linha>"
        partes_mapa = resto.split(":")
        if len(partes_mapa) >= 3:
            try:
                return {
                    "__transicao__": True,
                    "mapa_id": partes_mapa[0],
                    "col":     float(partes_mapa[1]),
                    "linha":   float(partes_mapa[2]),
                }
            except (ValueError, IndexError):
                on_log(f"[Trigger] Formato de mapa inválido: {acao}")

    return None


def _aplicar_efeito_no(efeito: str, jogador, flags: set, on_log) -> None:
    """Aplica o efeito de um nó de diálogo ao estado do jogador."""
    if not efeito:
        return
    partes = efeito.split(":", 1)
    tipo   = partes[0]
    resto  = partes[1] if len(partes) > 1 else ""

    if tipo == "san":
        try:
            delta = int(resto)
            if delta < 0:
                jogador.perder_sanidade(-delta)
            else:
                jogador.sanidade = min(jogador.san_max, jogador.sanidade + delta)
            on_log(f"😰 San (diálogo): {delta:+d}  ({jogador.sanidade})")
        except ValueError:
            pass
    elif tipo == "flag":
        flags.add(resto)
    elif tipo == "item":
        on_log(f"🎒 Item recebido: {resto}")


def _tratar_input_dialogo(tecla: int, dialogo_ativo: tuple,
                          jogador, flags: set, on_log) -> object:
    """
    Processa tecla durante diálogo.
    Retorna (dialogo, no_id) ou None (diálogo fechou).
    """
    dialogo, no_id = dialogo_ativo
    no = dialogo.nos.get(no_id)
    if no is None:
        return None

    if not no.escolhas:
        if tecla in (pygame.K_RETURN, pygame.K_SPACE,
                     pygame.K_KP_ENTER, pygame.K_1):
            _aplicar_efeito_no(no.efeito, jogador, flags, on_log)
            return None
    else:
        for i, esc in enumerate(no.escolhas[:9]):
            if tecla == pygame.K_1 + i:
                _aplicar_efeito_no(no.efeito, jogador, flags, on_log)
                return (dialogo, esc.proximo) if esc.proximo else None

    return dialogo_ativo  # sem mudança


def _desenhar_texto_quebrado(tela, texto: str, fonte, cor,
                             x: int, y: int, larg_max: int) -> int:
    """Renderiza texto quebrando em palavras. Retorna y final."""
    palavras    = texto.split()
    linha_atual = ""
    ly          = y
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if fonte.size(teste)[0] <= larg_max:
            linha_atual = teste
        else:
            if linha_atual:
                s = fonte.render(linha_atual, True, cor)
                tela.blit(s, (x, ly))
                ly += s.get_height() + 2
            linha_atual = palavra
    if linha_atual:
        s = fonte.render(linha_atual, True, cor)
        tela.blit(s, (x, ly))
        ly += s.get_height() + 2
    return ly


def _desenhar_dialogo(tela, dialogo_ativo: tuple, personagens: dict,
                      fn_hud, fn_small) -> None:
    """Desenha overlay de diálogo no canto inferior da tela."""
    dialogo, no_id = dialogo_ativo
    no = dialogo.nos.get(no_id)
    if no is None:
        return

    larg, alt = tela.get_size()
    painel_h  = 200
    painel_x  = 20
    painel_y  = alt - painel_h - 10
    painel_w  = larg - 40

    bg = pygame.Surface((painel_w, painel_h), pygame.SRCALPHA)
    bg.fill((15, 12, 30, 220))
    pygame.draw.rect(bg, (80, 60, 120), bg.get_rect(), width=2, border_radius=8)
    tela.blit(bg, (painel_x, painel_y))

    x = painel_x + 16
    y = painel_y + 12

    pers         = personagens.get(no.personagem_id)
    nome_display = pers.nome if pers else (no.personagem_id or "???")
    s_nome       = fn_hud.render(f"[ {nome_display} ]", True, (212, 168, 67))
    tela.blit(s_nome, (x, y))
    y += s_nome.get_height() + 6

    _desenhar_texto_quebrado(tela, no.texto, fn_small, (220, 210, 195),
                             x, y, painel_w - 32)

    sep_y = painel_y + painel_h - 75
    pygame.draw.line(tela, (60, 50, 90),
                     (x, sep_y), (painel_x + painel_w - 16, sep_y), 1)

    esc_y = sep_y + 6
    if not no.escolhas:
        s = fn_small.render("[ENTER/ESPAÇO] Continuar", True, (100, 180, 120))
        tela.blit(s, (x, esc_y))
    else:
        for i, esc in enumerate(no.escolhas[:6]):
            col_off = (i % 2) * (painel_w // 2)
            row_off = (i // 2) * 22
            s = fn_small.render(f"[{i + 1}] {esc.texto}", True, (160, 200, 255))
            tela.blit(s, (x + col_off, esc_y + row_off))


def main(
    spawn_col: float = 2.0,
    spawn_linha: float = 2.0,
    inimigos_externos=None,    # List[Entidade] pré-construídas ou None
    triggers_runtime=None,     # List[Trigger] da campanha ou None
    dialogos_runtime=None,     # Dict[str, Dialogo] ou None
    personagens_runtime=None,  # Dict[str, Personagem] ou None
):
    pygame.init()
    pygame.display.set_caption("Call of Cthulhu 7e — Exploração")
    tela  = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # ── Assets ────────────────────────────────────────────────
    _ga.garantir_fontes(verbose=False)
    fn_hud   = _ga.get_font("hud",    13)
    fn_small = _ga.get_font("hud",    11)

    # ── Mundo e entidades ─────────────────────────────────────
    mundo   = Mundo(MAPA)
    for col, linha, efeito, dur in _EFEITOS_INICIAIS:
        cel = mundo.celula(col, linha)
        if cel:
            cel.aplicar_efeito(efeito, dur)

    jogador  = Jogador(col=spawn_col, linha=spawn_linha)
    if inimigos_externos is not None:
        inimigos = list(inimigos_externos)
    else:
        inimigos = [
            Inimigo(nome="Cultista",   col=10.0, linha=9.0),
            Inimigo(nome="Cultista 2", col=11.0, linha=5.0, skin_id=2),
            Engendro(nome="Engendro",  col=12.0, linha=8.0),
        ]
    todas_entidades = [jogador] + inimigos

    # Marca ocupantes no grid
    for ent in todas_entidades:
        cel = mundo.celula(int(ent.col), int(ent.linha))
        if cel:
            cel.ocupante = ent

    # ── Renderer e HUD ────────────────────────────────────────
    renderer = Renderer(tela, LARGURA, ALTURA)
    hud      = HudCombate(tela, LARGURA, ALTURA, gerenciador_assets=_ga)

    # ── Gerenciador de combate ────────────────────────────────
    def on_log(msg: str):
        hud.adicionar_log(msg)
        print(f"[CoC] {msg}")

    gerenciador = GerenciadorCombate(mundo, on_log=on_log)

    # ── Estado de runtime da campanha ──────────────────────────
    _triggers_rt: list = list(triggers_runtime)  if triggers_runtime  else []
    _dialogos_rt: dict = dict(dialogos_runtime)  if dialogos_runtime  else {}
    _pers_rt:     dict = dict(personagens_runtime) if personagens_runtime else {}
    _flags:      set   = set()    # flags ativadas por triggers/diálogos
    _disparados: set   = set()    # IDs de triggers já disparados
    dialogo_ativo      = None     # (Dialogo, no_id) ou None
    _transicao_pendente = None    # dict com dados de transição de mapa, ou None

    # ── Velocidade de exploração ──────────────────────────────
    VEL = 0.06

    # ── Cores para highlights ─────────────────────────────────
    COR_HL_MOVER  = (80,  180, 255, 80)
    COR_HL_ATACAR = (255,  80,  80, 80)

    # ══════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════
    while True:
        dt = clock.tick(FPS)

        # ── Eventos ───────────────────────────────────────────
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ── Diálogo ativo: intercepta todo o input ────────
            if dialogo_ativo is not None:
                if e.type == pygame.KEYDOWN:
                    dialogo_ativo = _tratar_input_dialogo(
                        e.key, dialogo_ativo, jogador, _flags, on_log)
                continue

            if e.type == pygame.KEYDOWN:
                # Sai para o menu
                if e.key == pygame.K_ESCAPE:
                    if gerenciador.estado == EstadoCombate.ESCOLHENDO_ALVO:
                        gerenciador.cancelar_acao()
                    else:
                        _voltar_menu()

                # Combate: passar turno
                if (e.key == pygame.K_SPACE
                        and gerenciador.estado == EstadoCombate.TURNO_JOGADOR):
                    gerenciador.proximo_turno()

                # Combate: atalhos de teclado para ações
                if gerenciador.estado == EstadoCombate.TURNO_JOGADOR:
                    from engine.combate.gerenciador import ACOES_PADRAO
                    atalhos = {
                        pygame.K_m: TipoAcao.MOVER,
                        pygame.K_a: TipoAcao.ATACAR,
                        pygame.K_r: TipoAcao.RECARREGAR,
                        pygame.K_u: TipoAcao.USAR_ITEM,
                        pygame.K_w: TipoAcao.ESPERAR,
                    }
                    tipo = atalhos.get(e.key)
                    if tipo:
                        acao = next((ac for ac in ACOES_PADRAO
                                     if ac.tipo == tipo), None)
                        if acao:
                            gerenciador.selecionar_acao(acao)

            # Clique do mouse
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos

                # Verificar botões do HUD primeiro
                acao_clicada = hud.checar_clique((mx, my))
                if acao_clicada and gerenciador.estado in (
                    EstadoCombate.TURNO_JOGADOR, EstadoCombate.ESCOLHENDO_ALVO
                ):
                    gerenciador.selecionar_acao(acao_clicada)

                # Confirmar alvo no mapa
                elif gerenciador.estado == EstadoCombate.ESCOLHENDO_ALVO:
                    col_c, lin_c = tela_para_grid(
                        mx - renderer.offset_x,
                        my - renderer.offset_y,
                        renderer.cam_x, renderer.cam_y
                    )
                    gerenciador.confirmar_alvo(col_c, lin_c)

        # ── Exploração: movimento livre ────────────────────────
        if not gerenciador.em_combate and dialogo_ativo is None:
            teclas = pygame.key.get_pressed()
            dc, dl = 0.0, 0.0

            if teclas[pygame.K_UP]    or teclas[pygame.K_KP8]: dl -= VEL; dc -= VEL
            if teclas[pygame.K_DOWN]  or teclas[pygame.K_KP2]: dl += VEL; dc += VEL
            if teclas[pygame.K_LEFT]  or teclas[pygame.K_KP4]: dl += VEL; dc -= VEL
            if teclas[pygame.K_RIGHT] or teclas[pygame.K_KP6]: dl -= VEL; dc += VEL

            # Movimento diagonal isométrico com WASD (notação BG)
            if teclas[pygame.K_w]: dl -= VEL; dc -= VEL
            if teclas[pygame.K_s]: dl += VEL; dc += VEL
            if teclas[pygame.K_a]: dl += VEL; dc -= VEL
            if teclas[pygame.K_d]: dl -= VEL; dc += VEL

            if dc != 0 or dl != 0:
                nc = jogador.col + dc
                nl = jogador.linha + dl
                cel = mundo.celula(int(nc), int(nl))
                if cel and not cel.bloqueada:
                    # Libera célula anterior
                    cel_ant = mundo.celula(int(jogador.col), int(jogador.linha))
                    if cel_ant and cel_ant.ocupante is jogador:
                        cel_ant.ocupante = None

                    jogador.col   = nc
                    jogador.linha = nl
                    cel_nova = mundo.celula(int(nc), int(nl))
                    if cel_nova:
                        cel_nova.ocupante = jogador

                    jogador.direcao = direcao_de_delta(dc, dl)
                    jogador.movendo = True
                    jogador.atualizar_animacao(dt)
                else:
                    jogador.movendo = False
            else:
                jogador.movendo = False

            # Detecta inimigos próximos → inicia combate
            inimigos_vivos = [i for i in inimigos if i.vivo]
            for ini in inimigos_vivos:
                if _distancia_manhattan(jogador, ini) <= ini.ia_raio:
                    ini.ia_alerta = True
                    on_log(f"⚠ {ini.nome} avistou o investigador!")
                    gerenciador.iniciar_combate(jogador, inimigos_vivos)
                    break

            # Verifica triggers de zona da campanha
            if _triggers_rt:
                pos_jog = (int(jogador.col), int(jogador.linha))
                for trig in _triggers_rt:
                    if trig.id in _disparados:
                        continue
                    if not _trigger_condicao_ok(trig.condicao, _flags):
                        continue
                    if trig.tipo == "zona":
                        area = {(int(p[0]), int(p[1])) for p in trig.area}
                        if pos_jog not in area:
                            continue
                    _disparados.add(trig.id)
                    resultado = _executar_acao_trigger(
                        trig.acao, jogador, inimigos, gerenciador,
                        _dialogos_rt, _flags, on_log)
                    if resultado is not None:
                        if isinstance(resultado, dict) and resultado.get("__transicao__"):
                            _transicao_pendente = resultado
                        else:
                            dialogo_ativo = resultado
                    break  # uma trigger por frame

        # ── Combate: IA age automaticamente ───────────────────
        # (já tratado dentro de proximo_turno() no gerenciador)

        # ── Câmera suave ──────────────────────────────────────
        renderer.seguir_entidade(jogador, suavidade=0.09)

        # ══════════════════════════════════════════════════════
        # RENDER
        # ══════════════════════════════════════════════════════
        tela.fill((10, 8, 18))

        # 1. Mapa base (painter's algorithm interno)
        renderer.renderizar_mapa(mundo)

        # 2. Efeitos ambientais (overlay colorido)
        renderer.renderizar_efeitos(mundo)

        # 3. Highlights de alcance / alvo
        if gerenciador.celulas_highlight:
            acao = gerenciador.acao_selecionada
            cor  = (COR_HL_ATACAR if acao and acao.tipo == TipoAcao.ATACAR
                    else COR_HL_MOVER)
            renderer.renderizar_highlights(gerenciador.celulas_highlight, cor)

        # 4. Entidades ordenadas por profundidade (col+linha crescente)
        vivas = [e for e in todas_entidades if e.vivo]
        vivas.sort(key=lambda e: e.col + e.linha)
        for ent in vivas:
            renderer.renderizar_entidade(ent)
            renderer.renderizar_barra_status(ent)

        # 5. HUD de combate
        hud.desenhar(gerenciador)

        # 6. HUD de exploração (HP/SAN mínimo)
        if not gerenciador.em_combate:
            hud.desenhar_status_exploracao(jogador, fn_hud)

        # 7. Indicador de modo (canto superior esquerdo)
        _desenhar_indicador_modo(tela, gerenciador, fn_hud)

        # 8. Tela de fim de combate
        if gerenciador.estado == EstadoCombate.FIM_COMBATE:
            _desenhar_fim_combate(tela, gerenciador, fn_hud)

        # 9. Overlay de diálogo ativo
        if dialogo_ativo is not None:
            _desenhar_dialogo(tela, dialogo_ativo, _pers_rt, fn_hud, fn_small)

        # 10. Transição de mapa pendente → fade para preto e retorna
        if _transicao_pendente is not None:
            fade = pygame.Surface(tela.get_size())
            fade.fill((0, 0, 0))
            for _a in range(0, 256, 25):
                fade.set_alpha(_a)
                tela.blit(fade, (0, 0))
                pygame.display.flip()
                clock.tick(60)
            return _transicao_pendente

        pygame.display.flip()


# ══════════════════════════════════════════════════════════════
# HELPERS DE RENDER
# ══════════════════════════════════════════════════════════════

def _desenhar_indicador_modo(tela, gerenciador, fn):
    if gerenciador.em_combate:
        msg = "⚔ COMBATE  |  M=Mover  A=Atacar  W=Esperar  ESPAÇO=Próximo"
        cor = (220, 80, 80)
    else:
        msg = "EXPLORAÇÃO  |  WASD = mover  (aproxime-se de inimigos)"
        cor = (78, 204, 163)
    surf = fn.render(msg, True, cor)
    bg   = pygame.Surface((surf.get_width() + 16, surf.get_height() + 6), pygame.SRCALPHA)
    bg.fill((10, 8, 18, 170))
    tela.blit(bg,   (8, 8))
    tela.blit(surf, (16, 11))


def _desenhar_fim_combate(tela, gerenciador, fn):
    overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    tela.blit(overlay, (0, 0))

    larg, alt = tela.get_size()
    inimigos_vivos = [p for p in gerenciador.participantes[1:] if p.vivo]
    if inimigos_vivos:
        txt = "O Investigador foi derrotado..."
        cor = (220, 80, 80)
    else:
        txt = "Inimigos derrotados! Continue a investigação."
        cor = (78, 204, 163)

    s = fn.render(txt, True, cor)
    tela.blit(s, (larg // 2 - s.get_width() // 2, alt // 2 - 20))
    dica = fn.render("[ESC] Voltar ao menu", True, (150, 140, 120))
    tela.blit(dica, (larg // 2 - dica.get_width() // 2, alt // 2 + 10))


def _voltar_menu():
    import subprocess
    _menu = os.path.join(_RAIZ, "ui", "menu_pygame.py")
    subprocess.Popen([sys.executable, _menu])
    os._exit(0)


def _rodar_mapa(campanha, mapa_id: str, spawn_col: float, spawn_linha: float):
    """
    Carrega e executa um único mapa de uma campanha.
    Retorna dict de transição ou None (saída do jogo).
    """
    from dados.campanha_schema import TipoPersonagem as _TP, TipoIA as _TIA
    from engine.mundo import EfeitoAmbiental as _EA

    dm = campanha.mapas.get(mapa_id)
    if dm is None:
        print(f"[Cena] Mapa '{mapa_id}' não encontrado, usando fallback.")
        return None

    # ── Tiles e efeitos ──────────────────────────────────────
    global MAPA, _EFEITOS_INICIAIS
    MAPA = dm.tiles
    _EFEITOS_INICIAIS = []
    for ef in dm.efeitos:
        try:
            _EFEITOS_INICIAIS.append((ef.col, ef.linha, _EA[ef.tipo], ef.duracao))
        except KeyError:
            pass

    # ── Inimigos / NPCs do mapa ──────────────────────────────
    inimigos_externos = []
    for pid in dm.personagens_spawn:
        if pid == campanha.personagem_jogador_id:
            continue
        pers = campanha.personagens.get(pid)
        if pers is None:
            continue
        if pers.tipo == _TP.ENGENDRO:
            ent = Engendro(
                nome=pers.nome,
                col=float(pers.spawn_col), linha=float(pers.spawn_linha),
                hp=pers.stats.hp, skin_id=pers.sprite_id,
            )
        else:
            ent = Inimigo(
                nome=pers.nome,
                col=float(pers.spawn_col), linha=float(pers.spawn_linha),
                hp=pers.stats.hp, skin_id=pers.sprite_id,
            )
            if pers.ia == _TIA.REATIVO:    ent.ia_raio = 2
            elif pers.ia == _TIA.PATRULHA: ent.ia_raio = 8
            else:                          ent.ia_raio = 6
        inimigos_externos.append(ent)

    return main(
        spawn_col=spawn_col,
        spawn_linha=spawn_linha,
        inimigos_externos=inimigos_externos,
        triggers_runtime=dm.triggers,
        dialogos_runtime=campanha.dialogos,
        personagens_runtime=campanha.personagens,
    )


def main_campanha(pasta_campanha: str):
    """
    Inicia a cena de exploração carregando a campanha isométrica.
    Suporta transições entre mapas via triggers do tipo 'mapa'.
    """
    if not os.path.isdir(pasta_campanha):
        print(f"[Cena] Pasta '{pasta_campanha}' não encontrada, usando fallback.")
        main()
        return

    sys.path.insert(0, _RAIZ)
    from dados.campanha_schema import Campanha

    c = Campanha.carregar(pasta_campanha)

    mapa_id     = c.mapa_inicial
    p_jog       = c.personagens.get(c.personagem_jogador_id)
    spawn_col   = float(p_jog.spawn_col)   if p_jog else 2.0
    spawn_linha = float(p_jog.spawn_linha) if p_jog else 2.0

    while True:
        transicao = _rodar_mapa(c, mapa_id, spawn_col, spawn_linha)
        if not isinstance(transicao, dict) or not transicao.get("__transicao__"):
            break
        mapa_id     = transicao["mapa_id"]
        spawn_col   = float(transicao.get("col",   2.0))
        spawn_linha = float(transicao.get("linha", 2.0))
        if mapa_id not in c.mapas:
            print(f"[Cena] Mapa '{mapa_id}' não existe na campanha.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_campanha(sys.argv[1])
    else:
        main()
