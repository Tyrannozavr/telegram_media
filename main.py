import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from middlewares.error_middleware import ErrorLoggingMiddleware
from router import router
from logging_config import app_logger

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.update.middleware(ErrorLoggingMiddleware())
dp.include_router(router)


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    app_logger.info("Starting bot")
    bot = Bot(token=BOT_TOKEN, timeout=60, default=DefaultBotProperties(parse_mode=ParseMode.HTML))  # Увеличиваем таймауты для бота

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())