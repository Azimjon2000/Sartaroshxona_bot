import asyncio
import logging
from app.services import booking_service
from app.utils.time_utils import today_tashkent

logger = logging.getLogger("barbershop")

async def scheduler_loop():
    logger.info("Scheduler loop started")
    while True:
        try:
            # Expire drafts older than 5 minutes
            await booking_service.expire_old_drafts()

            # Phase 4: Auto-close past bookings (from yesterday and before)
            today = today_tashkent()
            await booking_service.auto_close_past_bookings(today)

            # Auto-finish active bookings (1 hour after slot)
            from app.utils.time_utils import now_tashkent
            from app.loader import bot
            from app.keyboards.inline import rating_stars_keyboard
            from app.services import client_service, barber_service
            
            now = now_tashkent()
            
            # Phase 10: Premium Auto-Expiry
            try:
                await barber_service.auto_expire_premium(today)
            except Exception as e:
                logger.error(f"Failed to auto-expire premium: {e}")

            # Phase 10: Premium Auto-Reminders
            try:
                await booking_service.send_premium_reminders(today, now, bot)
            except Exception as e:
                logger.error(f"Failed to send premium reminders: {e}")

            # P1 Extension: Automated Daily Reminders (at 10:00 AM)
            if now.hour == 10 and now.minute == 0:
                try:
                    from app.services import reminder_service
                    await reminder_service.run_daily_auto_reminders(bot)
                except Exception as e:
                    logger.error(f"Failed to run daily auto-reminders: {e}")
                
            to_finish = await booking_service.get_confirmed_bookings_to_finish(today, now.hour)
            
            for b in to_finish:
                try:
                    await booking_service.mark_booking_done(b["id"])
                    
                    # Notify client for rating
                    client_id = b["client_id"]
                    barber = await barber_service.get_barber(b["barber_id"])
                    client = await client_service.get_client(client_id)
                    
                    if client and barber:
                        lang = client.get("lang", "uz")
                        from app.i18n.uz import TEXTS_UZ
                        from app.i18n.ru import TEXTS_RU
                        texts = TEXTS_RU if lang == "ru" else TEXTS_UZ
                        
                        prompt = texts["rate_barber_prompt"].format(barber_name=barber["name"])
                        await bot.send_message(
                            chat_id=client_id,
                            text=prompt,
                            reply_markup=rating_stars_keyboard(b["id"]),
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.error(f"Failed to auto-finish booking {b['id']}: {e}")

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(60)  # Check every minute


async def start_scheduler():
    asyncio.create_task(scheduler_loop())
