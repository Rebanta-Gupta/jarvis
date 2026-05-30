"""
tools/memory_tools.py — Conversational memory management tools.

Lets the user say things like:
  "forget that I work at Google"
  "remember that I prefer dark mode"
  "what do you know about me?"
  "forget everything"
"""

from memory.store import upsert_fact, delete_fact, get_all_facts, search_facts


def remember_fact(key: str, value: str) -> str:
    """Manually store or update a fact about the user."""
    key = key.strip().lower().replace(" ", "_")
    value = value.strip()
    if not key or not value:
        return "Please provide both a key and a value to remember."
    upsert_fact(key, value, confidence=1.0, source="user")
    return f"Got it, I'll remember that your {key.replace('_', ' ')} is {value}."


def forget_fact(key: str) -> str:
    """Delete a specific fact by key."""
    key = key.strip().lower().replace(" ", "_")
    facts = get_all_facts()
    # Try exact match first, then fuzzy substring match
    match = next((f for f in facts if f["key"] == key), None)
    if not match:
        match = next((f for f in facts if key in f["key"] or f["key"] in key), None)
    if not match:
        return f"I don't have anything stored for '{key}'."
    delete_fact(match["key"])
    return f"Forgotten — I no longer know your {match['key'].replace('_', ' ')}."


def forget_all() -> str:
    """Delete every stored fact."""
    facts = get_all_facts()
    if not facts:
        return "There's nothing stored to forget."
    for f in facts:
        delete_fact(f["key"])
    return f"Done — forgot all {len(facts)} stored fact{'s' if len(facts) != 1 else ''}."


def recall_facts(query: str = "") -> str:
    """List stored facts, optionally filtered by a search query."""
    if query.strip():
        facts = search_facts(query.strip())
    else:
        facts = get_all_facts()

    if not facts:
        if query.strip():
            return f"Nothing stored matching '{query}'."
        return "I don't have anything stored about you yet."

    lines = [f"  • {f['key'].replace('_', ' ')}: {f['value']}" for f in facts]
    header = "Here's everything I know about you:" if not query.strip() else f"What I know matching '{query}':"
    return header + "\n" + "\n".join(lines)