import asyncio
import logging

from app.loader import bot, dp
from app.db.base import init_db
from app.db.seed import seed_regions
from app.utils.db_migrations import run_migrations
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.i18n import I18nMiddleware

# Import routers
from app.handlers import common, barber_reg, barber_menu, client_reg, client_menu, client_search, rating, admin
from app.handlers import barber_premium_features


from logging.handlers import RotatingFileHandler
import os

# Create data directory for logs if not exists
os.makedirs("data", exist_ok=True)

# 1. Console handler for journald (INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

# 2. Rotating File handler for critical errors (WARNING/ERROR only)
file_handler = RotatingFileHandler(
    filename="data/errors.log",
    maxBytes=2 * 1024 * 1024,  # 2MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

# Noise reduction for 1GB RAM stability
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger("barbershop")


async def seed_admins():
    """Seed admin IDs from config."""
    from app.config import ADMIN_IDS
    from app.services import admin_service, user_service
    for admin_id in ADMIN_IDS:
        await admin_service.add_admin(admin_id)
        await user_service.upsert_user(admin_id, "admin")
    if ADMIN_IDS:
        logger.info(f"Seeded {len(ADMIN_IDS)} admin(s).")


async def on_startup():
    logger.info("Initializing database...")
    await init_db()
    
    logger.info("Running safe database migrations...")
    await run_migrations()
    
    await seed_regions()
    await seed_admins()

    from app.scheduler import start_scheduler
    await start_scheduler()

    logger.info("Database ready and Scheduler started.")


def register_routers():
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(barber_reg.router)
    dp.include_router(barber_menu.router)
    dp.include_router(client_reg.router)
    dp.include_router(client_menu.router)
    dp.include_router(client_search.router)
    dp.include_router(rating.router)
    dp.include_router(barber_premium_features.router)


def register_middlewares():
    dp.callback_query.middleware(RateLimitMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())


async def main():
    await on_startup()
    register_middlewares()
    register_routers()

    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
