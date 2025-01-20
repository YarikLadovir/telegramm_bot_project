import pandas as pd
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

from io import BytesIO

def generate_grafic(user_id: int, column_name: str, column_name2: str = None):
    try:
        df = pd.read_excel("user_tracking_data.xlsx")
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')

        if column_name2:
            user_data = df.loc[df['user_id'] == user_id, [column_name, column_name2]]
            if user_data.empty:
                print(f"Нет данных для пользователя {user_id}")
                return None
            return user_data
        else:
            user_data = df.loc[df['user_id'] == user_id, column_name]
            if user_data.empty:
                print(f"Нет данных для пользователя {user_id}")
                return None
            return user_data

    except FileNotFoundError:
        print("Файл user_tracking_data.xlsx не найден.")
        return None
    except Exception as e:
        print(f"Произошла ошибка при чтении файла: {e}")
        return None
async def send_speed_pulse_histogram(message: types.Message, data: pd.DataFrame, xlabel: str, ylabel: str, title: str):
    if data.empty:
      await message.answer("Недостаточно данных для построения гистограммы.")
      return

    plt.figure()

    # Scatter plot с группировкой по диапазонам
    plt.scatter(data["pace"], data["pulse"], alpha=0.7)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    await message.answer_photo(photo=BufferedInputFile(buf.read(), filename="histogram.png"))
    plt.close()
    buf.close()


keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="График:\nдистанция/тренировки"),
            KeyboardButton(text="График:\nпульс/тренировки")
        ],
        [
            KeyboardButton(text="График:\nскорость/пульс"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите вариант"
)

private_router = Router()

@private_router.message(Command("report_achievements"))
async def start_cmd(message: types.Message):
    await message.answer(f"Выберите какой отчет вы хотите", reply_markup=keyboard)

async def send_plot(message: types.Message, data: pd.DataFrame | pd.Series, xlabel: str, ylabel: str, title: str):
    plt.figure()

    if isinstance(data, pd.DataFrame):
        # Если data - DataFrame, используем столбцы для осей
        plt.plot(data.iloc[:, 0], data.iloc[:, 1])
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
    elif isinstance(data, pd.Series):
        # Если data - Series, используем индексы для оси X
        x_values = range(1, len(data) + 1)
        plt.plot(x_values, data.values)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(x_values)
    else:
        await message.answer("Ошибка: Неподдерживаемый тип данных для графика.")
        plt.close()
        return

    plt.title(title)
    plt.grid(True)

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    await message.answer_photo(photo=BufferedInputFile(buf.read(), filename="plot.png"))
    plt.close()
    buf.close()


@private_router.message(F.text == "График:\nдистанция/тренировки")
async def report_distance(message: types.Message):
    user_id = message.from_user.id
    df = generate_grafic(user_id=user_id, column_name="distance")
    if df is not None:
        await send_plot(message, df, "Количество записанных измерений", "Дистанция", f"Дистанция/тренировки для пользователя {message.from_user.first_name}")
    else:
        await message.answer("Недостаточно данных для построения графика.")

@private_router.message(F.text == "График:\nпульс/тренировки")
async def report_pulse(message: types.Message):
    user_id = message.from_user.id
    df = generate_grafic(user_id=user_id, column_name="pulse")
    if df is not None:
        await send_plot(message, df, "Количество записанных измерений", "Пульс", f"Пульс/тренировки для пользователя {message.from_user.first_name}")
    else:
        await message.answer("Недостаточно данных для построения графика.")

@private_router.message(F.text == "График:\nскорость/пульс")
async def report_speed_pulse(message: types.Message):
    user_id = message.from_user.id
    df = generate_grafic(user_id=user_id, column_name="pace", column_name2="pulse")

    if df is not None:
        await send_speed_pulse_histogram(message, df, "Скорость", "Пульс", f"Зависимость пульса от скорости для пользователя {message.from_user.first_name}")
    else:
        await message.answer("Недостаточно данных для построения графика.")