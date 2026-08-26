import os
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable topilmadi!")

ADMIN_USERNAME = "@jaloliddino7"

# Telegram botlar uchun katta fayllar bilan ishlashda limitlar
MAX_FILE_SIZE = 20 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎥 Video yuborish", callback_data="convert")],
        [InlineKeyboardButton("📖 Qanday ishlaydi?", callback_data="help")],
        [InlineKeyboardButton("👨‍💻 Admin", callback_data="admin")],
    ]

    text = (
        "✨ <b>VIDEO CONVERTER</b> ✨\n\n"
        "Assalomu alaykum! 👋\n\n"
        "Men videoni avtomatik ravishda:\n\n"
        "⭕ <b>Dumaloq video</b>\n"
        "🎵 <b>MP3 audio</b>\n\n"
        "formatiga aylantirib beraman.\n\n"
        "📤 Videoni shu chatga yuboring.\n"
        "⚡ Qolganini men qilaman!"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# BUTTONS
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "convert":
        await query.message.reply_text(
            "🎥 <b>VIDEO YUBORING</b>\n\n"
            "Videoni shu chatga yuboring.\n\n"
            "Men sizga:\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "qilib beraman.",
            parse_mode="HTML",
        )

    elif query.data == "help":
        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ Videoni botga yuborasiz.\n\n"
            "2️⃣ Bot videoni qayta ishlaydi.\n\n"
            "3️⃣ ⭕ Dumaloq video tayyorlanadi.\n\n"
            "4️⃣ 🎵 Videodagi ovoz MP3 qilib chiqariladi.\n\n"
            "✅ Sizdan boshqa hech narsa talab qilinmaydi.",
            parse_mode="HTML",
        )

    elif query.data == "admin":
        await query.message.reply_text(
            f"👨‍💻 <b>ADMIN</b>\n\n"
            f"📩 Murojaat uchun: {ADMIN_USERNAME}",
            parse_mode="HTML",
        )


# ============================================================
# FFMPEG CHECK
# ============================================================

async def check_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")

    if not ffmpeg_path:
        raise RuntimeError(
            "FFmpeg topilmadi! Server muhitida ffmpeg o'rnatilmagan."
        )

    process = await asyncio.create_subprocess_exec(
        ffmpeg_path,
        "-version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await process.communicate()

    if process.returncode != 0:
        raise RuntimeError("FFmpeg ishlamayapti!")

    logger.info("FFmpeg muvaffaqiyatli topildi: %s", ffmpeg_path)


# ============================================================
# RUN FFMPEG
# ============================================================

async def run_ffmpeg(command):
    logger.info("FFmpeg ishga tushdi.")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_text = stderr.decode("utf-8", errors="ignore")
        logger.error("FFmpeg ERROR:\n%s", error_text)
        raise RuntimeError("FFmpeg videoni qayta ishlay olmadi.")

    logger.info("FFmpeg muvaffaqiyatli tugadi.")


# ============================================================
# CREATE ROUND VIDEO
# ============================================================

async def create_round_video(input_path: str, output_path: str):
    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf",
        "crop=min(iw\\,ih):min(iw\\,ih),scale=640:640:force_original_aspect_ratio=decrease,pad=640:640:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# CREATE MP3
# ============================================================

async def create_mp3(input_path: str, output_path: str):
    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# VIDEO HANDLER
# ============================================================

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.video:
        media = message.video
        file_size = media.file_size or 0
        duration = media.duration

    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("video/")
    ):
        media = message.document
        file_size = media.file_size or 0
        duration = None

    else:
        return

    if file_size > MAX_FILE_SIZE:
        await message.reply_text(
            "⚠️ <b>Video juda katta.</b>\n\n"
            "20 MB dan kichikroq video yuboring.",
            parse_mode="HTML",
        )
        return

    status = await message.reply_text(
        "⏳ <b>VIDEO QAYTA ISHLANMOQDA...</b>\n\n"
        "🎬 Dumaloq video tayyorlanmoqda...\n"
        "🎵 Audio ajratilmoqda...\n\n"
        "Iltimos, kuting.",
        parse_mode="HTML",
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="video_bot_"))

    input_path = temp_dir / "input.mp4"
    round_path = temp_dir / "round.mp4"
    audio_path = temp_dir / "audio.mp3"

    try:
        logger.info("Video qabul qilindi. File ID: %s", media.file_id)

        # DOWNLOAD
        telegram_file = await context.bot.get_file(media.file_id)
        await telegram_file.download_to_drive(custom_path=str(input_path))

        if not input_path.exists():
            raise RuntimeError("Video serverga yuklanmadi.")

        logger.info("Video yuklandi: %s bytes", input_path.stat().st_size)

        # FFMPEG
        await status.edit_text(
            "⚙️ <b>QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "Deyarli tayyor...",
            parse_mode="HTML",
        )

        await asyncio.gather(
            create_round_video(str(input_path), str(round_path)),
            create_mp3(str(input_path), str(audio_path)),
        )

        # CHECK OUTPUT
        if not round_path.exists():
            raise RuntimeError("Dumaloq video yaratilmagan.")

        if not audio_path.exists():
            raise RuntimeError("MP3 audio yaratilmagan.")

        logger.info("Output fayllar tayyor.")

        await status.edit_text(
            "✅ <b>TAYYOR!</b>\n\n"
            "📤 Fayllar yuborilmoqda...",
            parse_mode="HTML",
        )

        # ROUND VIDEO
        with open(round_path, "rb") as video_file:
            await message.reply_video_note(
                video=video_file,
                duration=duration,
                length=640,
            )

        # MP3
        with open(audio_path, "rb") as audio_file:
            await message.reply_audio(
                audio=audio_file,
                title="Video Audio",
                performer="Video Converter",
                caption="🎵 Videodan ajratilgan audio",
            )

        # FINISH
        await status.delete()

        await message.reply_text(
            "🎉 <b>TAYYOR!</b>\n\n"
            "⭕ Dumaloq video — tayyor\n"
            "🎵 MP3 audio — tayyor\n\n"
            "📤 Yana video yuborishingiz mumkin.",
            parse_mode="HTML",
        )

    except Exception as error:
        logger.exception("VIDEO PROCESSING ERROR")

        error_message = str(error)

        await status.edit_text(
            "❌ <b>XATOLIK</b>\n\n"
            "Videoni qayta ishlashning iloji bo'lmadi.\n\n"
            f"🔎 <code>{error_message[:500]}</code>",
            parse_mode="HTML",
        )

    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 <b>VIDEO YUBORING</b>\n\n"
        "Videoni shu chatga yuboring.\n\n"
        "⭕ Dumaloq video\n"
        "🎵 MP3 audio\n\n"
        "avtomatik tayyorlanadi.",
        parse_mode="HTML",
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram bot xatosi:", exc_info=context.error)


# ============================================================
# MAIN
# ============================================================

async def post_init(application: Application):
    await check_ffmpeg()

    logger.info("====================================")
    logger.info("VIDEO CONVERTER BOT ISHGA TUSHDI")
    logger.info("====================================")


def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            video_handler,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Bot polling boshlanmoqda...")

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
