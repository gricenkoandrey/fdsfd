import os
import asyncio
import logging
import edge_tts
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get('BOT_TOKEN') # Токен должен быть в Secrets

logging.basicConfig(level=logging.INFO)

# Список нейросетевых голосов Microsoft
VOICES = {
    "👩 Светлана (TikTok Style)": "ru-RU-SvetlanaNeural",
    "👨 Дмитрий (Четкий)": "ru-RU-DmitryNeural",
    "👧 Дарья (Милая)": "ru-RU-DariyaNeural",
    "🇺🇸 Спанч Боб (Eng)": "en-US-AnaNeural", # Для мультяшных на англ.
    "🎭 Эпичный диктор (Eng)": "en-US-ChristopherNeural"
}

CODE_TO_NAME = {v: k for k, v in VOICES.items()}

# --- ВЕБ-СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Edge TTS Bot Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ЛОГИКА БОТА ---
class VoiceState(StatesGroup):
    current_voice = State()

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def generate_voice(text: str, voice: str):
    """Генерация через Microsoft Edge TTS"""
    file_path = f"voice_{voice}.mp3"
    # Настройка скорости (+10% делает голос более "тиктокным")
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(file_path)
    return file_path

def get_keyboard():
    buttons = []
    for name, code in VOICES.items():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"v_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(current_voice="ru-RU-SvetlanaNeural")
    await message.answer(
        "🎧 **СИСТЕМА НЕЙРО-ОЗВУЧКИ ГОТОВА**\n\nЯ использую движок Edge Neural TTS. Выбери голос:",
        reply_markup=get_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("v_"))
async def set_voice(callback: CallbackQuery, state: FSMContext):
    voice_code = callback.data[2:]
    await state.update_data(current_voice=voice_code)
    await callback.message.edit_text(
        f"✅ Выбран голос: **{CODE_TO_NAME.get(voice_code)}**\n\nПришли мне текст.",
        reply_markup=get_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return
    
    user_data = await state.get_data()
    voice = user_data.get("current_voice", "ru-RU-SvetlanaNeural")
    
    if len(message.text) > 500:
        return await message.answer("⚠️ Текст слишком длинный (макс 500 симв.)")

    wait_msg = await message.answer("🎙 Записываю голосовое...")
    
    try:
        path = await generate_voice(message.text, voice)
        await message.answer_voice(voice=FSInputFile(path))
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logging.error(f"TTS Error: {e}")
        await message.answer("❌ Ошибка при генерации голоса.")
    
    await wait_msg.delete()

async def main():
    keep_alive()
    print(">>> Edge TTS Bot Started on Replit")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
