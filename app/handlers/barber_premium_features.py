"""Premium feature handlers: P1 client reminders, P3 analytics."""
import logging
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services import barber_service, booking_service
from app.services import reminder_service
from app.keyboards.inline import (
    premium_menu_keyboard, reminder_days_keyboard,
    analytics_category_keyboard, back_button,
)
from app.utils.flow_message import ensure_flow_message
from app.utils.pagination import paginate
from app.config import BROADCAST_BATCH_SIZE, BROADCAST_PAUSE_SECONDS
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger("barbershop")

router = Router(name="barber_premium_features")


class PremiumFSM(StatesGroup):
    reminder_custom_days = State()


# ═══════════════════════════════════════════
# Premium Menu
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bprem:menu")
async def premium_menu(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber = await barber_service.get_barber(callback.from_user.id)
    if not barber or barber.get("premium_status") != "ACTIVE":
        await callback.answer("Premium obunangiz faol emas!", show_alert=True)
        return
    await ensure_flow_message(callback, texts["premium_menu_title"], state,
                               keyboard=premium_menu_keyboard(texts))


@router.callback_query(F.data == "back:bprem_menu")
async def back_to_premium_menu(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await premium_menu(callback, state, texts)


# ═══════════════════════════════════════════
# P1 — Client Reminders
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bprem:reminder")
async def reminder_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber = await barber_service.get_barber(callback.from_user.id)
    if not barber or barber.get("premium_status") != "ACTIVE":
        await callback.answer("Premium obunangiz faol emas!", show_alert=True)
        return
    text = texts["reminder_days_title"]
    auto_days = barber.get("auto_reminder_days", 0)
    if auto_days > 0:
        text += texts["auto_reminder_info"].format(days=auto_days)
    
    await ensure_flow_message(callback, text, state,
                               keyboard=reminder_days_keyboard(texts))


@router.callback_query(F.data.startswith("bprem:remind_days:"))
async def reminder_days_chosen(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    days = int(callback.data.split(":")[2])
    await barber_service.update_auto_reminder_days(callback.from_user.id, days)
    await callback.answer(texts.get("auto_reminder_set", "Avtomatik eslatma saqlandi."), show_alert=True)
    await _send_reminders(callback, state, texts, days)


@router.callback_query(F.data == "bprem:remind_custom")
async def reminder_custom(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(PremiumFSM.reminder_custom_days)
    await ensure_flow_message(callback, texts["reminder_custom_prompt"], state)


@router.message(PremiumFSM.reminder_custom_days)
async def reminder_custom_receive(message: Message, state: FSMContext, texts: dict, **kwargs):
    try:
        days = int(message.text.strip())
        if days < 1 or days > 365:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(texts["error_generic"])
        return
    await state.clear()
    await barber_service.update_auto_reminder_days(message.from_user.id, days)
    await message.answer(texts.get("auto_reminder_set", "Avtomatik eslatma saqlandi."))
    await _send_reminders(message, state, texts, days)


async def _send_reminders(event, state, texts, days):
    """Send reminders to clients who haven't visited for N days."""
    user_id = event.from_user.id
    barber = await barber_service.get_barber(user_id)
    if not barber:
        return

    clients = await reminder_service.get_clients_not_visited(user_id, days)
    if not clients:
        await ensure_flow_message(event, texts["reminder_no_clients"], state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("bprem_menu", texts)]
                                   ]))
        return

    # Build referral link
    from app.loader import bot as bot_instance
    bot_info = await bot_instance.get_me()
    barber_id = barber.get("id") or barber.get("telegram_id")
    link = f"https://t.me/{bot_info.username}?start=ref_{barber_id}"

    from app.utils.time_utils import tashkent_now
    from datetime import timedelta
    now = tashkent_now()

    sent = 0
    for i, client in enumerate(clients):
        try:
            last_visit = client.get("last_visit", "")
            if last_visit:
                from datetime import datetime
                lv_date = datetime.strptime(last_visit, '%Y-%m-%d')
                actual_days = (now.replace(tzinfo=None) - lv_date).days
            else:
                actual_days = days

            text = texts["reminder_text"].format(
                name=client["name"],
                days=actual_days,
                link=link,
            )
            await bot_instance.send_message(chat_id=client["telegram_id"], text=text)
            await reminder_service.mark_reminder_sent(user_id, client["telegram_id"])
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send reminder to {client['telegram_id']}: {e}")

        # Rate limit
        if (i + 1) % BROADCAST_BATCH_SIZE == 0:
            await asyncio.sleep(BROADCAST_PAUSE_SECONDS)

    result_text = texts["reminder_done"].format(sent=sent)
    await ensure_flow_message(event, result_text, state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                   [back_button("bprem_menu", texts)]
                               ]))


# ═══════════════════════════════════════════
# P3 — Analytics
# ═══════════════════════════════════════════

@router.callback_query(F.data == "bprem:analytics")
async def analytics_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber = await barber_service.get_barber(callback.from_user.id)
    if not barber or barber.get("premium_status") != "ACTIVE":
        await callback.answer("Premium obunangiz faol emas!", show_alert=True)
        return
    await ensure_flow_message(callback, texts["analytics_title"], state,
                               keyboard=analytics_category_keyboard(texts))


@router.callback_query(F.data.startswith("bprem:ana:"))
async def analytics_category(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    category = callback.data.split(":")[2]
    await state.update_data(ana_category=category)
    await _show_analytics_page(callback, state, texts, category, 0)


@router.callback_query(F.data.startswith("page:ana:"))
async def analytics_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    category = parts[2]
    page = int(parts[3])
    await _show_analytics_page(callback, state, texts, category, page)


async def _show_analytics_page(event, state, texts, category, page):
    user_id = event.from_user.id
    clients = await booking_service.get_analytics_clients(user_id, category)

    category_names = {
        "kamnamo": "🐢 Kamnamo",
        "doimiy": "🔄 Doimiy",
        "yoqotilgan": "⚠️ Yo'qotilgan",
    }

    if not clients:
        await ensure_flow_message(event, texts["analytics_empty"], state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("bprem_analytics", texts)]
                                   ]))
        return

    page_items, total_pages, has_prev, has_next = paginate(clients, page)

    header = texts["analytics_list_title"].format(
        category=category_names.get(category, category),
        count=len(clients)
    )

    lines = [header]
    rows = []
    for c in page_items:
        phone_last4 = c.get("phone", "")[-4:] if c.get("phone") else "????"
        lines.append(f"\n👤 {c['name']} (***{phone_last4})")

        rows.append([InlineKeyboardButton(
            text=f"👤 {c['name']}",
            callback_data=f"bprem:client:{c['telegram_id']}:{category}"
        )])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:ana:{category}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:ana:{category}:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([back_button("bprem_analytics", texts)])

    await ensure_flow_message(event, "\n".join(lines), state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "back:bprem_analytics")
async def back_to_analytics(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await analytics_start(callback, state, texts)


@router.callback_query(F.data.startswith("back:page_ana_"))
async def back_to_analytics_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split("_")
    category = parts[2]
    page = int(parts[3])
    await _show_analytics_page(callback, state, texts, category, page)


# ── Client Detail Card ──

@router.callback_query(F.data.startswith("bprem:client:"))
async def client_detail(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    client_id = int(parts[2])
    category = parts[3] if len(parts) > 3 else "kamnamo"

    barber_id = callback.from_user.id
    from app.services import client_service
    client = await client_service.get_client(client_id)
    if not client:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    visits = await booking_service.get_client_visit_dates(barber_id, client_id)
    total = len(visits)
    last_visit = visits[0]["date"] if visits else "—"

    text = texts["client_detail_card"].format(
        name=client["name"],
        phone=client.get("phone", "—"),
        total=total,
        last_visit=last_visit,
    )

    rows = [
        [InlineKeyboardButton(
            text=texts["btn_send_reminder_single"],
            callback_data=f"bprem:send1:{client_id}"
        )],
        [back_button(f"page_ana_{category}_0", texts)],
    ]

    # Add visit dates (up to 10)
    if visits:
        visit_lines = []
        for v in visits[:10]:
            visit_lines.append(f"📅 {v['date']}")
        text += "\n\n📅 <b>Oxirgi tashriflar:</b>\n" + "\n".join(visit_lines)
        if total > 10:
            text += f"\n... va yana {total - 10} ta"

    await ensure_flow_message(callback, text, state,
                               keyboard=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("bprem:send1:"))
async def send_single_reminder(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    client_id = int(callback.data.split(":")[2])
    barber_id = callback.from_user.id

    barber = await barber_service.get_barber(barber_id)
    from app.services import client_service
    client = await client_service.get_client(client_id)
    if not barber or not client:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    from app.loader import bot as bot_instance
    bot_info = await bot_instance.get_me()
    barber_id = barber.get("id") or barber.get("telegram_id")
    link = f"https://t.me/{bot_info.username}?start=ref_{barber_id}"

    from app.utils.time_utils import tashkent_now
    from datetime import datetime
    now = tashkent_now()
    visits = await booking_service.get_client_visit_dates(barber_id, client_id)
    if visits:
        lv_date = datetime.strptime(visits[0]["date"], '%Y-%m-%d')
        actual_days = (now.replace(tzinfo=None) - lv_date).days
    else:
        actual_days = 0

    try:
        text = texts["reminder_text"].format(
            name=client["name"],
            days=actual_days,
            link=link,
        )
        await bot_instance.send_message(chat_id=client_id, text=text)
        await reminder_service.mark_reminder_sent(barber_id, client_id)
        await callback.answer(texts["single_reminder_sent"], show_alert=True)
    except Exception as e:
        logger.error(f"Failed single reminder to {client_id}: {e}")
        await callback.answer(texts["error_generic"], show_alert=True)
