import asyncio, os
from aiogram import types, Router, F, Bot, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from dotenv import load_dotenv, find_dotenv
import re
import pandas as pd
from typing import Callable, Dict, Any, Awaitable

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv('TOKEN_API'))

# extracts only first one number from all text (included other numbers)
def extract_number(text):
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    else:
        return None

class Recording(StatesGroup):
    user_id = State()
    name = State()
    age = State()
    weight = State()
    height = State()
    experience_running = State()
    target_distance = State()
    training_frequency = State()

reg_router = Router()

# Inline keyboard for registration
registration_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Регистрация", callback_data="start_registration")],
        [InlineKeyboardButton(text="о боте", callback_data="about")]
    ]
)
confirm_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Да",callback_data="yes")],
        [InlineKeyboardButton(text="Нет",callback_data="no")]
    ]
)

# Middleware для проверки регистрации
class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if event.data == "start_registration":
            user_id = event.from_user.id
            try:
                df = pd.read_excel("user_registration_data.xlsx")
                if user_id in df['user_id'].values:
                    await event.answer()
                    await event.message.answer("Вы уже зарегистрированы!")
                    return  # Прерываем дальнейшее выполнение
            except FileNotFoundError:
                pass  # Файл не найден, продолжаем регистрацию
        return await handler(event, data)

# Применяем middleware к роутеру
reg_router.callback_query.middleware(RegistrationMiddleware())

@reg_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Нажми кнопку для начала регистрации:", reply_markup=registration_keyboard)

@reg_router.callback_query(F.data == "about")
async def cmd_about(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("Привет, наш бот разработан для твоих кардио тренировок(бег),"
                         "данный проект поможет отслеживать твой прогресс!\n")
@reg_router.callback_query(F.data == "start_registration")
async def reg_cmd(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()

    user_id = callback_query.from_user.id
    await state.set_state(Recording.user_id)
    await state.update_data(user_id=user_id)

    async with ChatActionSender.typing(bot=bot, chat_id=callback_query.message.chat.id):
        await asyncio.sleep(2)
        await callback_query.message.answer('Привет. Напиши как тебя зовут: ')
    await state.set_state(Recording.name)

@reg_router.message(F.text, Recording.name)
async def capture_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        await asyncio.sleep(1)
        await message.answer('Супер! А теперь напиши сколько тебе полных лет: ')
    await state.set_state(Recording.age)

@reg_router.message(F.text, Recording.age)
async def capture_age(message:Message, state:FSMContext):
    check_age = extract_number(message.text)


    if not check_age or not (1 <= check_age <= 100):
        await message.reply('Пожалуйста, введите корректный возраст (число от 1 до 100).')
        return
    await state.update_data(age=check_age)

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        await asyncio.sleep(1)
        await message.answer('какой твой вес в кг?')
    await state.set_state(Recording.weight)

@reg_router.message(F.text, Recording.weight)
async def capture_weight(message:Message, state:FSMContext):
    check_weight = extract_number(message.text)

    if not check_weight or not (40 <= check_weight <= 240):
        await message.reply("пожалуйста, введите корректный вес в диапазоне от 40 до 240")
        return
    await state.update_data(weight=check_weight)

    await message.answer('какой твой рост в см?')
    await state.set_state(Recording.height)

@reg_router.message(F.text, Recording.height)
async def capture_height(message:Message, state:FSMContext):
    check_height = extract_number(message.text)

    if not check_height or not (40 <= check_height <= 300):
        await message.reply("пожалуйста, введите корректный рост в диапазоне от 40 до 300")
        return
    await state.update_data(height=check_height)

    await message.answer('какой твой опыт бега в месяцах?')
    await state.set_state(Recording.experience_running)

@reg_router.message(F.text, Recording.experience_running)
async def capture_experience_running(message:Message, state:FSMContext):
    check_experience_running = extract_number(message.text)

    if not check_experience_running:
        await message.reply("некорректный ответ, пожалуйста, введите ваш опыт бега")
        return
    await state.update_data(experience_running=check_experience_running)

    await message.answer('какую дистанцию ты хочешь преодолеть')
    await state.set_state(Recording.target_distance)

@reg_router.message(F.text, Recording.target_distance)
async def capture_target_distance(message:Message, state:FSMContext):
    check_target_distance = extract_number(message.text)

    if not check_target_distance:
        await message.reply("некорректный ответ, пожалуйста, введите вашу желаемую дистанцию")
        return
    await state.update_data(target_distance=check_target_distance)

    await message.answer('сколько тренировок ты хочешь в неделю?')
    await state.set_state(Recording.training_frequency)

@reg_router.message(F.text, Recording.training_frequency)
async def capture_training_frequency(message:Message, state:FSMContext):
    check_training_frequency = extract_number(message.text)

    if not check_training_frequency or not 0 < check_training_frequency <= 7:
        await message.reply("некорректный ответ, пожалуйста, введите:\nсколько тренировок вы хотите в неделю")
        return
    await state.update_data(training_frequency=check_training_frequency)

    data = await state.get_data()
    await message.answer(f"- вас зовут - {data.get('name')},\n"
                         f"- ваш возраст - {data.get('age')},\n"
                         f"- ваш вес - {data.get('weight')},\n"
                         f"- ваш рост - {data.get('height')},\n"
                         f"- ваша максимальная дистанция - {data.get('experience_running')},\n"
                         f"- ваша цель в км - {data.get('target_distance')},\n"
                         f"- желаемая частота тренировок в неделю - {data.get('training_frequency')}",
                         reply_markup=confirm_keyboard)

@reg_router.callback_query(F.data == "yes")
async def verification(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    try:
        df = pd.read_excel("user_registration_data.xlsx")
    except FileNotFoundError:
        df = pd.DataFrame(columns=list(data.keys()))

    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)


    df.to_excel("user_registration_data.xlsx", index=False)
    await state.clear()
    await callback_query.message.answer("Данные успешно сохранены!")

@reg_router.callback_query(F.data == "no")
async def restart_registration(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer("Регистрация начата заново.")
    await reg_cmd(callback_query, state)
