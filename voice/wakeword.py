import os
os.environ["PATH"] += os.pathsep + r"C:\Users\gupta\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

import pyaudio
import numpy as np
from openwakeword.model import Model

# ── Config ────────────────────────────────────────────────
WAKE_WORD        = "hey_jarvis_v0.1"
THRESHOLD        = 0.5   # 0.0–1.0, higher = less sensitive, fewer false triggers
SAMPLE_RATE      = 16000
FRAME_SIZE       = 1280  # required by openwakeword
FORMAT           = pyaudio.paInt16
CHANNELS         = 1

_model = None

def _get_model():
    global _model
    if _model is None:
        print("[WakeWord] Loading hey_jarvis model...")
        _model = Model(
            wakeword_models=["hey_jarvis_v0.1"],
            inference_framework="onnx"
        )
        print("[WakeWord] Listening for 'Hey Jarvis'...")
    return _model

def wait_for_wake_word():
    """
    Block until 'Hey Jarvis' is detected.
    Runs continuously in the foreground, uses minimal CPU.
    """
    model = _get_model()
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAME_SIZE,
    )

    try:
        while True:
            # Read one frame of audio
            raw = stream.read(FRAME_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)

            # Run wake word detection
            model.predict(frame)
            scores = model.prediction_buffer.get(WAKE_WORD, [0])
            score = scores[-1] if len(scores) > 0 else 0

            if score >= THRESHOLD:
                print(f"\n[WakeWord] 'Hey Jarvis' detected! (score: {score:.2f})")
                # Flush the model buffer so it doesn't re-trigger immediately
                model.reset()
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()