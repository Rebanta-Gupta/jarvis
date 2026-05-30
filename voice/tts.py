import asyncio
import os
import tempfile
import threading

import edge_tts
import sounddevice as sd
import soundfile as sf

from config import TTS_VOICE

_stop_event = threading.Event()


def stop_speaking() -> None:
    """Call from any thread to interrupt playback immediately."""
    _stop_event.set()
    try:
        sd.stop()
    except Exception:
        pass


async def _synthesize(text: str, path: str, retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, TTS_VOICE)
            await communicate.save(path)
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"[TTS] Server error, retrying in {wait}s... ({e})")
                await asyncio.sleep(wait)
            else:
                raise


def speak(text: str) -> None:
    """Convert text to speech and play it. Interruptible via stop_speaking()."""
    if not text or not text.strip():
        return

    _stop_event.clear()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        asyncio.run(_synthesize(text, tmp_path))

        if _stop_event.is_set():
            return

        data, sample_rate = sf.read(tmp_path)
        sd.play(data, sample_rate)

        # Poll until done or interrupted
        while True:
            try:
                active = sd.get_stream().active
            except Exception:
                break   # stream closed or not available — treat as done
            if not active:
                break
            if _stop_event.is_set():
                sd.stop()
                print("[TTS] Playback interrupted.")
                return
            sd.sleep(100)

    except Exception as e:
        print(f"[TTS] Failed to speak: {e}")
        print(f"[TTS] Jarvis would have said: '{text}'")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass