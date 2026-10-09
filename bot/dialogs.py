from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Dialog:
    name: str
    step: str
    data: dict[str, Any] = field(default_factory=dict)


class DialogStore:
    """In-memory FSM для пошагового ввода элективов."""

    def __init__(self) -> None:
        self._by_chat: dict[int, Dialog] = {}

    def get(self, chat_id: int) -> Dialog | None:
        return self._by_chat.get(chat_id)

    def start(self, chat_id: int, name: str, step: str, **data: Any) -> Dialog:
        dialog = Dialog(name=name, step=step, data=dict(data))
        self._by_chat[chat_id] = dialog
        return dialog

    def update(
        self,
        chat_id: int,
        *,
        step: str | None = None,
        **data: Any,
    ) -> Dialog | None:
        dialog = self._by_chat.get(chat_id)
        if dialog is None:
            return None
        if step is not None:
            dialog.step = step
        dialog.data.update(data)
        return dialog

    def clear(self, chat_id: int) -> None:
        self._by_chat.pop(chat_id, None)
