import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from google import genai

# --- Render va UptimeRobot uchun web-server ---
app = Flask('')

@app.route('/')
def home():
    return "Gemini AI Bot faol ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# ---------------------------------------------

# Environment Variables orqali olinadigan tokenlar
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>\n\n"
        f"🤖 Men **Gemini AI** aqlli yordamchisiman.\n"
        f"Menga xohlagan savolingizni berishingiz, matn yozdirishingiz yoki dasturlashga oid masalalar so'rashingiz mumkin!\n\n"
        f"💡 <i>Savolingizni matn ko'rinishida yuboring:</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(F.text)
async def ai_reply(message: types.Message):
    # Telegram'da "yozmoqda..." statusini ko'rsatish
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        
        reply_text = response.text
        # Telegram xabarlar limiti (4000 belgi) uchun tekshiruv
        if len(reply_text) > 4000:
            for i in range(0, len(reply_text), 4000):
                await message.answer(reply_text[i:i+4000])
        else:
            await message.answer(reply_text)

    except Exception as e:
        print(f"Xatolik: {e}")
        await message.answer("❌ Kechirasiz, javob tayyorlashda xatolik yuz berdi. Qaytadan urinib ko'ring.")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
