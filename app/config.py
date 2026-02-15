import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: List[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "data" / "barbershop.db"))

# Timezone
TIMEZONE = "Asia/Tashkent"
UTC_OFFSET_HOURS = 5

# Rate limit
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_HITS = 20

# Draft expiry
DRAFT_EXPIRY_SECONDS = 240  # 4 minutes

# Booking cancel threshold
CANCEL_THRESHOLD_SECONDS = 3600  # 1 hour

# Broadcast throttle
BROADCAST_BATCH_SIZE = 25
BROADCAST_PAUSE_SECONDS = 1

# Media limits
MAX_PHOTOS = 10
MAX_VIDEOS = 10

# Pagination
PAGE_SIZE = 8

# Work hours
WORK_HOUR_START = 8   # 08:00
WORK_HOUR_END = 23    # 23:00
TOTAL_SLOTS = 16      # 08:00 - 23:00 inclusive
