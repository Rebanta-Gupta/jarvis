from datetime import datetime
import pytz

def get_datetime(timezone: str = "America/Vancouver") -> str:
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime("%A, %B %d %Y — %I:%M %p (%Z)")
    except pytz.UnknownTimeZoneError:
        now = datetime.now()
        return now.strftime("%A, %B %d %Y — %I:%M %p (local)")

def get_date(timezone: str = "America/Vancouver") -> str:
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except pytz.UnknownTimeZoneError:
        now = datetime.now()
    return now.strftime("%A, %B %d %Y")

def get_time(timezone: str = "America/Vancouver") -> str:
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except pytz.UnknownTimeZoneError:
        now = datetime.now()
    return now.strftime("%I:%M %p (%Z)")