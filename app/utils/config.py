"""
Application configuration constants for SpeechMaster.
"""
import os
import sys
from pathlib import Path

# Application Info
APP_NAME = "SpeechMaster"
APP_VERSION = "1.0.0"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"

# Database
DB_PATH = DATA_DIR / "app.db"

# Audio Settings
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono
AUDIO_FORMAT = 'int16'  # 16-bit PCM
AUDIO_CHUNK_SIZE = 1024
MAX_RECORDING_DURATION = 30  # seconds
MIN_RECORDING_DURATION = 1  # seconds

# Whisper Settings — Custom finetuned model for Kenyan English non-standard speech
WHISPER_MODEL_ID = 'cdli/whisper-tiny_finetuned_kenyan_english_nonstandard_speech_v0.9'
WHISPER_DEVICE = 'cpu'
WHISPER_TIMEOUT = 60  # seconds

# Piper TTS Settings — two voice options
PIPER_VOICES = {
    'female': {
        'label': 'Woman',
        'model': MODELS_DIR / "piper" / "en_US-amy-low.onnx",
        'config': MODELS_DIR / "piper" / "en_US-amy-low.onnx.json",
    },
    'male': {
        'label': 'Man',
        'model': MODELS_DIR / "piper" / "en_US-hfc_male-medium.onnx",
        'config': MODELS_DIR / "piper" / "en_US-hfc_male-medium.onnx.json",
    },
}
PIPER_DEFAULT_VOICE = 'female'
TTS_CACHE_DIR = DATA_DIR / "tts_cache"

# Scoring Thresholds
SCORE_EXCELLENT_MIN = 70  # 70-100%
SCORE_GOOD_MIN = 50  # 50-69%
SCORE_POOR_MAX = 49  # 0-49%

# LED GPIO Pins (BCM numbering)
LED_PINS = {
    'green': 17,
    'orange': 27,
    'red': 22
}

# UI Settings
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 1280
ORIENTATION = 'portrait'
MIN_TOUCH_TARGET = 60  # pixels

# Colors (Google Material Design)
COLORS = {
    'primary_blue': '#4285F4',
    'success_green': '#34A853',
    'warning_orange': '#FBBC04',
    'error_red': '#EA4335',
    'background_white': '#FFFFFF',
    'surface_gray': '#F1F3F4',
    'text_dark': '#202124',
    'text_light': '#5F6368',
    'border': '#DADCE0',
}

# Session Settings
SESSION_TIMEOUT_MINUTES = 30
GUEST_USER_ID = -1

# Validation Rules
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
PASSWORD_MIN_LENGTH = 6
USERNAME_PATTERN = r'^[a-zA-Z][a-zA-Z0-9_]*$'

# Performance
MAX_HISTORY_RECORDS = 100  # Per user
DATABASE_CACHE_SIZE = 1000  # KB

# Error Messages
ERROR_MESSAGES = {
    'no_microphone': "No microphone detected. Please connect a microphone.",
    'model_load_failed': "Failed to load speech recognition model.",
    'tts_load_failed': "Failed to load text-to-speech model.",
    'disk_full': "Insufficient storage space. Please free up disk space.",
    'invalid_audio': "Recording is invalid. Please try again.",
    'processing_timeout': "Speech processing timed out. Please try again.",
    'username_taken': "Username already exists. Please choose another.",
    'invalid_credentials': "Invalid username or password.",
    'session_expired': "Your session has expired. Please log in again.",
}

# File Limits
MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RECORDINGS_PER_USER = 1000

# Logging
LOG_FILE = BASE_DIR / "app.log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Detect Raspberry Pi
def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except (FileNotFoundError, PermissionError):
        return False

IS_RASPBERRY_PI = is_raspberry_pi()
