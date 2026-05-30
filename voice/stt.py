import os
import shutil
import collections
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
import whisper

from config import WHISPER_MODEL, FFMPEG_PATH

# ── FFmpeg path ───────────────────────────────────────────────────────────────
# Set FFMPEG_PATH in .env to an explicit path, or leave empty to auto-detect.
def _setup_ffmpeg() -> None:
    if FFMPEG_PATH:
        os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")
        return
    detected = shutil.which("ffmpeg")
    if not detected:
        print(
            "[STT] Warning: ffmpeg not found on PATH.\n"
            "      Install ffmpeg or set FFMPEG_PATH in your .env file.\n"
            "      Download: https://ffmpeg.org/download.html"
        )

_setup_ffmpeg()

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE        = 16000
FRAME_MS           = 30
FRAME_SIZE         = int(SAMPLE_RATE * FRAME_MS / 1000)
VAD_AGGRESSIVENESS = 2
SILENCE_TIMEOUT    = 1.2
MAX_DURATION       = 10

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"[STT] Loading Whisper '{WHISPER_MODEL}' model...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("[STT] Model ready.")
    return _model


def record_with_vad() -> np.ndarray:
    """Record until silence detected or MAX_DURATION reached."""
    vad                  = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    silence_frames_needed = int(SILENCE_TIMEOUT * 1000 / FRAME_MS)
    ring_buffer          = collections.deque(maxlen=silence_frames_needed)
    recorded_frames      = []
    speaking_started     = False
    max_frames           = int(MAX_DURATION * 1000 / FRAME_MS)

    print("[STT] Listening... (speak now)")

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SIZE,
        ) as stream:
            for _ in range(max_frames):
                frame_bytes, _ = stream.read(FRAME_SIZE)
                frame_np       = np.frombuffer(frame_bytes, dtype=np.int16)

                try:
                    is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)
                except Exception:
                    is_speech = False

                recorded_frames.append(frame_np)
                ring_buffer.append(is_speech)

                if is_speech:
                    speaking_started = True

                if speaking_started and len(ring_buffer) == ring_buffer.maxlen and not any(ring_buffer):
                    print("[STT] Silence detected, processing...")
                    break

    except sd.PortAudioError as e:
        print(f"[STT] Microphone error: {e}\nCheck your audio device settings.")
        return np.array([], dtype=np.float32)

    if not recorded_frames:
        return np.array([], dtype=np.float32)

    return np.concatenate(recorded_frames).astype(np.float32) / 32768.0


def transcribe(audio: np.ndarray) -> str:
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
            condition_on_previous_text=False,
            temperature=0.0,
        )
        text = result["text"].strip()

        _hallucinations = {
            "thank you", "thanks for watching", "you", ".",
            "bye", "bye-bye", "goodbye", "the", "",
        }
        return "" if text.lower() in _hallucinations else text

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def listen() -> str:
    audio = record_with_vad()
    text  = transcribe(audio)
    if text:
        print(f"[STT] Heard: '{text}'")
    else:
        print("[STT] Nothing clear heard.")
    return text