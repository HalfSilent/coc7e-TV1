"""
demo.py — Demonstração standalone do sistema_pericia.
Roda sem pygame, sem mapa, sem nada do jogo.

  python demo.py
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
from sistema_pericia import grau_sucesso, normalizar_pericia

pericias = {
    "Furtividade": 45,
    "Biblioteca": 60,
    "Armas de Fogo": 30,
    "Psicologia": 50,
    "Ocultismo": 20,
}

print("=" * 52)
print("  Investigador: Heinrich Weber")
print("=" * 52)

icone = {"extremo": "🌟", "dificil": "✓✓", "regular": "✓",
         "falha": "✗", "fumble": "💀"}

for nome, valor in pericias.items():
    rolagem = random.randint(1, 100)
    grau    = grau_sucesso(rolagem, valor, valor)
    print(f"  {nome:<20} ({valor:>2}%)  rolou {rolagem:>3}  "
          f"{icone.get(grau,'?')} {grau.upper()}")

print("=" * 52)
print("Sistema de perícia funcionando!")
