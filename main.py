import threading
from fastapi import FastAPI
from pydantic import BaseModel
from core.orchestrator import Orchestrator
from tools.reminders import start_reminder_watcher

app = FastAPI(title="Jarvis")
orc = Orchestrator()

class Message(BaseModel):
    text: str

@app.post("/chat")
def chat_endpoint(msg: Message):
    reply = orc.turn(msg.text)
    return {"reply": reply}

@app.post("/reset")
def reset():
    orc.reset()
    return {"status": "conversation cleared"}

def run_cli():
    """Text-based loop."""
    print("Jarvis CLI — type 'quit' to exit, 'reset' to clear history\n")
    while True:
        user = input("You: ").strip()
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
    """Voice loop — press Enter to speak."""
    from voice.stt import listen
    from voice.tts import speak

    EXIT_WORDS = {"goodbye", "exit", "quit", "stop", "bye"}

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
                print("Goodbye.")
                break

            reply = orc.turn(text)
            print(f"Jarvis: {reply}\n")
            speak(reply)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

def run_wakeword():
    """
    Fully hands-free mode.
    Say 'Hey Jarvis' → listens → replies out loud.
    Say 'Hey Jarvis' again while speaking to interrupt.
    Say 'goodbye' to exit.
    """
    from voice.wakeword import wait_for_wake_word, watch_for_interrupt
    from voice.stt import listen
    from voice.tts import speak

    EXIT_WORDS = {"goodbye", "exit", "quit", "stop", "bye"}

    print("Jarvis WAKE WORD MODE")
    print("Say 'Hey Jarvis' to activate")
    print("Say 'Hey Jarvis' again while speaking to interrupt")
    print("Press Ctrl+C to quit\n")

    while True:
        try:
            # Wait for wake word
            wait_for_wake_word()

            # Acknowledge
            speak("Yeah?")

            # Listen for command
            text = listen()

            if not text:
                speak("I didn't catch that.")
                continue

            print(f"You: {text}")

            if text.lower().strip(" .") in EXIT_WORDS:
                speak("Goodbye!")
                print("Goodbye.")
                break

            reply = orc.turn(text)
            print(f"Jarvis: {reply}\n")

            # ── Speak with interrupt watcher running in background ──
            tts_done   = threading.Event()  # signals TTS finished naturally
            wake_fired = threading.Event()  # signals wake word interrupted

            # Start interrupt watcher thread
            watcher = threading.Thread(
                target=watch_for_interrupt,
                args=(tts_done, wake_fired),
                daemon=True
            )
            watcher.start()

            # Speak the reply (blocks until done or interrupted)
            speak(reply)

            # Signal watcher to stop if TTS finished naturally
            tts_done.set()
            watcher.join(timeout=1)

            # If wake word fired during speech, go straight to listening
            if wake_fired.is_set():
                print("[WakeWord] Interrupted — listening for new command...")
                speak("Yeah?")
                text = listen()
                if text and text.lower().strip(" .") not in EXIT_WORDS:
                    reply = orc.turn(text)
                    print(f"Jarvis: {reply}\n")
                    speak(reply)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

if __name__ == "__main__":
    import sys
    start_reminder_watcher()

    if "--wake" in sys.argv:
        run_wakeword()
    elif "--voice" in sys.argv:
        run_voice()
    else:
        run_cli()