"""
narrativa.py — Motor pygame de narrativa interativa.
Campanha: Degraus para o Abismo (CoC 7e)

Usa:
    twee_parser.py  — parseia .twee
    tinydb          — save / load de campanha
    networkx        — grafo interno de cenas
    combate.py      — chamado nos nos [combate]
"""

from __future__ import annotations

import json
import math
import os
import sys

# SDL_VIDEODRIVER deve ser definido ANTES de qualquer import pygame.
os.environ["SDL_VIDEODRIVER"] = "x11"

import pygame
import subprocess
from datetime import datetime
from typing import Optional

from tinydb import TinyDB, Query
import networkx as nx

# ── Caminhos ──────────────────────────────────────────────────
_DIR    = os.path.dirname(os.path.abspath(__file__))
_RAIZ   = os.path.normpath(os.path.join(_DIR, "..", ".."))
_GITHUB = os.path.join(_RAIZ, ".github")

sys.path.insert(0, _GITHUB)
sys.path.insert(0, _RAIZ)

from twee_parser import TweeParser, AvaliadorCondicoes, Link
import gerenciador_mundos as _gm
import gerenciador_assets as _ga
_MUNDO_ID = _gm.mundo_da_campanha(_DIR)

_TWEE    = os.path.join(_DIR, "degraus_para_o_abismo.twee")
_SAVE    = os.path.join(_DIR, "campanha.json")
_COMBATE = os.path.join(_GITHUB, "combate.py")
_MENU    = os.path.join(_GITHUB, "menu_pygame.py")
_MUNDO   = os.path.join(_RAIZ, "mundo_aberto.py")
# arquivo de estado compartilhado entre mundo_aberto ↔ narrativa
_ESTADO_CAMP  = os.path.join(_DIR, "estado_campanha.json")
_ENTRADA_NAR  = os.path.join(_DIR, "entrada_narrativa.json")

# ── Tela ───────────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60

# ── Paleta ─────────────────────────────────────────────────────
FUNDO   = ( 10,  14,  28)
PAINEL  = ( 18,  26,  50)
PAINEL2 = ( 22,  33,  62)
BORDA   = ( 45,  65, 105)
TEXTO   = (238, 226, 220)
DIM     = (130, 118, 112)
ACENTO  = (233,  69,  96)
VERDE   = ( 78, 204, 163)
OURO    = (212, 168,  67)
HOVER   = ( 38,  68, 118)
PRETO   = (  0,   0,   0)
COMBATE_COR = (140,  40,  20)
SAN_OK  = ( 78, 204, 163)
SAN_MED = (212, 168,  67)
SAN_BAD = (200,  55,  55)

# ── Fonte ──────────────────────────────────────────────────────
def _fonte(size: int, estilo: str = "narrativa") -> pygame.font.Font:
    return _ga.get_font(estilo, size)


# ══════════════════════════════════════════════════════════════
#  ESTADO DO JOGO
# ══════════════════════════════════════════════════════════════

class EstadoJogo:
    def __init__(self):
        self.variaveis:  dict = {}
        self.cena_atual: str  = "inicio"
        self.historico:  list = []
        self.san_max:    int  = 10

    @property
    def san(self) -> int:
        return int(self.variaveis.get("san", self.san_max))

    def aplicar_san(self, delta: int):
        novo = max(0, min(self.san_max, self.san + delta))
        self.variaveis["san"] = novo

    def para_dict(self) -> dict:
        return {
            "cena":      self.cena_atual,
            "variaveis": dict(self.variaveis),
            "historico": list(self.historico),
        }

    def de_dict(self, d: dict):
        self.cena_atual = d.get("cena", "inicio")
        self.variaveis  = d.get("variaveis", {})
        self.historico  = d.get("historico", [])


# ══════════════════════════════════════════════════════════════
#  MOTOR NARRATIVO
# ══════════════════════════════════════════════════════════════

class MotorNarrativa:
    MAX_RECURSAO = 10

    def __init__(self):
        self.parser    = TweeParser(_TWEE)
        self.avaliador = AvaliadorCondicoes()
        self.estado    = EstadoJogo()
        self.db        = TinyDB(_SAVE)
        self.grafo     = nx.DiGraph()
        self.cena_atual = None
        self._delta_san  = 0      # ultimo delta para UI piscar

        self._montar_grafo()
        self._ir_para(self.parser.inicio)

    def _montar_grafo(self):
        for a, b in self.parser.nos_grafo():
            self.grafo.add_edge(a, b)

    # ── Navegação ─────────────────────────────────────────────

    def _ir_para(self, nome: str, _prof: int = 0) -> bool:
        if _prof > self.MAX_RECURSAO:
            return False
        passagem = self.parser.obter(nome)
        if not passagem:
            return False

        self.estado.cena_atual = nome
        self.estado.historico.append(nome)
        self.cena_atual = passagem

        # Executa @set e @san
        san_antes = self.estado.san
        for cmd in passagem.comandos:
            if cmd["tipo"] in ("set", "san"):
                self._exec_cmd(cmd)
        self._delta_san = self.estado.san - san_antes

        # Auto-transicao por @if (executa o primeiro verdadeiro)
        for cmd in passagem.comandos:
            if cmd["tipo"] == "if":
                if self.avaliador.avaliar(cmd["condicao"], self.estado.variaveis):
                    return self._ir_para(cmd["destino"], _prof + 1)

        return True

    def _exec_cmd(self, cmd: dict):
        if cmd["tipo"] == "set":
            self.estado.variaveis[cmd["var"]] = cmd["valor"]
        elif cmd["tipo"] == "san":
            self.estado.aplicar_san(cmd["valor"])

    # ── Consultas ─────────────────────────────────────────────

    def links_disponiveis(self) -> list:
        if not self.cena_atual:
            return []
        return list(self.cena_atual.links)

    def combate_pendente(self) -> str | None:
        if not self.cena_atual:
            return None
        for cmd in self.cena_atual.comandos:
            if cmd["tipo"] == "combate":
                return cmd["inimigo"]
        return None

    def e_fim(self) -> bool:
        return bool(self.cena_atual and "fim" in self.cena_atual.tags)

    def nome_cena_formatado(self) -> str:
        if not self.cena_atual:
            return ""
        return self.cena_atual.nome.replace("_", " ").title()

    # ── Ação ──────────────────────────────────────────────────

    def escolher(self, link: Link):
        for k, v in link.efeitos.items():
            self.estado.variaveis[k] = v
        self._ir_para(link.destino)

    # ── Persistência ──────────────────────────────────────────

    def salvar(self, slot: str = "auto"):
        Slot = Query()
        dados = {
            "slot": slot,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "cena": self.estado.cena_atual,
            **self.estado.para_dict(),
        }
        self.db.upsert(dados, Slot.slot == slot)

    def carregar(self, slot: str = "auto") -> bool:
        Slot   = Query()
        result = self.db.search(Slot.slot == slot)
        if not result:
            return False
        dados = result[0]
        self.estado.de_dict(dados)
        passagem = self.parser.obter(self.estado.cena_atual)
        if passagem:
            self.cena_atual = passagem
        return True

    def slots_disponiveis(self) -> list[dict]:
        return sorted(self.db.all(),
                      key=lambda x: x.get("data", ""),
                      reverse=True)

    def novo_jogo(self):
        self.estado = EstadoJogo()
        self._ir_para(self.parser.inicio)


# ══════════════════════════════════════════════════════════════
#  INTERFACE PYGAME
# ══════════════════════════════════════════════════════════════

# Zonas de layout
_TOP_H    = 55
_NOME_H   = 38
_TEXT_Y   = _TOP_H + _NOME_H            # 93
_SEP_Y    = 468
_CHOICE_Y = 480
_BOT_Y    = 648
_TEXT_H   = _SEP_Y - _TEXT_Y           # 375
_CHOICE_H = _BOT_Y - _CHOICE_Y         # 168
_MARGEM   = 18
_CHOICE_W = W - 2 * _MARGEM
_CHOICE_BH = 32                         # altura de cada botao de escolha


class TelaJogo:
    CHARS_POR_SEG = 35   # velocidade do texto digitando

    def __init__(self, motor: MotorNarrativa,
                 tela: pygame.Surface, clock: pygame.time.Clock,
                 veio_do_mundo: bool = False):
        self.motor         = motor
        self.tela          = tela
        self.clock         = clock
        self.veio_do_mundo = veio_do_mundo

        # Fontes
        self.fn_titulo  = _fonte(15)
        self.fn_texto   = _fonte(15)
        self.fn_pequeno = _fonte(13)
        self.fn_hint    = _fonte(11)
        self.fn_flash   = _fonte(28)   # usado no flash de SAN
        self.fn_overlay = _fonte(18)   # usado nos overlays

        # Estado da UI
        self._linhas:      list[str]                    = []    # texto da cena, word-wrapped
        self._reveal:      float                        = 0.0   # chars revelados (float)
        self._scroll:      int                          = 0     # offset de scroll em pixels
        self._hover:       int                          = -1    # indice do link em hover
        self._san_flash:   int                          = 0     # ms restantes de flash
        self._san_delta:   int                          = 0     # ultimo delta de SAN
        self._processo:    Optional[subprocess.Popen]  = None  # subprocess combate
        self._modo:        str                          = "jogo" # "jogo"|"save"|"load"
        self._msg:         str                          = ""
        self._msg_t:       int                          = 0
        # Geometria dos overlays (inicializada em _render_overlay_fundo)
        self._ov_rect:     pygame.Rect                 = pygame.Rect(0, 0, 0, 0)
        self._ov_y0:       int                          = 0

        self._atualizar_texto()

    # ── Quebra de texto ───────────────────────────────────────

    def _quebrar_texto(self, linhas_fonte: list[str]) -> list[str]:
        largura = W - 2 * _MARGEM - 12
        resultado = []
        for linha in linhas_fonte:
            if not linha.strip():
                resultado.append("")
                continue
            palavras = linha.split()
            atual    = ""
            for p in palavras:
                teste = (atual + " " + p).strip()
                if self.fn_texto.size(teste)[0] <= largura:
                    atual = teste
                else:
                    if atual:
                        resultado.append(atual)
                    atual = p
            if atual:
                resultado.append(atual)
        return resultado

    def _atualizar_texto(self):
        if not self.motor.cena_atual:
            self._linhas = []
        else:
            self._linhas = self._quebrar_texto(self.motor.cena_atual.texto)
        self._reveal = 0.0
        self._scroll = 0

    # ── Loop principal ────────────────────────────────────────

    def executar(self):
        while True:
            dt = self.clock.tick(FPS)
            self._atualizar(dt)
            self._renderizar()
            pygame.display.flip()

    # ── Update ────────────────────────────────────────────────

    def _atualizar(self, dt: int):
        # Flash de SAN
        if self._san_flash > 0:
            self._san_flash = max(0, self._san_flash - dt)

        # Mensagem temporaria
        if self._msg_t > 0:
            self._msg_t = max(0, self._msg_t - dt)
            if self._msg_t == 0:
                self._msg = ""

        # Typing effect
        total_chars = sum(max(1, len(l)) for l in self._linhas)
        if self._reveal < total_chars:
            self._reveal = min(total_chars,
                               self._reveal + self.CHARS_POR_SEG * dt / 1000)

        # Checar subprocess de combate
        if self._processo is not None:
            if self._processo.poll() is not None:
                self._processo = None
                self._mostrar_msg("Combate encerrado. Escolha um caminho.")

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            self._processar_evento(event)

    # ── Eventos ───────────────────────────────────────────────

    def _processar_evento(self, event):
        if self._modo == "jogo":
            self._evento_jogo(event)
        elif self._modo == "save":
            self._evento_save(event)
        elif self._modo == "load":
            self._evento_load(event)

    def _evento_jogo(self, event):
        links = self._links_para_mostrar()

        if event.type == pygame.KEYDOWN:
            # Pular animacao
            if event.key == pygame.K_SPACE:
                total = sum(max(1, len(l)) for l in self._linhas)
                self._reveal = float(total)

            # ESC: voltar ao menu
            elif event.key == pygame.K_ESCAPE:
                self._voltar_menu()

            # F5: salvar rapido
            elif event.key == pygame.K_F5:
                self.motor.salvar("auto")
                self._mostrar_msg("Jogo salvo!")

            # F9: carregar rapido
            elif event.key == pygame.K_F9:
                if self.motor.carregar("auto"):
                    self._atualizar_texto()
                    self._mostrar_msg("Jogo carregado!")
                else:
                    self._mostrar_msg("Nenhum save encontrado.")

            # F2 / F3: save / load menu
            elif event.key == pygame.K_F2:
                self._modo = "save"
            elif event.key == pygame.K_F3:
                self._modo = "load"

            # Teclas de escolha [1-9]
            elif pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(links):
                    self._executar_link(links[idx])

            # ENTER no fim
            elif event.key == pygame.K_RETURN:
                if self.motor.e_fim():
                    self._voltar_menu()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clique nas escolhas
            for i, rect in enumerate(self._rects_choices(links)):
                if rect.collidepoint(event.pos):
                    self._executar_link(links[i])

        elif event.type == pygame.MOUSEWHEEL:
            lh  = self.fn_texto.get_linesize() + 2
            max_scroll = max(0, len(self._linhas) * lh - _TEXT_H)
            self._scroll = max(0, min(max_scroll,
                                      self._scroll - event.y * lh * 3))

        elif event.type == pygame.MOUSEMOTION:
            self._hover = -1
            for i, rect in enumerate(self._rects_choices(links)):
                if rect.collidepoint(event.pos):
                    self._hover = i
                    break

    def _evento_save(self, event):
        slots = ["slot1", "slot2", "slot3"]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._modo = "jogo"
            for i, s in enumerate(slots):
                if event.key == getattr(pygame, f"K_{i+1}"):
                    self.motor.salvar(s)
                    self._mostrar_msg(f"Salvo no slot {i+1}!")
                    self._modo = "jogo"

    def _evento_load(self, event):
        slots = ["auto", "slot1", "slot2", "slot3"]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._modo = "jogo"
            if event.key == pygame.K_0:
                if self.motor.carregar("auto"):
                    self._atualizar_texto()
                    self._mostrar_msg("Save automatico carregado!")
                self._modo = "jogo"
            for i in range(3):
                if event.key == getattr(pygame, f"K_{i+1}"):
                    if self.motor.carregar(f"slot{i+1}"):
                        self._atualizar_texto()
                        self._mostrar_msg(f"Slot {i+1} carregado!")
                    else:
                        self._mostrar_msg(f"Slot {i+1} vazio.")
                    self._modo = "jogo"

    # ── Ações ─────────────────────────────────────────────────

    def _executar_link(self, link):
        # Combate pendente: precisa lancá-lo antes de seguir
        if link.destino and self.motor.parser.obter(link.destino):
            passagem_dest = self.motor.parser.obter(link.destino)
            if passagem_dest and "combate" in passagem_dest.tags:
                self._iniciar_combate(link)
                return

        san_antes = self.motor.estado.san
        self.motor.escolher(link)
        delta = self.motor.estado.san - san_antes
        if delta < 0:
            self._san_flash  = 600
            self._san_delta  = delta
        elif delta > 0:
            self._san_flash  = 400
            self._san_delta  = delta
        self._atualizar_texto()

    def _iniciar_combate(self, link):
        if self._processo and self._processo.poll() is None:
            self._mostrar_msg("Combate ja em andamento!")
            return
        try:
            self._processo = subprocess.Popen([sys.executable, _COMBATE])
        except Exception as e:
            self._mostrar_msg(f"Erro ao iniciar combate: {e}")
            return
        # Navega para a cena de combate
        san_antes = self.motor.estado.san
        self.motor.escolher(link)
        self._san_delta = self.motor.estado.san - san_antes
        if self._san_delta < 0:
            self._san_flash = 600
        self._atualizar_texto()

    def _voltar_menu(self):
        self.motor.salvar("auto")

        if self.veio_do_mundo:
            # Exporta estado para mundo_aberto.py carregar ao reiniciar
            estado_exportado = self.motor.estado.para_dict()
            with open(_ESTADO_CAMP, "w", encoding="utf-8") as f:
                json.dump(estado_exportado, f, ensure_ascii=False, indent=2)
            # Relança mundo_aberto e fecha a narrativa
            try:
                subprocess.Popen([sys.executable, _MUNDO, "--mundo", _MUNDO_ID])
            except Exception:
                pass
        else:
            # Retorno normal ao menu principal
            try:
                subprocess.Popen([sys.executable, _MENU])
            except Exception:
                pass

        pygame.quit()
        sys.exit()

    def _mostrar_msg(self, txt: str, ms: int = 2500):
        self._msg   = txt
        self._msg_t = ms

    # ── Helpers de layout ─────────────────────────────────────

    def _links_para_mostrar(self) -> list:
        if self.motor.e_fim():
            return []
        if self._processo and self._processo.poll() is None:
            return []   # combate em andamento
        return self.motor.links_disponiveis()

    def _rects_choices(self, links: list) -> list[pygame.Rect]:
        rects = []
        y = _CHOICE_Y + 6
        for _ in links[:6]:
            rects.append(pygame.Rect(_MARGEM, y, _CHOICE_W, _CHOICE_BH))
            y += _CHOICE_BH + 5
        return rects

    # ══════════════════════════════════════════════════════════
    #  RENDERIZAÇÃO
    # ══════════════════════════════════════════════════════════

    def _renderizar(self):
        self.tela.fill(FUNDO)

        if self._modo == "save":
            self._render_overlay_save()
            return
        if self._modo == "load":
            self._render_overlay_load()
            return

        self._render_top()
        self._render_nome_cena()
        self._render_texto()
        self._render_separador()

        if self.motor.e_fim():
            self._render_fim()
        elif self._processo and self._processo.poll() is None:
            self._render_combate_andamento()
        else:
            self._render_choices()

        self._render_bottom()
        self._render_san_flash()
        self._render_msg()

    # ── Barra superior ────────────────────────────────────────

    def _render_top(self):
        pygame.draw.rect(self.tela, PAINEL, (0, 0, W, _TOP_H))
        pygame.draw.line(self.tela, BORDA, (0, _TOP_H), (W, _TOP_H), 1)

        # Titulo
        surf = self.fn_titulo.render("DEGRAUS PARA O ABISMO", True, OURO)
        self.tela.blit(surf, (15, (_TOP_H - surf.get_height()) // 2))

        # SAN bar
        san     = self.motor.estado.san
        san_max = self.motor.estado.san_max
        bx, by  = W - 240, 10
        bw, bh  = 160, 16
        pygame.draw.rect(self.tela, (30, 30, 50), (bx, by, bw, bh), border_radius=4)
        fill = int(bw * san / san_max) if san_max > 0 else 0
        if fill > 0:
            cor = SAN_OK if san >= 7 else (SAN_MED if san >= 4 else SAN_BAD)
            pygame.draw.rect(self.tela, cor, (bx, by, fill, bh), border_radius=4)
        pygame.draw.rect(self.tela, BORDA, (bx, by, bw, bh), 1, border_radius=4)

        lbl = self.fn_pequeno.render(f"SAN  {san}/{san_max}", True, TEXTO)
        self.tela.blit(lbl, (bx + bw + 8, by + 1))

        # Pistas coletadas
        pistas = self.motor.estado.variaveis.get("pistas", 0)
        if pistas:
            surf_p = self.fn_hint.render(f"Pistas: {pistas}", True, DIM)
            self.tela.blit(surf_p, (bx + bw + 8, by + 18))

    # ── Nome da cena ──────────────────────────────────────────

    def _render_nome_cena(self):
        y0 = _TOP_H
        pygame.draw.rect(self.tela, PAINEL2, (0, y0, W, _NOME_H))
        pygame.draw.line(self.tela, BORDA, (0, y0 + _NOME_H), (W, y0 + _NOME_H), 1)

        nome = self.motor.nome_cena_formatado()
        surf = self.fn_pequeno.render(f"▶  {nome}", True, DIM)
        self.tela.blit(surf, (_MARGEM, y0 + (_NOME_H - surf.get_height()) // 2))

    # ── Área de texto ─────────────────────────────────────────

    def _render_texto(self):
        # Clip na zona de texto
        clip = pygame.Rect(0, _TEXT_Y, W, _TEXT_H)
        self.tela.set_clip(clip)

        lh      = self.fn_texto.get_linesize() + 3
        y       = _TEXT_Y + 8 - self._scroll
        chars_v = int(self._reveal)
        chars_c = 0  # chars contados ate agora

        for linha in self._linhas:
            # Auto-scroll: manter texto visivel
            if y + lh > _TEXT_Y and y < _TEXT_Y + _TEXT_H:
                if not linha:  # linha em branco = espaco de paragrafo
                    y += lh // 2
                    continue
                # Quantos chars desta linha mostrar
                restante = chars_v - chars_c
                if restante <= 0:
                    break
                trecho = linha[:restante] if restante < len(linha) else linha
                surf   = self.fn_texto.render(trecho, True, TEXTO)
                self.tela.blit(surf, (_MARGEM, y))
            elif not linha:
                y += lh // 2
                chars_c += 1
                continue

            chars_c += max(1, len(linha))
            y       += lh

        # Auto-scroll ao digitar
        if chars_c < int(self._reveal):
            max_scroll = max(0, len(self._linhas) * lh - _TEXT_H + 16)
            tgt = max(0, y - _TEXT_Y - _TEXT_H + lh * 2)
            if tgt > self._scroll:
                self._scroll = min(max_scroll, tgt)

        self.tela.set_clip(None)

        # Indicador de scroll
        total_h = len(self._linhas) * lh
        if total_h > _TEXT_H:
            sb_h  = max(30, int(_TEXT_H * _TEXT_H / total_h))
            sb_y  = _TEXT_Y + int(self._scroll / (total_h - _TEXT_H) * (_TEXT_H - sb_h))
            pygame.draw.rect(self.tela, BORDA,
                             (W - 8, sb_y, 5, sb_h), border_radius=3)

    # ── Separador ─────────────────────────────────────────────

    def _render_separador(self):
        pygame.draw.line(self.tela, BORDA, (_MARGEM, _SEP_Y), (W - _MARGEM, _SEP_Y), 1)
        lbl  = self.fn_hint.render("━━━ ESCOLHA ━━━", True, BORDA)
        cx   = (W - lbl.get_width()) // 2
        self.tela.blit(lbl, (cx, _SEP_Y - 6))

    # ── Escolhas ──────────────────────────────────────────────

    def _render_choices(self):
        links = self._links_para_mostrar()

        for i, (link, rect) in enumerate(zip(links[:6], self._rects_choices(links))):
            # Cores
            is_hover = (i == self._hover)
            cor = HOVER if is_hover else PAINEL2
            pygame.draw.rect(self.tela, cor, rect, border_radius=5)
            pygame.draw.rect(self.tela, BORDA, rect, 1, border_radius=5)

            # Numero
            num  = self.fn_pequeno.render(f"[{i+1}]", True, OURO)
            self.tela.blit(num, (rect.x + 8, rect.y + (rect.h - num.get_height()) // 2))

            # Texto do link (trunca se necessario)
            max_w  = _CHOICE_W - 55
            txt    = link.texto
            surf_l = self.fn_texto.render(txt, True, TEXTO)
            while surf_l.get_width() > max_w and len(txt) > 4:
                txt    = txt[:-4] + "..."
                surf_l = self.fn_texto.render(txt, True, TEXTO)
            cy = rect.y + (rect.h - surf_l.get_height()) // 2
            self.tela.blit(surf_l, (rect.x + 40, cy))

        if not links and not self.motor.e_fim():
            surf = self.fn_pequeno.render(
                "  (nenhuma acao disponivel — pressione ESC para o menu)", True, DIM)
            self.tela.blit(surf, (_MARGEM, _CHOICE_Y + 10))

    # ── Combate em andamento ──────────────────────────────────

    def _render_combate_andamento(self):
        t    = pygame.time.get_ticks()
        alfa = int(128 + 60 * abs(math.sin(t * 0.003)))
        surf = pygame.Surface((W - 2 * _MARGEM, 45), pygame.SRCALPHA)
        surf.fill((*COMBATE_COR, alfa))
        pygame.draw.rect(surf, ACENTO, surf.get_rect(), 1, border_radius=6)
        self.tela.blit(surf, (_MARGEM, _CHOICE_Y + 10))

        msg  = self.fn_titulo.render(
            "  ⚔  COMBATE EM ANDAMENTO...  aguardando resultado  ⚔", True, TEXTO)
        cy   = _CHOICE_Y + 10 + (45 - msg.get_height()) // 2
        self.tela.blit(msg, ((W - msg.get_width()) // 2, cy))

    # ── Tela de fim ───────────────────────────────────────────

    def _render_fim(self):
        surf = self.fn_texto.render("[ENTER]  Voltar ao Menu Principal", True, VERDE)
        rect = surf.get_rect(center=(W // 2, _CHOICE_Y + 40))
        self.tela.blit(surf, rect)

        san = self.motor.estado.san
        cor = SAN_OK if san >= 7 else (SAN_MED if san >= 4 else SAN_BAD)
        s2  = self.fn_pequeno.render(
            f"Sanidade final: {san}/{self.motor.estado.san_max}", True, cor)
        self.tela.blit(s2, s2.get_rect(center=(W // 2, _CHOICE_Y + 70)))

    # ── Barra inferior ────────────────────────────────────────

    def _render_bottom(self):
        pygame.draw.line(self.tela, BORDA, (0, _BOT_Y), (W, _BOT_Y), 1)
        pygame.draw.rect(self.tela, PAINEL, (0, _BOT_Y, W, H - _BOT_Y))

        itens = [
            ("[F5] Salvar",   50),
            ("[F9] Carregar", 175),
            ("[F2] Slots",    310),
            ("[ESC] Menu",    440),
            ("[ESPAÇO] Pular",580),
        ]
        for txt, x in itens:
            surf = self.fn_hint.render(txt, True, DIM)
            self.tela.blit(surf, (x, _BOT_Y + (H - _BOT_Y - surf.get_height()) // 2))

    # ── Flash de SAN ─────────────────────────────────────────

    def _render_san_flash(self):
        if self._san_flash <= 0:
            return
        alfa = int(180 * self._san_flash / 600)
        cor  = ACENTO if self._san_delta < 0 else VERDE
        ov   = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((*cor, alfa))
        self.tela.blit(ov, (0, 0))

        delta_txt = f"SAN {self._san_delta:+d}"
        surf = self.fn_flash.render(delta_txt, True, (*cor, 255))
        self.tela.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

    # ── Mensagem temporária ───────────────────────────────────

    def _render_msg(self):
        if not self._msg or self._msg_t <= 0:
            return
        surf = self.fn_pequeno.render(self._msg, True, OURO)
        bx   = (W - surf.get_width()) // 2 - 10
        by   = _BOT_Y - surf.get_height() - 8
        bg   = pygame.Surface((surf.get_width() + 20, surf.get_height() + 8),
                               pygame.SRCALPHA)
        bg.fill((20, 20, 40, 200))
        self.tela.blit(bg, (bx, by))
        self.tela.blit(surf, (bx + 10, by + 4))

    # ── Overlay: Salvar ───────────────────────────────────────

    def _render_overlay_save(self):
        self._render_overlay_fundo("SALVAR JOGO")
        linhas = [
            "[1]  Slot 1",
            "[2]  Slot 2",
            "[3]  Slot 3",
            "",
            "[ESC]  Cancelar",
        ]
        self._render_overlay_linhas(linhas)

    # ── Overlay: Carregar ─────────────────────────────────────

    def _render_overlay_load(self):
        self._render_overlay_fundo("CARREGAR JOGO")
        slots = self.motor.slots_disponiveis()
        info  = {s["slot"]: s.get("data", "?") for s in slots}
        linhas = [
            f"[0]  Auto       {info.get('auto', '(vazio)')}",
            f"[1]  Slot 1     {info.get('slot1', '(vazio)')}",
            f"[2]  Slot 2     {info.get('slot2', '(vazio)')}",
            f"[3]  Slot 3     {info.get('slot3', '(vazio)')}",
            "",
            "[ESC]  Cancelar",
        ]
        self._render_overlay_linhas(linhas)

    def _render_overlay_fundo(self, titulo: str):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        self.tela.blit(ov, (0, 0))

        pw, ph = 460, 300
        px, py = (W - pw) // 2, (H - ph) // 2
        pygame.draw.rect(self.tela, PAINEL2, (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(self.tela, BORDA,   (px, py, pw, ph), 2, border_radius=10)

        surf = self.fn_overlay.render(titulo, True, OURO)
        self.tela.blit(surf, surf.get_rect(centerx=W // 2, y=py + 18))
        pygame.draw.line(self.tela, BORDA,
                         (px + 20, py + 44), (px + pw - 20, py + 44), 1)

        self._ov_rect = pygame.Rect(px, py, pw, ph)
        self._ov_y0   = py + 56

    def _render_overlay_linhas(self, linhas: list[str]):
        y = self._ov_y0
        for linha in linhas:
            if linha:
                surf = self.fn_texto.render(linha, True, TEXTO)
                x    = self._ov_rect.x + 30
                self.tela.blit(surf, (x, y))
            y += self.fn_texto.get_linesize() + 6


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Narrativa interativa CoC 7e")
    ap.add_argument("--passagem", default=None,
                    help="Nome da passagem twee inicial (lançado pelo mundo aberto)")
    ap.add_argument("--entrada", default=None,
                    help="Caminho para entrada_narrativa.json (variáveis da campanha)")
    args, _ = ap.parse_known_args()

    pygame.init()
    tela  = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Degraus para o Abismo — Call of Cthulhu 7e")
    clock = pygame.time.Clock()

    motor = MotorNarrativa()
    veio_do_mundo = bool(args.passagem)

    if args.passagem:
        # Lançado pelo mundo aberto: carrega variáveis e navega direto para a cena
        if args.entrada and os.path.exists(args.entrada):
            with open(args.entrada, "r", encoding="utf-8") as f:
                entrada = json.load(f)
            motor.estado.variaveis.update(entrada)
        motor._ir_para(args.passagem)
    else:
        # Lançado normalmente: carrega save automático
        motor.carregar("auto")

    ui = TelaJogo(motor, tela, clock, veio_do_mundo=veio_do_mundo)
    ui.executar()


if __name__ == "__main__":
    main()
