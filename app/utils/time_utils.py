from datetime import datetime, timedelta, timezone

from app.config import UTC_OFFSET_HOURS, WORK_HOUR_START

TZ_TASHKENT = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def now_tashkent() -> datetime:
    """Current time in Asia/Tashkent."""
    return datetime.now(TZ_TASHKENT)


def today_tashkent() -> str:
    """Today's date string YYYY-MM-DD in Asia/Tashkent."""
    return now_tashkent().strftime("%Y-%m-%d")


def slot_to_hour(slot: int) -> int:
    """Convert slot index (0..15) to hour (8..23)."""
    return WORK_HOUR_START + slot


def hour_to_slot(hour: int) -> int:
    """Convert hour (8..23) to slot index (0..15)."""
    return hour - WORK_HOUR_START


def slot_datetime(date_str: str, slot: int) -> datetime:
    """Create a datetime for a given date string and slot."""
    hour = slot_to_hour(slot)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(hour=hour, minute=0, second=0, tzinfo=TZ_TASHKENT)
    return dt


def end_of_day_tashkent() -> datetime:
    """Today 23:59:59 in Asia/Tashkent."""
    now = now_tashkent()
    return now.replace(hour=23, minute=59, second=59, microsecond=0)


def seconds_until_slot(date_str: str, slot: int) -> float:
    """Seconds from now until the slot time. Negative if in the past."""
    slot_dt = slot_datetime(date_str, slot)
    delta = slot_dt - now_tashkent()
    return delta.total_seconds()


# Aliases for newer code (Phase 10)
tashkent_now = now_tashkent
today_uz_str = today_tashkent
