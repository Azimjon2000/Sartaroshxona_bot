import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import aiosqlite

from app.config import DB_PATH
from app.utils.time_utils import tashkent_now

logger = logging.getLogger("barbershop")


async def column_exists(db: aiosqlite.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a given SQLite table."""
    try:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        columns = await cursor.fetchall()
        for col in columns:
            if col["name"] == column:
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking column {column} in {table}: {e}")
        return False


async def run_migrations():
    """Run safe database migrations with automatic backup and rollback."""
    db_file = Path(DB_PATH)
    if not db_file.exists():
        logger.info("Database file does not exist yet. Skipping migrations.")
        return

    # 1. Create a safe backup before any ALTER operations
    backup_path = f"{DB_PATH}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DB_PATH, backup_path)
    logger.info(f"Database backed up successfully to {backup_path}")

    from app.db.base import get_db
    
    db = await get_db()
    
    try:
        # ---------------------------------------------------------------------
        # A) barbers table migration
        # ---------------------------------------------------------------------
        if not await column_exists(db, "barbers", "id"):
            logger.info("Migrating barbers: adding 'id' column and backfilling")
            logger.info("Migrating barbers: adding 'id' column")
            await db.execute("ALTER TABLE barbers ADD COLUMN id INTEGER;")
            await db.commit()

        # Always ensure id is backfilled (for those registered between migration and service fix)
        # This must run AFTER the column is guaranteed to exist.
        logger.info("Backfilling barbers.id with telegram_id if NULL.")
        await db.execute("UPDATE barbers SET id = telegram_id WHERE id IS NULL;")
        await db.commit()

        if not await column_exists(db, "barbers", "auto_reminder_days"):
            logger.info("Migrating barbers: adding 'auto_reminder_days' column")
            await db.execute("ALTER TABLE barbers ADD COLUMN auto_reminder_days INTEGER DEFAULT 0;")
            await db.commit()

        if not await column_exists(db, "barbers", "premium_status"):
            logger.info("Migrating barbers: adding premium columns")
            await db.execute("ALTER TABLE barbers ADD COLUMN premium_status TEXT DEFAULT 'INACTIVE';")
            await db.execute("ALTER TABLE barbers ADD COLUMN premium_until TEXT;")
            await db.execute("ALTER TABLE barbers ADD COLUMN is_blocked_temp INTEGER DEFAULT 0;")
            await db.commit()

        # ---------------------------------------------------------------------
        # B) clients table migration
        # ---------------------------------------------------------------------
        if not await column_exists(db, "clients", "ref_barber_id"):
            logger.info("Migrating clients: adding ref_barber_id and ref_lock_date")
            await db.execute("ALTER TABLE clients ADD COLUMN ref_barber_id INTEGER;")
            await db.execute("ALTER TABLE clients ADD COLUMN ref_lock_date TEXT;")
            await db.commit()

        # ---------------------------------------------------------------------
        # C) bookings table migration
        # ---------------------------------------------------------------------
        if not await column_exists(db, "bookings", "created_date"):
            logger.info("Migrating bookings: adding created_date, is_active, reminded")
            await db.execute("ALTER TABLE bookings ADD COLUMN reminded INTEGER DEFAULT 0;")
            await db.execute("ALTER TABLE bookings ADD COLUMN created_date TEXT;")
            await db.execute("ALTER TABLE bookings ADD COLUMN is_active INTEGER DEFAULT 1;")
            
            # Backfill logic
            current_date_uz = tashkent_now().strftime('%Y-%m-%d')
            await db.execute("UPDATE bookings SET created_date = ? WHERE created_date IS NULL;", (current_date_uz,))
            await db.execute("UPDATE bookings SET is_active=0 WHERE status IN ('DONE','CANCELLED','EXPIRED');")
            await db.execute("UPDATE bookings SET is_active=1 WHERE status IN ('DRAFT','CONFIRMED');")
            
            # Assertions to ensure safety
            cursor = await db.execute("SELECT COUNT(*) FROM bookings WHERE created_date IS NULL")
            null_count_bookings = (await cursor.fetchone())[0]
            if null_count_bookings > 0:
                raise Exception("Migration failed safely trigger rollback: bookings.created_date has NULL values")
                
            await db.commit()

        # ---------------------------------------------------------------------
        # D) settings table backfill
        # ---------------------------------------------------------------------
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_profile', '@admin');")
        await db.commit()

        # ---------------------------------------------------------------------
        # E) reminder_log table
        # ---------------------------------------------------------------------
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminder_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                barber_id  INTEGER NOT NULL,
                client_id  INTEGER NOT NULL,
                sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(barber_id, client_id),
                FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (client_id) REFERENCES clients(telegram_id) ON DELETE CASCADE
            );
        """)
        await db.commit()

        # ---------------------------------------------------------------------
        # F) Additional indexes
        # ---------------------------------------------------------------------
        await db.execute("CREATE INDEX IF NOT EXISTS idx_barbers_premium ON barbers(premium_status, premium_until);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bookings_reminded ON bookings(date, status, reminded);")
        await db.commit()

        logger.info("All DB migrations completed successfully.")

    except Exception as e:
        await db.rollback()
        logger.critical(f"Database Migration FAILED. Rollback executed. Original DB remains intact. Error: {e}")
        import sys
        sys.exit(1)  # Stop bot startup to protect data
    finally:
        await db.close()
