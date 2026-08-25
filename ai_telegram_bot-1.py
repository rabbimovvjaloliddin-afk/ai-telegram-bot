import os
import re
import json
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
REFERRAL_BONUS = 2
SUBSCRIPTION_DAYS = 7

DATA_FILE = "users.json"


# ============================================
# AI
# ============================================

SYSTEM_PROMPT = """
Siz Aqilliyordam AI nomli foydali AI yordamchisiz.

Foydalanuvchiga o'zbek tilida aniq, tushunarli va foydali javob bering.

Siz quyidagilarda yordam bera olasiz:
- Matn yozish
- Insho yozish
- Telegram bot yaratish
- Test tuzish
- Dars va uy vazifalari
- Tarjima
- G'oya topish
- Kod yozish va tushuntirish
- Turli savollarga javob berish

Javoblarda Markdown belgilaridan foydalanmang.
**qalin**, *kursiv*, # sarlavha va ```kod``` kabi
belgilarni ishlatmang.

Oddiy matn, emoji va yangi qatorlardan foydalaning.
"""


logging.basicConfig(level=logging.INFO)

client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)


# ============================================
# MARKDOWN TOZALASH
# ============================================

def clean_markdown(text):

    if not text:
        return text

    text = re.sub(
        r"```(?:\w+\n)?(.*?)```",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"\1",
        text
    )

    text = re.sub(
        r"__(.+?)__",
        r"\1",
        text
    )

    text = re.sub(
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
        r"\1",
        text
    )

    text = re.sub(
        r"^#{1,6}\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"`(.+?)`",
        r"\1",
        text
    )

    return text.strip()


# ============================================
# DATABASE
# ============================================

def load_users():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_users():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            users,
            f,
            ensure_ascii=False,
            indent=2
        )


users = load_users()


# ============================================
# USER SAQLASH
# ============================================

def save_user_info(user):

    user_id = str(user.id)

    if user_id not in users:

        users[user_id] = {
            "free_used": 0,
            "subscription_until": None,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "referrals": [],
            "referred_by": None
        }

    else:

        users[user_id]["username"] = user.username
        users[user_id]["first_name"] = user.first_name
        users[user_id]["last_name"] = user.last_name

        if "referrals" not in users[user_id]:
            users[user_id]["referrals"] = []

        if "referred_by" not in users[user_id]:
            users[user_id]["referred_by"] = None

    save_users()


# ============================================
# START
# ============================================

async def start(update, context):

    user = update.effective_user
    user_id = str(user.id)

    new_user = user_id not in users

    save_user_info(user)

    # ========================================
    # REFERRAL
    # ========================================

    if new_user and context.args:

        referral_id = context.args[0]

        if referral_id.startswith("ref_"):
            referral_id = referral_id[4:]

        if (
            referral_id != user_id
            and referral_id in users
        ):

            ref_user = users[referral_id]

            if "referrals" not in ref_user:
                ref_user["referrals"] = []

            if user_id not in ref_user["referrals"]:

                ref_user["referrals"].append(
                    user_id
                )

                # +2 bepul savol
                ref_user["free_used"] = max(
                    0,
                    ref_user.get("free_used", 0)
                    - REFERRAL_BONUS
                )

                users[user_id]["referred_by"] = (
                    referral_id
                )

                save_users()

                try:

                    await context.bot.send_message(
                        chat_id=int(referral_id),
                        text=(
                            "🎉 YANGI DO'STINGIZ QO'SHILDI!\n\n"
                            f"🎁 Sizga +{REFERRAL_BONUS} ta "
                            "bepul savol berildi.\n\n"
                            f"👥 Jami takliflaringiz: "
                            f"{len(ref_user['referrals'])} ta"
                        )
                    )

                except Exception as e:

                    logging.error(
                        f"Referral xatosi: {e}"
                    )

    # ========================================
    # MENU
    # ========================================

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💎 OBUNA OLISH",
                callback_data="buy_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 DO'ST TAKLIF QILISH",
                callback_data="referral"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 REKLAMA",
                callback_data="advertisement"
            )
        ]

    ])

    await update.message.reply_text(

        "👋 Salom, "
        + (user.first_name or "do'stim")
        + "!\n\n"

        "🤖 Aqilliyordam AI botiga xush kelibsiz!\n\n"

        "🧠 Men sizga ko'plab vazifalarda yordam beraman.\n\n"

        "📝 Matn yozish\n"
        "📚 Insho yozish\n"
        "🤖 Telegram bot yaratish\n"
        "🧠 Test tuzish\n"
        "🌍 Tarjima\n"
        "📖 Dars va uy vazifalari\n"
        "💡 G'oya topish\n"
        "💻 Kod yozish\n\n"

        f"🆓 Sizda {FREE_MESSAGES} ta bepul savol bor.\n"
        f"💎 Keyin {SUBSCRIPTION_DAYS} kunlik obuna kerak.\n\n"

        "👇 Quyidagi menyudan foydalaning:",

        reply_markup=keyboard
    )


# ============================================
# BUY
# ============================================

async def buy(update, context):

    await update.message.reply_text(

        "💎 AI YORDAM OBUNASI\n\n"

        f"📅 Muddat: {SUBSCRIPTION_DAYS} kun\n"
        f"💰 Narx: {WEEKLY_PRICE}\n\n"

        "💳 TO'LOV UCHUN KARTA:\n"
        f"{CARD_NUMBER}\n\n"

        "1️⃣ Kartaga to'lov qiling.\n"
        "2️⃣ Chekni shu botga yuboring.\n"
        "3️⃣ Admin to'lovni tekshiradi.\n"
        "4️⃣ Tasdiqlangach obuna faollashadi.\n\n"

        "📸 Chekni rasm yoki PDF qilib yuboring."
    )


# ============================================
# BUTTONLAR
# ============================================

async def button_handler(update, context):

    query = update.callback_query

    await query.answer()

    user_id = str(query.from_user.id)

    # ========================================
    # OBUNA
    # ========================================

    if query.data == "buy_menu":

        await query.message.reply_text(

            "💎 AI YORDAM OBUNASI\n\n"

            f"📅 Muddat: {SUBSCRIPTION_DAYS} kun\n"
            f"💰 Narx: {WEEKLY_PRICE}\n\n"

            "💳 TO'LOV UCHUN KARTA:\n"
            f"{CARD_NUMBER}\n\n"

            "1️⃣ Kartaga to'lov qiling.\n"
            "2️⃣ Chekni shu botga yuboring.\n"
            "3️⃣ Admin tekshiradi.\n"
            "4️⃣ Tasdiqlangach obuna faollashadi.\n\n"

            "📸 Chekni rasm yoki PDF qilib yuboring."
        )

    # ========================================
    # REFERRAL
    # ========================================

    elif query.data == "referral":

        bot_username = context.bot.username

        referral_link = (
            f"https://t.me/{bot_username}"
            f"?start=ref_{user_id}"
        )

        count = len(
            users.get(
                user_id,
                {}
            ).get(
                "referrals",
                []
            )
        )

        await query.message.reply_text(

            "👥 DO'STLARNI TAKLIF QILING\n\n"

            f"Har bir yangi do'stingiz uchun "
            f"+{REFERRAL_BONUS} ta bepul savol olasiz! 🎁\n\n"

            "🔗 SIZNING TAKLIF HAVOLANGIZ:\n\n"

            f"{referral_link}\n\n"

            f"👥 Taklif qilganlaringiz: "
            f"{count} ta\n\n"

            "📢 Havolani do'stlaringizga yuboring "
            "va bepul savollar oling!"
        )

    # ========================================
    # REKLAMA
    # ========================================

    elif query.data == "advertisement":

        bot_username = context.bot.username

        advertisement = (

            "📢 Aqilliyordam AI 🤖\n\n"

            "Savolingiz bormi? AI sizga yordam beradi! 🚀\n\n"

            "📝 Matn yozish\n"
            "📚 Insho yozish\n"
            "🤖 Telegram bot yaratish\n"
            "🧠 Test tuzish\n"
            "🌍 Tarjima qilish\n"
            "📖 Dars va uy vazifalarida yordam\n"
            "💡 G'oya topish\n"
            "💻 Kod yozish\n"
            "❓ Turli savollarga javob\n\n"

            "🎁 Yangi foydalanuvchilarga "
            "3 ta savol BEPUL!\n\n"

            "⚡ Tez va qulay foydalaning!\n\n"

            "👇 Hozir sinab ko'ring:\n"
            f"https://t.me/{bot_username}"
        )

        await query.message.reply_text(
            advertisement
        )


# ============================================
# CHEKNI ADMINDA KO'RSATISH
# ============================================

async def send_receipt_to_admin(
    update,
    context,
    file_id,
    is_document=False
):

    user = update.effective_user

    user_id = user.id

    username = (
        f"@{user.username}"
        if user.username
        else "username yo'q"
    )

    name = " ".join(
        x for x in [
            user.first_name,
            user.last_name
        ]
        if x
    )

    if not name:
        name = "Ism yo'q"

    caption = (

        "💳 YANGI TO'LOV CHEKI\n\n"

        f"👤 Ism: {name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 User ID: {user_id}\n\n"

        f"💰 Narx: {WEEKLY_PRICE}\n\n"

        "⏳ TASDIQLASHNI KUTMOQDA..."
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

        "⏳ To'lov tekshirilmoqda.\n\n"

        "Tasdiqlangandan keyin obunangiz faollashadi."
    )


# ============================================
# RASM CHEK
# ============================================

async def handle_receipt_photo(
    update,
    context
):

    save_user_info(
        update.effective_user
    )

    photo = update.message.photo[-1]

    await send_receipt_to_admin(
        update,
        context,
        photo.file_id,
        False
    )


# ============================================
# PDF CHEK
# ============================================

async def handle_receipt_document(
    update,
    context
):

    save_user_info(
        update.effective_user
    )

    document = update.message.document

    await send_receipt_to_admin(
        update,
        context,
        document.file_id,
        True
    )


# ============================================
# ADMIN TASDIQLASH
# ============================================

async def receipt_action(
    update,
    context
):

    query = update.callback_query

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "❌ Siz admin emassiz!",
            show_alert=True
        )

        return

    await query.answer()

    data = query.data

    # ========================================
    # APPROVE
    # ========================================

    if data.startswith("approve:"):

        user_id = data.split(":")[1]

        if user_id not in users:

            users[user_id] = {
                "free_used": FREE_MESSAGES,
                "subscription_until": None,
                "username": None,
                "first_name": None,
                "last_name": None,
                "referrals": [],
                "referred_by": None
            }

        old_until = users[user_id].get(
            "subscription_until"
        )

        now = datetime.now()

        if old_until:

            try:

                old_date = datetime.fromisoformat(
                    old_until
                )

                if old_date > now:

                    until = (
                        old_date
                        + timedelta(
                            days=SUBSCRIPTION_DAYS
                        )
                    )

                else:

                    until = (
                        now
                        + timedelta(
                            days=SUBSCRIPTION_DAYS
                        )
                    )

            except Exception:

                until = (
                    now
                    + timedelta(
                        days=SUBSCRIPTION_DAYS
                    )
                )

        else:

            until = (
                now
                + timedelta(
                    days=SUBSCRIPTION_DAYS
                )
            )

        users[user_id][
            "subscription_until"
        ] = until.isoformat()

        users[user_id][
            "free_used"
        ] = FREE_MESSAGES

        save_users()

        try:

            await context.bot.send_message(

                chat_id=int(user_id),

                text=(

                    "🎉 TO'LOV TASDIQLANDI!\n\n"

                    "✅ Obunangiz faollashtirildi.\n\n"

                    f"💎 Muddat: {SUBSCRIPTION_DAYS} kun\n"

                    f"📅 Tugash sanasi: "
                    f"{until.strftime('%d.%m.%Y %H:%M')}\n\n"

                    "🤖 Endi Aqilliyordam AI'dan "
                    "foydalanishingiz mumkin!"
                )
            )

        except Exception as e:

            logging.error(
                f"User xabar xatosi: {e}"
            )

        await query.edit_message_caption(

            caption=(
                query.message.caption
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "✅ TO'LOV TASDIQLANDI\n"
                f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi."
            ),

            reply_markup=None
        )

    # ========================================
    # REJECT
    # ========================================

    elif data.startswith("reject:"):

        user_id = data.split(":")[1]

        try:

            await context.bot.send_message(

                chat_id=int(user_id),

                text=(

                    "❌ To'lov chekingiz "
                    "tasdiqlanmadi.\n\n"

                    "Iltimos, chekni tekshirib "
                    "qaytadan yuboring.\n\n"

                    f"👨‍💻 Admin: {ADMIN_USERNAME}"
                )
            )

        except Exception as e:

            logging.error(
                f"Reject xatosi: {e}"
            )

        await query.edit_message_caption(

            caption=(
                query.message.caption
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "❌ TO'LOV RAD ETILDI."
            ),

            reply_markup=None
        )


# ============================================
# ADMIN OBUNA
# /activate USER_ID
# ============================================

async def activate(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
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
            "last_name": None,
            "referrals": [],
            "referred_by": None
        }

    until = (
        datetime.now()
        + timedelta(
            days=SUBSCRIPTION_DAYS
        )
    )

    users[user_id][
        "subscription_until"
    ] = until.isoformat()

    save_users()

    await update.message.reply_text(

        "✅ OBUNA FAOLLASHTIRILDI!\n\n"

        f"👤 User ID: {user_id}\n"
        f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi."
    )


# ============================================
# ADMIN USERS
# /users
# ============================================

async def show_users(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    if not users:

        await update.message.reply_text(
            "📭 Foydalanuvchilar yo'q."
        )

        return

    text = (
        f"👥 JAMI: {len(users)} TA FOYDALANUVCHI\n\n"
    )

    for number, (user_id, data) in enumerate(
        users.items(),
        1
    ):

        username = data.get(
            "username"
        )

        full_name = " ".join(
            x for x in [
                data.get("first_name"),
                data.get("last_name")
            ]
            if x
        )

        if not full_name:
            full_name = "Ism yo'q"

        if username:
            username_text = f"@{username}"
        else:
            username_text = "username yo'q"

        free_used = data.get(
            "free_used",
            0
        )

        referrals = len(
            data.get(
                "referrals",
                []
            )
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
                    status = "✅ Faol"
                else:
                    status = "❌ Tugagan"

            except Exception:

                status = "❌ Noma'lum"

        else:

            status = "❌ Obuna yo'q"

        text += (

            f"{number}. 👤 {full_name}\n"
            f"🆔 {user_id}\n"
            f"🔗 {username_text}\n"
            f"?
