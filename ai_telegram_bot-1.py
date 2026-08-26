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
# SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN topilmadi!"
    )

ADMIN_USERNAME = "@jaloliddino7"

MAX_FILE_SIZE = 20 * 1024 * 1024   # 20 MB
MAX_DURATION = 25                  # 25 soniya


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
        "Men videoni:\n\n"
        "⭕ <b>Dumaloq video</b>\n"
        "🎵 <b>MP3 audio</b>\n\n"
        "qilib beraman.\n\n"
        "📌 <b>Limitlar:</b>\n"
        "⏱ 25 soniyagacha\n"
        "📦 20 MB gacha\n\n"
        "🎥 Videoni shu chatga yuboring."
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


# ============================================================
# BUTTON HANDLER
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
            "📦 Maksimal hajm: <b>20 MB</b>\n"
            "⏱ Maksimal davomiylik: <b>25 soniya</b>\n\n"
            "Men avtomatik:\n"
            "⭕ Dumaloq video\n"
            "🎵 MP3 audio\n\n"
            "tayyorlab beraman.",
            parse_mode="HTML",
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ Videoni yuborasiz.\n\n"
            "2️⃣ Bot hajmini tekshiradi.\n\n"
            "3️⃣ Bot davomiyligini tekshiradi.\n\n"
            "4️⃣ ⭕ Dumaloq video tayyorlaydi.\n\n"
            "5️⃣ 🎵 MP3 audio ajratadi.\n\n"
            "6️⃣ Ikkala faylni sizga yuboradi.\n\n"
            "📌 Limit: 25 soniya / 20 MB.",
            parse_mode="HTML",
        )

    elif query.data == "admin":

        await query.message.reply_text(
            "👨‍💻 <b>ADMIN</b>\n\n"
            f"📩 Murojaat: {ADMIN_USERNAME}",
            parse_mode="HTML",
        )


# ============================================================
# FFPROBE DURATION
# ============================================================

async def get_duration(file_path: str):

    ffprobe = shutil.which("ffprobe")

    if not ffprobe:
        raise RuntimeError(
            "ffprobe topilmadi. Serverda FFmpeg o'rnatilmagan."
        )

    process = await asyncio.create_subprocess_exec(
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        return None

    try:
        return float(
            stdout.decode(
                "utf-8",
                errors="ignore"
            ).strip()
        )
    except Exception:
        return None


# ============================================================
# RUN FFMPEG
# ============================================================

async def run_ffmpeg(command):

    logger.info(
        "FFmpeg: %s",
        " ".join(command)
    )

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:

        error = stderr.decode(
            "utf-8",
            errors="ignore"
        )

        logger.error(
            "FFmpeg ERROR: %s",
            error
        )

        raise RuntimeError(
            "Videoni qayta ishlashda FFmpeg xatosi."
        )


# ============================================================
# CREATE ROUND VIDEO
# ============================================================

async def create_round_video(
    input_path: str,
    output_path: str
):

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg topilmadi."
        )

    # Kvadrat video tayyorlaymiz.
    # Keyin Telegram video note sifatida yuboriladi.

    command = [
        ffmpeg,
        "-y",
        "-i",
        input_path,

        "-vf",
        (
            "crop=min(iw\\,ih):min(iw\\,ih),"
            "scale=640:640,"
            "format=yuv420p"
        ),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-an",

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

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg topilmadi."
        )

    command = [
        ffmpeg,
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
    duration = None

    # --------------------------------------------------------
    # ODDIY VIDEO
    # --------------------------------------------------------

    if message.video:

        media = message.video

        file_size = media.file_size or 0

        duration = media.duration or None

    # --------------------------------------------------------
    # DOCUMENT VIDEO
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
    # 20 MB TEKSHIRISH
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
    # TELEGRAM BERGAN DURATION
    # ========================================================

    if duration and duration > MAX_DURATION:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
            "⏱ Maksimal: <b>25 soniya</b>\n\n"
            "Iltimos, 25 soniyadan qisqaroq video yuboring.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # STATUS
    # ========================================================

    status = await message.reply_text(
        "⏳ <b>VIDEO QABUL QILINDI</b>\n\n"
        "📥 Video yuklanmoqda...",
        parse_mode="HTML",
    )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="video_converter_"
        )
    )

    input_path = temp_dir / "input.mp4"
    round_path = temp_dir / "round.mp4"
    audio_path = temp_dir / "audio.mp3"

    try:

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
                "Video yuklanmadi."
            )

        actual_size = input_path.stat().st_size

        # ====================================================
        # REAL FILE SIZE
        # ====================================================

        if actual_size > MAX_FILE_SIZE:

            await status.edit_text(
                "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
                "📦 Maksimal hajm: <b>20 MB</b>",
                parse_mode="HTML",
            )

            return

        # ====================================================
        # DOCUMENT UCHUN DURATION
        # ====================================================

        if duration is None:

            duration = await get_duration(
                str(input_path)
            )

            if duration is not None:

                if duration > MAX_DURATION:

                    await status.edit_text(
                        "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                        "⏱ Maksimal: <b>25 soniya</b>\n\n"
                        "25 soniyadan qisqaroq video yuboring.",
                        parse_mode="HTML",
                    )

                    return

        # ====================================================
        # PROCESSING
        # ====================================================

        await status.edit_text(
            "⚙️ <b>QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Dumaloq video tayyorlanmoqda...\n"
            "🎵 MP3 tayyorlanmoqda...\n\n"
            "⏳ Kuting...",
            parse_mode="HTML",
        )

        # Ikkalasini bir vaqtda tayyorlash
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
        # OUTPUT CHECK
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
                "MP3 yaratilmagan."
            )

        if audio_path.stat().st_size == 0:
            raise RuntimeError(
                "MP3 fayl bo'sh."
            )

        # ====================================================
        # SEND
        # ====================================================

        await status.edit_text(
            "✅ <b>TAYYOR!</b>\n\n"
            "📤 Fayllar yuborilmoqda...",
            parse_mode="HTML",
        )

        # ----------------------------------------------------
        # DUMALOQ VIDEO
        # ----------------------------------------------------

        with open(
            round_path,
            "rb"
        ) as video_file:

            await message.reply_video_note(
                video_note=video_file,
                duration=int(duration or 1),
                length=640,
            )

        # ----------------------------------------------------
        # MP3 — VOICE EMAS!
        # ----------------------------------------------------

        with open(
            audio_path,
            "rb"
        ) as audio_file:

            await message.reply_audio(
                audio=audio_file,
                title="Video Audio",
                performer="Video Converter",
                caption="🎵 Videodan ajratilgan MP3",
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

    except Exception as error:

        logger.exception(
            "VIDEO PROCESSING ERROR"
        )

        try:

            await status.edit_text(
                "❌ <b>XATOLIK!</b>\n\n"
                "Videoni qayta ishlashda muammo yuz berdi.\n\n"
                "📌 Video 25 soniyadan va "
                "20 MB dan oshmasin.",
                parse_mode="HTML",
            )

        except Exception:

            try:
                await message.reply_text(
                    "❌ Videoni qayta ishlashda xatolik yuz berdi."
                )
            except Exception:
                pass

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# TEXT
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    await update.message.reply_text(
        "🎥 <b>VIDEO YUBORING</b>\n\n"
        "📦 Maksimal: <b>20 MB</b>\n"
        "⏱ Maksimal: <b>25 soniya</b>\n\n"
        "Men sizga:\n"
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
        "BOT ERROR: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# STARTUP
# ============================================================

async def post_init(
    application: Application
):

    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg topilmadi!"
        )

    if not shutil.which("ffprobe"):
        raise RuntimeError(
            "ffprobe topilmadi!"
        )

    logger.info(
        "================================"
    )

    logger.info(
        "VIDEO CONVERTER ISHGA TUSHDI"
    )

    logger.info(
        "Limit: 25 soniya / 20 MB"
    )

    logger.info(
        "================================"
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

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            video_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot ishga tushmoqda..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
