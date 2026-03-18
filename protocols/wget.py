
import shutil
import subprocess
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse


VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".m4v", ".3gp",
}
AUDIO_EXTENSIONS = {
    ".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac", ".opus",
}
GIF_EXTENSIONS = {
    ".gif",
}


def _url_extension(url: str) -> str:
    path = urlparse(url).path or ""
    return Path(path).suffix.lower()


def is_direct_media_url(url: str) -> bool:
    ext = _url_extension(url)
    return ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS or ext in GIF_EXTENSIONS


def is_direct_audio_url(url: str) -> bool:
    return _url_extension(url) in AUDIO_EXTENSIONS


def is_direct_video_url(url: str) -> bool:
    return _url_extension(url) in VIDEO_EXTENSIONS


def is_direct_gif_url(url: str) -> bool:
    return _url_extension(url) in GIF_EXTENSIONS


def download_direct_file(url: str, media_dir: Path = Path("media")) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    ext = _url_extension(url) or ".bin"
    output_file = media_dir / f"downloaded_{uuid.uuid4().hex}{ext}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        with output_file.open("wb") as handle:
            shutil.copyfileobj(response, handle)

    return str(output_file)


def remux_to_h264_mp4(input_file: str, media_dir: Path = Path("media")) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = media_dir / f"downloaded_{uuid.uuid4().hex}.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_file),
    ]

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg remux failed: {completed.stderr[-500:]}")

    return str(output_file)


def extract_audio_to_aac(input_file: str, media_dir: Path = Path("media"), bitrate: str = "256k") -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = media_dir / f"downloaded_{uuid.uuid4().hex}.aac"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        bitrate,
        str(output_file),
    ]

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {completed.stderr[-500:]}")

    return str(output_file)


def convert_video_to_gif(input_file: str, media_dir: Path = Path("media"), fps: int = 12, width: int = 480) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    output_file = media_dir / f"downloaded_{uuid.uuid4().hex}.gif"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vf",
        f"fps={fps},scale={width}:-1:flags=lanczos",
        str(output_file),
    ]

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg gif conversion failed: {completed.stderr[-500:]}")

    return str(output_file)