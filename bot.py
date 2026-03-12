import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from db import db
from protocols import ytdlp, wget

TOKEN = os.getenv("BOT_TOKEN")
MEDIA_DIR = Path("media")

# Get a comma-separated list of allowed user IDs from environment variables.
allowed_users_env = os.getenv("ALLOWED_USER_IDS", "")

ALLOWED_USER_IDS = set(int(uid.strip()) for uid in allowed_users_env.split(",") if uid.strip())

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

def check_url_is_youtube(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc in {"www.youtube.com", "youtube.com", "youtu.be"}:
        return True
    return False

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

    url_is_youtube = check_url_is_youtube(url)

    context.user_data["extract_audio"] = {
        "url": url,
        "requester_id": user_id,
    }

    file_path = None
    try:
        if wget.is_direct_media_url(url):
            await update.message.reply_text("Direct file link detected. Downloading and remuxing audio...")
            downloaded_path = await asyncio.to_thread(wget.download_direct_file, url, MEDIA_DIR)
            file_path = downloaded_path
            if wget.is_direct_video_url(url):
                await update.message.reply_text("Video file detected!!!. Extracting audio...")
                file_path = await asyncio.to_thread(wget.extract_audio_to_aac, downloaded_path, MEDIA_DIR, "256k")
                await asyncio.to_thread(cleanup_download_file, downloaded_path)
        elif url_is_youtube:
            await update.message.reply_text("This could take a while... I hate YouTube videos")
            file_path = await asyncio.to_thread(ytdlp.download_audio_youtube, url, "aac", "256", MEDIA_DIR)
        else:
            await update.message.reply_text("This could take a while...")
            file_path = await asyncio.to_thread(ytdlp.download_audio, url, "aac", "256", MEDIA_DIR)
        print(f"Audio downloaded to {file_path}")
        await asyncio.to_thread(db.record_download, user_id, url, file_path)

        with open(file_path, "rb") as audio_file:
            await update.message.reply_audio(audio=audio_file)

        # Delete right away after Telegram confirms send.
        await asyncio.to_thread(cleanup_download_file, file_path)
        file_path = None
    except Exception as e:
        print(e)
        await update.message.reply_text("Couldn't download this link. Please try another URL.")
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

def cleanup_download_file(file_path: str | None) -> None:
    if not file_path:
        # Cleans media folder of any None entries, just in case.
        for item in MEDIA_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except OSError:
                    pass
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
        if wget.is_direct_media_url(url):
            await update.message.reply_text("Direct file link detected. Downloading and preparing file...")
            downloaded_path = await asyncio.to_thread(wget.download_direct_file, url, MEDIA_DIR)

            if wget.is_direct_audio_url(url):
                file_path = downloaded_path
                await asyncio.to_thread(db.record_download, user_id, url, file_path)
                with open(file_path, 'rb') as audio_file:
                    await update.message.reply_audio(audio=audio_file)
            else:
                remuxed_path = await asyncio.to_thread(wget.remux_to_h264_mp4, downloaded_path, MEDIA_DIR)
                await asyncio.to_thread(cleanup_download_file, downloaded_path)
                file_path = remuxed_path
                await asyncio.to_thread(db.record_download, user_id, url, file_path)
                with open(file_path, 'rb') as video_file:
                    await update.message.reply_video(video=video_file)
        elif check_url_is_youtube(url):
            await update.message.reply_text("This could take a while...")
            file_path = await asyncio.to_thread(ytdlp.download_video_youtube, url, MEDIA_DIR)
            await asyncio.to_thread(db.record_download, user_id, url, file_path)

            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
        else:
            file_path = await asyncio.to_thread(ytdlp.download_video, url, MEDIA_DIR)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()