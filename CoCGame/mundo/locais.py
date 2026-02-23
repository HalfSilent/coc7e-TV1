"""
mundo/locais.py — Definição dos locais de Arkham, 1923.

Estrutura de navegação TORN-style:
  - Cada Local tem: nome, descrição atmosférica, lista de ações, conexões
  - Ações podem: ir para outro local, entrar numa masmorra, comprar item, etc.
  - Conexões definem quais locais estão acessíveis a partir daqui

Locais de Arkham incluídos:
  rua_central     — Centro da cidade, hub de navegação
  biblioteca      — Biblioteca Orne, pesquisa e pistas
  hospital        — Hospital St. Mary's, cura e informações
  delegacia       — Delegacia, aliados e restrições
  porto           — Porto de Arkham, contrabando e mistério
  docas           — Docas abandonadas, masmorra disponível
  mansao          — Mansão Corbitt, investigação principal
  cemiterio       — Cemitério Silver Gate, ritual e horror
  universidade    — Universidade Miskatonic, professores e tomos
  estalagem       — Estalagem Silver Gate, descanso e boatos
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# ESTRUTURA DE DADOS
# ══════════════════════════════════════════════════════════════

@dataclass
class Acao:
    """Uma ação disponível num local."""
    tecla:    str            # ex: "E", "C", "1"
    texto:    str            # ex: "Examinar prateleiras"
    tipo:     str            # "ir" | "masmorra" | "explorar" | "comprar" | "info" | "descanso" | "pericia"
    destino:  str = ""       # ID do local destino (para tipo "ir") ou ID da masmorra/interior
    descricao: str = ""      # texto descritivo ao executar a ação
    custo_xp:  int = 0       # XP necessário (0 = livre)
    custo_dinheiro: int = 0  # dinheiro necessário (0 = grátis)
    item_necessario: str = ""  # item no inventário necessário (vazio = nenhum)


@dataclass
class Local:
    """Um local de Arkham navegável pelo jogador."""
    id:          str
    nome:        str
    descricao:   str          # texto atmosférico exibido ao entrar
    acoes:       List[Acao] = field(default_factory=list)
    conexoes:    List[str]  = field(default_factory=list)  # IDs de locais acessíveis
    cor:         tuple = (80, 80, 100)                     # cor de fundo do painel
    musica:      str = ""                                  # arquivo de música (futuro)
    hora_fechamento: Optional[int] = None                  # hora em que fecha (None = sempre aberto)
    dica:        str = ""    # dica de controles contextual


# ══════════════════════════════════════════════════════════════
# LOCAIS DE ARKHAM
# ══════════════════════════════════════════════════════════════

LOCAIS: Dict[str, Local] = {}


def _reg(local: Local) -> Local:
    LOCAIS[local.id] = local
    return local


# ── Rua Central ───────────────────────────────────────────────
_reg(Local(
    id="rua_central",
    nome="Rua Central — Arkham, 1923",
    descricao=(
        "A rua principal de Arkham está deserta nesta hora cinzenta. "
        "Lampiões a gás projetam sombras trêmulas nos paralelepípedos molhados. "
        "Um jornal velho rola no vento: 'TERCEIRO DESAPARECIMENTO EM DUAS SEMANAS'. "
        "Você sente olhares das janelas escuras."
    ),
    acoes=[
        Acao("B", "Ir para a Biblioteca",       "ir", destino="biblioteca"),
        Acao("H", "Ir para o Hospital",          "ir", destino="hospital"),
        Acao("D", "Ir para a Delegacia",         "ir", destino="delegacia"),
        Acao("P", "Ir para o Porto",             "ir", destino="porto"),
        Acao("U", "Ir para a Universidade",      "ir", destino="universidade"),
        Acao("E", "Ir para a Estalagem",         "ir", destino="estalagem"),
        Acao("M", "Ir para a Mansão Corbitt",    "ir", destino="mansao",
             descricao="Você sente um calafrio ao se aproximar da mansão abandonada..."),
        Acao("C", "Examinar jornal caído",       "info",
             descricao=(
                 "ARKHAM ADVERTISER, 14 de Outubro de 1923.\n"
                 "'...o Sr. Edward Corbitt foi visto pela última vez há três semanas.\n"
                 "Vizinhos relatam sons estranhos e luzes na mansão vazia de Derby St.'\n"
                 "Uma nota manuscrita no verso: 'eles vêm de baixo das pedras.'"
             )),
    ],
    conexoes=["biblioteca", "hospital", "delegacia", "porto", "universidade",
               "estalagem", "mansao"],
    cor=(40, 45, 55),
    dica="[B/H/D/P/U/E/M] Navegar  [C] Examinar",
))

# ── Biblioteca Orne ───────────────────────────────────────────
_reg(Local(
    id="biblioteca",
    nome="Biblioteca Orne",
    descricao=(
        "Estantes do teto ao chão se estendem em corredores sombrios. "
        "O cheiro de papel velho e poeira permeia o ar. "
        "A bibliotecária, Sra. Marsh, observa você com olhos pálidos e fundos. "
        "Em uma mesa no fundo, alguém deixou um livro aberto com páginas em latim. "
        "O título na capa: 'De Vermis Mysteriis'."
    ),
    acoes=[
        Acao("P", "Pesquisar sobre Corbitt",    "pericia",
             descricao=(
                 "Após horas de pesquisa, você encontra uma escritura datada de 1882.\n"
                 "Walter Corbitt vendeu a alma ao culto 'Irmandade da Pele'.\n"
                 "Seu corpo foi sepultado sob a mansão — mas o contrato nunca venceu."
             )),
        Acao("T", "Examinar 'De Vermis Mysteriis'",  "pericia",
             descricao=(
                 "O livro descreve rituais de invocação. Uma passagem sublinhada:\n"
                 "'...o servo aguarda sob a pedra negra, dormindo mas não morto...'\n"
                 "Teste de Sanidade falhou: -1d3 SAN."
             )),
        Acao("E", "Falar com a Sra. Marsh",     "info",
             descricao=(
                 "A bibliotecária fala em sussurros:\n"
                 "'Aquela mansão esteve fechada desde que o velho morreu.\n"
                 "Os últimos inquilinos saíram correndo de madrugada há três meses.\n"
                 "Disseram que havia algo... nos porões.'"
             )),
        Acao("X", "Explorar o interior",        "explorar",
             destino="biblioteca_interior",
             descricao="Você adentra os corredores escuros entre as estantes."),
        Acao("V", "Voltar à Rua Central",       "ir", destino="rua_central"),
    ],
    conexoes=["rua_central", "universidade"],
    cor=(45, 40, 35),
    hora_fechamento=20,
    dica="[P] Pesquisar  [T] Tomo  [E] Falar  [V] Voltar",
))

# ── Hospital St. Mary's ───────────────────────────────────────
_reg(Local(
    id="hospital",
    nome="Hospital St. Mary's",
    descricao=(
        "O cheiro de éter e desinfetante enche o corredor branco. "
        "Enfermeiras de tocas brancas circulam apressadas. "
        "Em uma maca, um jovem murmura frases sem sentido, olhos vidrados. "
        "O Dr. Hartwell limpa os óculos com ar cansado ao te ver entrar."
    ),
    acoes=[
        Acao("C", "Tratar ferimentos (10 HP)",  "descanso", custo_dinheiro=3,
             descricao="O Dr. Hartwell trata seus ferimentos. +10 HP."),
        Acao("S", "Tratar trauma mental (10 SAN)", "descanso", custo_dinheiro=5,
             descricao="Uma sessão de hipnose. +10 SAN."),
        Acao("F", "Falar com o paciente delirante", "info",
             descricao=(
                 "O jovem te agarra pelo braço, olhos abertos de terror:\n"
                 "'Eles chamam! A voz das pedras! O homem que não dorme...'\n"
                 "Ele perde os sentidos. Na sua mão, um pedaço de papel:\n"
                 "um mapa rasgado com a Rua Derby marcada com um X."
             )),
        Acao("D", "Perguntar ao Dr. Hartwell",   "info",
             descricao=(
                 "'Tivemos quatro casos assim em duas semanas. Todos moradores\n"
                 "das redondezas da Rua Derby. Trauma dissociativo severo.\n"
                 "Eu sei o que causou isso, mas ninguém me acreditaria.'"
             )),
        Acao("X", "Explorar a enfermaria",         "explorar",
             destino="hospital_interior",
             descricao="Você adentra os corredores brancos e silenciosos."),
        Acao("V", "Voltar à Rua Central",        "ir", destino="rua_central"),
    ],
    conexoes=["rua_central"],
    cor=(45, 55, 55),
    dica="[C] Curar HP  [S] Curar SAN  [F/D] Inf  [X] Explorar  [V] Voltar",
))

# ── Delegacia ─────────────────────────────────────────────────
_reg(Local(
    id="delegacia",
    nome="Delegacia de Arkham",
    descricao=(
        "A delegacia cheira a café velho e suor. "
        "Fotografias de pessoas desaparecidas cobrem um mural de cortiça. "
        "O Detetive Malone masca um charuto apagado e te olha de cima a baixo. "
        "'Outro curioso ou tem informação de verdade?'"
    ),
    acoes=[
        Acao("I", "Compartilhar informações",    "info",
             descricao=(
                 "Malone ouve com ceticismo crescente. Ao final, ele cospe:\n"
                 "'Mansão Corbitt? Já mandei dois homens lá. Sumiram.\n"
                 "Oficialmente, não existe investigação. Não oficialmente...\n"
                 "aqui está o que meu terceiro homem encontrou antes de pirar.'\n"
                 "[Obteve: Mapa do porão da Mansão Corbitt]"
             )),
        Acao("R", "Ver registros de desaparecimento", "info",
             descricao=(
                 "Cinco desaparecimentos em 30 dias. Todos na área do porto.\n"
                 "Última vítima: Thomas Walsh, estivador. Última localização: Docas Sul.\n"
                 "Nota no arquivo: 'sons subterrâneos relatados por 3 testemunhas.'"
             )),
        Acao("A", "Pedir autorização para a Mansão", "info",
             descricao=(
                 "Malone ri amargamente:\n"
                 "'Autorização? Não tenho jurisdição sobre casos sobrenaturais.\n"
                 "Se você entrar lá e voltar vivo, eu assino o que quiser.'"
             )),
        Acao("X", "Entrar nos arquivos secretos",  "explorar",
             destino="delegacia_interior",
             descricao="Aproveitando a distração de Malone, você acessa a sala de arquivos."),
        Acao("V", "Voltar à Rua Central",         "ir", destino="rua_central"),
    ],
    conexoes=["rua_central", "porto"],
    cor=(50, 45, 40),
    dica="[I] Inf  [R] Registros  [A] Autorização  [X] Explorar  [V] Voltar",
))

# ── Porto de Arkham ───────────────────────────────────────────
_reg(Local(
    id="porto",
    nome="Porto de Arkham",
    descricao=(
        "O cheiro de peixe podre e alcatrão domina o porto. "
        "Barcaças enferrujadas balançam sob o céu plúmbeo. "
        "Estivadores de rosto fechado te encaram brevemente. "
        "Ao fundo, nas docas abandonadas, algo se move nas sombras."
    ),
    acoes=[
        Acao("E", "Falar com estivadores",       "info",
             descricao=(
                 "Um velho pescador se afasta dos outros e sussurra:\n"
                 "'Não vá para as docas de noite. Ouvi coisa arrastando nas pedras.\n"
                 "Grande demais pra ser rato. Walsh foi investigar... não voltou.'"
             )),
        Acao("C", "Examinar caixotes suspeitos",  "info",
             descricao=(
                 "Um dos caixotes tem símbolos gravados: o mesmo que estava no diário.\n"
                 "Cheiro de incenso barato e algo mais... orgânico.\n"
                 "A etiqueta diz: 'Encomenda — R. Derby Street, Arkham.'"
             )),
        Acao("X", "Entrar no armazém suspeito",   "explorar",
             destino="porto_armazem",
             descricao="Você se esgueira pela entrada lateral do armazém 7."),
        Acao("D", "Ir para as Docas Abandonadas", "ir", destino="docas"),
        Acao("V", "Voltar à Rua Central",         "ir", destino="rua_central"),
    ],
    conexoes=["rua_central", "docas", "delegacia"],
    cor=(35, 45, 50),
    dica="[E] Falar  [C] Examinar  [X] Armazém  [D] Docas  [V] Voltar",
))

# ── Docas Abandonadas ─────────────────────────────────────────
_reg(Local(
    id="docas",
    nome="Docas Sul — Abandonadas",
    descricao=(
        "As docas sul foram abandonadas há uma década. "
        "Madeira apodrecida e ferragens enferrujadas criam uma paisagem de pesadelo. "
        "O barulho da água é abafado por algo mais grave, rítmico... "
        "vindo de baixo do assoalho. Um alçapão entreaberro revela degraus."
    ),
    acoes=[
        Acao("E", "Entrar nas catacumbas abaixo das docas", "masmorra",
             destino="catacumbas_porto",
             descricao=(
                 "Você desce os degraus escorregadios.\n"
                 "O frio aumenta a cada passo. Paredes de pedra coberta de fungos.\n"
                 "Ao longe, tochas. Vozes em língua desconhecida."
             )),
        Acao("E", "Examinar alçapão fechado",    "info",
             item_necessario="chave_doca",
             descricao="O alçapão está trancado. Você precisaria de uma chave."),
        Acao("V", "Voltar ao Porto",              "ir", destino="porto"),
    ],
    conexoes=["porto"],
    cor=(30, 35, 40),
    dica="[E] Entrar na masmorra  [V] Voltar",
))

# ── Mansão Corbitt ────────────────────────────────────────────
_reg(Local(
    id="mansao",
    nome="Mansão Corbitt — Derby Street",
    descricao=(
        "A mansão se ergue torta contra o céu encoberto. "
        "Janelas tapiadas com tábuas há anos. A ferrugem cobriu o portão. "
        "Mas à sua luz de lanterna você nota: a terra ao redor está morta. "
        "Até as ervas daninhas se recusam a crescer. "
        "A porta da frente está entreaberta."
    ),
    acoes=[
        Acao("E", "Entrar na mansão (pavimento térreo)", "masmorra",
             destino="mansao_terreo",
             descricao="Você empurra a porta. Os gonzos gritam. Escuridão total além."),
        Acao("P", "Entrar nos porões da mansão",   "masmorra",
             destino="mansao_porao",
             descricao=(
                 "A escada para os porões está no fundo da copa.\n"
                 "O cheiro que sobe é impossível de descrever.\n"
                 "Você sente que algo está ciente da sua presença."
             )),
        Acao("C", "Examinar o exterior",            "info",
             descricao=(
                 "No muro lateral, símbolos entalhados na pedra. Os mesmos dos caixotes.\n"
                 "Uma inscrição em latim: 'Aqui jaz mas não dorme.'\n"
                 "Uma janela no segundo andar está iluminada."
             )),
        Acao("V", "Recuar para a Rua Central",      "ir", destino="rua_central"),
    ],
    conexoes=["rua_central"],
    cor=(35, 30, 35),
    dica="[E] Térreo  [P] Porão  [C] Examinar  [V] Recuar",
))

# ── Cemitério Silver Gate ─────────────────────────────────────
_reg(Local(
    id="cemiterio",
    nome="Cemitério Silver Gate",
    descricao=(
        "Lápides inclinadas se perdem na neblina. "
        "Um corvo pousa numa sepultura rachada e te observa. "
        "A maioria das inscrições foi apagada pelo tempo, mas uma tumba nova "
        "destoa das outras. Flores frescas — de noite, neste lugar."
    ),
    acoes=[
        Acao("T", "Examinar a tumba nova",          "info",
             descricao=(
                 "A lápide diz: 'Irmão da Pele, guardião do portal.'\n"
                 "Data: 3 de outubro de 1923 — há 11 dias.\n"
                 "Sob a flor, um bilhete: 'O ritual deve ser concluído antes do eclipse.'"
             )),
        Acao("C", "Procurar no cemitério à noite",   "masmorra",
             destino="cemiterio_noite",
             descricao="A neblina engole sua lanterna. Algo se move entre as lápides."),
        Acao("V", "Voltar à Rua Central",             "ir", destino="rua_central"),
    ],
    conexoes=["rua_central", "mansao"],
    cor=(30, 35, 30),
    dica="[T] Examinar  [C] Explorar  [V] Voltar",
))

# ── Universidade Miskatonic ───────────────────────────────────
_reg(Local(
    id="universidade",
    nome="Universidade Miskatonic",
    descricao=(
        "O campus em estilo neogótico parece deslocado no tempo. "
        "Estudantes de ar pálido carregam livros pesados. "
        "O Prof. Armitage, chefe do Departamento de Línguas Antigas, "
        "te recebe em seu escritório cheio de pilhas de pergaminhos."
    ),
    acoes=[
        Acao("A", "Consultar Prof. Armitage",     "info",
             descricao=(
                 "O professor esfrega as mãos nervosamente:\n"
                 "'A Irmandade da Pele existe desde o século XVII aqui em Arkham.\n"
                 "Corbitt era seu servo mais dedicado. Seu contrato com eles...\n"
                 "garante imortalidade enquanto o culto existir. Para matá-lo,\n"
                 "você precisa destruir o Grimório da Pele no porão da mansão.'"
             )),
        Acao("T", "Consultar tomos da biblioteca restrita", "pericia",
             descricao=(
                 "Com autorização do Prof. Armitage, você acessa a coleção restrita.\n"
                 "O Necronomicon menciona criaturas como Corbitt como 'Servidores Fixos'.\n"
                 "Para exorcizá-los: sal, água benta, e a palavra de dissolução: PHUR-NETH.\n"
                 "[Teste de SAN: -1d6 ao ler os detalhes]"
             )),
        Acao("P", "Pedir ajuda do Prof. Armitage",  "info",
             descricao=(
                 "'Não posso ir pessoalmente — meu coração... Mas leve isto.'\n"
                 "Ele entrega um frasco pequeno: ÁGUA BENTA × 3.\n"
                 "[Obteve: água_benta]"
             )),
        Acao("V", "Voltar à Rua Central",            "ir", destino="rua_central"),
        Acao("X", "Explorar os corredores proibidos", "explorar", destino="universidade_interior"),
    ],
    conexoes=["rua_central", "biblioteca"],
    cor=(40, 40, 50),
    dica="[A/T/P] Informações  [X] Explorar  [V] Voltar",
))

# ── Estalagem Silver Gate ─────────────────────────────────────
_reg(Local(
    id="estalagem",
    nome="Estalagem 'A Âncora'",
    descricao=(
        "A estalagem cheira a cerveja rançosa e tabaco. "
        "Um barman de braços tatuados limpa um copo indefinidamente. "
        "Três bêbados discutem sobre o 'monstro das docas'. "
        "Aqui você pode descansar, ouvir rumores e se abastecer."
    ),
    acoes=[
        Acao("D", "Descansar (restaura 5 HP, 3 SAN)", "descanso", custo_dinheiro=1,
             descricao="Uma noite de sono pesado. Sonhos estranhos, mas acordou vivo."),
        Acao("R", "Ouvir rumores dos bêbados",     "info",
             descricao=(
                 "'...dizem que o velho Corbitt não morreu mesmo. Meu pai viu ele\n"
                 "na janela da mansão em 1901. Meu avô jurava o mesmo em 1872.'\n"
                 "---\n"
                 "'As docas do sul estão assombradas. Três homens entraram essa semana.\n"
                 "Saíram correndo às 2 da manhã gritando em língua de gago.'"
             )),
        Acao("C", "Comprar provisões",              "comprar", custo_dinheiro=2,
             descricao="Você compra pão velho, queijo duro e uma garrafa d'água."),
        Acao("V", "Voltar à Rua Central",            "ir", destino="rua_central"),
    ],
    conexoes=["rua_central"],
    cor=(45, 40, 35),
    dica="[D] Descansar  [R] Rumores  [C] Comprar  [V] Voltar",
))


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def get_local(id_local: str) -> Optional[Local]:
    return LOCAIS.get(id_local)


def locais_conectados(id_local: str) -> List[Local]:
    local = LOCAIS.get(id_local)
    if not local:
        return []
    return [LOCAIS[c] for c in local.conexoes if c in LOCAIS]


LOCAL_INICIAL = "rua_central"
