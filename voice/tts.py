import edge_tts
import asyncio
import tempfile
import os
import sounddevice as sd
import soundfile as sf
import time

VOICE = "en-US-GuyNeural"

async def _synthesize(text: str, path: str, retries: int = 3):
    """Generate speech with automatic retry on server errors."""
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(path)
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s backoff
                print(f"[TTS] Server error, retrying in {wait}s... ({e})")
                await asyncio.sleep(wait)
            else:
                raise

def speak(text: str):
    """Convert text to speech and play it."""
    if not text or not text.strip():
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        asyncio.run(_synthesize(text, tmp_path))
        data, sample_rate = sf.read(tmp_path)
        sd.play(data, sample_rate)
        sd.wait()
    except Exception as e:
        # TTS failed completely — print instead of crashing
        print(f"[TTS] Failed to speak: {e}")
        print(f"[TTS] Jarvis would have said: '{text}'")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass