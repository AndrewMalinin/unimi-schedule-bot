#!/bin/sh
# Обновление бота на NanoPi / FriendlyWrt:
# git pull → рестарт (код смонтирован) или пересборка, если сменились зависимости.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Нет .env в $ROOT — скопируй из .env.example и пропиши BOT_TOKEN." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Нужен git (opkg install git)." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Нужен docker." >&2
  exit 1
fi

before="$(git rev-parse HEAD)"

echo "==> git pull"
git pull --ff-only

after="$(git rev-parse HEAD)"

need_build=0
if [ "$before" != "$after" ]; then
  if ! git diff --quiet "$before" "$after" -- Dockerfile requirements.txt; then
    need_build=1
  fi
fi

# Первый запуск или контейнер ещё не создавали.
if ! docker compose ps -a --format '{{.Name}}' 2>/dev/null | grep -qx 'unimi-bot'; then
  need_build=1
fi

# Bake требует buildx; на OpenWrt его часто нет.
export COMPOSE_BAKE=false

if [ "$need_build" -eq 1 ]; then
  echo "==> пересборка (Dockerfile / requirements.txt или нет контейнера)"
  docker compose up -d --build --remove-orphans
elif [ "$before" = "$after" ]; then
  echo "==> уже актуально, пересборка не нужна"
else
  echo "==> только код — up + restart (без --build)"
  docker compose up -d --remove-orphans
  docker compose restart bot
fi

echo "==> статус"
docker compose ps
docker compose logs --tail=30 bot

echo "Готово."
