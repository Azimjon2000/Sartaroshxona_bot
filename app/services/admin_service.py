from typing import List
from app.db.base import fetch_one, fetch_all, execute_write


async def is_admin(telegram_id: int) -> bool:
    row = await fetch_one("SELECT telegram_id FROM admins WHERE telegram_id = ?", (telegram_id,))
    return row is not None


async def add_admin(telegram_id: int):
    await execute_write(
        "INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)",
        (telegram_id,),
    )


async def remove_admin(telegram_id: int):
    await execute_write("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))


async def get_all_admin_ids() -> List[int]:
    rows = await fetch_all("SELECT telegram_id FROM admins")
    return [r["telegram_id"] for r in rows]


async def get_support_username() -> str:
    row = await fetch_one("SELECT value FROM settings WHERE key = 'support_username'")
    return row["value"] if row else "@admin"


async def set_support_username(username: str):
    await execute_write(
        "INSERT INTO settings (key, value) VALUES ('support_username', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (username,),
    )
