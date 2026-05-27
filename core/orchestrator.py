from core.llm import chat
from tools.registry import TOOL_DEFINITIONS, run_tool

class Orchestrator:
    def __init__(self):
        self.history: list[dict] = []

    def turn(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})

        # Step 1 — ask the LLM, give it the tool menu
        result = chat(self.history, tools=TOOL_DEFINITIONS)

        # Step 2 — if it wants a tool, run it and feed result back
        if result["tool_call"]:
            tc = result["tool_call"]
            tool_result = run_tool(tc["name"], tc["args"])

            # Add the tool exchange to history so LLM can use the result
            self.history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": str(tc["args"]),
                    }
                }]
            })
            self.history.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

            # Step 3 — ask LLM to reply now that it has the real data
            result = chat(self.history)

        reply = result["content"]
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []