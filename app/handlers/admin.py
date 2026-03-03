"""Admin panel handlers: barber management, stats, broadcast, user delete, support."""
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states.admin import AdminFSM
from app.services import (
    admin_service, barber_service, client_service,
    user_service, broadcast_service, stats_service,
)
from app.db.base import fetch_one, fetch_all
from app.keyboards.inline import (
    admin_menu_keyboard, admin_barber_actions_keyboard,
    broadcast_target_keyboard, ok_keyboard, back_button,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.flow_message import ensure_flow_message
from app.utils.pagination import paginate
from app.loader import bot
from app.middlewares.role_guard import AdminGuard

logger = logging.getLogger("barbershop")

router = Router(name="admin")
router.message.middleware(AdminGuard())
router.callback_query.middleware(AdminGuard())


# ═══════════════════════════════════════════
# Admin Menu
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.clear()
    await ensure_flow_message(callback, texts["admin_menu_title"], state,
                               keyboard=admin_menu_keyboard(texts))


@router.callback_query(F.data == "back:adm_menu")
async def back_admin_menu(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.clear()
    await ensure_flow_message(callback, texts["admin_menu_title"], state,
                               keyboard=admin_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Barber List & Management
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:barbers")
async def admin_barbers_list(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_barbers_page(callback, state, texts, 0)


@router.callback_query(F.data.startswith("page:admbarbers:"))
async def admin_barbers_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    await _show_barbers_page(callback, state, texts, page)


async def _show_barbers_page(event, state, texts, page):
    barbers = await barber_service.get_all_barbers()
    if not barbers:
        await ensure_flow_message(event, texts["admin_no_barbers"], state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("adm_menu", texts)]
                                   ]))
        return

    page_items, total_pages, has_prev, has_next = paginate(barbers, page)

    rows = []
    for b in page_items:
        status_icon = {"PENDING": "⏳", "APPROVED": "✅", "BLOCKED": "🚫"}.get(b["status"], "?")
        rows.append([InlineKeyboardButton(
            text=f"{status_icon} {b['name']} — {b['salon_name']}",
            callback_data=f"admb:view:{b['telegram_id']}",
        )])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:admbarbers:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:admbarbers:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([back_button("adm_menu", texts)])

    await ensure_flow_message(
        event, texts["admin_barbers_title"], state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ── Barber Detail ──

@router.callback_query(F.data.startswith("admb:view:"))
async def admin_barber_detail(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    barber = await barber_service.get_barber(barber_id)
    if not barber:
        await callback.answer(texts["admin_user_not_found"], show_alert=True)
        return

    region = await fetch_one("SELECT name_uz FROM regions WHERE id = ?", (barber["region_id"],))
    district = await fetch_one("SELECT name_uz FROM districts WHERE id = ?", (barber["district_id"],))

    card_text = texts["admin_barber_card"].format(
        name=barber["name"],
        phone=barber["phone"],
        region=region["name_uz"] if region else "?",
        district=district["name_uz"] if district else "?",
        salon_name=barber["salon_name"],
        status=barber["status"],
    )

    kb = admin_barber_actions_keyboard(barber, texts)

    if barber.get("photo_file_id"):
        await ensure_flow_message(callback, card_text, state, keyboard=kb, photo=barber["photo_file_id"])
    else:
        await ensure_flow_message(callback, card_text, state, keyboard=kb)


@router.callback_query(F.data == "back:adm_barbers")
async def back_to_barbers(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_barbers_page(callback, state, texts, 0)


# ═══════════════════════════════════════════
# Premium Barbers List
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:premiums")
async def admin_premiums_list(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_premium_barbers_page(callback, state, texts, 0)


@router.callback_query(F.data.startswith("page:admprems:"))
async def admin_premiums_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    await _show_premium_barbers_page(callback, state, texts, page)


async def _show_premium_barbers_page(event, state, texts, page):
    barbers = await fetch_all("SELECT * FROM barbers WHERE premium_status = 'ACTIVE' ORDER BY id DESC")
    if not barbers:
        await ensure_flow_message(event, "Faol premium sartaroshlar mavjud emas.", state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("adm_menu", texts)]
                                   ]))
        return

    page_items, total_pages, has_prev, has_next = paginate(barbers, page)

    rows = []
    for b in page_items:
        until = b.get('premium_until', '?')
        rows.append([InlineKeyboardButton(
            text=f"👑 {b['name']} ({until} gacha)",
            callback_data=f"admb:view:{b['telegram_id']}",
        )])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:admprems:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:admprems:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([back_button("adm_menu", texts)])

    await ensure_flow_message(
        event, "👑 <b>Premium Sartaroshlar</b>\n\nQuyida faol obunaga ega sartaroshlar ro'yxati keltirilgan:", state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ── Approve ──

@router.callback_query(F.data.startswith("admb:approve:"))
async def admin_approve_barber(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await barber_service.update_barber_status(barber_id, "APPROVED")
    await callback.answer(texts["admin_approve_ok"], show_alert=True)
    logger.info(f"Admin {callback.from_user.id} approved barber {barber_id}")

    # Notify barber
    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(chat_id=barber_id, text=b_texts["barber_approved_msg"])
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id}: {e}")

    # Refresh barber detail
    await admin_barber_detail(callback, state, texts)


# ── Premium Approve/Reject ──

@router.callback_query(F.data.startswith("adm_prem:approve:"))
async def admin_premium_approve(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    
    from app.services.barber_service import update_barber_premium_status
    from app.utils.time_utils import tashkent_now
    from datetime import timedelta
    
    until_date = (tashkent_now() + timedelta(days=30)).strftime('%Y-%m-%d')
    await update_barber_premium_status(barber_id, "ACTIVE", until_date)
    await callback.answer("Premium tasdiqlandi!", show_alert=True)
    logger.info(f"Admin {callback.from_user.id} approved premium for barber {barber_id}")

    try:
        await callback.message.delete()
    except:
        pass

    # Notify barber
    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(
            chat_id=barber_id, 
            text=b_texts.get("premium_approved", "🎉 Tabriklaymiz! Premium obunangiz faollashdi.\\nAmal qilish muddati: {until}").format(until=until_date)
        )
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id} about premium: {e}")


@router.callback_query(F.data.startswith("adm_prem:reject:"))
async def admin_premium_reject(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    
    from app.services.barber_service import update_barber_premium_status
    await update_barber_premium_status(barber_id, "INACTIVE", None)
    await callback.answer("Premium rad etildi!", show_alert=True)
    logger.info(f"Admin {callback.from_user.id} rejected premium for barber {barber_id}")

    try:
        await callback.message.delete()
    except:
        pass

    # Notify barber
    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(
            chat_id=barber_id, 
            text=b_texts.get("premium_rejected", "❌ Premium obuna so'rovingiz rad etildi.")
        )
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id} about premium rejection: {e}")


# ═══════════════════════════════════════════
# Admin Premium Config
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:prem_settings")
async def admin_premium_settings(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    price_row = await fetch_one("SELECT value FROM settings WHERE key='premium_price'")
    card_row = await fetch_one("SELECT value FROM settings WHERE key='payment_card'")
    profile_row = await fetch_one("SELECT value FROM settings WHERE key='support_profile'")

    text = texts["admin_premium_settings_title"].format(
        price=price_row["value"] if price_row else "0",
        card=card_row["value"] if card_row else "—",
        profile=profile_row["value"] if profile_row else "@admin",
    )
    from app.keyboards.inline import admin_premium_settings_keyboard
    await ensure_flow_message(callback, text, state, keyboard=admin_premium_settings_keyboard(texts))


@router.callback_query(F.data == "adm_prem_cfg:price")
async def admin_edit_price_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.edit_premium_price)
    await ensure_flow_message(callback, texts["admin_enter_price"], state)


@router.message(AdminFSM.edit_premium_price)
async def admin_edit_price_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    try:
        price = str(int(message.text.strip()))
    except (ValueError, TypeError):
        await message.answer(texts["error_generic"])
        return
    from app.db.base import execute_write
    await execute_write("UPDATE settings SET value = ? WHERE key = 'premium_price'", (price,))
    await state.clear()
    await message.answer(texts["admin_price_updated"].format(price=price))


@router.callback_query(F.data == "adm_prem_cfg:card")
async def admin_edit_card_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.edit_payment_card)
    await ensure_flow_message(callback, texts["admin_enter_card"], state)


@router.message(AdminFSM.edit_payment_card)
async def admin_edit_card_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    card = message.text.strip()
    from app.db.base import execute_write
    await execute_write("UPDATE settings SET value = ? WHERE key = 'payment_card'", (card,))
    await state.clear()
    await message.answer(texts["admin_card_updated"])


@router.callback_query(F.data == "adm_prem_cfg:profile")
async def admin_edit_profile_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.edit_support_profile)
    await ensure_flow_message(callback, texts["admin_enter_profile"], state)


@router.message(AdminFSM.edit_support_profile)
async def admin_edit_profile_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    profile = message.text.strip()
    from app.db.base import execute_write
    await execute_write("UPDATE settings SET value = ? WHERE key = 'support_profile'", (profile,))
    await state.clear()
    await message.answer(texts["admin_profile_updated"])


# ═══════════════════════════════════════════
# Premium Requests
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:prem_requests")
async def admin_premium_requests(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_premium_requests_page(callback, state, texts, 0)


@router.callback_query(F.data.startswith("page:premreqs:"))
async def admin_premium_requests_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    await _show_premium_requests_page(callback, state, texts, page)


async def _show_premium_requests_page(event, state, texts, page):
    barbers = await fetch_all("SELECT * FROM barbers WHERE premium_status = 'PENDING_APPROVAL' ORDER BY created_at DESC")
    if not barbers:
        await ensure_flow_message(event, texts["admin_no_premium_requests"], state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("adm_menu", texts)]
                                   ]))
        return

    page_items, total_pages, has_prev, has_next = paginate(barbers, page)
    rows = []
    for b in page_items:
        rows.append([InlineKeyboardButton(
            text=f"👑 {b['name']} — {b['phone']}",
            callback_data=f"admb:view:{b['telegram_id']}",
        )])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:premreqs:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:premreqs:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([back_button("adm_menu", texts)])

    await ensure_flow_message(
        event, f"📋 <b>Premium so'rovlar</b> ({len(barbers)} ta):", state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ── Block ──

@router.callback_query(F.data.startswith("admb:block:"))
async def admin_block_barber(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await barber_service.update_barber_status(barber_id, "BLOCKED")
    await callback.answer(texts["admin_block_ok"], show_alert=True)
    logger.info(f"Admin {callback.from_user.id} blocked barber {barber_id}")

    # Notify barber
    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(chat_id=barber_id, text=b_texts["barber_blocked_msg"])
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id}: {e}")

    await admin_barber_detail(callback, state, texts)


# ── Unblock ──

@router.callback_query(F.data.startswith("admb:unblock:"))
async def admin_unblock_barber(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await barber_service.update_barber_status(barber_id, "APPROVED")
    await callback.answer(texts["admin_unblock_ok"], show_alert=True)
    logger.info(f"Admin {callback.from_user.id} unblocked barber {barber_id}")

    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(chat_id=barber_id, text=b_texts["barber_approved_msg"])
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id}: {e}")

    await admin_barber_detail(callback, state, texts)


# ── Hard Delete Barber ──

@router.callback_query(F.data.startswith("admb:delete:"))
async def admin_delete_barber(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    logger.info(f"Admin {callback.from_user.id} hard-deleted barber {barber_id}")

    # Notify barber before deleting
    try:
        barber = await barber_service.get_barber(barber_id)
        lang = barber["lang"] if barber else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        b_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        await bot.send_message(chat_id=barber_id, text=b_texts["deleted_user_restart"])
    except Exception as e:
        logger.warning(f"Failed to notify barber {barber_id}: {e}")

    await user_service.delete_user(barber_id)
    await callback.answer(texts["admin_delete_ok"], show_alert=True)

    # Return to barber list
    await _show_barbers_page(callback, state, texts, 0)


# ═══════════════════════════════════════════
# Statistics
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    stats = await stats_service.get_stats()
    text = texts["admin_stats_text"].format(
        total=stats["total"],
        barbers=stats["barbers"],
        clients=stats["clients"],
    )
    await ensure_flow_message(callback, text, state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                   [back_button("adm_menu", texts)]
                               ]))


# ═══════════════════════════════════════════
# Add Admin
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:add_admin")
async def admin_add_admin_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.add_admin_id)
    await ensure_flow_message(callback, texts["admin_add_admin_prompt"], state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                   [back_button("adm_menu", texts)]
                               ]))


@router.message(AdminFSM.add_admin_id, F.text)
async def admin_add_admin_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(texts["admin_add_admin_prompt"])
        return

    new_admin_id = int(text)
    await admin_service.add_admin(new_admin_id)
    await user_service.upsert_user(new_admin_id, "admin")

    logger.info(f"Admin {message.from_user.id} added new admin {new_admin_id}")

    await state.clear()
    await message.answer(texts["admin_added_ok"])
    await ensure_flow_message(message, texts["admin_menu_title"], state,
                               keyboard=admin_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Broadcast
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.broadcast_target)
    await ensure_flow_message(callback, texts["admin_broadcast_choose"], state,
                               keyboard=broadcast_target_keyboard(texts))


@router.callback_query(AdminFSM.broadcast_target, F.data.startswith("adm:bc_target:"))
async def admin_broadcast_target(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    target = callback.data.split(":")[2]  # all / barbers / clients
    await state.update_data(bc_target=target)
    await state.set_state(AdminFSM.broadcast_content)
    await ensure_flow_message(callback, texts["admin_broadcast_send"], state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                   [back_button("adm_menu", texts)]
                               ]))


@router.message(AdminFSM.broadcast_content)
async def admin_broadcast_send(message: Message, state: FSMContext, texts: dict, **kwargs):
    data = await state.get_data()
    target = data.get("bc_target", "all")

    # Collect user IDs
    user_ids = []
    if target == "all":
        barber_rows = await fetch_all("SELECT telegram_id FROM barbers WHERE status = 'APPROVED'")
        client_rows = await fetch_all("SELECT telegram_id FROM clients")
        user_ids = [r["telegram_id"] for r in barber_rows] + [r["telegram_id"] for r in client_rows]
    elif target == "barbers":
        rows = await fetch_all("SELECT telegram_id FROM barbers WHERE status = 'APPROVED'")
        user_ids = [r["telegram_id"] for r in rows]
    elif target == "clients":
        rows = await fetch_all("SELECT telegram_id FROM clients")
        user_ids = [r["telegram_id"] for r in rows]

    # Get text & photo
    bc_text = message.text or message.caption or ""
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id

    # Send broadcast
    sent, failed = await broadcast_service.broadcast_message(
        bot=bot, user_ids=user_ids, text=bc_text, photo_file_id=photo_file_id,
    )

    logger.info(f"Broadcast by admin {message.from_user.id}: target={target}, sent={sent}, failed={failed}")

    await state.clear()
    result_text = texts["admin_broadcast_done"].format(sent=sent, failed=failed)
    await message.answer(result_text)
    await ensure_flow_message(message, texts["admin_menu_title"], state,
                               keyboard=admin_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Delete User
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:delete_user")
async def admin_delete_user_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(AdminFSM.delete_user_id)
    await ensure_flow_message(callback, texts["admin_delete_user_prompt"], state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                   [back_button("adm_menu", texts)]
                               ]))


@router.message(AdminFSM.delete_user_id, F.text)
async def admin_delete_user_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(texts["admin_delete_user_prompt"])
        return

    target_id = int(text)
    user = await user_service.get_user(target_id)
    if not user:
        await message.answer(texts["admin_user_not_found"])
        return

    logger.info(f"Admin {message.from_user.id} hard-deleted user {target_id}")

    # Notify user
    try:
        from app.i18n.uz import TEXTS_UZ
        await bot.send_message(chat_id=target_id, text=TEXTS_UZ["deleted_user_restart"])
    except Exception:
        pass

    await user_service.delete_user(target_id)

    await state.clear()
    await message.answer(texts["admin_user_deleted"])
    await ensure_flow_message(message, texts["admin_menu_title"], state,
                               keyboard=admin_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Support Username
# ═══════════════════════════════════════════

@router.callback_query(F.data == "adm:support")
async def admin_support_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    current = await admin_service.get_support_username()
    await state.set_state(AdminFSM.support_username)
    await ensure_flow_message(
        callback,
        f"{texts['admin_support_prompt']}\n\n📌 Hozirgi: {current}",
        state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=[
            [back_button("adm_menu", texts)]
        ]),
    )


@router.message(AdminFSM.support_username, F.text)
async def admin_support_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username

    await admin_service.set_support_username(username)
    logger.info(f"Admin {message.from_user.id} updated support username to {username}")

    await state.clear()
    await message.answer(texts["admin_support_updated"])
    await ensure_flow_message(message, texts["admin_menu_title"], state,
                                keyboard=admin_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Message Barber
# ═══════════════════════════════════════════

@router.callback_query(F.data.startswith("admb:msg:"))
async def admin_message_barber_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await state.update_data(target_barber_id=barber_id)
    await state.set_state(AdminFSM.message_barber_content)
    await ensure_flow_message(
        callback, texts["admin_msg_barber_prompt"], state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=[
            [back_button(f"admb:view:{barber_id}", texts)]
        ])
    )


@router.message(AdminFSM.message_barber_content)
async def admin_message_barber_send(message: Message, state: FSMContext, texts: dict, **kwargs):
    data = await state.get_data()
    barber_id = data.get("target_barber_id")
    if not barber_id:
        await state.clear()
        return

    # Text & optional photo
    msg_text = message.text or message.caption or ""
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id

    try:
        from app.loader import bot
        if photo_file_id:
            await bot.send_photo(chat_id=barber_id, photo=photo_file_id, caption=msg_text, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=barber_id, text=msg_text, parse_mode="HTML")
        
        await message.answer(texts["admin_msg_sent_ok"])
    except Exception as e:
        logger.warning(f"Failed to send direct message to barber {barber_id}: {e}")
        await message.answer(texts["error_generic"])

    # Returns to barber detail view
    callback_mock = CallbackQuery(
        id="0",
        from_user=message.from_user,
        chat_instance="0",
        message=message,
        data=f"admb:view:{barber_id}"
    )
    await state.clear()
    await admin_barber_detail(callback_mock, state, texts)
