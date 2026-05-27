import edge_tts
import asyncio
import tempfile
import os
import sounddevice as sd
import soundfile as sf
import threading

VOICE = "en-US-GuyNeural"

_stop_event = threading.Event()

def stop_speaking():
    """Call this from any thread to interrupt playback."""
    _stop_event.set()
    sd.stop()  # immediately kills sounddevice playback

async def _synthesize(text: str, path: str, retries: int = 3):
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(path)
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"[TTS] Server error, retrying in {wait}s... ({e})")
                await asyncio.sleep(wait)
            else:
                raise

def speak(text: str):
    """
    Convert text to speech and play it.
    Interrupted immediately if stop_speaking() is called.
    """
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

        # Play the full audio — sd.stop() from another thread cuts it instantly
        sd.play(data, sample_rate)

        # Wait, but check stop flag every 100ms
        while sd.get_stream().active:
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