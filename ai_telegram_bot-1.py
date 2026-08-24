import os
import json
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from anthropic import Anthropic


# ============================================
# SOZLAMALAR
# ============================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

ADMIN_ID = 6078096693
ADMIN_USERNAME = "@jaloliddino7"

CARD_NUMBER = os.environ.get(
    "CARD_NUMBER",
    "5614 6818 1198 0360"
)

WEEKLY_PRICE = os.environ.get(
    "WEEKLY_PRICE",
    "10 000 so'm"
)

FREE_MESSAGES = 3
SUBSCRIPTION_DAYS = 7

SYSTEM_PROMPT = """
Siz do'stona va foydali AI yordamchisiz.
Foydalanuvchilarga o'zbek tilida qisqa, aniq va foydali javob bering.
"""


# ============================================

logging.basicConfig(level=logging.INFO)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

DATA_FILE = "users.json"


# ============================================
# MA'LUMOTLARNI SAQLASH
# ============================================

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


users = load_users()


# ============================================
# START
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)

    if user_id not in users:
        users[user_id] = {
            "free_used": 0,
            "subscription_until": None
        }
        save_users(users)

    await update.message.reply_text(
        "👋 Salom!\n\n"
        "🤖 Men Aqilliyordam AI botiman.\n\n"
        "🆓 Sizga 3 ta bepul javob beriladi.\n"
        "💳 Keyingi savollar uchun 7 kunlik obuna kerak.\n\n"
        "📌 Obuna olish: /buy"
    )


# ============================================
# BUY
# ============================================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "💎 AI YORDAM OBUNASI\n\n"
        f"📅 Muddat: {SUBSCRIPTION_DAYS} kun\n"
        f"💰 Narx: {WEEKLY_PRICE}\n\n"
        "💳 To'lov uchun karta:\n"
        f"{CARD_NUMBER}\n\n"
        "To'lovni amalga oshirgach, "
        "chekni adminga yuboring.\n\n"
        f"👨‍💻 Admin: {ADMIN_USERNAME}"
    )


# ============================================
# ADMIN OBUNA BERISH
# /activate USER_ID
# ============================================

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Sizda bu buyruqdan foydalanish huquqi yo'q."
        )
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Foydalanish:\n"
            "/activate USER_ID"
        )
        return

    user_id = context.args[0]

    if user_id not in users:
        users[user_id] = {
            "free_used": FREE_MESSAGES,
            "subscription_until": None
        }

    until = datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)

    users[user_id]["subscription_until"] = until.isoformat()

    save_users(users)

    await update.message.reply_text(
        f"✅ Obuna faollashtirildi!\n\n"
        f"👤 User ID: {user_id}\n"
        f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi."
    )


# ============================================
# MESSAGE
# ============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)
    user_text = update.message.text

    if user_id not in users:
        users[user_id] = {
            "free_used": 0,
            "subscription_until": None
        }

    user = users[user_id]

    # ========================================
    # OBUNA TEKSHIRISH
    # ========================================

    subscription_active = False

    if user.get("subscription_until"):

        try:
            until = datetime.fromisoformat(
                user["subscription_until"]
            )

            if datetime.now() < until:
                subscription_active = True

        except:
            subscription_active = False


    # ========================================
    # PULSIZ LIMIT
    # ========================================

    if not subscription_active:

        if user["free_used"] >= FREE_MESSAGES:

            save_users(users)

            await update.message.reply_text(
                "🔒 Bepul savolingiz tugadi.\n\n"
                "🤖 Botdan foydalanishni davom ettirish "
                "uchun 7 kunlik obuna oling.\n\n"
                f"💰 Narx: {WEEKLY_PRICE}\n"
                "💳 To'lov ma'lumotlari uchun: /buy"
            )

            return


    # ========================================
    # CLAUDE API
    # ========================================

    try:

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_text
                }
            ]
        )

        answer = response.content[0].text

        if not subscription_active:
            user["free_used"] += 1

        save_users(users)

        await update.message.reply_text(answer)

    except Exception as e:

        logging.error(f"Xatolik: {e}")

        await update.message.reply_text(
            "❌ Kechirasiz, xatolik yuz berdi. "
            "Qayta urinib ko'ring."
        )


# ============================================
# MAIN
# ============================================

def main():

    app = Application.builder().token(
        TELEGRAM_BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("buy", buy)
    )

    app.add_handler(
        CommandHandler("activate", activate)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot ishga tushdi...")

    app.run_polling()


if __name__ == "__main__":
    main()
