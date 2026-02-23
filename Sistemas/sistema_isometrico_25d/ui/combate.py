import pygame
import sys
import random
import math
import os
import json

pygame.init()
pygame.display.set_caption("CoC 7e — Combate")

LARGURA, ALTURA = 800, 650
tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
clock = pygame.time.Clock()

# ── Cores ──────────────────────────────────────────────────
COR_FUNDO       = (26,  26,  46)
COR_PAINEL      = (22,  33,  62)
COR_DESTAQUE    = (15,  52,  96)
COR_ACENTO      = (233, 69,  96)
COR_TEXTO       = (238, 226, 220)
COR_TEXTO_DIM   = (154, 140, 152)
COR_OURO        = (212, 168, 67)
COR_VERDE       = (78,  204, 163)
COR_ROXO        = (107, 45,  139)
COR_VERMELHO    = (200, 50,  50)
COR_AMARELO     = (230, 200, 60)
COR_LOG_INFO    = (180, 180, 220)
COR_LOG_DANO    = (233, 69,  96)
COR_LOG_SUCESSO = (78,  204, 163)
COR_LOG_FALHA   = (154, 140, 152)
COR_CRITICO     = (212, 168, 67)

# ── Fontes ─────────────────────────────────────────────────
fn_titulo  = pygame.font.SysFont("monospace", 26, bold=True)
fn_normal  = pygame.font.SysFont("monospace", 14)
fn_pequena = pygame.font.SysFont("monospace", 12)
fn_grande  = pygame.font.SysFont("monospace", 18, bold=True)

# ══════════════════════════════════════════════════════════════
# MODELOS DE DADOS
# ══════════════════════════════════════════════════════════════

def calcular_bonus_dano(for_, tam):
    """Calcula o Bônus de Dano (DB) baseado em FOR+TAM."""
    total = for_ + tam
    if total <= 64:
        return "-2"
    elif total <= 84:
        return "-1"
    elif total <= 124:
        return "0"
    elif total <= 164:
        return "+1d4"
    elif total <= 204:
        return "+1d6"
    else:
        return "+2d6"


def rolar_db(db_str):
    """Converte string de DB em valor numérico."""
    if db_str == "0":
        return 0
    elif db_str == "-1":
        return -1
    elif db_str == "-2":
        return -2
    elif db_str == "+1d4":
        return random.randint(1, 4)
    elif db_str == "+1d6":
        return random.randint(1, 6)
    elif db_str == "+2d6":
        return random.randint(2, 12)
    return 0


def classificar_rolagem(resultado, habilidade):
    """Retorna o tipo de sucesso/falha para CoC 7e."""
    if resultado == 1:
        return "SUCESSO CRITICO", COR_CRITICO
    if resultado <= habilidade // 5:
        return "SUCESSO EXTREMO", COR_OURO
    if resultado <= habilidade // 2:
        return "SUCESSO BONUS", COR_VERDE
    if resultado <= habilidade:
        return "SUCESSO", COR_LOG_SUCESSO
    if resultado >= 100 or (habilidade < 50 and resultado >= 96):
        return "FUMBLE", COR_VERMELHO
    return "FALHA", COR_LOG_FALHA


# ══════════════════════════════════════════════════════════════
# CARREGAMENTO DE FICHA  (JSON gerado por ficha.py)
# ══════════════════════════════════════════════════════════════

def carregar_investigador_json(caminho=None):
    """Busca investigador.json na pasta do jogo e retorna dict ou None."""
    if caminho is None:
        base    = os.path.dirname(os.path.abspath(__file__))
        caminho = os.path.join(base, "investigador.json")
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def personagem_de_ficha(ficha):
    """Converte dict de ficha (salvo por ficha.py) em Personagem."""
    dp  = ficha.get("dados_pessoais", {})
    car = ficha.get("caracteristicas", {})
    per = ficha.get("pericias", {})

    nome = dp.get("nome") or "Investigador"

    # Escolhe a melhor habilidade de combate como arma principal
    mapa_armas = {
        "Armas de Fogo (Pistola)":    ("Pistola .38",   "1d10"),
        "Armas de Fogo (Rifle)":      ("Rifle",         "1d10+2"),
        "Armas de Fogo (Espingarda)": ("Espingarda",    "2d6+1"),
        "Armas Brancas":              ("Arma Branca",   "1d8"),
        "Lutar (Soco)":               ("Punhos",        "1d3"),
        "Arremessar":                 ("Arremesso",     "1d6"),
    }
    arma_nome = "Punhos"
    arma_dano = "1d3"
    arma_hab  = per.get("Lutar (Soco)", 25)

    for pericia, (w_nome, w_dano) in mapa_armas.items():
        v = per.get(pericia, 0)
        if v > arma_hab:
            arma_hab  = v
            arma_nome = w_nome
            arma_dano = w_dano

    return Personagem(
        nome            = nome,
        for_            = car.get("forca",        60),
        con             = car.get("constituicao",  55),
        tam             = car.get("tamanho",       65),
        des             = car.get("destreza",      60),
        int_            = car.get("inteligencia",  70),
        pod             = car.get("poder",         55),
        apl             = car.get("aparencia",     60),
        edu             = car.get("educacao",      50),
        hp              = car.get("pv_max",        None),
        san             = car.get("sanidade",      None),
        arma_nome       = arma_nome,
        arma_dano       = arma_dano,
        arma_habilidade = arma_hab,
        eh_jogador      = True,
    )


class Personagem:
    def __init__(self, nome, for_, con, tam, des, int_, pod, apl,
                 edu=50, hp=None, san=None,
                 arma_nome="Punhos", arma_dano="1d3", arma_habilidade=50,
                 eh_jogador=True):
        self.nome            = nome
        self.FOR             = for_
        self.CON             = con
        self.TAM             = tam
        self.DES             = des
        self.INT             = int_
        self.POD             = pod
        self.APL             = apl
        self.EDU             = edu

        self.HP_MAX          = hp if hp else (con + tam) // 10
        self.HP              = self.HP_MAX
        self.SAN             = san if san else pod
        self.SAN_MAX         = self.SAN

        self.DB              = calcular_bonus_dano(for_, tam)
        self.MOV             = 8
        self.esquiva         = des // 2

        self.arma_nome       = arma_nome
        self.arma_dano       = arma_dano
        self.arma_habilidade = arma_habilidade

        self.eh_jogador      = eh_jogador
        self.incapacitado    = False

    def rolar_ataque(self):
        d100 = random.randint(1, 100)
        classe, cor = classificar_rolagem(d100, self.arma_habilidade)
        return d100, classe, cor

    def rolar_esquiva(self):
        d100 = random.randint(1, 100)
        classe, cor = classificar_rolagem(d100, self.esquiva)
        return d100, classe, cor

    def calcular_dano(self, classe_ataque):
        partes = self.arma_dano.split("d")
        qtd    = int(partes[0])
        faces  = int(partes[1])
        dano   = sum(random.randint(1, faces) for _ in range(qtd))
        db_val = rolar_db(self.DB)
        if classe_ataque in ("SUCESSO EXTREMO", "SUCESSO CRITICO"):
            dano = dano * 2 + max(0, db_val)
        else:
            dano = max(1, dano + db_val)
        return dano

    def receber_dano(self, dano):
        self.HP = max(0, self.HP - dano)
        if self.HP == 0:
            self.incapacitado = True

    def perder_sanidade(self, perda):
        self.SAN = max(0, self.SAN - perda)

    def esta_vivo(self):
        return self.HP > 0

    @property
    def porcentagem_hp(self):
        return self.HP / self.HP_MAX

    @property
    def porcentagem_san(self):
        return self.SAN / self.SAN_MAX if self.SAN_MAX > 0 else 0


# ══════════════════════════════════════════════════════════════
# FÁBRICA DE INIMIGOS
# ══════════════════════════════════════════════════════════════

INIMIGOS_PRESET = {
    "Cultista": lambda: Personagem(
        "Cultista", for_=50, con=50, tam=60, des=50,
        int_=50, pod=40, apl=40,
        arma_nome="Faca", arma_dano="1d4", arma_habilidade=40,
        eh_jogador=False,
    ),
    "Policial": lambda: Personagem(
        "Policial", for_=60, con=65, tam=70, des=55,
        int_=55, pod=50, apl=50,
        arma_nome="Pistola .38", arma_dano="1d10", arma_habilidade=55,
        eh_jogador=False,
    ),
    "Ghoul": lambda: Personagem(
        "Ghoul", for_=80, con=70, tam=65, des=60,
        int_=30, pod=50, apl=20, hp=14,
        arma_nome="Garras", arma_dano="2d6", arma_habilidade=65,
        eh_jogador=False,
    ),
    "Deep One": lambda: Personagem(
        "Deep One", for_=90, con=80, tam=80, des=50,
        int_=60, pod=60, apl=30, hp=16,
        arma_nome="Garras+Mordida", arma_dano="2d8", arma_habilidade=70,
        eh_jogador=False,
    ),
    "Shoggoth": lambda: Personagem(
        "Shoggoth", for_=150, con=120, tam=140, des=40,
        int_=20, pod=50, apl=0, hp=30,
        arma_nome="Pseudopode", arma_dano="3d6", arma_habilidade=60,
        eh_jogador=False,
    ),
}


# ══════════════════════════════════════════════════════════════
# LOG DE COMBATE
# ══════════════════════════════════════════════════════════════

class LogCombate:
    def __init__(self, max_linhas=14):
        self.linhas = []
        self.max    = max_linhas

    def add(self, texto, cor=COR_LOG_INFO):
        self.linhas.append((texto, cor))
        if len(self.linhas) > self.max:
            self.linhas.pop(0)

    def separador(self):
        self.add("─" * 52, COR_DESTAQUE)


# ══════════════════════════════════════════════════════════════
# ESTADO DO COMBATE
# ══════════════════════════════════════════════════════════════

class EstadoCombate:
    def __init__(self):
        self.fase            = "selecionar_inimigo"
        self.jogador         = None
        self.inimigo         = None
        self.turno           = 1
        self.log             = LogCombate()
        self.aguardando      = False
        self.encerrado       = False
        self.resultado       = ""
        self.ficha_carregada = False
        self._criar_jogador_padrao()

    def _criar_jogador_padrao(self):
        ficha = carregar_investigador_json()
        if ficha:
            self.jogador         = personagem_de_ficha(ficha)
            self.ficha_carregada = True
        else:
            self.jogador         = Personagem(
                nome="Investigador", for_=60, con=55, tam=65,
                des=60, int_=70, pod=55, apl=60,
                arma_nome="Revolver .38", arma_dano="1d10",
                arma_habilidade=50, eh_jogador=True,
            )
            self.ficha_carregada = False

    def iniciar_combate(self, nome_inimigo):
        self.inimigo = INIMIGOS_PRESET[nome_inimigo]()
        self.turno   = 1
        self.fase    = "combate"
        self.log.add(f"== ENCONTRO: {self.inimigo.nome.upper()} ==", COR_OURO)
        self.log.add(
            f"{self.inimigo.nome} surge das sombras!  (HP:{self.inimigo.HP})",
            COR_ACENTO,
        )
        self._determinar_iniciativa()

    def _determinar_iniciativa(self):
        j_ini = random.randint(1, 6) + self.jogador.DES // 10
        i_ini = random.randint(1, 6) + self.inimigo.DES  // 10
        if j_ini >= i_ini:
            self.log.add(
                f"Iniciativa: VOCE age primeiro! ({j_ini} vs {i_ini})", COR_VERDE)
            self.aguardando = True
        else:
            self.log.add(
                f"Iniciativa: {self.inimigo.nome} age primeiro! ({i_ini} vs {j_ini})",
                COR_ACENTO,
            )
            self._turno_inimigo()
            self.aguardando = True

    def acao_jogador(self, acao):
        if not self.aguardando or self.encerrado:
            return

        self.aguardando = False
        self.log.separador()
        self.log.add(f"[Rodada {self.turno}] Sua acao: {acao.upper()}", COR_TEXTO)

        if acao == "fugir":
            self.log.add("Voce recua e foge do combate!", COR_AMARELO)
            self._perda_san_por_fuga()
            self._encerrar("fuga")
            return

        if acao in ("atacar", "agressivo"):
            multiplicador  = 1.2 if acao == "agressivo" else 1.0
            habilidade_mod = min(99, int(self.jogador.arma_habilidade * multiplicador))
            d100, _, _     = self.jogador.rolar_ataque()
            classe, cor    = classificar_rolagem(d100, habilidade_mod)

            self.log.add(
                f"  Ataque ({self.jogador.arma_nome}): {d100}/{habilidade_mod}%  -> {classe}",
                cor,
            )

            if "SUCESSO" in classe:
                esq_d100, esq_classe, esq_cor = self.inimigo.rolar_esquiva()
                self.log.add(
                    f"  {self.inimigo.nome} esquiva: {esq_d100}/{self.inimigo.esquiva}%"
                    f"  -> {esq_classe}",
                    esq_cor,
                )
                if "SUCESSO" not in esq_classe:
                    dano = self.jogador.calcular_dano(classe)
                    self.inimigo.receber_dano(dano)
                    self.log.add(
                        f"  DANO: {dano}  "
                        f"(HP inimigo: {self.inimigo.HP}/{self.inimigo.HP_MAX})",
                        COR_LOG_DANO,
                    )
                else:
                    self.log.add("  Ataque esquivado!", COR_LOG_FALHA)
            else:
                self.log.add("  Ataque falhou!", COR_LOG_FALHA)

        elif acao == "esquivar":
            self.log.add(
                "Voce se prepara para esquivar do proximo ataque.", COR_VERDE)

        if not self.inimigo.esta_vivo():
            self._vitoria()
            return

        self._turno_inimigo()

        if not self.jogador.esta_vivo():
            self._derrota()
            return

        self.turno += 1
        self.aguardando = True

    def _turno_inimigo(self):
        d100, classe, cor = self.inimigo.rolar_ataque()
        self.log.add(
            f"  {self.inimigo.nome} ataca: {d100}/{self.inimigo.arma_habilidade}%"
            f"  -> {classe}",
            cor,
        )

        if "SUCESSO" in classe:
            esq_d100, esq_classe, esq_cor = self.jogador.rolar_esquiva()
            self.log.add(
                f"  Sua esquiva: {esq_d100}/{self.jogador.esquiva}%  -> {esq_classe}",
                esq_cor,
            )
            if "SUCESSO" not in esq_classe:
                dano     = self.inimigo.calcular_dano(classe)
                san_loss = random.randint(0, 1)
                self.jogador.receber_dano(dano)
                if san_loss:
                    self.jogador.perder_sanidade(san_loss)
                self.log.add(
                    f"  DANO recebido: {dano}"
                    f"  (HP: {self.jogador.HP}/{self.jogador.HP_MAX})",
                    COR_LOG_DANO,
                )
            else:
                self.log.add("  Voce esquivou!", COR_LOG_SUCESSO)
        else:
            self.log.add(f"  {self.inimigo.nome} errou!", COR_LOG_FALHA)

    def _vitoria(self):
        san_perda = random.randint(1, 3)
        self.jogador.perder_sanidade(san_perda)
        self.log.separador()
        self.log.add(f"VITORIA! {self.inimigo.nome} foi derrotado!", COR_VERDE)
        self.log.add(
            f"  Perda de Sanidade: -{san_perda} (testemunhar violencia)", COR_ROXO)
        self._encerrar("vitoria")

    def _derrota(self):
        self.log.separador()
        self.log.add("DERROTA! Voce foi incapacitado...", COR_VERMELHO)
        self._encerrar("derrota")

    def _perda_san_por_fuga(self):
        san_perda = random.randint(0, 2)
        if san_perda:
            self.jogador.perder_sanidade(san_perda)
            self.log.add(f"  Perda de Sanidade pela fuga: -{san_perda}", COR_ROXO)

    def _encerrar(self, resultado):
        self.encerrado  = True
        self.resultado  = resultado
        self.fase       = "fim"
        self.aguardando = False


# ══════════════════════════════════════════════════════════════
# INTERFACE GRÁFICA
# ══════════════════════════════════════════════════════════════

def barra(superficie, x, y, w, h, valor, maximo, cor_cheio, cor_vazio=(40, 40, 60)):
    pygame.draw.rect(superficie, cor_vazio, (x, y, w, h), border_radius=4)
    if maximo > 0:
        fill = int(w * (valor / maximo))
        if fill > 0:
            pygame.draw.rect(superficie, cor_cheio, (x, y, fill, h), border_radius=4)
    pygame.draw.rect(superficie, (80, 80, 100), (x, y, w, h), 1, border_radius=4)


def painel(superficie, x, y, w, h, cor=COR_PAINEL, borda=COR_DESTAQUE):
    pygame.draw.rect(superficie, cor, (x, y, w, h), border_radius=8)
    pygame.draw.rect(superficie, borda, (x, y, w, h), 1, border_radius=8)


def texto_sombra(surf, txt, fonte, cor, x, y, centralizar=False):
    s  = fonte.render(txt, True, (0, 0, 0))
    s2 = fonte.render(txt, True, cor)
    r  = s2.get_rect()
    if centralizar:
        r.centerx = x
        r.y = y
    else:
        r.x = x
        r.y = y
    surf.blit(s,  (r.x + 1, r.y + 1))
    surf.blit(s2, r)


def desenhar_ficha(surf, personagem, x, y, w=240):
    h_painel = 130
    painel(surf, x, y, w, h_painel)

    nome_cor = COR_VERDE if personagem.eh_jogador else COR_ACENTO
    texto_sombra(surf, personagem.nome, fn_grande, nome_cor, x + 10, y + 8)

    hp_cor = (
        COR_VERDE   if personagem.porcentagem_hp > 0.5  else
        COR_AMARELO if personagem.porcentagem_hp > 0.25 else
        COR_VERMELHO
    )
    texto_sombra(
        surf, f"HP  {personagem.HP}/{personagem.HP_MAX}",
        fn_normal, hp_cor, x + 10, y + 35,
    )
    barra(surf, x + 10, y + 52, w - 20, 10,
          personagem.HP, personagem.HP_MAX, hp_cor)

    if personagem.eh_jogador:
        san_cor = COR_ROXO if personagem.porcentagem_san < 0.4 else COR_TEXTO_DIM
        texto_sombra(
            surf, f"SAN {personagem.SAN}/{personagem.SAN_MAX}",
            fn_normal, san_cor, x + 10, y + 70,
        )
        barra(surf, x + 10, y + 87, w - 20, 10,
              personagem.SAN, personagem.SAN_MAX, san_cor)

    texto_sombra(
        surf,
        f"Arma: {personagem.arma_nome} ({personagem.arma_dano})",
        fn_pequena, COR_TEXTO_DIM, x + 10, y + 107,
    )


def desenhar_log(surf, log, x, y, w, h):
    painel(surf, x, y, w, h, cor=(18, 25, 50))
    titulo = fn_pequena.render("◈ LOG DE COMBATE", True, COR_OURO)
    surf.blit(titulo, (x + 8, y + 6))
    pygame.draw.line(surf, COR_DESTAQUE, (x + 8, y + 22), (x + w - 8, y + 22), 1)

    espaco = 16
    y_cur  = y + 28
    for txt, cor in log.linhas:
        if y_cur + espaco > y + h - 4:
            break
        s = fn_pequena.render(txt, True, cor)
        surf.blit(s, (x + 8, y_cur))
        y_cur += espaco


def desenhar_acoes(surf, estado, x, y, w):
    acoes = [
        ("A", "Atacar",    COR_ACENTO),
        ("G", "Agressivo", COR_VERMELHO),
        ("E", "Esquivar",  COR_VERDE),
        ("F", "Fugir",     COR_TEXTO_DIM),
    ]

    titulo = fn_pequena.render("► ACOES  (clique ou tecla)", True, COR_OURO)
    surf.blit(titulo, (x, y - 20))

    bw    = (w - 30) // 4
    rects = []
    ativo = estado.aguardando and not estado.encerrado

    for i, (tecla, label, cor) in enumerate(acoes):
        bx      = x + i * (bw + 10)
        cor_btn = cor if ativo else (50, 50, 70)

        alpha_s = pygame.Surface((bw, 42), pygame.SRCALPHA)
        pygame.draw.rect(
            alpha_s, (*cor_btn, 200 if ativo else 80),
            (0, 0, bw, 42), border_radius=6,
        )
        surf.blit(alpha_s, (bx, y))
        pygame.draw.rect(
            surf, cor_btn if ativo else (60, 60, 80),
            (bx, y, bw, 42), 1, border_radius=6,
        )

        cor_txt = COR_TEXTO if ativo else COR_TEXTO_DIM
        t1 = fn_pequena.render(f"[{tecla}]", True, COR_OURO if ativo else COR_TEXTO_DIM)
        t2 = fn_pequena.render(label, True, cor_txt)
        surf.blit(t1, (bx + bw // 2 - t1.get_width() // 2, y + 5))
        surf.blit(t2, (bx + bw // 2 - t2.get_width() // 2, y + 23))
        rects.append(pygame.Rect(bx, y, bw, 42))

    return rects   # [atacar, agressivo, esquivar, fugir]


def desenhar_selecao_inimigo(surf, mouse_pos, estado=None):
    titulo = fn_titulo.render("── SELECIONAR INIMIGO ──", True, COR_OURO)
    surf.blit(titulo, titulo.get_rect(centerx=LARGURA // 2, y=60))

    # Painel do investigador (superior direito)
    if estado is not None and estado.jogador is not None:
        j = estado.jogador
        cor_tag = COR_VERDE if estado.ficha_carregada else COR_TEXTO_DIM
        tag     = "[FICHA]" if estado.ficha_carregada else "[PADRAO]"
        ix, iy, iw, ih = LARGURA - 260, 20, 250, 56
        pygame.draw.rect(surf, COR_PAINEL,   (ix, iy, iw, ih), border_radius=6)
        pygame.draw.rect(surf, cor_tag,      (ix, iy, iw, ih), 1, border_radius=6)
        s1 = fn_pequena.render(f"Investigador  {tag}", True, cor_tag)
        s2 = fn_pequena.render(f"{j.nome}", True, COR_TEXTO)
        s3 = fn_pequena.render(
            f"HP:{j.HP_MAX}  SAN:{j.SAN}  {j.arma_nome}({j.arma_habilidade}%)",
            True, COR_TEXTO_DIM,
        )
        surf.blit(s1, (ix + 6, iy + 4))
        surf.blit(s2, (ix + 6, iy + 18))
        surf.blit(s3, (ix + 6, iy + 34))

    sub = fn_normal.render("Escolha o adversario para o encontro:", True, COR_TEXTO_DIM)
    surf.blit(sub, sub.get_rect(centerx=LARGURA // 2, y=110))

    nomes   = list(INIMIGOS_PRESET.keys())
    rects   = []
    bw, bh  = 260, 50
    colunas = 2

    for i, nome in enumerate(nomes):
        col = i % colunas
        row = i // colunas
        bx  = LARGURA // 2 - (bw * colunas + 20) // 2 + col * (bw + 20)
        by  = 160 + row * (bh + 14)
        r   = pygame.Rect(bx, by, bw, bh)
        hover = r.collidepoint(mouse_pos)

        pygame.draw.rect(surf, COR_ROXO if hover else COR_DESTAQUE, r, border_radius=8)
        pygame.draw.rect(surf, COR_ACENTO if hover else COR_ROXO, r, 1, border_radius=8)

        tmp    = INIMIGOS_PRESET[nome]()
        n_surf = fn_normal.render(nome, True, COR_TEXTO)
        inf    = fn_pequena.render(
            f"HP:{tmp.HP_MAX}  DEX:{tmp.DES}  {tmp.arma_nome} ({tmp.arma_dano})",
            True, COR_TEXTO_DIM,
        )
        surf.blit(n_surf, n_surf.get_rect(centerx=r.centerx, y=r.y + 8))
        surf.blit(inf,    inf.get_rect(centerx=r.centerx,    y=r.y + 28))
        rects.append((r, nome))

    # Botão voltar
    r_voltar = pygame.Rect(LARGURA // 2 - 80, ALTURA - 70, 160, 38)
    hover_v  = r_voltar.collidepoint(mouse_pos)
    pygame.draw.rect(surf, COR_ACENTO if hover_v else (60, 30, 40), r_voltar, border_radius=8)
    pygame.draw.rect(surf, COR_ACENTO, r_voltar, 1, border_radius=8)
    s = fn_normal.render("[ESC] Voltar", True, COR_TEXTO)
    surf.blit(s, s.get_rect(center=r_voltar.center))

    return rects, r_voltar


def desenhar_tela_fim(surf, estado):
    overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    cor_res = {"vitoria": COR_VERDE,   "derrota": COR_VERMELHO, "fuga": COR_AMARELO}
    txt_res = {"vitoria": "VITORIA!",  "derrota": "DERROTADO...", "fuga": "RECUOU!"}

    res = estado.resultado
    cor = cor_res.get(res, COR_TEXTO)
    txt = txt_res.get(res, "FIM")

    s = fn_titulo.render(txt, True, cor)
    surf.blit(s, s.get_rect(centerx=LARGURA // 2, centery=ALTURA // 2 - 40))

    j    = estado.jogador
    info = [
        f"HP Final:        {j.HP}/{j.HP_MAX}",
        f"Sanidade Final:  {j.SAN}/{j.SAN_MAX}",
        f"Rodadas:         {estado.turno}",
    ]
    for k, linha in enumerate(info):
        s2 = fn_normal.render(linha, True, COR_TEXTO_DIM)
        surf.blit(s2, s2.get_rect(centerx=LARGURA // 2, centery=ALTURA // 2 + 10 + k * 22))

    r_novo = pygame.Rect(LARGURA // 2 - 170, ALTURA // 2 + 90, 150, 38)
    r_menu = pygame.Rect(LARGURA // 2 + 20,  ALTURA // 2 + 90, 150, 38)

    pygame.draw.rect(surf, COR_VERDE,  r_novo, border_radius=8)
    pygame.draw.rect(surf, COR_ACENTO, r_menu, border_radius=8)

    t_novo = fn_normal.render("Novo Combate",   True, COR_FUNDO)
    t_menu = fn_normal.render("Menu Principal", True, COR_TEXTO)
    surf.blit(t_novo, t_novo.get_rect(center=r_novo.center))
    surf.blit(t_menu, t_menu.get_rect(center=r_menu.center))

    hint = fn_pequena.render("[R] Novo Combate   [ESC] Menu", True, COR_TEXTO_DIM)
    surf.blit(hint, hint.get_rect(centerx=LARGURA // 2, y=ALTURA // 2 + 140))

    return r_novo, r_menu


# ══════════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    global LARGURA, ALTURA, tela

    estado     = EstadoCombate()
    acoes_mapa = ["atacar", "agressivo", "esquivar", "fugir"]
    rects_acao = []
    rects_inim = []
    r_voltar   = None
    r_novo     = None
    r_menu     = None

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.VIDEORESIZE:
                LARGURA, ALTURA = event.w, event.h
                tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)

            # ── Seleção de inimigo ───────────────────────
            if estado.fase == "selecionar_inimigo":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for r, nome in rects_inim:
                        if r.collidepoint(mouse_pos):
                            estado.iniciar_combate(nome)
                    if r_voltar and r_voltar.collidepoint(mouse_pos):
                        pygame.quit()
                        sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            # ── Combate ──────────────────────────────────
            elif estado.fase == "combate":
                if event.type == pygame.KEYDOWN:
                    mapa = {
                        pygame.K_a: "atacar",
                        pygame.K_g: "agressivo",
                        pygame.K_e: "esquivar",
                        pygame.K_f: "fugir",
                    }
                    if event.key in mapa:
                        estado.acao_jogador(mapa[event.key])

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(rects_acao):
                        if r.collidepoint(mouse_pos):
                            estado.acao_jogador(acoes_mapa[i])

            # ── Fim ───────────────────────────────────────
            elif estado.fase == "fim":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if r_novo and r_novo.collidepoint(mouse_pos):
                        estado = EstadoCombate()
                    if r_menu and r_menu.collidepoint(mouse_pos):
                        pygame.quit()
                        sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        estado = EstadoCombate()
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

        # ══ DESENHO ══════════════════════════════════════
        tela.fill(COR_FUNDO)

        if estado.fase == "selecionar_inimigo":
            rects_inim, r_voltar = desenhar_selecao_inimigo(tela, mouse_pos, estado)

        else:
            # Fichas
            desenhar_ficha(tela, estado.jogador,  20,  20, 260)
            if estado.inimigo:
                desenhar_ficha(tela, estado.inimigo, LARGURA - 280, 20, 260)

            # VS central
            vs = fn_titulo.render("VS", True, COR_ACENTO)
            tela.blit(vs, vs.get_rect(centerx=LARGURA // 2, y=50))

            # Log
            log_y = 170
            log_h = ALTURA - log_y - 110
            desenhar_log(tela, estado.log, 20, log_y, LARGURA - 40, log_h)

            # Ações
            rects_acao = desenhar_acoes(tela, estado, 20, ALTURA - 90, LARGURA - 40)

            # Status de turno
            msg = "Aguardando sua acao..." if estado.aguardando else "Processando..."
            turno_txt = fn_pequena.render(
                f"Rodada {estado.turno}  |  {msg}", True, COR_OURO)
            tela.blit(turno_txt, turno_txt.get_rect(centerx=LARGURA // 2, y=145))

        if estado.fase == "fim":
            r_novo, r_menu = desenhar_tela_fim(tela, estado)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()

