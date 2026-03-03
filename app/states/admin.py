from aiogram.fsm.state import State, StatesGroup


class AdminFSM(StatesGroup):
    menu = State()
    add_admin_id = State()
    broadcast_target = State()
    broadcast_content = State()
    delete_user_id = State()
    support_username = State()
    message_barber_content = State()
    edit_premium_price = State()
    edit_payment_card = State()
    edit_support_profile = State()
