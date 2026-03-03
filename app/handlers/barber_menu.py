"""Barber menu handlers: schedule, bookings, prices, settings, media, rating, stats."""
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states.barber_menu import BarberMenuFSM
from app.services import barber_service, booking_service, admin_service
from app.keyboards.inline import (
    barber_menu_keyboard, barber_settings_keyboard, schedule_keyboard,
    media_gallery_keyboard, lang_keyboard, ok_keyboard,
    barber_booking_actions_keyboard, barber_confirm_cancel_keyboard,
    back_button,
)
from app.keyboards.reply import (
    main_menu_reply_keyboard, phone_request_keyboard,
    location_request_keyboard, remove_keyboard,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.flow_message import ensure_flow_message, send_ok_popup
from app.utils.time_utils import today_tashkent, slot_to_hour
from app.utils.pagination import paginate
from app.loader import bot

logger = logging.getLogger("barbershop")

router = Router(name="barber_menu")


# ═══════════════════════════════════════════
# Main Menu
# ═══════════════════════════════════════════

@router.callback_query(F.data == "back:bmenu")
async def back_to_barber_menu(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.menu)
    await ensure_flow_message(callback, texts["barber_menu_title"], state,
                               keyboard=barber_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Schedule (16 hour toggle grid)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:schedule")
async def barber_schedule(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = callback.from_user.id
    await _show_schedule(callback, state, texts, barber_id)


@router.callback_query(F.data.startswith("bsched:"))
async def barber_toggle_slot(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = callback.from_user.id
    hour_slot = int(callback.data.split(":")[1])
    await barber_service.toggle_work_hour(barber_id, hour_slot)
    await _show_schedule(callback, state, texts, barber_id)


async def _show_schedule(event, state, texts, barber_id):
    """Build schedule grid with booking indicators."""
    work_hours = await barber_service.get_work_hours(barber_id)
    today = today_tashkent()
    confirmed_slots = await booking_service.get_confirmed_slots(barber_id, today)

    slots = []
    for wh in work_hours:
        slot = dict(wh)
        slot["booked"] = wh["hour_slot"] in confirmed_slots
        slots.append(slot)

    # Fill missing slots
    existing_slots = {s["hour_slot"] for s in slots}
    for i in range(16):
        if i not in existing_slots:
            slots.append({"hour_slot": i, "is_enabled": 0, "booked": False})
    slots.sort(key=lambda x: x["hour_slot"])

    await ensure_flow_message(event, texts["schedule_title"], state,
                               keyboard=schedule_keyboard(slots, texts))


# ── View booking detail from schedule ──

@router.callback_query(F.data.startswith("bbron:") & F.data.func(lambda d: len(d.split(":")) == 2 and d.split(":")[1].isdigit()))
async def barber_view_booking_from_schedule(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    """View booking detail when barber taps a 💺 booked slot."""
    barber_id = callback.from_user.id
    hour_slot = int(callback.data.split(":")[1])
    today = today_tashkent()

    bookings = await booking_service.get_barber_bookings_for_date(barber_id, today)
    booking = next((b for b in bookings if b["hour_slot"] == hour_slot), None)

    if not booking:
        await send_ok_popup(callback, texts["no_booking_for_slot"])
        return

    hour = slot_to_hour(hour_slot)
    text = texts["barber_booking_detail"].format(
        client_name=booking["client_name"],
        client_phone=booking["client_phone"],
        hour=f"{hour:02d}:00",
        date=today,
    )

    from app.keyboards.inline import barber_booking_actions_keyboard
    kb = barber_booking_actions_keyboard(booking["id"], texts)
    await ensure_flow_message(callback, text, state, keyboard=kb)


@router.callback_query(F.data.startswith("bbron:cancel_ask:"))
async def barber_cancel_booking_ask(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    from app.keyboards.inline import barber_confirm_cancel_keyboard
    await ensure_flow_message(
        callback, texts["confirm_cancel_barber"], state,
        keyboard=barber_confirm_cancel_keyboard(booking_id, texts)
    )


@router.callback_query(F.data.startswith("bbron:cancel_confirm:"))
async def barber_cancel_booking_confirm(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    booking = await booking_service.get_booking(booking_id)
    if not booking:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    # Cancel booking
    await booking_service.cancel_booking(booking_id)
    
    # Notify client
    try:
        from app.services.client_service import get_client
        client = await get_client(booking["client_id"])
        lang = client["lang"] if client else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        c_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        
        barber = await barber_service.get_barber(booking["barber_id"])
        msg = c_texts["booking_cancelled_client_notify"].format(
            barber_name=barber["name"],
            barber_phone=barber["phone"],
            hour=slot_to_hour(booking["hour_slot"]),
            date=booking["date"]
        )
        await bot.send_message(chat_id=booking["client_id"], text=msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to notify client about cancel: {e}")

    await callback.answer(texts["cancel_confirmed_barber"], show_alert=True)
    await barber_schedule(callback, state, texts)


@router.callback_query(F.data.startswith("bbron:remind:"))
async def barber_remind_client(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    booking = await booking_service.get_booking(booking_id)
    if not booking:
        return

    try:
        from app.services.client_service import get_client
        client = await get_client(booking["client_id"])
        lang = client["lang"] if client else "uz"
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        c_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
        
        barber = await barber_service.get_barber(booking["barber_id"])
        msg = c_texts["reminder_client_msg"].format(
            hour=slot_to_hour(booking["hour_slot"]),
            barber_name=barber["name"]
        )
        await bot.send_message(chat_id=booking["client_id"], text=msg, parse_mode="HTML")
        await callback.answer(texts["remind_sent_popup"])
    except Exception as e:
        logger.warning(f"Failed to remind client: {e}")
        await callback.answer(texts["error_generic"])


# ═══════════════════════════════════════════
# Bookings List (today)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:bookings")
async def barber_bookings_list(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = callback.from_user.id
    today = today_tashkent()
    bookings = await booking_service.get_barber_bookings_for_date(barber_id, today)

    if not bookings:
        await send_ok_popup(callback, texts["no_bookings_today"])
        return

    # Show 16 hour buttons with booking indicators
    work_hours = await barber_service.get_work_hours(barber_id)
    confirmed_slots = await booking_service.get_confirmed_slots(barber_id, today)

    rows = []
    row = []
    for wh in work_hours:
        if not wh["is_enabled"]:
            continue
        hour = slot_to_hour(wh["hour_slot"])
        bk = next((b for b in bookings if b["hour_slot"] == wh["hour_slot"]), None)
        if bk:
            # Shorten label for 3-col: "14:00 Name" maybe too long.
            # Just "14:00*" or "14:00 ✅"?
            # User request: "3qator qilib chiqarilsin".
            # If I put full name, it will be very wide. Inline buttons wrap text? No.
            # Maybe just "14:00 👤"? Or "14:00 Alisher"?
            # Let's try to fit name. If not fit, Telegram truncates.
            # To be safe and compact: "14:00 👤" if booked. 
            # But barber needs to see WHO.
            # If I click, I see details.
            # Let's try to show name but keep it short?
            # Or just "14:00 (A...)"?
            # Let's standard "14:00 Name". If it's 3 col, it might be tight.
            # But 3 columns suggests they want compactness.
            label = f"💺 {hour:02d}:00 {bk['client_name']}"
            cb = f"bbron:{wh['hour_slot']}"
        else:
            label = f"◻️ {hour:02d}:00"
            cb = "noop"
        
        row.append(InlineKeyboardButton(text=label, callback_data=cb))
        if len(row) == 3:
            rows.append(row)
            row = []
            
    if row:
        rows.append(row)

    from app.keyboards.inline import back_button
    rows.append([back_button("bmenu", texts)])

    await ensure_flow_message(callback, texts["bookings_today_title"].format(date=today), state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=rows))


# ── Mark booking DONE ──

@router.callback_query(F.data.startswith("bbron:done:"))
async def barber_mark_done(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    booking = await booking_service.get_booking(booking_id)

    if not booking or booking["status"] != "CONFIRMED":
        await callback.answer(texts["booking_already_done"], show_alert=True)
        return

    await booking_service.mark_booking_done(booking_id)
    logger.info(f"Barber {callback.from_user.id} marked booking {booking_id} as DONE")

    await callback.answer(texts["booking_done_popup"], show_alert=True)

    # Notify client — ask to rate
    try:
        from app.keyboards.inline import rating_stars_keyboard
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        from app.services.client_service import get_client
        client = await get_client(booking["client_id"])
        lang = client["lang"] if client else "uz"
        c_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ

        barber = await barber_service.get_barber(booking["barber_id"])
        barber_name = barber["name"] if barber else "?"

        await bot.send_message(
            chat_id=booking["client_id"],
            text=c_texts["rate_barber_prompt"].format(barber_name=barber_name),
            reply_markup=rating_stars_keyboard(booking_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed to send rating request to client {booking['client_id']}: {e}")

    # Return to schedule
    await _show_schedule(callback, state, texts, callback.from_user.id)


# ═══════════════════════════════════════════
# Prices
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:prices")
async def barber_prices(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = callback.from_user.id
    prices = await barber_service.get_prices(barber_id)

    if not prices:
        await send_ok_popup(callback, texts["prices_not_set"])
        return

    text = texts["prices_view"].format(
        hair=prices["hair_price"] or "—",
        beard=prices["beard_price"] or "—",
        groom=prices["groom_price"] or "—",
        note=prices["extra_note"] or "—",
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_edit_prices"], callback_data="bprice:edit")],
        [InlineKeyboardButton(text=texts["back"], callback_data="back:bmenu")],
    ])
    await ensure_flow_message(callback, text, state, keyboard=kb)


@router.callback_query(F.data == "bprice:edit")
async def barber_edit_prices(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.price_hair)
    await ensure_flow_message(callback, texts["enter_hair_price"], state)


@router.message(BarberMenuFSM.price_hair, F.text)
async def on_hair_price(message: Message, state: FSMContext, texts: dict, **kwargs):
    price = message.text.strip()
    if not price.isdigit():
        await message.answer(texts["price_invalid"])
        return
    await barber_service.update_price(message.from_user.id, "hair_price", int(price))
    await state.set_state(BarberMenuFSM.price_beard)
    text = f"{texts['hair_price_set']}\n\n{texts['enter_beard_price']}"
    await ensure_flow_message(message, text, state)


@router.message(BarberMenuFSM.price_beard, F.text)
async def on_beard_price(message: Message, state: FSMContext, texts: dict, **kwargs):
    price = message.text.strip()
    if not price.isdigit():
        await message.answer(texts["price_invalid"])
        return
    await barber_service.update_price(message.from_user.id, "beard_price", int(price))
    await state.set_state(BarberMenuFSM.price_groom)
    text = f"{texts['beard_price_set']}\n\n{texts['enter_groom_price']}"
    await ensure_flow_message(message, text, state)


@router.message(BarberMenuFSM.price_groom, F.text)
async def on_groom_price(message: Message, state: FSMContext, texts: dict, **kwargs):
    price = message.text.strip()
    if not price.isdigit():
        await message.answer(texts["price_invalid"])
        return
    await barber_service.update_price(message.from_user.id, "groom_price", int(price))
    await state.set_state(BarberMenuFSM.price_note)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["rate_skip_btn"], callback_data="bprice:skip_note")],
    ])
    text = f"{texts['groom_price_set']}\n\n{texts['enter_extra_note']}"
    await ensure_flow_message(message, text, state, keyboard=kb)


@router.message(BarberMenuFSM.price_note, F.text)
async def on_price_note(message: Message, state: FSMContext, texts: dict, **kwargs):
    note = message.text.strip()[:300]
    await barber_service.update_price(message.from_user.id, "extra_note", note)
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(message, texts["prices_saved"])
    await ensure_flow_message(message, texts["barber_menu_title"], state,
                               keyboard=barber_menu_keyboard(texts))


@router.callback_query(F.data == "bprice:skip_note")
async def on_skip_note(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(callback, texts["prices_saved"])
    await ensure_flow_message(callback, texts["barber_menu_title"], state,
                               keyboard=barber_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:settings")
async def barber_settings(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await ensure_flow_message(callback, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


# ── Premium Obuna ──

@router.callback_query(F.data == "bmenu:premium")
async def barber_premium_status(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber = await barber_service.get_barber(callback.from_user.id)
    if not barber:
        return
        
    status = barber.get("premium_status", "INACTIVE")
    until = barber.get("premium_until")
    
    if status == 'ACTIVE' and until:
        until_text = f"Amal qilish muddati: <b>{until}</b>"
        status_text = texts.get("premium_status_active", "Faol")
    elif status == 'PENDING_APPROVAL':
        until_text = ""
        status_text = texts.get("premium_status_pending", "Admindan tasdiq kutilmoqda")
    else:
        until_text = ""
        status_text = texts.get("premium_status_inactive", "Faol emas")

    text = texts["premium_status_msg"].format(status=status_text, until_text=until_text)
    from app.keyboards.inline import premium_buy_keyboard
    
    if status == 'ACTIVE':
        # Show premium menu for active subscribers
        from app.keyboards.inline import premium_menu_keyboard
        rows = [
            [InlineKeyboardButton(text=texts["btn_premium_reminder"], callback_data="bprem:reminder")],
            [InlineKeyboardButton(text=texts["btn_premium_analytics"], callback_data="bprem:analytics")],
            [back_button("bmenu", texts)],
        ]
        from aiogram.types import InlineKeyboardMarkup
        await ensure_flow_message(callback, text, state, keyboard=InlineKeyboardMarkup(inline_keyboard=rows))
    else:
        await ensure_flow_message(callback, text, state, keyboard=premium_buy_keyboard(status, texts))


@router.callback_query(F.data == "back:bmenu_premium")
async def back_to_premium(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await barber_premium_status(callback, state, texts)


@router.callback_query(F.data == "bprem:buy")
async def barber_premium_buy(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    from app.db.base import fetch_one
    price_row = await fetch_one("SELECT value FROM settings WHERE key='premium_price'")
    card_row = await fetch_one("SELECT value FROM settings WHERE key='payment_card'")
    profile_row = await fetch_one("SELECT value FROM settings WHERE key='support_profile'")
    
    price = price_row["value"] if price_row else "0"
    card = card_row["value"] if card_row else "—"
    support_profile = profile_row["value"] if profile_row else "@admin"
    
    text = texts["premium_buy_msg"].format(price=price, card=card, support_profile=support_profile)
    from app.keyboards.inline import premium_confirm_keyboard
    await ensure_flow_message(callback, text, state, keyboard=premium_confirm_keyboard(texts))


@router.callback_query(F.data == "bprem:confirm")
async def barber_premium_confirm(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    user_id = callback.from_user.id
    barber = await barber_service.get_barber(user_id)
    if not barber:
        return

    # Update status to PENDING
    from app.services.barber_service import update_barber_premium_status
    await update_barber_premium_status(user_id, "PENDING_APPROVAL", None) 
    
    # Notify Admin
    from app.config import ADMIN_IDS
    from app.keyboards.inline import admin_premium_approve_keyboard
    from app.loader import bot
    
    # Default translation fallback if missing
    admin_text = texts.get("admin_premium_request", "👑 <b>PREMIUM SO'ROVI</b>\\n\\nSartarosh: {name}\\nTelefon: {phone}\\nSalon: {salon}\\nID: {id}\\n\\nTasdiqlaysizmi?").format(
        name=barber["name"],
        phone=barber["phone"],
        salon=barber["salon_name"],
        id=barber["id"]
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_premium_approve_keyboard(user_id, texts), 
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")
            
    await callback.answer(texts.get("premium_pending", "So'rov yuborildi"), show_alert=True)
    await barber_premium_status(callback, state, texts)


# ── Referral Link ──

@router.callback_query(F.data == "bset:referral")
async def bset_referral(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber = await barber_service.get_barber(callback.from_user.id)
    if not barber:
        return
    me = await callback.bot.get_me()
    bot_username = me.username
    barber_id = barber.get("id") or barber.get("telegram_id")
    link = f"https://t.me/{bot_username}?start=ref_{barber_id}"
    
    text = texts["referral_link_msg"].format(link=link)
    from app.keyboards.inline import back_button
    kb = InlineKeyboardMarkup(inline_keyboard=[[back_button("bmenu", texts)]])
    await ensure_flow_message(callback, text, state, keyboard=kb)


# ── Edit Name ──

@router.callback_query(F.data == "bset:name")
async def bset_name_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.edit_name)
    await ensure_flow_message(callback, texts["enter_new_name"], state)


@router.message(BarberMenuFSM.edit_name, F.text)
async def bset_name_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer(texts["enter_new_name"])
        return
    await barber_service.update_barber_field(message.from_user.id, "name", name)
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(message, texts["settings_saved"])
    await ensure_flow_message(message, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


# ── Edit Phone ──

@router.callback_query(F.data == "bset:phone")
async def bset_phone_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.edit_phone)
    await callback.message.answer(texts["share_phone"], reply_markup=phone_request_keyboard(texts))
    await callback.answer()


@router.message(BarberMenuFSM.edit_phone, F.contact)
async def bset_phone_contact(message: Message, state: FSMContext, texts: dict, **kwargs):
    import re
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    if not re.match(r"^\+998\d{9}$", phone):
        await message.answer(texts["invalid_phone"])
        return
    await barber_service.update_barber_field(message.from_user.id, "phone", phone)
    await state.set_state(BarberMenuFSM.menu)
    await message.answer("⠀", reply_markup=main_menu_reply_keyboard(texts))
    await send_ok_popup(message, texts["settings_saved"])
    await ensure_flow_message(message, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


@router.message(BarberMenuFSM.edit_phone, F.text)
async def bset_phone_text(message: Message, state: FSMContext, texts: dict, **kwargs):
    import re
    phone = message.text.strip()
    if not re.match(r"^\+998\d{9}$", phone):
        await message.answer(texts["invalid_phone"])
        return
    await barber_service.update_barber_field(message.from_user.id, "phone", phone)
    await state.set_state(BarberMenuFSM.menu)
    await message.answer("⠀", reply_markup=main_menu_reply_keyboard(texts))
    await send_ok_popup(message, texts["settings_saved"])
    await ensure_flow_message(message, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


# ── Edit Location ──

@router.callback_query(F.data == "bset:location")
async def bset_location_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.edit_location)
    await callback.message.answer(texts["share_location"], reply_markup=location_request_keyboard(texts))
    await callback.answer()


@router.message(BarberMenuFSM.edit_location, F.location)
async def bset_location_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    await barber_service.update_barber_field(message.from_user.id, "lat", message.location.latitude)
    await barber_service.update_barber_field(message.from_user.id, "lon", message.location.longitude)
    await state.set_state(BarberMenuFSM.menu)
    await message.answer("⠀", reply_markup=main_menu_reply_keyboard(texts))
    await send_ok_popup(message, texts["settings_saved"])
    await ensure_flow_message(message, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


# ── Edit Photo ──

@router.callback_query(F.data == "bset:photo")
async def bset_photo_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(BarberMenuFSM.edit_photo)
    await ensure_flow_message(callback, texts["send_new_photo"], state)


@router.message(BarberMenuFSM.edit_photo, F.photo)
async def bset_photo_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    file_id = message.photo[-1].file_id
    await barber_service.update_barber_field(message.from_user.id, "photo_file_id", file_id)
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(message, texts["settings_saved"])
    await ensure_flow_message(message, texts["barber_settings_title"], state,
                               keyboard=barber_settings_keyboard(texts))


# ── Language ──

@router.callback_query(F.data == "bset:lang")
async def bset_lang(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await ensure_flow_message(callback, texts["choose_lang"], state,
                               keyboard=lang_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def on_lang_chosen(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Update barber lang if barber
    barber = await barber_service.get_barber(user_id)
    if barber:
        await barber_service.update_barber_field(user_id, "lang", lang)

    # Update client lang if client
    from app.services.client_service import get_client, update_client_field
    client = await get_client(user_id)
    if client:
        await update_client_field(user_id, "lang", lang)

    # Reload texts
    from app.i18n.uz import TEXTS_UZ
    from app.i18n.ru import TEXTS_RU
    new_texts = TEXTS_RU if lang == "ru" else TEXTS_UZ

    await callback.answer(new_texts["lang_changed"], show_alert=True)

    # Return to appropriate menu
    if barber and barber["status"] == "APPROVED":
        await ensure_flow_message(callback, new_texts["barber_menu_title"], state,
                                   keyboard=barber_menu_keyboard(new_texts))
    elif client:
        from app.keyboards.inline import client_menu_keyboard
        await ensure_flow_message(callback, new_texts["client_menu_title"], state,
                                   keyboard=client_menu_keyboard(new_texts))


# ═══════════════════════════════════════════
# Work Photos Gallery
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:photos")
async def barber_photos(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_barber_photos(callback, state, texts, 0)


@router.callback_query(F.data.startswith("bphoto:prev:") | F.data.startswith("bphoto:next:"))
async def barber_photo_nav(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    idx = int(callback.data.split(":")[2])
    await _show_barber_photos(callback, state, texts, idx)


async def _show_barber_photos(event, state, texts, idx):
    barber_id = event.from_user.id
    photos = await barber_service.get_barber_photos(barber_id)

    if not photos:
        # Show add button
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts["btn_add_photo"], callback_data="bphoto:add")],
            [InlineKeyboardButton(text=texts["back"], callback_data="back:bmenu")],
        ])
        await ensure_flow_message(event, texts["no_work_photos"], state, keyboard=kb)
        return

    idx = max(0, min(idx, len(photos) - 1))
    photo = photos[idx]
    kb = media_gallery_keyboard(idx, len(photos), photo["id"], "photo", texts)

    # Add "Add photo" button if under max
    if len(photos) < 10:
        kb.inline_keyboard.insert(-1, [InlineKeyboardButton(
            text=texts["btn_add_photo"], callback_data="bphoto:add"
        )])

    await ensure_flow_message(event, texts["work_photos_title"], state,
                               keyboard=kb, photo=photo["file_id"])


@router.callback_query(F.data == "bphoto:add")
async def barber_add_photo(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    photos = await barber_service.get_barber_photos(callback.from_user.id)
    if len(photos) >= 10:
        await callback.answer(texts["max_media_reached"], show_alert=True)
        return
    await state.set_state(BarberMenuFSM.add_work_photo)
    await ensure_flow_message(callback, texts["send_work_photo"], state)


@router.message(BarberMenuFSM.add_work_photo, F.photo)
async def barber_receive_work_photo(message: Message, state: FSMContext, texts: dict, **kwargs):
    file_id = message.photo[-1].file_id
    await barber_service.add_barber_photo(message.from_user.id, file_id)
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(message, texts["photo_added"])
    await _show_barber_photos(message, state, texts, 0)


@router.callback_query(F.data.startswith("bphoto:del:"))
async def barber_delete_photo(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    photo_id = int(callback.data.split(":")[2])
    await barber_service.delete_barber_photo(photo_id)
    await callback.answer(texts["photo_deleted"], show_alert=True)
    await _show_barber_photos(callback, state, texts, 0)


# ═══════════════════════════════════════════
# Work Videos Gallery
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:videos")
async def barber_videos(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_barber_videos(callback, state, texts, 0)


@router.callback_query(F.data.startswith("bvideo:prev:") | F.data.startswith("bvideo:next:"))
async def barber_video_nav(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    idx = int(callback.data.split(":")[2])
    await _show_barber_videos(callback, state, texts, idx)


async def _show_barber_videos(event, state, texts, idx):
    barber_id = event.from_user.id
    videos = await barber_service.get_barber_videos(barber_id)

    if not videos:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts["btn_add_video"], callback_data="bvideo:add")],
            [InlineKeyboardButton(text=texts["back"], callback_data="back:bmenu")],
        ])
        await ensure_flow_message(event, texts["no_work_videos"], state, keyboard=kb)
        return

    idx = max(0, min(idx, len(videos) - 1))
    video = videos[idx]
    kb = media_gallery_keyboard(idx, len(videos), video["id"], "video", texts)

    if len(videos) < 10:
        kb.inline_keyboard.insert(-1, [InlineKeyboardButton(
            text=texts["btn_add_video"], callback_data="bvideo:add"
        )])

    # Send video as separate message (can't edit to video)
    try:
        await event.answer() if isinstance(event, CallbackQuery) else None
    except Exception:
        pass

    # We need to delete old flow msg and send video
    data = await state.get_data()
    flow_msg_id = data.get("flow_msg_id")
    chat_id = event.from_user.id
    if flow_msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=flow_msg_id)
        except Exception:
            pass

    msg = await bot.send_video(
        chat_id=chat_id,
        video=video["file_id"],
        caption=f"{texts['work_videos_title']} ({idx + 1}/{len(videos)})",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.update_data(flow_msg_id=msg.message_id)


@router.callback_query(F.data == "bvideo:add")
async def barber_add_video(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    videos = await barber_service.get_barber_videos(callback.from_user.id)
    if len(videos) >= 10:
        await callback.answer(texts["max_media_reached"], show_alert=True)
        return
    await state.set_state(BarberMenuFSM.add_work_video)
    await ensure_flow_message(callback, texts["send_work_video"], state)


@router.message(BarberMenuFSM.add_work_video, F.video)
async def barber_receive_work_video(message: Message, state: FSMContext, texts: dict, **kwargs):
    file_id = message.video.file_id
    await barber_service.add_barber_video(message.from_user.id, file_id)
    await state.set_state(BarberMenuFSM.menu)
    await send_ok_popup(message, texts["video_added"])
    await _show_barber_videos(message, state, texts, 0)


@router.callback_query(F.data.startswith("bvideo:del:"))
async def barber_delete_video(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    video_id = int(callback.data.split(":")[2])
    await barber_service.delete_barber_video(video_id)
    await callback.answer(texts["video_deleted"], show_alert=True)
    await _show_barber_videos(callback, state, texts, 0)


# ═══════════════════════════════════════════
# My Rating
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:rating")
async def barber_my_rating(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = callback.from_user.id
    avg, count = await barber_service.get_barber_avg_rating(barber_id)
    comments = await barber_service.get_barber_comments(barber_id)

    stars_display = "⭐" * int(avg) + ("½" if avg - int(avg) >= 0.5 else "")
    text = texts["my_rating_title"].format(avg=avg, count=count, stars=stars_display)

    if comments:
        text += "\n\n" + texts["comments_header"]
        for c in comments[:20]:
            text += f"\n👤 {c['client_name']}: {c['comment']}"

    from app.keyboards.inline import back_button
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [back_button("bmenu", texts)]
    ])
    await ensure_flow_message(callback, text, state, keyboard=kb)


# ═══════════════════════════════════════════
# Users Count / Served Count
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:users_count")
async def barber_users_count(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    from app.services.user_service import get_total_users
    total = await get_total_users()
    await send_ok_popup(callback, texts["total_users"].format(count=total))


@router.callback_query(F.data == "bmenu:served_count")
async def barber_served_count(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    count = await barber_service.get_barber_served_count(callback.from_user.id)
    await send_ok_popup(callback, texts["served_clients"].format(count=count))


# ═══════════════════════════════════════════
# Support & About
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bmenu:support")
async def barber_support(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    username = await admin_service.get_support_username()
    await send_ok_popup(callback, texts["support_contact"].format(username=username))


@router.callback_query(F.data == "bmenu:about")
async def barber_about(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await send_ok_popup(callback, texts["about_barber"])


# ═══════════════════════════════════════════
# Noop
# ═══════════════════════════════════════════

@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery, **kwargs):
    await callback.answer()
