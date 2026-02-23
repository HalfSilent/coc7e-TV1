"""
engine/audio_manager.py — Gerenciador de áudio para CoC 7e.

Suporta:
  - SFX (efeitos de curta duração): pygame.mixer.Sound
  - Músicas de fundo: pygame.mixer.music (streaming)

Pasta esperada: CoCGame/assets/audio/
Estrutura de arquivos sugerida:
    assets/audio/
        sfx/
            hit_punch.wav       ← soco
            hit_gun.wav         ← tiro
            step_stone.wav      ← passos em pedra
            step_wood.wav       ← passos em madeira
            door_open.wav       ← abrir porta
            item_pickup.wav     ← pegar item
            menu_open.wav       ← abrir menu/inventário
            menu_select.wav     ← selecionar opção
            sanity_loss.wav     ← perda de sanidade
            combat_start.wav    ← iniciar combate
            combat_win.wav      ← vitória
            combat_lose.wav     ← derrota
            clue_found.wav      ← pista encontrada
            page_turn.wav       ← folhear documento
        music/
            exploration.mp3     ← tema de exploração (loop)
            combat.mp3          ← tema de combate (loop)
            menu.mp3            ← menu principal
            horror.mp3          ← cena de horror/SAN baixa

Uso:
    from engine.audio_manager import audio
    audio.play_sfx("hit_punch")
    audio.play_music("exploration")
    audio.stop_music()
    audio.set_volume(sfx=0.8, music=0.4)
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import pygame


# ══════════════════════════════════════════════════════════════
# CAMINHOS
# ══════════════════════════════════════════════════════════════

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR   = os.path.join(_BASE, "assets", "audio", "sfx")
MUSIC_DIR = os.path.join(_BASE, "assets", "audio", "music")


# ══════════════════════════════════════════════════════════════
# MANAGER
# ══════════════════════════════════════════════════════════════

class AudioManager:
    """
    Singleton de áudio. Inicializado lazy (na primeira chamada).
    Falha silenciosamente se pygame.mixer não estiver disponível
    ou se os arquivos não existirem.
    """

    def __init__(self):
        self._inicializado: bool = False
        self._sfx_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._musica_atual: str = ""
        self._vol_sfx:   float = 0.7
        self._vol_music: float = 0.4
        self._mudo: bool = False

    # ── Inicialização lazy ────────────────────────────────────

    def _garantir_init(self):
        if self._inicializado:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16,
                                  channels=2, buffer=512)
            # Cria pastas se não existirem (facilita adição de arquivos depois)
            os.makedirs(SFX_DIR,   exist_ok=True)
            os.makedirs(MUSIC_DIR, exist_ok=True)
            self._inicializado = True
        except Exception as e:
            print(f"[Audio] Mixer não disponível: {e}")
            self._inicializado = False

    # ── SFX ───────────────────────────────────────────────────

    def play_sfx(self, nome: str, volume: float = 1.0):
        """
        Toca efeito sonoro pelo nome (sem extensão).
        Tenta .wav, .ogg, .mp3 nessa ordem.
        Falha silenciosamente se o arquivo não existir.
        """
        if self._mudo:
            return
        self._garantir_init()
        if not self._inicializado:
            return

        if nome not in self._sfx_cache:
            self._sfx_cache[nome] = self._carregar_sfx(nome)

        som = self._sfx_cache[nome]
        if som:
            som.set_volume(self._vol_sfx * volume)
            som.play()

    def _carregar_sfx(self, nome: str) -> Optional[pygame.mixer.Sound]:
        for ext in (".wav", ".ogg", ".mp3", ".flac"):
            path = os.path.join(SFX_DIR, nome + ext)
            if os.path.exists(path):
                try:
                    return pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[Audio] Erro ao carregar '{path}': {e}")
        return None   # arquivo não existe ainda — silêncio

    # ── Música ────────────────────────────────────────────────

    def play_music(self, nome: str, loop: bool = True, fade_ms: int = 1500):
        """
        Inicia música de fundo.
        Faz fade-out da música atual antes de trocar.
        """
        if self._mudo:
            return
        if nome == self._musica_atual:
            return   # já tocando
        self._garantir_init()
        if not self._inicializado:
            return

        path = self._achar_music(nome)
        if not path:
            return   # arquivo não existe ainda

        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms // 2)
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._vol_music)
            pygame.mixer.music.play(-1 if loop else 0,
                                    fade_ms=fade_ms)
            self._musica_atual = nome
        except Exception as e:
            print(f"[Audio] Erro ao tocar música '{nome}': {e}")

    def stop_music(self, fade_ms: int = 1000):
        self._garantir_init()
        if not self._inicializado:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
            self._musica_atual = ""
        except Exception:
            pass

    def _achar_music(self, nome: str) -> Optional[str]:
        for ext in (".mp3", ".ogg", ".wav"):
            path = os.path.join(MUSIC_DIR, nome + ext)
            if os.path.exists(path):
                return path
        return None

    # ── Volume ────────────────────────────────────────────────

    def set_volume(self, sfx: float = -1, music: float = -1):
        """Ajusta volume de SFX e/ou música. Valores 0.0–1.0."""
        if sfx   >= 0: self._vol_sfx   = max(0.0, min(1.0, sfx))
        if music >= 0: self._vol_music = max(0.0, min(1.0, music))
        self._garantir_init()
        if self._inicializado:
            try:
                pygame.mixer.music.set_volume(self._vol_music)
            except Exception:
                pass

    def toggle_mudo(self):
        self._mudo = not self._mudo
        if self._mudo:
            self.stop_music(fade_ms=300)
        else:
            if self._musica_atual:
                self.play_music(self._musica_atual)

    @property
    def mudo(self) -> bool:
        return self._mudo


# ══════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ══════════════════════════════════════════════════════════════

audio = AudioManager()
