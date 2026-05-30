import os
import sys
import signal
import threading

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from core.orchestrator import Orchestrator
from tools.reminders import start_reminder_watcher

# ── App & orchestrator ───────────────────────────────────────────────────────
app = FastAPI(title="Jarvis")
orc = Orchestrator()

EXIT_WORDS = {"goodbye", "exit", "quit", "stop", "bye"}

# ── API key auth ─────────────────────────────────────────────────────────────
# Set JARVIS_API_KEY in your cloud platform's environment variables (e.g. Render dashboard).
# Leave unset for local development — auth is skipped when no key is configured.
_API_KEY = os.getenv("JARVIS_API_KEY", "")

def _check_auth(x_api_key: Optional[str]) -> None:
    """Raise 401 if an API key is configured and the request doesn't match."""
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


class Message(BaseModel):
    text: str


@app.post("/chat")
def chat_endpoint(msg: Message, x_api_key: Optional[str] = Header(default=None)):
    _check_auth(x_api_key)
    reply = orc.turn(msg.text)
    return {"reply": reply}


@app.post("/reset")
def reset_endpoint(x_api_key: Optional[str] = Header(default=None)):
    _check_auth(x_api_key)
    orc.reset()
    return {"status": "conversation cleared"}


@app.get("/health")
def health():
    # Health check is public — Render uses this to verify the container is up
    return {"status": "ok"}


# ── Voice helpers ─────────────────────────────────────────────────────────────

def speak_with_watcher(reply: str, on_interrupt=None):
    """
    Speak reply while watching for a wake-word interrupt.
    Calls on_interrupt() if the wake word fires mid-speech.
    Returns True if interrupted, False if completed naturally.
    """
    from voice.wakeword import watch_for_interrupt
    from voice.tts import speak

    tts_done   = threading.Event()
    wake_fired = threading.Event()

    watcher = threading.Thread(
        target=watch_for_interrupt,
        args=(tts_done, wake_fired),
        daemon=True,
    )
    watcher.start()
    speak(reply)
    tts_done.set()
    watcher.join(timeout=1)

    if wake_fired.is_set() and on_interrupt:
        on_interrupt()
    return wake_fired.is_set()


# ── Run modes ─────────────────────────────────────────────────────────────────

def run_cli():
    print("Jarvis CLI — type 'quit' to exit, 'reset' to clear history\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user:
            continue
        if user.lower() == "quit":
            break
        if user.lower() == "reset":
            orc.reset()
            print("[ conversation cleared ]\n")
            continue
        reply = orc.turn(user)
        print(f"Jarvis: {reply}\n")


def run_voice():
    from voice.stt import listen
    from voice.tts import speak

    print("Jarvis VOICE MODE — press Enter to speak, Ctrl+C to quit\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
            text = listen()
            if not text:
                print("[ Nothing heard, try again ]\n")
                continue
            print(f"You: {text}")
            if text.lower().strip(" .") in EXIT_WORDS:
                speak("Goodbye!")
                break
            reply = orc.turn(text)
            print(f"Jarvis: {reply}\n")
            speak(reply)
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break


def run_wakeword():
    from voice.wakeword import wait_for_wake_word
    from voice.stt import listen
    from voice.tts import speak

    print("Jarvis WAKE WORD MODE")
    print(f"Say 'Hey Jarvis' to activate — Ctrl+C to quit\n")

    def _listen_and_respond():
        text = listen()
        if not text:
            speak("I didn't catch that.")
            return
        print(f"You: {text}")
        if text.lower().strip(" .") in EXIT_WORDS:
            speak("Goodbye!")
            raise SystemExit
        reply = orc.turn(text)
        print(f"Jarvis: {reply}\n")
        speak_with_watcher(reply, on_interrupt=_listen_and_respond)

    while True:
        try:
            wait_for_wake_word()
            speak("Yeah?")
            _listen_and_respond()
        except SystemExit:
            print("Goodbye.")
            break
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break


# ── Entry point ───────────────────────────────────────────────────────────────

def _graceful_shutdown(sig, frame):
    print("\n[Jarvis] Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT,  _graceful_shutdown)


if __name__ == "__main__":
    start_reminder_watcher()

    if "--wake" in sys.argv:
        run_wakeword()
    elif "--voice" in sys.argv:
        run_voice()
    elif "--api" in sys.argv:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
    else:
        run_cli()