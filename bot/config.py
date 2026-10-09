from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    unimi_anno: str
    unimi_corso: str
    unimi_anno2: str
    unimi_lang: str
    cache_ttl_seconds: int
    reminder_hour: int
    reminder_minute: int
    reminder_tz: str
    subscribers_path: Path
    electives_path: Path


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token.startswith("123456"):
        raise RuntimeError(
            "Задайте BOT_TOKEN в файле .env (получите у @BotFather)."
        )

    return Settings(
        bot_token=token,
        unimi_anno=os.getenv("UNIMI_ANNO", "2026").strip(),
        unimi_corso=os.getenv("UNIMI_CORSO", "BBJ").strip(),
        unimi_anno2=os.getenv("UNIMI_ANNO2", "BBJ-0|1").strip(),
        unimi_lang=os.getenv("UNIMI_LANG", "en").strip(),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "1800")),
        reminder_hour=int(os.getenv("REMINDER_HOUR", "20")),
        reminder_minute=int(os.getenv("REMINDER_MINUTE", "0")),
        reminder_tz=os.getenv("REMINDER_TZ", "Europe/Rome").strip(),
        subscribers_path=_resolve_path(
            os.getenv("SUBSCRIBERS_PATH", "data/subscribers.json").strip()
        ),
        electives_path=_resolve_path(
            os.getenv("ELECTIVES_PATH", "data/electives.json").strip()
        ),
    )
