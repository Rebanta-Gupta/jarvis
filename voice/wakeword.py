import os
import shutil
import threading

import numpy as np
import pyaudio
from openwakeword.model import Model

from config import WAKE_WORD, WAKE_THRESHOLD, FFMPEG_PATH

# ── FFmpeg (same approach as stt.py) ─────────────────────────────────────────
def _setup_ffmpeg() -> None:
    if FFMPEG_PATH:
        os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

_setup_ffmpeg()

# ── Audio config ──────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
FRAME_SIZE  = 1280
FORMAT      = pyaudio.paInt16
CHANNELS    = 1

# ── Singleton model with thread-safe init ─────────────────────────────────────
_model      = None
_model_lock = threading.Lock()


def _get_model() -> Model:
    global _model
    with _model_lock:
        if _model is None:
            print("[WakeWord] Loading model...")
            _model = Model(
                wakeword_models=[WAKE_WORD],
                inference_framework="onnx",
            )
            print(f"[WakeWord] Listening for '{WAKE_WORD}'...")
    return _model


def _open_stream(audio: pyaudio.PyAudio):
    return audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAME_SIZE,
    )


def wait_for_wake_word() -> None:
    """Block until the wake word is detected."""
    model = _get_model()
    audio = pyaudio.PyAudio()
    stream = _open_stream(audio)
    try:
        while True:
            raw   = stream.read(FRAME_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)
            model.predict(frame)
            scores = model.prediction_buffer.get(WAKE_WORD, [0])
            score  = scores[-1] if scores else 0
            if score >= WAKE_THRESHOLD:
                print(f"\n[WakeWord] Detected! (score: {score:.2f})")
                model.reset()
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


def watch_for_interrupt(stop_event: threading.Event, detected_event: threading.Event) -> None:
    """
    Run in background while Jarvis is speaking.
    Sets detected_event and stops TTS if wake word fires.
    """
    model = _get_model()
    audio = pyaudio.PyAudio()
    stream = _open_stream(audio)
    try:
        while not stop_event.is_set():
            raw   = stream.read(FRAME_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)
            model.predict(frame)
            scores = model.prediction_buffer.get(WAKE_WORD, [0])
            score  = scores[-1] if scores else 0
            if score >= WAKE_THRESHOLD:
                print(f"\n[WakeWord] Interrupt detected! (score: {score:.2f})")
                model.reset()
                detected_event.set()
                from voice.tts import stop_speaking
                stop_speaking()
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()