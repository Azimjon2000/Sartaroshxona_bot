import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import BROADCAST_BATCH_SIZE, BROADCAST_PAUSE_SECONDS

logger = logging.getLogger("barbershop")


from typing import List, Optional, Tuple

async def broadcast_message(
    bot: Bot,
    user_ids: List[int],
    text: str,
    photo_file_id: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Send broadcast to list of user IDs.
    Throttle: BROADCAST_BATCH_SIZE per second, then pause.
    Returns (sent_count, fail_count).
    """
    sent = 0
    failed = 0

    for i, uid in enumerate(user_ids):
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=uid, photo=photo_file_id, caption=text, parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            sent += 1
        except TelegramAPIError as e:
            logger.warning(f"Broadcast fail to {uid}: {e}")
            failed += 1

        # Throttle: pause after each batch
        if (i + 1) % BROADCAST_BATCH_SIZE == 0:
            await asyncio.sleep(BROADCAST_PAUSE_SECONDS)

    return sent, failed
