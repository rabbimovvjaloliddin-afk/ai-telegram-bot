import os
import re
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


# ============================================================
# SOZLAMALAR
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

ADMIN_ID = 6078096693
ADMIN_USERNAME = "@jaloliddino7"

# AI OBUNA TO'LOVI
CARD_NUMBER = os.environ.get(
    "CARD_NUMBER",
    "5614 6818 1198 0360"
)

WEEKLY_PRICE = os.environ.get(
    "WEEKLY_PRICE",
    "10 000 so'm"
)

SUBSCRIPTION_DAYS = 7

# BEPUL AI
FREE_MESSAGES = 3

# REFERRAL
REFERRAL_REWARD = 1500
MIN_WITHDRAW = 10000

DATA_FILE = "users.json"


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# AI
# ============================================================

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
- Kod yozish
- Kodni tushuntirish
- Turli savollarga javob berish

Javoblarni o'zbek tilida bering, agar foydalanuvchi boshqa tilni so'rasa,
o'sha tilda javob berishingiz mumkin.

Markdown belgilaridan foydalanmang.
Oddiy matn, emoji va yangi qatorlardan foydalaning.
"""


client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)


# ============================================================
# MARKDOWN TOZALASH
# ============================================================

def clean_markdown(text):

    if not text:
        return ""

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


# ============================================================
# DATABASE
# ============================================================

def load_users():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

            return {}

    except Exception as e:

        logging.error(
            f"Database o'qishda xato: {e}"
        )

        return {}


def save_users():

    try:

        temp_file = DATA_FILE + ".tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

    except Exception as e:

        logging.error(
            f"Database saqlashda xato: {e}"
        )


users = load_users()


# ============================================================
# USER MA'LUMOTLARI
# ============================================================

def default_user(user):

    return {
        "free_used": 0,

        "subscription_until": None,

        "username": user.username,

        "first_name": user.first_name,

        "last_name": user.last_name,

        "referrals": [],

        "referred_by": None,

        # Referral balansi
        "balance": 0,

        # Pul chiqarish
        "withdrawal_card": None,

        "withdrawal_pending": False
    }


def save_user_info(user):

    user_id = str(user.id)

    if user_id not in users:

        users[user_id] = default_user(user)

    else:

        data = users[user_id]

        data["username"] = user.username
        data["first_name"] = user.first_name
        data["last_name"] = user.last_name

        if "free_used" not in data:
            data["free_used"] = 0

        if "subscription_until" not in data:
            data["subscription_until"] = None

        if "referrals" not in data:
            data["referrals"] = []

        if "referred_by" not in data:
            data["referred_by"] = None

        if "balance" not in data:
            data["balance"] = 0

        if "withdrawal_card" not in data:
            data["withdrawal_card"] = None

        if "withdrawal_pending" not in data:
            data["withdrawal_pending"] = False

    save_users()


# ============================================================
# START
# ============================================================

async def start(update, context):

    user = update.effective_user

    user_id = str(user.id)

    new_user = user_id not in users

    save_user_info(user)

    # ========================================================
    # REFERRAL
    # ========================================================

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

                # 1500 so'm qo'shish
                old_balance = ref_user.get(
                    "balance",
                    0
                )

                new_balance = (
                    old_balance
                    + REFERRAL_REWARD
                )

                ref_user["balance"] = new_balance

                users[user_id]["referred_by"] = (
                    referral_id
                )

                save_users()

                try:

                    await context.bot.send_message(

                        chat_id=int(referral_id),

                        text=(
                            "🎉 YANGI DO'STINGIZ QO'SHILDI!\n\n"

                            f"💰 +{REFERRAL_REWARD:,} so'm "
                            "balansingizga qo'shildi.\n\n"

                            f"💳 Joriy balans: "
                            f"{new_balance:,} so'm\n\n"

                            f"🔓 Minimal yechish: "
                            f"{MIN_WITHDRAW:,} so'm"
                        ).replace(",", " ")
                    )

                except Exception as e:

                    logging.error(
                        f"Referral xatosi: {e}"
                    )

    # ========================================================
    # MENU
    # ========================================================

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
                "💰 BALANS",
                callback_data="balance"
            )
        ],

        [
            InlineKeyboardButton(
                "💸 PUL CHIQARISH",
                callback_data="withdraw"
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

        "🧠 Men sizga quyidagilarda yordam beraman:\n\n"

        "📝 Matn yozish\n"
        "📚 Insho yozish\n"
        "🤖 Telegram bot yaratish\n"
        "🧠 Test tuzish\n"
        "🌍 Tarjima\n"
        "📖 Dars va uy vazifalari\n"
        "💡 G'oya topish\n"
        "💻 Kod yozish\n"
        "❓ Turli savollarga javob\n\n"

        f"🆓 Sizda {FREE_MESSAGES} ta bepul savol bor.\n"
        f"💰 Referral uchun: {REFERRAL_REWARD:,} so'm\n"
        f"💸 Minimal yechish: {MIN_WITHDRAW:,} so'm\n\n"

        "👇 Menyudan foydalaning:"
    ).replace(",", " ")

    # Tugmalarni alohida yuboramiz
    await update.message.reply_text(
        "👇 Tanlang:",
        reply_markup=keyboard
    )


# ============================================================
# BUY
# ============================================================

async def send_buy_message(message):

    await message.reply_text(

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


async def buy(update, context):

    await send_buy_message(
        update.message
    )


# ============================================================
# BALANCE
# ============================================================

async def balance_command(update, context):

    user = update.effective_user

    save_user_info(user)

    user_id = str(user.id)

    balance = users[user_id].get(
        "balance",
        0
    )

    referrals = len(
        users[user_id].get(
            "referrals",
            []
        )
    )

    text = (

        "💰 SIZNING BALANSINGIZ\n\n"

        f"💵 Balans: {balance:,} so'm\n"
        f"👥 Takliflar: {referrals} ta\n\n"

        f"💸 Minimal yechish: "
        f"{MIN_WITHDRAW:,} so'm\n\n"
    )

    if balance >= MIN_WITHDRAW:

        text += (
            "✅ Pul chiqarishingiz mumkin!\n\n"
            "💳 /withdraw buyrug'ini bosing."
        )

    else:

        remaining = (
            MIN_WITHDRAW - balance
        )

        text += (
            f"🔒 Yana {remaining:,} so'm kerak."
        )

    await update.message.reply_text(
        text.replace(",", " ")
    )


# ============================================================
# WITHDRAW
# ============================================================

async def withdraw_command(update, context):

    user = update.effective_user

    save_user_info(user)

    user_id = str(user.id)

    user_data = users[user_id]

    balance = user_data.get(
        "balance",
        0
    )

    if balance < MIN_WITHDRAW:

        remaining = (
            MIN_WITHDRAW - balance
        )

        await update.message.reply_text(

            "❌ Pul chiqarish mumkin emas.\n\n"

            f"💰 Balans: {balance:,} so'm\n"
            f"🔒 Minimum: {MIN_WITHDRAW:,} so'm\n\n"

            f"Yana {remaining:,} so'm yig'ing."
        ).replace(",", " ")

        return

    if user_data.get(
        "withdrawal_pending",
        False
    ):

        await update.message.reply_text(

            "⏳ Sizda allaqachon pul chiqarish "
            "so'rovi mavjud.\n\n"

            "Admin tasdiqlashini kuting."
        )

        return

    user_data["withdrawal_pending"] = True

    save_users()

    await update.message.reply_text(

        "💳 PUL CHIQARISH\n\n"

        f"💰 Sizning balansingiz: "
        f"{balance:,} so'm\n\n"

        "Karta raqamingizni yuboring.\n\n"

        "Masalan:\n"
        "8600123456789012\n\n"

        "⚠️ Faqat pul qabul qiladigan "
        "o'zingizga tegishli karta raqamini yuboring."
    ).replace(",", " ")


# ============================================================
# WITHDRAW CARD
# ============================================================

async def handle_withdraw_card(update, context):

    user = update.effective_user

    user_id = str(user.id)

    if user_id not in users:
        return

    user_data = users[user_id]

    if not user_data.get(
        "withdrawal_pending",
        False
    ):
        return

    card_text = update.message.text.strip()

    card = re.sub(
        r"[^0-9]",
        "",
        card_text
    )

    # Oddiy 16 xonali tekshiruv
    if len(card) != 16:

        await update.message.reply_text(

            "❌ Karta raqami noto'g'ri.\n\n"

            "16 xonali karta raqamini yuboring.\n\n"

            "Masalan:\n"
            "8600123456789012"
        )

        return

    balance = user_data.get(
        "balance",
        0
    )

    if balance < MIN_WITHDRAW:

        user_data["withdrawal_pending"] = False

        save_users()

        await update.message.reply_text(
            "❌ Balansingiz yetarli emas."
        )

        return

    user_data["withdrawal_card"] = card

    save_users()

    username = (
        f"@{user.username}"
        if user.username
        else "username yo'q"
    )

    full_name = " ".join(
        x for x in [
            user.first_name,
            user.last_name
        ]
        if x
    )

    if not full_name:
        full_name = "Ism yo'q"

    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ TO'LANDI",
                callback_data=(
                    f"withdraw_paid:{user_id}"
                )
            ),

            InlineKeyboardButton(
                "❌ RAD ETISH",
                callback_data=(
                    f"withdraw_reject:{user_id}"
                )
            )

        ]

    ])

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 YANGI PUL CHIQARISH SO'ROVI\n\n"

            f"👤 Ism: {full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 User ID: {user_id}\n\n"

            f"💰 Summa: {balance:,} so'm\n"
            f"💳 Karta: {card}\n\n"

            "⏳ To'lovni amalga oshirib, "
            "TO'LANDI tugmasini bosing."
        ).replace(",", " "),

        reply_markup=keyboard
    )

    await update.message.reply_text(

        "✅ So'rovingiz adminga yuborildi.\n\n"

        f"💰 Summa: {balance:,} so'm\n"
        "⏳ To'lov tasdiqlanishini kuting."
    )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(update, context):

    query = update.callback_query

    await query.answer()

    user_id = str(
        query.from_user.id
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if query.data == "buy_menu":

        await send_buy_message(
            query.message
        )

    # --------------------------------------------------------
    # REFERRAL
    # --------------------------------------------------------

    elif query.data == "referral":

        bot_username = (
            context.bot.username
        )

        referral_link = (
            f"https://t.me/{bot_username}"
            f"?start=ref_{user_id}"
        )

        data = users.get(
            user_id,
            {}
        )

        count = len(
            data.get(
                "referrals",
                []
            )
        )

        balance = data.get(
            "balance",
            0
        )

        await query.message.reply_text(

            "👥 DO'STLARNI TAKLIF QILING\n\n"

            f"🎁 Har bir yangi foydalanuvchi "
            f"uchun +{REFERRAL_REWARD:,} so'm!\n\n"

            "🔗 SIZNING TAKLIF HAVOLANGIZ:\n\n"

            f"{referral_link}\n\n"

            f"👥 Takliflar: {count} ta\n"
            f"💰 Balans: {balance:,} so'm\n\n"

            f"💸 Minimal yechish: "
            f"{MIN_WITHDRAW:,} so'm"
        ).replace(",", " ")

    # --------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------

    elif query.data == "balance":

        data = users.get(
            user_id,
            {}
        )

        balance = data.get(
            "balance",
            0
        )

        referrals = len(
            data.get(
                "referrals",
                []
            )
        )

        if balance >= MIN_WITHDRAW:

            status = (
                "✅ Pul chiqarish mumkin!\n\n"
                "💳 /withdraw buyrug'ini bosing."
            )

        else:

            remaining = (
                MIN_WITHDRAW - balance
            )

            status = (
                f"🔒 Yana {remaining:,} so'm kerak."
            )

        await query.message.reply_text(

            "💰 BALANS\n\n"

            f"💵 Balans: {balance:,} so'm\n"
            f"👥 Referral: {referrals} ta\n"
            f"💸 Minimum: {MIN_WITHDRAW:,} so'm\n\n"

            f"{status}"
        ).replace(",", " ")

    # --------------------------------------------------------
    # WITHDRAW
    # --------------------------------------------------------

    elif query.data == "withdraw":

        data = users.get(
            user_id,
            {}
        )

        balance = data.get(
            "balance",
            0
        )

        if balance < MIN_WITHDRAW:

            remaining = (
                MIN_WITHDRAW - balance
            )

            await query.message.reply_text(

                "❌ Hali pul chiqarish mumkin emas.\n\n"

                f"💰 Balans: {balance:,} so'm\n"
                f"🔒 Minimum: {MIN_WITHDRAW:,} so'm\n\n"

                f"Yana {remaining:,} so'm kerak."
            ).replace(",", " ")

            return

        if data.get(
            "withdrawal_pending",
            False
        ):

            await query.message.reply_text(
                "⏳ So'rovingiz allaqachon adminga yuborilgan."
            )

            return

        data["withdrawal_pending"] = True

        save_users()

        await query.message.reply_text(

            "💳 KARTA RAQAMINGIZNI YUBORING\n\n"

            f"💰 Yechiladigan summa: "
            f"{balance:,} so'm\n\n"

            "16 xonali karta raqamingizni yuboring."
        ).replace(",", " ")

    # --------------------------------------------------------
    # ADVERTISEMENT
    # --------------------------------------------------------

    elif query.data == "advertisement":

        bot_username = (
            context.bot.username
        )

        advertisement = (

            "📢 AQILLIYORDAM AI 🤖\n\n"

            "Savolingiz bormi? AI yordam beradi! 🚀\n\n"

            "📝 Matn yozish\n"
            "📚 Insho yozish\n"
            "🤖 Telegram bot yaratish\n"
            "🧠 Test tuzish\n"
            "🌍 Tarjima\n"
            "📖 Dars va uy vazifalari\n"
            "💡 G'oya topish\n"
            "💻 Kod yozish\n"
            "❓ Turli savollarga javob\n\n"

            "🎁 Yangi foydalanuvchiga "
            "3 ta savol BEPUL!\n\n"

            "👇 Hozir sinab ko'ring:\n"

            f"https://t.me/{bot_username}"
        )

        await query.message.reply_text(
            advertisement
        )


# ============================================================
# RECEIPT ADMIN
# ============================================================

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
                callback_data=(
                    f"approve:{user_id}"
                )
            ),

            InlineKeyboardButton(
                "❌ RAD ETISH",
                callback_data=(
                    f"reject:{user_id}"
                )
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


# ============================================================
# PHOTO RECEIPT
# ============================================================

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


# ============================================================
# PDF RECEIPT
# ============================================================

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


# ============================================================
# ADMIN RECEIPT ACTION
# ============================================================

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

    # ========================================================
    # OBUNA TASDIQLASH
    # ========================================================

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
                "referred_by": None,
                "balance": 0,
                "withdrawal_card": None,
                "withdrawal_pending": False
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

                    f"💎 Muddat: "
                    f"{SUBSCRIPTION_DAYS} kun\n"

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

        try:

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

        except Exception as e:

            logging.error(
                f"Caption edit xatosi: {e}"
            )

    # ========================================================
    # OBUNA RAD
    # ========================================================

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

        try:

            await query.edit_message_caption(

                caption=(
                    query.message.caption
                    + "\n\n"
                    "━━━━━━━━━━━━━━\n"
                    "❌ TO'LOV RAD ETILDI."
                ),

                reply_markup=None
            )

        except Exception as e:

            logging.error(
                f"Caption edit xatosi: {e}"
            )

    # ========================================================
    # REFERRAL PULI TO'LANDI
    # ========================================================

    elif data.startswith("withdraw_paid:"):

        user_id = data.split(":")[1]

        if user_id not in users:

            await query.edit_message_text(
                "❌ Foydalanuvchi topilmadi."
            )

            return

        user_data = users[user_id]

        amount = user_data.get(
            "balance",
            0
        )

        if amount < MIN_WITHDRAW:

            user_data["withdrawal_pending"] = False

            save_users()

            await query.edit_message_text(
                "❌ Balans minimum summadan kam."
            )

            return

        # Balansni nol qilamiz
        user_data["balance"] = 0

        user_data[
            "withdrawal_card"
        ] = None

        user_data[
            "withdrawal_pending"
        ] = False

        save_users()

        try:

            await context.bot.send_message(

                chat_id=int(user_id),

                text=(

                    "🎉 PULINGIZ TO'LANDI!\n\n"

                    f"💰 To'langan summa: "
                    f"{amount:,} so'm\n\n"

                    "✅ To'lov tasdiqlandi.\n\n"

                    "🤖 Aqilliyordam AI'dan "
                    "foydalanishda davom etishingiz mumkin!"
                ).replace(",", " ")
            )

        except Exception as e:

            logging.error(
                f"Withdraw paid xatosi: {e}"
            )

        try:

            await query.edit_message_text(

                query.message.text
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "✅ TO'LOV AMALGA OSHIRILDI"
            )

        except Exception as e:

            logging.error(
                f"Withdraw edit xatosi: {e}"
            )

    # ========================================================
    # REFERRAL PULI RAD
    # ========================================================

    elif data.startswith("withdraw_reject:"):

        user_id = data.split(":")[1]

        if user_id not in users:

            return

        user_data = users[user_id]

        user_data[
            "withdrawal_card"
        ] = None

        user_data[
            "withdrawal_pending"
        ] = False

        # Balans saqlanib qoladi
        save_users()

        try:

            await context.bot.send_message(

                chat_id=int(user_id),

                text=(

                    "❌ Pul chiqarish so'rovingiz "
                    "rad etildi.\n\n"

                    "💰 Balansingiz saqlanib qoldi.\n\n"

                    f"👨‍💻 Admin: {ADMIN_USERNAME}\n"

                    "Kerak bo'lsa qaytadan so'rov yuboring."
                )
            )

        except Exception as e:

            logging.error(
                f"Withdraw reject xatosi: {e}"
            )

        try:

            await query.edit_message_text(

                query.message.text
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "❌ SO'ROV RAD ETILDI"
            )

        except Exception as e:

            logging.error(
                f"Withdraw reject edit xatosi: {e}"
            )


# ============================================================
# ADMIN ACTIVATE
# ============================================================

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

        await update.message.reply_text(
            "❌ Bu foydalanuvchi hali botga kirmagan."
        )

        return

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
        f"📅 {SUBSCRIPTION_DAYS} kunlik obuna berildi.\n"
        f"⏰ Tugaydi: "
        f"{until.strftime('%d.%m.%Y %H:%M')}"
    )


# ============================================================
# ADMIN USERS
# ============================================================

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

        username_text = (
            f"@{username}"
            if username
            else "username yo'q"
        )

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

        balance = data.get(
            "balance",
            0
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
            f"🆓 Bepul: {free_used}/{FREE_MESSAGES}\n"
            f"👥 Referral: {referrals} ta\n"
            f"💰 Balans: {balance:,} so'm\n"
            f"💎 Obuna: {status}\n\n"
        ).replace(",", " ")

        if len(text) > 3500:

            await update.message.reply_text(
                text
            )

            text = "👥 DAVOMI:\n\n"

    if text.strip():

        await update.message.reply_text(
            text
        )


# ============================================================
# AI MESSAGE
# ============================================================

async def handle_message(
    update,
    context
):

    user_id = str(
        update.effective_user.id
    )

    user_text = update.message.text

    save_user_info(
        update.effective_user
    )

    user = users[user_id]

    # ========================================================
    # OBUNA TEKSHIRISH
    # ========================================================

    subscription_active = False

    subscription_until = user.get(
        "subscription_until"
    )

    if subscription_until:

        try:

            until = datetime.fromisoformat(
                subscription_until
            )

            if datetime.now() < until:

                subscription_active = True

        except Exception:

            subscription_active = False

    # ========================================================
    # FREE LIMIT
    # ========================================================

    if not subscription_active:

        if user.get(
            "free_used",
            0
        ) >= FREE_MESSAGES:

            await update.message.reply_text(

                "🔒 Bepul savollaringiz tugadi.\n\n"

                "💎 Davom ettirish uchun "
                f"{SUBSCRIPTION_DAYS} kunlik obuna oling.\n\n"

                f"💰 Narx: {WEEKLY_PRICE}\n\n"

                "👉 /buy\n\n"

                "👥 Yoki do'stlaringizni taklif qilib "
                "pul yig'ing."
            )

            return

    # ========================================================
    # CLAUDE
    # ========================================================

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

        answer = clean_markdown(
            answer
        )

        # Faqat bepul foydalanuvchining savolini hisoblaymiz
        if not subscription_active:

            user["free_used"] = (
                user.get(
                    "free_used",
                    0
                ) + 1
            )

        save_users()

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        logging.error(
            f"Claude xatosi: {e}"
        )

        await update.message.reply_text(

            "❌ Kechirasiz, AI bilan bog'lanishda "
            "xatolik yuz berdi.\n\n"

            "Birozdan keyin qayta urinib ko'ring."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    app = (
        Application.builder()
        .token(
            TELEGRAM_BOT_TOKEN
        )
        .build()
    )

    # ========================================================
    # COMMANDS
    # ========================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "buy",
            buy
        )
    )

    app.add_handler(
        CommandHandler(
            "balance",
            balance_command
        )
    )

    app.add_handler(
        CommandHandler(
            "withdraw",
            withdraw_command
        )
    )

    app.add_handler(
        CommandHandler(
            "activate",
            activate
        )
    )

    app.add_handler(
        CommandHandler(
            "users",
            show_users
        )
    )

    # ========================================================
    # RECEIPTS
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_receipt_photo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_receipt_document
        )
    )

    # ========================================================
    # BUTTONS
    # ========================================================

    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern=(
                "^(buy_menu|referral|balance|"
                "withdraw|advertisement)$"
            )
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            receipt_action,
            pattern=(
                "^(approve|reject|"
                "withdraw_paid|withdraw_reject):"
            )
        )
    )

    # ========================================================
    # KARTA RAQAMI
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_withdraw_card
        )
    )

    # ========================================================
    # AI
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "Aqilliyordam AI bot ishga tushdi..."
    )

    app.run_polling()


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()
