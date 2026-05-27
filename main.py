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
    """Original text-based loop."""
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
    """Voice loop — press Enter to speak, Jarvis replies out loud."""
    from voice.stt import listen
    from voice.tts import speak

    print("Jarvis VOICE MODE — press Enter to speak, Ctrl+C to quit\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
            text = listen(duration=5)

            if not text:
                print("[ Nothing heard, try again ]")
                continue

            print(f"You: {text}")
            reply = orc.turn(text)
            print(f"Jarvis: {reply}\n")
            speak(reply)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

if __name__ == "__main__":
    import sys
    start_reminder_watcher()

    # pass --voice flag to use voice mode
    # e.g: python main.py --voice
    if "--voice" in sys.argv:
        run_voice()
    else:
        run_cli()