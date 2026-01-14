import os
import base64
import requests
import asyncio
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- АДМИН-НАСТРОЙКИ ---
# Берем токен из Secrets (безопасно)
TOKEN = os.environ.get('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)

VOICES = {
    "🤖 Спанч Боб": "en_us_010",
    "😱 Крик (Ghostface)": "en_us_ghostface",
    "👽 Стич": "en_us_stitch",
    "🚀 Ракета (Марвел)": "en_us_rocket",
    "🤡 Барт Симпсон": "en_domi_funny",
    "🎭 Эпичный диктор": "en_us_006",
    "👩‍🦰 Русская (Дрыся)": "ru_001",
    "👨‍💼 Мужской (RU)": "ru_002",
}
CODE_TO_NAME = {v: k for k, v in VOICES.items()}

# --- ВЕБ-СЕРВЕР ДЛЯ ОБХОДА СОННОГО РЕЖИМА ---
app = Flask('')
@app.route('/')
def home(): return "OmniVoice System Active"

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

def generate_tiktok_tts(text: str, voice: str):
    url = "https://api16-normal-v4.tiktokv.com/media/api/ad/v1/tts/"
    # Маскируемся под официальное приложение максимально жестко
    headers = {
        "User-Agent": "com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; en_US; SM-G973N)",
        "Cookie": "sessionid=34c3829035e4d2a14e21a24d8b688d9c" 
    }
    params = {
        "speaker_map_type": 0, "aid": 1233, "text_str": text,
        "speaker_id": voice, "platform": "google", "language": "ru"
    }
    try:
        response = requests.post(url, headers=headers, params=params, timeout=15)
        data = response.json()
        if data.get("message") == "success":
            return base64.b64decode(data["data"]["v_str"])
        return None
    except Exception as e:
        logging.error(f"TTS Error: {e}")
        return None

def get_keyboard():
    buttons = []
    keys = list(VOICES.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(text=keys[i], callback_data=f"v_{VOICES[keys[i]]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(text=keys[i+1], callback_data=f"v_{VOICES[keys[i+1]]}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(current_voice="ru_001")
    await message.answer(
        "🎙 **СИСТЕМА ОЗВУЧКИ АКТИВИРОВАНА**\n\nВыбери персонажа:",
        reply_markup=get_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("v_"))
async def set_voice(callback: CallbackQuery, state: FSMContext):
    voice_code = callback.data[2:]
    await state.update_data(current_voice=voice_code)
    await callback.message.edit_text(
        f"✅ Выбран: **{CODE_TO_NAME.get(voice_code)}**\nОтправь текст для озвучки.",
        reply_markup=get_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return
    
    data = await state.get_data()
    voice = data.get("current_voice", "ru_001")
    
    if len(message.text) > 300:
        return await message.answer("⚠️ Максимум 300 символов!")

    wait_msg = await message.answer("📡 Генерирую...")
    
    audio_data = generate_tiktok_tts(message.text, voice)
    
    if audio_data:
        file_path = f"voice_{message.from_user.id}.mp3"
        with open(file_path, "wb") as f:
            f.write(audio_data)
        
        await message.answer_voice(voice=FSInputFile(file_path))
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        await message.answer("❌ Ошибка TikTok API. Возможно, Replit забанен в TikTok. Попробуй позже.")
    
    await wait_msg.delete()

async def main():
    keep_alive() # Запускаем сервер-"антисон"
    print(">>> OmniCode Voice Bot Started on Replit")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
