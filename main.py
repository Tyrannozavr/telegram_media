import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
# from aiogram.utils import executor
from config import BOT_TOKEN
from router import router
from services.images import render

# Настройка логирования
logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.include_router(router)

# class BotHandler:
#     def __init__(self):
#         self.last_update_id = 0
#
#     async def send_reply_text_message(self, chat_id: int, text: str, to_message_id: int):
#         await dp.send_message(chat_id, text, reply_to_message_id=to_message_id)
#
#     async def send_reply_document(self, chat_id: int, data: bytes, to_message_id: int, context: dict):
#         filename = f"result{context['font_size']}.png"
#         keyboard = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="Меньше на 10px", callback_data=str(context["font_size"] - 10))],
#             [InlineKeyboardButton(text="Больше на 10px", callback_data=str(context["font_size"] + 10))],
#         ])
#
#         await bot.send_document(
#             chat_id,
#             InputFile(data, filename=filename),
#             reply_to_message_id=to_message_id,
#             reply_markup=keyboard
#         )
#
#     async def edit_reply_document(self, chat_id: int, message_id: int, data: bytes, context: dict):
#         filename = f"result{context['font_size']}.png"
#         keyboard = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="Меньше на 10px", callback_data=str(context["font_size"] - 10))],
#             [InlineKeyboardButton(text="Больше на 10px", callback_data=str(context["font_size"] + 10))],
#         ])
#
#         await bot.edit_message_media(
#             chat_id=chat_id,
#             message_id=message_id,
#             media=types.InputMediaDocument(InputFile(data, filename=filename)),
#             reply_markup=keyboard
#         )
#
#     async def handle_update_message(self, message: types.Message):
#         if not message.document:
#             await self.send_reply_text_message(message.chat.id, "Unsupported message", message.message_id)
#             return
#
#         caption = message.caption or ""
#         is_story = caption.startswith("*")
#         if is_story:
#             caption = caption[1:].strip()
#
#         context = {
#             "file_id": message.document.file_id,
#             "caption": caption,
#             "font_size": 100,
#             "index": "index3.html" if is_story else "index2.html",
#         }
#
#         file = await bot.get_file(context["file_id"])
#         file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
#         result_img = render(file_url, context["caption"], context["font_size"], index=context["index"])
#
#         await self.send_reply_document(message.chat.id, result_img, message.message_id, context)
#
#     async def handle_update_callback_query(self, callback_query: types.CallbackQuery):
#         bot_message = callback_query.message
#         user_message = bot_message.reply_to_message
#         font_size = int(callback_query.data)
#
#         caption = user_message.caption or ""
#         is_story = caption.startswith("*")
#         if is_story:
#             caption = caption[1:].strip()
#
#         context = {
#             "file_id": user_message.document.file_id,
#             "caption": caption,
#             "font_size": font_size,
#             "index": "index3.html" if is_story else "index2.html",
#         }
#
#         file = await bot.get_file(context["file_id"])
#         file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
#         result_img = render(file_url, context["caption"], context["font_size"], index=context["index"])
#
#         await self.edit_reply_document(bot_message.chat.id, bot_message.message_id, result_img, context)
#
#     @dp.message(content_types=types.ContentType.DOCUMENT)
#     async def handle_message(self, message: types.Message):
#         await self.handle_update_message(message)
#
#     @dp.callback_query()
#     async def handle_callback_query(self, callback_query: types.CallbackQuery):
#         await self.handle_update_callback_query(callback_query)

# Инициализация обработчика
async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)

# Запуск бота
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())