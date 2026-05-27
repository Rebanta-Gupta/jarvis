import edge_tts
import asyncio
import tempfile
import os
import sounddevice as sd
import soundfile as sf

# Good free voices — change to your preference
# Full list: run `edge-tts --list-voices` in terminal
VOICE = "en-US-GuyNeural"       # male, natural
# VOICE = "en-US-JennyNeural"   # female, natural
# VOICE = "en-GB-RyanNeural"    # british male

async def _synthesize(text: str, path: str):
    """Generate speech and save to a file."""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)

def speak(text: str):
    """Convert text to speech and play it."""
    if not text or not text.strip():
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        # Generate the audio file
        asyncio.run(_synthesize(text, tmp_path))

        # Read and play it
        data, sample_rate = sf.read(tmp_path)
        sd.play(data, sample_rate)
        sd.wait()  # wait until playback finishes
    finally:
        os.unlink(tmp_path)