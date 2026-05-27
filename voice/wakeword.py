import os
os.environ["PATH"] += os.pathsep + r"C:\Users\gupta\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

import pyaudio
import numpy as np
from openwakeword.model import Model
import threading

WAKE_WORD        = "hey_jarvis_v0.1"
THRESHOLD        = 0.5
SAMPLE_RATE      = 16000
FRAME_SIZE       = 1280
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
    """Block until 'Hey Jarvis' is detected."""
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
            raw = stream.read(FRAME_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)
            model.predict(frame)
            scores = model.prediction_buffer.get(WAKE_WORD, [0])
            score = scores[-1] if len(scores) > 0 else 0
            if score >= THRESHOLD:
                print(f"\n[WakeWord] 'Hey Jarvis' detected! (score: {score:.2f})")
                model.reset()
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

def watch_for_interrupt(stop_event: threading.Event, detected_event: threading.Event):
    """
    Run in a background thread while Jarvis is speaking.
    Sets detected_event if wake word is heard, then sets stop_event.
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
        while not stop_event.is_set():
            raw = stream.read(FRAME_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)
            model.predict(frame)
            scores = model.prediction_buffer.get(WAKE_WORD, [0])
            score = scores[-1] if len(scores) > 0 else 0
            if score >= THRESHOLD:
                print(f"\n[WakeWord] Interrupt detected! (score: {score:.2f})")
                model.reset()
                detected_event.set()  # signal that wake word fired
                from voice.tts import stop_speaking
                stop_speaking()       # cut TTS immediately
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()