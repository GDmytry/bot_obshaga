"""Admin check middleware — restricts admin-only commands."""

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Any, Awaitable

from config import ADMIN_IDS


class AdminMiddleware(BaseMiddleware):
    """Sets data['is_admin'] = True/False for every incoming message."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            data["is_admin"] = event.from_user.id in ADMIN_IDS
        else:
            data["is_admin"] = False
        return await handler(event, data)
