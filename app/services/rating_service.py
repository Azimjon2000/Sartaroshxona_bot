from app.db.base import fetch_one, execute_write


from typing import Optional


async def create_rating(booking_id: int, barber_id: int, client_id: int, stars: int, comment: Optional[str] = None):
    await execute_write(
        "INSERT INTO ratings (booking_id, barber_id, client_id, stars, comment) VALUES (?, ?, ?, ?, ?)",
        (booking_id, barber_id, client_id, stars, comment),
    )


async def update_comment(booking_id: int, comment: str):
    await execute_write(
        "UPDATE ratings SET comment = ? WHERE booking_id = ?",
        (comment, booking_id),
    )


async def get_rating_by_booking(booking_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM ratings WHERE booking_id = ?", (booking_id,))
