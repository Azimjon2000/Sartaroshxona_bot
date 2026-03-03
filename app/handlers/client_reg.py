"""Client registration handlers — name + phone (contact)."""
import logging
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states.client_reg import ClientRegFSM
from app.services import user_service, client_service
from app.keyboards.inline import client_menu_keyboard
from app.keyboards.reply import phone_request_keyboard, main_menu_reply_keyboard, remove_keyboard
from app.utils.flow_message import ensure_flow_message

logger = logging.getLogger("barbershop")

router = Router(name="client_reg")

PHONE_RE = re.compile(r"^\+998\d{9}$")


# ── Step 1: Name ──

@router.message(ClientRegFSM.name, F.text)
async def on_client_name(message: Message, state: FSMContext, texts: dict, **kwargs):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await ensure_flow_message(message, texts["enter_name"], state)
        return
    await state.update_data(name=name)
    await state.set_state(ClientRegFSM.phone)
    await message.answer(texts["share_phone"], reply_markup=phone_request_keyboard(texts))


# ── Step 2: Phone ──

@router.message(ClientRegFSM.phone, F.contact)
async def on_client_phone_contact(message: Message, state: FSMContext, texts: dict, **kwargs):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await _finish_client_reg(message, state, texts, phone)


@router.message(ClientRegFSM.phone, F.text.in_(["🏠 Asosiy menyu", "🏠 Главное меню"]))
async def on_client_reg_interrupt(message: Message, state: FSMContext, texts: dict, **kwargs):
    from app.keyboards.inline import role_keyboard
    await state.clear()
    await message.answer(texts["choose_role"], reply_markup=role_keyboard(texts))


@router.message(ClientRegFSM.phone, F.text)
async def on_client_phone_text(message: Message, state: FSMContext, texts: dict, **kwargs):
    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer(texts["invalid_phone"])
        return
    await _finish_client_reg(message, state, texts, phone)


async def _finish_client_reg(message: Message, state: FSMContext, texts: dict, phone: str):
    """Complete client registration."""
    data = await state.get_data()
    user_id = message.from_user.id

    await user_service.upsert_user(user_id, "client")
    await client_service.create_client(
        telegram_id=user_id,
        name=data["name"],
        phone=phone,
        lang="uz",
    )

    logger.info(f"Client registered: user={user_id}, name={data['name']}")

    # Check for referral redirection
    ref_id = data.get("ref_barber_id")
    if ref_id:
        from app.handlers.client_search import show_barber_card
        from app.services import barber_service, booking_service
        from app.utils.time_utils import today_tashkent
        
        # Double check for ANY Usage Today even if they just registered (safety)
        usage = await booking_service.get_client_today_usage(user_id, today_tashkent())
        if usage:
            await state.clear()
            await message.answer(texts.get("done_booking_block_msg", "Siz bugun xizmatdan foydalanib bo'lgansiz, ertaga qayta kiring."))
            await message.answer(texts["main_menu"], reply_markup=main_menu_reply_keyboard(texts))
            return

        # Get barber details to get their telegram_id
        barber = await barber_service.get_barber_by_db_id(ref_id)
        if barber:
            await state.clear()
            await show_barber_card(message, state, texts, barber["telegram_id"])
            await message.answer(texts["main_menu"], reply_markup=main_menu_reply_keyboard(texts))
            # ... continue with admin notification
    else:
        await state.clear()
        # Show client menu
        await message.answer(
            texts["client_menu_title"],
            reply_markup=client_menu_keyboard(texts),
            parse_mode="HTML",
        )
        # Send main menu reply keyboard
        await message.answer(texts["main_menu"], reply_markup=main_menu_reply_keyboard(texts))

    # Notify Admins
    try:
        from app.config import ADMIN_IDS
        from app.loader import bot
        from app.utils.time_utils import now_tashkent
        total_users = await user_service.get_total_users()
        dt = now_tashkent().strftime("%Y-%m-%d %H:%M:%S")
        
        admin_msg = (
            f"🆕 <b>Yangi Foydalanuvchi (Client)</b>\n\n"
            f"🔢 №: {total_users}\n"
            f"👤 Ism: {data['name']}\n"
            f"📱 Tel: {phone}\n"
            f"🆔 ID: {user_id}\n"
            f"🕒 Vaqt: {dt}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_msg, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to notify admins about new client: {e}")
