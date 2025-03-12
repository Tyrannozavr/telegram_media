from io import BytesIO

from aiogram.types import Message, input_file, input_media, InputFile, BufferedInputFile

from aiogram import Router, Bot
from aiogram.filters import CommandStart

from services.images import cover_text

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
    file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file.file_path)
    # Получаем текст из подписи (caption)
    text = message.caption or "Пример текста"

    # Рендерим изображение с текстом
    result_image = cover_text(file_bytes.read(), text, font_size=40)
    result_file = BufferedInputFile(result_image, filename="result.png")
    await message.answer_document(result_file)

