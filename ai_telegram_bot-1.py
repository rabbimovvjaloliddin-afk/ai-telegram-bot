import os
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path

import aiohttp

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
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")

ADMIN_USERNAME = "@jaloliddino7"

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_DURATION = 25

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
                callback_data="video"
            )
        ],
        [
            InlineKeyboardButton(
                "🎵 Musiqani topish",
                callback_data="music"
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Yordam",
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

    await update.message.reply_text(
        "✨ <b>VIDEO CONVERTER</b> ✨\n\n"
        "🎥 Video yuboring.\n\n"
        "Bot:\n"
        "⭕ Kvadrat video qiladi\n"
        "🔊 Original ovozni saqlaydi\n"
        "🎵 MP3 chiqaradi\n"
        "🔍 Musiqani aniqlashga harakat qiladi\n\n"
        "📌 Limit:\n"
        "⏱ 25 soniya\n"
        "📦 20 MB",
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

    if query.data == "video":

        await query.message.reply_text(
            "🎥 <b>VIDEO YUBORING</b>\n\n"
            "⏱ 25 soniyagacha\n"
            "📦 20 MB gacha\n\n"
            "Natijada video + original ovoz + MP3 "
            "va musiqa ma'lumoti olinadi.",
            parse_mode="HTML",
        )

    elif query.data == "music":

        await query.message.reply_text(
            "🎵 <b>MUSIQANI TOPISH</b>\n\n"
            "Musiqa eshitiladigan videoni yuboring.\n\n"
            "Bot qo'shiq nomi va ijrochini "
            "aniqlashga harakat qiladi.",
            parse_mode="HTML",
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 <b>QANDAY ISHLAYDI?</b>\n\n"
            "1️⃣ Video yuborasiz.\n"
            "2️⃣ Video tekshiriladi.\n"
            "3️⃣ Audio ajratiladi.\n"
            "4️⃣ Musiqa aniqlanadi.\n"
            "5️⃣ Video original ovozi bilan qaytariladi.\n"
            "6️⃣ MP3 yuboriladi.\n\n"
            "📌 25 soniya / 20 MB.",
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

def ffmpeg_path():

    path = shutil.which("ffmpeg")

    if not path:
        raise RuntimeError(
            "FFmpeg topilmadi!"
        )

    return path


def ffprobe_path():

    path = shutil.which("ffprobe")

    if not path:
        raise RuntimeError(
            "FFprobe topilmadi!"
        )

    return path


# ============================================================
# DURATION
# ============================================================

async def get_duration(path):

    process = await asyncio.create_subprocess_exec(
        ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            "Video davomiyligini aniqlab bo'lmadi."
        )

    try:
        return float(stdout.decode().strip())
    except:
        return None


# ============================================================
# RUN FFMPEG
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
            "FFmpeg xatosi: " + error[-500:]
        )


# ============================================================
# CREATE VIDEO
# ============================================================

async def create_video(
    input_path,
    output_path
):

    command = [
        ffmpeg_path(),
        "-y",
        "-i",
        input_path,

        "-vf",
        (
            "crop=min(iw\\,ih):min(iw\\,ih),"
            "scale=640:640,"
            "format=yuv420p"
        ),

        "-map",
        "0:v:0",

        "-map",
        "0:a:0?",

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

    await run_ffmpeg(command)


# ============================================================
# CREATE MP3
# ============================================================

async def create_mp3(
    input_path,
    output_path
):

    command = [
        ffmpeg_path(),
        "-y",
        "-i",
        input_path,

        "-vn",

        "-c:a",
        "libmp3lame",

        "-b:a",
        "192k",

        output_path,
    ]

    await run_ffmpeg(command)


# ============================================================
# AUDD MUSIC RECOGNITION
# ============================================================

async def recognize_music(audio_path):

    if not AUDD_API_TOKEN:
        logger.warning(
            "AUDD_API_TOKEN mavjud emas."
        )
        return None

    url = "https://api.audd.io/"

    timeout = aiohttp.ClientTimeout(
        total=60
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            with open(
                audio_path,
                "rb"
            ) as audio:

                form = aiohttp.FormData()

                form.add_field(
                    "api_token",
                    AUDD_API_TOKEN
                )

                form.add_field(
                    "return",
                    "apple_music,spotify"
                )

                form.add_field(
                    "file",
                    audio,
                    filename="audio.mp3",
                    content_type="audio/mpeg"
                )

                async with session.post(
                    url,
                    data=form
                ) as response:

                    response_text = await response.text()

                    logger.info(
                        "AudD HTTP: %s",
                        response.status
                    )

                    logger.info(
                        "AudD RESPONSE: %s",
                        response_text[:3000]
                    )

                    if response.status != 200:
                        return {
                            "error": response_text
                        }

                    try:
                        data = await response.json()
                    except:
                        return {
                            "error": response_text
                        }

        if data.get("status") != "success":

            return {
                "error": data.get(
                    "error",
                    "AudD API xatosi"
                )
            }

        result = data.get("result")

        if not result:
            return None

        return result

    except Exception as error:

        logger.exception(
            "AudD xatosi"
        )

        return {
            "error": str(error)
        }


# ============================================================
# MUSIC TEXT
# ============================================================

def music_text(result):

    if "error" in result:

        return (
            "❌ <b>MUSIQA ANIQLASHDA XATO</b>\n\n"
            f"<code>{result['error']}</code>"
        )

    title = result.get(
        "title",
        "Noma'lum"
    )

    artist = result.get(
        "artist",
        "Noma'lum"
    )

    album = result.get(
        "album"
    )

    song_link = result.get(
        "song_link"
    )

    text = (
        "🎵 <b>MUSIQA TOPILDI!</b>\n\n"
        f"🎶 <b>Nomi:</b> {title}\n"
        f"👤 <b>Ijrochi:</b> {artist}\n"
    )

    if album:
        text += f"💿 <b>Albom:</b> {album}\n"

    if result.get("timecode"):
        text += (
            f"⏱ <b>Topilgan joy:</b> "
            f"{result['timecode']}\n"
        )

    if song_link:
        text += (
            f'\n🔗 <a href="{song_link}">'
            "Qo'shiq sahifasi</a>"
        )

    apple = result.get(
        "apple_music"
    )

    if apple:

        apple_url = apple.get(
            "url"
        )

        if apple_url:
            text += (
                f'\n🍎 <a href="{apple_url}">'
                "Apple Music</a>"
            )

    spotify = result.get(
        "spotify"
    )

    if spotify:

        spotify_url = (
            spotify.get("external_urls", {})
            .get("spotify")
        )

        if spotify_url:
            text += (
                f'\n🟢 <a href="{spotify_url}">'
                "Spotify</a>"
            )

    return text


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

    if message.video:

        media = message.video
        file_size = media.file_size or 0
        duration = media.duration

    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith(
            "video/"
        )
    ):

        media = message.document
        file_size = media.file_size or 0
        duration = None

    else:
        return

    # --------------------------------------------------------
    # 20 MB
    # --------------------------------------------------------

    if file_size > MAX_FILE_SIZE:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA KATTA!</b>\n\n"
            "📦 Maksimal: <b>20 MB</b>",
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # 25 SEC
    # --------------------------------------------------------

    if duration and duration > MAX_DURATION:

        await message.reply_text(
            "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
            "⏱ Maksimal: <b>25 soniya</b>",
            parse_mode="HTML",
        )

        return

    status = await message.reply_text(
        "⏳ <b>VIDEO QABUL QILINDI</b>\n\n"
        "📥 Yuklanmoqda...",
        parse_mode="HTML",
    )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="converter_"
        )
    )

    input_path = temp_dir / "input.mp4"
    output_video = temp_dir / "video.mp4"
    output_mp3 = temp_dir / "audio.mp3"

    try:

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DURATION AGAIN
        # ----------------------------------------------------

        if not duration:

            duration = await get_duration(
                str(input_path)
            )

        if duration and duration > MAX_DURATION:

            await status.edit_text(
                "⚠️ <b>VIDEO JUDA UZUN!</b>\n\n"
                "⏱ Maksimal: <b>25 soniya</b>",
                parse_mode="HTML",
            )

            return

        # ----------------------------------------------------
        # PROCESS
        # ----------------------------------------------------

        await status.edit_text(
            "⚙️ <b>QAYTA ISHLANMOQDA...</b>\n\n"
            "⭕ Video tayyorlanmoqda\n"
            "🔊 Original ovoz saqlanmoqda\n"
            "🎵 MP3 chiqarilmoqda",
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
            )
        )

        # ----------------------------------------------------
        # MUSIC
        # ----------------------------------------------------

        await status.edit_text(
            "🔍 <b>MUSIQA ANIQLANMOQDA...</b>\n\n"
            "Bir oz kuting...",
            parse_mode="HTML",
        )

        music_result = await recognize_music(
            str(output_mp3)
        )

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # MP3
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # MUSIC RESULT
        # ----------------------------------------------------

        if music_result:

            await message.reply_text(
                music_text(music_result),
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

        else:

            await message.reply_text(
                "🔍 <b>MUSIQA TOPILMADI</b>\n\n"
                "Musiqa juda qisqa, shovqinli yoki "
                "AudD bazasida moslik topilmadi.\n\n"
                "Boshqa video yuborib ko'ring.",
                parse_mode="HTML",
            )

        try:
            await status.delete()
        except:
            pass

    except Exception as error:

        logger.exception(
            "VIDEO ERROR"
        )

        try:

            await status.edit_text(
                "❌ <b>XATOLIK</b>\n\n"
                f"<code>{str(error)[:1500]}</code>",
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
        "⏱ 25 soniyagacha\n"
        "📦 20 MB gacha",
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
            "FFprobe topilmadi!"
        )

    if not AUDD_API_TOKEN:

        logger.warning(
            "AUDD_API_TOKEN yo'q!"
        )

    else:

        logger.info(
            "AudD API yoqilgan."
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
