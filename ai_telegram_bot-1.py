import os
import json
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
# LOGGING / API
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
    except Exception:
        return {}


def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


users = load_users()


# ============================================
# FOYDALANUVCHI
# ============================================

def save_user_info(user):

    user_id = str(user.id)

    if user_id not in users:
        users[user_id] = {
            "free_used": 0,
            "subscription_until": None,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }

    else:
        users[user_id]["username"] = user.username
        users[user_id]["first_name"] = user.first_name
        users[user_id]["last_name"] = user.last_name

    save_users(users)


# ============================================
# START
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_user_info(update.effective_user)

    await update.message.reply_text(
        "👋 Salom!\n\n"
        "🤖 Men Aqilliyordam AI botiman.\n\n"
        "🆓 Sizga 3 ta savolga bepul javob beriladi.\n"
        "💎 Keyingi savollar uchun 7 kunlik obuna kerak.\n\n"
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
        "1️⃣ Yuqoridagi kartaga to'lov qiling.\n"
        "2️⃣ To'lov chekini shu botga yuboring.\n"
        "3️⃣ Admin tekshiradi va obunangizni faollashtiradi.\n\n"
        "⚠️ Chekni aynan shu botga yuboring."
    )


# ============================================
# CHEKNI ADMINDA TASDIQLASH
# ============================================

async def send_receipt_to_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    is_document: bool = False
):

    user = update.effective_user
    user_id = user.id

    username = (
        f"@{user.username}"
        if user.username
        else "username yo'q"
    )

    name = " ".join(
        x for x in [user.first_name, user.last_name] if x
    )

    if not name:
        name = "Ism yo'q"

    caption = (
        "💳 YANGI TO'LOV CHEKI\n\n"
        f"👤 Ism: {name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 User ID: {user_id}\n\n"
        f"💰 Narx: {WEEKLY_PRICE}\n"
        "⏳ Tasdiqlashni kutmoqda..."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ TASDIQLASH",
                callback_data=f"approve:{user_id}"
            ),
            InlineKeyboardButton(
                "❌ RAD ETISH",
                callback_data=f"reject:{user_id}"
            )
        ]
    ])

    if is_document:
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=file_id,
            caption=caption,
            reply_markup=keyboard
        )
    else:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            reply_markup=keyboard
        )

    await update.message.reply_text(
        "✅ Chekingiz adminga yuborildi.\n\n"
        "⏳ To'lov tekshirilmoqda.\n"
        "Tasdiqlangandan keyin 7 kunlik obuna avtomatik faollashadi."
    )


# ============================================
# RASM CHEK
# ============================================

async def handle_receipt_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    save_user_info(update.effective_user)

    photo = update.message.photo[-1]

    await send_receipt_to_admin(
        update,
        context,
        photo.file_id,
        is_document=False
    )


# ============================================
# PDF / FILE CHEK
# ============================================

async def handle_receipt_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    save_user_info(update.effective_user)

    document = update.message.document

    await send_receipt_to_admin(
        update,
        context,
        document.file_id,
        is_document=True
    )


# ============================================
# ADMIN TUGMALARINI BOSISH
# ============================================

async def receipt_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    # Faqat admin
    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Siz admin emassiz!",
            show_alert=True
        )
        return

    data = query.data

    # ========================================
    # TASDIQLASH
    # ========================================

    if data.startswith("approve:"):

        user_id = data.split(":")[1]

        if user_id not in users:
            users[user_id] = {
                "free_used": FREE_MESSAGES,
                "subscription_until": None,
                "username": None,
                "first_name": None,
                "last_name": None
            }

        # Agar eski obuna hali tugamagan bo'lsa,
        # yangi 7 kunni eski muddatga qo'shamiz
        old_until = users[user_id].get(
            "subscription_until"
        )

        now = datetime.now()

        if old_until:
            try:
                old_date = datetime.fromisoformat(old_until)

                if old_date > now:
                    until = old_date + timedelta(
                        days=SUBSCRIPTION_DAYS
                    )
                else:
                    until = now + timedelta(
                        days=SUBSCRIPTION_DAYS
                    )

            except Exception:
                until = now + timedelta(
                    days=SUBSCRIPTION_DAYS
                )

        else:
            until = now + timedelta(
                days=SUBSCRIPTION_DAYS
            )

        users[user_id]["subscription_until"] = (
            until.isoformat()
        )

        # Bepul limitni ham tugatib qo'yamiz
        users[user_id]["free_used"] = FREE_MESSAGES

        save_users(users)

        # Foydalanuvchiga xabar
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    "🎉 TO'LOV TASDIQLANDI!\n\n"
                    "✅ AI Yordam obunangiz faollashtirildi.\n\n"
                    f"💎 Muddat: {SUBSCRIPTION_DAYS} kun\n"
                    f"📅 Tugash sanasi: "
                    f"{until.strftime('%d.%m.%Y %H:%M')}\n\n"
                    "🤖 Endi AI yordamchidan foydalanishingiz mumkin!"
                )
            )
        except Exception as e:
            logging.error(
                f"Foydalanuvchiga xabar yuborishda xato: {e}"
            )

        # Admin xabarini yangilash
        await query.edit_message_caption(
            caption=(
                query.message.caption +
                "\n\n"
                "━━━━━━━━━━━━━━\n"
                "✅ TO'LOV TASDIQLANDI\n"
                f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi."
            ),
            reply_markup=None
        )

    # ========================================
    # RAD ETISH
    # ========================================

    elif data.startswith("reject:"):

        user_id = data.split(":")[1]

        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    "❌ To'lov chekingiz tasdiqlanmadi.\n\n"
                    "Iltimos, to'lov chekini tekshirib, "
                    "qaytadan yuboring yoki admin bilan bog'laning.\n\n"
                    f"👨‍💻 Admin: {ADMIN_USERNAME}"
                )
            )
        except Exception as e:
            logging.error(
                f"Rad javobini yuborishda xato: {e}"
            )

        await query.edit_message_caption(
            caption=(
                query.message.caption +
                "\n\n"
                "━━━━━━━━━━━━━━\n"
                "❌ TO'LOV RAD ETILDI."
            ),
            reply_markup=None
        )


# ============================================
# ADMIN OBUNA BERISH
# /activate USER_ID
# ============================================

async def activate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
            "subscription_until": None,
            "username": None,
            "first_name": None,
            "last_name": None
        }

    until = datetime.now() + timedelta(
        days=SUBSCRIPTION_DAYS
    )

    users[user_id]["subscription_until"] = (
        until.isoformat()
    )

    save_users(users)

    await update.message.reply_text(
        "✅ Obuna faollashtirildi!\n\n"
        f"👤 User ID: {user_id}\n"
        f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi."
    )


# ============================================
# ADMIN FOYDALANUVCHILAR
# /users
# ============================================

async def show_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )
        return

    if not users:
        await update.message.reply_text(
            "📭 Hozircha foydalanuvchilar yo'q."
        )
        return

    total = len(users)

    text = (
        f"👥 JAMI FOYDALANUVCHILAR: {total}\n\n"
    )

    for number, (user_id, data) in enumerate(
        users.items(), 1
    ):

        username = data.get("username")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        if username:
            username_text = f"@{username}"
        else:
            username_text = "username yo'q"

        full_name = " ".join(
            x for x in [first_name, last_name] if x
        )

        if not full_name:
            full_name = "Ism yo'q"

        free_used = data.get(
            "free_used", 0
        )

        subscription = data.get(
            "subscription_until"
        )

        if subscription:
            try:
                until = datetime.fromisoformat(
                    subscription
                )

                if datetime.now() < until:
                    subscription_text = (
                        "✅ Faol"
                    )
                else:
                    subscription_text = (
                        "❌ Tugagan"
                    )

            except Exception:
                subscription_text = (
                    "❌ Noma'lum"
                )
        else:
            subscription_text = (
                "❌ Obuna yo'q"
            )

        text += (
            f"{number}. 👤 {full_name}\n"
            f"   🆔 ID: {user_id}\n"
            f"   🔗 {username_text}\n"
            f"   🆓 Bepul: "
            f"{free_used}/{FREE_MESSAGES}\n"
            f"   💎 Obuna: "
            f"{subscription_text}\n\n"
        )

        if len(text) > 3500:

            await update.message.reply_text(
                text
            )

            text = "👥 DAVOMI:\n\n"

    if text.strip():
        await update.message.reply_text(text)


# ============================================
# AI MESSAGE
# ============================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(
        update.effective_user.id
    )

    user_text = update.message.text

    save_user_info(
        update.effective_user
    )

    user = users[user_id]

    # ========================================
    # OBUNANI TEKSHIRISH
    # ========================================

    subscription_active = False

    if user.get("subscription_until"):

        try:

            until = datetime.fromisoformat(
                user["subscription_until"]
            )

            if datetime.now() < until:
                subscription_active = True

        except Exception:
            subscription_active = False

    # ========================================
    # BEPUL LIMIT
    # ========================================

    if not subscription_active:

        if user["free_used"] >= FREE_MESSAGES:

            save_users(users)

            await update.message.reply_text(
                "🔒 Bepul savollaringiz tugadi.\n\n"
                "🤖 Botdan foydalanishni davom "
                "ettirish uchun 7 kunlik obuna oling.\n\n"
                f"💰 Narx: {WEEKLY_PRICE}\n"
                "💳 To'lov: /buy"
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

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        logging.error(
            f"Xatolik: {e}"
        )

        await update.message.reply_text(
            "❌ Kechirasiz, xatolik yuz berdi. "
            "Qayta urinib ko'ring."
        )


# ============================================
# MAIN
# ============================================

def main():

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # BUY
    app.add_handler(
        CommandHandler(
            "buy",
            buy
        )
    )

    # ADMIN ACTIVATE
    app.add_handler(
        CommandHandler(
            "activate",
            activate
        )
    )

    # ADMIN USERS
    app.add_handler(
        CommandHandler(
            "users",
            show_users
        )
    )

    # CHEK - RASM
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_receipt_photo
        )
    )

    # CHEK - PDF / FILE
    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_receipt_document
        )
    )

    # ADMIN TASDIQLASH / RAD ETISH
    app.add_handler(
        CallbackQueryHandler(
            receipt_action
        )
    )

    # AI TEXT
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
