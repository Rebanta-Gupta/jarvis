import os
os.environ["PATH"] += os.pathsep + r"C:\Users\gupta\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

import whisper
import sounddevice as sd
import numpy as np
import tempfile
import soundfile as sf
import webrtcvad
import collections

# ── Model config ──────────────────────────────────────────
WHISPER_MODEL = "small"   # upgrade from "base" for better accuracy
SAMPLE_RATE   = 16000     # required by both Whisper and webrtcvad
FRAME_MS      = 30        # webrtcvad works in 10/20/30ms frames
FRAME_SIZE    = int(SAMPLE_RATE * FRAME_MS / 1000)  # samples per frame

# ── VAD config ────────────────────────────────────────────
VAD_AGGRESSIVENESS = 2    # 0=least aggressive, 3=most aggressive
SILENCE_TIMEOUT    = 1.2  # seconds of silence before stopping
MAX_DURATION       = 10   # max seconds to record regardless

_model = None

def _get_model():
    global _model
    if _model is None:
        print(f"[Whisper] Loading '{WHISPER_MODEL}' model (one-time download)...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("[Whisper] Model ready.")
    return _model

def record_with_vad() -> np.ndarray:
    """
    Record audio until the user stops speaking.
    Uses WebRTC VAD to detect silence and stop early.
    Falls back to MAX_DURATION if silence isn't detected.
    """
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    # Ring buffer holds recent frames to detect silence window
    silence_frames_needed = int(SILENCE_TIMEOUT * 1000 / FRAME_MS)
    ring_buffer = collections.deque(maxlen=silence_frames_needed)

    recorded_frames = []
    speaking_started = False
    max_frames = int(MAX_DURATION * 1000 / FRAME_MS)

    print("[STT] Listening... (speak now, will stop when you pause)")

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SIZE,
    ) as stream:
        for _ in range(max_frames):
            frame_bytes, _ = stream.read(FRAME_SIZE)
            frame_np = np.frombuffer(frame_bytes, dtype=np.int16)

            # Check if this frame contains speech
            try:
                is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)
            except Exception:
                is_speech = False

            recorded_frames.append(frame_np)
            ring_buffer.append(is_speech)

            if is_speech:
                speaking_started = True

            # Once speaking has started, check if we've hit a silence window
            if speaking_started:
                # If the ring buffer is full and all frames are silence → stop
                if (
                    len(ring_buffer) == ring_buffer.maxlen
                    and not any(ring_buffer)
                ):
                    print("[STT] Silence detected, processing...")
                    break

    if not recorded_frames:
        return np.array([], dtype=np.float32)

    audio = np.concatenate(recorded_frames).astype(np.float32) / 32768.0
    return audio

def transcribe(audio: np.ndarray) -> str:
    """Transcribe a numpy audio array to text using Whisper."""
    if audio is None or len(audio) == 0:
        return ""

    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, audio, SAMPLE_RATE)
        result = model.transcribe(
            tmp_path,
            language="en",
            fp16=False,
            condition_on_previous_text=False,  # reduces hallucinations
            temperature=0.0,                   # deterministic, more accurate
        )
        text = result["text"].strip()

        # Filter out common Whisper hallucinations on silence
        hallucinations = {
            "thank you", "thanks for watching", "you", ".",
            "bye", "bye-bye", "goodbye", "the", ""
        }
        if text.lower() in hallucinations:
            return ""

        return text
    finally:
        os.unlink(tmp_path)

def listen() -> str:
    """Record with VAD and transcribe. Returns transcribed text."""
    audio = record_with_vad()
    text = transcribe(audio)
    if text:
        print(f"[STT] Heard: '{text}'")
    else:
        print("[STT] Nothing clear heard.")
    return text