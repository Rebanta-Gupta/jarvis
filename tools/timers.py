import threading
import time

# Stores active timers: name → thread
_active_timers: dict[str, threading.Timer] = {}

def set_timer(duration_seconds: int, label: str = "Timer") -> str:
    """Set a timer that alerts after duration_seconds."""
    if duration_seconds <= 0:
        return "Duration must be greater than zero."
    if duration_seconds > 86400:
        return "Maximum timer duration is 24 hours."

    def _alert():
        print(f"\n⏰ [{label}] Time's up!\nYou: ", end="", flush=True)
        _active_timers.pop(label, None)

    # Cancel existing timer with same label
    if label in _active_timers:
        _active_timers[label].cancel()

    timer = threading.Timer(duration_seconds, _alert)
    timer.daemon = True
    timer.start()
    _active_timers[label] = timer

    minutes, seconds = divmod(duration_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")

    return f"Timer '{label}' set for {' '.join(parts)}."

def cancel_timer(label: str = "Timer") -> str:
    """Cancel an active timer by label."""
    if label in _active_timers:
        _active_timers[label].cancel()
        _active_timers.pop(label)
        return f"Timer '{label}' cancelled."
    return f"No active timer named '{label}'."

def list_timers() -> str:
    """List all active timers."""
    if not _active_timers:
        return "No active timers."
    return "Active timers: " + ", ".join(_active_timers.keys())