import json
import os
from datetime import datetime

NOTES_FILE = "data/notes.json"

def _load() -> list[dict]:
    if not os.path.exists(NOTES_FILE):
        return []
    with open(NOTES_FILE, "r") as f:
        return json.load(f)

def _save(notes: list[dict]):
    os.makedirs("data", exist_ok=True)
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)

def add_note(content: str = "", title: str = "", note: str = "") -> str:
    """Save a new note."""
    actual_content = content or note
    if not actual_content:
        return "No content provided for the note."

    notes = _load()
    note_obj = {
        "id": len(notes) + 1,
        "title": title or f"Note {len(notes) + 1}",
        "content": actual_content,
        "created": datetime.now().isoformat(),
    }
    notes.append(note_obj)
    _save(notes)
    return f"Note saved: '{note_obj['title']}'"

def get_notes(limit: int = 5) -> str:
    """Read back the most recent notes."""
    notes = _load()
    if not notes:
        return "No notes saved yet."
    recent = notes[-limit:]
    lines = []
    for n in reversed(recent):
        lines.append(f"[{n['id']}] {n['title']}: {n['content']}")
    return "\n".join(lines)

def delete_note(note_id: int) -> str:
    """Delete a note by its ID."""
    notes = _load()
    original_len = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    if len(notes) == original_len:
        return f"No note found with ID {note_id}."
    _save(notes)
    return f"Note {note_id} deleted."