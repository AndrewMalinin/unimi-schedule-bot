from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._client = httpx.AsyncClient(timeout=60.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, **params: Any) -> Any:
        response = await self._client.post(f"{self._base}/{method}", json=params)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return payload["result"]

    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe")

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            return await self._call("getUpdates", **params)
        except httpx.ReadTimeout:
            return []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str | None = "HTML",
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_markup is not None:
            params["reply_markup"] = reply_markup
        return await self._call("sendMessage", **params)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        *,
        text: str | None = None,
        show_alert: bool = False,
    ) -> bool:
        params: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            params["text"] = text
        if show_alert:
            params["show_alert"] = True
        return await self._call("answerCallbackQuery", **params)
