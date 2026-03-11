import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import yt_dlp

from db import db

TOKEN = os.getenv("BOT_TOKEN")
MEDIA_DIR = Path("media")

# Get a comma-separated list of allowed user IDs from environment variables.
allowed_users_env = os.getenv("ALLOWED_USER_IDS", "")

ALLOWED_USER_IDS = set(int(uid.strip()) for uid in allowed_users_env.split(",") if uid.strip())

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

VIDEO_QUALITY_PRESETS = {
    "highest": "best",
    "normal": "best[height<=720]",
    "dontcare": "best[height<=480]",
}

AUDIO_CODECS = {
    "aac": "AAC",
    "mp3": "MP3",
    "opus": "Opus",
    "m4a": "M4A",
}

QUALITY_PRESETS = {
    "highest": "320",
    "normal": "192",
    "dontcare": "128",
}

QUALITY_LABELS = {
    "highest": "Highest One",
    "normal": "Normal",
    "dontcare": "Really Dont Care",
}

def is_authorized(user_id: int) -> bool:
    """Check if the user ID is in our whitelist."""
    return user_id in ALLOWED_USER_IDS

def is_admin(user_id: int) -> bool:
    """Check if the user ID is the admin."""
    admin_id = os.getenv("ADMIN_USER_ID")
    return str(user_id) == admin_id

async def extract_audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start interactive audio extraction flow from /extractAudio URL."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if not db.check_user(user_id, username):
        await update.message.reply_text(f"You are not authorized. Ask the admin to whitelist your ID: {user_id}")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /extractAudio [URL]")
        return

    url = context.args[0].strip()

    if not is_valid_url(url):
        await update.message.reply_text("Please send a valid URL.")
        return

    context.user_data["extract_audio"] = {
        "url": url,
        "requester_id": user_id,
    }

    codec_buttons = [
        [InlineKeyboardButton(label, callback_data=f"extract_audio:codec:{codec}")]
        for codec, label in AUDIO_CODECS.items()
    ]

    await update.message.reply_text(
        "Codec to use?",
        reply_markup=InlineKeyboardMarkup(codec_buttons),
    )


async def extract_audio_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.data is None or not query.data.startswith("extract_audio:"):
        return

    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 3:
        return

    _, action, value = parts
    state = context.user_data.get("extract_audio")
    if not state:
        await query.message.reply_text("No active audio request. Use /extractAudio [URL] again.")
        return

    requester_id = state.get("requester_id")
    caller_id = query.from_user.id

    # Only the user who started the flow can finish it.
    if caller_id != requester_id:
        return

    if action == "codec":
        if value not in AUDIO_CODECS:
            await query.message.reply_text("Invalid codec selected.")
            return

        state["codec"] = value
        quality_buttons = [
            [InlineKeyboardButton(QUALITY_LABELS[key], callback_data=f"extract_audio:quality:{key}")]
            for key in QUALITY_PRESETS
        ]

        await query.message.reply_text(
            "Choose quality:",
            reply_markup=InlineKeyboardMarkup(quality_buttons),
        )
        return

    if action == "quality":
        if value not in QUALITY_PRESETS:
            await query.message.reply_text("Invalid quality selected.")
            return

        codec = state.get("codec")
        url = state.get("url")
        if not codec or not url:
            await query.message.reply_text("Missing data. Use /extractAudio [URL] again.")
            context.user_data.pop("extract_audio", None)
            return

        bitrate = QUALITY_PRESETS[value]
        quality_label = QUALITY_LABELS[value]
        await query.message.reply_text(
            f"Processing your audio... Codec: {AUDIO_CODECS[codec]}, Quality: {quality_label}"
        )

        file_path = None
        try:
            file_path = await asyncio.to_thread(download_audio, url, codec, bitrate)
            await asyncio.to_thread(db.record_download, caller_id, url, file_path)

            with open(file_path, "rb") as audio_file:
                await query.message.reply_audio(audio=audio_file)

            # Delete right away after Telegram confirms send.
            await asyncio.to_thread(cleanup_download_file, file_path)
            file_path = None
        except Exception as e:
            print(e)
            await query.message.reply_text("Couldn't download this link. Please try another URL.")
        finally:
            context.user_data.pop("extract_audio", None)
            await asyncio.to_thread(cleanup_download_file, file_path)



async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caller_id = update.effective_user.id

    # If caller is not admin, silently ignore.
    if not is_admin(caller_id):
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addUser [ID_User] [Password]")
        return

    new_user_id_raw, provided_password = context.args

    try:
        new_user_id = int(new_user_id_raw)
    except ValueError:
        await update.message.reply_text("ID_User must be a valid number.")
        return

    """ if not MY_SECRET_PASSWORD or provided_password != MY_SECRET_PASSWORD:
        await update.message.reply_text("Invalid password.")
        return """

    # Ensure user row exists, then whitelist.
    await asyncio.to_thread(db.check_user, new_user_id, "Unknown")
    await asyncio.to_thread(db.add_user_to_whitelist, new_user_id)
    await update.message.reply_text(f"User {new_user_id} added to whitelist.")

def download_audio(url, codec="aac", quality="192"):
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = str(MEDIA_DIR / f"downloaded_{uuid.uuid4().hex}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_file,
        'quiet': True,
        'nopart': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': codec,
            'preferredquality': quality,
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_file

def download_video(url):
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = str(MEDIA_DIR / f"downloaded_{uuid.uuid4().hex}.mp4")
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_file,
        'quiet': True,
        'nopart': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_file

def cleanup_download_file(file_path: str | None) -> None:
    if not file_path:
        return

    file = Path(file_path)
    artifacts = [file, Path(f"{file}.part"), Path(f"{file}.ytdl")]
    for artifact in artifacts:
        try:
            artifact.unlink(missing_ok=True)
        except OSError:
            pass

def is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if not db.check_user(user_id, username):
        await update.message.reply_text(f"You are not authorized. Ask the admin to whitelist your ID: {user_id}")
        return

    await update.message.reply_text("Send a URL link and ill download it on HD")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if not db.check_user(user_id, username):
        await update.message.reply_text(f"You are not authorized. Ask the admin to whitelist your ID: {user_id}")
        return

    url = (update.message.text or "").strip()

    if not is_valid_url(url):
        await update.message.reply_text("Please send a valid URL.")
        return

    await update.message.reply_text("Processing your video... ")

    file_path = None
    try:
        file_path = await asyncio.to_thread(download_video, url)
        
        # Guardar en base de datos ewe
        await asyncio.to_thread(db.record_download, user_id, url, file_path)
        
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file)

        # Delete right away after Telegram confirms send.
        await asyncio.to_thread(cleanup_download_file, file_path)
        file_path = None
    except Exception as e:
        print(e)
        await update.message.reply_text("Couldn't download this link. Please try another URL.")
    finally:
        await asyncio.to_thread(cleanup_download_file, file_path)
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Configure it in your environment or .env file.")


    db.init_db()
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("addUser", add_user_command))
    app.add_handler(CommandHandler("extractAudio", extract_audio_command))
    app.add_handler(CallbackQueryHandler(extract_audio_selection_callback, pattern=r"^extract_audio:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()