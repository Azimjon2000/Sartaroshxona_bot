from typing import List, Dict
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def main_menu_reply_keyboard(texts: Dict) -> ReplyKeyboardMarkup:
    """Reply keyboard with only 'Asosiy menyu' button."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts["main_menu"])]],
        resize_keyboard=True,
        is_persistent=True,
    )


def phone_request_keyboard(texts: Dict) -> ReplyKeyboardMarkup:
    """Reply keyboard with contact share button and Main Menu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["share_phone_btn"], request_contact=True)],
            [KeyboardButton(text=texts["main_menu"])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_request_keyboard(texts: Dict) -> ReplyKeyboardMarkup:
    """Reply keyboard with location share button and Main Menu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["share_location_btn"], request_location=True)],
            [KeyboardButton(text=texts["main_menu"])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )



def region_reply_keyboard(names: List[str], texts: Dict) -> ReplyKeyboardMarkup:
    """Dynamic 2-column keyboard for regions."""
    keyboard = []
    row = []
    for name in names:
        row.append(KeyboardButton(text=name))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Navigation
    keyboard.append([KeyboardButton(text=texts["main_menu"])])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def district_reply_keyboard(names: List[str], texts: Dict) -> ReplyKeyboardMarkup:
    """Dynamic 2-column keyboard for districts."""
    keyboard = []
    row = []
    for name in names:
        row.append(KeyboardButton(text=name))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Navigation: Back and Main Menu
    keyboard.append([
        KeyboardButton(text=texts["back"]),
        KeyboardButton(text=texts["main_menu"])
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_reply_keyboard(texts: Dict) -> ReplyKeyboardMarkup:
    """Confirm/Cancel reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts["confirm"]), KeyboardButton(text=texts["cancel"])],
            [KeyboardButton(text=texts["main_menu"])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
