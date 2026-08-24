import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import Anthropic

# ============================================
# SOZLAMALAR - kalitlar Railway'ning "Variables" bo'limidan olinadi
# (kodga hech qachon to'g'ridan-to'g'ri yozmang!)
# ============================================
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

ADMIN_ID = int(os.environ["ADMIN_ID"])  # sizning Telegram ID'ingiz (raqam)
CARD_NUMBER = os.environ.get("CARD_NUMBER", "5614 6818 1198 0360")  # to'lov uchun karta
WEEKLY_PRICE = os.environ.get("WEEKLY_PRICE", "10 000 so'm")

FREE_MESSAGES = 1          # necha ta savol bepul
SUBSCRIPTION_DAYS = 7       # obuna necha kunlik

# Botning "shaxsiyati" - shu yerni o'zgartirib, botni o'z bizneslaringizga moslashtiring
SYSTEM_PROMPT = """Siz do'stona va foydali yordamchisiz. Foydalanuvchilarga o'zbek tilida,
qisqa va aniq javob bering. Agar savol biznes/xizmat haqida bo'lsa, mos maslahat bering."""

# ============================================

logging.basicConfig(level=logging.INFO)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Har bir foydalanuvchi uchun suhbat tarixi
user_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men AI yordamchiman. Menga istalgan savolingizni yozing 👋"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": user_text})
    # Faqat oxirgi 10 ta xabarni saqlaymiz (xotira tejash uchun)
    user_histories[user_id] = user_histories[user_id][-10:]

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001" ,
            max_tokens=1000,
            messages=[
                { "role" : "user" , "content" :
                 user_text}
            ]
        )
        answer = response.content[0].text 
        reply_text = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply_text})
        await update.message.reply_text(reply_text)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await update.message.reply_text("Kechirasiz, xatolik yuz berdi. Qayta urinib ko'ring.")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
