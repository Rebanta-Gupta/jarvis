from fastapi import FastAPI
from pydantic import BaseModel
from core.orchestrator import Orchestrator

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

# ── quick CLI test (run directly with: python main.py) ──────────────────
if __name__ == "__main__":
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