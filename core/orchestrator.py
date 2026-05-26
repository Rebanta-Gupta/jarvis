from core.llm import chat

class Orchestrator:
    def __init__(self):
        self.history: list[dict] = []   # short-term memory for now

    def turn(self, user_input: str) -> str:
        """Process one user turn and return the assistant reply."""
        self.history.append({"role": "user", "content": user_input})
        reply = chat(self.history)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []