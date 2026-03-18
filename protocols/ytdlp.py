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


def _is_gif_info(info: dict) -> bool:
    if not isinstance(info, dict):
        return False

    ext = str(info.get("ext", "")).lower()
    if ext == "gif":
        return True

    requested_formats = info.get("requested_formats") or []
    for requested in requested_formats:
        if str(requested.get("ext", "")).lower() == "gif":
            return True

    return False


def _probe_is_gif(url: str, ydl_opts: dict) -> bool:
    probe_opts = dict(ydl_opts)
    probe_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if isinstance(info, dict) and info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            return False
        info = entries[0]

    return _is_gif_info(info)


def _download_or_convert_gif(url: str, ydl_opts: dict, media_dir: Path = Path("media")) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    output_base = media_dir / f"downloaded_{uuid.uuid4().hex}"

    gif_scale_filter = "fps=10,scale=300:300:force_original_aspect_ratio=decrease:flags=lanczos"

    if _probe_is_gif(url, ydl_opts):
        direct_opts = dict(ydl_opts)
        direct_opts["format"] = "best[ext=gif]/best"
        direct_opts["outtmpl"] = str(output_base) + ".%(ext)s"
        direct_opts.pop("postprocessors", None)
        direct_opts.pop("postprocessor_args", None)
        direct_opts.pop("merge_output_format", None)

        with yt_dlp.YoutubeDL(direct_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if isinstance(info, dict) and info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if entries:
                info = entries[0]

        downloaded_path = Path(str(output_base) + ".gif")
        if isinstance(info, dict):
            prepared = ydl.prepare_filename(info)
            if prepared:
                downloaded_path = Path(prepared)

        if downloaded_path.suffix.lower() != ".gif":
            return str(downloaded_path.with_suffix(".gif"))
        return str(downloaded_path)

    convert_opts = dict(ydl_opts)
    convert_opts["format"] = "bestvideo/best"
    convert_opts["outtmpl"] = str(output_base) + ".%(ext)s"
    convert_opts.pop("merge_output_format", None)
    convert_opts["postprocessors"] = [{
        "key": "FFmpegVideoConvertor",
        "preferedformat": "gif",
    }]
    convert_opts["postprocessor_args"] = [
        "-vf",
        gif_scale_filter,
    ]

    with yt_dlp.YoutubeDL(convert_opts) as ydl:
        ydl.download([url])

    return str(output_base.with_suffix(".gif"))

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
    """Download a direct GIF when available, otherwise convert to a compressed 300x300-max GIF."""
    ydl_opts = {
        'quiet': True,
        'nopart': True,
        'noplaylist': True,
    }
    return _download_or_convert_gif(url, ydl_opts, media_dir)


def download_gif_youtube(url, media_dir=Path("media")):
    """Download YouTube GIF directly when possible, otherwise convert to a compressed 300x300-max GIF."""
    ydl_opts = _build_youtube_opts("", 'bestvideo/best')
    return _download_or_convert_gif(url, ydl_opts, media_dir)
