from typing import Any, Callable, Awaitable, Union, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.db.base import fetch_one
from app.i18n.uz import TEXTS_UZ
from app.i18n.ru import TEXTS_RU

TEXTS = {"uz": TEXTS_UZ, "ru": TEXTS_RU}


class I18nMiddleware(BaseMiddleware):
    """
    Injects `lang` and `texts` into handler data based on user's language preference.
    Checks clients table first, then barbers, defaults to 'uz'.
    """

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        # Try client lang
        row = await fetch_one(
            "SELECT lang FROM clients WHERE telegram_id = ?", (user_id,)
        )
        if not row:
            # Try barber lang
            row = await fetch_one(
                "SELECT lang FROM barbers WHERE telegram_id = ?", (user_id,)
            )

        lang = row["lang"] if row else "uz"
        data["lang"] = lang
        data["texts"] = TEXTS.get(lang, TEXTS_UZ)

        return await handler(event, data)
