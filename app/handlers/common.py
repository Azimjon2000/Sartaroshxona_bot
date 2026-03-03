"""Common handlers: /start, role selection, OK delete, main menu reply."""
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from app.utils.time_utils import today_uz_str
from aiogram.fsm.context import FSMContext

from app.services import user_service, admin_service, barber_service, client_service
from app.keyboards.inline import role_keyboard, client_menu_keyboard, barber_menu_keyboard, admin_menu_keyboard
from app.keyboards.reply import main_menu_reply_keyboard, remove_keyboard
from app.utils.flow_message import ensure_flow_message
from app.states.barber_reg import BarberRegFSM
from app.states.client_reg import ClientRegFSM

logger = logging.getLogger("barbershop")

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject, texts: dict, **kwargs):
    """Handle /start command — route based on existing role."""
    await state.clear()
    user_id = message.from_user.id
    ref_param = command.args

    is_referral_handled = False
    ref_barber_id = None
    if ref_param and str(ref_param).startswith("ref_"):
        # Check for ANY Usage Today (Strict Limit)
        from app.services import booking_service
        from app.utils.time_utils import today_tashkent
        usage = await booking_service.get_client_today_usage(user_id, today_tashkent())
        if usage:
            await message.answer(texts.get("done_booking_block_msg", "Siz bugun xizmatdan foydalanib bo'lgansiz, ertaga qayta kiring."))
            return

        try:
            barber_db_id = int(str(ref_param).replace("ref_", ""))
            barber_by_id = await barber_service.get_barber_by_db_id(barber_db_id)
            if barber_by_id:
                ref_barber_id = barber_db_id
                await state.update_data(ref_barber_id=ref_barber_id)
                client = await client_service.get_client(user_id)
                if client:
                    await client_service.update_client_lock(user_id, barber_db_id, today_uz_str())
                    is_referral_handled = True
        except ValueError:
            pass
            
    if not is_referral_handled:
        client = await client_service.get_client(user_id)
        if client:
            await client_service.update_client_lock(user_id, None, None)

    # Check admin first
    if await admin_service.is_admin(user_id):
        await user_service.upsert_user(user_id, "admin")
        await message.answer(
            texts["admin_menu_title"],
            reply_markup=admin_menu_keyboard(texts),
            parse_mode="HTML",
        )
        return

    # Check existing user
    user = await user_service.get_user(user_id)
    if user:
        role = user["role"]

        if role == "barber":
            barber = await barber_service.get_barber(user_id)
            if barber:
                if barber.get("is_blocked_temp") == 1:
                    await barber_service.update_barber_field(user_id, "is_blocked_temp", 0)
                    from app.i18n.uz import TEXTS_UZ
                    from app.i18n.ru import TEXTS_RU
                    lang = barber.get("lang", "uz")
                    b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
                    try:
                        await message.bot.send_message(
                            chat_id=user_id, 
                            text=b_texts.get("premium_expired", "Sizning premium obunangiz muddati tugadi. Bepul rejimga qaytdingiz.")
                        )
                    except:
                        pass
                
                if barber["status"] == "PENDING":
                    await message.answer(texts["wait_approval"])
                    return
                elif barber["status"] == "BLOCKED":
                    await message.answer(texts["barber_blocked_msg"])
                    return
                elif barber["status"] == "APPROVED":
                    await message.answer(
                        texts["barber_menu_title"],
                        reply_markup=barber_menu_keyboard(texts),
                        parse_mode="HTML",
                    )
                    await message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))
                    return

        elif role == "client":
            client = await client_service.get_client(user_id)
            if client:
                data = await state.get_data()
                ref_id = data.get("ref_barber_id")
                if ref_id:
                    from app.handlers.client_search import show_barber_card
                    # Get barber details to get their telegram_id
                    barber = await barber_service.get_barber_by_db_id(ref_id)
                    if barber:
                        await show_barber_card(message, state, texts, barber["telegram_id"])
                        return

                await message.answer(
                    texts["client_menu_title"],
                    reply_markup=client_menu_keyboard(texts),
                    parse_mode="HTML",
                )
                await message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))
                return

    # No role or deleted user → show role picker
    await message.answer(
        texts["choose_role"],
        reply_markup=role_keyboard(texts),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "role:barber")
async def on_role_barber(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    """Start barber registration flow."""
    await callback.answer()
    user_id = callback.from_user.id

    # Check if already registered
    barber = await barber_service.get_barber(user_id)
    if barber:
        if barber["status"] == "PENDING":
            await callback.message.edit_text(texts["wait_approval"])
            return
        elif barber["status"] == "APPROVED":
            await callback.message.edit_text(
                texts["barber_menu_title"],
                reply_markup=barber_menu_keyboard(texts),
                parse_mode="HTML",
            )
            await callback.message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))
            return

    await state.set_state(BarberRegFSM.name)
    await ensure_flow_message(callback, texts["enter_name"], state)


@router.callback_query(F.data == "role:client")
async def on_role_client(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    """Start client registration flow."""
    await callback.answer()
    user_id = callback.from_user.id

    # Check if already registered
    client = await client_service.get_client(user_id)
    if client:
        await callback.message.edit_text(
            texts["client_menu_title"],
            reply_markup=client_menu_keyboard(texts),
            parse_mode="HTML",
        )
        return

    await state.set_state(ClientRegFSM.name)
    await ensure_flow_message(callback, texts["enter_name"], state)


@router.callback_query(F.data == "ok:delete")
async def on_ok_delete(callback: CallbackQuery, **kwargs):
    """Delete the OK popup message."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.message(F.text.in_(["🏠 Asosiy menyu", "🏠 Главное меню"]))
async def on_main_menu(message: Message, state: FSMContext, texts: dict, **kwargs):
    """Handle reply keyboard 'Asosiy menyu' button."""
    await state.clear()
    user_id = message.from_user.id

    # Check admin
    if await admin_service.is_admin(user_id):
        await message.answer(
            texts["admin_menu_title"],
            reply_markup=admin_menu_keyboard(texts),
            parse_mode="HTML",
        )
        return

    user = await user_service.get_user(user_id)
    if not user:
        await message.answer(texts["choose_role"], reply_markup=role_keyboard(texts))
        return

    if user["role"] == "barber":
        barber = await barber_service.get_barber(user_id)
        if barber and barber["status"] == "APPROVED":
            await message.answer(
                texts["barber_menu_title"],
                reply_markup=barber_menu_keyboard(texts),
                parse_mode="HTML",
            )
            await message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))
            return

    if user["role"] == "client":
        client = await client_service.get_client(user_id)
        if client:
            await message.answer(
                texts["client_menu_title"],
                reply_markup=client_menu_keyboard(texts),
                parse_mode="HTML",
            )
            return

    await message.answer(texts["choose_role"], reply_markup=role_keyboard(texts))
