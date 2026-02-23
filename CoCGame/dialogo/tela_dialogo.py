"""
dialogo/tela_dialogo.py — Sistema de diálogo para encontros com NPCs humanos.

Aparece quando o investigador se aproxima de um inimigo do tipo "humano".
Em CoC 7e, humanos quase sempre têm alternativas ao combate.

Três opções:
  [C]  Conversar      — bate-papo sobre assuntos do Rio, 1923
  [A]  Ameaçar        — teste de Intimidação; sucesso = NPC foge
                        falha = NPC luta furioso (+Força)
  [F]  Partir pra porrada — vai direto ao combate por turnos

Retorna uma string de resultado:
  "ignorou"         — NPC foi apaziguado, deixa passar
  "fugiu"           — NPC correu com o rabo entre as pernas
  "combate"         — NPC não curtiu e quer brigar
  "combate_furioso" — NPC foi humilhado na ameaça, luta com raiva

Uso:
    from dialogo.tela_dialogo import TelaDialogo
    resultado = TelaDialogo(screen, jogador, npc).run()
"""
from __future__ import annotations

import random
import textwrap
from typing import Optional

import pygame

from gerenciador_assets import get_font, garantir_fontes


# ══════════════════════════════════════════════════════════════
# CORES
# ══════════════════════════════════════════════════════════════

C_OVERLAY  = (0,   0,   0,   180)    # fundo semitransparente
C_PAINEL   = (18,  25,  45,  255)
C_BORDA    = (60,  80, 130,  255)
C_TITULO   = (212, 168,  67,  255)   # ouro
C_TEXTO    = (238, 226, 220,  255)
C_DIM      = (140, 130, 120,  255)
C_ACENTO   = (233,  69,  96,  255)   # vermelho
C_VERDE    = ( 78, 204, 163,  255)
C_ROXO     = (130,  70, 180,  255)
C_AMARELO  = (240, 210,  80,  255)
C_FUGA     = ( 90, 190, 100,  255)
C_PORRADA  = (200,  60,  60,  255)

HOVER_SHIFT = 30   # quanto clarear o botão em hover


# ══════════════════════════════════════════════════════════════
# CONTEÚDO DE DIÁLOGO — RIO DE JANEIRO, 1923
# ══════════════════════════════════════════════════════════════

# Saudações do NPC ao ser abordado (indexado por nome parcial)
_SAUDACOES: dict[str, list[str]] = {
    "Cultista Corbitt": [
        "Você não devia estar aqui. Este lugar pertence ao Mestre.",
        "Saia antes que eu seja obrigado a tomar providências.",
    ],
    "Cultista Ritualista": [
        "O ritual não pode ser interrompido! Vá embora, intruso!",
        "Você profana um ato sagrado. Retire-se imediatamente.",
    ],
    "Cultista": [
        "Para! Quem te deixou entrar aqui?",
        "Intruso! Este lugar é proibido aos de fora.",
        "O que você quer? Este não é lugar para estranhos.",
    ],
    "Guarda": [
        "Alto aí! Identifique-se!",
        "Zona restrita. Dê meia-volta.",
    ],
}
_SAUDACAO_PADRAO = [
    "O que você faz aqui?",
    "Não deveria estar aqui.",
    "Para. O que você quer?",
]

# Tópicos para Conversar — o investigador abre o assunto, o NPC reage
_TOPICOS: list[dict] = [
    {
        "tema":    "Futebol",
        "jogador": "Viu o Vasco no fim de semana? Ganharam o campeonato carioca, histórico!",
        "npc_ok": [
            "Pois é... aquele time com os negros e mestiços. O pessoal do clube não gostou nada, "
            "mas ganhou, que seja. Dinheiro não tem cor.",
            "Vasco campeão! Meu filho chorou de alegria. É torcedor desde criança.",
            "Bah, futebol... a única coisa decente nesta cidade ultimamente.",
        ],
        "npc_desconfiado": [
            "Futebol, futebol... Espera. Você tá tentando me distrair, né?",
        ],
    },
    {
        "tema":    "Rádio",
        "jogador": "Escutou a Rádio Sociedade do Rio? Inaugurou esse ano, é uma maravilha!",
        "npc_ok": [
            "Nunca ouvi, mas meu patrão tem um aparelho. Diz que é o futuro.",
            "Rádio! O vizinho comprou um. A mulher dele fica horas ouvindo músicas.",
            "Isso é coisa de rico. Aqui a gente se vira com jornal mesmo.",
        ],
        "npc_desconfiado": [
            "Rádio? Tô pouco me importando com isso agora.",
        ],
    },
    {
        "tema":    "Calor",
        "jogador": "Meu Deus, que calor! Tá insuportável esse outubro no Rio.",
        "npc_ok": [
            "Nem me fale. Ontem quase desmaiou aqui dentro.",
            "É o que digo: esse calor não é natural. Algo tá errado nesse inverno.",
            "Cada ano pior. E sem uma cerveja gelada pra aguentar.",
        ],
        "npc_desconfiado": [
            "Hmm... o calor, claro. Ei, você não tem nada melhor pra fazer aqui?",
        ],
    },
    {
        "tema":    "Tenentismo",
        "jogador": "Soube dos tenentes? O Prestes tá mobilizando o sul do país.",
        "npc_ok": [
            "Esses militares... tentaram derrubar o governo no ano passado. Os 18 do Forte, "
            "marchando pela praia. Corajosos, mas loucos.",
            "Política, política. O Brasil nunca muda. Só muda quem manda.",
            "O Prestes? Esse vai longe. Ou vai preso, um dos dois.",
        ],
        "npc_desconfiado": [
            "Política agora? Você tá com algum interesse nisso tudo aqui, não tá?",
        ],
    },
    {
        "tema":    "Enchentes",
        "jogador": "As enchentes do mês passado foram terríveis. Perdeu alguma coisa?",
        "npc_ok": [
            "Perdi o tapete da sala inteiro. A água chegou no joelho.",
            "As enchentes tão cada vez piores. Dizem que é por causa das derrubadas no morro.",
            "Tive sorte. Moro no segundo andar. Os da rua de baixo perderam tudo.",
        ],
        "npc_desconfiado": [
            "Enchentes... Ei, por que você me pergunta isso aqui?",
        ],
    },
    {
        "tema":    "Café",
        "jogador": "O preço do café subiu de novo. Tá ficando caro até pra beber em casa.",
        "npc_ok": [
            "Subiu, é. E o fazendeiro de São Paulo fica rico enquanto a gente se vira.",
            "Sempre foi assim. Quem planta não fica com o dinheiro.",
            "Que saudade de quando um quilo custava barato. Os tempos mudam.",
        ],
        "npc_desconfiado": [
            "Café? Eu como, eu não planto. Ei, você veio aqui falar de café mesmo?",
        ],
    },
    {
        "tema":    "Bonde",
        "jogador": "Esse bonde novo da Light tá uma delícia. Rápido e fresco!",
        "npc_ok": [
            "Ah, o bonde elétrico! Muito melhor que o de burro, isso é fato.",
            "Pegue o bonde da manhã: fica cheio mas vai rápido. Já andei hoje.",
            "Progresso, progredir progresso. Daqui a pouco vai ter bonde até no morro.",
        ],
        "npc_desconfiado": [
            "Bonde... você veio de longe pra falar de bonde?",
        ],
    },
    {
        "tema":    "Jornal",
        "jogador": "Leu o jornal hoje? Dizem que tem coisa estranha acontecendo na cidade.",
        "npc_ok": [
            "Li sim. Terceiro desaparecimento esse mês. A polícia não acha nada.",
            "O jornal sempre exagera. Embora... desta vez eu mesmo vi uma coisa esquisita.",
            "Não leio jornal, traz angústia. Mas minha vizinha me contou tudo mesmo assim.",
        ],
        "npc_desconfiado": [
            "Jornal... Peraí. Você está investigando alguma coisa, não tá?",
        ],
    },
    {
        "tema":    "Carnaval",
        "jogador": "Já pensando no carnaval do ano que vem? As escolas de samba tão animadas.",
        "npc_ok": [
            "Carnaval! A única época em que o Rio vive de verdade.",
            "Minha filha vai desfilar pela primeira vez. Tô todo orgulhoso.",
            "Esse ano eu vou sim. Ano passado trabalhei... nunca mais.",
        ],
        "npc_desconfiado": [
            "Carnaval agora? Aqui? Que papo mais estranho...",
        ],
    },
    {
        "tema":    "Cinema",
        "jogador": "Viu o filme novo do Chaplin? Tá passando no Cine Pathé.",
        "npc_ok": [
            "Chaplin! Aquele homenzinho do bigode. Rir na miséria, isso sim é arte.",
            "Fui semana passada com a namorada. Ela gargalhou tanto que engoliu balas.",
            "Cinema é coisa boa. Esqueço os problemas por duas horas.",
        ],
        "npc_desconfiado": [
            "Cinema... Olha, você é simpático, mas o que você realmente quer aqui?",
        ],
    },
]

# Frases de ameaça do investigador (usadas na tela de ameaça)
_FRASES_AMEACA = [
    "Me deixa em paz, se não vou rasgar teu moletom com você dentro.",
    "Sai do meu caminho antes que eu te mostre como é a dor de verdade.",
    "Última chance. Suma daqui antes que eu mude de ideia sobre te deixar vivo.",
    "Olha nos meus olhos. Você quer mesmo testar isso?",
]

# Respostas do NPC ao ser ameaçado — sucesso (NPC foge)
_AMEACA_SUCESSO: list[str] = [
    "F-fica comigo não... não tenho nada a ver com isso não! Sou embora!",
    "Tá bem, tá bem! Não precisa disso! Vou sumindo...",
    "Mãe do céu... pode ficar com o corredor todo! Estou fora!",
    "Ok! Ok! Sem briga! Só quero ir embora com minha pele intacta!",
]

# Respostas do NPC ao ser ameaçado — falha (NPC fica furioso)
_AMEACA_FALHA: list[str] = [
    "Você me ameaça?! A MIM?! Vai se arrepender disso, seus ossos vão trincar!",
    "Hahaha! Acha que me assusta? Vou te mostrar quem tem MEDO aqui!",
    "Essa foi a pior ideia da sua vida. Preparado pra morrer?",
    "Ameaça?! Tô tremendo de raiva, não de medo! VEM!",
]

# Frases de porrada direta
_FRASES_PORRADA = [
    "Pois morra, seu merda.",
    "Acabou o papo.",
    "Nem vou perder tempo.",
]


# ══════════════════════════════════════════════════════════════
# TELA DE DIÁLOGO
# ══════════════════════════════════════════════════════════════

class TelaDialogo:
    """
    Tela modal de diálogo para encontros com NPCs humanos.

    Parâmetros:
        screen  — superfície pygame principal
        jogador — Jogador (usado para checar perícia Intimidação)
        npc     — Inimigo ou Entidade com campo .nome
        contexto — string opcional descrevendo o local do encontro
    """

    PANEL_W = 660
    PANEL_H = 330

    def __init__(self, screen: pygame.Surface, jogador,
                 npc, contexto: str = ""):
        self.screen   = screen
        self.jogador  = jogador
        self.npc      = npc
        self.contexto = contexto
        self.clock    = pygame.time.Clock()

        garantir_fontes()
        self.f_titulo  = get_font("titulo",    20)
        self.f_normal  = get_font("hud",       16)
        self.f_pequeno = get_font("hud",       13)
        self.f_botao   = get_font("titulo",    16)

        # Snapshot do background (para o overlay)
        self._bg = screen.copy()

        # Overlay pré-criado uma vez (evita alocar Surface a cada frame)
        self._overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self._overlay.fill(C_OVERLAY)

        # Tópico selecionado para esta instância
        self._topico = random.choice(_TOPICOS)

        # Saudação cacheada — gerada UMA VEZ, não a cada frame (fix flickering)
        self._saudacao = self._saudacao_npc()

        # Estado: "escolha" → "conversa" → "resultado"
        self._estado   = "escolha"
        self._linhas_conversa: list[tuple[str, tuple]] = []   # (texto, cor)
        self._resultado_texto  = ""
        self._resultado_cor    = C_TEXTO

    # ── Helpers de layout ────────────────────────────────────

    def _panel_rect(self) -> pygame.Rect:
        sw, sh = self.screen.get_size()
        x = (sw - self.PANEL_W) // 2
        y = (sh - self.PANEL_H) // 2
        return pygame.Rect(x, y, self.PANEL_W, self.PANEL_H)

    def _saudacao_npc(self) -> str:
        nome = self.npc.nome
        for chave, frases in _SAUDACOES.items():
            if chave.lower() in nome.lower():
                return random.choice(frases)
        return random.choice(_SAUDACAO_PADRAO)

    def _intimidacao_inv(self) -> int:
        pericias = getattr(self.jogador, "pericias", {})
        return pericias.get("Intimidação", 15)

    # ── Renderização ─────────────────────────────────────────

    def _desenhar(self, hover: Optional[str] = None):
        # Fundo + overlay pré-criado (sem alocar Surface a cada frame)
        self.screen.blit(self._bg, (0, 0))
        self.screen.blit(self._overlay, (0, 0))

        r = self._panel_rect()

        # Sombra
        sombra = r.inflate(8, 8)
        s = pygame.Surface((sombra.w, sombra.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 140), s.get_rect(), border_radius=14)
        self.screen.blit(s, sombra.topleft)

        # Painel
        pygame.draw.rect(self.screen, C_PAINEL, r, border_radius=10)
        pygame.draw.rect(self.screen, C_BORDA,  r, width=2, border_radius=10)

        x0 = r.x + 22
        y  = r.y + 16

        # ── Cabeçalho ────────────────────────────────────────
        hp_npc  = getattr(self.npc, "hp", "?")
        disp    = getattr(self.npc, "disposicao", "Hostil")
        titulo  = f"⚠  ENCONTRO  —  {self.npc.nome}"
        sub     = f"HP {hp_npc}  •  Disposição: {disp}"

        self.screen.blit(
            self.f_titulo.render(titulo, True, C_TITULO),
            (x0, y),
        )
        y += 28
        self.screen.blit(
            self.f_pequeno.render(sub, True, C_DIM),
            (x0, y),
        )

        # Separador
        y += 20
        pygame.draw.line(self.screen, C_BORDA,
                         (r.x + 12, y), (r.right - 12, y))
        y += 12

        if self._estado == "escolha":
            self._desenhar_escolha(r, x0, y, hover)
        elif self._estado in ("conversa", "resultado"):
            self._desenhar_conversa(r, x0, y)

    def _desenhar_escolha(self, r, x0, y, hover):
        # Saudação do NPC — usa cache para não chamar random.choice() a cada frame
        saud = self._saudacao
        for linha in textwrap.wrap(f'"{saud}"', 62):
            self.screen.blit(
                self.f_normal.render(linha, True, C_TEXTO),
                (x0, y),
            )
            y += 22

        if self.contexto:
            y += 4
            for linha in textwrap.wrap(self.contexto, 62):
                self.screen.blit(
                    self.f_pequeno.render(linha, True, C_DIM),
                    (x0, y),
                )
                y += 18

        # Separador
        y = r.bottom - 108
        pygame.draw.line(self.screen, C_BORDA,
                         (r.x + 12, y), (r.right - 12, y))
        y += 10

        intim = self._intimidacao_inv()
        opcoes = [
            ("C", f"[C]  CONVERSAR          — 'Ei, viu o jogo do Vasco?'",            C_VERDE,   "conversar"),
            ("A", f"[A]  AMEAÇAR  (INT {intim:02d}%)  — 'Me deixa em paz ou vai se arrepender'", C_AMARELO, "ameacar"),
            ("F", f"[F]  PARTIR PRA PORRADA — 'Pois morra, seu merda!'",              C_PORRADA, "porrada"),
        ]

        for tecla, txt, cor, key in opcoes:
            ativo = hover == key
            cor_real = tuple(min(255, c + HOVER_SHIFT) for c in cor) if ativo else cor
            surf = self.f_botao.render(txt, True, cor_real)
            self.screen.blit(surf, (x0, y))
            y += 28

    def _desenhar_conversa(self, r, x0, y):
        for texto, cor in self._linhas_conversa:
            for linha in textwrap.wrap(texto, 60):
                s = self.f_normal.render(linha, True, cor)
                self.screen.blit(s, (x0, y))
                y += 22

        if self._estado == "resultado":
            y += 10
            pygame.draw.line(self.screen, C_BORDA,
                             (r.x + 12, y), (r.right - 12, y))
            y += 12
            for linha in textwrap.wrap(self._resultado_texto, 62):
                s = self.f_botao.render(linha, True, self._resultado_cor)
                self.screen.blit(s, (x0, y))
                y += 26

        # Dica de tecla
        dica = "[ Qualquer tecla para continuar ]" if self._estado == "conversa" else ""
        if dica:
            sd = self.f_pequeno.render(dica, True, C_DIM)
            self.screen.blit(sd, sd.get_rect(centerx=r.centerx, bottom=r.bottom - 8))

    # ── Lógica das opções ────────────────────────────────────

    def _fazer_conversar(self) -> str:
        """
        Mostra troca de conversa e determina resultado.
        65% → NPC é apaziguado (ignora)
        35% → NPC desconfia e quer brigar
        Modificado por Charme/Lábia/Persuasão do jogador.
        """
        pericias = getattr(self.jogador, "pericias", {})
        social = max(
            pericias.get("Charme",     15),
            pericias.get("Lábia",      15),
            pericias.get("Persuasão",  15),
        )
        roll = random.randint(1, 100)

        topico = self._topico
        npc_ok = random.choice(topico["npc_ok"])

        self._linhas_conversa = [
            (f"Você: \"{topico['jogador']}\"",  C_VERDE),
        ]

        if roll <= social:
            self._linhas_conversa.append(
                (f"{self.npc.nome}: \"{npc_ok}\"", C_TEXTO)
            )
            self._linhas_conversa.append(
                ("... ele olha para o lado e acena com a cabeça. "
                 "Você aproveita e passa.", C_DIM)
            )
            return "ignorou"
        else:
            desconfiado = random.choice(topico["npc_desconfiado"])
            self._linhas_conversa.append(
                (f"{self.npc.nome}: \"{desconfiado}\"", C_ACENTO)
            )
            self._linhas_conversa.append(
                ("Ele avança. A conversa não deu em nada.", C_DIM)
            )
            return "combate"

    def _fazer_ameacar(self) -> str:
        """
        Teste de Intimidação (d100 vs habilidade).
        Sucesso → NPC foge.
        Falha → NPC enlouquece de raiva, luta furioso.
        """
        intim   = self._intimidacao_inv()
        roll    = random.randint(1, 100)
        frase   = random.choice(_FRASES_AMEACA)
        sucesso = roll <= intim

        self._linhas_conversa = [
            (f"Você: \"{frase}\"", C_AMARELO),
            (f"[Intimidação: rolou {roll:02d} vs {intim:02d} — "
             f"{'SUCESSO' if sucesso else 'FALHOU'}]", C_DIM),
        ]

        if sucesso:
            self._linhas_conversa.append(
                (f"{self.npc.nome}: \"{random.choice(_AMEACA_SUCESSO)}\"", C_FUGA)
            )
            return "fugiu"
        else:
            self._linhas_conversa.append(
                (f"{self.npc.nome}: \"{random.choice(_AMEACA_FALHA)}\"", C_PORRADA)
            )
            return "combate_furioso"

    def _fazer_porrada(self) -> str:
        frase = random.choice(_FRASES_PORRADA)
        self._linhas_conversa = [
            (f"Você: \"{frase}\"", C_PORRADA),
            ("Não há mais conversa.", C_DIM),
        ]
        return "combate"

    # ── Textos de resultado ──────────────────────────────────

    _RESULTADO_TEXTOS = {
        "ignorou":         ("✓  O caminho está livre.",                     C_VERDE),
        "fugiu":           ("✓  O inimigo correu. Ameaça neutralizada.",     C_FUGA),
        "combate":         ("✗  Combate iniciado!",                          C_ACENTO),
        "combate_furioso": ("✗  Combate! O inimigo está em FÚRIA! (+Força)", C_PORRADA),
    }

    # ── Loop principal ────────────────────────────────────────

    def run(self) -> str:
        """
        Executa a tela de diálogo e retorna o resultado:
          "ignorou" | "fugiu" | "combate" | "combate_furioso"
        """
        resultado_final = "combate"
        hover: Optional[str] = None

        _KEY_MAP = {
            pygame.K_c: "conversar",
            pygame.K_a: "ameacar",
            pygame.K_f: "porrada",
            pygame.K_1: "conversar",
            pygame.K_2: "ameacar",
            pygame.K_3: "porrada",
        }

        while True:
            self._desenhar(hover if self._estado == "escolha" else None)
            pygame.display.flip()
            self.clock.tick(60)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    import sys; pygame.quit(); sys.exit()

                # ── Estado: escolha de opção ─────────────────
                if self._estado == "escolha":
                    acao: Optional[str] = None
                    if ev.type == pygame.KEYDOWN:
                        acao = _KEY_MAP.get(ev.key)
                    elif ev.type == pygame.MOUSEMOTION:
                        # Calcula hover por posição Y dos botões
                        r   = self._panel_rect()
                        my  = ev.pos[1]
                        y0  = r.bottom - 108 + 10
                        for i, key in enumerate(("conversar", "ameacar", "porrada")):
                            btn_top = y0 + i * 28
                            btn_bot = btn_top + 26
                            if btn_top <= my <= btn_bot:
                                hover = key
                                break
                        else:
                            hover = None
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        r   = self._panel_rect()
                        my  = ev.pos[1]
                        y0  = r.bottom - 108 + 10
                        for i, key in enumerate(("conversar", "ameacar", "porrada")):
                            btn_top = y0 + i * 28
                            btn_bot = btn_top + 26
                            if btn_top <= my <= btn_bot:
                                acao = key
                                break

                    if acao == "conversar":
                        resultado_final = self._fazer_conversar()
                        self._estado = "conversa"
                    elif acao == "ameacar":
                        resultado_final = self._fazer_ameacar()
                        self._estado = "conversa"
                    elif acao == "porrada":
                        resultado_final = self._fazer_porrada()
                        self._estado = "conversa"

                # ── Estado: mostrando a conversa ─────────────
                elif self._estado == "conversa":
                    if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                        txt, cor = self._RESULTADO_TEXTOS.get(
                            resultado_final,
                            ("Fim do diálogo.", C_DIM)
                        )
                        self._resultado_texto = txt
                        self._resultado_cor   = cor
                        self._estado = "resultado"
                        self._desenhar()
                        pygame.display.flip()
                        pygame.time.wait(1400)
                        return resultado_final

        # nunca alcançado, mas por garantia:
        return resultado_final
