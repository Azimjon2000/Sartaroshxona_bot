from typing import List, Dict, Optional, Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ── Common ──

def role_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts["btn_client"], callback_data="role:client"),
            InlineKeyboardButton(text=texts["btn_barber"], callback_data="role:barber"),
        ]
    ])


def ok_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="OK", callback_data="ok:delete")]
    ])


def back_button(target: str, texts: dict) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=texts["back"], callback_data=f"back:{target}")


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ])


# ── Barber Registration ──

def barber_reg_regions_keyboard(regions: List[Dict], page: int, texts: Dict, back_callback: Optional[str] = None) -> InlineKeyboardMarkup:
    from app.utils.pagination import paginate
    page_items, total_pages, has_prev, has_next = paginate(regions, page, page_size=20)

    rows = []
    row = []
    for r in page_items:
        row.append(InlineKeyboardButton(
            text=r["name_uz"], callback_data=f"breg:region:{r['id']}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:region:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:region:{page + 1}"))
    if nav:
        rows.append(nav)
    
    if back_callback:
        rows.append([InlineKeyboardButton(text=texts["back"], callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def barber_reg_districts_keyboard(districts: List[Dict], page: int, texts: Dict, back_callback: Optional[str] = None) -> InlineKeyboardMarkup:
    from app.utils.pagination import paginate
    page_items, total_pages, has_prev, has_next = paginate(districts, page, page_size=20)

    rows = []
    row = []
    for d in page_items:
        row.append(InlineKeyboardButton(
            text=d["name_uz"], callback_data=f"breg:district:{d['id']}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:district:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:district:{page + 1}"))
    if nav:
        rows.append(nav)

    if back_callback:
        rows.append([InlineKeyboardButton(text=texts["back"], callback_data=back_callback)])
    else:
        rows.append([back_button("breg_region", texts)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def barber_reg_confirm_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts["confirm"], callback_data="breg:confirm"),
            InlineKeyboardButton(text=texts["cancel"], callback_data="breg:cancel"),
        ],
        [InlineKeyboardButton(text=texts["edit_field_prompt"], callback_data="breg:edit_menu")],
    ])


def barber_reg_edit_keyboard(texts: dict) -> InlineKeyboardMarkup:
    fields = [
        ("👤 Ism", "breg:edit:name"),
        ("📱 Telefon", "breg:edit:phone"),
        ("🏙 Viloyat", "breg:edit:region"),
        ("💈 Salon", "breg:edit:salon_name"),
        ("📸 Rasm", "breg:edit:photo"),
        ("📍 Lokatsiya", "breg:edit:location"),
    ]
    rows = [[InlineKeyboardButton(text=t, callback_data=d)] for t, d in fields]
    rows.append([back_button("breg_confirm", texts)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Admin ──

def admin_menu_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_admin_barbers"], callback_data="adm:barbers")],
        [InlineKeyboardButton(text=texts["btn_admin_stats"], callback_data="adm:stats")],
        [InlineKeyboardButton(text=texts["btn_admin_add"], callback_data="adm:add_admin")],
        [InlineKeyboardButton(text=texts["btn_admin_broadcast"], callback_data="adm:broadcast")],
        [InlineKeyboardButton(text=texts["btn_admin_delete_user"], callback_data="adm:delete_user")],
        [InlineKeyboardButton(text=texts["btn_admin_support"], callback_data="adm:support")],
    ])


def admin_barber_actions_keyboard(barber_id: int, status: str, texts: dict) -> InlineKeyboardMarkup:
    rows = []
    if status == "PENDING":
        rows.append([InlineKeyboardButton(text=texts["btn_approve"], callback_data=f"admb:approve:{barber_id}")])
    if status != "BLOCKED":
        rows.append([InlineKeyboardButton(text=texts["btn_block"], callback_data=f"admb:block:{barber_id}")])
    else:
        rows.append([InlineKeyboardButton(text=texts["btn_unblock"], callback_data=f"admb:unblock:{barber_id}")])
    rows.append([InlineKeyboardButton(text=texts["btn_hard_delete"], callback_data=f"admb:delete:{barber_id}")])
    rows.append([InlineKeyboardButton(text=texts["btn_send_message"], callback_data=f"admb:msg:{barber_id}")])
    rows.append([back_button("adm_barbers", texts)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_barber_approve_keyboard(barber_id: int, texts: dict) -> InlineKeyboardMarkup:
    """Keyboard sent to admins when new barber registers."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts["btn_approve"], callback_data=f"admb:approve:{barber_id}"),
            InlineKeyboardButton(text=texts["btn_block"], callback_data=f"admb:block:{barber_id}"),
        ]
    ])


def broadcast_target_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_bc_all"], callback_data="adm:bc_target:all")],
        [InlineKeyboardButton(text=texts["btn_bc_barbers"], callback_data="adm:bc_target:barbers")],
        [InlineKeyboardButton(text=texts["btn_bc_clients"], callback_data="adm:bc_target:clients")],
        [back_button("adm_menu", texts)],
    ])


# ── Barber Menu ──

def barber_menu_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_schedule"], callback_data="bmenu:schedule")],
        [InlineKeyboardButton(text=texts["btn_bookings"], callback_data="bmenu:bookings")],
        [InlineKeyboardButton(text=texts["btn_prices"], callback_data="bmenu:prices")],
        [InlineKeyboardButton(text=texts["btn_settings"], callback_data="bmenu:settings")],
        [InlineKeyboardButton(text=texts["btn_work_photos"], callback_data="bmenu:photos")],
        [InlineKeyboardButton(text=texts["btn_work_videos"], callback_data="bmenu:videos")],
        [InlineKeyboardButton(text=texts["btn_my_rating"], callback_data="bmenu:rating")],
        [
            InlineKeyboardButton(text=texts["btn_users_count"], callback_data="bmenu:users_count"),
            InlineKeyboardButton(text=texts["btn_served_count"], callback_data="bmenu:served_count"),
        ],
        [InlineKeyboardButton(text=texts["btn_support"], callback_data="bmenu:support")],
        [InlineKeyboardButton(text=texts["btn_about"], callback_data="bmenu:about")],
    ])


def barber_settings_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Ism", callback_data="bset:name")],
        [InlineKeyboardButton(text="📱 Telefon", callback_data="bset:phone")],
        [InlineKeyboardButton(text="📍 Lokatsiya", callback_data="bset:location")],
        [InlineKeyboardButton(text="📸 Rasm", callback_data="bset:photo")],
        [InlineKeyboardButton(text=texts["btn_lang"], callback_data="bset:lang")],
        [back_button("bmenu", texts)],
    ])


def schedule_keyboard(slots: List[Dict], texts: Dict) -> InlineKeyboardMarkup:
    """4x4 grid of hour toggles."""
    from app.utils.time_utils import slot_to_hour
    rows = []
    for row_start in range(0, 16, 4):
        row = []
        for i in range(row_start, min(row_start + 4, 16)):
            slot = slots[i] if i < len(slots) else {"hour_slot": i, "is_enabled": 0, "booked": False}
            hour = slot_to_hour(slot["hour_slot"])
            if slot.get("booked"):
                label = f"💺 {hour:02d}:00"
                cb = f"bbron:{slot['hour_slot']}"
            elif slot["is_enabled"]:
                label = f"✅ {hour:02d}:00"
                cb = f"bsched:{slot['hour_slot']}"
            else:
                label = f"◻️ {hour:02d}:00"
                cb = f"bsched:{slot['hour_slot']}"
            row.append(InlineKeyboardButton(text=label, callback_data=cb))
        rows.append(row)
    rows.append([back_button("bmenu", texts)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def media_gallery_keyboard(
    current_idx: int, total: int, media_id: int,
    media_type: str, texts: dict
) -> InlineKeyboardMarkup:
    """Navigation for photo/video gallery: prev/next/delete."""
    prefix = "bphoto" if media_type == "photo" else "bvideo"
    nav = []
    if current_idx > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:prev:{current_idx - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_idx + 1}/{total}", callback_data="noop"))
    if current_idx < total - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:next:{current_idx + 1}"))

    rows = [nav]
    rows.append([InlineKeyboardButton(text=texts["btn_delete"], callback_data=f"{prefix}:del:{media_id}")])
    rows.append([back_button("bmenu", texts)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Client Menu ──

def client_menu_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_search"], callback_data="cmenu:search")],
        # "Active Orders" button removed as per Phase 12
        [InlineKeyboardButton(text=texts["btn_top_rated"], callback_data="cmenu:top_rated")],
        [InlineKeyboardButton(text=texts["btn_client_settings"], callback_data="cmenu:settings")],
        [InlineKeyboardButton(text=texts["btn_users_count"], callback_data="cmenu:users_count")],
        [InlineKeyboardButton(text=texts["btn_support"], callback_data="cmenu:support")],
        [InlineKeyboardButton(text=texts["btn_about"], callback_data="cmenu:about")],
    ])


def client_settings_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Ism", callback_data="cset:name")],
        [InlineKeyboardButton(text="📱 Telefon", callback_data="cset:phone")],
        [InlineKeyboardButton(text=texts["btn_lang"], callback_data="cset:lang")],
        [back_button("cmenu", texts)],
    ])


def search_method_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["send_location_btn"], callback_data="csearch:location")],
        [InlineKeyboardButton(text=texts["manual_search_btn"], callback_data="csearch:manual")],
        [back_button("cmenu", texts)],
    ])


def radius_keyboard(texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 km", callback_data="csearch:radius:5"),
            InlineKeyboardButton(text="10 km", callback_data="csearch:radius:10"),
            InlineKeyboardButton(text="15 km", callback_data="csearch:radius:15"),
        ],
        [back_button("csearch", texts)],
    ])


def barber_card_keyboard(barber_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_book"], callback_data=f"cbarber:book:{barber_id}")],
        [InlineKeyboardButton(text=texts["btn_view_location"], callback_data=f"cbarber:location:{barber_id}")],
        [
            InlineKeyboardButton(text=texts["btn_view_photos"], callback_data=f"cbarber:photos:{barber_id}"),
            InlineKeyboardButton(text=texts["btn_view_videos"], callback_data=f"cbarber:videos:{barber_id}"),
        ],
        [InlineKeyboardButton(text=texts["btn_view_reviews"], callback_data=f"cbarber:reviews:{barber_id}")],
        [back_button("csearch_list", texts)],
    ])


def booking_slots_keyboard(
    slots: List[Dict], barber_id: int, texts: Dict
) -> InlineKeyboardMarkup:
    """Grid of available hour slots for booking."""
    from app.utils.time_utils import slot_to_hour
    rows = []
    for row_start in range(0, len(slots), 4):
        row = []
        for slot in slots[row_start:row_start + 4]:
            hour = slot_to_hour(slot["hour_slot"])
            if slot.get("booked"):
                label = f"❌ {hour:02d}:00"
                cb = "noop"
            else:
                label = f"✅ {hour:02d}:00"
                cb = f"cbook:slot:{slot['hour_slot']}"
            row.append(InlineKeyboardButton(text=label, callback_data=cb))
        rows.append(row)
    rows.append([back_button(f"cbarber:{barber_id}", texts)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def booking_confirm_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts["confirm"], callback_data=f"cbook:confirm:{booking_id}"),
            InlineKeyboardButton(text=texts["cancel"], callback_data=f"cbook:cancel:{booking_id}"),
        ]
    ])


def booking_done_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    """For barber: 'Bajarildi' button under booking notification."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["bajarildi_btn"], callback_data=f"bbron:done:{booking_id}")]
    ])


# ── Rating ──

def rating_stars_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    stars = []
    for i in range(1, 6):
        stars.append(InlineKeyboardButton(
            text="⭐" * i, callback_data=f"crate:{i}:{booking_id}"
        ))
    # 2 rows: 1-3, 4-5
    return InlineKeyboardMarkup(inline_keyboard=[
        stars[:3],
        stars[3:],
    ])


def rating_comment_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["rate_skip_btn"], callback_data=f"ccomment:skip:{booking_id}")]
    ])


# ── Phase 8: Barber Booking Management & Improved Rating ──

def barber_booking_actions_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["bajarildi_btn"], callback_data=f"bbron:done:{booking_id}")],
        [
            InlineKeyboardButton(text=texts["btn_cancel_booking"], callback_data=f"bbron:cancel_ask:{booking_id}"),
            InlineKeyboardButton(text=texts["btn_remind_client"], callback_data=f"bbron:remind:{booking_id}")
        ],
        [back_button("bmenu:schedule", texts)]
    ])


def barber_confirm_cancel_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts["confirm"], callback_data=f"bbron:cancel_confirm:{booking_id}"),
            InlineKeyboardButton(text=texts["cancel"], callback_data=f"bbron:{booking_id}") # Return to detail
        ]
    ])


def unrated_booking_keyboard(booking_id: int, texts: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["btn_rate_now"], callback_data=f"crate:start:{booking_id}")],
        [back_button("cmenu", texts)]
    ])
