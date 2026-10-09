"""
Простой i18n (как JS): все пользовательские тексты в bot/locales/*.py

Использование:
    from bot.i18n import t, locale

    t("start.hello", sub="включена", hour=20, minute=0, tz="Europe/Rome")
    locale.BTN_TODAY
    locale.WEEKDAYS_FULL[0]
"""

from __future__ import annotations

from types import ModuleType

from bot.locales import ru as locale_ru

_LOCALES: dict[str, ModuleType] = {
    "ru": locale_ru,
}

_current = "ru"


def set_locale(code: str) -> None:
    if code not in _LOCALES:
        raise ValueError(f"Неизвестная локаль: {code}. Доступны: {list(_LOCALES)}")
    global _current
    _current = code


def get_locale_code() -> str:
    return _current


def _mod() -> ModuleType:
    return _LOCALES[_current]


class _LocaleProxy:
    """Доступ к константам текущей локали: locale.BTN_TODAY, locale.MESSAGES…"""

    def __getattr__(self, name: str):
        return getattr(_mod(), name)


locale = _LocaleProxy()


def t(key: str, **kwargs) -> str:
    """Вернуть строку по ключу; подставить {placeholders} через str.format."""
    messages = getattr(_mod(), "MESSAGES", {})
    text = messages.get(key)
    if text is None:
        # fallback на ru, затем на сам ключ
        text = locale_ru.MESSAGES.get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def pairs_word(n: int) -> str:
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 19:
        return t("pairs.many")
    if n1 == 1:
        return t("pairs.one")
    if 2 <= n1 <= 4:
        return t("pairs.few")
    return t("pairs.many")
