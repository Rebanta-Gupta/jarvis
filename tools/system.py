from datetime import datetime
import pytz

def get_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time in the given timezone."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime("%A, %B %d %Y — %I:%M %p (%Z)")
    except pytz.UnknownTimeZoneError:
        # fallback to local system time
        now = datetime.now()
        return now.strftime("%A, %B %d %Y — %I:%M %p (local)")

def get_date(timezone: str = "UTC") -> str:
    """Return just today's date."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except pytz.UnknownTimeZoneError:
        now = datetime.now()
    return now.strftime("%A, %B %d %Y")

def get_time(timezone: str = "UTC") -> str:
    """Return just the current time."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except pytz.UnknownTimeZoneError:
        now = datetime.now()
    return now.strftime("%I:%M %p (%Z)")