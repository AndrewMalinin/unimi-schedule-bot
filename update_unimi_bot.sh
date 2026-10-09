#!/bin/sh
# Обновление бота на NanoPi / FriendlyWrt:
# git pull → пересборка образа → перезапуск контейнера.
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

echo "==> git pull"
git pull --ff-only

echo "==> docker compose up -d --build"
# Bake требует buildx; на OpenWrt его часто нет.
COMPOSE_BAKE=false docker compose up -d --build --remove-orphans

echo "==> статус"
docker compose ps
docker compose logs --tail=30 bot

echo "Готово."
