from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command
import datetime

scheduler = AsyncIOScheduler()

# Роутер для напоминаний
reminder_router = Router()

REMINDER_TEXT = "Вы не забыли про тренировку?)"

async def send_reminder(bot: Bot, chat_id: int):
    try:
        await bot.send_message(chat_id=chat_id, text=REMINDER_TEXT)
        print(f"Reminder sent to chat {chat_id}")
    except Exception as e:
        print(f"Error sending reminder: {e}")


def set_interval_reminder(bot: Bot, chat_id: int):
    existing_job = scheduler.get_job(str(chat_id))
    if existing_job:
        print(f"Reminder already exists for chat {chat_id}")
        return

    scheduler.add_job(
        send_reminder,
        'interval',
        minutes=5,
        args=[bot, chat_id],
        id=str(chat_id)
    )
    print(f"Reminder set for chat {chat_id} every 5 minutes")


def stop_interval_reminder(chat_id: int):
    try:
        scheduler.remove_job(str(chat_id))
        print(f"Reminder stopped for chat {chat_id}")
    except Exception as e:
        print(f"Error stopping reminder: {e}")

@reminder_router.message(Command("start_reminders"))
async def command_start_reminder(message: Message, bot: Bot):
    set_interval_reminder(bot, message.chat.id)
    await message.answer("Напоминания включены! Каждые 5 минут я буду спрашивать, не забыли ли вы про тренировку.")

@reminder_router.message(Command("stop_reminders"))
async def command_stop_reminder(message: Message):
    stop_interval_reminder(message.chat.id)
    await message.answer("Напоминания отключены!")


# Запуск APScheduler (должен быть перед bot.infinity_polling())
async def start_scheduler():
    scheduler.start()
    print("Scheduler started.")