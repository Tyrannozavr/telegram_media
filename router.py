from io import BytesIO

from aiogram.types import Message, input_file, input_media, InputFile, BufferedInputFile

from aiogram import Router, Bot
from aiogram.filters import CommandStart

from services.images import cover_text, process_image, image_to_bytes
from services.text import wrap_text, calculate_characters_width

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
    font_size = 100
    text_width = calculate_characters_width(font_size=font_size)
    text = wrap_text(message.caption, text_width) or "Пример текста"

    # Рендерим изображение с текстом
    image_resized = process_image(file_bytes.read())
    # image_bytes_resized = image_resized.tobytes()
    image_bytes_resized = image_to_bytes(image_resized)
    result_image = cover_text(image_bytes_resized, text, font_size=font_size)

    result_file = BufferedInputFile(result_image, filename="result.png")
    await message.answer_document(result_file)

# Это пример текста, который нужно ограничить по ширине в 32 символа. Он содержит длинные слова, такие как 'саморазвитие' и 'высокотехнологичный',  а также короткие слова.