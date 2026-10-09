from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from bot.config import Settings
from bot.dialogs import DialogStore
from bot.electives import ElectiveStore, merge_lessons
from bot.electives_ui import handle_elective_callback, handle_elective_text
from bot.formatters import format_day, format_month, format_week
from bot.i18n import t
from bot.keyboards import (
    BTN_MONTH,
    BTN_NEXT_WEEK,
    BTN_REFRESH,
    BTN_SUB_OFF,
    BTN_SUB_ON,
    BTN_TODAY,
    BTN_TOMORROW,
    BTN_WEEK,
    reply_keyboard,
    site_link_keyboard,
)
from bot.schedule import TZ, Lesson, ScheduleService, monday_of
from bot.subscriptions import SubscriptionStore
from bot.telegram_api import TelegramClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    bot: TelegramClient
    schedule: ScheduleService
    subscriptions: SubscriptionStore
    electives: ElectiveStore
    dialogs: DialogStore
    settings: Settings


def _reply_kb(ctx: AppContext, chat_id: int) -> dict[str, Any]:
    return reply_keyboard(
        subscribed=ctx.subscriptions.is_subscribed(chat_id)
    )


def _site_kb(ctx: AppContext, day=None) -> dict[str, Any]:
    return site_link_keyboard(ctx.settings, day)


async def _merged(
    ctx: AppContext,
    portal: list[Lesson],
    range_start: date,
    range_end: date,
) -> list[Lesson]:
    return merge_lessons(
        portal,
        ctx.electives.list_all(),
        range_start,
        range_end,
    )


async def send_start(ctx: AppContext, chat_id: int) -> None:
    ctx.dialogs.clear(chat_id)
    sub = (
        t("start.sub_on")
        if ctx.subscriptions.is_subscribed(chat_id)
        else t("start.sub_off")
    )
    await ctx.bot.send_message(
        chat_id,
        t(
            "start.hello",
            sub=sub,
            hour=ctx.settings.reminder_hour,
            minute=ctx.settings.reminder_minute,
            tz=ctx.settings.reminder_tz,
        ),
        parse_mode=None,
        reply_markup=_reply_kb(ctx, chat_id),
    )


async def send_today(ctx: AppContext, chat_id: int) -> None:
    try:
        day = datetime.now(TZ).date()
        portal = await ctx.schedule.today()
        lessons = await _merged(ctx, portal, day, day)
        await ctx.bot.send_message(
            chat_id,
            format_day(lessons, day),
            reply_markup=_site_kb(ctx, day),
        )
    except Exception:
        logger.exception("Ошибка today")
        await ctx.bot.send_message(
            chat_id,
            t("schedule.load_error"),
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )


async def send_tomorrow(ctx: AppContext, chat_id: int) -> None:
    try:
        day = datetime.now(TZ).date() + timedelta(days=1)
        portal = await ctx.schedule.tomorrow()
        lessons = await _merged(ctx, portal, day, day)
        await ctx.bot.send_message(
            chat_id,
            format_day(
                lessons,
                day,
                intro=t("schedule.tomorrow_intro"),
            ),
            reply_markup=_site_kb(ctx, day),
        )
    except Exception:
        logger.exception("Ошибка tomorrow")
        await ctx.bot.send_message(
            chat_id,
            t("schedule.load_error"),
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )


async def _send_week_view(
    ctx: AppContext,
    chat_id: int,
    *,
    anchor: date,
    intro: str,
) -> None:
    try:
        start = monday_of(anchor)
        end = start + timedelta(days=6)
        portal = await ctx.schedule.week(anchor)
        lessons = await _merged(ctx, portal, start, end)
        text = format_week(lessons, anchor, intro=intro)
        chunks = _split_message(text)
        for index, chunk in enumerate(chunks):
            markup = _site_kb(ctx, anchor) if index == len(chunks) - 1 else None
            await ctx.bot.send_message(chat_id, chunk, reply_markup=markup)
    except Exception:
        logger.exception("Ошибка week")
        await ctx.bot.send_message(
            chat_id,
            t("schedule.load_error"),
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )


async def send_week(ctx: AppContext, chat_id: int) -> None:
    await _send_week_view(
        ctx,
        chat_id,
        anchor=datetime.now(TZ).date(),
        intro=t("schedule.week_this_intro"),
    )


async def send_next_week(ctx: AppContext, chat_id: int) -> None:
    await _send_week_view(
        ctx,
        chat_id,
        anchor=datetime.now(TZ).date() + timedelta(days=7),
        intro=t("schedule.week_next_intro"),
    )


async def send_month(ctx: AppContext, chat_id: int) -> None:
    try:
        today = datetime.now(TZ).date()
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        portal = await ctx.schedule.month(year=today.year, month=today.month)
        lessons = await _merged(ctx, portal, month_start, month_end)
        await ctx.bot.send_message(
            chat_id,
            format_month(lessons, year=today.year, month=today.month),
            reply_markup=_site_kb(ctx, today),
        )
    except Exception:
        logger.exception("Ошибка month")
        await ctx.bot.send_message(
            chat_id,
            t("schedule.load_error"),
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )


async def send_refresh(ctx: AppContext, chat_id: int) -> None:
    try:
        lessons = await ctx.schedule.get_lessons(force=True)
        el_count = ctx.electives.count()
        text = (
            t(
                "schedule.refresh_ok_with_electives",
                portal=len(lessons),
                electives=el_count,
            )
            if el_count
            else t("schedule.refresh_ok", portal=len(lessons))
        )
        await ctx.bot.send_message(
            chat_id,
            text,
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )
    except Exception:
        logger.exception("Ошибка refresh")
        await ctx.bot.send_message(
            chat_id,
            t("schedule.refresh_error"),
            parse_mode=None,
            reply_markup=_reply_kb(ctx, chat_id),
        )


async def send_subscribe(ctx: AppContext, chat_id: int) -> None:
    created = ctx.subscriptions.subscribe(chat_id)
    hour = ctx.settings.reminder_hour
    minute = ctx.settings.reminder_minute
    tz_name = ctx.settings.reminder_tz
    text = (
        t("sub.enabled", hour=hour, minute=minute, tz=tz_name)
        if created
        else t("sub.already", hour=hour, minute=minute, tz=tz_name)
    )
    await ctx.bot.send_message(
        chat_id,
        text,
        parse_mode=None,
        reply_markup=_reply_kb(ctx, chat_id),
    )


async def send_unsubscribe(ctx: AppContext, chat_id: int) -> None:
    removed = ctx.subscriptions.unsubscribe(chat_id)
    text = t("sub.disabled") if removed else t("sub.not_subscribed")
    await ctx.bot.send_message(
        chat_id,
        text,
        parse_mode=None,
        reply_markup=_reply_kb(ctx, chat_id),
    )


COMMANDS = {
    "/start": send_start,
    "/menu": send_start,
    "/today": send_today,
    "/tomorrow": send_tomorrow,
    "/week": send_week,
    "/nextweek": send_next_week,
    "/month": send_month,
    "/refresh": send_refresh,
    "/subscribe": send_subscribe,
    "/unsubscribe": send_unsubscribe,
}

BUTTONS = {
    BTN_TODAY: send_today,
    BTN_TOMORROW: send_tomorrow,
    BTN_WEEK: send_week,
    BTN_NEXT_WEEK: send_next_week,
    BTN_MONTH: send_month,
    BTN_REFRESH: send_refresh,
    BTN_SUB_ON: send_subscribe,
    BTN_SUB_OFF: send_unsubscribe,
}


def _split_message(text: str, limit: int = 3900) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    size = 0
    for block in text.split("\n\n"):
        block_size = len(block) + (2 if current else 0)
        if current and size + block_size > limit:
            parts.append("\n\n".join(current))
            current = [block]
            size = len(block)
        else:
            current.append(block)
            size += block_size
    if current:
        parts.append("\n\n".join(current))
    return parts or [text]


async def dispatch_update(ctx: AppContext, update: dict) -> None:
    callback = update.get("callback_query")
    if callback:
        await _handle_callback(ctx, callback)
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    chat_id = int(chat_id)

    if not text:
        await send_start(ctx, chat_id)
        return

    if await handle_elective_text(ctx, chat_id, text):
        return

    dialog = ctx.dialogs.get(chat_id)
    if dialog is not None:
        await ctx.bot.send_message(
            chat_id,
            t("menu.dialog_busy"),
            parse_mode=None,
        )
        return

    button_handler = BUTTONS.get(text)
    if button_handler is not None:
        await button_handler(ctx, chat_id)
        return

    command = text.split()[0].split("@", 1)[0].lower()
    command_handler = COMMANDS.get(command)
    if command_handler is not None:
        await command_handler(ctx, chat_id)
        return

    await ctx.bot.send_message(
        chat_id,
        t("menu.choose"),
        parse_mode=None,
        reply_markup=_reply_kb(ctx, chat_id),
    )


async def _handle_callback(ctx: AppContext, callback: dict) -> None:
    data = (callback.get("data") or "").strip()
    callback_id = callback.get("id")
    message = callback.get("message") or {}
    chat = message.get("chat") or callback.get("from") or {}
    chat_id = chat.get("id")

    if callback_id:
        try:
            await ctx.bot.answer_callback_query(callback_id)
        except Exception:
            logger.debug("answerCallbackQuery failed", exc_info=True)

    if chat_id is None:
        return
    chat_id = int(chat_id)

    if await handle_elective_callback(ctx, chat_id, data):
        return
