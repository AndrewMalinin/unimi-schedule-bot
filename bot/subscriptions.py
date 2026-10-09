from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class SubscriptionStore:
    """Простое хранилище подписчиков в JSON."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._chat_ids: set[int] = set()
        self._last_reminder_on: str | None = None
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._chat_ids = {int(x) for x in raw.get("chat_ids", [])}
            self._last_reminder_on = raw.get("last_reminder_on")
        except Exception:
            logger.exception("Не удалось прочитать %s", self._path)
            self._chat_ids = set()
            self._last_reminder_on = None

    def _save(self) -> None:
        payload = {
            "chat_ids": sorted(self._chat_ids),
            "last_reminder_on": self._last_reminder_on,
        }
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def subscribe(self, chat_id: int) -> bool:
        """True если подписка новая."""
        with self._lock:
            if chat_id in self._chat_ids:
                return False
            self._chat_ids.add(chat_id)
            self._save()
            return True

    def unsubscribe(self, chat_id: int) -> bool:
        """True если подписка была."""
        with self._lock:
            if chat_id not in self._chat_ids:
                return False
            self._chat_ids.discard(chat_id)
            self._save()
            return True

    def is_subscribed(self, chat_id: int) -> bool:
        with self._lock:
            return chat_id in self._chat_ids

    def list_chat_ids(self) -> list[int]:
        with self._lock:
            return sorted(self._chat_ids)

    @property
    def last_reminder_on(self) -> str | None:
        with self._lock:
            return self._last_reminder_on

    def mark_reminder_sent(self, day_iso: str) -> None:
        with self._lock:
            self._last_reminder_on = day_iso
            self._save()
