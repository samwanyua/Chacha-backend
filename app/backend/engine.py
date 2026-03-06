import os
import shutil
import uuid
import subprocess
from faster_whisper import WhisperModel
from difflib import SequenceMatcher

# -----------------------------
# Paths to models
# -----------------------------
PIPER_MODELS = {
    "en": "/home/rpi/dev/edge_tts_comparison/models/piper/en_US-lessac-medium.onnx",
    "sw": "/home/rpi/dev/edge_tts_comparison/models/piper/sw_Kenyan-medium.onnx"
}

STT_MODEL_PATH = "/home/rpi/dev/captioning/models"

SAVE_DIR = "saved_audio"
os.makedirs(SAVE_DIR, exist_ok=True)

# -----------------------------
# Load FasterWhisper ASR
# -----------------------------
print("Loading FasterWhisper model...")
asr_model = WhisperModel("tiny", compute_type="int8")
print("ASR ready")

# -----------------------------
# Helpers
# -----------------------------
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def score_sentence(expected, detected, probs):
    exp_words = expected.lower().split()
    det_words = detected.lower().split()

    correct = 0
    for ew in exp_words:
        for dw in det_words:
            if similarity(ew, dw) > 0.7:
                correct += 1
                break

    word_acc = correct / max(len(exp_words), 1)
    conf = sum(probs)/len(probs) if probs else 0.0

    if conf > 0.85 and word_acc > 0.75:
        return "high", "green", "Good pronunciation"
    elif conf > 0.6 and word_acc > 0.4:
        return "medium", "yellow", "Getting better"
    else:
        return "low", "red", "Try again"

# -----------------------------
# TTS using Piper
# -----------------------------
def text_to_speech(sentence: str, language="en", output_file="tts_output.wav"):
    model_path = PIPER_MODELS.get(language, PIPER_MODELS["en"])
    cmd = [
        "piper",
        "--model", model_path,
        "--output_file", output_file
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
    proc.communicate(sentence)
    return output_file

# -----------------------------
# Evaluate user audio
# -----------------------------
def evaluate_audio(audio_path, expected_sentence, mode="guest"):
    segments, info = asr_model.transcribe(audio_path, word_timestamps=True, language=None)

    detected = ""
    probs = []

    for seg in segments:
        detected += seg.text.strip() + " "
        if seg.words:
            for w in seg.words:
                if w.probability:
                    probs.append(w.probability)

    detected = detected.strip().lower()
    rating, color, message = score_sentence(expected_sentence, detected, probs)

    # Save recording in login mode
    if mode == "login":
        shutil.move(audio_path, f"{SAVE_DIR}/{uuid.uuid4()}.wav")
    else:
        os.remove(audio_path)

    return {
        "detected_sentence": detected,
        "score": rating,
        "color": color,
        "message": message
    }
