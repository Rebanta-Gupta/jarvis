"""
memory/manager.py — High-level memory logic for Jarvis.
"""

import re
import uuid
import json
from datetime import datetime

from memory.store import (
    init_db, save_turn, get_recent_turns, clear_history,
    upsert_fact, get_all_facts, delete_fact, hard_delete_all_facts, search_facts,
)

CONTEXT_TURNS    = 30
MAX_FACTS_IN_CTX = 30
MIN_FACT_CONFIDENCE = 0.5   # facts below this are not injected into context

_FACT_SIGNALS = re.compile(
    r"\b(my name is|i'm called|call me|i live in|i'm from|i work at|"
    r"i work as|i prefer|i like|i hate|i don't like|i use|my .+ is|"
    r"remember that|don't forget|note that)\b",
    re.IGNORECASE,
)

# Rule-based extractors — ordered most-specific first
_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmy name is ([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", re.I), "user_name"),
    (re.compile(r"\bcall me ([A-Z][a-z]+)",                       re.I), "user_name"),
    (re.compile(r"\bi(?:'m| am) called ([A-Z][a-z]+)",            re.I), "user_name"),
    (re.compile(r"\bi live in ([A-Za-z\s]+?)(?:\.|,|$)",          re.I), "user_location"),
    (re.compile(r"\bi(?:'m| am) from ([A-Za-z\s]+?)(?:\.|,|$)",   re.I), "user_location"),
    (re.compile(r"\bi work (?:at|for) ([A-Za-z\s]+?)(?:\.|,|$)",  re.I), "user_employer"),
    # Occupation: require at least two words OR a known profession keyword
    # to avoid storing fragments like "I'm a bit tired"
    (re.compile(
        r"\bi(?:'m| am) (?:a|an) "
        r"((?:software|senior|junior|lead|staff|principal|head of|chief|full.stack|front.end|back.end)\s+\w[\w\s]{2,}|"
        r"\w+\s+(?:engineer|developer|designer|manager|director|analyst|architect|consultant|doctor|lawyer|teacher|nurse))"
        r"(?:\.|,|$)",
        re.I,
    ), "user_occupation"),
]


class MemoryManager:
    def __init__(self):
        init_db()
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]

    # ── Context ──────────────────────────────────────────────────────────────

    def build_memory_block(self) -> str:
        facts = [f for f in get_all_facts(MAX_FACTS_IN_CTX) if f["confidence"] >= MIN_FACT_CONFIDENCE]
        if not facts:
            return ""
        lines = "\n".join(f"  - {f['key']}: {f['value']}" for f in facts)
        return f"[What you know about the user]\n{lines}"

    def get_history(self) -> list[dict]:
        return get_recent_turns(CONTEXT_TURNS)

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self, role: str, content: str) -> None:
        if content:
            save_turn(self.session_id, role, content)

    def clear_history(self) -> None:
        clear_history()

    # ── Fact extraction ──────────────────────────────────────────────────────

    def maybe_extract_facts(self, user_text: str, llm_caller=None) -> None:
        self._rule_extract(user_text)
        if llm_caller and _FACT_SIGNALS.search(user_text):
            self._llm_extract(user_text, llm_caller)

    def _rule_extract(self, text: str) -> None:
        for pattern, key in _RULES:
            m = pattern.search(text)
            if m:
                value = m.group(1).strip().rstrip(".,!?")
                if len(value) > 1:
                    upsert_fact(key, value, confidence=0.95, source="rule")

    def _llm_extract(self, text: str, llm_caller) -> None:
        prompt = (
            "Extract personal facts from this message as JSON. "
            "Return ONLY a JSON object like {\"key\": \"value\"} with snake_case keys. "
            "Use keys like: user_name, user_location, user_occupation, user_employer, "
            "user_preference_<topic>, user_dislikes_<topic>. "
            "Only extract clear, definite facts. If none, return {}.\n\n"
            f"Message: {text}"
        )
        try:
            raw   = llm_caller(prompt)
            raw   = re.sub(r"```(?:json)?|```", "", raw).strip()
            facts = json.loads(raw)
            if isinstance(facts, dict):
                for key, value in facts.items():
                    if key and value and isinstance(key, str) and isinstance(value, str):
                        upsert_fact(key, str(value), confidence=0.8, source="llm")
        except Exception as e:
            print(f"[Memory] LLM fact extraction failed (non-fatal): {e}")

    # ── Manual fact management ────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> None:
        upsert_fact(key, value, confidence=1.0, source="manual")

    def forget(self, key: str) -> None:
        delete_fact(key)

    def forget_all(self) -> int:
        return hard_delete_all_facts()

    def recall(self, query: str) -> list[dict]:
        return search_facts(query)

    def all_facts(self) -> list[dict]:
        return get_all_facts()