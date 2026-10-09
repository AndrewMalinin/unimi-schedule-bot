from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from bot.electives import Elective, format_weekdays, new_id, summarize_elective
from bot.i18n import locale, t
from bot.keyboards import (
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_EL_ADD,
    BTN_EL_BACK,
    BTN_EL_LIST,
    BTN_ELECTIVES,
    BTN_INTERVAL_1,
    BTN_INTERVAL_2,
    BTN_SKIP_TEACHER,
    BTN_WD,
    BTN_WD_DONE,
    cancel_keyboard,
    confirm_keyboard,
    edit_fields_keyboard,
    elective_actions_keyboard,
    electives_menu_keyboard,
    interval_keyboard,
    kind_keyboard,
    reply_keyboard,
    teachers_keyboard,
    weekdays_multiselect_keyboard,
)
from bot.schedule import TZ

if TYPE_CHECKING:
    from bot.handlers import AppContext

logger = logging.getLogger(__name__)

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
DATE_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")
WD_INDEX = {name: idx for idx, name in enumerate(BTN_WD)}
KIND_CHOICES = locale.KIND_TO_CODE


def _main_kb(ctx: AppContext, chat_id: int) -> dict:
    return reply_keyboard(
        subscribed=ctx.subscriptions.is_subscribed(chat_id)
    )


def _parse_weekday_button(text: str) -> int | None:
    raw = text.strip()
    if raw.startswith("✓ "):
        raw = raw[2:].strip()
    return WD_INDEX.get(raw)


def _selected_set(data: dict) -> set[int]:
    return {int(x) for x in data.get("weekdays") or []}


def _weekdays_prompt(selected: set[int]) -> str:
    chosen = (
        format_weekdays(sorted(selected))
        if selected
        else t("el.weekdays_none")
    )
    return t("el.weekdays_prompt", chosen=chosen)


async def open_electives_menu(ctx: AppContext, chat_id: int) -> None:
    ctx.dialogs.clear(chat_id)
    await ctx.bot.send_message(
        chat_id,
        t("el.menu"),
        parse_mode=None,
        reply_markup=electives_menu_keyboard(),
    )


async def cancel_dialog(ctx: AppContext, chat_id: int) -> None:
    ctx.dialogs.clear(chat_id)
    await ctx.bot.send_message(
        chat_id,
        t("el.cancelled"),
        parse_mode=None,
        reply_markup=electives_menu_keyboard(),
    )


async def start_add(ctx: AppContext, chat_id: int) -> None:
    ctx.dialogs.start(chat_id, "elective_add", "title")
    await ctx.bot.send_message(
        chat_id,
        t("el.add_title"),
        parse_mode=None,
        reply_markup=cancel_keyboard(),
    )


async def show_list(ctx: AppContext, chat_id: int) -> None:
    ctx.dialogs.clear(chat_id)
    items = ctx.electives.list_all()
    if not items:
        await ctx.bot.send_message(
            chat_id,
            t("el.empty"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        return

    await ctx.bot.send_message(
        chat_id,
        t("el.list_header", count=len(items)),
        parse_mode=None,
        reply_markup=electives_menu_keyboard(),
    )
    for item in items:
        markup = (
            elective_actions_keyboard(item.id)
            if item.is_owned_by(chat_id)
            else None
        )
        await ctx.bot.send_message(
            chat_id,
            summarize_elective(item),
            reply_markup=markup,
        )


def _parse_time(text: str) -> str | None:
    match = TIME_RE.match(text.strip())
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"


def _parse_date(text: str) -> date | None:
    raw = text.strip().lower()
    today = datetime.now(TZ).date()
    if raw in locale.DATE_TODAY_ALIASES:
        return today
    if raw in locale.DATE_TOMORROW_ALIASES:
        return today + timedelta(days=1)
    match = DATE_RE.match(raw)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


async def _ask(ctx: AppContext, chat_id: int, text: str, markup: dict) -> None:
    await ctx.bot.send_message(
        chat_id, text, parse_mode=None, reply_markup=markup
    )


async def _toggle_weekday(
    ctx: AppContext, chat_id: int, text: str, *, step_name: str
) -> bool:
    dialog = ctx.dialogs.get(chat_id)
    if dialog is None:
        return False

    if text == BTN_WD_DONE:
        selected = sorted(_selected_set(dialog.data))
        if not selected:
            await _ask(
                ctx,
                chat_id,
                t("el.weekdays_need_one"),
                weekdays_multiselect_keyboard(set()),
            )
            return True
        if dialog.name == "elective_add":
            ctx.dialogs.update(
                chat_id, step="start_date", weekdays=selected
            )
            await _ask(
                ctx,
                chat_id,
                t("el.step_start_date"),
                cancel_keyboard(),
            )
            return True
        elective_id = dialog.data.get("id")
        elective = ctx.electives.get(elective_id) if elective_id else None
        if elective is None or not elective.is_owned_by(chat_id):
            await cancel_dialog(ctx, chat_id)
            return True
        updated = Elective(**elective.to_dict())
        updated.weekdays = selected
        ctx.electives.update(updated)
        ctx.dialogs.clear(chat_id)
        await ctx.bot.send_message(
            chat_id,
            t("el.saved"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        await ctx.bot.send_message(
            chat_id,
            summarize_elective(updated),
            reply_markup=elective_actions_keyboard(updated.id),
        )
        return True

    weekday = _parse_weekday_button(text)
    if weekday is None:
        return False

    selected = _selected_set(dialog.data)
    if weekday in selected:
        selected.remove(weekday)
    else:
        selected.add(weekday)
    ctx.dialogs.update(chat_id, step=step_name, weekdays=sorted(selected))
    await _ask(
        ctx,
        chat_id,
        _weekdays_prompt(selected),
        weekdays_multiselect_keyboard(selected),
    )
    return True


async def handle_add_step(
    ctx: AppContext, chat_id: int, text: str
) -> bool:
    dialog = ctx.dialogs.get(chat_id)
    if dialog is None or dialog.name != "elective_add":
        return False

    if text == BTN_CANCEL:
        await cancel_dialog(ctx, chat_id)
        return True

    step = dialog.step
    data = dialog.data

    if step == "weekdays":
        handled = await _toggle_weekday(
            ctx, chat_id, text, step_name="weekdays"
        )
        if handled:
            return True
        await _ask(
            ctx,
            chat_id,
            _weekdays_prompt(_selected_set(data)),
            weekdays_multiselect_keyboard(_selected_set(data)),
        )
        return True

    if step == "title":
        if len(text) < 2:
            await _ask(
                ctx, chat_id, t("el.err_title_short"), cancel_keyboard()
            )
            return True
        ctx.dialogs.update(chat_id, step="teachers", title=text)
        await _ask(ctx, chat_id, t("el.step_teachers"), teachers_keyboard())
        return True

    if step == "teachers":
        teachers = "" if text == BTN_SKIP_TEACHER else text
        ctx.dialogs.update(chat_id, step="kind", teachers=teachers)
        await _ask(ctx, chat_id, t("el.step_kind"), kind_keyboard())
        return True

    if step == "kind":
        kind = KIND_CHOICES.get(text)
        if kind is None:
            await _ask(ctx, chat_id, t("el.err_kind"), kind_keyboard())
            return True
        ctx.dialogs.update(chat_id, step="start_time", kind=kind)
        await _ask(ctx, chat_id, t("el.step_start_time"), cancel_keyboard())
        return True

    if step == "start_time":
        value = _parse_time(text)
        if value is None:
            await _ask(ctx, chat_id, t("el.err_time"), cancel_keyboard())
            return True
        ctx.dialogs.update(chat_id, step="end_time", start_time=value)
        await _ask(ctx, chat_id, t("el.step_end_time"), cancel_keyboard())
        return True

    if step == "end_time":
        value = _parse_time(text)
        if value is None:
            await _ask(ctx, chat_id, t("el.err_time_end"), cancel_keyboard())
            return True
        if value <= data["start_time"]:
            await _ask(
                ctx, chat_id, t("el.err_time_order"), cancel_keyboard()
            )
            return True
        ctx.dialogs.update(chat_id, step="room", end_time=value)
        await _ask(ctx, chat_id, t("el.step_room"), cancel_keyboard())
        return True

    if step == "room":
        ctx.dialogs.update(
            chat_id, step="weekdays", room=text.strip(), weekdays=[]
        )
        await _ask(
            ctx,
            chat_id,
            t("el.step_weekdays", prompt=_weekdays_prompt(set())),
            weekdays_multiselect_keyboard(set()),
        )
        return True

    if step == "start_date":
        value = _parse_date(text)
        if value is None:
            await _ask(ctx, chat_id, t("el.err_date"), cancel_keyboard())
            return True
        ctx.dialogs.update(chat_id, step="weeks", start_date=value.isoformat())
        await _ask(ctx, chat_id, t("el.step_weeks"), cancel_keyboard())
        return True

    if step == "weeks":
        if not text.isdigit() or int(text) < 1 or int(text) > 52:
            await _ask(ctx, chat_id, t("el.err_weeks"), cancel_keyboard())
            return True
        ctx.dialogs.update(chat_id, step="interval", weeks=int(text))
        await _ask(ctx, chat_id, t("el.step_interval"), interval_keyboard())
        return True

    if step == "interval":
        if text == BTN_INTERVAL_1:
            interval = 1
        elif text == BTN_INTERVAL_2:
            interval = 2
        else:
            await _ask(
                ctx, chat_id, t("el.err_interval"), interval_keyboard()
            )
            return True
        ctx.dialogs.update(chat_id, step="confirm", interval_weeks=interval)
        draft = _draft_from_data(chat_id, dialog.data)
        await ctx.bot.send_message(
            chat_id,
            t("el.review", summary=summarize_elective(draft)),
        )
        await _ask(ctx, chat_id, t("el.save_q"), confirm_keyboard())
        return True

    if step == "confirm":
        if text != BTN_CONFIRM:
            await _ask(ctx, chat_id, t("el.save_hint"), confirm_keyboard())
            return True
        elective = _draft_from_data(chat_id, data)
        elective.id = new_id()
        ctx.electives.add(elective)
        ctx.dialogs.clear(chat_id)
        await ctx.bot.send_message(
            chat_id,
            t("el.created"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        await ctx.bot.send_message(
            chat_id,
            summarize_elective(elective),
            reply_markup=elective_actions_keyboard(elective.id),
        )
        return True

    return True


def _draft_from_data(owner_id: int, data: dict) -> Elective:
    return Elective(
        id=data.get("id") or "draft",
        owner_id=owner_id,
        title=data["title"],
        teachers=data.get("teachers") or "",
        kind=data["kind"],
        weekdays=sorted({int(x) for x in data.get("weekdays") or [0]}),
        start_time=data["start_time"],
        end_time=data["end_time"],
        room=data.get("room") or "",
        start_date=data["start_date"],
        weeks=int(data["weeks"]),
        interval_weeks=int(data.get("interval_weeks") or 1),
    )


async def handle_edit_step(
    ctx: AppContext, chat_id: int, text: str
) -> bool:
    dialog = ctx.dialogs.get(chat_id)
    if dialog is None or dialog.name != "elective_edit":
        return False

    if text == BTN_CANCEL:
        await cancel_dialog(ctx, chat_id)
        return True

    if dialog.step == "weekdays":
        handled = await _toggle_weekday(
            ctx, chat_id, text, step_name="weekdays"
        )
        if handled:
            return True
        selected = _selected_set(dialog.data)
        await _ask(
            ctx,
            chat_id,
            _weekdays_prompt(selected),
            weekdays_multiselect_keyboard(selected),
        )
        return True

    elective_id = dialog.data.get("id")
    elective = ctx.electives.get(elective_id) if elective_id else None
    if elective is None or not elective.is_owned_by(chat_id):
        ctx.dialogs.clear(chat_id)
        await ctx.bot.send_message(
            chat_id,
            t("el.not_found") if elective is None else t("el.not_owner"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        return True

    field = dialog.step
    updated = Elective(**elective.to_dict())

    if field == "title":
        if len(text) < 2:
            await _ask(
                ctx, chat_id, t("el.err_title_short_edit"), cancel_keyboard()
            )
            return True
        updated.title = text
    elif field == "teachers":
        updated.teachers = "" if text == BTN_SKIP_TEACHER else text
    elif field == "kind":
        kind = KIND_CHOICES.get(text)
        if kind is None:
            await _ask(ctx, chat_id, t("el.err_kind"), kind_keyboard())
            return True
        updated.kind = kind
    elif field == "start_time":
        value = _parse_time(text)
        if value is None:
            await _ask(
                ctx, chat_id, t("el.err_time_short"), cancel_keyboard()
            )
            return True
        updated.start_time = value
    elif field == "end_time":
        value = _parse_time(text)
        if value is None or value <= updated.start_time:
            await _ask(
                ctx,
                chat_id,
                t("el.err_time_order_short"),
                cancel_keyboard(),
            )
            return True
        updated.end_time = value
    elif field == "room":
        updated.room = text.strip()
    elif field == "weeks":
        if not text.isdigit() or not (1 <= int(text) <= 52):
            await _ask(
                ctx, chat_id, t("el.err_weeks_short"), cancel_keyboard()
            )
            return True
        updated.weeks = int(text)
    elif field == "start_date":
        value = _parse_date(text)
        if value is None:
            await _ask(
                ctx, chat_id, t("el.err_date_short"), cancel_keyboard()
            )
            return True
        updated.start_date = value.isoformat()
    elif field == "interval_weeks":
        if text == BTN_INTERVAL_1:
            updated.interval_weeks = 1
        elif text == BTN_INTERVAL_2:
            updated.interval_weeks = 2
        else:
            await _ask(
                ctx,
                chat_id,
                t("el.err_interval_short"),
                interval_keyboard(),
            )
            return True
    else:
        ctx.dialogs.clear(chat_id)
        await cancel_dialog(ctx, chat_id)
        return True

    ctx.electives.update(updated)
    ctx.dialogs.clear(chat_id)
    await ctx.bot.send_message(
        chat_id,
        t("el.saved"),
        parse_mode=None,
        reply_markup=electives_menu_keyboard(),
    )
    await ctx.bot.send_message(
        chat_id,
        summarize_elective(updated),
        reply_markup=elective_actions_keyboard(updated.id),
    )
    return True


async def handle_elective_text(
    ctx: AppContext, chat_id: int, text: str
) -> bool:
    if text == BTN_ELECTIVES:
        await open_electives_menu(ctx, chat_id)
        return True
    if text == BTN_EL_BACK:
        ctx.dialogs.clear(chat_id)
        await ctx.bot.send_message(
            chat_id,
            t("menu.main"),
            parse_mode=None,
            reply_markup=_main_kb(ctx, chat_id),
        )
        return True
    if text == BTN_EL_ADD:
        await start_add(ctx, chat_id)
        return True
    if text == BTN_EL_LIST:
        await show_list(ctx, chat_id)
        return True

    dialog = ctx.dialogs.get(chat_id)
    if dialog is None:
        return False
    if dialog.name == "elective_add":
        return await handle_add_step(ctx, chat_id, text)
    if dialog.name == "elective_edit":
        return await handle_edit_step(ctx, chat_id, text)
    return False


async def handle_elective_callback(
    ctx: AppContext, chat_id: int, data: str
) -> bool:
    if not data.startswith("el:"):
        return False

    parts = data.split(":")
    if len(parts) < 3:
        return True

    action = parts[1]
    elective_id = parts[2]
    elective = ctx.electives.get(elective_id)
    if elective is None:
        await ctx.bot.send_message(
            chat_id,
            t("el.not_found"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        return True
    if not elective.is_owned_by(chat_id):
        await ctx.bot.send_message(
            chat_id,
            t("el.not_owner"),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        return True

    if action == "del":
        ctx.electives.delete(elective_id, chat_id)
        ctx.dialogs.clear(chat_id)
        await ctx.bot.send_message(
            chat_id,
            t("el.deleted", title=elective.title),
            parse_mode=None,
            reply_markup=electives_menu_keyboard(),
        )
        return True

    if action == "edit":
        await ctx.bot.send_message(
            chat_id,
            t("el.what_edit", summary=summarize_elective(elective)),
            reply_markup=edit_fields_keyboard(elective_id),
        )
        return True

    if action == "f" and len(parts) >= 4:
        field = parts[3]
        if field == "weekdays":
            selected = set(elective.weekdays)
            ctx.dialogs.start(
                chat_id,
                "elective_edit",
                "weekdays",
                id=elective_id,
                weekdays=sorted(selected),
            )
            await _ask(
                ctx,
                chat_id,
                _weekdays_prompt(selected),
                weekdays_multiselect_keyboard(selected),
            )
            return True

        prompts = {
            "title": (t("el.edit_title"), cancel_keyboard()),
            "teachers": (t("el.edit_teachers"), teachers_keyboard()),
            "kind": (t("el.edit_kind"), kind_keyboard()),
            "start_time": (t("el.edit_start_time"), cancel_keyboard()),
            "end_time": (t("el.edit_end_time"), cancel_keyboard()),
            "room": (t("el.edit_room"), cancel_keyboard()),
            "weeks": (t("el.edit_weeks"), cancel_keyboard()),
            "start_date": (t("el.edit_start_date"), cancel_keyboard()),
            "interval_weeks": (t("el.edit_interval"), interval_keyboard()),
        }
        prompt = prompts.get(field)
        if prompt is None:
            return True
        ctx.dialogs.start(chat_id, "elective_edit", field, id=elective_id)
        await _ask(ctx, chat_id, prompt[0], prompt[1])
        return True

    return True
