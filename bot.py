import asyncio
import os
import uuid
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

def download_video(url):
    output_file = f"downloaded_{uuid.uuid4().hex}.mp4"
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_file,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_file


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()

    if not is_valid_url(url):
        await update.message.reply_text("Please send a valid URL.")
        return

    await update.message.reply_text("Processing your video... ⏳")

    file_path = None
    try:
        file_path = await asyncio.to_thread(download_video, url)
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file)
    except Exception:
        await update.message.reply_text("Couldn't download this link. Please try another URL.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Configure it in your environment or .env file.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()