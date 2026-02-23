"""
dialogo_inline.py — Caixa de diálogo NPC renderizada sobre o mapa.

Não sai da tela do mundo. O mapa fica visível e escurecido ao fundo.

Uso em mundo_aberto.py:
    dlg = DialogoInline(
        tela, "botequim_benedito",
        twee_path, variaveis, npc_nome="Seu Benedito",
    )
    resultado, vars_novas, san_delta = dlg.rodar()

    resultado:
        "fechar"           → diálogo encerrado normalmente
        "combate:<nome>"   → NPC escalou para combate
        "cena:<passagem>"  → cena cinemática completa (lança narrativa.py)
"""
from __future__ import annotations

import math
import os
import sys
from typing import Optional

import pygame

# ── Caminhos ──────────────────────────────────────────────────
_DIR    = os.path.dirname(os.path.abspath(__file__))
_RAIZ   = os.path.normpath(os.path.join(_DIR, "..", ".."))
_GITHUB = os.path.join(_RAIZ, ".github")
sys.path.insert(0, _GITHUB)

from twee_parser import TweeParser, AvaliadorCondicoes

# ── Constantes visuais ────────────────────────────────────────
PANEL_H   = 255     # altura do painel no fundo da tela
MARGEM    = 20      # margem horizontal interna
CHARS_S   = 38      # caracteres por segundo (typewriter)
MAX_TEXTO = 6       # máx linhas de texto visíveis

_FONTE_PATH = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf"

# ── Paleta ────────────────────────────────────────────────────
C_FUNDO   = ( 10,   8,  20, 210)   # fundo do painel (RGBA)
C_BORDA   = ( 80,  60,  30)
C_TITULO  = (212, 168,  67)         # OURO — nome do NPC
C_TEXTO   = (235, 225, 215)
C_DIM     = (140, 128, 112)
C_HOVER   = ( 40,  55, 105)
C_OPCAO   = ( 70,  55,  20)
C_OPCAO_H = (100,  80,  30)
C_ACENTO  = (233,  69,  96)
C_VERDE   = ( 78, 204, 163)
C_SAN_BAD = (200,  55,  55)

# Overlay do mapa quando diálogo está ativo
OVERLAY_ALPHA = 145


def _fonte(size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(_FONTE_PATH, size)
    except Exception:
        return pygame.font.SysFont("monospace", size)


def _quebrar(texto: str, fonte: pygame.font.Font, largura: int) -> list[str]:
    """Word-wrap de uma linha em várias."""
    if not texto.strip():
        return [""]
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if fonte.size(teste)[0] <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas or [""]


# ══════════════════════════════════════════════════════════════
#  DIALOGO INLINE
# ══════════════════════════════════════════════════════════════

class DialogoInline:
    """
    Overlay de diálogo pygame.
    Preserva o mapa ao fundo, escurecido.
    """

    def __init__(
        self,
        tela: pygame.Surface,
        passagem_inicial: str,
        twee_path: str,
        variaveis: dict,
        npc_nome: str = "",
        ficha: Optional[dict] = None,
    ):
        self.tela     = tela
        self.vars     = dict(variaveis)
        self.npc_nome = npc_nome
        self.san_delta = 0      # acumulado durante o diálogo
        self.ficha     = ficha or {}
        self._teste_pendente: Optional[dict] = None  # cmd @teste aguardando execução

        W = tela.get_width()
        H = tela.get_height()

        # ── Fontes ──────────────────────────────────────────
        self._fn_titulo  = _fonte(14)
        self._fn_texto   = _fonte(14)
        self._fn_opcao   = _fonte(13)
        self._fn_hint    = _fonte(10)

        # ── Parser twee ─────────────────────────────────────
        self._parser = TweeParser(twee_path)

        # ── Geometria do painel ─────────────────────────────
        self._W       = W
        self._H       = H
        self._panel_y = H - PANEL_H
        self._txt_w   = W - 2 * MARGEM - 16   # largura útil de texto
        self._opcao_x = MARGEM + 4
        self._opcao_w = W - 2 * MARGEM - 8

        # ── Estado da cena ──────────────────────────────────
        self._resultado: Optional[str] = None  # None = continua

        self._texto_linhas: list[str]  = []    # linhas word-wrapped da cena
        self._opcoes:       list[str]  = []    # textos das opções visíveis
        self._destinos:     list[str]  = []    # passagem alvo de cada opção
        self._reveal:       float      = 0.0   # chars revelados (typewriter)
        self._hover:        int        = -1
        self._msg:          str        = ""
        self._msg_t:        int        = 0     # ms restantes da mensagem

        # Carrega passagem inicial
        self._ir_para(passagem_inicial)

    # ── Carregamento de passagem ───────────────────────────────

    def _ir_para(self, nome: str):
        p = self._parser.obter(nome)
        if p is None:
            self._resultado = "fechar"
            return
        self._passagem_atual = p  # guarda para _passagem_atual_tags()

        # ── Aplica comandos @ ──────────────────────────────
        san_antes = int(self.vars.get("san", 10))
        for cmd in p.comandos:
            tipo = cmd["tipo"]
            if tipo == "set":
                self.vars[cmd["var"]] = cmd["valor"]
            elif tipo == "san":
                san_max = int(self.vars.get("san_max", 10))
                novo = max(0, min(san_max, san_antes + cmd["valor"]))
                self.vars["san"] = novo
                self.san_delta += (novo - san_antes)
                san_antes = novo
            elif tipo == "combate":
                # Escalada para combate
                self._resultado = f"combate:{cmd['inimigo']}"
                return
            elif tipo == "if":
                if AvaliadorCondicoes.avaliar(cmd["condicao"], self.vars):
                    self._ir_para(cmd["destino"])
                    return
            elif tipo == "teste":
                # Pausa o diálogo — o loop de rodar() executa o teste
                self._teste_pendente = cmd
                return

        # ── Verifica tags da passagem ──────────────────────
        # Passagem marcada como [narrativa] → cena completa
        if "narrativa" in p.tags and nome != getattr(self, "_passagem_inicial", nome):
            self._resultado = f"cena:{nome}"
            return

        # Passagem marcada como [combate] → combate direto
        if "combate" in p.tags:
            # extrai inimigo do texto se houver
            inimigo = next(
                (cmd["inimigo"] for cmd in p.comandos if cmd["tipo"] == "combate"),
                nome,
            )
            self._resultado = f"combate:{inimigo}"
            return

        # Passagem marcada como [fim]
        if "fim" in p.tags:
            # Mostra texto e depois fecha
            self._resultado = None  # vira "fechar" quando o user pressionar

        # ── Guarda passagem inicial ────────────────────────
        if not hasattr(self, "_passagem_inicial"):
            self._passagem_inicial = nome

        # ── Word-wrap do texto ─────────────────────────────
        linhas: list[str] = []
        for linha in p.texto:
            if linha == "":
                linhas.append("")
            else:
                linhas.extend(_quebrar(linha, self._fn_texto, self._txt_w))
        self._texto_linhas = linhas
        self._reveal       = 0.0

        # ── Opções (links) ─────────────────────────────────
        opcoes_vis, destinos_vis = [], []

        for link in p.links:
            dest_p = self._parser.obter(link.destino)
            # Links para passagens [narrativa] → escalada
            if dest_p and "narrativa" in dest_p.tags:
                opcoes_vis.append(f"► {link.texto}")
                destinos_vis.append(f"__cena:{link.destino}")
            else:
                opcoes_vis.append(link.texto)
                destinos_vis.append(link.destino)

        # Se não tem links → botão "Fechar"
        if not opcoes_vis:
            opcoes_vis.append("[ Fechar ]")
            destinos_vis.append("__fechar")

        self._opcoes   = opcoes_vis[:6]
        self._destinos = destinos_vis[:6]

    # ── Escolha ───────────────────────────────────────────────

    def _escolher(self, idx: int):
        if idx < 0 or idx >= len(self._destinos):
            return
        dest = self._destinos[idx]
        if dest == "__fechar":
            self._resultado = "fechar"
        elif dest.startswith("__cena:"):
            self._resultado = f"cena:{dest[7:]}"
        else:
            self._ir_para(dest)

    # ── Loop principal ─────────────────────────────────────────

    def rodar(self) -> tuple[str, dict, int]:
        """
        Roda o diálogo. Retorna (resultado, variaveis, san_delta).
        O caller é responsável por renderizar o mundo antes de chamar.
        """
        clock = pygame.time.Clock()
        # Captura snapshot do fundo (mundo já renderizado)
        fundo_snap = self.tela.copy()

        # Overlay de escurecimento
        overlay = pygame.Surface((self._W, self._H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, OVERLAY_ALPHA))

        # Superfície do painel
        panel = pygame.Surface((self._W, PANEL_H), pygame.SRCALPHA)

        while self._resultado is None or self._resultado == "__aguardando_enter":
            dt = clock.tick(60)
            t  = pygame.time.get_ticks()

            # ── Teste de perícia pendente ────────────────────────
            if self._teste_pendente is not None:
                self._executar_teste(fundo_snap)
                continue

            mx, my = pygame.mouse.get_pos()
            rel_y  = my - self._panel_y

            # Hover nas opções
            self._hover = -1
            total_txt_h = self._altura_texto()
            opc_y0 = total_txt_h + 46   # Y relativo dentro do painel
            for i in range(len(self._opcoes)):
                oy = opc_y0 + i * 26
                if self._opcao_x <= mx <= self._opcao_x + self._opcao_w:
                    if oy - 2 <= rel_y <= oy + 20:
                        self._hover = i
                        break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); import sys; sys.exit()

                if event.type == pygame.KEYDOWN:
                    # ESC fecha
                    if event.key == pygame.K_ESCAPE:
                        self._resultado = "fechar"
                    # ESPAÇO / ENTER → completa reveal ou escolhe única opção
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        if self._reveal < len("".join(self._texto_linhas)):
                            self._reveal = float(10_000)  # revela tudo
                        elif len(self._opcoes) == 1:
                            self._escolher(0)
                        elif "fim" in self._passagem_atual_tags():
                            self._resultado = "fechar"
                    # Teclas numéricas 1-6
                    elif pygame.K_1 <= event.key <= pygame.K_6:
                        idx = event.key - pygame.K_1
                        if self._reveal >= len("".join(self._texto_linhas)):
                            self._escolher(idx)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._hover >= 0:
                        if self._reveal >= len("".join(self._texto_linhas)):
                            self._escolher(self._hover)
                        else:
                            self._reveal = float(10_000)  # clique revela tudo

            # Typewriter
            total_chars = sum(max(1, len(l)) for l in self._texto_linhas)
            if self._reveal < total_chars:
                self._reveal += CHARS_S * dt / 1000.0

            # Mensagem temporária
            if self._msg_t > 0:
                self._msg_t -= dt

            # ── Render ──────────────────────────────────────
            # Fundo (mapa escurecido)
            self.tela.blit(fundo_snap, (0, 0))
            self.tela.blit(overlay, (0, 0))

            # Painel
            panel.fill((0, 0, 0, 0))
            self._render_painel(panel, t)
            self.tela.blit(panel, (0, self._panel_y))

            pygame.display.flip()

        resultado = self._resultado or "fechar"
        return resultado, self.vars, self.san_delta

    # ── Altura do bloco de texto ───────────────────────────────

    def _altura_texto(self) -> int:
        lh = self._fn_texto.get_linesize() + 2
        n = min(MAX_TEXTO, len(self._texto_linhas))
        return n * lh + 12

    def _executar_teste(self, fundo: pygame.Surface):
        """Executa o teste de perícia pendente e retoma o diálogo."""
        cmd = self._teste_pendente
        self._teste_pendente = None

        # Importação lazy para não depender de sistema_pericia no topo
        _raiz = os.path.normpath(os.path.join(_DIR, "..", ".."))
        if _raiz not in sys.path:
            sys.path.insert(0, _raiz)
        from sistema_pericia import PainelTeste

        pericia     = cmd["pericia"]
        dificuldade = cmd.get("dificuldade", "normal")
        dest_ok     = cmd.get("sucesso", "")
        dest_fail   = cmd.get("falha", "")

        # Valor da perícia: tenta ficha do investigador, fallback variável twee
        valor = self._valor_pericia(pericia)

        # Para teste de SAN usa o valor atual da variável twee
        eh_san = pericia.lower() == "san"
        san_at = int(self.vars.get("san", valor if eh_san else 10))

        painel = PainelTeste(
            tela          = self.tela,
            pericia       = pericia,
            valor         = san_at if eh_san else valor,
            dificuldade   = dificuldade,
            san_atual     = san_at,
            perda_sucesso = cmd.get("perda_sucesso", "1"),
            perda_falha   = cmd.get("perda_falha",   "1d6"),
        )
        res = painel.rodar(fundo)

        # Aplica resultado nas variáveis twee
        self.vars["_ultimo_teste"]     = "sucesso" if res.sucesso else "falha"
        self.vars["_ultimo_teste_grau"] = res.grau

        if res.san_delta < 0:
            self.san_delta         += res.san_delta
            self.vars["san"]        = res.san_final

        # Rota para passagem de sucesso/falha se definida no twee
        if res.sucesso and dest_ok:
            self._ir_para(dest_ok)
        elif not res.sucesso and dest_fail:
            self._ir_para(dest_fail)
        # Caso contrário o diálogo continua na passagem atual (links normais)

    def _valor_pericia(self, nome: str) -> int:
        """Busca valor da perícia na ficha do investigador."""
        from sistema_pericia import normalizar_pericia
        nome_norm = normalizar_pericia(nome)
        pericias  = self.ficha.get("pericias", {})
        if nome_norm in pericias:
            return int(pericias[nome_norm])
        # Busca case-insensitive
        nome_lower = nome_norm.lower()
        for k, v in pericias.items():
            if k.lower() == nome_lower:
                return int(v)
        # Fallback: valor base padrão de CoC (20 para investigação)
        return 20

    def _passagem_atual_tags(self) -> list[str]:
        """Tags da passagem atual (para checar [fim])."""
        p = getattr(self, "_passagem_atual", None)
        return p.tags if p is not None else []

    # ── Renderização do painel ─────────────────────────────────

    def _render_painel(self, surf: pygame.Surface, t: int):
        W = self._W

        # Fundo com gradiente simulado (rects semitransparentes)
        for i in range(3):
            a = (200 - i * 18, 160 - i * 14, 20 - i * 4, 220 - i * 20)
            pygame.draw.rect(surf, a,
                             pygame.Rect(i, i, W - 2 * i, PANEL_H - 2 * i),
                             border_radius=8)

        # Borda dourada
        pygame.draw.rect(surf, C_BORDA,
                         pygame.Rect(0, 0, W, PANEL_H), 2, border_radius=8)

        # ── Nome do NPC ────────────────────────────────────
        if self.npc_nome:
            # Fundo do cabeçalho
            pygame.draw.rect(surf, (18, 14, 4, 200),
                             pygame.Rect(0, 0, W, 28), border_radius=8)
            pygame.draw.line(surf, C_BORDA, (0, 28), (W, 28), 1)

            # Ícone pulsante
            pulso = int(180 + 75 * abs(math.sin(t * 0.003)))
            pygame.draw.circle(surf, (pulso, pulso // 3, 0), (MARGEM - 4, 14), 4)

            nome_surf = self._fn_titulo.render(
                self.npc_nome.upper(), True, C_TITULO)
            surf.blit(nome_surf, (MARGEM + 6, (28 - nome_surf.get_height()) // 2))

            # SAN indicator (se houve perda)
            if self.san_delta < 0:
                san_txt = self._fn_hint.render(
                    f"SAN {self.san_delta:+d}", True, C_SAN_BAD)
                surf.blit(san_txt, (W - san_txt.get_width() - MARGEM, 8))

        # ── Texto da cena (typewriter) ─────────────────────
        lh       = self._fn_texto.get_linesize() + 2
        start_y  = 36
        chars_v  = int(self._reveal)
        chars_c  = 0
        y        = start_y

        for linha in self._texto_linhas[:MAX_TEXTO]:
            if y > start_y + MAX_TEXTO * lh:
                break
            if linha == "":
                y += lh // 2
                chars_c += 1
                continue
            restante = chars_v - chars_c
            if restante <= 0:
                break
            trecho = linha[:restante] if restante < len(linha) else linha
            s = self._fn_texto.render(trecho, True, C_TEXTO)
            surf.blit(s, (MARGEM, y))
            chars_c += max(1, len(linha))
            y += lh

        # Indicador "mais texto" (pontilhado pulsante)
        if chars_c < sum(max(1, len(l)) for l in self._texto_linhas):
            pt = int(128 + 127 * abs(math.sin(t * 0.005)))
            for xi in range(3):
                pygame.draw.circle(surf, (pt, pt, pt),
                                   (W // 2 - 8 + xi * 12, y + 4), 2)

        # ── Separador ─────────────────────────────────────
        sep_y = self._altura_texto() + 36
        pygame.draw.line(surf, C_BORDA, (MARGEM, sep_y), (W - MARGEM, sep_y), 1)

        # ── Opções ────────────────────────────────────────
        reveal_completo = (int(self._reveal) >=
                           sum(max(1, len(l)) for l in self._texto_linhas))
        opc_y = sep_y + 8

        for i, opcao in enumerate(self._opcoes):
            hover = (i == self._hover) and reveal_completo
            oy    = opc_y + i * 26

            if hover:
                hbg = pygame.Surface((self._opcao_w, 22), pygame.SRCALPHA)
                hbg.fill((*C_HOVER, 180))
                surf.blit(hbg, (self._opcao_x, oy - 2))

            # Número
            cor_num = C_TITULO if hover else C_DIM
            num_s = self._fn_opcao.render(f"[{i+1}]", True, cor_num)
            surf.blit(num_s, (self._opcao_x + 2, oy))

            # Texto da opção
            cor_txt = C_TEXTO if reveal_completo else C_DIM
            max_w   = self._opcao_w - 45
            txt     = opcao
            s       = self._fn_opcao.render(txt, True, cor_txt)
            while s.get_width() > max_w and len(txt) > 6:
                txt = txt[:-4] + "…"
                s   = self._fn_opcao.render(txt, True, cor_txt)
            surf.blit(s, (self._opcao_x + 38, oy))

        # ── Dica de teclado ────────────────────────────────
        dica = self._fn_hint.render(
            "[1-6] escolher   [ESPAÇO] pular   [ESC] fechar",
            True, (55, 50, 35),
        )
        surf.blit(dica, (W - dica.get_width() - MARGEM,
                         PANEL_H - dica.get_height() - 4))
