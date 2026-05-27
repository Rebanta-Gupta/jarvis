from core.llm import chat
from tools.registry import TOOL_DEFINITIONS, run_tool
from tools.system import get_datetime
import re

# Keywords that always mean "get the time" — skip LLM tool calling entirely
TIME_PATTERNS = re.compile(
    r"\b(what'?s? (the )?(time|date|day)|current time|time (is it|right now)|"
    r"what time|tell me the time|time in \w+|date today|today'?s? date)\b",
    re.IGNORECASE
)

TIMEZONE_MAP = {
    "vancouver": "America/Vancouver",
    "pacific": "America/Vancouver",
    "pst": "America/Vancouver",
    "pdt": "America/Vancouver",
    "toronto": "America/Toronto",
    "eastern": "America/Toronto",
    "est": "America/Toronto",
    "new york": "America/New_York",
    "london": "Europe/London",
    "utc": "UTC",
}

def _extract_timezone(text: str) -> str:
    """Pull a timezone out of the user's message if mentioned."""
    text_lower = text.lower()
    for keyword, tz in TIMEZONE_MAP.items():
        if keyword in text_lower:
            return tz
    return "America/Vancouver"  # default

class Orchestrator:
    def __init__(self):
        self.history: list[dict] = []

    def turn(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})

        # ── Fast path: handle time queries directly ──────────
        if TIME_PATTERNS.search(user_input):
            tz = _extract_timezone(user_input)
            result = get_datetime(timezone=tz)
            reply = f"It's {result}."
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # ── Normal path: send to LLM with tools ──────────────
        result = chat(self.history, tools=TOOL_DEFINITIONS)

        if result["tool_call"]:
            tc = result["tool_call"]
            tool_result = run_tool(tc["name"], tc["args"])

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

            result = chat(self.history)

        reply = result["content"]
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []