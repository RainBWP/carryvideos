# CarryVideos
Simple Telegram Bot Downloader Video using [yt.dlp](https://github.com/yt-dlp/yt-dlp) as backend for downloading.

## The `.env` file
You need to create a `.env` file for bot configuration

On **BOT_TOKEN** thats ur bot token

On **ALLOWED_USER_IDS** theres ur ids
```json
BOT_TOKEN=[YourTokenHere]
ADMIN_USER_ID="[YourIDS]"
```

### Right now, the youtube cookie session is not working, but expect it
Create a `.youtube-cookie.txt` on root folder
There you need copy your cookies session from youtube.
__You can use Cookie.txt for that.__
we recommend follow this [Instrucctions to update cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) and [This guide too for youtube perma cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
## Run this

```sh
docker compose pull
docker compose build --no-cache
docker compose up -d
```

### Stop docker 
```sh
docker compose stop
```
### delete docker
```sh
docker compose down --rmi all --volumes --remove-orphans
docker system prune -a --volumes -f
```

## Commands on telegram
Right now this only support 3 of 4 commands
1. `/start`
    - This will only send two messages if you register on the whitelist or not
        - If you are register
            - **Just send an URL to download**
        - If you aren't register
            - **You are not autorized to use this bot, ask admin to allow you *[ID_USER]***
2. `/addUser [IDUser]`
    - Right now this is only an admin command, this allows add people to the service
3. `[URL_Video]`
    - Send a the url video to the bot directly, this will process the video
    - Chech [Supported Sites yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) for supported urls.
4. `/extractaudio [URL]` [work in progress, maybe]
    - Extract the audio from a video, this will ask you the format and the quality.

## About DataBase
Database will register all videos downloaded, and how many videos the users download on all-time.

Videos will be register but only the URL and a SHA-256 for **EXACT VIDEO**. Thinking on
    ~~Sutitute SHA for PDQ or DinoHash~~

# TO-DO
1. Allow user selects their default quality and codec
2. Youtube downloads with Node.js and youtube accounts
3. Allow user selects which metadata from videos delete
4. ~~Support the *stars* thing of telegram?~~
5. Keep it all this into the docker, not interested on run this on a non container space
