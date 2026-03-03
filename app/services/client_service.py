from app.db.base import fetch_one, fetch_all, execute_write


from typing import Optional, List


async def create_client(telegram_id: int, name: str, phone: Optional[str] = None, lang: str = "uz"):
    await execute_write(
        "INSERT INTO clients (telegram_id, name, phone, lang) VALUES (?, ?, ?, ?)",
        (telegram_id, name, phone, lang),
    )


async def get_client(telegram_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,))


async def update_client_field(telegram_id: int, field: str, value):
    allowed = {"name", "phone", "lang"}
    if field not in allowed:
        raise ValueError(f"Field {field} not allowed")
    await execute_write(
        f"UPDATE clients SET {field} = ? WHERE telegram_id = ?",
        (value, telegram_id),
    )


async def update_client_lock(telegram_id: int, ref_barber_id: Optional[int], ref_lock_date: Optional[str]):
    await execute_write(
        "UPDATE clients SET ref_barber_id = ?, ref_lock_date = ? WHERE telegram_id = ?",
        (ref_barber_id, ref_lock_date, telegram_id),
    )


async def get_clients_count() -> int:
    row = await fetch_one("SELECT COUNT(*) as cnt FROM clients")
    return row["cnt"] if row else 0


async def get_all_client_ids() -> List[int]:
    rows = await fetch_all("SELECT telegram_id FROM clients")
    return [r["telegram_id"] for r in rows]
