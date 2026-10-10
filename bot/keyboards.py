from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlencode

from bot.config import Settings
from bot.i18n import locale
from bot.schedule import TZ

# Реэкспорт подписей кнопок из локали (для сравнения текста сообщений)
BTN_TODAY = locale.BTN_TODAY
BTN_TOMORROW = locale.BTN_TOMORROW
BTN_WEEK = locale.BTN_WEEK
BTN_NEXT_WEEK = locale.BTN_NEXT_WEEK
BTN_MONTH = locale.BTN_MONTH
BTN_REFRESH = locale.BTN_REFRESH
BTN_ELECTIVES = locale.BTN_ELECTIVES
BTN_SUB_ON = locale.BTN_SUB_ON
BTN_SUB_OFF = locale.BTN_SUB_OFF

BTN_EL_ADD = locale.BTN_EL_ADD
BTN_EL_LIST = locale.BTN_EL_LIST
BTN_EL_BACK = locale.BTN_EL_BACK
BTN_CANCEL = locale.BTN_CANCEL
BTN_CONFIRM = locale.BTN_CONFIRM
BTN_WD_DONE = locale.BTN_WD_DONE
BTN_SKIP_TEACHER = locale.BTN_SKIP_TEACHER
BTN_INTERVAL_1 = locale.BTN_INTERVAL_1
BTN_INTERVAL_2 = locale.BTN_INTERVAL_2

BTN_KIND_LEC = locale.BTN_KIND_LEC
BTN_KIND_PRAC = locale.BTN_KIND_PRAC
BTN_KIND_LAB = locale.BTN_KIND_LAB
BTN_KIND_SEM = locale.BTN_KIND_SEM

BTN_WD = locale.BTN_WD


def portal_url(settings: Settings, day: date | None = None) -> str:
    target = day or datetime.now(TZ).date()
    params = {
        "view": "easycourse",
        "include": "corso",
        "anno": settings.unimi_anno,
        "corso": settings.unimi_corso,
        "anno2[0]": settings.unimi_anno2,
        "visualizzazione_orario": "cal",
        "_lang": settings.unimi_lang,
        "week_grid_type": "0",
        "highlighted_date": "0",
        "all_events": "0",
        "date": target.strftime("%d-%m-%Y"),
        "col_cells": "1",
        "only_grid": "0",
        "empty_box": "0",
    }
    return (
        "https://orari.unimi.it/PortaleStudenti/index.php?"
        + urlencode(params)
    )


def reply_keyboard(*, subscribed: bool) -> dict:
    sub_btn = BTN_SUB_OFF if subscribed else BTN_SUB_ON
    return {
        "keyboard": [
            [{"text": BTN_TODAY}, {"text": BTN_TOMORROW}],
            [{"text": BTN_WEEK}, {"text": BTN_NEXT_WEEK}],
            [{"text": BTN_MONTH}, {"text": BTN_ELECTIVES}],
            [{"text": BTN_REFRESH}, {"text": sub_btn}],
        ],
        "resize_keyboard": True,
    }


def electives_menu_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_EL_ADD}],
            [{"text": BTN_EL_LIST}],
            [{"text": BTN_EL_BACK}],
        ],
        "resize_keyboard": True,
    }


def cancel_keyboard() -> dict:
    return {
        "keyboard": [[{"text": BTN_CANCEL}]],
        "resize_keyboard": True,
    }


def kind_keyboard() -> dict:
    return {
        "keyboard": [
            [
                {"text": BTN_KIND_LEC},
                {"text": BTN_KIND_PRAC},
                {"text": BTN_KIND_LAB},
                {"text": BTN_KIND_SEM},
            ],
            [{"text": BTN_CANCEL}],
        ],
        "resize_keyboard": True,
    }


def weekdays_multiselect_keyboard(selected: set[int] | list[int]) -> dict:
    selected_set = set(selected)
    row1 = []
    row2 = []
    for idx, name in enumerate(BTN_WD):
        label = f"✓ {name}" if idx in selected_set else name
        (row1 if idx < 4 else row2).append({"text": label})
    return {
        "keyboard": [
            row1,
            row2,
            [{"text": BTN_WD_DONE}],
            [{"text": BTN_CANCEL}],
        ],
        "resize_keyboard": True,
    }


def weekday_keyboard() -> dict:
    return weekdays_multiselect_keyboard(set())


def teachers_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_SKIP_TEACHER}],
            [{"text": BTN_CANCEL}],
        ],
        "resize_keyboard": True,
    }


def interval_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_INTERVAL_1}],
            [{"text": BTN_INTERVAL_2}],
            [{"text": BTN_CANCEL}],
        ],
        "resize_keyboard": True,
    }


def confirm_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_CONFIRM}],
            [{"text": BTN_CANCEL}],
        ],
        "resize_keyboard": True,
    }


def site_link_keyboard(settings: Settings, day: date | None = None) -> dict:
    return {
        "inline_keyboard": [
            [{"text": locale.BTN_SITE, "url": portal_url(settings, day)}]
        ]
    }


def elective_actions_keyboard(elective_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": locale.BTN_EDIT,
                    "callback_data": f"el:edit:{elective_id}",
                },
                {
                    "text": locale.BTN_DELETE,
                    "callback_data": f"el:del:{elective_id}",
                },
            ]
        ]
    }


def edit_fields_keyboard(elective_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": locale.BTN_FIELD_TITLE,
                    "callback_data": f"el:f:{elective_id}:title",
                },
                {
                    "text": locale.BTN_FIELD_TEACHERS,
                    "callback_data": f"el:f:{elective_id}:teachers",
                },
            ],
            [
                {
                    "text": locale.BTN_FIELD_KIND,
                    "callback_data": f"el:f:{elective_id}:kind",
                },
                {
                    "text": locale.BTN_FIELD_WEEKDAYS,
                    "callback_data": f"el:f:{elective_id}:weekdays",
                },
            ],
            [
                {
                    "text": locale.BTN_FIELD_START,
                    "callback_data": f"el:f:{elective_id}:start_time",
                },
                {
                    "text": locale.BTN_FIELD_END,
                    "callback_data": f"el:f:{elective_id}:end_time",
                },
            ],
            [
                {
                    "text": locale.BTN_FIELD_ROOM,
                    "callback_data": f"el:f:{elective_id}:room",
                },
                {
                    "text": locale.BTN_FIELD_WEEKS,
                    "callback_data": f"el:f:{elective_id}:weeks",
                },
            ],
            [
                {
                    "text": locale.BTN_FIELD_START_DATE,
                    "callback_data": f"el:f:{elective_id}:start_date",
                },
                {
                    "text": locale.BTN_FIELD_INTERVAL,
                    "callback_data": f"el:f:{elective_id}:interval_weeks",
                },
            ],
        ]
    }
