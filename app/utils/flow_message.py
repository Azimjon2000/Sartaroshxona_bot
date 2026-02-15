from typing import Union, Optional
import logging
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger("barbershop")


async def ensure_flow_message(
    event: Union[Message, CallbackQuery],
    text: str,
    state: FSMContext,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    photo: Optional[str] = None,
    bot: Optional[Bot] = None,
):
    """
    Edit existing flow message or send a new one.
    Stores the flow message ID in FSM state data.

    - If `photo` is provided, sends as photo with caption.
    - Otherwise, sends/edits as text message.
    """
    data = await state.get_data()
    flow_msg_id = data.get("flow_msg_id")
    chat_id = event.from_user.id

    if bot is None:
        if isinstance(event, CallbackQuery):
            bot = event.message.bot
        else:
            bot = event.bot

    # If callback query, answer it to remove loading spinner
    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass

    # Try to edit existing message
    if flow_msg_id and not photo:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=flow_msg_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return flow_msg_id
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return flow_msg_id
            # Message not found or can't edit — send new
            logger.debug(f"Cannot edit flow message {flow_msg_id}: {e}")

    # Delete old flow message if exists
    if flow_msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=flow_msg_id)
        except Exception:
            pass

    # Send new message
    if photo:
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    # Store message id
    await state.update_data(flow_msg_id=msg.message_id)
    return msg.message_id


async def send_ok_popup(
    event: Union[Message, CallbackQuery],
    text: str,
    bot: Optional[Bot] = None,
):
    """
    Send a separate 'OK' message that deletes itself when OK is pressed.
    Returns the message id.
    """
    from app.keyboards.inline import ok_keyboard

    chat_id = event.from_user.id
    if bot is None:
        if isinstance(event, CallbackQuery):
            bot = event.message.bot
        else:
            bot = event.bot

    msg = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=ok_keyboard(),
        parse_mode="HTML",
    )
    return msg.message_id
