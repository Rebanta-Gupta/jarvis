from core.llm import chat, quick_extract
from tools.registry import TOOL_DEFINITIONS, run_tool
from tools.system import get_datetime
from config import build_system_prompt
from memory.manager import MemoryManager
import re

# Fast path: time queries bypass LLM entirely
TIME_PATTERNS = re.compile(
    r"\b(what'?s? (the )?(time|date|day)|current time|time (is it|right now)|"
    r"what time|tell me the time|time in \w+|date today|today'?s? date)\b",
    re.IGNORECASE
)

TIMEZONE_MAP = {
    "vancouver": "America/Vancouver",
    "pacific":   "America/Vancouver",
    "pst":       "America/Vancouver",
    "pdt":       "America/Vancouver",
    "toronto":   "America/Toronto",
    "eastern":   "America/Toronto",
    "est":       "America/Toronto",
    "new york":  "America/New_York",
    "london":    "Europe/London",
    "utc":       "UTC",
}

def _extract_timezone(text: str) -> str:
    text_lower = text.lower()
    for keyword, tz in TIMEZONE_MAP.items():
        if keyword in text_lower:
            return tz
    return "America/Vancouver"


class Orchestrator:
    def __init__(self):
        self.memory = MemoryManager()
        # Seed history from DB so conversation continues across restarts
        self.history: list[dict] = self.memory.get_history()

    def turn(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})

        # Extract facts from user input (rule-based always; LLM-assisted when signals present)
        self.memory.maybe_extract_facts(
            user_input,
            llm_caller=quick_extract   # passes the cheap extractor
        )

        # ── Fast path: time queries ──────────────────────────────────────
        if TIME_PATTERNS.search(user_input):
            tz = _extract_timezone(user_input)
            result = get_datetime(timezone=tz)
            reply = f"It's {result}."
            self._save_turn(user_input, reply)
            return reply

        # ── Build system prompt with current memory state ────────────────
        memory_block = self.memory.build_memory_block()
        system_prompt = build_system_prompt(memory_block)

        # ── Normal LLM path ──────────────────────────────────────────────
        result = chat(self.history, tools=TOOL_DEFINITIONS, system_prompt=system_prompt)

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

            result = chat(self.history, tools=TOOL_DEFINITIONS, system_prompt=system_prompt)

        reply = result["content"]
        self._save_turn(user_input, reply)
        return reply

    def _save_turn(self, user_input: str, reply: str):
        """Persist the completed turn and update in-memory history."""
        self.memory.save("user", user_input)
        self.memory.save("assistant", reply)
        self.history.append({"role": "assistant", "content": reply})

    def reset(self):
        """Clear in-session history (DB log is preserved)."""
        self.history = []