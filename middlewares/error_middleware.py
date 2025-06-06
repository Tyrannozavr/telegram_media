import logging
from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from logging_config import app_logger


class ErrorLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            # Продолжаем выполнение хэндлера
            return await handler(event, data)
        except Exception as e:
            # Логируем ошибку
            app_logger.error(f"Ошибка в хэндлере: {e}", exc_info=True)
            # Можно также отправить сообщение об ошибке в Telegram
            # bot = data.get("bot")
            # if bot:
            #     await bot.send_message(chat_id=YOUR_CHAT_ID, text=f"Произошла ошибка: {e}")
            # Пробрасываем исключение дальше, если нужно
            raise