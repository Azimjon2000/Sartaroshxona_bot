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


async def send_premium_reminders(today: str, now, bot):
    """P4: Send 2-hour reminders for bookings of ACTIVE premium barbers only."""
    import logging
    from app.utils.time_utils import slot_to_hour
    logger = logging.getLogger("barbershop")
    
    target_slot = now.hour + 2 - 8  # convert hour to slot index (WORK_HOUR_START=8)
    if target_slot < 0 or target_slot > 15:
        return
    
    query = """
        SELECT b.*, c.lang, c.name as client_name,
               br.name as barber_name, br.phone as barber_phone,
               br.lat as barber_lat, br.lon as barber_lon,
               br.salon_name
        FROM bookings b
        JOIN barbers br ON b.barber_id = br.telegram_id
        JOIN clients c ON b.client_id = c.telegram_id
        WHERE b.date = ? 
          AND b.status = 'CONFIRMED'
          AND b.hour_slot = ?
          AND b.reminded = 0
          AND br.premium_status = 'ACTIVE'
    """
    to_remind = await fetch_all(query, (today, target_slot))
    
    for b in to_remind:
        try:
            target_hour = slot_to_hour(b["hour_slot"])
            loc_link = ""
            if b.get("barber_lat") and b.get("barber_lon"):
                loc_link = f"\n📍 https://www.google.com/maps/search/?api=1&query={b['barber_lat']},{b['barber_lon']}"
            
            text = (
                f"⏰ {b['barber_name']}ga soat {target_hour:02d}:00 ga yozilgansiz.\n"
                f"💈 {b.get('salon_name', '')}"
                f"{loc_link}\n"
                f"📞 {b.get('barber_phone', '')}"
            )
            await bot.send_message(chat_id=b["client_id"], text=text)
            await execute_write("UPDATE bookings SET reminded = 1 WHERE id = ?", (b["id"],))
        except Exception as e:
            logger.error(f"Failed to remind booking {b['id']}: {e}")


async def get_client_future_confirmed_bookings(client_id: int) -> List[dict]:
    """Get all future CONFIRMED bookings for a client."""
    from app.utils.time_utils import today_tashkent
    today = today_tashkent()
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
    """Get a single CONFIRMED booking for client that is in the future or current hour."""
    from app.utils.time_utils import today_tashkent, now_tashkent, slot_to_hour
    today = today_tashkent()
    now = now_tashkent()
    
    bookings = await get_client_future_confirmed_bookings(client_id)
    
    for b in bookings:
        if b["date"] > today:
            return b
        elif b["date"] == today:
            if slot_to_hour(b["hour_slot"]) + 1 > now.hour:
                return b
    return None


async def get_client_today_usage(client_id: int, today: str) -> Optional[dict]:
    """Check if client has ANY booking today that uses their daily slot."""
    return await fetch_one(
        "SELECT * FROM bookings WHERE client_id = ? AND date = ? AND status IN ('DONE', 'CONFIRMED') LIMIT 1",
        (client_id, today)
    )


async def get_client_booking_for_date(client_id: int, date: str) -> Optional[dict]:
    """Check if client already has an active booking for a specific date."""
    return await fetch_one(
        "SELECT * FROM bookings WHERE client_id = ? AND date = ? AND status IN ('DRAFT', 'CONFIRMED') LIMIT 1",
        (client_id, date)
    )


async def get_confirmed_bookings_to_finish(date: str, current_hour: int) -> List[Dict]:
    """Get all CONFIRMED bookings for a date that have finished."""
    from app.config import WORK_HOUR_START
    limit_slot = current_hour - WORK_HOUR_START - 1
    return await fetch_all(
        "SELECT * FROM bookings WHERE date = ? AND status = 'CONFIRMED' AND hour_slot <= ?",
        (date, limit_slot)
    )


# ═══════════════════════════════════════════
# P3 — Client Analytics
# ═══════════════════════════════════════════

async def get_analytics_clients(barber_id: int, category: str) -> List[dict]:
    """Get client analytics for a barber.
    category: 'kamnamo' (90 days no visit), 'doimiy' (2+ in 90d), 'yoqotilgan' (180d no visit)
    """
    from app.utils.time_utils import tashkent_now
    from datetime import timedelta
    now = tashkent_now()

    if category == "kamnamo":
        cutoff = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        return await fetch_all(
            """SELECT c.telegram_id, c.name, c.phone, MAX(b.date) as last_visit, COUNT(b.id) as total
               FROM bookings b JOIN clients c ON b.client_id = c.telegram_id
               WHERE b.barber_id = ? AND b.status = 'DONE'
               GROUP BY c.telegram_id
               HAVING MAX(b.date) < ?
               ORDER BY MAX(b.date) ASC""",
            (barber_id, cutoff),
        )
    elif category == "doimiy":
        cutoff = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        return await fetch_all(
            """SELECT c.telegram_id, c.name, c.phone, MAX(b.date) as last_visit, COUNT(b.id) as total
               FROM bookings b JOIN clients c ON b.client_id = c.telegram_id
               WHERE b.barber_id = ? AND b.status = 'DONE' AND b.date >= ?
               GROUP BY c.telegram_id
               HAVING COUNT(b.id) >= 2
               ORDER BY COUNT(b.id) DESC""",
            (barber_id, cutoff),
        )
    elif category == "yoqotilgan":
        cutoff = (now - timedelta(days=180)).strftime('%Y-%m-%d')
        return await fetch_all(
            """SELECT c.telegram_id, c.name, c.phone, MAX(b.date) as last_visit, COUNT(b.id) as total
               FROM bookings b JOIN clients c ON b.client_id = c.telegram_id
               WHERE b.barber_id = ? AND b.status = 'DONE'
               GROUP BY c.telegram_id
               HAVING MAX(b.date) < ?
               ORDER BY MAX(b.date) ASC""",
            (barber_id, cutoff),
        )
    return []


async def get_client_visit_dates(barber_id: int, client_id: int) -> List[dict]:
    """Get all visit dates for a specific client at a specific barber."""
    return await fetch_all(
        "SELECT date, hour_slot FROM bookings WHERE barber_id = ? AND client_id = ? AND status = 'DONE' ORDER BY date DESC",
        (barber_id, client_id),
    )

