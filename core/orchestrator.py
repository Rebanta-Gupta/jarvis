import re
import threading
from core.llm import chat, quick_extract
from tools.registry import TOOL_DEFINITIONS, run_tool
from tools.system import get_datetime
from config import build_system_prompt, DEFAULT_TIMEZONE
from memory.manager import MemoryManager

# ── Fast-path regex — time queries bypass the LLM entirely ──────────────────
_TIME_RE = re.compile(
    r"\b(what'?s? (the )?(time|date|day)|current time|time (is it|right now)|"
    r"what time|tell me the time|time in \w+|date today|today'?s? date)\b",
    re.IGNORECASE,
)

_TIMEZONE_MAP = {
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

# Maximum turns kept in memory to stay within the LLM context window.
# Each turn = 1 user + 1 assistant message, so this is 2 × CONTEXT_TURNS items.
_MAX_HISTORY = 60   # 30 turns

# Maximum sequential tool calls per turn (prevents infinite loops)
_MAX_TOOL_CALLS = 5


def _extract_timezone(text: str) -> str:
    lower = text.lower()
    for keyword, tz in _TIMEZONE_MAP.items():
        if keyword in lower:
            return tz
    return DEFAULT_TIMEZONE


class Orchestrator:
    def __init__(self):
        self.memory  = MemoryManager()
        self.history: list[dict] = self.memory.get_history()
        self._lock   = threading.Lock()   # safe for concurrent FastAPI requests

    # ── Public API ──────────────────────────────────────────────────────────

    def turn(self, user_input: str) -> str:
        """Process one user turn and return Jarvis's reply."""
        with self._lock:
            return self._turn(user_input)

    def reset(self, clear_db: bool = False) -> None:
        """
        Clear in-session history.
        Pass clear_db=True to also wipe the conversation log from SQLite.
        """
        with self._lock:
            self.history = []
            if clear_db:
                self.memory.clear_history()

    # ── Internal ────────────────────────────────────────────────────────────

    def _turn(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        # Passive fact extraction (rule-based always; LLM-assisted on signal)
        self.memory.maybe_extract_facts(user_input, llm_caller=quick_extract)

        # ── Fast path: time queries ──────────────────────────────────────
        if _TIME_RE.search(user_input):
            tz     = _extract_timezone(user_input)
            result = get_datetime(timezone=tz)
            reply  = f"It's {result}."
            self._save_turn(user_input, reply)
            return reply

        # ── Normal LLM path ──────────────────────────────────────────────
        memory_block  = self.memory.build_memory_block()
        system_prompt = build_system_prompt(memory_block)

        result = chat(self.history, tools=TOOL_DEFINITIONS, system_prompt=system_prompt)

        # ── Tool call loop (up to _MAX_TOOL_CALLS sequential calls) ──────
        calls_made = 0
        while result["tool_call"] and calls_made < _MAX_TOOL_CALLS:
            tc          = result["tool_call"]
            tool_result = run_tool(tc["name"], tc["args"])
            calls_made += 1

            self.history.append({
                "role":       "assistant",
                "content":    None,
                "tool_calls": [{
                    "id":       tc["id"],
                    "type":     "function",
                    "function": {
                        "name":      tc["name"],
                        "arguments": str(tc["args"]),
                    },
                }],
            })
            self.history.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      tool_result,
            })

            self._trim_history()
            result = chat(self.history, tools=TOOL_DEFINITIONS, system_prompt=system_prompt)

        reply = result["content"] or "I couldn't come up with a response — please try again."
        self._save_turn(user_input, reply)
        return reply

    def _save_turn(self, user_input: str, reply: str) -> None:
        """Persist completed turn and append assistant message to history."""
        self.memory.save("user",      user_input)
        self.memory.save("assistant", reply)
        self.history.append({"role": "assistant", "content": reply})
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep history within _MAX_HISTORY to avoid context window overflow."""
        if len(self.history) > _MAX_HISTORY:
            self.history = self.history[-_MAX_HISTORY:]