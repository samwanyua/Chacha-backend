from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
import shutil
import uuid

# import the engine functions
from engine import text_to_speech, evaluate_audio

app = FastAPI(title="Speech Therapy Backend")

@app.post("/tts/")
async def tts(sentence: str = Form(...), language: str = Form("en")):
    """
    Generate TTS audio from sentence.
    language: 'en' or 'sw'
    """
    try:
        output_file = text_to_speech(sentence, language)
        return FileResponse(output_file, media_type="audio/wav", filename="tts_output.wav")
    except Exception as e:
        return JSONResponse({"error": str(e)})

@app.post("/evaluate/")
async def evaluate(file: UploadFile, expected_sentence: str = Form(...), mode: str = Form("guest")):
    """
    Evaluate user audio.
    mode: 'guest' or 'login'
    """
    try:
        temp_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = evaluate_audio(temp_path, expected_sentence, mode)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)})
