import os
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv


swap_buffer = {}

# ------------------ НАСТРОЙКИ ------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ Не найден BOT_TOKEN в .env")

QUEUE_FILE = "queues.json"

subjects = ["Предмет 1", "Предмет 2"]
students = [
    "Студент 1", "Студент 2"
]

student_ids = {str(i): student for i, student in enumerate(students)}

ADMINS = [1000000001, 1000000002]  # <-- замените на реальные id админов

# ------------------ ЗАГРУЗКА И СОХРАНЕНИЕ ОЧЕРЕДЕЙ ------------------
def save_queues():
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queues, f, ensure_ascii=False, indent=4)

def load_queues():
    global queues
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                queues = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            queues = {subject: [] for subject in subjects}
    else:
        queues = {subject: [] for subject in subjects}

# ------------------ ФУНКЦИИ ДЛЯ КЛАВИАТУР ------------------
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=subj, callback_data=f"subj:{i}")] for i, subj in enumerate(subjects)]
    )

def subject_menu(subj_index: int, is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="📜 Вывести очередь", callback_data=f"queue:{subj_index}")],
        [InlineKeyboardButton(text="📝 Записаться", callback_data=f"join:{subj_index}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")]
    ]
    if is_admin:
        buttons.insert(1, [InlineKeyboardButton(text="❌ Удалить студента", callback_data=f"admin_delete:{subj_index}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def students_menu(subj_index: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=student, callback_data=f"add:{subj_index}:{i}")] for i, student in enumerate(students)
        ] + [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_subj:{subj_index}")]]
    )

def queue_menu(subj_index: int, is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="📜 Вывести очередь", callback_data=f"queue:{subj_index}")],
        [InlineKeyboardButton(text="🔄 Поменять местами", callback_data=f"swap_start:{subj_index}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ]
    if is_admin:
        buttons.insert(1, [InlineKeyboardButton(text="❌ Удалить студента", callback_data=f"admin_delete:{subj_index}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_delete_menu(subj_index: int):
    queue = queues[subjects[subj_index]]
    if not queue:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_subj:{subj_index}")]]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=student, callback_data=f"del:{subj_index}:{i}")] for i, student in enumerate(queue)
        ] + [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_subj:{subj_index}")]]
    )

# ------------------ СОЗДАНИЕ БОТА ------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ------------------ ЗАГРУЗКА ОЧЕРЕДЕЙ ПРИ СТАРТЕ ------------------
load_queues()

# ------------------ ОБРАБОТЧИК /start ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! 👋 Я бот для очередей студентов.\n\nВыберите предмет:",
        reply_markup=main_menu()
    )

# ------------------ ВЫБОР ПРЕДМЕТА ------------------
@dp.callback_query(lambda c: c.data.startswith("subj:"))
async def choose_subject(callback: types.CallbackQuery):
    await callback.answer()
    subj_index = int(callback.data.split(":")[1])
    is_admin = callback.from_user.id in ADMINS
    await callback.message.edit_text(
        f"Предмет: {subjects[subj_index]}",
        reply_markup=subject_menu(subj_index, is_admin)
    )

# ------------------ ВЫВОД ОЧЕРЕДИ С НУМЕРАЦИЕЙ ------------------
@dp.callback_query(lambda c: c.data.startswith("queue:"))
async def show_queue(callback: types.CallbackQuery):
    await callback.answer()
    subj_index = int(callback.data.split(":")[1])
    subj = subjects[subj_index]
    q = queues[subj]
    text = f"Очередь по {subj}:\n" + ("\n".join([f"{i+1}. {name}" for i, name in enumerate(q)]) if q else "Очередь пуста.")
    is_admin = callback.from_user.id in ADMINS
    await callback.message.edit_text(text, reply_markup=queue_menu(subj_index, is_admin))

# ------------------ ЗАПИСЬ В ОЧЕРЕДЬ ------------------
@dp.callback_query(lambda c: c.data.startswith("join:"))
async def join_queue(callback: types.CallbackQuery):
    await callback.answer()
    subj_index = int(callback.data.split(":")[1])
    await callback.message.edit_text("Выберите себя из списка:", reply_markup=students_menu(subj_index))

@dp.callback_query(lambda c: c.data.startswith("add:"))
async def add_to_queue(callback: types.CallbackQuery):
    await callback.answer()
    _, subj_index, student_index = callback.data.split(":")
    subj_index, student_index = int(subj_index), int(student_index)
    subj = subjects[subj_index]
    student = student_ids[str(student_index)]
    if student in queues[subj]:
        msg = f"{student}, вы уже в очереди на {subj}."
    else:
        queues[subj].append(student)
        save_queues()  # <-- сохраняем после добавления
        msg = f"{student} записан(а) в очередь по {subj}."
    is_admin = callback.from_user.id in ADMINS
    await callback.message.edit_text(msg, reply_markup=subject_menu(subj_index, is_admin))

# ------------------ АДМИН: УДАЛЕНИЕ ------------------
@dp.callback_query(lambda c: c.data.startswith("admin_delete:"))
async def admin_delete(callback: types.CallbackQuery):
    await callback.answer()
    if callback.from_user.id not in ADMINS:
        await callback.message.answer("❌ У вас нет прав администратора.")
        return
    subj_index = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Выберите студента для удаления:",
        reply_markup=admin_delete_menu(subj_index)
    )

@dp.callback_query(lambda c: c.data.startswith("del:"))
async def delete_student(callback: types.CallbackQuery):
    await callback.answer()
    if callback.from_user.id not in ADMINS:
        await callback.message.answer("❌ У вас нет прав администратора.")
        return
    _, subj_index, student_index = callback.data.split(":")
    subj_index, student_index = int(subj_index), int(student_index)
    subj = subjects[subj_index]
    student = queues[subj][student_index]
    queues[subj].pop(student_index)
    save_queues()  # <-- сохраняем после удаления
    await callback.message.edit_text(
        f"Студент {student} удален из очереди по {subj}.",
        reply_markup=admin_delete_menu(subj_index)
    )

# ------------------ НАЗАД ------------------
@dp.callback_query(lambda c: c.data.startswith("back_main"))
async def back_main(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Выберите предмет:", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data.startswith("back_subj:"))
async def back_subject(callback: types.CallbackQuery):
    await callback.answer()
    subj_index = int(callback.data.split(":")[1])
    is_admin = callback.from_user.id in ADMINS
    await callback.message.edit_text(f"Предмет: {subjects[subj_index]}", reply_markup=subject_menu(subj_index, is_admin))

# ------------------ ФУНКЦИЯ SWAP ------------------
@dp.callback_query(lambda c: c.data.startswith("swap_start:"))
async def swap_start(callback: types.CallbackQuery):
    await callback.answer()

    subj_index = int(callback.data.split(":")[1])
    subj = subjects[subj_index]
    queue = queues[subj]

    if len(queue) < 2:
        await callback.message.edit_text("В очереди меньше двух студентов, менять нечего.")
        return

    # Меню для выбора первого студента
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=student, callback_data=f"swap_first:{subj_index}:{i}")]
                            for i, student in enumerate(queue)
                        ] + [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_subj:{subj_index}")]]
    )

    await callback.message.edit_text("Выберите **первого** студента для обмена:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("swap_first:"))
async def swap_first(callback: types.CallbackQuery):
    await callback.answer()
    _, subj_index, student_index = callback.data.split(":")
    subj_index, student_index = int(subj_index), int(student_index)

    swap_buffer[callback.from_user.id] = {"subj_index": subj_index, "first_index": student_index}

    subj = subjects[subj_index]
    queue = queues[subj]

    # Меню выбора второго студента (кроме первого)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=student, callback_data=f"swap_second:{subj_index}:{i}")]
                            for i, student in enumerate(queue) if i != student_index
                        ] + [[InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_subj:{subj_index}")]]
    )

    await callback.message.edit_text(
        f"✅ Первый выбран: {queue[student_index]}\nТеперь выберите **второго** студента для обмена:",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("swap_second:"))
async def swap_second(callback: types.CallbackQuery):
    await callback.answer()
    _, subj_index, second_index = callback.data.split(":")
    subj_index, second_index = int(subj_index), int(second_index)

    if callback.from_user.id not in swap_buffer:
        await callback.message.edit_text("⚠ Сначала выберите первого студента.")
        return

    first_data = swap_buffer.pop(callback.from_user.id)
    first_index = first_data["first_index"]
    subj = subjects[subj_index]

    queue = queues[subj]
    queue[first_index], queue[second_index] = queue[second_index], queue[first_index]
    save_queues()

    text = f"🔄 Поменяли местами:\n{queue[second_index]} ↔ {queue[first_index]}\n\nОбновлённая очередь:\n" + \
           "\n".join([f"{i + 1}. {name}" for i, name in enumerate(queue)])

    await callback.message.edit_text(text, reply_markup=queue_menu(subj_index))


# ------------------ ГЛАВНАЯ ФУНКЦИЯ ------------------
async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
