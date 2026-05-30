import os
from dotenv import load_dotenv

load_dotenv()

# ── Required ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError(
        "\n\n[Jarvis] GROQ_API_KEY is not set.\n"
        "Create a .env file in the project root with:\n"
        "  GROQ_API_KEY=your_key_here\n"
        "Get a free key at https://console.groq.com\n"
    )

# ── Optional — override in .env ──────────────────────────────────────────────
ASSISTANT_NAME   = os.getenv("ASSISTANT_NAME",   "Jarvis")
DEFAULT_TIMEZONE = os.getenv("TIMEZONE",          "America/Vancouver")
LLM_MODEL        = os.getenv("LLM_MODEL",         "llama-3.3-70b-versatile")
LLM_MAX_TOKENS   = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE", "0.7"))
TTS_VOICE        = os.getenv("TTS_VOICE",         "en-US-GuyNeural")
WAKE_WORD        = os.getenv("WAKE_WORD",         "hey_jarvis_v0.1")
WAKE_THRESHOLD   = float(os.getenv("WAKE_THRESHOLD", "0.5"))
WHISPER_MODEL    = os.getenv("WHISPER_MODEL",     "small")
FFMPEG_PATH      = os.getenv("FFMPEG_PATH",       "")   # leave empty to auto-detect

_BASE_PROMPT = f"""You are {ASSISTANT_NAME}, a personal AI assistant.
You are helpful, concise, and conversational.
Keep responses short — 1 to 3 sentences unless the user asks for detail.

RULES:
- For time or date questions, always use your tools. Never guess.
- For weather questions, always use get_weather with the city name.
- For timers, use set_timer with duration_seconds as an integer.
- For notes, use add_note. For reminders, use set_reminder with minutes_from_now as an integer.
- If a tool returns an error, tell the user briefly and suggest an alternative.
- Before deleting all notes, reminders, or facts, confirm with the user first.
- If you are unsure of a tool argument (e.g. duration, city name), ask rather than guessing.
- If you don't have a tool for something, say so honestly.
- Default timezone is {DEFAULT_TIMEZONE}.
- Always pass numeric arguments as numbers, never as strings.
- Stored facts may be outdated — if something seems inconsistent, ask to confirm.
- Use user facts naturally — don't announce that you remember them, just use them when relevant.
"""

def build_system_prompt(memory_block: str = "") -> str:
    """Build the full system prompt, injecting memory block if present."""
    if memory_block:
        return f"{_BASE_PROMPT}\n\n{memory_block}"
    return _BASE_PROMPT