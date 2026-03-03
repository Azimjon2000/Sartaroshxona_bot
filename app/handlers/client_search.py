"""Client search, barber card, booking flow, top rated, media/review viewing."""
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states.client_menu import ClientMenuFSM
from app.services import barber_service, booking_service, client_service
from app.db.base import fetch_all, fetch_one
from app.keyboards.inline import (
    search_method_keyboard, radius_keyboard,
    barber_card_keyboard, booking_slots_keyboard,
    booking_confirm_keyboard, client_menu_keyboard,
    ok_keyboard,
)
from app.keyboards.reply import location_request_keyboard, main_menu_reply_keyboard, remove_keyboard
from app.utils.flow_message import ensure_flow_message, send_ok_popup
from app.utils.geo import haversine_distance
from app.utils.pagination import paginate
from app.utils.time_utils import today_tashkent, slot_to_hour, seconds_until_slot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.keyboards.inline import back_button, barber_reg_regions_keyboard, barber_reg_districts_keyboard
from app.loader import bot

logger = logging.getLogger("barbershop")

router = Router(name="client_search")


# ═══════════════════════════════════════════
# Search Entry Point
# ═══════════════════════════════════════════

async def enforce_referral_lock(callback: CallbackQuery, state: FSMContext, texts: dict) -> bool:
    """Check if the client is locked today and redirect to barber card if so."""
    from app.utils.time_utils import today_uz_str
    user_id = callback.from_user.id
    
    client = await client_service.get_client(user_id)
    if client and client.get("ref_lock_date") == today_uz_str():
        ref_barber_id = client.get("ref_barber_id")
        if ref_barber_id:
            barber = await barber_service.get_barber_by_db_id(ref_barber_id)
            if barber:
                # Enforce globally required rating checks before letting them access the card
                unrated = await booking_service.get_client_unrated_done(user_id)
                if unrated:
                    from app.keyboards.inline import unrated_booking_keyboard
                    kb = unrated_booking_keyboard(unrated["id"], texts)
                    await ensure_flow_message(callback, texts["rate_before_book"], state, keyboard=kb)
                    return True

                # Check booking limit violations
                active_booking = await booking_service.get_client_active_booking(user_id)
                if active_booking:
                    text = texts["active_booking_block_msg"]
                    booking_id = active_booking["id"]
                    from app.keyboards.inline import back_button
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=texts["btn_view_active_booking"], callback_data="cmenu:active_orders")],
                        [InlineKeyboardButton(text=texts["cancel"], callback_data=f"cbook:cancel_ask:{booking_id}")],
                        [back_button("cmenu", texts)]
                    ])
                    await ensure_flow_message(callback, text, state, keyboard=kb)
                    return True
                    
                # Check for ANY Usage Today (Strict Limit)
                from app.utils.time_utils import today_tashkent
                today = today_tashkent()
                usage = await booking_service.get_client_today_usage(user_id, today)
                if usage:
                    text = texts.get("done_booking_block_msg", "Siz bugun xizmatdan foydalanib bo'lgansiz.")
                    from app.keyboards.inline import back_button
                    kb = InlineKeyboardMarkup(inline_keyboard=[[back_button("cmenu", texts)]])
                    await ensure_flow_message(callback, text, state, keyboard=kb)
                    return True
                    
                await callback.answer(texts.get("referral_locked_search_msg", "Siz bugun faqat vizitka orqali yozila olasiz!"), show_alert=True)
                await show_barber_card(callback, state, texts, barber["telegram_id"])
                return True
    return False

@router.callback_query(F.data == "cmenu:search")
async def client_search_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    if await enforce_referral_lock(callback, state, texts):
        return

    # Check if client has unrated booking
    unrated = await booking_service.get_client_unrated_done(callback.from_user.id)
    if unrated:
        from app.keyboards.inline import unrated_booking_keyboard
        kb = unrated_booking_keyboard(unrated["id"], texts)
        await ensure_flow_message(callback, texts["rate_before_book"], state, keyboard=kb)
        return

    # 1. Check for Active Booking
    active_booking = await booking_service.get_client_active_booking(callback.from_user.id)
    if active_booking:
        # Block search, show "View / Cancel"
        text = texts["active_booking_block_msg"]
        booking_id = active_booking["id"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts["btn_view_active_booking"], callback_data="cmenu:active_orders")],
            [InlineKeyboardButton(text=texts["cancel"], callback_data=f"cbook:cancel_ask:{booking_id}")],
            [back_button("cmenu", texts)]
        ])
        await ensure_flow_message(callback, text, state, keyboard=kb)
        return

    # 2. Check for ANY Usage Today (Strict Limit)
    from app.utils.time_utils import today_tashkent
    today = today_tashkent()
    # Check for any confirmed/done booking today
    usage = await booking_service.get_client_today_usage(callback.from_user.id, today)
    if usage:
        # If usage exists, user cannot book again today.
        # Exception: if it is the SAME as active_booking, we already handled it above.
        # But get_client_today_usage returns CONFIRMED (which might be active) or DONE.
        # If it returns a CONFIRMED booking that is NOT active (e.g. past hour but not done?), 
        # actually get_client_active_booking covers future. 
        # get_client_today_usage covers today's history.
        
        # If we are here, active_booking is None. So client has no FUTURE confirmed bookings.
        # So 'usage' must be a DONE booking or a past-hour CONFIRMED booking (not marked done yet).
        # In either case, they practiced a slot today. So block.
        
        text = texts["done_booking_block_msg"]
        kb = InlineKeyboardMarkup(inline_keyboard=[[back_button("cmenu", texts)]])
        await ensure_flow_message(callback, text, state, keyboard=kb)
        return

    await ensure_flow_message(callback, texts["search_method"], state,
                               keyboard=search_method_keyboard(texts))


@router.callback_query(F.data == "back:csearch")
async def back_to_search(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await ensure_flow_message(callback, texts["search_method"], state,
                               keyboard=search_method_keyboard(texts))


# ═══════════════════════════════════════════
# Location-Based Search
# ═══════════════════════════════════════════

@router.callback_query(F.data == "csearch:location")
async def search_by_location(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(ClientMenuFSM.search_location)
    await callback.message.answer(texts["share_location"], reply_markup=location_request_keyboard(texts))
    await callback.answer()


@router.message(ClientMenuFSM.search_location, F.location)
async def on_client_location(message: Message, state: FSMContext, texts: dict, **kwargs):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(client_lat=lat, client_lon=lon)
    await state.set_state(None)
    
    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))
    # The above line replaces the 'Send Location' keyboard with Main Menu.
    # Send a new message for Radius since the old flow message (if any) or user message is gone
    await message.answer(texts["choose_radius"], reply_markup=radius_keyboard(texts))


@router.message(ClientMenuFSM.search_location, F.text.in_(["🏠 Asosiy menyu", "🏠 Главное меню"]))
async def on_search_location_cancel(message: Message, state: FSMContext, texts: dict, **kwargs):
    await state.clear()
    await message.answer(texts["client_menu_title"], reply_markup=client_menu_keyboard(texts))
    await message.answer(texts["select_action"], reply_markup=main_menu_reply_keyboard(texts))


@router.callback_query(F.data.startswith("csearch:radius:"))
async def on_radius_chosen(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    radius_km = int(callback.data.split(":")[2])
    
    # Delete the "Choose Radius" message to clean up chat
    try:
        await callback.message.delete()
    except Exception:
        pass

    data = await state.get_data()
    client_lat = data.get("client_lat")
    client_lon = data.get("client_lon")

    if not client_lat or not client_lon:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    # Phase 2 Optimization: First filter by Bounding Box in SQL
    barbers = await barber_service.get_barbers_nearby(client_lat, client_lon, radius_km)

    # Then calculate exact haversine distance and filter/sort
    nearby = []
    for b in barbers:
        dist = haversine_distance(client_lat, client_lon, b["lat"], b["lon"])
        if dist <= radius_km:
            nearby.append({**dict(b), "distance": round(dist, 1)})

    nearby.sort(key=lambda x: (
        0 if x.get("premium_status") == "ACTIVE" else 1,
        x["distance"]
    ))
    await state.update_data(search_results=[
        {"telegram_id": b["telegram_id"], "name": b["name"],
         "salon_name": b["salon_name"], "distance": b["distance"],
         "premium_status": b.get("premium_status")}
        for b in nearby
    ])
    await _show_barber_list(callback, state, texts, 0)


# ═══════════════════════════════════════════
# Manual Search (Region → District)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "csearch:manual")
async def search_manual(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(ClientMenuFSM.search_region)
    regions = await fetch_all("SELECT id, name_uz, name_ru FROM regions ORDER BY id")
    data = await state.get_data()
    back_cb = "back:cmenu" if data.get("search_mode") == "top_rated" else "back:csearch"
    await ensure_flow_message(callback, texts["choose_region"], state,
                               keyboard=barber_reg_regions_keyboard(regions, 0, texts, back_callback=back_cb))


@router.callback_query(ClientMenuFSM.search_region, F.data.startswith("breg:region:"))
async def on_search_region(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    region_id = int(callback.data.split(":")[2])
    await state.update_data(search_region_id=region_id)
    await state.set_state(ClientMenuFSM.search_district)
    districts = await fetch_all(
        "SELECT id, name_uz, name_ru FROM districts WHERE region_id = ? ORDER BY id",
        (region_id,),
    )
    await ensure_flow_message(callback, texts["choose_district"], state,
                               keyboard=barber_reg_districts_keyboard(districts, 0, texts))


@router.callback_query(ClientMenuFSM.search_region, F.data.startswith("page:region:"))
async def on_search_region_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    regions = await fetch_all("SELECT id, name_uz, name_ru FROM regions ORDER BY id")
    data = await state.get_data()
    back_cb = "back:cmenu" if data.get("search_mode") == "top_rated" else "back:csearch"
    await ensure_flow_message(callback, texts["choose_region"], state,
                               keyboard=barber_reg_regions_keyboard(regions, page, texts, back_callback=back_cb))


@router.callback_query(ClientMenuFSM.search_district, F.data.startswith("breg:district:"))
async def on_search_district(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    district_id = int(callback.data.split(":")[2])
    await state.set_state(None)

    barbers = await barber_service.get_barbers_by_district(district_id)
    result = []
    for b in barbers:
        avg, count = await barber_service.get_barber_avg_rating(b["telegram_id"])
        result.append({
            "telegram_id": b["telegram_id"], "name": b["name"],
            "salon_name": b["salon_name"], "distance": None,
            "avg_rating": avg, "served_count": count,
            "premium_status": b.get("premium_status"),
        })

    result.sort(key=lambda x: (
        0 if x.get("premium_status") == "ACTIVE" else 1,
        -x["avg_rating"], -x["served_count"]
    ))
    await state.update_data(search_results=[
        {"telegram_id": b["telegram_id"], "name": b["name"],
         "salon_name": b["salon_name"], "distance": b.get("distance"),
         "premium_status": b.get("premium_status")}
        for b in result
    ])
    await _show_barber_list(callback, state, texts, 0)


@router.callback_query(ClientMenuFSM.search_district, F.data.startswith("page:district:"))
async def on_search_district_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    data = await state.get_data()
    region_id = data.get("search_region_id")
    districts = await fetch_all(
        "SELECT id, name_uz, name_ru FROM districts WHERE region_id = ? ORDER BY id",
        (region_id,),
    )
    await ensure_flow_message(callback, texts["choose_district"], state,
                               keyboard=barber_reg_districts_keyboard(districts, page, texts))


@router.callback_query(ClientMenuFSM.search_district, F.data == "back:breg_region")
async def on_back_to_search_region(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await state.set_state(ClientMenuFSM.search_region)
    regions = await fetch_all("SELECT id, name_uz, name_ru FROM regions ORDER BY id")
    data = await state.get_data()
    back_cb = "back:cmenu" if data.get("search_mode") == "top_rated" else "back:csearch"
    await ensure_flow_message(callback, texts["choose_region"], state,
                               keyboard=barber_reg_regions_keyboard(regions, 0, texts, back_callback=back_cb))


# ═══════════════════════════════════════════
# Barber List (search results)
# ═══════════════════════════════════════════

async def _show_barber_list(event, state, texts, page):
    data = await state.get_data()
    results = data.get("search_results", [])

    if not results:
        await ensure_flow_message(event, texts["no_barbers_found"], state,
                                   keyboard=InlineKeyboardMarkup(inline_keyboard=[
                                       [back_button("csearch", texts)]
                                   ]))
        return

    page_items, total_pages, has_prev, has_next = paginate(results, page)

    rows = []
    for b in page_items:
        dist_str = f" ({b['distance']} km)" if b.get("distance") is not None else ""
        prefix = "👑 " if b.get("premium_status") == "ACTIVE" else "💈 "
        rows.append([InlineKeyboardButton(
            text=f"{prefix}{b['name']} — {b['salon_name']}{dist_str}",
            callback_data=f"cbarber:view:{b['telegram_id']}",
        )])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:csearch:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:csearch:{page + 1}"))
    if nav:
        rows.append(nav)

    if data.get("search_region_id"):
        # Back to district list
        region_id = data.get("search_region_id")
        rows.append([InlineKeyboardButton(text=texts["back"], callback_data=f"breg:region:{region_id}")])
    else:
        # Back to location/search method
        rows.append([back_button("csearch", texts)])

    await ensure_flow_message(
        event, texts["barber_list_title"].format(count=len(results)), state,
        keyboard=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("page:csearch:"))
async def barber_list_page(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    page = int(callback.data.split(":")[2])
    await _show_barber_list(callback, state, texts, page)


@router.callback_query(F.data == "back:csearch_list")
async def back_to_search_list(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    await _show_barber_list(callback, state, texts, 0)


# ═══════════════════════════════════════════
# Barber Card
# ═══════════════════════════════════════════

@router.callback_query(F.data.startswith("cbarber:view:"))
async def barber_card_view(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await show_barber_card(callback, state, texts, barber_id)


async def show_barber_card(event, state, texts, barber_id):
    barber = await barber_service.get_barber(barber_id)
    if not barber:
        await send_ok_popup(event, texts["no_barbers_found"])
        return

    prices = await barber_service.get_prices(barber_id)
    avg, served = await barber_service.get_barber_avg_rating(barber_id)

    card = texts["barber_card_text"].format(
        name=barber["name"],
        salon_name=barber["salon_name"],
        rating=f"{avg}/5",
        served=served,
        phone=barber["phone"],
        hair_price=prices["hair_price"] if prices and prices["hair_price"] else "—",
        beard_price=prices["beard_price"] if prices and prices["beard_price"] else "—",
        groom_price=prices["groom_price"] if prices and prices["groom_price"] else "—",
        extra_note=prices["extra_note"] if prices and prices["extra_note"] else "",
    )

    kb = barber_card_keyboard(barber_id, texts)
    await state.update_data(current_barber_id=barber_id)

    if barber.get("photo_file_id"):
        await ensure_flow_message(event, card, state, keyboard=kb, photo=barber["photo_file_id"])
    else:
        await ensure_flow_message(event, card, state, keyboard=kb)


@router.callback_query(F.data.startswith("cbarber:") & F.data.contains(":"))
async def barber_card_actions(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    action = parts[1]
    barber_id = int(parts[2]) if len(parts) > 2 else 0

    if action == "location":
        barber = await barber_service.get_barber(barber_id)
        if barber and barber.get("lat") and barber.get("lon"):
            await bot.send_location(
                chat_id=callback.from_user.id,
                latitude=barber["lat"],
                longitude=barber["lon"],
            )
            await callback.answer()
        else:
            await callback.answer(texts["no_location_data"], show_alert=True)

    elif action == "photos":
        await _show_client_barber_photos(callback, state, texts, barber_id, 0)

    elif action == "videos":
        await _show_client_barber_videos(callback, state, texts, barber_id, 0)

    elif action == "reviews":
        await _show_barber_reviews(callback, state, texts, barber_id)

    elif action == "book":
        # Check unrated
        unrated = await booking_service.get_client_unrated_done(callback.from_user.id)
        if unrated:
            await callback.answer(texts["rate_before_book"], show_alert=True)
            return

        # Check premium expired barber
        barber = await barber_service.get_barber(barber_id)
        if barber and barber.get("is_blocked_temp") == 1:
            await callback.answer(texts.get("premium_barber_blocked_msg", "Bu sartarosh hozirda mavjud emas."), show_alert=True)
            return

        # P2: Premium barber → show date picker
        if barber and barber.get("premium_status") == "ACTIVE":
            from app.keyboards.inline import future_booking_date_keyboard
            await ensure_flow_message(callback, texts["choose_booking_date"], state,
                                       keyboard=future_booking_date_keyboard(barber_id, texts))
        else:
            await _show_booking_slots(callback, state, texts, barber_id, today_tashkent())


# ═══════════════════════════════════════════
# Client viewing barber's photos/videos/reviews
# ═══════════════════════════════════════════

async def _show_client_barber_photos(event, state, texts, barber_id, idx):
    photos = await barber_service.get_barber_photos(barber_id)
    if not photos:
        await send_ok_popup(event, texts["no_work_photos"])
        return

    idx = max(0, min(idx, len(photos) - 1))
    photo = photos[idx]

    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cph:prev:{barber_id}:{idx - 1}"))
    nav.append(InlineKeyboardButton(text=f"{idx + 1}/{len(photos)}", callback_data="noop"))
    if idx < len(photos) - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cph:next:{barber_id}:{idx + 1}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [back_button(f"cbarber_card:{barber_id}", texts)],
    ])
    await ensure_flow_message(event, texts["work_photos_title"], state,
                               keyboard=kb, photo=photo["file_id"])


@router.callback_query(F.data.startswith("cph:prev:") | F.data.startswith("cph:next:"))
async def client_photo_nav(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    barber_id = int(parts[2])
    idx = int(parts[3])
    await _show_client_barber_photos(callback, state, texts, barber_id, idx)


async def _show_client_barber_videos(event, state, texts, barber_id, idx):
    videos = await barber_service.get_barber_videos(barber_id)
    if not videos:
        await send_ok_popup(event, texts["no_work_videos"])
        return

    idx = max(0, min(idx, len(videos) - 1))
    video = videos[idx]

    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cvd:prev:{barber_id}:{idx - 1}"))
    nav.append(InlineKeyboardButton(text=f"{idx + 1}/{len(videos)}", callback_data="noop"))
    if idx < len(videos) - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cvd:next:{barber_id}:{idx + 1}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [back_button(f"cbarber_card:{barber_id}", texts)],
    ])

    # Delete old flow, send video
    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass

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


@router.callback_query(F.data.startswith("cvd:prev:") | F.data.startswith("cvd:next:"))
async def client_video_nav(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    barber_id = int(parts[2])
    idx = int(parts[3])
    await _show_client_barber_videos(callback, state, texts, barber_id, idx)


async def _show_barber_reviews(event, state, texts, barber_id):
    comments = await barber_service.get_barber_comments(barber_id)
    if not comments:
        await send_ok_popup(event, texts["no_reviews"])
        return

    text = texts["reviews_title"] + "\n"
    for c in comments[:20]:
        text += f"\n👤 {c['client_name']}: {c['comment']}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [back_button(f"cbarber_card:{barber_id}", texts)],
    ])
    await ensure_flow_message(event, text, state, keyboard=kb)


# ── Back to barber card from sub-views ──

@router.callback_query(F.data.startswith("back:cbarber_card:"))
async def back_to_barber_card(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.split(":")[2])
    await show_barber_card(callback, state, texts, barber_id)


# ═══════════════════════════════════════════
# P2 — Future Booking Date Selection
# ═══════════════════════════════════════════

@router.callback_query(F.data.startswith("cbook:date:"))
async def on_date_chosen(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    barber_id = int(parts[2])
    date_choice = parts[3]

    if date_choice == "today":
        target_date = today_tashkent()
    elif date_choice == "tomorrow":
        from datetime import timedelta
        from app.utils.time_utils import tashkent_now
        target_date = (tashkent_now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target_date = today_tashkent()

    existing = await booking_service.get_client_booking_for_date(callback.from_user.id, target_date)
    if existing:
        await callback.answer(texts["booking_date_blocked"], show_alert=True)
        return

    await _show_booking_slots(callback, state, texts, barber_id, target_date)


@router.callback_query(F.data.startswith("cbook:cal:"))
async def on_calendar_view(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    barber_id = int(parts[2])
    year = int(parts[3])
    month = int(parts[4])

    if year == 0 and month == 0:
        from app.utils.time_utils import tashkent_now
        now = tashkent_now()
        year = now.year
        month = now.month

    from app.keyboards.inline import calendar_keyboard
    await ensure_flow_message(callback, texts.get("choose_booking_date", "Sana tanlang:"), state,
                               keyboard=calendar_keyboard(barber_id, year, month, texts))


@router.callback_query(F.data.startswith("cbook:pick:"))
async def on_calendar_pick(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    parts = callback.data.split(":")
    barber_id = int(parts[2])
    target_date = parts[3]

    existing = await booking_service.get_client_booking_for_date(callback.from_user.id, target_date)
    if existing:
        await callback.answer(texts["booking_date_blocked"], show_alert=True)
        return

    await _show_booking_slots(callback, state, texts, barber_id, target_date)


@router.callback_query(F.data.startswith("back:cbook_datepick_"))
async def back_to_date_pick(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    barber_id = int(callback.data.replace("back:cbook_datepick_", ""))
    from app.keyboards.inline import future_booking_date_keyboard
    await ensure_flow_message(callback, texts["choose_booking_date"], state,
                               keyboard=future_booking_date_keyboard(barber_id, texts))


# ═══════════════════════════════════════════
# Booking Flow
# ═══════════════════════════════════════════

async def _show_booking_slots(event, state, texts, barber_id, target_date=None):
    if target_date is None:
        target_date = today_tashkent()
    work_hours = await barber_service.get_work_hours(barber_id)
    confirmed = await booking_service.get_confirmed_slots(barber_id, target_date)

    enabled_slots = [wh for wh in work_hours if wh["is_enabled"]]
    if not enabled_slots:
        await send_ok_popup(event, texts["no_available_slots"])
        return

    today = today_tashkent()
    slots = []
    for wh in enabled_slots:
        slot = dict(wh)
        slot["booked"] = wh["hour_slot"] in confirmed
        if target_date == today:
            remaining = seconds_until_slot(target_date, wh["hour_slot"])
            if remaining < 0:
                slot["booked"] = True
        slots.append(slot)

    await state.update_data(booking_barber_id=barber_id, booking_date=target_date)
    await ensure_flow_message(event, texts["book_choose_slot"], state,
                               keyboard=booking_slots_keyboard(slots, barber_id, texts))


@router.callback_query(F.data.startswith("cbook:slot:"))
async def on_slot_chosen(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    hour_slot = int(callback.data.split(":")[2])
    data = await state.get_data()
    barber_id = data.get("booking_barber_id")
    date = data.get("booking_date", today_tashkent())

    if not barber_id:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    # Create draft booking
    booking_id = await booking_service.create_draft_booking(barber_id, callback.from_user.id, date, hour_slot)
    await state.update_data(draft_booking_id=booking_id)

    barber = await barber_service.get_barber(barber_id)
    hour = slot_to_hour(hour_slot)

    text = texts["book_confirm_text"].format(
        barber_name=barber["name"] if barber else "?",
        hour=f"{hour:02d}",
        date=date,
    )
    await ensure_flow_message(callback, text, state,
                               keyboard=booking_confirm_keyboard(booking_id, texts))


@router.callback_query(F.data.startswith("cbook:confirm:"))
async def on_booking_confirm(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])

    success = await booking_service.confirm_booking(booking_id)
    if not success:
        await callback.answer(texts["book_slot_taken"], show_alert=True)
        return

    booking = await booking_service.get_booking(booking_id)
    barber = await barber_service.get_barber(booking["barber_id"])
    client = await client_service.get_client(callback.from_user.id)
    hour = slot_to_hour(booking["hour_slot"])

    # Notify client
    price_info = await barber_service.get_prices(booking["barber_id"])
    client_text = texts["book_confirmed_client"].format(
        barber_name=barber["name"] if barber else "?",
        barber_phone=barber["phone"] if barber else "?",
        hour=f"{hour:02d}",
        date=booking["date"],
    )
    
    # Add extra info
    client_text += f"\n💈 {barber['salon_name']}\n"
    if price_info:
        client_text += (
            f"💇 {texts['hair_price']}: {price_info.get('hair_price', '—')}\n"
            f"🧔 {texts['beard_price']}: {price_info.get('beard_price', '—')}\n"
        )
    client_text += f"📍 <a href='https://www.google.com/maps/search/?api=1&query={barber['lat']},{barber['lon']}'>{texts['view_location']}</a>"

    # If barber has photo, send photo. Else just text.
    if barber.get("photo_file_id"):
        await ensure_flow_message(callback, client_text, state, 
                                  keyboard=client_menu_keyboard(texts), 
                                  photo=barber["photo_file_id"])
    else:
        await ensure_flow_message(callback, client_text, state, 
                                  keyboard=client_menu_keyboard(texts))

    # Notify barber (NO Done button)
    try:
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        # from app.keyboards.inline import booking_done_keyboard  <-- Removed
        b_lang = barber["lang"] if barber else "uz"
        b_texts = TEXTS_RU if b_lang == "ru" else TEXTS_UZ

        barber_msg = b_texts["book_confirmed_barber"].format(
            client_name=client["name"] if client else "?",
            client_phone=client["phone"] if client else "?",
            hour=f"{hour:02d}",
            date=booking["date"],
        )
        await bot.send_message(
            chat_id=booking["barber_id"],
            text=barber_msg,
            # reply_markup=booking_done_keyboard(booking_id, b_texts), <-- Removed
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed to notify barber {booking['barber_id']}: {e}")

    logger.info(f"Booking confirmed: id={booking_id}, client={callback.from_user.id}, barber={booking['barber_id']}")


@router.callback_query(F.data.startswith("cbook:cancel_ask:"))
async def on_cancel_ask(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    booking = await booking_service.get_booking(booking_id)
    
    if not booking:
        await callback.answer(texts["error_generic"], show_alert=True)
        return

    # Check 1-hour rule
    if booking["status"] == "CONFIRMED":
        remaining = seconds_until_slot(booking["date"], booking["hour_slot"])
        if remaining < 3600:
            await booking_service.add_penalty(
                callback.from_user.id, 
                booking["date"], 
                f"Attempted cancel at {remaining}s before slot"
            )
            await callback.answer(texts["cancel_too_late"], show_alert=True)
            return

    # Ask confirmation
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_yes_cancel"], callback_data=f"cbook:cancel_confirm:{booking_id}")],
        [InlineKeyboardButton(text=texts["btn_no_keep"], callback_data="cmenu:search")] # Retries search -> enters block -> shows menu
    ])
    await ensure_flow_message(callback, texts["prompt_cancel_booking"], state, keyboard=kb)


@router.callback_query(F.data.startswith("cbook:cancel_confirm:"))
async def on_cancel_confirm(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    booking_id = int(callback.data.split(":")[2])
    # Re-check status and time (race condition)
    booking = await booking_service.get_booking(booking_id)
    if not booking:
         await callback.answer(texts["error_generic"])
         return
         
    if booking["status"] == "CONFIRMED":
        remaining = seconds_until_slot(booking["date"], booking["hour_slot"])
        if remaining < 3600:
            await callback.answer(texts["cancel_too_late"], show_alert=True)
            # Return to block screen
            await client_search_start(callback, state, texts) 
            return

    await booking_service.cancel_booking(booking_id)
    
    # Notify barber
    try:
        from app.i18n.uz import TEXTS_UZ
        from app.i18n.ru import TEXTS_RU
        barber = await barber_service.get_barber(booking["barber_id"])
        b_lang = barber["lang"] if barber else "uz"
        b_texts = TEXTS_RU if b_lang == "ru" else TEXTS_UZ
        
        # We need a proper message for cancellation notification
        # "book_cancelled" text is generic "Bron bekor qilindi".
        # Let's send it.
        await bot.send_message(
            chat_id=booking["barber_id"],
            text=b_texts["book_cancelled"], 
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed to notify barber on cancel: {e}")

    await send_ok_popup(callback, texts["cancel_success_msg"])
    # Return to menu
    await ensure_flow_message(callback, texts["client_menu_title"], state,
                               keyboard=client_menu_keyboard(texts))


@router.callback_query(F.data.startswith("cbook:cancel:"))
async def on_booking_cancel(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    # This was the OLD cancellation handler (likely from draft or other flows).
    # We keep it for draft cancellation or compatibility, but the blocking flow uses cancel_ask.
    booking_id = int(callback.data.split(":")[2])
    booking = await booking_service.get_booking(booking_id)

    if booking and booking["status"] == "DRAFT":
        await booking_service.expire_booking(booking_id)
    elif booking and booking["status"] == "CONFIRMED":
        # Check 1-hour rule
        remaining = seconds_until_slot(booking["date"], booking["hour_slot"])
        if remaining < 3600:
            await callback.answer(texts["cancel_too_late"], show_alert=True)
            return
        await booking_service.cancel_booking(booking_id)
        # Notify barber
        try:
            from app.i18n.uz import TEXTS_UZ
            from app.i18n.ru import TEXTS_RU
            barber = await barber_service.get_barber(booking["barber_id"])
            b_lang = barber["lang"] if barber else "uz"
            b_texts = TEXTS_RU if b_lang == "ru" else TEXTS_UZ
            await bot.send_message(
                chat_id=booking["barber_id"],
                text=b_texts["book_cancelled"],
                parse_mode="HTML",
            )
        except Exception:
            pass

    await send_ok_popup(callback, texts["book_cancelled"])
    await ensure_flow_message(callback, texts["client_menu_title"], state,
                               keyboard=client_menu_keyboard(texts))


# ═══════════════════════════════════════════
# Top Rated
# ═══════════════════════════════════════════

@router.callback_query(F.data == "cmenu:top_rated")
async def top_rated_start(callback: CallbackQuery, state: FSMContext, texts: dict, **kwargs):
    if await enforce_referral_lock(callback, state, texts):
        return

    # Check unrated
    unrated = await booking_service.get_client_unrated_done(callback.from_user.id)
    if unrated:
        from app.keyboards.inline import unrated_booking_keyboard
        kb = unrated_booking_keyboard(unrated["id"], texts)
        await ensure_flow_message(callback, texts["rate_before_book"], state, keyboard=kb)
        return

    # 1. Check for Active Booking
    active_booking = await booking_service.get_client_active_booking(callback.from_user.id)
    if active_booking:
        text = texts["active_booking_block_msg"]
        booking_id = active_booking["id"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts["btn_view_active_booking"], callback_data="cmenu:active_orders")],
            [InlineKeyboardButton(text=texts["cancel"], callback_data=f"cbook:cancel_ask:{booking_id}")],
            [back_button("cmenu", texts)]
        ])
        await ensure_flow_message(callback, text, state, keyboard=kb)
        return

    # 2. Check for ANY Usage Today (Strict Limit)
    from app.utils.time_utils import today_tashkent
    today = today_tashkent()
    usage = await booking_service.get_client_today_usage(callback.from_user.id, today)
    if usage:
        text = texts["done_booking_block_msg"]
        kb = InlineKeyboardMarkup(inline_keyboard=[[back_button("cmenu", texts)]])
        await ensure_flow_message(callback, text, state, keyboard=kb)
        return


    await state.set_state(ClientMenuFSM.search_region)
    await state.update_data(search_mode="top_rated")
    regions = await fetch_all("SELECT id, name_uz, name_ru FROM regions ORDER BY id")
    await ensure_flow_message(callback, texts["choose_region"], state,
                               keyboard=barber_reg_regions_keyboard(regions, 0, texts, back_callback="back:cmenu"))
