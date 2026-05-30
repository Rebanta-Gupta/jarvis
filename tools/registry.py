from tools.system    import get_datetime, get_date, get_time
from tools.weather   import get_weather
from tools.timers    import set_timer, cancel_timer, list_timers, get_timer_remaining
from tools.notes     import add_note, get_notes, search_notes, delete_note
from tools.reminders import set_reminder, list_reminders, cancel_reminder
from tools.memory_tools import remember_fact, forget_fact, forget_all, recall_facts

TOOL_DEFINITIONS = [
    # ── Time ──────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current date AND time together. Use for 'what time is it', 'what's today's date', or any combined date-time question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone e.g. America/Vancouver"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time only (no date). Use when the user asks specifically for the time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get today's date only (no time). Use when the user asks specifically for the date or day.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"}
                },
                "required": [],
            },
        },
    },
    # ── Weather ────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for any city worldwide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name e.g. 'Vancouver', 'Tokyo', 'Maple Ridge'"}
                },
                "required": ["city"],
            },
        },
    },
    # ── Timers ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer. Use when the user says 'set a timer for X minutes/seconds'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {"type": "integer", "description": "Timer duration in seconds. Convert minutes to seconds first."},
                    "label": {"type": "string", "description": "Short name for the timer e.g. 'pasta', 'workout'"}
                },
                "required": ["duration_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timer",
            "description": "Cancel an active timer by its label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"}
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timer_remaining",
            "description": "Check how much time is left on an active timer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"}
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timers",
            "description": "List all currently active timers with remaining time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Notes ──────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Save a note. Use when the user says 'note that', 'write this down', or 'remember this'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The full text of the note"},
                    "title":   {"type": "string", "description": "Optional short title"}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": "Read back recent notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "How many recent notes to return (default 5)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search notes by keyword. Use when the user asks to find a specific note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search for"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_note",
            "description": "Delete a note by its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer"}
                },
                "required": ["note_id"],
            },
        },
    },
    # ── Reminders ──────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder for N minutes from now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message":          {"type": "string",  "description": "What to remind the user about"},
                    "minutes_from_now": {"type": "integer", "description": "How many minutes until the reminder fires"}
                },
                "required": ["message", "minutes_from_now"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List all upcoming (unfired) reminders.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "Cancel a reminder by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer"}
                },
                "required": ["reminder_id"],
            },
        },
    },
    # ── Memory ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Store or update a fact about the user. Use when they say 'remember that', 'my X is Y'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key":   {"type": "string", "description": "snake_case identifier e.g. 'favourite_colour'"},
                    "value": {"type": "string"}
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_fact",
            "description": "Delete a specific stored fact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_all",
            "description": "Delete ALL stored facts. Only use when the user explicitly asks to forget everything.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_facts",
            "description": "List what Jarvis knows about the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword filter"}
                },
                "required": [],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_datetime":       get_datetime,
    "get_date":           get_date,
    "get_time":           get_time,
    "get_weather":        get_weather,
    "set_timer":          set_timer,
    "cancel_timer":       cancel_timer,
    "get_timer_remaining": get_timer_remaining,
    "list_timers":        list_timers,
    "add_note":           add_note,
    "get_notes":          get_notes,
    "search_notes":       search_notes,
    "delete_note":        delete_note,
    "set_reminder":       set_reminder,
    "list_reminders":     list_reminders,
    "cancel_reminder":    cancel_reminder,
    "remember_fact":      remember_fact,
    "forget_fact":        forget_fact,
    "forget_all":         forget_all,
    "recall_facts":       recall_facts,
}


def run_tool(name: str, args: dict) -> str:
    """Dispatch a tool call. Always returns a string — never raises."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Error: unknown tool '{name}'"
    try:
        return str(func(**(args or {})))
    except TypeError as e:
        return f"Error calling '{name}': bad arguments — {e}"
    except Exception as e:
        return f"Error calling '{name}': {e}"