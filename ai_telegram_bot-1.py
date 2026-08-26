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
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable topilmadi!"
    )

ADMIN_USERNAME = "@jaloliddino7"

# Maksimal fayl hajmi: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# Maksimal video davomiyligi: 25 soniya
MAX_DURATION = 25

# Output video o'lchami
VIDEO_SIZE = 640

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
        [
            InlineKeyboardButton(
                "🎥 Video yuborish",
                callback_data="convert"
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Qanday ishlaydi?",
                callback_data="help"
            )
        ],
        [
            InlineKeyboardButton(
                "👨‍💻 Admin",
                callback_data="admin"
            )
        ],
    ]

    text = (
        "✨ <b>VIDEO CONVERTER</b> ✨\n\n"
        "Assalomu alaykum! 👋\n\n"
        "Men videoni avtomatik ravishda:\n\n"
        "⭕ <b>Dumaloq video</b>\n"
        "🎵 <b>MP3 audio</b>\n\n"
        "formatiga aylantirib beraman.\n\n"
        "📌 <b>Limitlar:</b>\n"
        "⏱ Maksimal davomiylik: <b>25 soniya</b>\n"
        "📦 Maksimal hajm: <b>20 MB</b>\n\n"
        "📤 Videoni shu chatga yuboring."
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


# ============================================================
# BUTTONS
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    if query.data == "convert":

        await query.message.reply_text(
            "🎥 <b>VIDEO YUBORING</b>\n\n"
            "Videoni shu chatga yuboring.\n\n"
            "⏱ Maksimal: <b>25 soniya</b>\n"
            "📦 Maksimal: <b>20 MB</b>\n\n"
            "Bot avtomatik ravishda:\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "tayyorlaydi.",
            parse_mode="HTML",
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ Videoni botga yuborasiz.\n\n"
            "2️⃣ Bot video hajmi va davomiyligini tekshiradi.\n\n"
            "3️⃣ Video mos bo'lsa, qayta ishlanadi.\n\n"
            "4️⃣ ⭕ Dumaloq video tayyorlanadi.\n\n"
            "5️⃣ 🎵 MP3 audio ajratiladi.\n\n"
            "6️⃣ Tayyor fayllar sizga yuboriladi.\n\n"
            "📌 Limit: 25 soniya / 20 MB.",
            parse_mode="HTML",
        )

    elif query.data == "admin":

        await query.message.reply_text(
            "👨‍💻 <b>ADMIN</b>\n\n"
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
            "FFmpeg topilmadi! Serverga FFmpeg o'rnatilishi kerak."
        )

    process = await asyncio.create_subprocess_exec(
        ffmpeg_path,
        "-version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            "FFmpeg topildi, lekin ishlamayapti!"
        )

    logger.info(
        "FFmpeg muvaffaqiyatli topildi: %s",
        ffmpeg_path
    )


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

        error_text = stderr.decode(
            "utf-8",
            errors="ignore"
        )

        logger.error(
            "FFmpeg ERROR:\n%s",
            error_text
        )

        raise RuntimeError(
            "FFmpeg videoni qayta ishlay olmadi."
        )

    logger.info(
        "FFmpeg muvaffaqiyatli tugadi."
    )


# ============================================================
# CREATE ROUND VIDEO
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

        "-vf",
        (
            "crop=min(iw\\,ih):min(iw\\,ih),"
            "scale=640:640:force_original_aspect_ratio=decrease,"
            "pad=640:640:(ow-iw)/2:(oh-ih)/2"
        ),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-movflags",
        "+faststart",

        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# CREATE MP3
# ============================================================

async def create_mp3(
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

    await run_ffmpeg(command)


# ============================================================
# GET VIDEO DURATION USING FFMPEG
# ============================================================

async def get_video_duration(
    input_path: str
):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]

    try:

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning(
                "ffprobe ishlamadi."
            )
            return None

        result = stdout.decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not result:
            return None

        return float(result)

    except Exception:
        logger.exception(
            "Video duration aniqlashda xatolik."
        )
        return None


# ============================================================
# VIDEO HANDLER
# ============================================================

async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if not message:
        return

    media = None
    file_size = 0
    telegram_duration = None

    # --------------------------------------------------------
    # NORMAL VIDEO
    # --------------------------------------------------------

    if message.video:

        media = message.video

        file_size = media.file_size or 0

        telegram_duration = media.duration or 0

    # --------------------------------------------------------
    # VIDEO AS DOCUMENT
    # --------------------------------------------------------

    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("video/")
    ):

        media = message.document

        file_size = media.file_size or 0

    else:
        return

    # ========================================================
    # FILE SIZE CHECK
    # ========================================================

    if file_size > MAX_FILE_SIZE:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
            "📦 Maksimal hajm: <b>20 MB</b>\n\n"
            "Iltimos, 20 MB dan kichik video yuboring.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # QUICK TELEGRAM DURATION CHECK
    # ========================================================

    if telegram_duration and telegram_duration > MAX_DURATION:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
            f"⏱ Maksimal davomiylik: <b>{MAX_DURATION} soniya</b>\n\n"
            "Iltimos, 25 soniyadan qisqaroq video yuboring.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # STATUS
    # ========================================================

    status = await message.reply_text(
        "⏳ <b>VIDEO TEKSHIRILMOQDA...</b>\n\n"
        "📦 Hajmi tekshirilmoqda...\n"
        "⏱ Davomiyligi tekshirilmoqda...",
        parse_mode="HTML",
    )

    # ========================================================
    # TEMP DIRECTORY
    # ========================================================

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="video_bot_"
        )
    )

    input_path = temp_dir / "input.mp4"
    round_path = temp_dir / "round.mp4"
    audio_path = temp_dir / "audio.mp3"

    try:

        logger.info(
            "Video qabul qilindi. File ID: %s",
            media.file_id
        )

        # ====================================================
        # DOWNLOAD
        # ====================================================

        telegram_file = await context.bot.get_file(
            media.file_id
        )

        await telegram_file.download_to_drive(
            custom_path=str(input_path)
        )

        if not input_path.exists():

            raise RuntimeError(
                "Video serverga yuklanmadi."
            )

        actual_size = input_path.stat().st_size

        logger.info(
            "Video yuklandi: %s bytes",
            actual_size
        )

        # ====================================================
        # SECOND FILE SIZE CHECK
        # ====================================================

        if actual_size > MAX_FILE_SIZE:

            await status.edit_text(
                "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
                "📦 Maksimal hajm: <b>20 MB</b>\n\n"
                "Iltimos, kichikroq video yuboring.",
                parse_mode="HTML",
            )

            return

        # ====================================================
        # DOCUMENT VIDEO DURATION CHECK
        # ====================================================

        if not telegram_duration:

            detected_duration = await get_video_duration(
                str(input_path)
            )

            if detected_duration is not None:

                logger.info(
                    "Aniqlangan duration: %.2f",
                    detected_duration
                )

                if detected_duration > MAX_DURATION:

                    await status.edit_text(
                        "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                        f"⏱ Maksimal davomiylik: "
                        f"<b>{MAX_DURATION} soniya</b>\n\n"
                        "Iltimos, 25 soniyadan qisqaroq "
                        "video yuboring.",
                        parse_mode="HTML",
                    )

                    return

                telegram_duration = int(
                    detected_duration
                )

        # ====================================================
        # PROCESSING
        # ====================================================

        await status.edit_text(
            "⚙️ <b>VIDEO QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Dumaloq video tayyorlanmoqda...\n"
            "🎵 MP3 audio tayyorlanmoqda...\n\n"
            "⏳ Iltimos, kuting...",
            parse_mode="HTML",
        )

        # FFmpeg ikkala vazifani parallel bajaradi
        await asyncio.gather(
            create_round_video(
                str(input_path),
                str(round_path)
            ),

            create_mp3(
                str(input_path),
                str(audio_path)
            ),
        )

        # ====================================================
        # CHECK OUTPUT
        # ====================================================

        if not round_path.exists():

            raise RuntimeError(
                "Dumaloq video yaratilmagan."
            )

        if round_path.stat().st_size == 0:

            raise RuntimeError(
                "Dumaloq video bo'sh."
            )

        if not audio_path.exists():

            raise RuntimeError(
                "MP3 audio yaratilmagan."
            )

        if audio_path.stat().st_size == 0:

            raise RuntimeError(
                "MP3 fayl bo'sh."
            )

        logger.info(
            "Output fayllar tayyor."
        )

        # ====================================================
        # SEND RESULT
        # ====================================================

        await status.edit_text(
            "✅ <b>TAYYOR!</b>\n\n"
            "📤 Fayllar yuborilmoqda...",
            parse_mode="HTML",
        )

        # ----------------------------------------------------
        # ROUND VIDEO
        # ----------------------------------------------------

        with open(
            round_path,
            "rb"
        ) as video_file:

            await message.reply_video_note(
                video_note=video_file,
                duration=telegram_duration or 1,
                length=VIDEO_SIZE,
            )

        # ----------------------------------------------------
        # MP3
        # ----------------------------------------------------

        with open(
            audio_path,
            "rb"
        ) as audio_file:

            await message.reply_audio(
                audio=audio_file,
                title="Video Audio",
                performer="Video Converter",
                caption="🎵 Videodan ajratilgan audio",
            )

        # ====================================================
        # FINISH
        # ====================================================

        try:
            await status.delete()
        except Exception:
            pass

        await message.reply_text(
            "🎉 <b>TAYYOR!</b>\n\n"
            "⭕ Dumaloq video — tayyor\n"
            "🎵 MP3 audio — tayyor\n\n"
            "📤 Yana video yuborishingiz mumkin.",
            parse_mode="HTML",
        )

    # ========================================================
    # ERROR
    # ========================================================

    except Exception as error:

        logger.exception(
            "VIDEO PROCESSING ERROR"
        )

        error_message = str(error)

        try:

            await status.edit_text(
                "❌ <b>XATOLIK YUZ BERDI</b>\n\n"
                "Videoni qayta ishlashning iloji bo'lmadi.\n\n"
                "📌 Video 25 soniyadan kichik va "
                "20 MB dan kichik ekanini tekshiring.",
                parse_mode="HTML",
            )

        except Exception:

            await message.reply_text(
                "❌ Videoni qayta ishlashda xatolik yuz berdi."
            )

        logger.error(
            "Xatolik: %s",
            error_message
        )

    # ========================================================
    # CLEAN TEMP FILES
    # ========================================================

    finally:

        try:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

        except Exception:

            pass


# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    await update.message.reply_text(
        "🎥 <b>VIDEO YUBORING</b>\n\n"
        "Menga video yuboring.\n\n"
        "⏱ Maksimal: <b>25 soniya</b>\n"
        "📦 Maksimal: <b>20 MB</b>\n\n"
        "Men avtomatik ravishda:\n"
        "⭕ Dumaloq video\n"
        "🎵 MP3 audio\n\n"
        "tayyorlab beraman.",
        parse_mode="HTML",
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram bot xatosi: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# POST INIT
# ============================================================

async def post_init(
    application: Application
):

    await check_ffmpeg()

    # ffprobe ham tekshiriladi
    if not shutil.which("ffprobe"):

        raise RuntimeError(
            "ffprobe topilmadi! FFmpeg paketi to'liq "
            "o'rnatilganini tekshiring."
        )

    logger.info(
        "===================================="
    )

    logger.info(
        "VIDEO CONVERTER BOT ISHGA TUSHDI"
    )

    logger.info(
        "MAX VIDEO: 25 soniya"
    )

    logger.info(
        "MAX FILE: 20 MB"
    )

    logger.info(
        "===================================="
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Inline buttons
    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # Normal video + document video
    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            video_handler,
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    # Errors
    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot polling boshlanmoqda..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":
    main()
