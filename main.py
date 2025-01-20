import os, asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv, find_dotenv
from handlers.private import private_router
from common.bot_cmd_list import private
from FSM.registration import reg_router
from FSM.tracking import track_router
from handlers.gpt_train import gpt_speaking_router
from handlers.reminder import reminder_router, start_scheduler
load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('TOKEN_API'))
dp = Dispatcher()

dp.include_router(private_router)
dp.include_router(reg_router)
dp.include_router(track_router)
dp.include_router(reminder_router)
dp.include_router(gpt_speaking_router)

ALLOWED_UPDATES = ["message", "edited_message", "callback_query"]


# Запуск бота
async def main()->None:
    await start_scheduler()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)

asyncio.run(main())