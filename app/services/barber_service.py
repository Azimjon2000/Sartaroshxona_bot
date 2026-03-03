from typing import List, Optional, Tuple
from app.db.base import fetch_one, fetch_all, execute_write


async def create_barber(
    telegram_id: int, name: str, phone: str,
    region_id: int, district_id: int,
    salon_name: str, photo_file_id: Optional[str],
    lat: Optional[float], lon: Optional[float],
    lang: str = "uz",
):
    await execute_write(
        """INSERT INTO barbers
           (id, telegram_id, name, phone, region_id, district_id, salon_name,
            photo_file_id, lat, lon, lang)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (telegram_id, telegram_id, name, phone, region_id, district_id,
         salon_name, photo_file_id, lat, lon, lang),
    )
    # Initialize 16 work_hours (all disabled)
    for slot in range(16):
        await execute_write(
            "INSERT OR IGNORE INTO work_hours (barber_id, hour_slot, is_enabled) VALUES (?, ?, 0)",
            (telegram_id, slot),
        )
    # Initialize services_prices
    await execute_write(
        "INSERT OR IGNORE INTO services_prices (barber_id) VALUES (?)",
        (telegram_id,),
    )


async def get_barber(telegram_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM barbers WHERE telegram_id = ?", (telegram_id,))


async def update_auto_reminder_days(telegram_id: int, days: int):
    from app.db.base import execute_write
    await execute_write("UPDATE barbers SET auto_reminder_days = ? WHERE telegram_id = ?", (days, telegram_id))


async def get_barber_by_db_id(db_id: int) -> Optional[dict]:
    """Lookup barber by the helper `id` column (= telegram_id)."""
    return await fetch_one("SELECT * FROM barbers WHERE id = ?", (db_id,))


async def update_barber_status(telegram_id: int, status: str):
    await execute_write(
        "UPDATE barbers SET status = ? WHERE telegram_id = ?",
        (status, telegram_id),
    )


async def update_barber_premium_status(telegram_id: int, status: str, until: Optional[str] = None):
    await execute_write(
        "UPDATE barbers SET premium_status = ?, premium_until = ? WHERE telegram_id = ?",
        (status, until, telegram_id),
    )


async def update_barber_field(telegram_id: int, field: str, value):
    allowed = {"name", "phone", "salon_name", "photo_file_id", "lat", "lon", "lang", "region_id", "district_id", "is_blocked_temp"}
    if field not in allowed:
        raise ValueError(f"Field {field} not allowed")
    await execute_write(
        f"UPDATE barbers SET {field} = ? WHERE telegram_id = ?",
        (value, telegram_id),
    )


async def get_all_barbers(status: Optional[str] = None) -> List[dict]:
    if status:
        return await fetch_all("SELECT * FROM barbers WHERE status = ?", (status,))
    return await fetch_all("SELECT * FROM barbers")


async def get_barbers_by_district(district_id: int) -> List[dict]:
    return await fetch_all(
        "SELECT * FROM barbers WHERE district_id = ? AND status = 'APPROVED'",
        (district_id,),
    )


async def get_approved_barbers_with_location() -> List[dict]:
    return await fetch_all(
        "SELECT * FROM barbers WHERE status = 'APPROVED' AND lat IS NOT NULL AND lon IS NOT NULL"
    )


async def get_barbers_nearby(lat: float, lon: float, radius_km: float) -> List[dict]:
    """Retrieve barbers within a bounding box using SQL, for further haversine filtering."""
    import math
    # 1 degree lat approx 111km
    dlat = radius_km / 111.0
    # 1 degree lon approx 111 * cos(lat) km
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    
    query = """
        SELECT * FROM barbers 
        WHERE status = 'APPROVED' 
          AND lat BETWEEN ? AND ? 
          AND lon BETWEEN ? AND ?
    """
    return await fetch_all(query, (lat - dlat, lat + dlat, lon - dlon, lon + dlon))


async def get_work_hours(barber_id: int) -> List[dict]:
    return await fetch_all(
        "SELECT * FROM work_hours WHERE barber_id = ? ORDER BY hour_slot",
        (barber_id,),
    )


async def toggle_work_hour(barber_id: int, hour_slot: int):
    await execute_write(
        "UPDATE work_hours SET is_enabled = CASE WHEN is_enabled = 1 THEN 0 ELSE 1 END "
        "WHERE barber_id = ? AND hour_slot = ?",
        (barber_id, hour_slot),
    )


async def get_prices(barber_id: int) -> Optional[dict]:
    return await fetch_one("SELECT * FROM services_prices WHERE barber_id = ?", (barber_id,))


async def update_price(barber_id: int, field: str, value):
    allowed = {"hair_price", "beard_price", "groom_price", "extra_note"}
    if field not in allowed:
        raise ValueError(f"Price field {field} not allowed")
    await execute_write(
        f"UPDATE services_prices SET {field} = ? WHERE barber_id = ?",
        (value, barber_id),
    )


async def get_barber_photos(barber_id: int) -> List[dict]:
    return await fetch_all(
        "SELECT * FROM media_photos WHERE barber_id = ? ORDER BY id",
        (barber_id,),
    )


async def add_barber_photo(barber_id: int, file_id: str) -> int:
    from app.config import MAX_PHOTOS
    photos = await get_barber_photos(barber_id)
    if len(photos) >= MAX_PHOTOS:
        raise ValueError(f"Maximum of {MAX_PHOTOS} photos reached")
        
    from app.db.base import execute_write_returning
    return await execute_write_returning(
        "INSERT INTO media_photos (barber_id, file_id) VALUES (?, ?)",
        (barber_id, file_id),
    )


async def delete_barber_photo(photo_id: int):
    await execute_write("DELETE FROM media_photos WHERE id = ?", (photo_id,))


async def get_barber_videos(barber_id: int) -> List[dict]:
    return await fetch_all(
        "SELECT * FROM media_videos WHERE barber_id = ? ORDER BY id",
        (barber_id,),
    )


async def add_barber_video(barber_id: int, file_id: str) -> int:
    from app.config import MAX_VIDEOS
    videos = await get_barber_videos(barber_id)
    if len(videos) >= MAX_VIDEOS:
        raise ValueError(f"Maximum of {MAX_VIDEOS} videos reached")
        
    from app.db.base import execute_write_returning
    return await execute_write_returning(
        "INSERT INTO media_videos (barber_id, file_id) VALUES (?, ?)",
        (barber_id, file_id),
    )


async def delete_barber_video(video_id: int):
    await execute_write("DELETE FROM media_videos WHERE id = ?", (video_id,))


async def get_barber_avg_rating(barber_id: int) -> Tuple[float, int]:
    """Returns (average_stars, count)."""
    row = await fetch_one(
        "SELECT AVG(stars) as avg_stars, COUNT(*) as cnt FROM ratings WHERE barber_id = ?",
        (barber_id,),
    )
    if row and row["cnt"] > 0:
        return round(row["avg_stars"], 1), row["cnt"]
    return 0.0, 0


async def get_barber_served_count(barber_id: int) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) as cnt FROM bookings WHERE barber_id = ? AND status = 'DONE'",
        (barber_id,),
    )
    return row["cnt"] if row else 0


async def get_barber_comments(barber_id: int) -> List[dict]:
    return await fetch_all(
        """SELECT r.comment, c.name as client_name
           FROM ratings r
           JOIN clients c ON r.client_id = c.telegram_id
           WHERE r.barber_id = ? AND r.comment IS NOT NULL AND r.comment != ''
           ORDER BY r.created_at DESC""",
        (barber_id,),
    )


async def auto_expire_premium(today: str):
    """Set premium status to EXPIRED for barbers whose until date has passed."""
    await execute_write(
        "UPDATE barbers SET premium_status = 'EXPIRED', is_blocked_temp = 1 WHERE premium_status = 'ACTIVE' AND premium_until < ?",
        (today,),
    )


async def get_barbers_count() -> int:
    row = await fetch_one("SELECT COUNT(*) as cnt FROM barbers")
    return row["cnt"] if row else 0
