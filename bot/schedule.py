from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

import httpx
from icalendar import Calendar

from bot.config import Settings

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Rome")
ICS_URL = (
    "https://orari.unimi.it/PortaleStudenti/export/ec_download_ical_list.php"
)
USER_AGENT = (
    "Mozilla/5.0 (compatible; UnimiScheduleBot/1.0; +local-telegram-bot)"
)

# "Course Title Teacher Name Aula 12 [Building] Lezione"
SUMMARY_RE = re.compile(
    r"^(?P<body>.+?)\s+"
    r"(?P<room>Aula\s+\S+(?:\s+\[[^\]]+\])?)\s*"
    r"(?P<kind>Lezione|Esercitazione|Laboratorio|Seminar|Seminario)?\s*$",
    re.IGNORECASE,
)

# Преподаватели в конце: "CIABARRI LUCA" или "Masullo Juan, Sala Roberta"
TEACHERS_ALLCAPS_RE = re.compile(
    r"^(?P<title>.+?)\s+(?P<teachers>[A-Z]{2,}(?:\s+[A-Za-z]+)+)$"
)
TEACHERS_NAMES_RE = re.compile(
    r"^(?P<title>.+?)\s+"
    r"(?P<teachers>"
    r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’\-]+\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’\-]+"
    r"(?:,\s*[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’\-]+\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’\-]+)*"
    r")$"
)


@dataclass(frozen=True, slots=True)
class Lesson:
    start: datetime
    end: datetime
    title: str
    teachers: str
    room: str
    kind: str
    raw_summary: str
    is_elective: bool = False

    @property
    def day(self) -> date:
        return self.start.astimezone(TZ).date()


def _split_course_teachers(body: str) -> tuple[str, str]:
    text = body.strip()
    match = TEACHERS_ALLCAPS_RE.match(text)
    if match:
        return match.group("title").strip(), match.group("teachers").strip()
    match = TEACHERS_NAMES_RE.match(text)
    if match:
        return match.group("title").strip(), match.group("teachers").strip()
    return text, ""


def _parse_summary(summary: str) -> tuple[str, str, str, str]:
    text = " ".join(summary.split())
    match = SUMMARY_RE.match(text)
    if not match:
        title, teachers = _split_course_teachers(text)
        return title, teachers, "", ""
    title, teachers = _split_course_teachers(match.group("body").strip())
    room = (match.group("room") or "").strip()
    kind = (match.group("kind") or "").strip()
    return title, teachers, room, kind


def _to_local_dt(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=TZ)
        return value.astimezone(TZ)
    return datetime.combine(value, dt_time.min, tzinfo=TZ)


def _normalize_ics(ics_bytes: bytes) -> bytes:
    # EasyStaff иногда отдаёт DTEND=...T240000 — это невалидно для RFC 5545.
    return ics_bytes.replace(b"T240000", b"T235959")


def parse_lessons(ics_bytes: bytes) -> list[Lesson]:
    calendar = Calendar.from_ical(_normalize_ics(ics_bytes))
    lessons: list[Lesson] = []

    for component in calendar.walk("VEVENT"):
        summary = str(component.get("SUMMARY") or "").strip()
        if not summary:
            continue

        start_prop = component.get("DTSTART")
        end_prop = component.get("DTEND")
        if start_prop is None:
            continue

        try:
            start = _to_local_dt(start_prop.dt)
            if end_prop is not None:
                end = _to_local_dt(end_prop.dt)
            else:
                end = start + timedelta(hours=2)
        except Exception:
            logger.debug("Пропуск события с битой датой: %s", summary[:80])
            continue

        # Полнодневные заметки вроде "Didactic activities are suspended"
        if start.time() == dt_time(0, 0) and end.time() in {
            dt_time(0, 0),
            dt_time(23, 59, 59),
        }:
            if "aula" not in summary.lower():
                continue

        title, teachers, room, kind = _parse_summary(summary)
        lessons.append(
            Lesson(
                start=start,
                end=end,
                title=title,
                teachers=teachers,
                room=room,
                kind=kind,
                raw_summary=summary,
            )
        )

    lessons.sort(key=lambda item: item.start)
    return lessons


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def filter_by_day(lessons: Iterable[Lesson], day: date) -> list[Lesson]:
    return [lesson for lesson in lessons if lesson.day == day]


def filter_by_week(lessons: Iterable[Lesson], day: date) -> list[Lesson]:
    start = monday_of(day)
    end = start + timedelta(days=6)
    return [lesson for lesson in lessons if start <= lesson.day <= end]


def filter_by_month(
    lessons: Iterable[Lesson], *, year: int, month: int
) -> list[Lesson]:
    return [
        lesson
        for lesson in lessons
        if lesson.day.year == year and lesson.day.month == month
    ]


class ScheduleService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._cached_at = 0.0
        self._lessons: list[Lesson] = []

    def _build_params(self) -> dict[str, str]:
        today = datetime.now(TZ).date()
        return {
            "view": "easycourse",
            "include": "corso",
            "anno": self._settings.unimi_anno,
            "corso": self._settings.unimi_corso,
            "anno2[0]": self._settings.unimi_anno2,
            "visualizzazione_orario": "cal",
            "_lang": self._settings.unimi_lang,
            "date": today.strftime("%d-%m-%Y"),
        }

    async def _download(self) -> bytes:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(ICS_URL, params=self._build_params())
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/calendar" not in content_type and not response.content.startswith(
                b"BEGIN:VCALENDAR"
            ):
                raise RuntimeError(
                    f"Ожидался ICS, получен content-type={content_type!r}"
                )
            return response.content

    async def get_lessons(self, *, force: bool = False) -> list[Lesson]:
        async with self._lock:
            age = time.monotonic() - self._cached_at
            if (
                not force
                and self._lessons
                and age < self._settings.cache_ttl_seconds
            ):
                return list(self._lessons)

            logger.info("Загрузка ICS расписания Unimi…")
            raw = await self._download()
            self._lessons = parse_lessons(raw)
            self._cached_at = time.monotonic()
            logger.info("Загружено занятий: %s", len(self._lessons))
            return list(self._lessons)

    async def today(self) -> list[Lesson]:
        lessons = await self.get_lessons()
        return filter_by_day(lessons, datetime.now(TZ).date())

    async def tomorrow(self) -> list[Lesson]:
        lessons = await self.get_lessons()
        day = datetime.now(TZ).date() + timedelta(days=1)
        return filter_by_day(lessons, day)

    async def week(self, day: date | None = None) -> list[Lesson]:
        lessons = await self.get_lessons()
        return filter_by_week(lessons, day or datetime.now(TZ).date())

    async def next_week(self) -> list[Lesson]:
        anchor = datetime.now(TZ).date() + timedelta(days=7)
        return await self.week(anchor)

    async def month(
        self, *, year: int | None = None, month: int | None = None
    ) -> list[Lesson]:
        today = datetime.now(TZ).date()
        lessons = await self.get_lessons()
        return filter_by_month(
            lessons,
            year=year or today.year,
            month=month or today.month,
        )
