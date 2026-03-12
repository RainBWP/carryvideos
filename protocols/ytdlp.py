import yt_dlp
import os
import uuid
from pathlib import Path


YOUTUBE_COOKIE_FILE = Path(os.getenv("YOUTUBE_COOKIE_FILE", ".youtube-cookie.txt"))


def _is_netscape_cookie_file(cookie_file: Path) -> bool:
    if not cookie_file.exists() or not cookie_file.is_file():
        return False

    try:
        with cookie_file.open("r", encoding="utf-8", errors="ignore") as handle:
            first_non_empty_line = ""
            for line in handle:
                stripped_line = line.strip()
                if stripped_line:
                    first_non_empty_line = stripped_line
                    break
    except OSError:
        return False

    if not first_non_empty_line:
        return False

    return first_non_empty_line.startswith("# Netscape HTTP Cookie File")


def _build_youtube_opts(output_file: str, media_format: str) -> dict:
    ydl_opts = {
        'format': media_format,
        'outtmpl': output_file,
        'quiet': True,
        'nopart': True,
        'noplaylist': True,
        'js_runtimes': {'node': {}},
        'remote_components': ['ejs:github'],
    }

    if _is_netscape_cookie_file(YOUTUBE_COOKIE_FILE):
        ydl_opts['cookiefile'] = str(YOUTUBE_COOKIE_FILE)
    elif YOUTUBE_COOKIE_FILE.exists():
        print(f"Skipping invalid YouTube cookie file: {YOUTUBE_COOKIE_FILE}")

    return ydl_opts

def download_audio(url, codec="aac", quality="192", media_dir=Path("media")):
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(media_dir / f"downloaded_{uuid.uuid4().hex}")
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
    return f"{output_file}.{codec}"

def download_audio_youtube(url, codec="aac", quality="192", media_dir=Path("media")):
    """Download YouTube audio with yt-dlp configured to use Node.js runtime."""
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(media_dir / f"downloaded_{uuid.uuid4().hex}")
    ydl_opts = _build_youtube_opts(output_file, 'bestaudio/best')
    ydl_opts['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': codec,
        'preferredquality': quality,
    }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return f"{output_file}.{codec}"

def download_video(url, media_dir=Path("media")):
    """
        This is the default video download function, which downloads the best quality video available.
    """
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(media_dir / f"downloaded_{uuid.uuid4().hex}.mp4")
    ydl_opts = {
        'format': 'bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'outtmpl': output_file,
        'quiet': True,
        'nopart': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_file

def download_video_youtube(url, media_dir=Path("media")):
    """Download YouTube video with yt-dlp configured to use Node.js runtime."""
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(media_dir / f"downloaded_{uuid.uuid4().hex}.mp4")
    ydl_opts = _build_youtube_opts(output_file, 'bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]')
    ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_file

def download_gif(url, media_dir=Path("media")):
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(media_dir / f"downloaded_{uuid.uuid4().hex}.gif")
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
