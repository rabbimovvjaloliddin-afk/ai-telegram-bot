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
    ContextTypes,
    filters
)
from anthropic import AsyncAnthropic


# ============================================================
# SOZLAMALAR
# ============================================================

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

SUBSCRIPTION_DAYS = 7

FREE_MESSAGES = 3

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

client = AsyncAnthropic(
    api_key=ANTHROPIC_API_KEY
)

SYSTEM_PROMPT = """
Siz Aqilliyordam AI nomli foydali AI yordamchisiz.

Foydalanuvchiga aniq, tushunarli va foydali javob bering.

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

Foydalanuvchi qaysi tilda yozsa, imkon qadar o'sha tilda javob bering.

Markdown belgilaridan imkon qadar foydalanmang.
"""


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
            "Database o'qishda xato: %s",
            e
        )

        return {}


users = load_users()


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
            "Database saqlashda xato: %s",
            e
        )


def default_user(user):

    return {

        "free_used": 0,

        "subscription_until": None,

        "username": user.username,

        "first_name": user.first_name,

        "last_name": user.last_name,

        "referrals": [],

        "referred_by": None,

        "balance": 0,

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

        defaults = default_user(user)

        for key, value in defaults.items():

            if key not in data:
                data[key] = value

    save_users()


def fmt_money(amount):

    return f"{int(amount):,}".replace(
        ",",
        " "
    )


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


def subscription_is_active(user_data):

    until_text = user_data.get(
        "subscription_until"
    )

    if not until_text:
        return False

    try:

        until = datetime.fromisoformat(
            until_text
        )

        return datetime.now() < until

    except Exception:

        return False


# ============================================================
# MENU
# ============================================================

def main_keyboard():

    return InlineKeyboardMarkup([

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


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = str(user.id)

    new_user = user_id not in users

    save_user_info(user)

    # ========================================================
    # REFERRAL
    # ========================================================

    if new_user and context.args:

        referral_id = context.args[0].strip()

        if referral_id.startswith("ref_"):

            referral_id = referral_id[4:]

        if (
            referral_id != user_id
            and referral_id in users
        ):

            ref_user = users[referral_id]

            referrals = ref_user.setdefault(
                "referrals",
                []
            )

            if user_id not in referrals:

                referrals.append(
                    user_id
                )

                ref_user["balance"] = (
                    int(
                        ref_user.get(
                            "balance",
                            0
                        )
                    )
                    + REFERRAL_REWARD
                )

                users[user_id][
                    "referred_by"
                ] = referral_id

                save_users()

                try:

                    await context.bot.send_message(

                        chat_id=int(
                            referral_id
                        ),

                        text=(

                            "🎉 YANGI DO'STINGIZ "
                            "QO'SHILDI!\n\n"

                            f"💰 +{fmt_money(REFERRAL_REWARD)} "
                            "so'm balansingizga qo'shildi.\n\n"

                            f"💳 Joriy balans: "
                            f"{fmt_money(ref_user['balance'])} so'm\n\n"

                            f"🔓 Minimal yechish: "
                            f"{fmt_money(MIN_WITHDRAW)} so'm"
                        )
                    )

                except Exception as e:

                    logging.error(
                        "Referral xabari xatosi: %s",
                        e
                    )

    # ========================================================
    # START MESSAGE
    # ========================================================

    await update.message.reply_text(

        "👋 Salom, "
        + (
            user.first_name
            or "do'stim"
        )
        + "!\n\n"

        "🤖 Aqilliyordam AI botiga "
        "xush kelibsiz!\n\n"

        "🧠 Men sizga yordam beraman:\n\n"

        "📝 Matn yozish\n"
        "📚 Insho yozish\n"
        "🤖 Telegram bot yaratish\n"
        "🧠 Test tuzish\n"
        "🌍 Tarjima\n"
        "📖 Dars va uy vazifalari\n"
        "💡 G'oya topish\n"
        "💻 Kod yozish\n"
        "❓ Turli savollarga javob\n\n"

        f"🆓 Sizda {FREE_MESSAGES} ta "
        "bepul savol bor.\n"

        f"💰 Har bir referral: "
        f"{fmt_money(REFERRAL_REWARD)} so'm\n"

        f"💸 Minimal yechish: "
        f"{fmt_money(MIN_WITHDRAW)} so'm\n\n"

        "👇 Menyudan foydalaning:",

        reply_markup=main_keyboard()
    )


# ============================================================
# BUY
# ============================================================

async def send_buy_message(message):

    await message.reply_text(

        "💎 AI YORDAM OBUNASI\n\n"

        f"📅 Muddat: "
        f"{SUBSCRIPTION_DAYS} kun\n"

        f"💰 Narx: "
        f"{WEEKLY_PRICE}\n\n"

        "💳 TO'LOV UCHUN KARTA:\n"

        f"{CARD_NUMBER}\n\n"

        "1️⃣ Kartaga to'lov qiling.\n"
        "2️⃣ Chekni shu botga yuboring.\n"
        "3️⃣ Admin to'lovni tekshiradi.\n"
        "4️⃣ Tasdiqlangach obuna faollashadi.\n\n"

        "📸 Chekni rasm yoki PDF qilib yuboring."
    )


async def buy(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await send_buy_message(
        update.message
    )


# ============================================================
# BALANCE
# ============================================================

async def send_balance(
    message,
    user_id
):

    data = users.get(
        user_id,
        {}
    )

    balance = int(
        data.get(
            "balance",
            0
        )
    )

    referrals = len(
        data.get(
            "referrals",
            []
        )
    )

    if balance >= MIN_WITHDRAW:

        status = (
            "✅ Pul chiqarishingiz mumkin!\n"
            "💳 Pul chiqarish tugmasini bosing."
        )

    else:

        status = (
            f"🔒 Yana "
            f"{fmt_money(MIN_WITHDRAW - balance)} "
            "so'm kerak."
        )

    await message.reply_text(

        "💰 SIZNING BALANSINGIZ\n\n"

        f"💵 Balans: "
        f"{fmt_money(balance)} so'm\n"

        f"👥 Takliflar: "
        f"{referrals} ta\n"

        f"💸 Minimal yechish: "
        f"{fmt_money(MIN_WITHDRAW)} so'm\n\n"

        f"{status}"
    )


async def balance_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    save_user_info(user)

    await send_balance(
        update.message,
        str(user.id)
    )


# ============================================================
# WITHDRAW
# ============================================================

async def request_withdraw(
    message,
    user_id
):

    data = users.get(
        user_id,
        {}
    )

    balance = int(
        data.get(
            "balance",
            0
        )
    )

    if balance < MIN_WITHDRAW:

        await message.reply_text(

            "❌ Pul chiqarish mumkin emas.\n\n"

            f"💰 Balans: "
            f"{fmt_money(balance)} so'm\n"

            f"🔒 Minimum: "
            f"{fmt_money(MIN_WITHDRAW)} so'm\n\n"

            f"Yana "
            f"{fmt_money(MIN_WITHDRAW - balance)} "
            "so'm yig'ing."
        )

        return

    if data.get(
        "withdrawal_pending",
        False
    ):

        await message.reply_text(

            "⏳ Sizda allaqachon pul "
            "chiqarish so'rovi mavjud.\n\n"

            "Admin tasdiqlashini kuting."
        )

        return

    data["withdrawal_pending"] = True

    data["withdrawal_card"] = None

    save_users()

    await message.reply_text(

        "💳 PUL CHIQARISH\n\n"

        f"💰 Balansingiz: "
        f"{fmt_money(balance)} so'm\n\n"

        "16 xonali karta raqamingizni yuboring.\n"

        "Masalan:\n"
        "8600123456789012"
    )


async def withdraw_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    save_user_info(user)

    await request_withdraw(
        update.message,
        str(user.id)
    )


# ============================================================
# WITHDRAW CARD
# ============================================================

async def handle_withdraw_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = str(user.id)

    if user_id not in users:
        return

    data = users[user_id]

    if not data.get(
        "withdrawal_pending",
        False
    ):
        return

    card_text = (
        update.message.text
        or ""
    ).strip()

    card = re.sub(
        r"\D",
        "",
        card_text
    )

    if len(card) != 16:

        await update.message.reply_text(

            "❌ Karta raqami noto'g'ri.\n\n"

            "16 xonali karta raqamini yuboring."
        )

        return

    balance = int(
        data.get(
            "balance",
            0
        )
    )

    if balance < MIN_WITHDRAW:

        data[
            "withdrawal_pending"
        ] = False

        data[
            "withdrawal_card"
        ] = None

        save_users()

        await update.message.reply_text(
            "❌ Balansingiz yetarli emas."
        )

        return

    data[
        "withdrawal_card"
    ] = card

    save_users()

    username = (

        f"@{user.username}"

        if user.username

        else "username yo'q"
    )

    full_name = " ".join(

        x

        for x in [
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

            "💸 YANGI PUL "
            "CHIQARISH SO'ROVI\n\n"

            f"👤 Ism: {full_name}\n"

            f"🔗 Username: {username}\n"

            f"🆔 User ID: {user_id}\n\n"

            f"💰 Summa: "
            f"{fmt_money(balance)} so'm\n"

            f"💳 Karta: {card}\n\n"

            "⏳ Pulni o'tkazib bo'lgach, "
            "TO'LANDI tugmasini bosing."
        ),

        reply_markup=keyboard
    )

    await update.message.reply_text(

        "✅ So'rovingiz adminga yuborildi.\n\n"

        f"💰 Summa: "
        f"{fmt_money(balance)} so'm\n"

        "⏳ To'lov tasdiqlanishini kuting."
    )


# ============================================================
# REFERRAL
# ============================================================

async def send_referral(
    message,
    context,
    user_id
):

    bot_username = context.bot.username

    if not bot_username:

        bot = await context.bot.get_me()

        bot_username = bot.username

    referral_link = (

        f"https://t.me/"
        f"{bot_username}"
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

    balance = int(
        data.get(
            "balance",
            0
        )
    )

    await message.reply_text(

        "👥 DO'STLARNI TAKLIF QILING\n\n"

        f"🎁 Har bir yangi foydalanuvchi "
        f"uchun +{fmt_money(REFERRAL_REWARD)} so'm!\n\n"

        "🔗 SIZNING TAKLIF HAVOLANGIZ:\n"

        f"{referral_link}\n\n"

        f"👥 Takliflar: "
        f"{count} ta\n"

        f"💰 Balans: "
        f"{fmt_money(balance)} so'm\n\n"

        f"💸 Minimal yechish: "
        f"{fmt_money(MIN_WITHDRAW)} so'm"
    )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = str(
        query.from_user.id
    )

    if user_id not in users:

        save_user_info(
            query.from_user
        )

    # BUY
    if query.data == "buy_menu":

        await send_buy_message(
            query.message
        )

    # REFERRAL
    elif query.data == "referral":

        await send_referral(
            query.message,
            context,
            user_id
        )

    # BALANCE
    elif query.data == "balance":

        await send_balance(
            query.message,
            user_id
        )

    # WITHDRAW
    elif query.data == "withdraw":

        await request_withdraw(
            query.message,
            user_id
        )

    # ADVERTISEMENT
    elif query.data == "advertisement":

        bot_username = context.bot.username

        if not bot_username:

            bot = await context.bot.get_me()

            bot_username = bot.username

        await query.message.reply_text(

            "📢 AQILLIYORDAM AI 🤖\n\n"

            "Savolingiz bormi? "
            "AI yordam beradi! 🚀\n\n"

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

            f"https://t.me/{bot_username}"
        )


# ============================================================
# TO'LOV CHEKI
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

        x

        for x in [
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

        "Tasdiqlangandan keyin "
        "obunangiz faollashadi."
    )


async def handle_receipt_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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


async def handle_receipt_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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
# ADMIN ACTIONS
# ============================================================

async def receipt_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

        user_id = data.split(
            ":",
            1
        )[1]

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

                    f"📅 Tugash: "
                    f"{until.strftime('%d.%m.%Y %H:%M')}\n\n"

                    "🤖 Endi Aqilliyordam AI'dan "
                    "foydalanishingiz mumkin!"
                )
            )

        except Exception as e:

            logging.error(
                "Approve user xabari xatosi: %s",
                e
            )

        try:

            old_caption = (
                query.message.caption
                or ""
            )

            await query.edit_message_caption(

                caption=(

                    old_caption
                    + "\n\n"
                    "━━━━━━━━━━━━━━\n"
                    "✅ TO'LOV TASDIQLANDI\n"
                    f"📅 {SUBSCRIPTION_DAYS} "
                    "kunlik obuna berildi."
                ),

                reply_markup=None
            )

        except Exception as e:

            logging.error(
                "Approve caption xatosi: %s",
                e
            )

    # ========================================================
    # OBUNA RAD
    # ========================================================

    elif data.startswith("reject:"):

        user_id = data.split(
            ":",
            1
        )[1]

        try:

            await context.bot.send_message(

                chat_id=int(user_id),

                text=(

                    "❌ To'lov chekingiz "
                    "tasdiqlanmadi.\n\n"

                    "Iltimos, chekni tekshirib "
                    "qaytadan yuboring.\n\n"

                    f"👨‍💻 Admin: "
                    f"{ADMIN_USERNAME}"
                )
            )

        except Exception as e:

            logging.error(
                "Reject user xatosi: %s",
                e
            )

        try:

            old_caption = (
                query.message.caption
                or ""
            )

            await query.edit_message_caption(

                caption=(

                    old_caption
                    + "\n\n"
                    "━━━━━━━━━━━━━━\n"
                    "❌ TO'LOV RAD ETILDI."
                ),

                reply_markup=None
            )

        except Exception as e:

            logging.error(
                "Reject caption xatosi: %s",
                e
            )

    # ========================================================
    # WITHDRAW PAID
    # ========================================================

    elif data.startswith(
        "withdraw_paid:"
    ):

        user_id = data.split(
            ":",
            1
        )[1]

        if user_id not in users:

            await query.edit_message_text(
                "❌ Foydalanuvchi topilmadi."
            )

            return

        user_data = users[user_id]

        amount = int(
            user_data.get(
                "balance",
                0
            )
        )

        if amount < MIN_WITHDRAW:

            user_data[
                "withdrawal_pending"
            ] = False

            user_data[
                "withdrawal_card"
            ] = None

            save_users()

            await query.edit_message_text(
                "❌ Balans minimum summadan kam."
            )

            return

        # To'lov tasdiqlanganda balans 0 bo'ladi
        user_data[
            "balance"
        ] = 0

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
                    f"{fmt_money(amount)} so'm\n\n"

                    "✅ To'lov tasdiqlandi.\n\n"

                    "🤖 Aqilliyordam AI'dan "
                    "foydalanishda davom etishingiz mumkin!"
                )
            )

        except Exception as e:

            logging.error(
                "Withdraw paid xatosi: %s",
                e
            )

        try:

            await query.edit_message_text(

                (
                    query.message.text
                    or ""
                )
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "✅ TO'LOV AMALGA OSHIRILDI"
            )

        except Exception as e:

            logging.error(
                "Withdraw paid edit xatosi: %s",
                e
            )

    # ========================================================
    # WITHDRAW REJECT
    # ========================================================

    elif data.startswith(
        "withdraw_reject:"
    ):

        user_id = data.split(
            ":",
            1
        )[1]

        if user_id not in users:

            await query.edit_message_text(
                "❌ Foydalanuvchi topilmadi."
            )

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

                    f"👨‍💻 Admin: "
                    f"{ADMIN_USERNAME}\n\n"

                    "Kerak bo'lsa qaytadan "
                    "so'rov yuboring."
                )
            )

        except Exception as e:

            logging.error(
                "Withdraw reject xatosi: %s",
                e
            )

        try:

            await query.edit_message_text(

                (
                    query.message.text
                    or ""
                )
                + "\n\n"
                "━━━━━━━━━━━━━━\n"
                "❌ SO'ROV RAD ETILDI"
            )

        except Exception as e:

            logging.error(
                "Withdraw reject edit xatosi: %s",
                e
            )


# ============================================================
# ADMIN ACTIVATE
# ============================================================

async def activate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    if not context.args:

        await update.message.reply_text(

            "❌ Foydalanish:\n"
            "/activate USER_ID"
        )

        return

    user_id = context.args[0]

    if user_id not in users:

        await update.message.reply_text(

            "❌ Bu foydalanuvchi hali "
            "botga kirmagan."
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

        f"📅 {SUBSCRIPTION_DAYS} kunlik "
        "obuna berildi.\n"

        f"⏰ Tugaydi: "
        f"{until.strftime('%d.%m.%Y %H:%M')}"
    )


# ============================================================
# ADMIN USERS
# ============================================================

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
            "📭 Foydalanuvchilar yo'q."
        )

        return

    text = (
        f"👥 JAMI: {len(users)} "
        "TA FOYDALANUVCHI\n\n"
    )

    for number, (
        user_id,
        data
    ) in enumerate(
        users.items(),
        1
    ):

        username = data.get(
            "username"
        )

        full_name = " ".join(

            x

            for x in [
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

        balance = int(
            data.get(
                "balance",
                0
            )
        )

        subscription = data.get(
            "subscription_until"
        )

        status = "❌ Obuna yo'q"

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

        item = (

            f"{number}. 👤 {full_name}\n"

            f"🆔 {user_id}\n"

            f"🔗 {username_text}\n"

            f"🆓 Bepul: "
            f"{free_used}/{FREE_MESSAGES}\n"

            f"👥 Referral: "
            f"{referrals} ta\n"

            f"💰 Balans: "
            f"{fmt_money(balance)} so'm\n"

            f"💎 Obuna: {status}\n\n"
        )

        if len(text) + len(item) > 3500:

            await update.message.reply_text(
                text
            )

            text = (
                "👥 DAVOMI:\n\n"
            )

        text += item

    if text.strip():

        await update.message.reply_text(
            text
        )


# ============================================================
# BARCHA ODDIY MATNLAR
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = str(
        user.id
    )

    save_user_info(user)

    data = users[user_id]

    # Karta kutilayotgan bo'lsa
    # AI ishlamaydi
    if data.get(
        "withdrawal_pending",
        False
    ):

        await handle_withdraw_card(
            update,
            context
        )

        return

    # Aks holda AI
    await handle_ai_message(
        update,
        context
    )


# ============================================================
# AI
# ============================================================

async def handle_ai_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(
        update.effective_user.id
    )

    user_text = (
        update.message.text
        or ""
    ).strip()

    if not user_text:
        return

    save_user_info(
        update.effective_user
    )

    user = users[user_id]

    subscription_active = (
        subscription_is_active(user)
    )

    # ========================================================
    # FREE LIMIT
    # ========================================================

    if (
        not subscription_active
        and
        user.get(
            "free_used",
            0
        ) >= FREE_MESSAGES
    ):

        await update.message.reply_text(

            "🔒 Bepul savollaringiz tugadi.\n\n"

            f"💎 Davom ettirish uchun "
            f"{SUBSCRIPTION_DAYS} kunlik "
            "obuna oling.\n\n"

            f"💰 Narx: {WEEKLY_PRICE}\n\n"

            "👉 /buy\n\n"

            "👥 Yoki do'stlaringizni "
            "taklif qilib pul yig'ing."
        )

        return

    # ========================================================
    # CLAUDE
    # ========================================================

    try:

        response = await client.messages.create(

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

        answer = ""

        for block in response.content:

            if getattr(
                block,
                "type",
                None
            ) == "text":

                answer += block.text

        answer = clean_markdown(
            answer
        )

        if not answer:

            answer = (
                "❌ AI javob qaytara olmadi. "
                "Qaytadan urinib ko'ring."
            )

        # Bepul savolni hisoblash
        if not subscription_active:

            user["free_used"] = (

                int(
                    user.get(
                        "free_used",
                        0
                    )
                )
                + 1
            )

        save_users()

        # Telegram 4096 belgidan
        # uzun xabarni qabul qilmaydi
        for i in range(
            0,
            len(answer),
            4000
        ):

            await update.message.reply_text(
                answer[i:i + 4000]
            )

    except Exception as e:

        logging.exception(
            "Claude xatosi: %s",
            e
        )

        await update.message.reply_text(

            "❌ AI bilan bog'lanishda "
            "xatolik yuz berdi.\n\n"

            "Birozdan keyin "
            "qayta urinib ko'ring."
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
                r"^(buy_menu|referral|balance|"
                r"withdraw|advertisement)$"
            )
        )
    )

    app.add_handler(
        CallbackQueryHandler(

            receipt_action,

            pattern=(
                r"^(approve|reject|"
                r"withdraw_paid|withdraw_reject):"
            )
        )
    )

    # ========================================================
    # BARCHA ODDIY MATNLAR UCHUN FAQAT BITTA HANDLER
    # ========================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    print(
        "Aqilliyordam AI bot ishga tushdi..."
    )

    app.run_polling()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
