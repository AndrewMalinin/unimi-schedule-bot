from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from bot.i18n import locale, pairs_word, t
from bot.schedule import TZ, Lesson, monday_of

ROOM_RE = re.compile(
    r"^Aula\s+(?P<num>\S+)(?:\s+\[(?P<body>[^\]]+)\])?\s*$",
    re.IGNORECASE,
)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_date(day: date) -> str:
    return f"{day.day}.{day.month}.{day.year}"


def _fmt_kind(kind: str) -> str:
    if not kind:
        return ""
    label = locale.KIND_LABEL.get(kind.lower(), kind.lower())
    return f" [{label}]"


def _fmt_room(room: str) -> str:
    if not room:
        return ""
    match = ROOM_RE.match(room.strip())
    if not match:
        return t("schedule.room", room=_escape(room))
    num = match.group("num")
    body = match.group("body")
    if body:
        return t(
            "schedule.room_with_body",
            num=_escape(num),
            body=_escape(body),
        )
    return t("schedule.room", room=_escape(num))


def _fmt_lesson(lesson: Lesson) -> str:
    start = lesson.start.astimezone(TZ).strftime("%H:%M")
    end = lesson.end.astimezone(TZ).strftime("%H:%M")
    mark = " ⚡" if lesson.is_elective else ""
    lines = [
        f"⏰ <b>{start} — {end}</b>{mark}",
        f"<u>{_escape(lesson.title)}</u> <i>{_escape(_fmt_kind(lesson.kind))}</i>",
    ]
    if lesson.teachers:
        lines.append(f"<i>{_escape(lesson.teachers)}</i>")
    room_line = _fmt_room(lesson.room)
    if room_line:
        lines.append(room_line)
    return "\n".join(lines)


def _day_time_span(lessons: list[Lesson]) -> str:
    if not lessons:
        return ""
    start = min(item.start for item in lessons).astimezone(TZ).strftime("%H:%M")
    end = max(item.end for item in lessons).astimezone(TZ).strftime("%H:%M")
    return t("schedule.day_time_span", start=start, end=end)


def format_day(
    lessons: list[Lesson],
    day: date | None = None,
    *,
    intro: str | None = None,
    highlight_today: bool = False,
) -> str:
    target = day or (lessons[0].day if lessons else datetime.now(TZ).date())
    header_key = (
        "schedule.day_header_today" if highlight_today else "schedule.day_header"
    )
    header = t(
        header_key,
        date=_fmt_date(target),
        weekday=locale.WEEKDAYS_FULL[target.weekday()],
        time_span=_day_time_span(lessons),
    )
    if intro is None:
        intro = t("schedule.today_intro")
    if not lessons:
        empty = t("schedule.empty_day")
        return f"{intro}\n\n{header}\n\n{empty}" if intro else f"{header}\n\n{empty}"
    body = "\n\n".join(_fmt_lesson(item) for item in lessons)
    if not intro:
        return f"{header}\n\n{body}"
    return f"{intro}\n\n{header}\n\n{body}"


def format_week(
    lessons: list[Lesson],
    day: date | None = None,
    *,
    intro: str | None = None,
) -> str:
    anchor = day or datetime.now(TZ).date()
    start = monday_of(anchor)
    end = start + timedelta(days=6)

    by_day: dict[date, list[Lesson]] = defaultdict(list)
    for lesson in lessons:
        by_day[lesson.day].append(lesson)

    if intro is None:
        intro = t("schedule.week_intro")
    parts = [
        intro,
        t(
            "schedule.week_range",
            start=_fmt_date(start),
            end=_fmt_date(end),
        ),
        '\n',
    ]

    if not lessons:
        parts.append("\n" + t("schedule.empty_week"))
        return "\n".join(parts)

    today = datetime.now(TZ).date()
    day_blocks: list[str] = []
    for offset in range(7):
        current = start + timedelta(days=offset)
        day_lessons = by_day.get(current, [])
        day_blocks.append(
            format_day(
                day_lessons,
                current,
                intro="",
                highlight_today=(current == today),
            ).lstrip("\n")
        )

    if not day_blocks:
        parts.append("\n" + t("schedule.empty_week"))
        return "\n".join(parts)

    #parts.append("")
    parts.append(("\n\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n").join(day_blocks))
    return "\n".join(parts)


def format_month(
    lessons: list[Lesson],
    *,
    year: int | None = None,
    month: int | None = None,
) -> str:
    today = datetime.now(TZ).date()
    year = year or today.year
    month = month or today.month

    counts: dict[date, int] = defaultdict(int)
    for lesson in lessons:
        if lesson.day.year == year and lesson.day.month == month:
            counts[lesson.day] += 1

    title = t(
        "schedule.month_title",
        month=locale.MONTHS[month].capitalize(),
        year=year,
    )
    if not counts:
        return f"{title}\n\n{t('schedule.empty_month')}"

    lines = [title, "", t("schedule.month_days_header")]
    total = 0
    for day in sorted(counts):
        n = counts[day]
        total += n
        lines.append(
            f"• {locale.WEEKDAYS_SHORT[day.weekday()]} {_fmt_date(day)} — "
            f"<b>{n}</b> {pairs_word(n)}"
        )
    lines.append("")
    lines.append(
        t("schedule.month_total", total=total, pairs_word=pairs_word(total))
    )
    return "\n".join(lines)


def format_tomorrow_reminder(lessons: list[Lesson], day: date) -> str:
    return format_day(
        lessons,
        day,
        intro=t("schedule.reminder_intro"),
    )
