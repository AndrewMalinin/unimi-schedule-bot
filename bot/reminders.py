from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.config import Settings
from bot.electives import ElectiveStore, merge_lessons
from bot.formatters import format_tomorrow_reminder
from bot.keyboards import site_link_keyboard
from bot.schedule import ScheduleService, filter_by_day
from bot.subscriptions import SubscriptionStore
from bot.telegram_api import TelegramClient

logger = logging.getLogger(__name__)


def seconds_until_reminder(settings: Settings) -> float:
    tz = ZoneInfo(settings.reminder_tz)
    now = datetime.now(tz)
    target = now.replace(
        hour=settings.reminder_hour,
        minute=settings.reminder_minute,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


async def send_evening_reminders(
    bot: TelegramClient,
    schedule: ScheduleService,
    subscriptions: SubscriptionStore,
    electives: ElectiveStore,
    settings: Settings,
) -> None:
    tz = ZoneInfo(settings.reminder_tz)
    today = datetime.now(tz).date()
    today_iso = today.isoformat()

    if subscriptions.last_reminder_on == today_iso:
        logger.info("Напоминание за %s уже отправлялось — пропуск", today_iso)
        return

    subscribers = subscriptions.list_chat_ids()
    if not subscribers:
        subscriptions.mark_reminder_sent(today_iso)
        logger.info("Подписчиков нет — отмечаем день %s", today_iso)
        return

    tomorrow = today + timedelta(days=1)
    portal = filter_by_day(await schedule.get_lessons(force=True), tomorrow)
    lessons = merge_lessons(
        portal,
        electives.list_all(),
        tomorrow,
        tomorrow,
    )

    subscriptions.mark_reminder_sent(today_iso)
    if not lessons:
        logger.info("На завтра (%s) пар нет — напоминания не шлём", tomorrow)
        return

    ok = 0
    for chat_id in subscribers:
        try:
            await bot.send_message(
                chat_id,
                format_tomorrow_reminder(lessons, tomorrow),
                reply_markup=site_link_keyboard(settings, tomorrow),
            )
            ok += 1
        except Exception:
            logger.exception(
                "Не удалось отправить напоминание chat_id=%s", chat_id
            )

    logger.info("Напоминания отправлены: %s/%s", ok, len(subscribers))


async def reminder_loop(
    bot: TelegramClient,
    schedule: ScheduleService,
    subscriptions: SubscriptionStore,
    electives: ElectiveStore,
    settings: Settings,
) -> None:
    logger.info(
        "Планировщик напоминаний: %02d:%02d %s",
        settings.reminder_hour,
        settings.reminder_minute,
        settings.reminder_tz,
    )
    while True:
        delay = seconds_until_reminder(settings)
        logger.info("Следующее напоминание через %.0f сек", delay)
        await asyncio.sleep(delay)
        try:
            await send_evening_reminders(
                bot, schedule, subscriptions, electives, settings
            )
        except Exception:
            logger.exception("Сбой планировщика напоминаний")
        await asyncio.sleep(60)
