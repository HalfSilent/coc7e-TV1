"""
demo.py — Demonstração standalone do sistema_temporal.
Mostra o ciclo de períodos do dia sem banco de dados.

  python demo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sistema_temporal import _periodo, _fase_lua

print("=" * 55)
print("  Sistema Temporal — Rio de Janeiro, 1923")
print("=" * 55)

# Simula 24 horas de um dia completo
tempo_base = 0.0  # início do dia (em horas de jogo)
for hora in range(24):
    tempo_jogo = tempo_base + hora
    periodo = _periodo(hora)
    fase    = _fase_lua(tempo_jogo)
    icone = {"manha": "🌅", "tarde": "☀️ ", "noite": "🌙", "madrugada": "⭐"}.get(periodo, "  ")
    print(f"  {hora:02d}:00  {icone} {periodo:<10}  {fase}")

print("=" * 55)
# Mostra ciclo de fases da lua ao longo de 30 dias
print("\n  Fases da lua — 30 dias:")
print("  " + "-" * 40)
for dia in range(0, 30, 3):
    fase = _fase_lua(float(dia * 24))
    print(f"  Dia {dia+1:>2}  →  {fase}")
print("=" * 55)
print("Sistema temporal funcionando!")
