"""
Text-to-Speech service using Piper TTS for SpeechMaster.
Supports multiple voices (male / female).
"""
import hashlib
import logging
import wave
from pathlib import Path

import numpy as np

from app.utils.config import (
    PIPER_VOICES,
    PIPER_DEFAULT_VOICE,
    TTS_CACHE_DIR,
)

logger = logging.getLogger(__name__)


class TTSService:
    """Offline text-to-speech using Piper with voice selection."""

    def __init__(self):
        self._voices: dict = {}          # voice_key -> PiperVoice
        self._current_voice_key: str = PIPER_DEFAULT_VOICE
        self._initialized = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def initialize(self, voice_key: str = None) -> bool:
        """
        Load the specified Piper voice (or default).
        Returns True if at least one voice is ready.
        """
        key = voice_key or PIPER_DEFAULT_VOICE
        if key in self._voices:
            self._current_voice_key = key
            self._initialized = True
            return True

        cfg = PIPER_VOICES.get(key)
        if not cfg:
            logger.error("Unknown voice key: %s", key)
            return False

        model_path = cfg['model']
        config_path = cfg['config']

        try:
            from piper import PiperVoice
            voice = PiperVoice.load(str(model_path), config_path=str(config_path))
            self._voices[key] = voice
            self._current_voice_key = key
            self._initialized = True
            logger.info("Piper TTS initialized with voice: %s (%s)", cfg['label'], model_path.name)
            return True
        except ImportError:
            logger.warning("piper-tts not installed. TTS will use fallback.")
            return False
        except FileNotFoundError:
            logger.error("Piper model not found at %s", model_path)
            return False
        except Exception as e:
            logger.error("Failed to initialize Piper TTS: %s", e)
            return False

    def switch_voice(self, voice_key: str) -> bool:
        """Switch to a different voice. Loads the model if not already loaded."""
        if voice_key in self._voices:
            self._current_voice_key = voice_key
            logger.info("Switched TTS voice to: %s", voice_key)
            return True
        return self.initialize(voice_key)

    @property
    def current_voice_key(self) -> str:
        return self._current_voice_key

    @property
    def is_available(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def _cache_key(self, text: str) -> str:
        """Generate a deterministic cache filename including voice key and speed."""
        blob = f"{self._current_voice_key}_slow::{text.strip().lower()}"
        return hashlib.md5(blob.encode('utf-8')).hexdigest()

    def _get_cache_path(self, text: str) -> Path:
        TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return TTS_CACHE_DIR / f"{self._cache_key(text)}.wav"

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def text_to_speech(self, text: str, output_path: str = None, cache: bool = True) -> dict:
        """
        Convert text to speech audio file.

        Returns:
            {'success': bool, 'audio_path': str, 'duration': float, 'message': str}
        """
        if not text or not text.strip():
            return {'success': False, 'audio_path': '', 'duration': 0.0,
                    'message': 'No text provided.'}

        # Check cache
        cache_path = self._get_cache_path(text)
        if cache and cache_path.exists():
            duration = self._get_wav_duration(str(cache_path))
            target = output_path or str(cache_path)
            if output_path and str(cache_path) != output_path:
                import shutil
                shutil.copy2(str(cache_path), output_path)
            logger.debug("TTS cache hit for: %s", text[:40])
            return {'success': True, 'audio_path': target, 'duration': duration,
                    'message': 'From cache.'}

        if not self._initialized or self._current_voice_key not in self._voices:
            return {'success': False, 'audio_path': '', 'duration': 0.0,
                    'message': 'TTS engine not initialized.'}

        # Generate
        target_path = output_path or str(cache_path)
        try:
            piper_voice = self._voices[self._current_voice_key]
            from piper import SynthesisConfig
            syn_config = SynthesisConfig(length_scale=1.35)
            with wave.open(target_path, 'wb') as wav_file:
                # Piper generates 1 channel (mono), 16-bit (2 bytes), and uses config sample rate. We set it up first:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(piper_voice.config.sample_rate)
                piper_voice.synthesize_wav(text, wav_file, syn_config=syn_config, set_wav_format=False)

            duration = self._get_wav_duration(target_path)

            if cache and output_path and str(cache_path) != output_path:
                import shutil
                shutil.copy2(output_path, str(cache_path))

            logger.info("TTS generated (%0.1fs, voice=%s): %s",
                        duration, self._current_voice_key, text[:40])
            return {'success': True, 'audio_path': target_path, 'duration': duration,
                    'message': 'Generated successfully.'}
        except Exception as e:
            logger.error("TTS generation failed: %s", e)
            return {'success': False, 'audio_path': '', 'duration': 0.0,
                    'message': f'TTS error: {e}'}

    def pre_generate_cache(self, sentences: list, progress_callback=None):
        """Pre-generate TTS audio for a list of sentences."""
        total = len(sentences)
        for i, sentence in enumerate(sentences):
            text = sentence.get('text', '')
            if text:
                self.text_to_speech(text, cache=True)
            if progress_callback:
                progress_callback(i + 1, total)

    # ------------------------------------------------------------------
    # Audio helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_wav_duration(path: str) -> float:
        try:
            with wave.open(path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / float(rate)
        except Exception:
            pass
        return 0.0

    def play_audio(self, file_path: str, callback=None) -> bool:
        """Play audio file through speakers."""
        if not Path(file_path).exists():
            logger.error("Audio file not found: %s", file_path)
            return False

        try:
            import sounddevice as sd
            import soundfile as sf

            data, samplerate = sf.read(file_path)
            sd.play(data, samplerate)
            sd.wait()
            if callback:
                callback()
            return True
        except Exception as e:
            logger.error("Audio playback failed: %s", e)
            return False
