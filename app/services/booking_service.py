from typing import List, Optional, Union, Dict
from app.db.base import fetch_one, fetch_all, execute_write, execute_write_returning


async def create_draft_booking(barber_id: int, client_id: int, date: str, hour_slot: int) -> int:
    """Create a DRAFT booking. Returns booking ID."""
    # Expire any existing drafts for this client immediately
    await execute_write(
        "UPDATE bookings SET status = 'EXPIRED' WHERE client_id = ? AND status = 'DRAFT'",
        (client_id,),
    )
    return await execute_write_returning(
        "INSERT INTO bookings (barber_id, client_id, date, hour_slot, status, created_at) "
        "VALUES (?, ?, ?, ?, 'DRAFT', datetime('now'))",
        (barber_id, client_id, date, hour_slot),
    )


async def confirm_booking(booking_id: int) -> bool:
    """
    Confirm a DRAFT booking. Returns True if successful.
    Checks that the slot is not already CONFIRMED by another client.
    """
    booking = await get_booking(booking_id)
    if not booking or booking["status"] != "DRAFT":
        return False

    # Check for slot collision
    existing = await fetch_one(
        """SELECT id FROM bookings
           WHERE barber_id = ? AND date = ? AND hour_slot = ? AND status = 'CONFIRMED' AND id != ?""",
        (booking["barber_id"], booking["date"], booking["hour_slot"], booking_id),
    )
    if existing:
        return False

    await execute_write(
        "UPDATE bookings SET status = 'CONFIRMED', confirmed_at = datetime('now') WHERE id = ?",
        (booking_id,),
    )
    return True


async def cancel_booking(booking_id: int):
    await execute_write(
        "UPDATE bookings SET status = 'CANCELLED' WHERE id = ?",
        (booking_id,),
    )


async def mark_booking_done(booking_id: int):
    await execute_write(
        "UPDATE bookings SET status = 'DONE' WHERE id = ?",
        (booking_id,),
    )


async def expire_booking(booking_id: int):
    await execute_write(
        "UPDATE bookings SET status = 'EXPIRED' WHERE id = ? AND status = 'DRAFT'",
        (booking_id,),
    )


async def get_booking(booking_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM bookings WHERE id = ?", (booking_id,))


async def get_confirmed_slots(barber_id: int, date: str) -> List[int]:
    """Get list of hour_slots that are CONFIRMED for a barber on a date."""
    rows = await fetch_all(
        "SELECT hour_slot FROM bookings WHERE barber_id = ? AND date = ? AND status = 'CONFIRMED'",
        (barber_id, date),
    )
    return [r["hour_slot"] for r in rows]


async def get_client_active_draft(client_id: int) -> Optional[dict]:
    """Get active DRAFT booking for a client."""
    return await fetch_one(
        "SELECT * FROM bookings WHERE client_id = ? AND status = 'DRAFT' ORDER BY created_at DESC LIMIT 1",
        (client_id,),
    )


async def get_client_unrated_done(client_id: int) -> Optional[dict]:
    """Check if client has a DONE booking without rating."""
    return await fetch_one(
        """SELECT b.* FROM bookings b
           LEFT JOIN ratings r ON b.id = r.booking_id
           WHERE b.client_id = ? AND b.status = 'DONE' AND r.id IS NULL
           LIMIT 1""",
        (client_id,),
    )


async def get_client_cancelled_today(client_id: int, today: str) -> Optional[dict]:
    """Check if client has a penalty (cancelled with <1hr remaining today)."""
    # Check both cancelled bookings (historical logic) and new penalties table
    penalty = await fetch_one(
        "SELECT * FROM penalties WHERE client_id = ? AND date = ? LIMIT 1",
        (client_id, today)
    )
    if penalty:
        return penalty
        
    return await fetch_one(
        """SELECT * FROM bookings
           WHERE client_id = ? AND date = ? AND status = 'CANCELLED'
           AND confirmed_at IS NOT NULL
           ORDER BY created_at DESC LIMIT 1""",
        (client_id, today),
    )


async def add_penalty(client_id: int, date: str, reason: str):
    """Record a penalty for a client."""
    await execute_write(
        "INSERT INTO penalties (client_id, date, reason) VALUES (?, ?, ?)",
        (client_id, date, reason)
    )


async def get_barber_bookings_for_date(barber_id: int, date: str) -> List[dict]:
    """Get all CONFIRMED bookings for a barber on a date."""
    return await fetch_all(
        """SELECT b.*, c.name as client_name, c.phone as client_phone
           FROM bookings b
           JOIN clients c ON b.client_id = c.telegram_id
           WHERE b.barber_id = ? AND b.date = ? AND b.status = 'CONFIRMED'
           ORDER BY b.hour_slot""",
        (barber_id, date),
    )


async def auto_close_past_bookings(today: str):
    """Set all past CONFIRMED bookings to DONE."""
    await execute_write(
        "UPDATE bookings SET status = 'DONE' WHERE status = 'CONFIRMED' AND date < ?",
        (today,),
    )


async def expire_old_drafts():
    """Expire drafts older than 4 minutes (Phase 4 requirement)."""
    await execute_write(
        "UPDATE bookings SET status = 'EXPIRED' WHERE status = 'DRAFT' "
        "AND created_at < datetime('now', '-4 minutes')"
    )

async def get_client_future_confirmed_bookings(client_id: int) -> List[dict]:
    """Get all future CONFIRMED bookings for a client."""
    from app.utils.time_utils import today_tashkent
    today = today_tashkent()
    # Simple check: date >= today. stricter check requires time logic.
    # For now, let's fetch >= today and filter in python or SQL if needed.
    # We want to show details including barber info.
    return await fetch_all(
        """SELECT b.*, bar.name as barber_name, bar.phone as barber_phone, 
                  bar.salon_name, bar.lat, bar.lon, bar.photo_file_id
           FROM bookings b
           JOIN barbers bar ON b.barber_id = bar.telegram_id
           WHERE b.client_id = ? AND b.status = 'CONFIRMED' AND b.date >= ?
           ORDER BY b.date, b.hour_slot""",
        (client_id, today),
    )
async def get_client_active_booking(client_id: int) -> Optional[dict]:
    """
    Get a single CONFIRMED booking for client that is in the future or current hour.
    Includes barber details.
    """
    from app.utils.time_utils import today_tashkent, now_tashkent, slot_to_hour
    today = today_tashkent()
    now = now_tashkent()
    
    # We fetch all (there should be max 1-2 if logic was loose) and filter strictly in python
    bookings = await get_client_future_confirmed_bookings(client_id)
    
    for b in bookings:
        if b["date"] > today:
            return b
        elif b["date"] == today:
            # If start_hour=14, it is active until 15:00.
            # slot_to_hour(14) -> 14.
            # 14 + 1 = 15. If now.hour < 15, it's active.
            if slot_to_hour(b["hour_slot"]) + 1 > now.hour:
                return b
    return None


async def get_client_today_usage(client_id: int, today: str) -> Optional[dict]:
    """
    Check if client has ANY booking today that effectively uses their daily slot.
    This includes:
    - DONE bookings.
    - CONFIRMED bookings for today (even if past hour, if not cancelled).
    Purpose: strict 1-booking-per-day limit.
    """
    return await fetch_one(
        "SELECT * FROM bookings WHERE client_id = ? AND date = ? AND status IN ('DONE', 'CONFIRMED') LIMIT 1",
        (client_id, today)
    )

async def get_confirmed_bookings_to_finish(date: str, current_hour: int) -> List[Dict]:
    """
    Get all CONFIRMED bookings for a date that have finished.
    A booking for 09:00 (slot 1) is considered finished at 10:00.
    """
    from app.config import WORK_HOUR_START
    # Example: if current_hour is 10, limit_slot is 10 - 8 - 1 = 1.
    # Slots <= 1 (08:00, 09:00) are marked DONE.
    limit_slot = current_hour - WORK_HOUR_START - 1
    return await fetch_all(
        "SELECT * FROM bookings WHERE date = ? AND status = 'CONFIRMED' AND hour_slot <= ?",
        (date, limit_slot)
    )
