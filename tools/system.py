from datetime import datetime
import pytz
from config import DEFAULT_TIMEZONE


def _now(timezone: str) -> datetime:
    try:
        return datetime.now(pytz.timezone(timezone))
    except pytz.UnknownTimeZoneError:
        return datetime.now(pytz.timezone(DEFAULT_TIMEZONE))


def get_datetime(timezone: str = DEFAULT_TIMEZONE) -> str:
    return _now(timezone).strftime("%A, %B %d %Y — %I:%M %p (%Z)")


def get_date(timezone: str = DEFAULT_TIMEZONE) -> str:
    return _now(timezone).strftime("%A, %B %d %Y")


def get_time(timezone: str = DEFAULT_TIMEZONE) -> str:
    return _now(timezone).strftime("%I:%M %p (%Z)")