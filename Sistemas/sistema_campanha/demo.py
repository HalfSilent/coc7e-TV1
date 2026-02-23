"""
demo.py — Demonstração standalone do sistema_campanha.

Cria uma campanha completa, salva em pasta temporária e a recarrega.
Não depende de pygame.

  python demo.py
"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))

from sistema_campanha import (
    Campanha, DadosMapa, Personagem, Dialogo, NoDialogo, EscolhaDialogo,
    Trigger, EfeitoMapa, ObjetoMapa, Conexao,
    TipoPersonagem, TipoIA, Stats,
)

SEP = "=" * 62


def secao(titulo: str):
    print(f"\n  {titulo}")
    print("  " + "-" * (len(titulo) + 2))


print(SEP)
print("  Sistema de Campanha CoC 7e — Demo")
print(SEP)

# ── 1. Nova campanha ──────────────────────────────────────────
c = Campanha.nova("Degraus para o Abismo", autor="Keeper")
secao("Campanha criada")
print(f"  Nome  : {c.nome}")
print(f"  Autor : {c.autor}")
print(f"  Mapa  : {c.mapa_inicial}")
print(f"  Jogador ID: {c.personagem_jogador_id}")

# ── 2. Personalizar mapa inicial ──────────────────────────────
mapa = c.mapas[c.mapa_inicial]
mapa.nome = "Mansão Blackwood — Saguão"
mapa.efeitos.append(EfeitoMapa(col=5, linha=5, tipo="SANGUE", duracao=99))
mapa.efeitos.append(EfeitoMapa(col=3, linha=6, tipo="OLEO",   duracao=99))

secao(f"Mapa: '{mapa.nome}' ({mapa.largura}×{mapa.altura})")
print(f"  Tiles  : {mapa.largura * mapa.altura} células")
print(f"  Efeitos: {[e.tipo for e in mapa.efeitos]}")

# ── 3. Segundo mapa ────────────────────────────────────────────
mapa2 = c.novo_mapa("Porão dos Ritos", largura=10, altura=8)
c.mapas[mapa.id].conexoes.append(
    Conexao(col=11, linha=5,
            destino_mapa=mapa2.id,
            destino_col=1, destino_linha=1)
)
print(f"  Conexão para: '{mapa2.nome}'")

# ── 4. Personagens ────────────────────────────────────────────
cultista = Personagem(
    id="cultista_01",
    nome="Irmão Valdez",
    tipo=TipoPersonagem.CULTISTA,
    sprite_id=3,
    ia=TipoIA.AGRESSIVO,
    stats=Stats(hp=8, san=20, forca=60, destreza=50),
    background="Guardião do altar secreto do porão. Serve a Shub-Niggurath.",
    spawn_col=9.0, spawn_linha=7.0,
)
c.personagens[cultista.id] = cultista

engendro = Personagem(
    id="engendro_01",
    nome="A Coisa da Adega",
    tipo=TipoPersonagem.ENGENDRO,
    sprite_id=7,
    ia=TipoIA.AGRESSIVO,
    stats=Stats(hp=20, san=0, forca=85, destreza=30),
    background="Entidade convocada por ritos profanos no solstício de 1922.",
    spawn_col=4.0, spawn_linha=5.0,
)
c.personagens[engendro.id] = engendro
mapa.personagens_spawn += [cultista.id, engendro.id]

secao(f"Personagens ({len(c.personagens)})")
for p in c.personagens.values():
    bar = f"HP:{p.stats.hp:>3}  SAN:{p.stats.san:>3}  STR:{p.stats.forca:>3}"
    print(f"  [{p.tipo:>12}] {p.nome:<24} {bar}  IA:{p.ia}")

# ── 5. Diálogo ────────────────────────────────────────────────
dial = c.novo_dialogo("Confronto com Irmão Valdez")
n_intro = NoDialogo(
    id="n1", personagem_id=cultista.id,
    texto="Insensato! Você não compreende o que invocamos aqui...",
    efeito="san:-1",
    escolhas=[
        EscolhaDialogo(texto="O que vocês invocaram?",          proximo="n2"),
        EscolhaDialogo(texto="Onde está o artefato?",           proximo="n3"),
        EscolhaDialogo(texto="[Atacar] Não me importa!",        proximo=None),
    ],
)
n_resp1 = NoDialogo(
    id="n2", personagem_id=cultista.id,
    texto="Algo além do tempo e do espaço. Algo que não pode ser morto!",
    efeito="san:-3",
    escolhas=[EscolhaDialogo(texto="[Fugir]", proximo=None)],
)
n_resp2 = NoDialogo(
    id="n3", personagem_id=cultista.id,
    texto="Jamais o encontrará a tempo de impedir o ritual...",
    efeito="evento:saber_ritual",
    escolhas=[EscolhaDialogo(texto="Veremos.", proximo=None)],
)
dial.adicionar_no(n_intro)
dial.adicionar_no(n_resp1)
dial.adicionar_no(n_resp2)

secao(f"Diálogo: '{dial.titulo}'")
for nid, no in dial.nos.items():
    print(f"  [{nid}] {no.texto[:50]}...")
    for esc in no.escolhas:
        pr = esc.proximo or "fim"
        print(f"       → '{esc.texto}'  ⟶  [{pr}]")

# ── 6. Trigger ────────────────────────────────────────────────
mapa.triggers.append(Trigger(
    id="t_entrada",
    tipo="dialogo_inicio",
    area=[(4, 3), (5, 3), (4, 4), (5, 4)],
    condicao="sempre",
    acao=f"dialogo:{dial.id}",
))
mapa.triggers.append(Trigger(
    id="t_transicao",
    tipo="transicao",
    area=[(11, 5)],
    condicao="sempre",
    acao=f"mapa:{mapa2.id}:1:1",
))

secao(f"Triggers ({len(mapa.triggers)})")
for t in mapa.triggers:
    print(f"  [{t.id}] tipo={t.tipo}  área={len(t.area)} tiles  → {t.acao}")

# ── 7. Validar ────────────────────────────────────────────────
secao("Validação")
avisos = c.validar()
if avisos:
    for av in avisos:
        print(f"  ⚠ {av}")
else:
    print("  ✓ Campanha válida — sem avisos.")

# ── 8. Salvar e recarregar ────────────────────────────────────
secao("Salvar / Carregar")
pasta_tmp = tempfile.mkdtemp(prefix="coc_campanha_demo_")
c.salvar(pasta_tmp)
print(f"  Salva em: {pasta_tmp}")

c2 = Campanha.carregar(pasta_tmp)
print(f"  Recarregada: '{c2.nome}'")
print(f"    Mapas       : {len(c2.mapas)}")
print(f"    Personagens : {len(c2.personagens)}")
print(f"    Diálogos    : {len(c2.dialogos)}")
print(f"    Triggers    : {sum(len(m.triggers) for m in c2.mapas.values())}")

shutil.rmtree(pasta_tmp)

print()
print(SEP)
print("  Sistema de campanha funcionando!")
print(SEP)
