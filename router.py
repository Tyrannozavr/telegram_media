from aiogram import Router, Bot
from aiogram import types
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import storage
from interactors.images import image_instagram_process_interactor

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer(f"Hello, {message.from_user.username}! \n Ты можешь отправить мне изображение и я "
                         f"приведу его к предустановленному формату")


@router.message(lambda message: message.photo or message.document or message.text)
async def handle_media(message: Message, bot: Bot):
    file_id = None
    file_bytes = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    if file_id is not None:
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)

    font_size = 100
    if file_bytes is not None:
        file_bytes = file_bytes.read()
    photo_text = message.caption if message.caption else message.text
    await message.bot.send_chat_action(action="upload_photo", chat_id=message.chat.id)
    result_image = image_instagram_process_interactor(image=file_bytes, text=photo_text,
                                                      font_size=font_size)

    builder = InlineKeyboardBuilder()
    builder.button(text="-5px", callback_data=f"adjust_size:{font_size - 5}")
    builder.button(text="+5px", callback_data=f"adjust_size:{font_size + 5}")
    result_file = BufferedInputFile(result_image, filename="result.png")
    answer_text = message.caption if message.caption else message.text
    answer = await message.answer_document(result_file, caption=answer_text, reply_markup=builder.as_markup())
    
    # Only store file_id in Redis if it exists
    if file_id is not None:
        storage.set(answer.message_id, file_id)


@router.callback_query(lambda callback: callback.data.startswith("adjust_size"))
async def handle_adjust_size(callback: CallbackQuery, bot: Bot):
    data = callback.data.split(":")
    action = data[1]  # +10 или -10
    message = callback.message
    file_id = storage.get(message.message_id)
    file_bytes = None
    # Выводим в консоль
    if file_id is not None:
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)
        file_bytes = file_bytes.read()
    font_size = int(action)
    result_image = image_instagram_process_interactor(image=file_bytes, text=message.caption,
                                                      font_size=font_size)
    result_file = BufferedInputFile(result_image, filename="result.png")
    # Отправляем ответ пользователю (чтобы убрать "часики" у кнопки)
    await callback.answer(f"Вы нажали {action} для файла {file_id}")

    builder = InlineKeyboardBuilder()
    builder.button(text="-5px", callback_data=f"adjust_size:{font_size - 5}")
    builder.button(text="+5px", callback_data=f"adjust_size:{font_size + 5}")

    await bot.edit_message_media(
        media=types.InputMediaDocument(media=result_file, caption=message.caption),
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=builder.as_markup()
    )
