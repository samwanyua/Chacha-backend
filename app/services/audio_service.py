"""
Audio recording and playback service for SpeechMaster.
"""
import logging
import os
import time
import threading
import wave
from pathlib import Path
from typing import Optional, Callable

import numpy as np

from app.utils.config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SIZE,
    MAX_RECORDING_DURATION,
    MIN_RECORDING_DURATION,
    MAX_AUDIO_FILE_SIZE,
)

logger = logging.getLogger(__name__)


class AudioService:
    """Handles audio recording and playback."""

    def __init__(self):
        self._is_recording = False
        self._is_playing = False
        self._recording_thread: Optional[threading.Thread] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._audio_data: list = []
        self._stream = None
        self._current_level: float = 0.0
        self._sd = None  # sounddevice module
        self._stop_event = threading.Event()

    def _ensure_sounddevice(self):
        """Lazy-import sounddevice."""
        if self._sd is None:
            import sounddevice as sd
            self._sd = sd

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_level(self) -> float:
        """Current audio input level (0.0 - 1.0)."""
        return self._current_level

    def check_microphone(self) -> bool:
        """Check if a microphone is available."""
        try:
            self._ensure_sounddevice()
            devices = self._sd.query_devices()
            # query_devices() returns a DeviceList; iterate over its indices
            for i in range(len(devices)):
                if devices[i]['max_input_channels'] > 0:
                    return True
            return False
        except Exception as e:
            logger.error("Microphone check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def start_recording(
        self,
        output_path: str,
        duration: int = MAX_RECORDING_DURATION,
        level_callback: Callable[[float], None] = None,
        done_callback: Callable[[dict], None] = None,
    ):
        """
        Start recording audio from microphone in a background thread.

        Args:
            output_path: Where to save WAV file
            duration: Max recording time in seconds
            level_callback: Called with current audio level (0.0-1.0)
            done_callback: Called with result dict when recording finishes
        """
        if self._is_recording:
            logger.warning("Already recording.")
            return

        self._stop_event.clear()
        self._audio_data = []
        self._is_recording = True

        def _record():
            try:
                self._ensure_sounddevice()
                start_time = time.time()

                def _audio_callback(indata, frames, time_info, status):
                    if status:
                        logger.warning("Audio callback status: %s", status)
                    self._audio_data.append(indata.copy())
                    # Calculate RMS level — cast to float32 to avoid int16 overflow
                    float_data = indata.astype(np.float32) / 32768.0
                    rms = float(np.sqrt(max(0.0, np.mean(float_data ** 2))))
                    self._current_level = min(1.0, rms * 5)
                    if level_callback:
                        level_callback(self._current_level)

                self._stream = self._sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=AUDIO_CHANNELS,
                    dtype='int16',
                    blocksize=AUDIO_CHUNK_SIZE,
                    callback=_audio_callback,
                )

                with self._stream:
                    while not self._stop_event.is_set():
                        elapsed = time.time() - start_time
                        if elapsed >= duration:
                            break
                        self._stop_event.wait(timeout=0.1)

                actual_duration = time.time() - start_time
                self._is_recording = False
                self._current_level = 0.0

                # Save to WAV
                if self._audio_data:
                    audio_array = np.concatenate(self._audio_data, axis=0)
                    self._save_wav(output_path, audio_array)

                    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

                    result = {
                        'success': True,
                        'audio_path': output_path,
                        'duration': round(actual_duration, 2),
                        'file_size': file_size,
                        'message': 'Recording saved.',
                    }
                else:
                    result = {
                        'success': False,
                        'audio_path': '',
                        'duration': 0.0,
                        'file_size': 0,
                        'message': 'No audio data captured.',
                    }

                if done_callback:
                    done_callback(result)

            except Exception as e:
                self._is_recording = False
                self._current_level = 0.0
                logger.error("Recording failed: %s", e)
                result = {
                    'success': False,
                    'audio_path': '',
                    'duration': 0.0,
                    'file_size': 0,
                    'message': f'Recording error: {e}',
                }
                if done_callback:
                    done_callback(result)

        self._recording_thread = threading.Thread(target=_record, daemon=True)
        self._recording_thread.start()

    def stop_recording(self):
        """Stop an ongoing recording."""
        if self._is_recording:
            self._stop_event.set()
            logger.info("Recording stop requested.")

    def _save_wav(self, path: str, audio_data: np.ndarray):
        """Save numpy audio data to WAV file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        logger.info("WAV saved: %s", path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_recording(self, audio_path: str) -> dict:
        """
        Check if a recording is usable.

        Returns:
            {'valid': bool, 'issues': list, 'message': str}
        """
        issues = []

        if not os.path.exists(audio_path):
            return {'valid': False, 'issues': ['file_not_found'],
                    'message': 'Recording file not found.'}

        try:
            with wave.open(audio_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate) if rate > 0 else 0

                if duration < MIN_RECORDING_DURATION:
                    issues.append('too_short')

                if rate != AUDIO_SAMPLE_RATE:
                    issues.append('wrong_sample_rate')

            # Check audio levels
            audio_data = np.frombuffer(
                open(audio_path, 'rb').read()[44:],  # Skip WAV header
                dtype=np.int16,
            ).astype(np.float32) / 32768.0

            if len(audio_data) > 0:
                rms = float(np.sqrt(np.mean(audio_data ** 2)))
                peak = float(np.max(np.abs(audio_data)))

                if rms < 0.01:
                    issues.append('too_quiet')
                if peak > 0.95:
                    issues.append('clipping')

            file_size = os.path.getsize(audio_path)
            if file_size > MAX_AUDIO_FILE_SIZE:
                issues.append('too_large')

        except Exception as e:
            logger.error("Validation error: %s", e)
            issues.append('corrupted')

        valid = len(issues) == 0
        if issues:
            msg = "Issues: " + ", ".join(issues)
        else:
            msg = "Recording is valid."

        return {'valid': valid, 'issues': issues, 'message': msg}

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def play_audio(self, file_path: str, done_callback: Callable = None):
        """
        Play audio file through speakers in a background thread.

        Args:
            file_path: Path to WAV file
            done_callback: Called when playback finishes
        """
        if self._is_playing:
            self.stop_playback()

        def _play():
            self._is_playing = True
            try:
                self._ensure_sounddevice()
                import soundfile as sf

                data, samplerate = sf.read(file_path)
                self._sd.play(data, samplerate)
                self._sd.wait()
            except Exception as e:
                logger.error("Playback failed: %s", e)
            finally:
                self._is_playing = False
                if done_callback:
                    done_callback()

        self._playback_thread = threading.Thread(target=_play, daemon=True)
        self._playback_thread.start()

    def stop_playback(self):
        """Stop audio playback."""
        try:
            self._ensure_sounddevice()
            self._sd.stop()
        except Exception:
            pass
        self._is_playing = False
