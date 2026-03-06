"""
Speech-to-Text service using HuggingFace Transformers (Whisper) for SpeechMaster.

Uses: cdli/whisper-tiny_finetuned_kenyan_english_nonstandard_speech_v0.9
"""
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

from app.utils.config import (
    WHISPER_MODEL_ID,
    WHISPER_DEVICE,
    WHISPER_TIMEOUT,
    AUDIO_SAMPLE_RATE,
)

logger = logging.getLogger(__name__)


class STTService:
    """Offline speech-to-text using HuggingFace Whisper models."""

    def __init__(self):
        self._model = None
        self._processor = None
        self._initialized = False
        self._model_id = WHISPER_MODEL_ID

    def initialize(self, model_id: str = None) -> bool:
        """
        Load a Whisper model from HuggingFace.

        Args:
            model_id: HuggingFace model ID, e.g.
                       'cdli/whisper-tiny_finetuned_kenyan_english_nonstandard_speech_v1.0'
                       Defaults to WHISPER_MODEL_ID from config.

        Returns:
            True if loaded successfully
        """
        model_id = model_id or self._model_id

        try:
            import torch
            import os
            from transformers import WhisperProcessor, WhisperForConditionalGeneration

            logger.info("Loading Whisper model '%s' ...", model_id)
            
            #Try to load cache first (offline)
            try:
                logger.info("Attempting to load the model from cache (offline mode)...")
                self._processor = WhisperProcessor.from_pretrained(
                    model_id,
                    local_files_only=True # only used cached files
                )
                self._model = WhisperForConditionalGeneration.from_pretrained(
                    model_id,
                    local_files_only=True # only used cached files
                )
                logger.info("Model loaded from cache")
            except Exception as cache_err:
                #If cache does'nt exist download (needs internet)
                logger.warning("Model is not in cache downloading requires internet: %s", cache_err)
                self._processor = WhisperProcessor.from_pretrained(model_id)
                self._model = WhisperForConditionalGeneration.from_pretrained(model_id)
                logger.info("Model downloaded and cached for future use")

            # self._processor = WhisperProcessor.from_pretrained(model_id)
            # self._model = WhisperForConditionalGeneration.from_pretrained(model_id)
            self._model.to(WHISPER_DEVICE)
            self._model.eval()

            self._initialized = True
            self._model_id = model_id

            # Count parameters for logging
            params = sum(p.numel() for p in self._model.parameters())
            logger.info(
                "Whisper model loaded: %s  (%.1fM params, device=%s)",
                model_id, params / 1e6, WHISPER_DEVICE,
            )
            return True

        except ImportError as e:
            logger.error(
                "Required packages not installed. "
                "Run: pip install transformers torch  — %s", e,
            )
            self._initialized = False
            return False
        except Exception as e:
            logger.error("Failed to initialize Whisper model '%s': %s", model_id, e)
            self._initialized = False
            return False

    @property
    def is_available(self) -> bool:
        return self._initialized

    @property
    def active_model(self) -> str:
        return self._model_id

    def transcribe_audio(self, audio_path: str) -> dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to WAV file (16 kHz, mono)

        Returns:
            {
                'success': bool,
                'transcription': str,
                'confidence': float,
                'processing_time': float,
                'message': str
            }
        """
        if not self._initialized:
            return {
                'success': False,
                'transcription': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'message': 'STT engine not initialized.',
            }

        if not Path(audio_path).exists():
            return {
                'success': False,
                'transcription': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'message': f'Audio file not found: {audio_path}',
            }

        start_time = time.time()

        try:
            import torch
            import soundfile as sf

            # Load audio
            audio_data, sample_rate = sf.read(audio_path, dtype='float32')

            # Resample to 16 kHz if needed
            if sample_rate != AUDIO_SAMPLE_RATE:
                logger.info("Resampling from %d Hz to %d Hz", sample_rate, AUDIO_SAMPLE_RATE)
                audio_data = self._resample(audio_data, sample_rate, AUDIO_SAMPLE_RATE)

            # Ensure mono
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            # Prepare input features
            input_features = self._processor(
                audio_data,
                sampling_rate=AUDIO_SAMPLE_RATE,
                return_tensors="pt",
            ).input_features.to(WHISPER_DEVICE)

            # Generate transcription
            with torch.no_grad():
                predicted_ids = self._model.generate(
                    input_features,
                    max_new_tokens=128,
                    language="en",
                    task="transcribe",
                )

            # Decode
            transcription = self._processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0].strip()

            processing_time = time.time() - start_time

            logger.info(
                "Transcription complete (%.1fs): '%s'",
                processing_time,
                transcription[:60],
            )

            return {
                'success': True,
                'transcription': transcription,
                'confidence': 0.0,       # Whisper generate() doesn't expose this easily
                'processing_time': round(processing_time, 2),
                'message': 'Transcription successful.',
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Transcription failed: %s", e)
            return {
                'success': False,
                'transcription': '',
                'confidence': 0.0,
                'processing_time': round(processing_time, 2),
                'message': f'Transcription error: {e}',
            }

    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear-interpolation resample (no librosa dependency)."""
        duration = len(audio) / orig_sr
        target_len = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
