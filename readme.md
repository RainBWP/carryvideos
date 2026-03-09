# CarryVideos
Simple Telegram Bot Downloader video

## Run this
You need to create a `.env` file for bot connection
```.env
BOT_TOKEN=[YourTokenHere]
```

### Now u need run this

```sh
docker compose pull
docker compose build --no-cache
docker compose up -d
docker compose logs -f --tail=100
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