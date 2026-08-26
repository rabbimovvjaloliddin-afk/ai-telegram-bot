import os
import asyncio
import logging
import tempfile
import shutil

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi!")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "🎥 Video yuborish",
                callback_data="video"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Yordam",
                callback_data="help"
            ),
            InlineKeyboardButton(
                "👨‍💻 Admin",
                callback_data="admin"
            )
        ],
    ]

    text = """
✨ ASSALOMU ALAYKUM! ✨

🎬 VIDEO CONVERTER BOT

Men videolaringizni tez va qulay
formatga aylantirib beraman.

📤 Video yuboring:

⭕ Dumaloq video
🎵 MP3 audio

⚡ Tez ishlaydi
🎯 Oddiy foydalanish
🤖 Avtomatik qayta ishlash

👇 Boshlash uchun tugmani bosing:
"""

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# BUTTONLAR
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if query.data == "video":

        await query.message.reply_text(
            "🎥 VIDEO YUBORING\n\n"
            "Videoni shu chatga yuboring.\n\n"
            "Men sizga:\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "qilib qaytaraman."
        )

    elif query.data == "help":

        await query.message.reply_text(
            "ℹ️ YORDAM\n\n"
            "1️⃣ Videoni botga yuboring.\n"
            "2️⃣ Bot videoni qayta ishlaydi.\n"
            "3️⃣ Dumaloq video va MP3 audio tayyor bo‘ladi.\n\n"
            "💡 Video yuborishning o‘zi kifoya."
        )

    elif query.data == "admin":

        await query.message.reply_text(
            "👨‍💻 ADMIN\n\n"
            "Savol yoki taklif bo‘lsa:\n"
            "@jaloliddino7"
        )


# ============================================================
# FFMPEG — DUMALOQ VIDEO
# ============================================================

async def create_round_video(
    input_path: str,
    output_path: str
):

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,

        # Markazdan kvadrat kesish
        "-vf",
        "crop=min(iw\\,ih):min(iw\\,ih),scale=640:640,setsar=1",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-movflags",
        "+faststart",

        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logging.error(
            stderr.decode(errors="ignore")
        )
        raise RuntimeError(
            "Dumaloq video yaratishda xatolik"
        )


# ============================================================
# FFMPEG — MP3 AUDIO
# ============================================================

async def create_audio(
    input_path: str,
    output_path: str
):

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,

        "-vn",

        "-codec:a",
        "libmp3lame",

        "-b:a",
        "192k",

        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logging.error(
            stderr.decode(errors="ignore")
        )
        raise RuntimeError(
            "Audio yaratishda xatolik"
        )


# ============================================================
# VIDEO QABUL QILISH
# ============================================================

async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if message.video:

        media = message.video

    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith(
            "video/"
        )
    ):

        media = message.document

    else:
        return

    status = await message.reply_text(
        "⏳ VIDEO QAYTA ISHLANMOQDA...\n\n"
        "🎬 Dumaloq video tayyorlanmoqda...\n"
        "🎵 Audio ajratilmoqda..."
    )

    temp_dir = tempfile.mkdtemp()

    input_path = os.path.join(
        temp_dir,
        "input.mp4"
    )

    round_path = os.path.join(
        temp_dir,
        "round.mp4"
    )

    audio_path = os.path.join(
        temp_dir,
        "audio.mp3"
    )

    try:

        # Telegramdan videoni olish
        telegram_file = await context.bot.get_file(
            media.file_id
        )

        await telegram_file.download_to_drive(
            input_path
        )

        # Bir vaqtning o‘zida ikkala faylni tayyorlash
        await asyncio.gather(
            create_round_video(
                input_path,
                round_path
            ),
            create_audio(
                input_path,
                audio_path
            ),
        )

        await status.edit_text(
            "✅ TAYYOR!\n\n"
            "📤 Fayllar yuborilmoqda..."
        )

        # ====================================================
        # DUMALOQ VIDEO
        # ====================================================

        with open(round_path, "rb") as round_video:

            await message.reply_video_note(
                video=round_video,
                length=640,
            )

        # ====================================================
        # AUDIO
        # ====================================================

        with open(audio_path, "rb") as audio:

            await message.reply_audio(
                audio=audio,
                title="Video audio",
                performer="Video Converter Bot",
                caption="🎵 Videodan ajratilgan audio"
            )

        await status.delete()

        await message.reply_text(
            "🎉 HAMMASI TAYYOR!\n\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "Yana video yuborishingiz mumkin."
        )

    except Exception as error:

        logging.exception(
            "Video processing error"
        )

        try:

            await status.edit_text(
                "❌ XATOLIK YUZ BERDI.\n\n"
                "Videoni boshqa formatda yuborib "
                "yana urinib ko‘ring."
            )

        except Exception:
            pass

    finally:

        # Vaqtinchalik fayllarni o‘chirish
        try:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )
        except Exception:
            pass


# ============================================================
# MATN
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🎥 Menga video yuboring.\n\n"
        "Men undan:\n\n"
        "⭕ Dumaloq video\n"
        "🎵 MP3 audio\n\n"
        "tayyorlab beraman."
    )


# ============================================================
# ERROR
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logging.error(
        "Bot error:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VIDEO
            | filters.Document.VIDEO,
            video_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "🤖 VIDEO CONVERTER BOT ISHLAYAPTI..."
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
