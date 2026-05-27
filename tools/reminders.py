import threading
import time
import json
import os
from datetime import datetime, timedelta
import pytz

REMINDERS_FILE = "data/reminders.json"
_reminder_thread: threading.Thread = None
_running = False

def _load() -> list[dict]:
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, "r") as f:
        return json.load(f)

def _save(reminders: list[dict]):
    os.makedirs("data", exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

def _watch():
    """Background thread — checks reminders every second."""
    while _running:
        reminders = _load()
        now = datetime.now(pytz.UTC).isoformat()
        updated = False
        for r in reminders:
            if not r.get("fired") and r["due"] <= now:
                print(f"\n🔔 Reminder: {r['message']}\nYou: ", end="", flush=True)
                r["fired"] = True
                updated = True
        if updated:
            _save(reminders)
        time.sleep(1)

def start_reminder_watcher():
    """Call this once at startup to begin watching reminders."""
    global _reminder_thread, _running
    _running = True
    _reminder_thread = threading.Thread(target=_watch, daemon=True)
    _reminder_thread.start()

def set_reminder(message: str, minutes_from_now: int = 5) -> str:
    """Set a reminder for N minutes from now."""
    if minutes_from_now <= 0:
        return "Please set a reminder at least 1 minute from now."
    if minutes_from_now > 1440:
        return "Maximum reminder time is 24 hours (1440 minutes)."

    due = (datetime.now(pytz.UTC) + timedelta(minutes=minutes_from_now)).isoformat()
    reminders = _load()
    reminder = {
        "id": len(reminders) + 1,
        "message": message,
        "due": due,
        "fired": False,
        "created": datetime.now(pytz.UTC).isoformat(),
    }
    reminders.append(reminder)
    _save(reminders)
    return f"Reminder set: '{message}' in {minutes_from_now} minute{'s' if minutes_from_now != 1 else ''}."

def list_reminders() -> str:
    """List all upcoming (unfired) reminders."""
    reminders = _load()
    upcoming = [r for r in reminders if not r.get("fired")]
    if not upcoming:
        return "No upcoming reminders."
    lines = []
    for r in upcoming:
        due = datetime.fromisoformat(r["due"]).strftime("%I:%M %p")
        lines.append(f"[{r['id']}] {r['message']} — due at {due} UTC")
    return "\n".join(lines)

def cancel_reminder(reminder_id: int) -> str:
    """Cancel a reminder by ID."""
    reminders = _load()
    original_len = len(reminders)
    reminders = [r for r in reminders if r["id"] != reminder_id]
    if len(reminders) == original_len:
        return f"No reminder found with ID {reminder_id}."
    _save(reminders)
    return f"Reminder {reminder_id} cancelled."