import os
os.environ["PATH"] += os.pathsep + r"C:\Users\gupta\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

import whisper
import sounddevice as sd
import numpy as np
import tempfile
import soundfile as sf

# Load once at startup — "base" is fast enough and free
# Change to "small" for better accuracy if you want
_model = None

def _get_model():
    global _model
    if _model is None:
        print("[Whisper] Loading model...")
        _model = whisper.load_model("base")
        print("[Whisper] Model ready.")
    return _model

def record_audio(duration: int = 5, sample_rate: int = 16000) -> np.ndarray:
    """Record audio from the microphone for `duration` seconds."""
    print(f"[STT] Listening for {duration}s...")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()  # wait until recording is done
    return audio.flatten()

def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe a numpy audio array to text using Whisper."""
    model = _get_model()

    # Whisper needs a temp wav file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, audio, sample_rate)
        result = model.transcribe(tmp_path, language="en", fp16=False)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)

def listen(duration: int = 5) -> str:
    """Record and transcribe in one call. Returns transcribed text."""
    audio = record_audio(duration=duration)
    text = transcribe(audio)
    print(f"[STT] Heard: '{text}'")
    return text