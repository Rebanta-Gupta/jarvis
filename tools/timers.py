import threading
import time as _time

_active_timers: dict[str, dict] = {}  # label → {timer, start, duration}
_notify_handler = None


def set_notify_handler(fn) -> None:
    """Register a callable(label: str) used when a timer fires."""
    global _notify_handler
    _notify_handler = fn


def _notify(label: str) -> None:
    if _notify_handler:
        try:
            _notify_handler(f"Timer '{label}' is done!")
        except Exception as e:
            print(f"[Timers] Notify handler error: {e}")
    print(f"\n⏰ [{label}] Time's up!", flush=True)


def set_timer(duration_seconds: int, label: str = "Timer") -> str:
    if duration_seconds <= 0:
        return "Duration must be greater than zero."
    if duration_seconds > 86400:
        return "Maximum timer duration is 24 hours."

    overwriting = label in _active_timers
    if overwriting:
        _active_timers[label]["timer"].cancel()

    def _alert():
        _notify(label)
        _active_timers.pop(label, None)

    timer = threading.Timer(duration_seconds, _alert)
    timer.daemon = True
    timer.start()
    _active_timers[label] = {
        "timer":    timer,
        "start":    _time.monotonic(),
        "duration": duration_seconds,
    }

    minutes, seconds = divmod(duration_seconds, 60)
    hours,   minutes = divmod(minutes, 60)
    parts = []
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    label_str = " ".join(parts)

    if overwriting:
        return f"Timer '{label}' restarted for {label_str}."
    return f"Timer '{label}' set for {label_str}."


def cancel_timer(label: str = "Timer") -> str:
    if label not in _active_timers:
        return f"No active timer named '{label}'."
    _active_timers[label]["timer"].cancel()
    _active_timers.pop(label)
    return f"Timer '{label}' cancelled."


def get_timer_remaining(label: str = "Timer") -> str:
    if label not in _active_timers:
        return f"No active timer named '{label}'."
    entry   = _active_timers[label]
    elapsed = _time.monotonic() - entry["start"]
    left    = max(0, entry["duration"] - elapsed)
    minutes, seconds = divmod(int(left), 60)
    if minutes:
        return f"Timer '{label}' has {minutes}m {seconds}s remaining."
    return f"Timer '{label}' has {seconds}s remaining."


def list_timers() -> str:
    if not _active_timers:
        return "No active timers."
    parts = []
    for label, entry in _active_timers.items():
        elapsed = _time.monotonic() - entry["start"]
        left    = max(0, entry["duration"] - elapsed)
        m, s    = divmod(int(left), 60)
        parts.append(f"'{label}' — {m}m {s}s left")
    return "Active timers: " + ", ".join(parts)