import os
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from langchain_gigachat import GigaChat
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from langchain_core.runnables import RunnablePassthrough
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, callback_query
from typing import Dict
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

# Загрузка переменных окружения
load_dotenv(find_dotenv())

class KindTraining(StatesGroup):
    training = State()

# Константы
GIGACHAT_API = os.getenv('ACCESS_TOKEN')
EXCEL_FILE = "user_data.xlsx"
MEMORY_COLUMN = "memory"
USER_ID_COLUMN = "user_id"

# Инициализация GigaChat
chat = GigaChat(credentials=GIGACHAT_API, verify_ssl_certs=False)

gpt_speaking_router = Router()

def load_user_data() -> Dict[int, list]:
    try:
        df = pd.read_excel(EXCEL_FILE, index_col=USER_ID_COLUMN, engine="openpyxl")
        # Преобразование словаря из строки обратно в словарь
        user_data = {
            user_id: eval(memory_str)
            for user_id, memory_str in df[MEMORY_COLUMN].items()
        }
    except FileNotFoundError:
        user_data = {}
    return user_data


def save_user_data(user_data: Dict[int, list]):
    # Преобразование словаря в строку для сохранения
    data_to_save = {
        user_id: str(memory)
        for user_id, memory in user_data.items()
    }
    df = pd.DataFrame.from_dict(data_to_save, orient='index', columns=[MEMORY_COLUMN])
    df.index.name = USER_ID_COLUMN
    df.to_excel(EXCEL_FILE, engine="openpyxl")


def get_user_memory(user_id: int) -> list:
    user_data = load_user_data()
    if user_id not in user_data:
        user_data[user_id] = []
        save_user_data(user_data)
    return user_data[user_id]


def clear_user_memory(user_id: int):
    user_data = load_user_data()
    if user_id in user_data:
        user_data[user_id] = []  # Очищаем историю, устанавливая пустой список
        save_user_data(user_data)

system_template = "You are a helpful AI that helps runners reach new heights. Talk in Russian."
system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
human_template = "{user_message}"
human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

prompt = ChatPromptTemplate.from_messages(
    [
        system_message_prompt,
        MessagesPlaceholder(variable_name="history"),
        human_message_prompt,
    ]
)

kind_of_training_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Интервальная", callback_data="interval_training")],
        [InlineKeyboardButton(text="Длительная", callback_data="long_training")],
        [InlineKeyboardButton(text="Темповая", callback_data="speed_training")],
        [InlineKeyboardButton(text="восстановительная", callback_data="refresh_training")]
    ]
)

def get_gpt_response(user_id: int, message: str) -> str:
    # Получаем историю из хранилища
    user_history = get_user_memory(user_id)

    chain = (
            RunnablePassthrough.assign(
                history=lambda _: user_history
            )
            | prompt
            | chat
    )
    response = chain.invoke({"user_message": message})

    user_data = load_user_data()
    user_data[user_id].extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": response.content}
    ])
    save_user_data(user_data)

    return response.content

@gpt_speaking_router.message(Command("gpt_use"))
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {message.from_user.full_name}! Я помогу тебе достичь новых высот в беге. Задавай свои вопросы!")

@gpt_speaking_router.message(Command("clear"))
async def clear_memory_handler(message: Message) -> None:
    user_id = message.from_user.id
    clear_user_memory(user_id)
    await message.answer("История диалога очищена.")

@gpt_speaking_router.message(Command("get_personal_training"))
async def get_personal_training(message:Message):
    await message.answer("Какую тренировку вы хотите:\n"
                         "(интервальная, темповая, длительная, восстановительная)?", reply_markup=kind_of_training_keyboard)


@gpt_speaking_router.callback_query(
    F.data.in_(["interval_training", "long_training", "speed_training", "refresh_training"]))
async def make_training(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    try:
        df = pd.read_excel("user_registration_data.xlsx")
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')
        user_data = df[df['user_id'] == user_id].iloc[0] 

        training_type_mapping = {
            "interval_training": "интервальную",
            "long_training": "длительную",
            "speed_training": "скоростную",
            "refresh_training": "восстановительную",
        }

        training_type = training_type_mapping.get(callback_query.data, "неизвестного типа")

        user_message = (f"Составь {training_type} тренировку для бега, имея следующие данные человека:"
                        f" возраст - {user_data['age']},"
                        f" вес - {user_data['weight']},"
                        f" рост - {user_data['height']},"
                        f" опыт бега в (месяцах) - {user_data['experience_running']},"
                        f" цель пробежать - {user_data['target_distance']},"
                        f" желаемая частота тренировок - {user_data['training_frequency']}")
        response = get_gpt_response(user_id, user_message)
        await callback_query.message.answer(response)  
        await callback_query.answer()  

    except FileNotFoundError:
        await callback_query.message.answer("Ошибка: Файл user_registration_data.xlsx не найден.")
        await callback_query.answer()
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error processing user data: {e}")
        await callback_query.message.answer("Ошибка: Не удалось обработать данные пользователя.")
        await callback_query.answer()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await callback_query.message.answer("Произошла непредвиденная ошибка.")
        await callback_query.answer()

@gpt_speaking_router.message(Command("get_equipment"))
async def get_equipment(message:Message):
    user_id = message.from_user.id
    try:
        df = pd.read_excel("user_registration_data.xlsx")
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')
        user_data = df[df['user_id'] == user_id].iloc[0]

        user_message = (f"дай совет про экипировку для бега, имея следующие данные:"
                        f"\nвозраст - {user_data["age"]},"
                        f"\nвес - {user_data["weight"]},"
                        f"\nрост - {user_data["height"]}")
        response = get_gpt_response(user_id, user_message)
        await message.answer(response)

    except FileNotFoundError:
        await message.answer("Ошибка: Файл user_registration_data.xlsx не найден.")
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error processing user data: {e}")
        await message.answer("Ошибка: Не удалось обработать данные пользователя.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await message.answer("Произошла непредвиденная ошибка.")

@gpt_speaking_router.message(Command("get_nutrition"))
async def get_nutrition(message:Message):
    user_id = message.from_user.id
    try:
        df = pd.read_excel("user_registration_data.xlsx")
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')
        user_data = df[df['user_id'] == user_id].iloc[0]

        user_message = (f"дай совет про то, чем лучше питаться исходя из следующих данных:"
                        f"\nвозраст - {user_data["age"]},"
                        f"\nвес - {user_data["weight"]},"
                        f"\nрост - {user_data["height"]},"
                        f"\nчастота тренировок - {user_data["training_frequency"]}")
        response = get_gpt_response(user_id, user_message)
        await message.answer(response)

    except FileNotFoundError:
        await message.answer("Ошибка: Файл user_registration_data.xlsx не найден.")
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error processing user data: {e}")
        await message.answer("Ошибка: Не удалось обработать данные пользователя.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await message.answer("Произошла непредвиденная ошибка.")


@gpt_speaking_router.message(F.text)
async def gpt_conversation(message: Message):
    user_id = message.from_user.id
    user_message = message.text
    response = get_gpt_response(user_id, user_message)
    await message.reply(response)
