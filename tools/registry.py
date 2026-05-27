from tools.system import get_datetime, get_date, get_time
from tools.weather import get_weather
from tools.timers import set_timer, cancel_timer, list_timers
from tools.notes import add_note, get_notes, delete_note
from tools.reminders import set_reminder, list_reminders, cancel_reminder

TOOL_DEFINITIONS = [
    # ── Time ──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current date and time. Use for any time or date question.",
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
            "description": "Get the current time only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone string."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get today's date only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone string."}
                },
                "required": [],
            },
        },
    },
    # ── Weather ───────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. Use when the user asks about weather, temperature, or conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name e.g. 'Vancouver', 'Toronto', 'London'"}
                },
                "required": ["city"],
            },
        },
    },
    # ── Timers ────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer. Use when the user says 'set a timer for X minutes/seconds'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {"type": "integer", "description": "Timer duration in seconds"},
                    "label": {"type": "string", "description": "A short name for the timer e.g. 'pasta', 'workout'"}
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
                    "label": {"type": "string", "description": "The timer label to cancel"}
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timers",
            "description": "List all currently active timers.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Notes ─────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Save a note. Use when the user says 'note that', 'remember this', or 'write this down'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The full text content of the note to save"
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional short title for the note"
                    }
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": "Read back saved notes. Use when the user asks to see their notes.",
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
            "name": "delete_note",
            "description": "Delete a note by its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "The ID of the note to delete"}
                },
                "required": ["note_id"],
            },
        },
    },
    # ── Reminders ─────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder for N minutes from now. Use when the user says 'remind me in X minutes'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to remind the user about"},
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
            "description": "List all upcoming reminders.",
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
                    "reminder_id": {"type": "integer", "description": "The ID of the reminder to cancel"}
                },
                "required": ["reminder_id"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_datetime": get_datetime,
    "get_date": get_date,
    "get_time": get_time,
    "get_weather": get_weather,
    "set_timer": set_timer,
    "cancel_timer": cancel_timer,
    "list_timers": list_timers,
    "add_note": add_note,
    "get_notes": get_notes,
    "delete_note": delete_note,
    "set_reminder": set_reminder,
    "list_reminders": list_reminders,
    "cancel_reminder": cancel_reminder,
}

def run_tool(name: str, args: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Error: unknown tool '{name}'"
    return str(func(**(args or {})))  # ← args or {} handles None