"""
memory/manager.py — High-level memory logic for Jarvis.

Responsibilities
----------------
1. Build the memory block injected into the system prompt each turn.
2. Save every turn to the conversation log after it completes.
3. Extract facts from conversation turns (lightweight rule-based + LLM-assisted).

Fact extraction strategy
------------------------
Rule-based patterns catch the obvious ones instantly ("my name is X",
"I live in Y"). For anything subtler, we do a single cheap LLM call
after the turn completes — but only if the user turn looks like it
contains personal info (heuristic gate keeps it from running every turn).
"""

import re
import uuid
import json
from datetime import datetime

from memory.store import (
    init_db, save_turn, get_recent_turns,
    upsert_fact, get_all_facts, delete_fact, search_facts
)

# ── Config ─────────────────────────────────────────────────────────────────

CONTEXT_TURNS    = 30   # how many recent turns to inject into context
MAX_FACTS_IN_CTX = 30   # cap on facts shown to LLM (avoids bloat)

# Patterns that reliably signal a personal fact worth extracting
_FACT_SIGNALS = re.compile(
    r"\b(my name is|i'm called|call me|i live in|i'm from|i work at|"
    r"i work as|i prefer|i like|i hate|i don't like|i use|my .+ is|"
    r"remember that|don't forget|note that)\b",
    re.IGNORECASE
)

# Quick rule-based extractors for common patterns
_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmy name is ([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", re.I), "user_name"),
    (re.compile(r"\bcall me ([A-Z][a-z]+)",                       re.I), "user_name"),
    (re.compile(r"\bi(?:'m| am) called ([A-Z][a-z]+)",            re.I), "user_name"),
    (re.compile(r"\bi live in ([A-Za-z\s]+?)(?:\.|,|$)",          re.I), "user_location"),
    (re.compile(r"\bi(?:'m| am) from ([A-Za-z\s]+?)(?:\.|,|$)",   re.I), "user_location"),
    (re.compile(r"\bi work (?:at|for) ([A-Za-z\s]+?)(?:\.|,|$)",  re.I), "user_employer"),
    (re.compile(r"\bi(?:'m| am) a(?:n)? ([a-z\s]+?)(?:\.|,|$)",   re.I), "user_occupation"),
]


class MemoryManager:
    def __init__(self):
        init_db()
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]

    # ── Context building ───────────────────────────────────────────────────

    def build_memory_block(self) -> str:
        """
        Returns a formatted string to append to the system prompt.
        Called once per turn before the LLM call.
        """
        parts: list[str] = []

        facts = get_all_facts()
        if facts:
            fact_lines = "\n".join(
                f"  - {f['key']}: {f['value']}"
                for f in facts[:MAX_FACTS_IN_CTX]
            )
            parts.append(f"[What you know about the user]\n{fact_lines}")

        return "\n\n".join(parts) if parts else ""

    def get_history(self) -> list[dict]:
        """
        Load recent conversation turns from DB to seed self.history in
        Orchestrator on startup. Returns list of {role, content} dicts.
        """
        return get_recent_turns(CONTEXT_TURNS)

    # ── Persistence ────────────────────────────────────────────────────────

    def save(self, role: str, content: str):
        """Persist one turn. Call this after every user + assistant message."""
        if content:
            save_turn(self.session_id, role, content)

    # ── Fact extraction ────────────────────────────────────────────────────

    def maybe_extract_facts(self, user_text: str, llm_caller=None):
        """
        Try to extract facts from a user message.
        1. Always runs fast rule-based patterns.
        2. If signal words detected AND llm_caller provided, does one LLM pass.

        llm_caller: optional callable(prompt: str) -> str
                    should be a cheap, fast call (use same Groq client).
        """
        # Pass 1 — rule-based (always, zero cost)
        self._rule_extract(user_text)

        # Pass 2 — LLM-assisted (only when signal words present)
        if llm_caller and _FACT_SIGNALS.search(user_text):
            self._llm_extract(user_text, llm_caller)

    def _rule_extract(self, text: str):
        for pattern, key in _RULES:
            m = pattern.search(text)
            if m:
                value = m.group(1).strip().rstrip(".,!?")
                if len(value) > 1:
                    upsert_fact(key, value, confidence=0.95, source="rule")

    def _llm_extract(self, text: str, llm_caller):
        """
        Single cheap LLM call to extract structured facts from user text.
        Only fires when _FACT_SIGNALS matched — not every turn.
        """
        prompt = (
            "Extract personal facts from this message as JSON. "
            "Return ONLY a JSON object like {\"key\": \"value\"} with snake_case keys. "
            "Use keys like: user_name, user_location, user_occupation, user_employer, "
            "user_preference_<topic>, user_dislikes_<topic>. "
            "If there are no clear facts, return {}.\n\n"
            f"Message: {text}"
        )
        try:
            raw = llm_caller(prompt)
            # Strip markdown fences if present
            raw = re.sub(r"```(?:json)?|```", "", raw).strip()
            facts = json.loads(raw)
            if isinstance(facts, dict):
                for key, value in facts.items():
                    if key and value and isinstance(key, str) and isinstance(value, str):
                        upsert_fact(key, str(value), confidence=0.8, source="llm")
        except Exception as e:
            # Fact extraction is best-effort — never crash the main loop
            print(f"[Memory] LLM fact extraction failed (non-fatal): {e}")

    # ── Manual fact management ─────────────────────────────────────────────

    def remember(self, key: str, value: str):
        """Manually store a fact. Use from tools or tests."""
        upsert_fact(key, value, confidence=1.0, source="manual")

    def forget(self, key: str):
        """Manually delete a fact."""
        delete_fact(key)

    def recall(self, query: str) -> list[dict]:
        """Search facts by keyword. Returns list of {key, value, confidence}."""
        return search_facts(query)

    def all_facts(self) -> list[dict]:
        return get_all_facts()