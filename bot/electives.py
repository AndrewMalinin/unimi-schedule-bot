from __future__ import annotations

import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from threading import Lock

from bot.i18n import locale, t
from bot.schedule import TZ, Lesson, monday_of

logger = logging.getLogger(__name__)

# Совместимость со старым импортом
KIND_CHOICES = locale.KIND_TO_CODE
KIND_LABEL = locale.KIND_LABEL
WEEKDAY_SHORT = locale.WEEKDAYS_SHORT
WEEKDAY_RU = locale.WEEKDAYS_FULL


@dataclass
class Elective:
    id: str
    owner_id: int  # кто создал — только он может править/удалять
    title: str
    teachers: str
    kind: str
    weekdays: list[int]  # 0=пн … 6=вс, можно несколько
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    room: str
    start_date: str  # YYYY-MM-DD — с этой даты (включительно)
    weeks: int  # сколько учебных недель
    interval_weeks: int  # 1 = каждую неделю, 2 = раз в 2 недели

    def to_dict(self) -> dict:
        return asdict(self)

    def is_owned_by(self, user_id: int) -> bool:
        return self.owner_id == user_id

    @classmethod
    def from_dict(cls, raw: dict) -> Elective:
        if "weekdays" in raw and raw["weekdays"] is not None:
            weekdays = sorted({int(x) for x in raw["weekdays"]})
        elif "weekday" in raw and raw["weekday"] is not None:
            weekdays = [int(raw["weekday"])]
        else:
            weekdays = [0]
        if not weekdays:
            weekdays = [0]
        # Миграция: старое поле chat_id → owner_id
        owner_raw = raw.get("owner_id", raw.get("chat_id", 0))
        return cls(
            id=str(raw["id"]),
            owner_id=int(owner_raw),
            title=str(raw["title"]),
            teachers=str(raw.get("teachers") or ""),
            kind=str(raw.get("kind") or "lezione"),
            weekdays=weekdays,
            start_time=str(raw["start_time"]),
            end_time=str(raw["end_time"]),
            room=str(raw.get("room") or ""),
            start_date=str(raw["start_date"]),
            weeks=int(raw["weeks"]),
            interval_weeks=max(1, int(raw.get("interval_weeks") or 1)),
        )


def _parse_hhmm(value: str) -> dt_time:
    hour, minute = value.split(":")
    return dt_time(int(hour), int(minute))


def _format_room(room: str) -> str:
    text = room.strip()
    if not text:
        return ""
    if text.lower().startswith("aula"):
        return text
    if "," in text:
        num, body = text.split(",", 1)
        return f"Aula {num.strip()} [{body.strip()}]"
    return f"Aula {text}"


def expand_elective(
    elective: Elective,
    range_start: date,
    range_end: date,
) -> list[Lesson]:
    period_start = date.fromisoformat(elective.start_date)
    week0 = monday_of(period_start)
    start_t = _parse_hhmm(elective.start_time)
    end_t = _parse_hhmm(elective.end_time)
    room = _format_room(elective.room)

    lessons: list[Lesson] = []
    for active in range(elective.weeks):
        week_monday = week0 + timedelta(
            weeks=active * elective.interval_weeks
        )
        for weekday in sorted(elective.weekdays):
            day = week_monday + timedelta(days=weekday)
            if day < period_start:
                continue
            if not (range_start <= day <= range_end):
                continue
            lessons.append(
                Lesson(
                    start=datetime.combine(day, start_t, tzinfo=TZ),
                    end=datetime.combine(day, end_t, tzinfo=TZ),
                    title=elective.title,
                    teachers=elective.teachers,
                    room=room,
                    kind=elective.kind,
                    raw_summary=f"elective:{elective.id}",
                    is_elective=True,
                )
            )
    return lessons


def merge_lessons(
    portal: list[Lesson],
    electives: list[Elective],
    range_start: date,
    range_end: date,
) -> list[Lesson]:
    extra: list[Lesson] = []
    for item in electives:
        extra.extend(expand_elective(item, range_start, range_end))
    return sorted([*portal, *extra], key=lambda lesson: lesson.start)


class ElectiveStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._items: dict[str, Elective] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            items = raw.get("items", raw if isinstance(raw, list) else [])
            self._items = {
                item["id"]: Elective.from_dict(item) for item in items
            }
            # Пересохраняем, чтобы мигрировать weekday → weekdays
            self._save()
        except Exception:
            logger.exception("Не удалось прочитать %s", self._path)
            self._items = {}

    def _save(self) -> None:
        payload = {
            "items": [item.to_dict() for item in self._items.values()]
        }
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_all(self) -> list[Elective]:
        with self._lock:
            return sorted(
                self._items.values(),
                key=lambda e: (
                    min(e.weekdays) if e.weekdays else 0,
                    e.start_time,
                    e.title.lower(),
                ),
            )

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def get(self, elective_id: str) -> Elective | None:
        with self._lock:
            return self._items.get(elective_id)

    def add(self, elective: Elective) -> Elective:
        with self._lock:
            self._items[elective.id] = elective
            self._save()
            return elective

    def update(self, elective: Elective) -> Elective:
        with self._lock:
            if elective.id not in self._items:
                raise KeyError(elective.id)
            self._items[elective.id] = elective
            self._save()
            return elective

    def delete(self, elective_id: str, owner_id: int) -> bool:
        with self._lock:
            item = self._items.get(elective_id)
            if item is None or not item.is_owned_by(owner_id):
                return False
            del self._items[elective_id]
            self._save()
            return True

    def expand_all(
        self,
        range_start: date,
        range_end: date,
    ) -> list[Lesson]:
        return merge_lessons([], self.list_all(), range_start, range_end)


def new_id() -> str:
    return secrets.token_hex(4)


def format_weekdays(weekdays: list[int]) -> str:
    return ", ".join(WEEKDAY_SHORT[d] for d in sorted(weekdays))


def summarize_elective(elective: Elective) -> str:
    kind = KIND_LABEL.get(elective.kind, elective.kind)
    interval = (
        t("el.interval_weekly")
        if elective.interval_weeks == 1
        else t("el.interval_every_n", n=elective.interval_weeks)
    )
    start = date.fromisoformat(elective.start_date)
    return t(
        "el.summary",
        title=elective.title,
        kind=kind,
        weekdays=format_weekdays(elective.weekdays),
        start_time=elective.start_time,
        end_time=elective.end_time,
        teachers=elective.teachers or t("el.no_teacher"),
        room=elective.room or t("el.no_room"),
        interval=interval,
        weeks=elective.weeks,
        start_date=f"{start.day}.{start.month}.{start.year}",
    )
