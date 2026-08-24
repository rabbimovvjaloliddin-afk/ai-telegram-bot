import os
import sqlite3
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)
from anthropic import Anthropic

# ============================================
# SOZLAMALAR - kalitlar Railway'ning "Variables" bo'limidan olinadi
# (kodga hech qachon to'g'ridan-to'g'ri yozmang!)
# ============================================
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ADMIN_ID = int(os.environ["@jaloliddino7"])  # sizning Telegram ID'ingiz (raqam)
CARD_NUMBER = os.environ.get("CARD_NUMBER", "5614 6818 1198 0360")  # to'lov uchun karta
WEEKLY_PRICE = os.environ.get("WEEKLY_PRICE", "10 000 so'm")

FREE_MESSAGES = 2          # necha ta savol bepul
SUBSCRIPTION_DAYS = 7       # obuna necha kunlik

# Botning "shaxsiyati" - shu yerni o'zgartirib, botni o'z bizneslaringizga moslashtiring
SYSTEM_PROMPT = """Siz do'stona va foydali yordamchisiz. Foydalanuvchilarga o'zbek tilida,
qisqa va aniq javob bering. Agar savol biznes/xizmat haqida bo'lsa, mos maslahat bering."""

# ============================================

logging.basicConfig(level=logging.INFO)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Har bir foydalanuvchi uchun suhbat tarixi (RAM ichida, xotira uchun)
user_histories = {}

DB_PATH = os.path.join(os.path.dirname(file), "bot.db")


# ------------------ BAZA ------------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            message_count INTEGER DEFAULT 0,
            subscribed_until TEXT,
            pending_payment INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id, username=None):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (user_id, username, message_count) VALUES (?, ?, 0)",
            (user_id, username),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def increment_count(user_id):
    conn = db()
    conn.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def has_active_subscription(row):
    if row["subscribed_until"] is None:
        return False
    return datetime.fromisoformat(row["subscribed_until"]) > datetime.now()


def set_pending_payment(user_id, value: int):
    conn = db()
    conn.execute("UPDATE users SET pending_payment = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def activate_subscription(user_id):
    until = datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)
    conn = db()
    conn.execute(
        "UPDATE users SET subscribed_until = ?, pending_payment = 0 WHERE user_id = ?",
        (until.isoformat(), user_id),
    )
    conn.commit()
    conn.close()
    return until


# ------------------ HANDLERLAR ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text(
        "Salom! Men AI yordamchiman. Menga istalgan savolingizni yozing 👋\n\n"
        f"Birinchi savolingiz bepul, keyin haftalik obuna kerak bo'ladi ({WEEKLY_PRICE})."
    )


async def send_payment_prompt(update: Update, user_id: int):

set_pending_payment(user_id, 1)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ To'ladim", callback_data="paid")
    ]])
    await update.message.reply_text(
        f"Bepul limitingiz tugadi.\n\n"
        f"Haftalik obuna narxi: {WEEKLY_PRICE}\n"
        f"Karta raqami: {CARD_NUMBER}\n\n"
        f"To'lovni amalga oshirgach, pastdagi tugmani bosing 👇",
        reply_markup=keyboard,
    )


async def handle_payment_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "noma'lum"

    await query.edit_message_text(
        "To'lovingiz adminga yuborildi. Tasdiqlangach, sizga xabar beramiz ✅"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user_id}")
    ]])
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💰 Yangi to'lov so'rovi!\nFoydalanuvchi: @{username} (ID: {user_id})",
        reply_markup=keyboard,
    )


async def handle_approve_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return  # faqat admin tasdiqlay oladi

    user_id = int(query.data.split("_")[1])
    until = activate_subscription(user_id)

    await query.edit_message_text(f"✅ Tasdiqlandi! Obuna: {until.strftime('%Y-%m-%d')} gacha")
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ To'lovingiz tasdiqlandi! Obunangiz {until.strftime('%Y-%m-%d')} sanagacha faol.",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    row = get_user(user_id, update.effective_user.username)

    # limit va obuna tekshiruvi
    if row["message_count"] >= FREE_MESSAGES and not has_active_subscription(row):
        if row["pending_payment"]:
            await update.message.reply_text(
                "To'lovingiz admin tomonidan tekshirilmoqda, biroz kuting ⏳"
            )
        else:
            await send_payment_prompt(update, user_id)
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": user_text})
    # Faqat oxirgi 10 ta xabarni saqlaymiz (xotira tejash uchun)
    user_histories[user_id] = user_histories[user_id][-10:]

   try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id],
        )
        reply_text = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply_text})
        await update.message.reply_text(reply_text)
        increment_count(user_id)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await update.message.reply_text("Kechirasiz, xatolik yuz berdi. Qayta urinib ko'ring.")


def main():
    init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_payment_button, pattern="^paid$"))
    app.add_handler(CallbackQueryHandler(handle_approve_button, pattern="^approve_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi...")
    app.run_polling()


if name == "main":
    main()
