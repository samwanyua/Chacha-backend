"""
Chacha — FastAPI Backend Entry Point
API for Chacha Speech Learning Tool
"""
import logging
import sys
from pathlib import Path

# Ensure the project root is on the path so "app.*" imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import shutil
import uuid

from app.utils.config import APP_NAME, APP_VERSION, LOG_FORMAT
from app.utils.database import Database, init_database
from app.services.auth_service import AuthService
from app.services.tts_service import TTSService
from app.services.stt_service import STTService
from app.services.scoring_service import score_recording

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(title=APP_NAME, version=APP_VERSION)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Services ──
db: Database = None
auth_service: AuthService = None
tts_service: TTSService = None
stt_service: STTService = None

@app.on_event("startup")
async def startup_event():
    global db, auth_service, tts_service, stt_service
    # Initialize DB & Seed Data
    db = init_database()
    
    # Initialize Services
    auth_service = AuthService(db)
    
    tts_service = TTSService()
    if not tts_service.initialize():
        logger.warning("TTS service unavailable.")
        
    stt_service = STTService()
    if not stt_service.initialize():
        logger.warning("STT service unavailable.")
        
    logger.info("FastAPI application started and services initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    global db
    if db:
        db.close()
    logger.info("Application shutdown, database closed.")

# ── Pydantic Models ──
class UserLogin(BaseModel):
    username: str
    password: Optional[str] = None

class UserRegister(BaseModel):
    username: str
    password: str

class TTSText(BaseModel):
    text: str

# ── Endpoints: System ──
@app.get("/")
def read_root():
    return {"message": "Welcome to the Chacha  API! Documentation available at /docs."}

# ── Endpoints: Auth ──
@app.post("/api/auth/register")
def register_user(user: UserRegister):
    res = auth_service.register_user(user.username, user.password, user.password)
    if not res['success']:
        raise HTTPException(status_code=400, detail=res['message'])
    return {"message": res['message'], "user_id": res['user_id']}

@app.post("/api/auth/login")
def login_user(user: UserLogin):
    res = auth_service.login_user(user.username, user.password)
    if not res['success']:
        raise HTTPException(status_code=401, detail=res['message'])
    return {"message": "Login successful", "user": {"id": res['user_id'], "username": res['username']}}

@app.post("/api/auth/guest")
def guest_login():
    res = auth_service.create_guest_session()
    return {"message": "Guest login successful", "user": res}

@app.post("/api/auth/logout")
def logout_user():
    auth_service.logout()
    return {"message": "Logged out successfully"}

# ── Endpoints: Sentences ──
@app.get("/api/sentences")
def get_all_sentences():
    sentences = db.get_all_sentences()
    return {"sentences": sentences}

@app.get("/api/sentences/{level}")
def get_sentences_by_level(level: int):
    sentences = db.get_sentences_by_difficulty(level)
    return {"sentences": sentences}

@app.get("/api/sentences/id/{sentence_id}")
def get_sentence_by_id(sentence_id: int):
    sentence = db.get_sentence_by_id(sentence_id)
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")
    return {"sentence": sentence}

# ── Endpoints: TTS ──
@app.post("/api/tts")
def generate_tts(item: TTSText):
    if not tts_service or not tts_service.is_available:
        raise HTTPException(status_code=503, detail="TTS service unavailable")
    
    result = tts_service.text_to_speech(item.text)
    if not result.get('success'):
        raise HTTPException(status_code=500, detail="TTS generation failed")
    
    return FileResponse(result['audio_path'], media_type="audio/wav")

# ── Endpoints: Speech Recognition & Evaluation ──
@app.post("/api/recordings/evaluate")
async def evaluate_recording(
    audio: UploadFile = File(...),
    target_text: str = Form(...),
    user_id: int = Form(1),
    sentence_id: int = Form(1)
):
    if not stt_service or not stt_service.is_available:
        raise HTTPException(status_code=503, detail="STT service unavailable")
    
    # Save the uploaded file temporarily
    temp_dir = PROJECT_ROOT / "data" / "temp_audio"
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    temp_file_path = temp_dir / f"{file_id}.wav"
    
    with open(temp_file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(audio.file, buffer)
    
    # 1. Transcribe the audio
    result = stt_service.transcribe_audio(str(temp_file_path))
    if not result.get('success'):
        raise HTTPException(status_code=500, detail="Transcription failed")
    
    transcription = result['transcription']
    
    # 2. Evaluate pronunciation
    evaluation = score_recording(transcription, target_text)
    
    # 3. Save to database
    db.save_recording(
        user_id=user_id,
        sentence_id=sentence_id,
        audio_file_path=str(temp_file_path),
        transcription=transcription,
        target_text=target_text,
        wer_score=evaluation["wer"],
        accuracy_percentage=evaluation["accuracy"],
        score_category=evaluation["category"],
        duration_seconds=0.0  # Optional: Calculate actual duration if needed
    )
    
    return {
        "transcription": transcription,
        "evaluation": evaluation
    }

# ── Endpoints: User Stats & History ──
@app.get("/api/users/{user_id}/history")
def get_user_history(user_id: int, limit: int = 100):
    history = db.get_recordings_for_user(user_id=user_id, limit=limit)
    return {"history": history}

@app.get("/api/users/{user_id}/stats")
def get_user_stats(user_id: int):
    stats = db.get_user_stats(user_id)
    return {"stats": stats}

if __name__ == "__main__":
    import uvicorn
    # To run: python app/main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
