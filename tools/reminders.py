import threading
import time
import json
import os
from datetime import datetime, timedelta
import pytz

REMINDERS_FILE = "data/reminders.json"
_reminder_thread: threading.Thread | None = None
_running = False

# ── Notification hook ────────────────────────────────────────────────────────
# Replace this at runtime for voice mode:
#   from tools.reminders import set_notify_handler
#   set_notify_handler(lambda msg: speak(f"Reminder: {msg}"))

_notify_handler = None

def set_notify_handler(fn) -> None:
    """Register a callable(message: str) used when a reminder fires."""
    global _notify_handler
    _notify_handler = fn

def _notify(message: str) -> None:
    if _notify_handler:
        try:
            _notify_handler(message)
        except Exception as e:
            print(f"[Reminders] Notify handler error: {e}")
    # Always print as fallback
    print(f"\n🔔 Reminder: {message}", flush=True)


# ── Storage ──────────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, "r") as f:
        return json.load(f)


def _save(reminders: list[dict]) -> None:
    os.makedirs("data", exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)


def _next_id(reminders: list[dict]) -> int:
    return max((r["id"] for r in reminders), default=0) + 1


# ── Background watcher ───────────────────────────────────────────────────────

def _watch() -> None:
    while _running:
        reminders = _load()
        now       = datetime.now(pytz.UTC).isoformat()
        updated   = False
        for r in reminders:
            if not r.get("fired") and r["due"] <= now:
                _notify(r["message"])
                r["fired"] = True
                updated    = True
        if updated:
            _save(reminders)
        time.sleep(1)


def start_reminder_watcher() -> None:
    global _reminder_thread, _running
    _running          = True
    _reminder_thread  = threading.Thread(target=_watch, daemon=True)
    _reminder_thread.start()


# ── Public tool functions ─────────────────────────────────────────────────────

def set_reminder(message: str, minutes_from_now: int = 5) -> str:
    if minutes_from_now <= 0:
        return "Please set a reminder at least 1 minute from now."
    if minutes_from_now > 1440:
        return "Maximum reminder time is 24 hours (1440 minutes)."

    reminders = _load()
    due       = (datetime.now(pytz.UTC) + timedelta(minutes=minutes_from_now)).isoformat()
    reminder  = {
        "id":      _next_id(reminders),
        "message": message,
        "due":     due,
        "fired":   False,
        "created": datetime.now(pytz.UTC).isoformat(),
    }
    reminders.append(reminder)
    _save(reminders)
    plural = "s" if minutes_from_now != 1 else ""
    return f"Reminder set: '{message}' in {minutes_from_now} minute{plural}."


def list_reminders() -> str:
    reminders = _load()
    upcoming  = [r for r in reminders if not r.get("fired")]
    if not upcoming:
        return "No upcoming reminders."
    lines = []
    for r in upcoming:
        due = datetime.fromisoformat(r["due"]).strftime("%I:%M %p")
        lines.append(f"[{r['id']}] {r['message']} — due at {due} UTC")
    return "\n".join(lines)


def cancel_reminder(reminder_id: int) -> str:
    reminders = _load()
    filtered  = [r for r in reminders if r["id"] != reminder_id]
    if len(filtered) == len(reminders):
        return f"No reminder found with ID {reminder_id}."
    _save(filtered)
    return f"Reminder {reminder_id} cancelled."


def purge_fired_reminders() -> str:
    """Remove all already-fired reminders from storage."""
    reminders = _load()
    active    = [r for r in reminders if not r.get("fired")]
    removed   = len(reminders) - len(active)
    _save(active)
    return f"Cleared {removed} fired reminder{'s' if removed != 1 else ''}."