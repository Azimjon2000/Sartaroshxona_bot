TEXTS_RU = {
    # --- Common ---
    "choose_role": "👋 Добро пожаловать!\n\nВыберите роль:",
    "btn_client": "👤 Клиент",
    "btn_barber": "💈 Барбер",
    "main_menu": "🏠 Главное меню",
    "ok": "OK",
    "back": "◀️ Назад",
    "cancel": "❌ Отмена",
    "confirm": "✅ Подтвердить",
    "next_page": "▶️",
    "prev_page": "◀️",
    "rate_limit": "⏳ Пожалуйста, подождите…",
    "error_generic": "⚠️ Произошла ошибка. Попробуйте снова.",
    "access_denied": "⛔ Доступ запрещён",
    "deleted_user_restart": "Вы удалены из системы. Нажмите /start заново.",
    "users_count": "👥 Количество пользователей: {count}",
    "support_text": "📞 Поддержка: {username}",

    # --- Barber Registration ---
    "enter_name": "✍️ Введите ваше имя:",
    "share_phone": "📱 Отправьте номер телефона:",
    "share_phone_btn": "📱 Отправить номер",
    "choose_region": "🏙 Выберите область:",
    "choose_district": "🏘 Выберите район:",
    "enter_salon_name": "💈 Введите название салона:",
    "send_salon_photo": "📸 Отправьте фото салона:",
    "share_location": "📍 Отправьте локацию:",
    "share_location_btn": "📍 Отправить локацию",
    "confirm_registration": (
        "📋 <b>Данные регистрации:</b>\n\n"
        "👤 Имя: {name}\n"
        "📱 Телефон: {phone}\n"
        "🏙 Область: {region}\n"
        "🏘 Район: {district}\n"
        "💈 Салон: {salon_name}\n\n"
        "Подтверждаете?"
    ),
    "reg_sent_pending": "✅ Заявка отправлена!\nОжидайте подтверждения админа.",
    "wait_approval": "⏳ Ваша заявка рассматривается. Ожидайте подтверждения.",
    "admin_new_barber": (
        "🆕 <b>Новая заявка барбера:</b>\n\n"
        "👤 Имя: {name}\n"
        "📱 Телефон: {phone}\n"
        "🏙 Область: {region}\n"
        "🏘 Район: {district}\n"
        "💈 Салон: {salon_name}"
    ),
    "barber_blocked_msg": "🚫 Ваш профиль заблокирован.",
    "barber_approved_msg": "✅ Ваш профиль подтверждён! Нажмите /start для меню.",
    "invalid_phone": "❌ Неверный номер. Формат: +998XXXXXXXXX.",
    "edit_field_prompt": "✏️ Какое поле изменить?",

    # --- Barber Menu ---
    "barber_menu_title": "💈 <b>Меню барбера</b>",
    "btn_schedule": "📅 Расписание",
    "btn_bookings": "💺 Записи",
    "btn_prices": "💰 Цены",
    "btn_settings": "⚙️ Настройки",
    "btn_work_photos": "📸 Фото работ",
    "btn_work_videos": "🎬 Видео работ",
    "btn_my_rating": "⭐ Мой рейтинг",
    "btn_users_count": "👥 Кол-во пользователей",
    "btn_served_count": "✅ Обслуженные клиенты",
    "btn_support": "📞 Поддержка",
    "btn_about": "ℹ️ О боте",
    "schedule_title": "📅 <b>Расписание</b>\n\n✅ — включено, ◻️ — выключено\nНажмите для переключения:",
    "schedule_slot_booked": "💺 {hour}:00 (запись есть)",
    "barber_booking_detail": (
        "💺 <b>Запись:</b>\n\n"
        "👤 Клиент: {client_name}\n"
        "📱 Телефон: {client_phone}\n"
        "🕐 Время: {hour}\n"
        "📅 Дата: {date}"
    ),
    "no_booking_for_slot": "На это время записей нет.",
    "bookings_today_title": "💺 <b>Записи на сегодня</b> ({date})",
    "no_bookings_today": "Сегодня записей нет.",
    "booking_already_done": "Эта запись уже завершена.",
    "booking_done_popup": "✅ Услуга отмечена как выполненная!",
    "bajarildi_btn": "✅ Выполнено",
    "rate_barber_prompt": "✅ Оцените услугу <b>{barber_name}</b>:",
    "prices_view": (
        "💰 <b>Цены</b>\n\n"
        "💇 Стрижка: {hair} сум\n"
        "🧔 Борода: {beard} сум\n"
        "🤵 Жених: {groom} сум\n"
        "📝 Описание: {note}"
    ),
    "prices_not_set": "Цены ещё не указаны.",
    "btn_edit_prices": "✏️ Редактировать цены",
    "enter_hair_price": "💇 Введите цену стрижки (только число):",
    "enter_beard_price": "🧔 Введите цену бороды (только число):",
    "enter_groom_price": "🤵 Введите цену стрижки жениха (только число):",
    "enter_extra_note": "📝 Доп. описание услуги (макс 300 символов):",
    "prices_saved": "✅ Цены сохранены!",
    "price_invalid": "❌ Введите только число.",
    "hair_price_set": "💇 Цена на стрижку установлена.",
    "beard_price_set": "🧔 Цена на бороду установлена.",
    "groom_price_set": "🤵 Цена на стрижку жениха установлена.",
    "settings_saved": "✅ Настройки сохранены!",
    "barber_settings_title": "⚙️ <b>Настройки</b>",
    "enter_new_name": "✍️ Введите новое имя:",
    "enter_new_phone": "📱 Отправьте новый номер:",
    "send_new_location": "📍 Отправьте новую локацию:",
    "send_new_photo": "📸 Отправьте новое фото:",
    "lang_changed": "✅ Язык изменён!",
    "btn_lang": "🌐 Сменить язык",
    "choose_lang": "🌐 Выберите язык:",
    "send_work_photo": "📸 Отправьте фото работы:",
    "send_work_video": "🎬 Отправьте видео работы:",
    "no_work_photos": "📸 Фото пока нет.",
    "no_work_videos": "🎬 Видео пока нет.",
    "work_photos_title": "📸 <b>Фото работ</b>",
    "work_videos_title": "🎬 <b>Видео работ</b>",
    "photo_added": "✅ Фото добавлено!",
    "video_added": "✅ Видео добавлено!",
    "photo_deleted": "🗑 Фото удалено!",
    "video_deleted": "🗑 Видео удалено!",
    "max_media_reached": "❌ Максимум 10. Сначала удалите старое.",
    "btn_add_photo": "📸 Добавить фото",
    "btn_add_video": "🎬 Добавить видео",
    "btn_delete": "🗑 Удалить",
    "my_rating_title": "⭐ <b>Мой рейтинг</b>\n\n{stars} Среднее: {avg}/5 ({count} оценок)",
    "comments_header": "💬 <b>Отзывы:</b>",
    "total_users": "👥 Количество пользователей: {count}",
    "served_clients": "✅ Обслуженных клиентов: {count}",
    "support_contact": "📞 Поддержка: {username}",
    "about_barber": (
        "ℹ️ <b>О боте</b>\n\n"
        "Этот бот связывает барберов и клиентов.\n"
        "Настройте расписание, цены и принимайте клиентов!"
    ),

    # --- Client ---
    "client_menu_title": "👤 <b>Меню клиента</b>",
    "btn_search": "🔍 Найти ближайшего барбера",
    "btn_active_orders": "📅 Мои активные заказы",
    "btn_top_rated": "🏆 Лучшие по рейтингу",
    "btn_client_settings": "⚙️ Настройки",
    "send_location_btn": "📍 Отправить локацию",
    "manual_search_btn": "🔎 Поиск вручную",
    "search_method": "🔍 Выберите метод поиска:",
    "choose_radius": "📏 Выберите радиус:",
    "select_action": "Выберите действие:",
    "no_active_orders": "🤷‍♂️ Нет активных заказов.",
    "active_order_title": "Активный заказ:",
    "view_location": "Посмотреть локацию",
    "hair_price": "Стрижка",
    "beard_price": "Борода",
    "barber_list_title": "💈 <b>Барберы</b> ({count}):",
    "no_barbers_found": "😕 Барберы не найдены.",
    "barber_card_text": (
        "💈 <b>{name}</b> — {salon_name}\n"
        "⭐ {rating} ({served} клиентов)\n"
        "📞 {phone}\n\n"
        "💇 Стрижка: {hair_price} сум\n"
        "🧔 Борода: {beard_price} сум\n"
        "🤵 Жених: {groom_price} сум\n"
        "{extra_note}"
    ),
    "btn_book": "📅 Выбрать время записи",
    "btn_view_location": "📍 Посмотреть локацию",
    "btn_view_photos": "📸 Фото",
    "btn_view_videos": "🎬 Видео",
    "btn_view_reviews": "💬 Отзывы клиентов",
    "book_choose_slot": "📅 <b>Выберите время:</b>\n\n✅ — свободно, ❌ — занято",
    "no_available_slots": "😕 Сегодня нет свободного времени.",
    "book_confirm_text": (
        "📅 <b>Подтвердить запись?</b>\n\n"
        "💈 Барбер: {barber_name}\n"
        "🕐 Время: {hour}:00\n"
        "📅 Дата: {date}"
    ),
    "book_confirmed_client": (
        "✅ <b>Запись подтверждена!</b>\n\n"
        "💈 Барбер: {barber_name}\n"
        "📞 Телефон: {barber_phone}\n"
        "🕐 Время: {hour}:00\n"
        "📅 Дата: {date}"
    ),
    "book_confirmed_barber": (
        "🆕 <b>Новая запись!</b>\n\n"
        "👤 Клиент: {client_name}\n"
        "📞 Телефон: {client_phone}\n"
        "🕐 Время: {hour}:00\n"
        "📅 Дата: {date}"
    ),
    "book_cancelled": "❌ Запись отменена.",
    "book_slot_taken": "❌ Это время уже занято другим клиентом.",
    "book_draft_expired": "⏳ Время бронирования истекло (4 минуты). Выберите заново.",
    "cancel_too_late": "❌ Отмена невозможна! До записи менее 1 часа.",
    "cancel_penalty_text": "⚠️ Повторная запись недоступна до 23:59 сегодня.",
    "rate_before_book": "⚠️ Сначала оцените предыдущую услугу!",
    "top_rated_title": "🏆 <b>Лучшие по рейтингу</b>",
    "client_settings_title": "⚙️ <b>Настройки</b>",
    "client_name_updated": "✅ Имя обновлено!",
    "client_phone_updated": "✅ Телефон обновлён!",
    "client_lang_changed": "✅ Язык изменён!",
    "client_about": (
        "ℹ️ <b>О боте</b>\n\n"
        "С помощью этого бота найдите ближайших барберов,\n"
        "запишитесь и оцените качество услуги!"
    ),
    "barber_location_sent": "📍 Локация барбера:",
    "reviews_title": "💬 <b>Отзывы клиентов</b>",
    "no_reviews": "Отзывов пока нет.",

    # --- Rating ---
    "rate_prompt": "⭐ Оцените услугу (1-5):",
    "rate_comment_prompt": "💬 Оставьте отзыв (макс 300 символов)\n\nИли нажмите «Пропустить»:",
    "rate_skip_btn": "⏭ Пропустить",
    "rate_comment_saved": "✅ Ваш отзыв сохранён! Спасибо!",
    "rate_thank_you": "✅ Ваша оценка сохранена! Спасибо!",

    # --- Admin ---
    "admin_menu_title": "🔐 <b>Панель администратора</b>",
    "btn_admin_barbers": "💈 Барберы",
    "btn_admin_stats": "📊 Статистика",
    "btn_admin_add": "➕ Добавить админа",
    "btn_admin_broadcast": "📢 Рассылка",
    "btn_admin_delete_user": "🗑 Удалить пользователя",
    "btn_admin_support": "📞 Настроить поддержку",
    "admin_barbers_title": "💈 <b>Список барберов</b>",
    "admin_barber_card": (
        "💈 <b>{name}</b>\n"
        "📱 {phone}\n"
        "🏙 {region} / {district}\n"
        "💈 {salon_name}\n"
        "📊 Статус: {status}"
    ),
    "btn_approve": "✅ Подтвердить",
    "btn_block": "🚫 Заблокировать",
    "btn_unblock": "✅ Разблокировать",
    "btn_hard_delete": "🗑 Удалить",
    "admin_approve_ok": "✅ Барбер подтверждён!",
    "admin_block_ok": "🚫 Барбер заблокирован!",
    "admin_unblock_ok": "✅ Барбер разблокирован!",
    "admin_delete_ok": "🗑 Барбер удалён!",
    "admin_stats_text": (
        "📊 <b>Статистика</b>\n\n"
        "👥 Всего пользователей: {total}\n"
        "💈 Барберов: {barbers}\n"
        "👤 Клиентов: {clients}"
    ),
    "admin_add_admin_prompt": "👤 Введите Telegram ID нового админа:",
    "admin_added_ok": "✅ Админ добавлен!",
    "admin_broadcast_choose": "📢 Кому отправить?",
    "btn_bc_all": "👥 Всем",
    "btn_bc_barbers": "💈 Только барберам",
    "btn_bc_clients": "👤 Только клиентам",
    "admin_broadcast_send": "📝 Отправьте текст сообщения (медиа + текст):",
    "admin_broadcast_done": "✅ Рассылка завершена!\n\n📨 Отправлено: {sent}\n❌ Ошибки: {failed}",
    "admin_delete_user_prompt": "🗑 Введите Telegram ID пользователя для удаления:",
    "admin_user_deleted": "🗑 Пользователь удалён!",
    "admin_user_not_found": "❌ Пользователь не найден.",
    "admin_support_prompt": "📞 Введите новый username поддержки (с @):",
    "admin_support_updated": "✅ Username поддержки обновлён!",
    "admin_no_barbers": "💈 Барберов нет.",
    "btn_send_message": "✉️ Отправить сообщение",
    "admin_msg_barber_prompt": "📝 Введите сообщение для барбера:",
    "admin_msg_sent_ok": "✅ Сообщение отправлено!",

    # --- Phase 12: Restricted Booking ---
    "active_booking_block_msg": "🚫 У вас есть активная бронь. Вы не можете создать новую до её завершения.",
    "done_booking_block_msg": "🚫 Вы уже пользовались услугой сегодня.\nПожалуйста, приходите завтра.",
    "btn_view_active_booking": "👁 Посмотреть бронь",

    # --- Phase 13: Cancellation from Block ---
    "prompt_cancel_booking": "⚠️ Вы действительно хотите отменить бронь?",
    "btn_yes_cancel": "✅ Да, отменить",
    "btn_no_keep": "❌ Нет, оставить",
    "cancel_success_msg": "✅ Бронь отменена.",
    "btn_cancel_booking": "❌ Отменить бронь",
    "btn_remind_client": "🔔 Напомнить",
    "confirm_cancel_barber": "⚠️ Вы действительно хотите отменить эту бронь?",
    "cancel_confirmed_barber": "✅ Бронь отменена, время освобождено.",
    "booking_cancelled_client_notify": "⚠️ <b>Ваша бронь отменена</b>\n\n💈 Барбер: {barber_name}\n📞 Телефон: {barber_phone}\n🕐 Время: {hour}:00\n📅 Дата: {date}",
    "btn_rate_now": "⭐️ Оценить сейчас",
    "reminder_client_msg": "🔔 <b>Напоминание</b>\n\nВас сегодня в {hour}:00 ожидает <b>{barber_name}</b>!",
    "remind_sent_popup": "✅ Напоминание отправлено!",
    "already_rated": "Вы уже оценили эту услугу.",
    "reminder_days_title": "🔔 Клиентам, не приходившим сколько дней, вы отправите напоминание?",
    "reminder_custom_prompt": "📝 Введите количество дней (например: 30):",
    "reminder_sending": "⏳ Отправка напоминаний... ({sent}/{total})",
    "reminder_done": "✅ Напоминание отправлено {sent} клиентам!",
    "reminder_no_clients": "😕 Клиентов для напоминания в этом интервале не найдено.",
    "reminder_text": (
        "{name}, прошло {days} дн. с вашего последнего визита.\n"
        "Хороший вид — залог хорошего настроения!\n\n"
        "{link}"
    ),
    "reminder_confirm": "⚠️ Напоминание будет отправлено {count} клиентам. Подтверждаете?",
    "auto_reminder_set": "✅ Автоматическое напоминание сохранено. Бот будет ежедневно отправлять сообщения клиентам, которые не приходили в течение этого срока.",
    "auto_reminder_info": "\n\n🔔 Текущая периодичность: <b>{days} дн.</b>",
}
