import logging
import wave, io
from fastapi.testclient import TestClient
from app.main import app

logging.basicConfig(level=logging.DEBUG)

f = io.BytesIO()
w = wave.open(f, 'wb')
w.setnchannels(1)
w.setsampwidth(2)
w.setframerate(16000)
w.writeframes(b'\x00' * 32000)
w.close()
f.seek(0)

with TestClient(app) as client:
    r = client.post('/api/recordings/evaluate', data={'target_text': 'HAPPY DOG'}, files={'audio': ('test.wav', f, 'audio/wav')})
    print(r.status_code)
    print(r.text)
