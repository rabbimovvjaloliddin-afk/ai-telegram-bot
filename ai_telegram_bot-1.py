import os
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import TelegramError
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

ADMIN_USERNAME = "@jaloliddino7"

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_DURATION = 25                 # 25 soniya
VIDEO_SIZE = 640


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# HTML
# ============================================================

def safe_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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
        "Videoni yuboring — men:\n\n"
        "⭕ Kvadrat video\n"
        "🔊 Original ovoz\n"
        "🎵 MP3 audio\n\n"
        "qilib beraman.\n\n"
        "📌 <b>Limitlar:</b>\n"
        "⏱ Maksimal: <b>25 soniya</b>\n"
        "📦 Maksimal: <b>20 MB</b>"
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


# ============================================================
# BUTTONLAR
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
            "📦 20 MB gacha\n"
            "⏱ 25 soniyagacha\n\n"
            "Natijada:\n"
            "⭕ Kvadrat video\n"
            "🔊 Original ovoz saqlanadi\n"
            "🎵 MP3 audio ham beriladi.",
            parse_mode="HTML",
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ Video yuborasiz.\n\n"
            "2️⃣ Hajmi tekshiriladi.\n\n"
            "3️⃣ Davomiyligi tekshiriladi.\n\n"
            "4️⃣ Video kvadrat formatga o'tkaziladi.\n\n"
            "5️⃣ 🔊 Original ovoz videoda saqlanadi.\n\n"
            "6️⃣ 🎵 Alohida MP3 ham chiqariladi.\n\n"
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
# FFMPEG
# ============================================================

def get_ffmpeg():

    path = shutil.which("ffmpeg")

    if not path:
        raise RuntimeError(
            "FFmpeg topilmadi! Serverga FFmpeg o'rnatish kerak."
        )

    return path


def get_ffprobe():

    path = shutil.which("ffprobe")

    if not path:
        raise RuntimeError(
            "FFprobe topilmadi! FFmpeg paketi to'liq o'rnatilmagan."
        )

    return path


# ============================================================
# VIDEO DAVOMIYLIGI
# ============================================================

async def get_video_duration(file_path):

    ffprobe = get_ffprobe()

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

        error = stderr.decode(
            "utf-8",
            errors="ignore"
        )

        raise RuntimeError(
            f"FFprobe xatosi: {error[-500:]}"
        )

    result = stdout.decode(
        "utf-8",
        errors="ignore"
    ).strip()

    if not result:
        return None

    try:
        return float(result)
    except ValueError:
        return None


# ============================================================
# FFMPEG ISHLATISH
# ============================================================

async def run_ffmpeg(command):

    logger.info(
        "FFmpeg ishga tushmoqda..."
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
            "FFmpeg ERROR:\n%s",
            error
        )

        raise RuntimeError(
            "FFmpeg xatosi:\n" + error[-1500:]
        )

    return stdout, stderr


# ============================================================
# VIDEO + ORIGINAL OVOZ
# ============================================================

async def create_video(
    input_path,
    output_path
):

    ffmpeg = get_ffmpeg()

    command = [
        ffmpeg,
        "-y",

        "-i",
        input_path,

        # Videoni kvadrat qilish
        "-vf",
        (
            "crop=min(iw\\,ih):min(iw\\,ih),"
            "scale=640:640,"
            "format=yuv420p"
        ),

        # VIDEO
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        # ORIGINAL AUDIO
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # Video va audio mapping
        "-map",
        "0:v:0",

        "-map",
        "0:a:0?",

        # MP4
        "-movflags",
        "+faststart",

        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# MP3
# ============================================================

async def create_mp3(
    input_path,
    output_path
):

    ffmpeg = get_ffmpeg()

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
    # 20 MB LIMIT
    # ========================================================

    if file_size > MAX_FILE_SIZE:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
            "📦 Maksimal: <b>20 MB</b>\n\n"
            "20 MB dan kichik video yuboring.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # 25 SONIYA LIMIT
    # ========================================================

    if duration is not None:

        if duration > MAX_DURATION:

            await message.reply_text(
                "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                "⏱ Maksimal: <b>25 soniya</b>\n\n"
                "25 soniyadan qisqaroq video yuboring.",
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
    output_video = temp_dir / "video.mp4"
    output_mp3 = temp_dir / "audio.mp3"

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
                "Video Telegramdan yuklanmadi."
            )

        # ====================================================
        # HAJM TEKSHIRISH
        # ====================================================

        actual_size = input_path.stat().st_size

        if actual_size > MAX_FILE_SIZE:

            await status.edit_text(
                "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
                "📦 Maksimal: <b>20 MB</b>",
                parse_mode="HTML",
            )

            return

        # ====================================================
        # DOCUMENT DURATION
        # ====================================================

        if duration is None:

            await status.edit_text(
                "⏳ <b>VIDEO TEKSHIRILMOQDA...</b>\n\n"
                "⏱ Davomiyligi aniqlanmoqda...",
                parse_mode="HTML",
            )

            duration = await get_video_duration(
                str(input_path)
            )

            if duration is None:

                raise RuntimeError(
                    "Video davomiyligini aniqlab bo'lmadi."
                )

            if duration > MAX_DURATION:

                await status.edit_text(
                    "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                    "⏱ Maksimal: <b>25 soniya</b>",
                    parse_mode="HTML",
                )

                return

        # ====================================================
        # PROCESSING
        # ====================================================

        await status.edit_text(
            "⚙️ <b>QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Video tayyorlanmoqda...\n"
            "🔊 Original ovoz saqlanmoqda...\n"
            "🎵 MP3 tayyorlanmoqda...\n\n"
            "⏳ Kuting...",
            parse_mode="HTML",
        )

        # Bir vaqtning o'zida video + MP3
        await asyncio.gather(

            create_video(
                str(input_path),
                str(output_video)
            ),

            create_mp3(
                str(input_path),
                str(output_mp3)
            ),
        )

        # ====================================================
        # OUTPUT TEKSHIRISH
        # ====================================================

        if not output_video.exists():

            raise RuntimeError(
                "Video fayli yaratilmagan."
            )

        if output_video.stat().st_size <= 0:

            raise RuntimeError(
                "Video fayli bo'sh."
            )

        if not output_mp3.exists():

            raise RuntimeError(
                "MP3 fayli yaratilmagan."
            )

        if output_mp3.stat().st_size <= 0:

            raise RuntimeError(
                "MP3 fayli bo'sh."
            )

        # ====================================================
        # VIDEO YUBORISH
        # ====================================================

        await status.edit_text(
            "✅ <b>VIDEO TAYYOR!</b>\n\n"
            "📤 Original ovozi bilan yuborilmoqda...",
            parse_mode="HTML",
        )

        with open(
            output_video,
            "rb"
        ) as video_file:

            await message.reply_video(
                video=video_file,
                caption=(
                    "⭕ <b>Tayyor video</b>\n"
                    "🔊 Original ovoz saqlangan."
                ),
                parse_mode="HTML",
                supports_streaming=True,
            )

        # ====================================================
        # MP3 YUBORISH
        # ====================================================

        await status.edit_text(
            "🎵 <b>MP3 TAYYOR!</b>\n\n"
            "📤 Audio yuborilmoqda...",
            parse_mode="HTML",
        )

        with open(
            output_mp3,
            "rb"
        ) as audio_file:

            await message.reply_audio(
                audio=audio_file,
                title="Video Audio",
                performer="Video Converter",
                caption="🎵 Videoning original ovozidan MP3",
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
            "⭕ Video — tayyor\n"
            "🔊 Original ovoz — saqlangan\n"
            "🎵 MP3 — tayyor\n\n"
            "📤 Yana video yuborishingiz mumkin.",
            parse_mode="HTML",
        )

    # ========================================================
    # TELEGRAM ERROR
    # ========================================================

    except TelegramError as error:

        logger.exception(
            "TELEGRAM ERROR"
        )

        error_text = safe_html(
            str(error)
        )

        try:

            await status.edit_text(
                "❌ <b>TELEGRAM XATOSI</b>\n\n"
                f"<code>{error_text[:1500]}</code>",
                parse_mode="HTML",
            )

        except Exception:
            pass

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as error:

        logger.exception(
            "VIDEO PROCESSING ERROR"
        )

        error_text = safe_html(
            str(error)
        )

        try:

            await status.edit_text(
                "❌ <b>XATOLIK SABABI:</b>\n\n"
                f"<code>{error_text[:2000]}</code>\n\n"
                "📌 Limit: 25 soniya / 20 MB",
                parse_mode="HTML",
            )

        except Exception:

            try:

                await message.reply_text(
                    "❌ <b>XATOLIK SABABI:</b>\n\n"
                    f"<code>{error_text[:2000]}</code>",
                    parse_mode="HTML",
                )

            except Exception:
                pass

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


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
        "📦 20 MB gacha\n"
        "⏱ 25 soniyagacha\n\n"
        "Natijada:\n"
        "⭕ Kvadrat video\n"
        "🔊 Original ovoz\n"
        "🎵 MP3\n\n"
        "olinadi.",
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

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    if not ffmpeg:

        raise RuntimeError(
            "FFmpeg topilmadi!"
        )

    if not ffprobe:

        raise RuntimeError(
            "FFprobe topilmadi!"
        )

    logger.info(
        "FFmpeg: %s",
        ffmpeg
    )

    logger.info(
        "FFprobe: %s",
        ffprobe
    )

    logger.info(
        "VIDEO CONVERTER ISHGA TUSHDI"
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
        "Bot polling boshlanmoqda..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
