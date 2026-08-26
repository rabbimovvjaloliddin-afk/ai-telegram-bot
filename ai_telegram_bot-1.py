import os
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path

import aiohttp

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
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")

ADMIN_USERNAME = "@jaloliddino7"

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_DURATION = 25
VIDEO_SIZE = 640

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi!")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
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
                "🎵 Musiqani topish",
                callback_data="recognize"
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
        "🎥 Videoni yuboring.\n\n"
        "Men:\n"
        "⭕ Kvadrat video\n"
        "🔊 Original ovoz\n"
        "🎵 MP3 audio\n"
        "🔍 Musiqa nomini aniqlash\n\n"
        "qilib beraman.\n\n"
        "📌 <b>Limit:</b>\n"
        "⏱ 25 soniyagacha\n"
        "📦 20 MB gacha"
    )

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
    await query.answer()

    if query.data == "convert":

        await query.message.reply_text(
            "🎥 <b>VIDEO YUBORING</b>\n\n"
            "📦 Maksimal: 20 MB\n"
            "⏱ Maksimal: 25 soniya\n\n"
            "Natijada:\n"
            "⭕ Kvadrat video\n"
            "🔊 Original ovoz\n"
            "🎵 MP3\n"
            "🔍 Musiqa aniqlash",
            parse_mode="HTML",
        )

    elif query.data == "recognize":

        await query.message.reply_text(
            "🎵 <b>MUSIQANI TOPISH</b>\n\n"
            "Musiqa eshitiladigan videoni yuboring.\n\n"
            "Bot videodagi musiqani aniqlashga "
            "harakat qiladi va:\n\n"
            "🎵 Qo'shiq nomi\n"
            "👤 Ijrochi\n"
            "💿 Albom\n"
            "🔗 Mavjud rasmiy manbalar\n\n"
            "haqida ma'lumot beradi.",
            parse_mode="HTML",
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ 25 soniyagacha video yuborasiz.\n\n"
            "2️⃣ Bot videoni tekshiradi.\n\n"
            "3️⃣ Musiqani aniqlashga harakat qiladi.\n\n"
            "4️⃣ Video kvadrat formatga o'tadi.\n\n"
            "5️⃣ Original ovoz saqlanadi.\n\n"
            "6️⃣ MP3 chiqariladi.\n\n"
            "📌 Video: 20 MB / 25 soniya.",
            parse_mode="HTML",
        )

    elif query.data == "admin":

        await query.message.reply_text(
            f"👨‍💻 <b>ADMIN</b>\n\n"
            f"📩 {ADMIN_USERNAME}",
            parse_mode="HTML",
        )


# ============================================================
# FFMPEG
# ============================================================

def get_ffmpeg():

    path = shutil.which("ffmpeg")

    if not path:
        raise RuntimeError(
            "FFmpeg topilmadi!"
        )

    return path


def get_ffprobe():

    path = shutil.which("ffprobe")

    if not path:
        raise RuntimeError(
            "FFprobe topilmadi!"
        )

    return path


# ============================================================
# DURATION
# ============================================================

async def get_video_duration(
    file_path: str
):

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
        raise RuntimeError(
            "Video davomiyligini aniqlab bo'lmadi."
        )

    result = stdout.decode().strip()

    try:
        return float(result)
    except:
        return None


# ============================================================
# FFMPEG
# ============================================================

async def run_ffmpeg(command):

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

        logger.error(error)

        raise RuntimeError(
            "FFmpeg xatosi."
        )


# ============================================================
# VIDEO + ORIGINAL AUDIO
# ============================================================

async def create_video(
    input_path: str,
    output_path: str
):

    ffmpeg = get_ffmpeg()

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

        # ORIGINAL OVOZ
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-map",
        "0:v:0",

        "-map",
        "0:a:0?",

        "-movflags",
        "+faststart",

        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# MP3
# ============================================================

async def create_mp3(
    input_path: str,
    output_path: str
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
# MUSIC RECOGNITION — AUDD
# ============================================================

async def recognize_music(
    audio_path: str
):

    if not AUDD_API_TOKEN:

        logger.warning(
            "AUDD_API_TOKEN sozlanmagan."
        )

        return None

    url = "https://api.audd.io/"

    try:

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            form = aiohttp.FormData()

            form.add_field(
                "api_token",
                AUDD_API_TOKEN
            )

            form.add_field(
                "return",
                "apple_music,spotify"
            )

            with open(
                audio_path,
                "rb"
            ) as audio:

                form.add_field(
                    "file",
                    audio,
                    filename="audio.mp3",
                    content_type="audio/mpeg",
                )

                async with session.post(
                    url,
                    data=form
                ) as response:

                    if response.status != 200:

                        logger.error(
                            "AudD HTTP: %s",
                            response.status
                        )

                        return None

                    data = await response.json()

        if data.get("status") != "success":
            return None

        result = data.get("result")

        if not result:
            return None

        return result

    except Exception as error:

        logger.exception(
            "Musiqa aniqlash xatosi: %s",
            error
        )

        return None


# ============================================================
# MUSIC RESULT TEXT
# ============================================================

def format_music_result(result):

    title = result.get(
        "title",
        "Noma'lum"
    )

    artist = result.get(
        "artist",
        "Noma'lum"
    )

    album = result.get(
        "album",
        None
    )

    lines = [
        "🎵 <b>MUSIQA TOPILDI!</b>",
        "",
        f"🎶 <b>Qo'shiq:</b> {title}",
        f"👤 <b>Ijrochi:</b> {artist}",
    ]

    if album:
        lines.append(
            f"💿 <b>Albom:</b> {album}"
        )

    # Spotify
    spotify = result.get("spotify")

    if spotify:

        spotify_url = spotify.get(
            "external_urls",
            {}
        ).get("spotify")

        if spotify_url:

            lines.append(
                f'🟢 <a href="{spotify_url}">Spotify</a>'
            )

    # Apple Music
    apple = result.get("apple_music")

    if apple:

        apple_url = apple.get(
            "url"
        )

        if apple_url:

            lines.append(
                f'🍎 <a href="{apple_url}">Apple Music</a>'
            )

    lines.extend([
        "",
        "ℹ️ To'liq qo'shiqni qonuniy "
        "ravishda yuqoridagi rasmiy "
        "manbalardan tinglashingiz mumkin."
    ])

    return "\n".join(lines)


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

    # NORMAL VIDEO
    if message.video:

        media = message.video

        file_size = media.file_size or 0

        duration = media.duration

    # DOCUMENT VIDEO
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith(
            "video/"
        )
    ):

        media = message.document

        file_size = media.file_size or 0

    else:
        return

    # ========================================================
    # SIZE LIMIT
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
    # DURATION LIMIT
    # ========================================================

    if duration and duration > MAX_DURATION:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
            "⏱ Maksimal: <b>25 soniya</b>\n\n"
            "25 soniyadan qisqa video yuboring.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # STATUS
    # ========================================================

    status = await message.reply_text(
        "⏳ <b>VIDEO QABUL QILINDI</b>\n\n"
        "📥 Yuklanmoqda...",
        parse_mode="HTML",
    )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="video_bot_"
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
                "Video yuklanmadi."
            )

        # ====================================================
        # REAL DURATION
        # ====================================================

        if not duration:

            duration = await get_video_duration(
                str(input_path)
            )

        if duration and duration > MAX_DURATION:

            await status.edit_text(
                "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                "⏱ Maksimal: <b>25 soniya</b>",
                parse_mode="HTML",
            )

            return

        # ====================================================
        # PROCESS
        # ====================================================

        await status.edit_text(
            "⚙️ <b>QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Video tayyorlanmoqda...\n"
            "🔊 Original ovoz saqlanmoqda...\n"
            "🎵 MP3 tayyorlanmoqda...",
            parse_mode="HTML",
        )

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
        # MUSIC RECOGNITION
        # ====================================================

        await status.edit_text(
            "🔍 <b>MUSIQA ANIQLANMOQDA...</b>\n\n"
            "🎵 Videodagi musiqani qidirmoqdaman...",
            parse_mode="HTML",
        )

        music_result = await recognize_music(
            str(output_mp3)
        )

        # ====================================================
        # SEND VIDEO
        # ====================================================

        await status.edit_text(
            "📤 <b>VIDEO YUBORILMOQDA...</b>",
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
        # SEND MP3
        # ========================================================

        with open(
            output_mp3,
            "rb"
        ) as audio_file:

            await message.reply_audio(
                audio=audio_file,
                title="Video Audio",
                performer="Video Converter",
                caption="🎵 Videoning original ovozi",
            )

        # ====================================================
        # MUSIC RESULT
        # ====================================================

        if music_result:

            music_text = format_music_result(
                music_result
            )

            await message.reply_text(
                music_text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

        else:

            await message.reply_text(
                "🔍 <b>MUSIQA ANIQLANMADI</b>\n\n"
                "Musiqa juda qisqa bo'lishi yoki "
                "fon shovqini ko'p bo'lishi mumkin.\n\n"
                "Boshqa video yuborib ko'ring.",
                parse_mode="HTML",
            )

        # ====================================================
        # FINISH
        # ====================================================

        try:
            await status.delete()
        except:
            pass

        await message.reply_text(
            "✅ <b>TAYYOR!</b>\n\n"
            "⭕ Video — tayyor\n"
            "🔊 Original ovoz — saqlangan\n"
            "🎵 MP3 — tayyor\n"
            "🔍 Musiqa — tekshirildi",
            parse_mode="HTML",
        )

    except TelegramError as error:

        logger.exception(
            "Telegram xatosi"
        )

        try:

            await status.edit_text(
                "❌ <b>TELEGRAM XATOSI</b>\n\n"
                f"<code>{safe_html(error)}</code>",
                parse_mode="HTML",
            )

        except:
            pass

    except Exception as error:

        logger.exception(
            "Processing error"
        )

        try:

            await status.edit_text(
                "❌ <b>XATOLIK</b>\n\n"
                f"<code>{safe_html(error)}</code>",
                parse_mode="HTML",
            )

        except:
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

    await update.message.reply_text(
        "🎥 <b>VIDEO YUBORING</b>\n\n"
        "📦 20 MB gacha\n"
        "⏱ 25 soniyagacha\n\n"
        "🎵 Musiqasini ham aniqlashga "
        "harakat qilaman.",
        parse_mode="HTML",
    )


# ============================================================
# ERROR
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
# POST INIT
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
            "FFprobe topilmadi!"
        )

    if AUDD_API_TOKEN:
        logger.info(
            "AudD musiqa aniqlash yoqilgan."
        )
    else:
        logger.warning(
            "AUDD_API_TOKEN yo'q. "
            "Musiqa aniqlash ishlamaydi."
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

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
