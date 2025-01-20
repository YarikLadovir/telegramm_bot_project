import asyncio, os
from aiogram import types, Router, F, Bot, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
from aiogram.utils.chat_action import ChatActionSender
from dotenv import load_dotenv, find_dotenv
import re
from typing import Callable, Dict, Any, Awaitable

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('TOKEN_API'))

# Inline keyboard for registration
registration_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Регистрация", callback_data="start_registration")],
        [InlineKeyboardButton(text="о боте", callback_data="about")]
    ]
)

# extracts only first one number from all text (included other numbers)
def extract_number(text):
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    else:
        return None

class Tracking(StatesGroup):
    user_id = State()
    distance = State()
    time = State()
    average_pace = State()
    average_pulse = State()
    burned_calories = State()
    confirmation = State()

track_router = Router()

confirm_track_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Да",callback_data="yes_track")],
        [InlineKeyboardButton(text="Нет",callback_data="no_track")]
    ]
)

# Middleware для проверки регистрации перед трекингом
class TrackingRegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.text.startswith('/tracking'):
            user_id = event.from_user.id
            try:
                df = pd.read_excel("user_registration_data.xlsx")
                if user_id not in df['user_id'].values:
                    await event.answer("Пожалуйста, сначала зарегистрируйтесь!")
                    await event.answer("Нажмите кнопку для начала регистрации:", reply_markup=registration_keyboard)
                    return  # Прерываем дальнейшее выполнение
            except FileNotFoundError:
                await event.answer("Пожалуйста, сначала зарегистрируйтесь!")
                await event.answer("Нажмите кнопку для начала регистрации:", reply_markup=registration_keyboard)
                return  # Прерываем дальнейшее выполнение
        return await handler(event, data)

# Применяем middleware к роутеру
track_router.message.middleware(TrackingRegistrationMiddleware())

@track_router.message(Command("tracking"))
async def reg_cmd(message: types.Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    await state.update_data(user_id=user_id)

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        await asyncio.sleep(2)
        await message.answer('Какую дистанцию вы пробежали (в км)?')
    await state.set_state(Tracking.distance)

@track_router.message(F.text, Tracking.distance)
async def process_distance(message: types.Message, state: FSMContext):
    distance = extract_number(message.text)
    if not distance or not 0 < distance <= 60:
        await message.reply("Пожалуйста, введите корректную дистанцию.(0-60км)")
        return

    await state.update_data(distance=distance)
    await message.answer('Сколько времени у вас ушло на преодоление этой дистанции(в минутах)?')
    await state.set_state(Tracking.time)

@track_router.message(F.text, Tracking.time)
async def process_time(message: types.Message, state: FSMContext):
    time = extract_number(message.text)
    if not time or time < 0:
        await message.reply("Пожалуйста, введите корректное время.")
        return

    await state.update_data(time=time)
    await message.answer('Какой был ваш средний темп бега(км/ч)?')
    await state.set_state(Tracking.average_pace)


@track_router.message(F.text, Tracking.average_pace)
async def process_average_pace(message: types.Message, state: FSMContext):
    pace = extract_number(message.text)
    if not pace or not 0 < pace <= 44:
        await message.reply("Пожалуйста, введите корректный средний темп.(0-44 км/ч)")
        return

    await state.update_data(pace=pace)
    await message.answer('Какой был ваш средний пульс(удары в минуту)?')
    await state.set_state(Tracking.average_pulse)

@track_router.message(F.text, Tracking.average_pulse)
async def process_average_pulse(message: types.Message, state: FSMContext):
    pulse = extract_number(message.text)
    if not pulse or not 90 < pulse <= 240:
        await message.reply("Пожалуйста, введите корректный средний пульс. (90-240)")
        return

    await state.update_data(pulse=pulse)
    await message.answer('Сколько калорий было сожжено?')
    await state.set_state(Tracking.burned_calories)

@track_router.message(F.text, Tracking.burned_calories)
async def process_burned_calories(message: types.Message, state: FSMContext):
    calories = extract_number(message.text)
    if not calories or not 0 < calories < 6000:
        await message.reply("Пожалуйста, введите корректное количество сожженных калорий (0-6000).")
        return

    await state.update_data(calories=calories)
    user_data = await state.get_data()
    await message.answer(f'Отличная работа! Вот ваши результаты:\n'
                         f'- Дистанция: {user_data["distance"]} километров\n'
                         f'- Время: {user_data["time"]} минут\n'
                         f'- Средний темп: {user_data["pace"]} км/ч\n'
                         f'- Средний пульс: {user_data["pulse"]} ударов/мин\n'
                         f'- Сожженные калории: {user_data["calories"]}\n\n'
                         f'Всё верно?',
                         reply_markup=confirm_track_keyboard)
    await state.set_state(Tracking.confirmation)

@track_router.callback_query(Tracking.confirmation, F.data == "yes_track")
async def confirm_tracking(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()

    try:
        df = pd.read_excel("user_tracking_data.xlsx")
    except FileNotFoundError:
        df = pd.DataFrame(columns=list(data.keys()))

    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)

    df.to_excel("user_tracking_data.xlsx", index=False)
    await state.clear()
    await callback_query.message.answer("Данные успешно сохранены!")

@track_router.callback_query(Tracking.confirmation, F.data == "no_track")
async def reject_tracking(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    user_id = data.get("user_id")
    await state.clear()
    await state.update_data(user_id=user_id)
    await callback_query.message.answer("Попробуем ещё раз.")

    async with ChatActionSender.typing(bot=bot, chat_id=callback_query.message.chat.id):
        await asyncio.sleep(2)
        await callback_query.message.answer('Какую дистанцию вы пробежали (в км)?')
    await state.set_state(Tracking.distance)
