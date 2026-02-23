"""
chunks_rio1923.py — Locais handmade do Rio de Janeiro, 1923.
Pertence à campanha "Degraus para o Abismo".

Define os 6 locais principais como grids 20×15 de tiles:

  (1,1) casa_investigador.tmj   — sobrado colonial, Rua do Senado
  (2,2) faculdade_malheiros.tmj — academia neo-gótica, Santa Teresa
  (2,3) bairro_catumbi.tmj      — botequim, praça, trilhos de bonde
  (3,3) casarao_rua_almas.tmj   — mansão em ruínas com segredos
  (3,4) camara_subterranea.tmj  — câmara ritualística subterrânea
  (6,4) centro_prefeitura.tmj   — edifício eclético + arquivo público

API pública:
    configurar()           → redireciona sistema_chunks para esta pasta
    gerar_locais_padrao()  → cria .tmj em locais/ se não existirem
    LOCAIS                 → dict {(cx,cy): "nome.tmj"}
    LOCAIS_DIR             → str, caminho absoluto de locais/

Os .tmj são compatíveis com Tiled Editor — abrir, editar e salvar
para personalizar os locais sem alterar este arquivo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

# ── Caminhos ──────────────────────────────────────────────────────────
_CAMP      = Path(os.path.dirname(os.path.abspath(__file__)))
LOCAIS_DIR = str(_CAMP / "locais")
os.makedirs(LOCAIS_DIR, exist_ok=True)

# Garante que sistema_chunks (na raiz do projeto) pode ser importado
_RAIZ = _CAMP.parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import sistema_chunks

# ── Registro de locais ────────────────────────────────────────────────
# Chave: (chunk_x, chunk_y) → arquivo .tmj em LOCAIS_DIR
LOCAIS: dict[tuple[int, int], str] = {
    (1, 1): "casa_investigador.tmj",
    (2, 2): "faculdade_malheiros.tmj",
    (2, 3): "bairro_catumbi.tmj",
    (3, 3): "casarao_rua_almas.tmj",
    (3, 4): "camara_subterranea.tmj",
    (6, 4): "centro_prefeitura.tmj",
}

# ── IDs de tile (espelha mundo_aberto.T) ──────────────────────────────
_V  = 0   # VAZIO     — escuridão / rocha intransponível
_G  = 1   # GRAMA     — jardim, praça, terreno natural
_C  = 2   # CALCADA   — calçada de paralelepípedos
_R  = 3   # RUA       — rua de paralelepípedos (traversável)
_P  = 4   # PAREDE    — muro, coluna, estrutura de pedra
_E  = 5   # EDIFICIO  — interior habitável
_A  = 6   # AGUA      — baía, fonte, chafariz
_T  = 7   # TERRA     — chão batido, poço, altar
_D  = 8   # PORTA     — porta, janela, portão
_AR = 9   # ARVORE    — árvore (bloqueante)
_L  = 10  # LAMPIAO   — lampião a gás (bloqueante)
_SC = 11  # ESCADA    — escada, ponto de interação narrativo


# ══════════════════════════════════════════════════════════════════════
#  API PÚBLICA
# ══════════════════════════════════════════════════════════════════════

def configurar():
    """
    Redireciona sistema_chunks para usar a pasta desta campanha.
    Deve ser chamado antes de qualquer operação de chunk no mundo.
    """
    sistema_chunks.configurar_campanha(LOCAIS_DIR, LOCAIS)


def gerar_locais_padrao():
    """Cria os .tmj de todos os locais em locais/ se não existirem."""
    _gerar_se_novo("casa_investigador.tmj",   _layout_casa_investigador)
    _gerar_se_novo("faculdade_malheiros.tmj", _layout_faculdade_malheiros)
    _gerar_se_novo("bairro_catumbi.tmj",      _layout_bairro_catumbi)
    _gerar_se_novo("casarao_rua_almas.tmj",   _layout_casarao_rua_almas)
    _gerar_se_novo("camara_subterranea.tmj",  _layout_camara_subterranea)
    _gerar_se_novo("centro_prefeitura.tmj",   _layout_centro_prefeitura)


# ══════════════════════════════════════════════════════════════════════
#  HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════

def _base(tile: int = _C) -> np.ndarray:
    """Array 15×20 preenchido com um tile."""
    return np.full((15, 20), tile, dtype=np.uint16)


def _borda_rua(d: np.ndarray):
    """Aplica ruas de borda ao array."""
    d[0, :]  = _R
    d[14, :] = _R
    d[:, 0]  = _R
    d[:, 19] = _R


def _rect(d: np.ndarray,
          ty0: int, tx0: int, ty1: int, tx1: int,
          interior: int = _E, borda: int = _P,
          porta_ty: int = -1, porta_tx: int = -1):
    """Preenche retângulo com borda/interior; opcionalmente abre porta."""
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            if ty in (ty0, ty1) or tx in (tx0, tx1):
                d[ty, tx] = borda
            else:
                d[ty, tx] = interior
    if porta_ty >= 0 and porta_tx >= 0:
        d[porta_ty, porta_tx] = _D


def _gerar_se_novo(nome: str, func):
    path = os.path.join(LOCAIS_DIR, nome)
    if not os.path.exists(path):
        dados = func()
        sistema_chunks.salvar_tmj(path, dados)
        print(f"[chunks_rio1923] Local gerado: {nome}")


# ══════════════════════════════════════════════════════════════════════
#  LAYOUTS  (CHUNK_W=20 colunas × CHUNK_H=15 linhas)
#  Orientação: linha 0 = norte / col 0 = oeste
# ══════════════════════════════════════════════════════════════════════

# ── (1, 1) Sobrado colonial — casa do investigador ────────────────────

def _layout_casa_investigador() -> np.ndarray:
    """
    Residência do investigador: sobrado colonial de dois andares
    na Rua do Senado, Catumbi.

    NW: sobrado principal (sala + escritório + escada)
    NE: quintal com jardim, árvores frutíferas e poço artesiano
    S:  calçada frontal com portão e lampiões
    SE: casa dos vizinhos (menor, fechada)
    """
    d = _base(_C)
    _borda_rua(d)

    # ── Sobrado principal (linhas 1–8, colunas 1–10) ──────────────
    _rect(d, 1, 1, 8, 10, porta_ty=8, porta_tx=5)

    # Divisória interna: corredor vertical na coluna 5
    for ty in range(2, 8):
        d[ty, 5] = _P
    d[4, 5] = _D   # porta interna

    # Escada para o sobrado superior (escritório/biblioteca)
    d[3, 3] = _SC
    d[3, 7] = _SC

    # Janelas
    d[3, 1]  = _D   # fachada oeste — sala de estar
    d[6, 1]  = _D   # fachada oeste — escritório
    d[4, 10] = _D   # fachada leste — quintal
    d[6, 10] = _D

    # ── Quintal NE (linhas 1–8, colunas 11–18) ────────────────────
    d[1:9, 11:19] = _G

    # Árvores frutíferas
    d[2, 13] = _AR
    d[2, 16] = _AR
    d[5, 12] = _AR
    d[7, 17] = _AR

    # Poço artesiano (terra = lama / pedra = borda)
    d[4, 15] = _T
    d[4, 16] = _P
    d[3, 15] = _P
    d[3, 16] = _P

    # Canteiro de ervas junto à parede sul do sobrado
    d[7, 12:16] = _G

    # ── Passagem coberta entre sobrado e quintal ──────────────────
    d[1:9, 10] = _C

    # ── Calçada e portão de entrada (linha 9) ────────────────────
    d[9, :]  = _C
    d[9, 5]  = _D   # portão principal
    d[9, 1]  = _L   # lampião
    d[9, 18] = _L   # lampião

    # ── Jardim frontal SW (linhas 10–13, colunas 1–9) ─────────────
    d[10:14, 1:10] = _G
    d[11, 2]  = _AR
    d[12, 7]  = _AR
    # Caminho de pedras até a porta
    d[10:14, 5] = _C

    # ── Casa dos vizinhos SE (linhas 10–13, colunas 11–18) ────────
    _rect(d, 10, 11, 13, 18, porta_ty=13, porta_tx=14)
    d[11, 11] = _D   # janela
    d[11, 18] = _D   # janela

    return d


# ── (2, 2) Academia neo-gótica — Faculdade de Malheiros ───────────────

def _layout_faculdade_malheiros() -> np.ndarray:
    """
    Faculdade onde leciona o Prof. Malheiros: edifício eclético
    de dois andares, fachada com colunas, jardim frontal.

    Ala Oeste:  escritório de Malheiros (NPCs aparece aqui)
    Ala Leste:  biblioteca (estantes visíveis, pista de pesquisa)
    Escada:     acesso ao segundo andar e arquivos secretos
    Jardim:     alameda de coqueiros na fachada sul
    """
    d = _base(_C)
    _borda_rua(d)

    # ── Bloco principal (linhas 1–10, colunas 2–17) ───────────────
    _rect(d, 1, 2, 10, 17, porta_ty=10, porta_tx=9)
    d[10, 10] = _D   # segunda folha da porta dupla

    # Colunas na fachada norte (decorativas / bloqueantes)
    for tx in (4, 7, 12, 15):
        d[1, tx] = _P

    # ── Corredor central horizontal (linha 5) ─────────────────────
    for tx in range(3, 17):
        d[5, tx] = _P
    d[5, 9]  = _D   # porta centro-esquerda
    d[5, 10] = _D   # porta centro-direita

    # ── Divisória ala oeste (coluna 6) ────────────────────────────
    for ty in range(2, 5):
        d[ty, 6] = _P
    d[4, 6] = _D   # entrada do escritório de Malheiros

    # ── Escritório de Malheiros (linhas 2–4, colunas 3–6) ─────────
    # Interior já é _E (marcado pelo _rect)
    d[2, 3] = _D   # janela norte

    # ── Escada central (sobe para 2o andar com arquivos) ──────────
    d[3, 9]  = _SC
    d[3, 10] = _SC

    # ── Divisória ala leste (coluna 13) ───────────────────────────
    for ty in range(2, 5):
        d[ty, 13] = _P
    d[4, 13] = _D   # entrada da biblioteca

    # ── Biblioteca (linhas 2–4, colunas 14–16) ────────────────────
    # Estantes de livros: _E em fileiras densas
    for tx in range(14, 17):
        d[2, tx] = _E
        d[3, tx] = _E
    d[2, 16] = _D   # janela norte da biblioteca

    # ── Sala de aula (linhas 6–9, colunas 3–16) ───────────────────
    # Interior amplo já marcado como _E
    # Carteiras (agrupamentos de EDIFICIO)
    for tx in (4, 7, 10, 13):
        d[7, tx] = _E
        d[8, tx] = _E

    # Janelas fachada sul
    for tx in (4, 8, 11, 15):
        d[10, tx] = _D

    # Janelas fachada norte
    for tx in (3, 5, 14, 16):
        d[1, tx] = _D

    # ── Jardim frontal sul (linhas 11–13) ─────────────────────────
    d[11:14, 3:17] = _G

    # Alameda central de coqueiros
    for tx in (5, 8, 11, 14):
        d[12, tx] = _AR

    d[11, 9]  = _C  # alameda de pedra central
    d[11, 10] = _C
    d[12, 9]  = _C
    d[12, 10] = _C
    d[13, 9]  = _C
    d[13, 10] = _C

    # Lampiões da fachada
    d[1, 2]   = _L
    d[1, 17]  = _L
    d[10, 2]  = _L
    d[10, 17] = _L

    return d


# ── (2, 3) Bairro do Catumbi — início da campanha ────────────────────

def _layout_bairro_catumbi() -> np.ndarray:
    """
    Bairro popular do Catumbi: malha de ruas, botequim, praça.

    Grade de ruas:
      Horizontal: linhas 0, 7, 14
      Vertical:   colunas 0, 10, 19
      Lampião em cada interseção

    QNO: Botequim de Benedito — entrada sul, balcão interno (SC)
    QNE: Cortiço — três casas geminadas com janelas
    QSO: Igreja de N. Sra. do Carmo — torre, nave e altar
    QSE: Praça com chafariz de pedra e árvores tropicais

    Trilho de bonde corre pela Rua Central (linha 7).
    """
    d = _base(_C)

    # Grade de ruas
    d[0, :]  = _R;  d[7, :]  = _R;  d[14, :] = _R
    d[:, 0]  = _R;  d[:, 10] = _R;  d[:, 19] = _R

    # Lampiões em todas as interseções de rua
    for tx, ty in [
        (0,  0),  (10,  0), (19,  0),
        (0,  7),  (10,  7), (19,  7),
        (0, 14),  (10, 14), (19, 14),
    ]:
        d[ty, tx] = _L

    # ── QNO: Botequim de Benedito (linhas 1–6, colunas 1–9) ──────
    _rect(d, 1, 1, 6, 9, porta_ty=6, porta_tx=4)
    d[6, 5] = _D   # segunda folha (porta dupla do bar)

    # Balcão de serviço interno (ESCADA = ponto de interação)
    d[3, 7] = _SC
    d[4, 7] = _SC

    # Janelas
    d[2, 2] = _D;  d[2, 8] = _D
    d[4, 1] = _D   # janela voltada para a rua principal

    # Mesa e cadeiras no salão (pequenos grupos de EDIFICIO)
    d[3, 3] = _E;  d[3, 5] = _E
    d[4, 3] = _E;  d[4, 5] = _E

    # ── QNE: Cortiço (linhas 1–5, colunas 11–18) ─────────────────
    # Três casas geminadas (3 colunas cada)
    for i, tx0 in enumerate((11, 14, 17)):
        tx1 = min(tx0 + 2, 18)
        _rect(d, 1, tx0, 5, tx1)
        d[5, tx0 + 1] = _D   # porta sul de cada casa
        d[2, tx0]     = _D   # janela norte

    # ── QSO: Igreja de N. Sra. do Carmo (linhas 8–13, colunas 1–9) ──
    _rect(d, 8, 1, 13, 9, porta_ty=13, porta_tx=4)
    d[13, 5] = _D   # segunda folha

    # Torres nos cantos da fachada norte (ornamentais)
    d[8, 1] = _P
    d[8, 9] = _P

    # Corredor da nave central (ESCADA = bancos / caminho até o altar)
    for ty in range(9, 13):
        d[ty, 4] = _SC
        d[ty, 6] = _SC

    # Altar (fundo norte da nave)
    d[9, 4] = _T
    d[9, 5] = _T
    d[9, 6] = _T

    # Janelas laterais da nave
    d[10, 1] = _D;  d[10, 9] = _D
    d[12, 1] = _D;  d[12, 9] = _D

    # ── QSE: Praça com chafariz (linhas 8–13, colunas 11–18) ─────
    d[8:14, 11:19] = _G

    # Chafariz central: moldura de pedra + água
    d[10, 14] = _P;  d[10, 15] = _P
    d[11, 14] = _A;  d[11, 15] = _P   # água e pedra
    d[12, 14] = _P;  d[12, 15] = _A
    d[11, 13] = _P;  d[11, 16] = _P   # laterais

    # Árvores tropicais ao redor da praça
    for tx, ty in ((12, 9), (17, 9), (12, 13), (17, 13), (14, 8), (15, 13)):
        d[ty, tx] = _AR

    # Banco de pedra (calçada ao lado do chafariz)
    d[9, 13] = _C

    return d


# ── (3, 3) Casarão da Rua das Almas ──────────────────────────────────

def _layout_casarao_rua_almas() -> np.ndarray:
    """
    Mansão colonial em decadência — cenário central da campanha.

    Muro perimetral alto com portão norte (único acesso).
    Jardim morto: árvores retorcidas, sem vida.
    Ala principal: sala nobre, corredor, quartos fechados.
    Escada oculta no centro da ala (tile [5,9] e [5,10]):
      começa como EDIFICIO; após evento "casarao_noite"
      o sistema temporal revela ESCADA.
    Quintal sul: poço seco + estábulo em ruínas.
    """
    d = _base(_C)
    _borda_rua(d)

    # ── Muro perimetral ───────────────────────────────────────────
    d[1, 2:18]  = _P   # muro norte
    d[1:14, 2]  = _P   # muro oeste
    d[1:14, 17] = _P   # muro leste

    # Portão de entrada norte
    d[1, 9]  = _D
    d[1, 10] = _D

    # ── Jardim de entrada (linhas 2–3) ────────────────────────────
    d[2:4, 3:17] = _G

    # Árvores mortas — distribuição irregular e sombria
    for tx in (4, 7, 12, 15):
        d[2, tx] = _AR
    d[3, 5]  = _AR
    d[3, 14] = _AR

    # Caminho de pedras até o casarão
    d[2:4, 9]  = _C
    d[2:4, 10] = _C

    # ── Casarão principal (linhas 4–11, colunas 3–16) ─────────────
    _rect(d, 4, 3, 11, 16)

    # Porta principal (sul)
    d[11, 9]  = _D
    d[11, 10] = _D

    # Porta norte (acesso ao jardim — normalmente trancada)
    d[4, 9] = _D

    # ── Corredor leste-oeste interno (linha 7) ────────────────────
    for tx in range(4, 16):
        d[7, tx] = _E
    d[7, 7]  = _D   # porta oeste do corredor
    d[7, 12] = _D   # porta leste do corredor

    # ── Sala nobre NO (linhas 5–6, colunas 4–7) ───────────────────
    # Interior já marcado como _E pelo _rect
    d[5, 3] = _D   # janela oeste
    d[6, 3] = _D   # janela oeste

    # ── Escada oculta para a câmara (linhas 5–6, colunas 9–10) ───
    # Começa como EDIFICIO; sistema temporal muda para ESCADA
    # após o evento "casarao_noite" (ver sistema_temporal.py)
    d[5, 9]  = _E   # ponto de revelação — ESCADA
    d[5, 10] = _E
    d[6, 9]  = _E
    d[6, 10] = _E

    # ── Quartos NE (linhas 5–6, colunas 12–15) ────────────────────
    d[5, 16] = _D   # janela leste
    d[6, 16] = _D

    # Divisória interna entre quartos (coluna 13)
    for ty in range(5, 7):
        d[ty, 13] = _P

    # ── Janelas fachada sul ────────────────────────────────────────
    for tx in (5, 8, 11, 14):
        d[11, tx] = _D

    # ── Quintal sul (linhas 12–13) ────────────────────────────────
    d[12:14, 3:17] = _C

    # Poço seco (poço sem água — simbolismo da decadência)
    d[12, 6] = _T   # boca do poço
    d[12, 7] = _P   # borda de pedra

    # Estábulo em ruínas (canto SE)
    _rect(d, 12, 12, 13, 16)
    d[13, 14] = _D

    return d


# ── (3, 4) Câmara Subterrânea de Valverde ────────────────────────────

def _layout_camara_subterranea() -> np.ndarray:
    """
    Câmara ritualística subterrânea — núcleo do horror da campanha.

    VAZIO  = rocha sólida / escuridão (intransponível)
    TERRA  = chão de pedra talhada
    PAREDE = parede de pedra / coluna / estrutura do altar
    ESCADA = pontos de interação narrativa (altar, relíquias, saídas)

    Norte:   corredor de acesso (escada descendo do casarão)
    Centro:  câmara principal com altar em 'U' de Valverde
    Laterais:nichos com relíquias / velas votivas
    SO:      câmara auxiliar de preparação ritual
    Sul:     corredor de saída de emergência (capítulo final)
    """
    d = _base(_V)   # tudo escuridão / rocha sólida

    # ── Corredor norte de acesso (linhas 0–3) ─────────────────────
    for ty in range(0, 4):
        d[ty, 9]  = _T
        d[ty, 10] = _T

    # Topo da escada descendo do casarão
    d[0, 9]  = _SC
    d[0, 10] = _SC

    # ── Câmara principal (linhas 3–11, colunas 3–16) ──────────────
    for ty in range(3, 12):
        for tx in range(3, 17):
            if ty in (3, 11) or tx in (3, 16):
                d[ty, tx] = _P
            else:
                d[ty, tx] = _T

    # Abertura norte para o corredor de acesso
    d[3, 9]  = _T
    d[3, 10] = _T

    # ── Altar central de Valverde (estrutura em 'U') ──────────────
    d[6, 7:13]  = _P   # borda norte do altar
    d[9, 7:13]  = _P   # borda sul do altar
    d[6:10, 7]  = _P   # borda oeste
    d[6:10, 12] = _P   # borda leste

    # Piso ritual no interior do altar (ESCADA = interação)
    d[7, 8]  = _SC;  d[7, 9]  = _SC
    d[7, 10] = _SC;  d[7, 11] = _SC
    d[8, 8]  = _SC;  d[8, 9]  = _SC
    d[8, 10] = _SC;  d[8, 11] = _SC

    # ── Pilares de sustentação da abóbada ─────────────────────────
    for ty2, tx2 in ((4, 5), (4, 14), (10, 5), (10, 14)):
        d[ty2, tx2] = _P

    # Pilares menores intermediários
    for ty2, tx2 in ((5, 7), (5, 12), (9, 7), (9, 12)):
        d[ty2, tx2] = _P

    # ── Nicho oeste — velas e relíquias (colunas 1–2) ─────────────
    d[5:10, 2] = _T
    d[7, 1]    = _SC   # relíquia principal (interativa)

    # ── Nicho leste — velas e relíquias (colunas 17–18) ──────────
    d[5:10, 17] = _T
    d[7, 18]    = _SC   # relíquia principal (interativa)

    # ── Câmara auxiliar SO (linhas 5–10, colunas 4–6) ─────────────
    # Sala de preparação do ritual (livros proibidos, roupas rituais)
    for ty in range(5, 11):
        for tx in range(4, 7):
            if ty in (5, 10) or tx in (4, 6):
                d[ty, tx] = _P
            else:
                d[ty, tx] = _T
    d[5, 5] = _D   # porta da câmara auxiliar (passagem de pedra)

    # ── Corredor sul — saída de emergência (linhas 12–14) ─────────
    for ty in range(12, 15):
        d[ty, 9]  = _T
        d[ty, 10] = _T

    # Saída de emergência sul (ativada no capítulo final)
    d[14, 9]  = _SC
    d[14, 10] = _SC

    return d


# ── (6, 4) Centro / Prefeitura do Rio de Janeiro ─────────────────────

def _layout_centro_prefeitura() -> np.ndarray:
    """
    Edifício eclético da Prefeitura e Arquivo Público, Centro do Rio.

    Fachada norte: colunas monumentais + 2 pares de lampiões.
    Ala Norte:     salão nobre + gabinete do prefeito.
    Ala Sul:       arquivo público (estantes com documentos / pistas).
    Praça:         Jardim da República com fonte, alameda e árvores.

    Pistas importantes da campanha ficam no arquivo (ala sul).
    """
    d = _base(_C)
    _borda_rua(d)

    # ── Edifício principal (linhas 1–9, colunas 2–17) ─────────────
    _rect(d, 1, 2, 9, 17, porta_ty=9, porta_tx=9)
    d[9, 10] = _D   # segunda folha da porta dupla

    # Colunas decorativas na fachada norte
    for tx in (4, 7, 10, 12, 15):
        d[1, tx] = _P

    # ── Corredor central horizontal (linha 5) ─────────────────────
    for tx in range(3, 17):
        d[5, tx] = _P
    d[5, 9]  = _D   # porta do corredor
    d[5, 10] = _D

    # ── Ala Norte — Salão Nobre + Gabinete (linhas 2–4) ───────────
    # Divisória vertical: coluna 8
    for ty in range(2, 5):
        d[ty, 8] = _P
    d[4, 8] = _D   # porta do gabinete

    # Janelas fachada norte
    for tx in (3, 5, 12, 14, 16):
        d[1, tx] = _D

    # ── Ala Sul — Arquivo Público (linhas 6–8) ────────────────────
    # Divisória vertical: coluna 8
    for ty in range(6, 9):
        d[ty, 8] = _P
    d[7, 8] = _D   # porta do arquivo público

    # Estantes com documentos (EDIFICIO = armários fechados)
    for tx in range(9, 17, 2):
        d[6, tx] = _E
        d[7, tx] = _E

    # Janelas laterais do edifício
    for ty in (3, 7):
        d[ty, 2]  = _D
        d[ty, 17] = _D

    # ── Praça da República (linhas 10–13) ─────────────────────────
    d[10:14, 2:18] = _G

    # Alameda central de paralelepípedo
    d[10:14, 9]  = _C
    d[10:14, 10] = _C

    # Fonte central (moldura de pedra + água)
    d[11, 9]  = _P;  d[11, 10] = _P
    d[12, 9]  = _A;  d[12, 10] = _P
    d[11, 10] = _A
    d[11, 8]  = _P;  d[11, 11] = _P   # moldura lateral
    d[12, 8]  = _P;  d[12, 11] = _P

    # Árvores ornamentais (ficus, coqueiros)
    for tx, ty in ((4, 11), (8, 13), (11, 11), (15, 13), (17, 11), (4, 13)):
        d[ty, tx] = _AR

    # Lampiões da praça
    for tx, ty in ((2, 10), (17, 10), (2, 13), (17, 13)):
        d[ty, tx] = _L

    return d
