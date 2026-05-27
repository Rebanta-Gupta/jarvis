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
    Say 'Hey Jarvis' → Jarvis listens → replies out loud.
    Say 'goodbye' to exit.
    """
    from voice.wakeword import wait_for_wake_word
    from voice.stt import listen
    from voice.tts import speak

    EXIT_WORDS = {"goodbye", "exit", "quit", "stop", "bye"}

    print("Jarvis WAKE WORD MODE — say 'Hey Jarvis' to activate, Ctrl+C to quit\n")

    while True:
        try:
            # Wait for wake word
            wait_for_wake_word()

            # Acknowledge so user knows we're listening
            speak("Yeah?")

            # Listen for the actual command
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