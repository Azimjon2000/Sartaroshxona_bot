import time
from collections import defaultdict
from typing import Any, Callable, Awaitable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

from app.config import RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_HITS


# Prefixes that trigger rate limiting
CRITICAL_PREFIXES = ("csearch:", "cbook:", "bsched:")


class RateLimitMiddleware(BaseMiddleware):
    """
    Rate-limit middleware for callback queries.
    Allows max RATE_LIMIT_MAX_HITS within RATE_LIMIT_WINDOW seconds
    for critical action prefixes.
    """

    def __init__(self):
        super().__init__()
        self.hits: Dict[int, List[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery) or not event.data:
            return await handler(event, data)

        # Only rate-limit critical actions
        is_critical = any(event.data.startswith(p) for p in CRITICAL_PREFIXES)
        if not is_critical:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        # Clean old timestamps
        self.hits[user_id] = [
            t for t in self.hits[user_id] if now - t < RATE_LIMIT_WINDOW
        ]

        if len(self.hits[user_id]) >= RATE_LIMIT_MAX_HITS:
            # Get lang for i18n
            lang = data.get("lang", "uz")
            from app.i18n.uz import TEXTS_UZ
            from app.i18n.ru import TEXTS_RU
            texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
            await event.answer(texts["rate_limit"], show_alert=True)
            return

        self.hits[user_id].append(now)
        return await handler(event, data)
