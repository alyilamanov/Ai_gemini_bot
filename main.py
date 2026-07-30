import os
import asyncio
import logging
from threading import Thread
from flask import Flask
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from google import genai

logging.basicConfig(level=logging.INFO)

# --- 1. Web Server ---
app = Flask('')

@app.route('/')
def home():
    return "Ultra AI Bot faol va ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# --- 2. Konfiguratsiya ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

DB_NAME = "bot_data.db"

# --- 3. Ko'p tillilik Lug'ati ---
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Assalomu alaykum!</b>\n\nMen eng kuchli AI yordamchisiman. Matn, rasm, fayl, audio yuborishingiz yoki rasm chizdirishingiz mumkin!",
        'select_lang': "Iltimos, muloqot tilini tanlang:",
        'lang_changed': "✅ Til o'zgartirildi: O'zbek tili",
        'stat': "📊 <b>Statistika:</b>\n\n👥 Jami foydalanuvchilar: {users} ta",
        'gen_image': "🎨 Rasm chizilmoqda, kuting...",
        'error': "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        'cmd_help': "📌 <b>Buyruqlar:</b>\n/start - Qayta ishga tushirish\n/lang - Tilni o'zgartirish\n/image [tasvir] - Rasm yaratish"
    },
    'ru': {
        'welcome': "👋 <b>Здравствуйте!</b>\n\nЯ мощный ИИ-помощник. Вы можете отправлять текст, фото, файлы, аудио или создавать изображения!",
        'select_lang': "Пожалуйста, выберите язык:",
        'lang_changed': "✅ Язык изменен: Русский",
        'stat': "📊 <b>Статистика:</b>\n\n👥 Всего пользователей: {users}",
        'gen_image': "🎨 Изображение генерируется, подождите...",
        'error': "❌ Произошла ошибка. Попробуйте снова.",
        'cmd_help': "📌 <b>Команды:</b>\n/start - Перезапуск\n/lang - Сменить язык\n/image [описание] - Создать фото"
    },
    'en': {
        'welcome': "👋 <b>Hello!</b>\n\nI am an advanced AI assistant. You can send text, images, files, audio, or generate images!",
        'select_lang': "Please select your language:",
        'lang_changed': "✅ Language changed: English",
        'stat': "📊 <b>Statistics:</b>\n\n👥 Total users: {users}",
        'gen_image': "🎨 Generating image, please wait...",
        'error': "❌ An error occurred. Please try again.",
        'cmd_help': "📌 <b>Commands:</b>\n/start - Restart\n/lang - Change language\n/image [prompt] - Generate photo"
    },
    'tk': {
        'welcome': "👋 <b>Salam!</b>\n\nMen iň güýçli AI kömekçisi. Tekst, surat, faýl, ses ugradyp ýa-da surat çyzdyryp bilersiňiz!",
        'select_lang': "Haýyş, dili saýlaň:",
        'lang_changed': "✅ Dil üýtgedildi: Türkmen dili",
        'stat': "📊 <b>Statistika:</b>\n\n👥 Jemi ulanyjylar: {users}",
        'gen_image': "🎨 Surat çyzylýar, garaşyň...",
        'error': "❌ Sazlaşykda ýalňyşlyk boldy.",
        'cmd_help': "📌 <b>Buyruklar:</b>\n/start - Gaýtadan başlatmak\n/lang - Dili üýtgetmek\n/image [beýan] - Surat döretmek"
    }
}

# --- 4. Database ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'uz'
            )
        """)
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 'uz'

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO users (user_id, lang) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET lang = ?", (user_id, lang, lang))
        await db.commit()

async def get_users_count() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# --- 5. Klaviaturalar ---
def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"), InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"), InlineKeyboardButton(text="🇹🇲 Türkmençe", callback_data="lang_tk")]
    ])

# --- 6. Handlers ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    await set_user_lang(message.from_user.id, lang)
    txt = TEXTS[lang]
    await message.answer(f"{txt['welcome']}\n\n{txt['select_lang']}", parse_mode="HTML", reply_markup=get_lang_keyboard())

@dp.message(Command("lang"))
async def lang_cmd(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]['select_lang'], reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang_callback(call: types.CallbackQuery):
    lang_code = call.data.split("_")[1]
    await set_user_lang(call.from_user.id, lang_code)
    await call.message.edit_text(TEXTS[lang_code]['lang_changed'])

@dp.message(Command("admin"))
@dp.message(Command("stat"))
async def admin_cmd(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    count = await get_users_count()
    await message.answer(TEXTS[lang]['stat'].format(users=count), parse_mode="HTML")

# AI Rasm Yaratish
@dp.message(Command("image"))
async def generate_image_cmd(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    prompt = message.text.replace("/image", "").strip()
    
    if not prompt:
        await message.answer("⚠️ Iltimos, rasm tarifini yozing. Masalan: `/image kosmosdagi mushuk`", parse_mode="Markdown")
        return

    status_msg = await message.answer(TEXTS[lang]['gen_image'])
    
    try:
        result = ai_client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=dict(number_of_images=1, output_mime_type="image/jpeg")
        )
        
        for generated_image in result.generated_images:
            image_bytes = generated_image.image.image_bytes
            photo = BufferedInputFile(image_bytes, filename="ai_photo.jpg")
            await message.answer_photo(photo, caption=f"🎨 **Prompt:** {prompt}", parse_mode="Markdown")
            
        await status_msg.delete()
    except Exception as e:
        logging.error(f"Image error: {e}")
        await status_msg.edit_text(TEXTS[lang]['error'])

# Matn Javobi (Gemini 1.5 Flash ga to'g'rilangan)
@dp.message(F.text)
async def ai_text_reply(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    lang = await get_user_lang(message.from_user.id)

    prompt = f"Respond strictly in language code '{lang}'. User message: {message.text}"

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        reply = response.text
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await message.answer(reply[i:i+4000])
        else:
            await message.answer(reply)
            
    except Exception as e:
        logging.error(f"Text AI error: {e}")
        await message.answer(TEXTS[lang]['error'])

# Media Handlers (Gemini 1.5 Flash ga to'g'rilangan)
@dp.message(F.photo | F.document | F.voice | F.audio)
async def media_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    lang = await get_user_lang(message.from_user.id)

    try:
        file_id = None
        mime_type = "image/jpeg"

        if message.photo:
            file_id = message.photo[-1].file_id
            mime_type = "image/jpeg"
        elif message.document:
            file_id = message.document.file_id
            mime_type = message.document.mime_type or "application/pdf"
        elif message.voice or message.audio:
            media = message.voice or message.audio
            file_id = media.file_id
            mime_type = "audio/ogg"

        file_info = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file_info.file_path)

        caption = message.caption if message.caption else "Ushbu faylni tushuntirib bering."

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                {"mime_type": mime_type, "data": file_bytes.read()},
                f"Respond in language code {lang}. Query: {caption}"
            ]
        )
        await message.answer(response.text)

    except Exception as e:
        logging.error(f"Media error: {e}")
        await message.answer(TEXTS[lang]['error'])

# --- 7. Boshlash ---
async def main():
    keep_alive()
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
