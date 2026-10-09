"""Русские строки интерфейса. Редактируй тексты здесь."""

# --- Кнопки reply-клавиатуры ---
BTN_TODAY = "📅 Сегодня"
BTN_TOMORROW = "⏭ Завтра"
BTN_WEEK = "🗓 Эта неделя"
BTN_NEXT_WEEK = "➡️ След. неделя"
BTN_MONTH = "📆 Месяц"
BTN_REFRESH = "🔄 Обновить"
BTN_ELECTIVES = "📚 Элективы"
BTN_SUB_ON = "🔔 Вкл. напоминания"
BTN_SUB_OFF = "🔕 Выкл. напоминания"

BTN_EL_ADD = "➕ Добавить электив"
BTN_EL_LIST = "📋 Список элективов"
BTN_EL_BACK = "⬅️ В меню"
BTN_CANCEL = "❌ Отмена"
BTN_CONFIRM = "✅ Сохранить"
BTN_WD_DONE = "✅ Готово"
BTN_SKIP_TEACHER = "без преподавателя"
BTN_INTERVAL_1 = "каждую неделю"
BTN_INTERVAL_2 = "раз в 2 недели"

BTN_KIND_LEC = "лекция"
BTN_KIND_PRAC = "практ."
BTN_KIND_LAB = "лаб."
BTN_KIND_SEM = "семинар"

BTN_WD = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")

BTN_SITE = "Проверить на сайте"
BTN_EDIT = "✏️ Изменить"
BTN_DELETE = "🗑 Удалить"

BTN_FIELD_TITLE = "Название"
BTN_FIELD_TEACHERS = "Препод"
BTN_FIELD_KIND = "Тип"
BTN_FIELD_WEEKDAYS = "Дни"
BTN_FIELD_START = "Начало"
BTN_FIELD_END = "Конец"
BTN_FIELD_ROOM = "Аудитория"
BTN_FIELD_WEEKS = "Недель"
BTN_FIELD_START_DATE = "Старт курса"
BTN_FIELD_INTERVAL = "Период."

# --- Словари / списки ---
WEEKDAYS_FULL = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)

WEEKDAYS_SHORT = BTN_WD

MONTHS = (
    "",
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
)

# Подпись типа пары в UI → код Unimi/ICS
KIND_TO_CODE = {
    BTN_KIND_LEC: "lezione",
    BTN_KIND_PRAC: "esercitazione",
    BTN_KIND_LAB: "laboratorio",
    BTN_KIND_SEM: "seminario",
}

# Код ICS → короткая подпись в расписании
KIND_LABEL = {
    "lezione": "лекция",
    "esercitazione": "практ",
    "laboratorio": "лаб",
    "seminar": "семинар",
    "seminario": "семинар",
}

DATE_TODAY_ALIASES = ("сегодня", "today")
DATE_TOMORROW_ALIASES = ("завтра", "tomorrow")

# --- Сообщения (шаблоны с {placeholders}) ---
MESSAGES = {
    # start / menu
    "start.hello": (
        "Привет! Я бот расписания Unimi (курс BBJ).\n\n"
        "Пользуйся кнопками внизу экрана.\n"
        "Элективы — свои пары, которых нет на портале.\n\n"
        "Подписка на напоминания: {sub}\n"
        "Время напоминания: {hour:02d}:{minute:02d} ({tz})"
    ),
    "start.sub_on": "включена ✅",
    "start.sub_off": "выключена",
    "menu.main": "Главное меню.",
    "menu.choose": "Выбери действие кнопками внизу экрана.\nИли нажми /start",
    "menu.dialog_busy": (
        "Сейчас идёт ввод электива. Продолжи по подсказке или нажми «❌ Отмена»."
    ),
    # schedule
    "schedule.load_error": "Не удалось загрузить расписание. Попробуйте позже.",
    "schedule.refresh_error": "Не удалось обновить расписание.",
    "schedule.today_intro": "Вот твоё расписание на сегодня:",
    "schedule.tomorrow_intro": "Вот твоё расписание на завтра:",
    "schedule.week_intro": "Вот твоё расписание на неделю:",
    "schedule.week_this_intro": "Вот твоё расписание на эту неделю:",
    "schedule.week_next_intro": "Вот твоё расписание на следующую неделю:",
    "schedule.empty_day": "Занятий нет💅.",
    "schedule.empty_week": "На этой неделе занятий нет💅.",
    "schedule.empty_month": "В этом месяце занятий нет💅.",
    "schedule.month_days_header": "Дни с парами:",
    "schedule.month_total": "Всего: <b>{total}</b> {pairs_word} за месяц",
    "schedule.month_title": "📆 {month} {year}",
    "schedule.day_header": "🗓 {date}, {weekday} <i>{time_span}</i>",
    "schedule.day_header_today": "🗓 {date}, {weekday} <i>{time_span}</i> 👈",
    "schedule.day_time_span": " ({start}–{end})",
    "schedule.week_range": "<b>{start} — {end}</b>",
    "schedule.room": "ауд. {room}",
    "schedule.room_with_body": "ауд. <b>{num}</b>, {body}",
    "schedule.refresh_ok": "Готово. В кэше {portal} занятий с портала.",
    "schedule.refresh_ok_with_electives": (
        "Готово. В кэше {portal} занятий с портала, элективов: {electives}."
    ),
    "schedule.reminder_intro": "Напоминание: завтра у нас будут такие пары:",
    "pairs.one": "пара",
    "pairs.few": "пары",
    "pairs.many": "пар",
    # subscriptions
    "sub.enabled": (
        "Подписка оформлена.\n"
        "Каждый день в {hour:02d}:{minute:02d} ({tz}) "
        "пришлю расписание на завтра (если пары есть)."
    ),
    "sub.already": (
        "Вы уже подписаны.\n"
        "Напоминание: {hour:02d}:{minute:02d} ({tz})."
    ),
    "sub.disabled": "Подписка отключена.",
    "sub.not_subscribed": "Вы и так не подписаны.",
    # electives menu
    "el.menu": (
        "Элективы — пары, которых нет на портале.\n"
        "Расписание общее для всех: смотреть могут все, "
        "менять и удалять — только тот, кто добавил.\n"
        "Один электив может быть в несколько дней недели."
    ),
    "el.cancelled": "Отменено.",
    "el.empty": "Пока нет элективов. Нажми «➕ Добавить электив».",
    "el.list_header": "Элективы ({count}):",
    "el.saved": "Сохранено.",
    "el.not_found": "Электив не найден.",
    "el.not_owner": "Править и удалять может только тот, кто добавил этот электив.",
    "el.deleted": "🗑️Удалено: {title}",
    "el.what_edit": "Что изменить?\n\n{summary}",
    "el.created": "Электив сохранён. Он появится в расписании на выбранные дни.",
    "el.review": "Проверь электив:\n\n{summary}",
    "el.save_q": "Сохранить?",
    "el.save_hint": "Нажми «✅ Сохранить» или «❌ Отмена».",
    "el.summary": (
        "<b>[Название]:</b> <b>{title}</b> <i>[{kind}]</i>\n"
        "<b>[Дни]:</b> {weekdays} {start_time}–{end_time}\n"
        "<b>[Преподаватели]:</b> <i>{teachers}</i>\n"
        "<b>[Аудитория]:</b> ауд. {room}\n"
        "<b>[Периодичность]:</b> {interval}, {weeks} нед. с {start_date}"
    ),
    "el.interval_weekly": "каждую неделю",
    "el.interval_every_n": "раз в {n} нед.",
    "el.no_teacher": "—",
    "el.no_room": "—",
    # electives wizard
    "el.add_title": "Добавление электива.\n\n1/9 Название пары:",
    "el.step_teachers": "2/9 Имя преподавателя (или «без преподавателя»):",
    "el.step_kind": "3/9 Тип пары:",
    "el.step_start_time": "4/9 Время начала (ЧЧ:ММ), например 14:30:",
    "el.step_end_time": "5/9 Время конца (ЧЧ:ММ), например 16:30:",
    "el.step_room": (
        "6/9 Аудитория (например `23` или `23, Conservatorio (Edificio 1)`):"
    ),
    "el.step_weekdays": "7/9 {prompt}",
    "el.step_start_date": (
        "8/9 Дата начала курса (ДД.ММ.ГГГГ), «сегодня» или «завтра»:\n"
        "Пары раньше текущей даты не ставятся."
    ),
    "el.step_weeks": (
        "9/9 Сколько учебных недель длится электив? (число, например 12):"
    ),
    "el.step_interval": "Периодичность:",
    "el.weekdays_prompt": (
        "Выбери дни недели (можно несколько).\n"
        "Нажимай дни ещё раз, чтобы снять галочку.\n"
        "Сейчас: {chosen}\n\n"
        "Когда закончишь — «✅ Готово»."
    ),
    "el.weekdays_none": "пока ничего",
    "el.weekdays_need_one": "Выбери хотя бы один день.",
    "el.err_title_short": "Слишком коротко. Введи название:",
    "el.err_title_short_edit": "Слишком коротко. Название:",
    "el.err_kind": "Выбери тип кнопкой:",
    "el.err_time": "Формат ЧЧ:ММ, например 09:30:",
    "el.err_time_end": "Формат ЧЧ:ММ, например 16:30:",
    "el.err_time_order": "Конец должен быть позже начала. Ещё раз:",
    "el.err_time_short": "Формат ЧЧ:ММ:",
    "el.err_time_order_short": "Конец позже начала, формат ЧЧ:ММ:",
    "el.err_date": "Дата в формате ДД.ММ.ГГГГ, либо «сегодня»/«завтра»:",
    "el.err_date_short": "ДД.ММ.ГГГГ / сегодня / завтра:",
    "el.err_weeks": "Введи число недель от 1 до 52:",
    "el.err_weeks_short": "Число недель 1–52:",
    "el.err_interval": "Выбери периодичность кнопкой:",
    "el.err_interval_short": "Выбери периодичность:",
    # edit prompts
    "el.edit_title": "Новое название:",
    "el.edit_teachers": "Преподаватель (или «без преподавателя»):",
    "el.edit_kind": "Тип пары:",
    "el.edit_start_time": "Время начала ЧЧ:ММ:",
    "el.edit_end_time": "Время конца ЧЧ:ММ:",
    "el.edit_room": "Аудитория:",
    "el.edit_weeks": "Число учебных недель (1–52):",
    "el.edit_start_date": "Дата начала курса ДД.ММ.ГГГГ / сегодня / завтра:",
    "el.edit_interval": "Периодичность:",
}
