from aiogram import Router, Bot
from aiogram import types
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import storage
from interactors.images import image_instagram_process_interactor
from logging_config import app_logger

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message):
    app_logger.info(f"User {message.from_user.username} (ID: {message.from_user.id}) started the bot")
    await message.answer(f"Hello, {message.from_user.username}! \n Ты можешь отправить мне изображение и я "
                         f"приведу его к предустановленному формату")


@router.message(lambda message: message.photo or message.document or message.text)
async def handle_media(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Log the type of content received
    if message.photo:
        app_logger.info(f"Received photo from user {username} (ID: {user_id})")
        file_id = message.photo[-1].file_id
    elif message.document:
        app_logger.info(f"Received document from user {username} (ID: {user_id})")
        file_id = message.document.file_id
    else:
        app_logger.info(f"Received text from user {username} (ID: {user_id}): {message.text[:50]}...")
        file_id = None

    file_bytes = None
    if file_id is not None:
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)

    font_size = 100
    if file_bytes is not None:
        file_bytes = file_bytes.read()
    photo_text = message.caption if message.caption else message.text
    await bot.send_chat_action(action="upload_photo", chat_id=message.chat.id)
    
    app_logger.info(f"Processing image for user {username} (ID: {user_id}) with font size {font_size}")
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
        app_logger.debug(f"Stored file_id {file_id} in Redis with key {answer.message_id}")


@router.callback_query(lambda callback: callback.data.startswith("adjust_size"))
async def handle_adjust_size(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Сразу отвечаем на callback, чтобы убрать "часики"
    await callback.answer("Обрабатываю изображение...")

    try:
        data = callback.data.split(":")
        action = data[1]  # Font size value
        message = callback.message
        
        # Получаем file_id из Redis, но не прерываем выполнение, если его нет
        file_bytes = None
        try:
            file_id = storage.get(message.message_id)
            app_logger.debug(f"Retrieved file_id from Redis: {file_id} for message_id: {message.message_id}")
            
            # Пытаемся загрузить файл, только если file_id существует
            if file_id:
                try:
                    file = await bot.get_file(file_id)
                    file_bytes_response = await bot.download_file(file.file_path)
                    file_bytes = file_bytes_response.read()
                    app_logger.debug(f"Successfully downloaded file with ID: {file_id}")
                except Exception as e:
                    app_logger.error(f"Error downloading file: {str(e)}")
                    # Продолжаем с file_bytes=None
            else:
                app_logger.warning(f"No file_id found for message_id: {message.message_id}, continuing with transparent image")
        except Exception as e:
            app_logger.error(f"Redis error: {str(e)}")
            # Продолжаем с file_bytes=None
        
        font_size = int(action)
        
        app_logger.info(f"User {username} (ID: {user_id}) adjusted font size to {action}")
        app_logger.info(f"Reprocessing image with new font size {font_size} for user {username} (ID: {user_id})")
        
        # Обрабатываем изображение с обработкой ошибок
        try:
            # Используем текст из caption сообщения
            text = message.caption
            result_image = image_instagram_process_interactor(image=file_bytes, text=text, font_size=font_size)
        except Exception as e:
            app_logger.error(f"Error processing image: {str(e)}")
            await bot.send_message(chat_id=message.chat.id, 
                                  text="Ошибка при обработке изображения. Пожалуйста, попробуйте еще раз.")
            return
        
        # Создаем клавиатуру и отправляем результат
        builder = InlineKeyboardBuilder()
        builder.button(text="-5px", callback_data=f"adjust_size:{font_size - 5}")
        builder.button(text="+5px", callback_data=f"adjust_size:{font_size + 5}")
        
        result_file = BufferedInputFile(result_image, filename="result.png")
        
        try:
            await bot.edit_message_media(
                media=types.InputMediaDocument(media=result_file, caption=message.caption),
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=builder.as_markup()
            )
            app_logger.debug(f"Updated message with new image for user {username} (ID: {user_id})")
        except Exception as e:
            app_logger.error(f"Error sending result: {str(e)}")
            # Пробуем отправить как новое сообщение, если не удалось отредактировать
            try:
                new_message = await bot.send_document(
                    chat_id=message.chat.id,
                    document=result_file,
                    caption=message.caption,
                    reply_markup=builder.as_markup()
                )
                # Сохраняем новый file_id в Redis, если он был
                if file_id:
                    storage.set(new_message.message_id, file_id)
                app_logger.debug(f"Sent as new message with ID: {new_message.message_id}")
            except Exception as nested_e:
                app_logger.error(f"Failed to send as new message: {str(nested_e)}")
                await bot.send_message(chat_id=message.chat.id, 
                                      text="Не удалось отправить результат. Пожалуйста, попробуйте позже.")
    
    except Exception as e:
        app_logger.error(f"Unexpected error in handle_adjust_size: {str(e)}")
        try:
            await bot.send_message(chat_id=callback.message.chat.id, 
                                  text="Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        except:
            pass