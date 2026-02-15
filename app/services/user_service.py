from app.db.base import fetch_one, fetch_all, execute_write


from typing import Optional


async def get_user(telegram_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))


async def upsert_user(telegram_id: int, role: str):
    await execute_write(
        "INSERT INTO users (telegram_id, role) VALUES (?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET role = excluded.role",
        (telegram_id, role),
    )


async def delete_user(telegram_id: int):
    """Hard delete user and all related data."""
    await execute_write("DELETE FROM ratings WHERE client_id = ?", (telegram_id,))
    await execute_write("DELETE FROM bookings WHERE client_id = ?", (telegram_id,))
    await execute_write("DELETE FROM bookings WHERE barber_id = ?", (telegram_id,))
    await execute_write("DELETE FROM media_photos WHERE barber_id = ?", (telegram_id,))
    await execute_write("DELETE FROM media_videos WHERE barber_id = ?", (telegram_id,))
    await execute_write("DELETE FROM work_hours WHERE barber_id = ?", (telegram_id,))
    await execute_write("DELETE FROM services_prices WHERE barber_id = ?", (telegram_id,))
    await execute_write("DELETE FROM barbers WHERE telegram_id = ?", (telegram_id,))
    await execute_write("DELETE FROM clients WHERE telegram_id = ?", (telegram_id,))
    await execute_write("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
    await execute_write("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))


async def get_total_users() -> int:
    row = await fetch_one("SELECT COUNT(*) as cnt FROM users")
    return row["cnt"] if row else 0
