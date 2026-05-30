import json
import os
from datetime import datetime

NOTES_FILE = "data/notes.json"


def _load() -> list[dict]:
    if not os.path.exists(NOTES_FILE):
        return []
    with open(NOTES_FILE, "r") as f:
        return json.load(f)


def _save(notes: list[dict]) -> None:
    os.makedirs("data", exist_ok=True)
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)


def _next_id(notes: list[dict]) -> int:
    """Always use max(existing ids) + 1 to avoid collisions after deletions."""
    return max((n["id"] for n in notes), default=0) + 1


def add_note(content: str, title: str = "") -> str:
    """Save a new note."""
    if not content or not content.strip():
        return "No content provided for the note."
    notes   = _load()
    note_id = _next_id(notes)
    note    = {
        "id":      note_id,
        "title":   title or f"Note {note_id}",
        "content": content.strip(),
        "created": datetime.now().isoformat(),
    }
    notes.append(note)
    _save(notes)
    return f"Note saved: '{note['title']}' (id {note_id})"


def get_notes(limit: int = 5) -> str:
    """Read back the most recent notes."""
    notes = _load()
    if not notes:
        return "No notes saved yet."
    recent = notes[-limit:]
    lines  = [f"[{n['id']}] {n['title']}: {n['content']}" for n in reversed(recent)]
    return "\n".join(lines)


def search_notes(query: str) -> str:
    """Search notes by keyword in title or content."""
    if not query or not query.strip():
        return get_notes()
    q     = query.lower()
    notes = _load()
    hits  = [n for n in notes if q in n["title"].lower() or q in n["content"].lower()]
    if not hits:
        return f"No notes found matching '{query}'."
    lines = [f"[{n['id']}] {n['title']}: {n['content']}" for n in reversed(hits[-10:])]
    return "\n".join(lines)


def delete_note(note_id: int) -> str:
    """Delete a note by its ID."""
    notes      = _load()
    filtered   = [n for n in notes if n["id"] != note_id]
    if len(filtered) == len(notes):
        return f"No note found with ID {note_id}."
    _save(filtered)
    return f"Note {note_id} deleted."