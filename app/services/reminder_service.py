"""Reminder service for P1 — barber-initiated client reminders."""
import logging
from typing import List, Optional
from app.db.base import fetch_all, fetch_one, execute_write
from app.utils.time_utils import tashkent_now

logger = logging.getLogger("barbershop")


async def get_clients_not_visited(barber_id: int, days: int) -> List[dict]:
    """Get clients who had DONE bookings with this barber but haven't visited in N days.
    Excludes clients already reminded (in reminder_log).
    """
    cutoff = (tashkent_now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d')
    return await fetch_all(
        """SELECT c.telegram_id, c.name, c.phone,
                  MAX(b.date) as last_visit
           FROM bookings b
           JOIN clients c ON b.client_id = c.telegram_id
           WHERE b.barber_id = ? AND b.status = 'DONE'
             AND b.client_id NOT IN (
                 SELECT client_id FROM reminder_log WHERE barber_id = ?
             )
           GROUP BY c.telegram_id
           HAVING MAX(b.date) <= ?
           ORDER BY MAX(b.date) ASC""",
        (barber_id, barber_id, cutoff),
    )


async def mark_reminder_sent(barber_id: int, client_id: int):
    """Record that a reminder was sent to this client by this barber."""
    await execute_write(
        "INSERT OR REPLACE INTO reminder_log (barber_id, client_id, sent_at) VALUES (?, ?, ?)",
        (barber_id, client_id, tashkent_now().strftime('%Y-%m-%d %H:%M:%S')),
    )


async def get_reminder_count(barber_id: int) -> int:
    """Get total reminders sent by barber."""
    row = await fetch_one(
        "SELECT COUNT(*) as cnt FROM reminder_log WHERE barber_id = ?",
        (barber_id,),
    )
    return row["cnt"] if row else 0


async def get_barbers_with_auto_reminders() -> List[dict]:
    """Get all ACTIVE premium barbers who have automated reminders enabled."""
    return await fetch_all(
        "SELECT * FROM barbers WHERE premium_status = 'ACTIVE' AND auto_reminder_days > 0"
    )


async def get_clients_for_auto_reminder(barber_id: int, days: int) -> List[dict]:
    """Get clients whose last DONE visit was exactly N days ago with this barber."""
    from datetime import timedelta
    cutoff_date = (tashkent_now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    return await fetch_all(
        """SELECT c.telegram_id, c.name, c.phone, c.lang,
                  MAX(b.date) as last_visit
           FROM bookings b
           JOIN clients c ON b.client_id = c.telegram_id
           WHERE b.barber_id = ? AND b.status = 'DONE'
           GROUP BY c.telegram_id
           HAVING MAX(b.date) = ?
           ORDER BY c.telegram_id ASC""",
        (barber_id, cutoff_date),
    )


async def run_daily_auto_reminders(bot):
    """Find all barbers with auto-reminders and send them to matching clients."""
    import asyncio
    from app.config import BROADCAST_BATCH_SIZE, BROADCAST_PAUSE_SECONDS
    from app.i18n.uz import TEXTS_UZ
    from app.i18n.ru import TEXTS_RU

    barbers = await get_barbers_with_auto_reminders()
    if not barbers:
        return

    for barber in barbers:
        barber_id = barber["telegram_id"]
        days = barber["auto_reminder_days"]
        
        clients = await get_clients_for_auto_reminder(barber_id, days)
        if not clients:
            continue

        bot_info = await bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=ref_{barber.get('id') or barber_id}"

        for i, client in enumerate(clients):
            try:
                lang = client.get("lang", "uz")
                texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
                
                text = texts["reminder_text"].format(
                    name=client["name"],
                    days=days,
                    link=link,
                )
                await bot.send_message(chat_id=client["telegram_id"], text=text)
                await mark_reminder_sent(barber_id, client["telegram_id"])
                
                # Rate limit within one barber's broadcast
                if (i + 1) % BROADCAST_BATCH_SIZE == 0:
                    await asyncio.sleep(BROADCAST_PAUSE_SECONDS)
            except Exception as e:
                logger.error(f"Auto-reminder failed for client {client['telegram_id']} (barber {barber_id}): {e}")
        
        # Pause between barbers to avoid global rate limits
        await asyncio.sleep(1)
