"""dialogo_arquivo.py — Seletor de arquivo nativo pygame.
Substitui tkinter.filedialog; funciona em Wayland sem dependência de Tk.

Uso:
    import dialogo_arquivo
    caminho = dialogo_arquivo.askopenfilename(tela, clock)
    caminho = dialogo_arquivo.asksaveasfilename(tela, clock, nome_default="mapa")
"""

import pygame
import os

# ── Cores ──────────────────────────────────────────────────
_FUNDO   = (22,  33,  62)
_PAINEL  = (30,  40,  75)
_BORDA   = (50,  70, 110)
_TEXTO   = (238, 226, 220)
_DIM     = (154, 140, 152)
_ACENTO  = (233,  69,  96)
_VERDE   = ( 78, 204, 163)
_OURO    = (212, 168,  67)
_SEL     = ( 15,  52,  96)
_HOVER   = ( 35,  65, 110)
_PASTA   = (212, 168,  67)
_ARQUIVO = (238, 226, 220)

_W       = 640
_H       = 480
_ROW_H   = 22
_MAX_VIS = 14


def _listar(diretorio, ext):
    try:
        entradas = os.listdir(diretorio)
    except PermissionError:
        return [], []
    pastas = sorted(
        [e for e in entradas
         if os.path.isdir(os.path.join(diretorio, e)) and not e.startswith(".")],
        key=str.lower,
    )
    arquivos = sorted(
        [e for e in entradas
         if e.lower().endswith(ext) and os.path.isfile(os.path.join(diretorio, e))],
        key=str.lower,
    )
    return pastas, arquivos


def _dialogo(tela, clock, titulo, modo, nome_default="arquivo", ext=".json"):
    """modo: 'abrir' | 'salvar'  — retorna caminho str ou None."""
    pygame.font.init()
    fn   = pygame.font.SysFont("monospace", 13)
    fn_s = pygame.font.SysFont("monospace", 11)
    fn_t = pygame.font.SysFont("monospace", 15, bold=True)

    sw, sh = tela.get_size()
    dx     = (sw - _W) // 2
    dy     = (sh - _H) // 2

    fundo   = tela.copy()
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))

    diretorio   = os.path.expanduser("~")
    entrada     = nome_default
    campo_ativo = False
    scroll      = 0
    sel_nome    = ""
    cursor_vis  = True
    cursor_t    = pygame.time.get_ticks()

    def reconstruir():
        nonlocal scroll, sel_nome
        scroll   = 0
        sel_nome = ""

    def itens():
        p, a = _listar(diretorio, ext)
        return [("..", "pasta")] + [(x, "pasta") for x in p] + [(x, "arquivo") for x in a]

    running   = True
    resultado = None

    while running:
        now = pygame.time.get_ticks()
        if now - cursor_t > 500:
            cursor_vis = not cursor_vis
            cursor_t   = now

        lista = itens()

        janela      = pygame.Rect(dx,          dy,          _W,       _H)
        barra_tit   = pygame.Rect(dx,          dy,          _W,       32)
        barra_cam   = pygame.Rect(dx + 8,      dy + 38,     _W - 16,  24)
        lista_rect  = pygame.Rect(dx + 8,      dy + 70,     _W - 18,  _ROW_H * _MAX_VIS)
        nome_label  = pygame.Rect(dx + 8,      dy + _H - 90, 80,      24)
        nome_rect   = pygame.Rect(dx + 92,     dy + _H - 90, _W - 100, 24)
        btn_ok      = pygame.Rect(dx + _W - 200, dy + _H - 50, 90,   32)
        btn_cancel  = pygame.Rect(dx + _W - 105, dy + _H - 50, 90,   32)

        mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max(0, len(lista) - _MAX_VIS), scroll - event.y))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                if campo_ativo:
                    if event.key == pygame.K_BACKSPACE:
                        entrada = entrada[:-1]
                    elif event.key == pygame.K_RETURN:
                        if modo == "salvar" and entrada.strip():
                            resultado = os.path.join(diretorio, entrada)
                            if not resultado.lower().endswith(ext):
                                resultado += ext
                            running = False
                        elif modo == "abrir":
                            p = os.path.join(diretorio, entrada)
                            if os.path.isfile(p):
                                resultado = p
                                running   = False
                    elif event.unicode and event.unicode.isprintable():
                        entrada += event.unicode
                else:
                    if event.key == pygame.K_RETURN and sel_nome:
                        resultado = os.path.join(diretorio, sel_nome)
                        running   = False
                    if event.key == pygame.K_PAGEUP:
                        scroll = max(0, scroll - _MAX_VIS)
                    if event.key == pygame.K_PAGEDOWN:
                        scroll = min(max(0, len(lista) - _MAX_VIS), scroll + _MAX_VIS)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                campo_ativo = nome_rect.collidepoint(mouse)

                for i in range(_MAX_VIS):
                    idx = scroll + i
                    if idx >= len(lista):
                        break
                    row_r = pygame.Rect(
                        lista_rect.x, lista_rect.y + i * _ROW_H,
                        lista_rect.w - 8, _ROW_H,
                    )
                    if row_r.collidepoint(mouse):
                        nome, tipo = lista[idx]
                        if tipo == "pasta":
                            if nome == "..":
                                diretorio = os.path.dirname(diretorio) or diretorio
                            else:
                                diretorio = os.path.join(diretorio, nome)
                            reconstruir()
                        else:
                            sel_nome    = nome
                            entrada     = nome
                            campo_ativo = False
                        break

                if btn_ok.collidepoint(mouse):
                    if modo == "salvar" and entrada.strip():
                        resultado = os.path.join(diretorio, entrada)
                        if not resultado.lower().endswith(ext):
                            resultado += ext
                        running = False
                    elif modo == "abrir":
                        if sel_nome:
                            resultado = os.path.join(diretorio, sel_nome)
                            running   = False
                        elif entrada.strip():
                            p = os.path.join(diretorio, entrada)
                            if os.path.isfile(p):
                                resultado = p
                                running   = False

                if btn_cancel.collidepoint(mouse):
                    return None

        # ── Desenho ─────────────────────────────────────────
        tela.blit(fundo, (0, 0))
        tela.blit(overlay, (0, 0))

        # Janela
        pygame.draw.rect(tela, _FUNDO, janela, border_radius=8)
        pygame.draw.rect(tela, _BORDA, janela, 1, border_radius=8)

        # Barra de título
        pygame.draw.rect(tela, (30, 45, 90), barra_tit, border_radius=8)
        t = fn_t.render(titulo, True, _OURO)
        tela.blit(t, (barra_tit.x + 10, barra_tit.y + (32 - t.get_height()) // 2))

        # Barra de caminho
        pygame.draw.rect(tela, _PAINEL, barra_cam, border_radius=4)
        pygame.draw.rect(tela, _BORDA,  barra_cam, 1, border_radius=4)
        cam = diretorio
        if len(cam) > 72:
            cam = "..." + cam[-69:]
        tc = fn_s.render(cam, True, _DIM)
        tela.blit(tc, (barra_cam.x + 6, barra_cam.y + (24 - tc.get_height()) // 2))

        # Lista
        pygame.draw.rect(tela, _PAINEL, lista_rect, border_radius=4)
        pygame.draw.rect(tela, _BORDA,  lista_rect, 1, border_radius=4)

        for i in range(_MAX_VIS):
            idx = scroll + i
            if idx >= len(lista):
                break
            nome, tipo = lista[idx]
            row_r = pygame.Rect(
                lista_rect.x + 1, lista_rect.y + i * _ROW_H,
                lista_rect.w - 10, _ROW_H,
            )
            hover = row_r.collidepoint(mouse)
            sel   = (nome == sel_nome and tipo == "arquivo")
            if sel:
                pygame.draw.rect(tela, _SEL, row_r)
            elif hover:
                pygame.draw.rect(tela, _HOVER, row_r)
            prefixo = "[/] " if tipo == "pasta" else "    "
            cor     = _PASTA if tipo == "pasta" else _ARQUIVO
            ti      = fn_s.render(prefixo + nome, True, cor)
            tela.blit(ti, (row_r.x + 6, row_r.y + (row_r.h - ti.get_height()) // 2))

        # Scrollbar
        if len(lista) > _MAX_VIS:
            sb_h    = lista_rect.h
            thumb_h = max(20, int(sb_h * _MAX_VIS / len(lista)))
            thumb_y = lista_rect.y + int(
                (sb_h - thumb_h) * scroll / max(1, len(lista) - _MAX_VIS)
            )
            pygame.draw.rect(tela, _BORDA, (lista_rect.right - 8, lista_rect.y, 8, sb_h))
            pygame.draw.rect(tela, _DIM,   (lista_rect.right - 8, thumb_y,      8, thumb_h))

        # Campo nome / filtro
        label_txt = "Salvar como:" if modo == "salvar" else "Arquivo:"
        tl = fn_s.render(label_txt, True, _DIM)
        tela.blit(tl, (nome_label.x, nome_label.y + (24 - tl.get_height()) // 2))

        cor_b = _ACENTO if campo_ativo else _BORDA
        pygame.draw.rect(tela, _PAINEL, nome_rect, border_radius=4)
        pygame.draw.rect(tela, cor_b,   nome_rect, 1, border_radius=4)
        txt_e = fn.render(
            entrada + ("|" if campo_ativo and cursor_vis else ""), True, _TEXTO
        )
        tela.blit(txt_e, (nome_rect.x + 6, nome_rect.y + (nome_rect.h - txt_e.get_height()) // 2))

        # Botões
        ok_txt  = "Salvar" if modo == "salvar" else "Abrir"
        ok_hov  = btn_ok.collidepoint(mouse)
        can_hov = btn_cancel.collidepoint(mouse)
        pygame.draw.rect(tela, _VERDE  if ok_hov  else (40, 120, 90), btn_ok,     border_radius=6)
        pygame.draw.rect(tela, _ACENTO if can_hov else (80, 40,  50), btn_cancel, border_radius=6)
        pygame.draw.rect(tela, _VERDE,  btn_ok,     1, border_radius=6)
        pygame.draw.rect(tela, _ACENTO, btn_cancel, 1, border_radius=6)
        tok = fn.render(ok_txt,     True, _TEXTO)
        tca = fn.render("Cancelar", True, _TEXTO)
        tela.blit(tok, tok.get_rect(center=btn_ok.center))
        tela.blit(tca, tca.get_rect(center=btn_cancel.center))

        pygame.display.flip()
        clock.tick(60)

    return resultado


def askopenfilename(tela, clock, titulo="Abrir Arquivo", ext=".json"):
    """Retorna caminho do arquivo selecionado, ou None se cancelado."""
    return _dialogo(tela, clock, titulo, "abrir", ext=ext)


def asksaveasfilename(tela, clock, titulo="Salvar Arquivo",
                      nome_default="mapa", ext=".json"):
    """Retorna caminho para salvar (com extensão), ou None se cancelado."""
    return _dialogo(tela, clock, titulo, "salvar",
                    nome_default=nome_default, ext=ext)
