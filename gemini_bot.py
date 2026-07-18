import asyncio
import logging
import os

import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

# .env faylidan tokenlarni o'qish
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("TELEGRAM_TOKEN yoki GEMINI_API_KEY .env faylida topilmadi!")

# Gemini sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

# Har bir foydalanuvchi uchun suhbat tarixini saqlash (oddiy dict, RAM ichida)
user_chats: dict[int, list] = {}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_chats[message.from_user.id] = []
    await message.answer(
        "Salom! Men Gemini AI asosida ishlovchi botman.\n"
        "Menga xohlagan savolingizni yozing.\n\n"
        "/reset — suhbat tarixini tozalash"
    )


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    user_chats[message.from_user.id] = []
    await message.answer("Suhbat tarixi tozalandi.")


@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    text = message.text

    if user_id not in user_chats:
        user_chats[user_id] = []

    # "yozmoqda..." holatini ko'rsatish
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        chat = model.start_chat(history=user_chats[user_id])
        response = await asyncio.to_thread(chat.send_message, text)
        answer = response.text

        # Tarixni yangilash (keyingi savollarda kontekst saqlanishi uchun)
        user_chats[user_id] = chat.history

        # Telegram xabar uzunligi cheklovi (4096 belgi)
        for i in range(0, len(answer), 4000):
            await message.answer(answer[i:i + 4000])

    except Exception as e:
        logging.exception("Gemini xatosi")
        await message.answer(f"Xatolik yuz berdi: {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
