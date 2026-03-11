FROM python:3.11-slim

# Install ffmpeg (needed by yt-dlp to process videos)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
# Install node.js (needed by yt-dlp to process videos)
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]