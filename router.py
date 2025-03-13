from aiogram import types

from aiogram.types import Message, BufferedInputFile, CallbackQuery

from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from interactors.images import image_instagram_process_interactor

router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer(f"Hello, {message.from_user.username}! \n Ты можешь отправить мне изображение и я "
                         f"приведу его к предустановленному формату")


@router.message(lambda message: message.photo)
async def handle_image(message: Message, bot: Bot):
    await message.answer(f"Фото тоже будет")

@router.message(lambda message: message.document)
async def handle_file(message: Message, bot: Bot):
    file_id = message.document.file_id
    print("First got ", file_id)
    file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file.file_path)
    font_size = 100
    result_image = image_instagram_process_interactor(file_bytes.read(),  message.caption, font_size)

    builder = InlineKeyboardBuilder()
    builder.button(text="-10px", callback_data=f"adjust_size:{font_size-10}")
    builder.button(text="+10px", callback_data=f"adjust_size:{font_size+10}")
    result_file = BufferedInputFile(result_image, filename="result.png")
    await message.answer_document(result_file, caption=message.caption, reply_markup=builder.as_markup())

@router.callback_query(lambda callback: callback.data.startswith("adjust_size"))
async def handle_adjust_size(callback: CallbackQuery, bot: Bot):
    data = callback.data.split(":")
    action = data[1]  # +10 или -10


    message = callback.message
    file_id = message.document.file_id
    # Выводим в консоль
    # print(f"File ID: {file_id}, Action: {action}, message: {text}")
    file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file.file_path)
    font_size = int(action)
    print(f"font size ", font_size)
    result_image = image_instagram_process_interactor(file_bytes.read(), message.caption, font_size)
    result_file = BufferedInputFile(result_image, filename="result.png")
    # Отправляем ответ пользователю (чтобы убрать "часики" у кнопки)
    await callback.answer(f"Вы нажали {action} для файла {file_id}")

    builder = InlineKeyboardBuilder()
    builder.button(text="-10px", callback_data=f"adjust_size:{font_size-10}")
    builder.button(text="+10px", callback_data=f"adjust_size:{font_size+10}")

    await bot.edit_message_media(
        media=types.InputMediaDocument(media=result_file, caption=message.caption),
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=builder.as_markup()
    )