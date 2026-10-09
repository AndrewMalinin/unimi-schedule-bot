from __future__ import annotations

import asyncio
import logging
import sys

from bot.config import load_settings
from bot.dialogs import DialogStore
from bot.electives import ElectiveStore
from bot.handlers import AppContext, dispatch_update
from bot.reminders import reminder_loop
from bot.schedule import ScheduleService
from bot.subscriptions import SubscriptionStore
from bot.telegram_api import TelegramClient


async def poll_loop(ctx: AppContext) -> None:
    log = logging.getLogger(__name__)
    offset: int | None = None
    while True:
        updates = await ctx.bot.get_updates(offset=offset, timeout=30)
        for update in updates:
            offset = int(update["update_id"]) + 1
            try:
                await dispatch_update(ctx, update)
            except Exception:
                log.exception(
                    "Ошибка обработки update=%s", update.get("update_id")
                )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    log = logging.getLogger(__name__)

    settings = load_settings()
    schedule = ScheduleService(settings)
    subscriptions = SubscriptionStore(settings.subscribers_path)
    electives = ElectiveStore(settings.electives_path)
    dialogs = DialogStore()
    bot = TelegramClient(settings.bot_token)
    ctx = AppContext(
        bot=bot,
        schedule=schedule,
        subscriptions=subscriptions,
        electives=electives,
        dialogs=dialogs,
        settings=settings,
    )

    try:
        me = await bot.get_me()
        log.info(
            "Бот @%s запущен (corso=%s anno=%s anno2=%s)",
            me.get("username"),
            settings.unimi_corso,
            settings.unimi_anno,
            settings.unimi_anno2,
        )
        log.info(
            "Подписчиков: %s | напоминание %02d:%02d %s",
            len(subscriptions.list_chat_ids()),
            settings.reminder_hour,
            settings.reminder_minute,
            settings.reminder_tz,
        )

        await asyncio.gather(
            poll_loop(ctx),
            reminder_loop(
                bot, schedule, subscriptions, electives, settings
            ),
        )
    finally:
        await bot.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановка бота.")
