import os

import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

load_dotenv()
# Конфигурация
TELEGRAM_TOKEN = os.getenv("SECOND_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_kH5Hqlq79f98XG1Q4qMLtAuo"  # Ваш ID ассистента

# Инициализация клиентов
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
# client = AsyncOpenAI(api_key=OPENAI_API_KEY)

proxy_url = "http://username:password@proxy_ip:port"  # или "socks5://..."

http_client = httpx.AsyncClient(
    proxy=proxy_url,
    timeout=30.0  # Таймаут на запросы
)

# Создаем клиент OpenAI с прокси
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    http_client=http_client
)

# Хранилище thread_id (user_id -> thread_id)
user_threads = {}

@dp.message(Command("re"))
async def reset_thread(message: Message):
    user_id = message.from_user.id
    user_threads.pop(user_id, None)
    await message.answer("Сессия сброшена. Начнем заново!", parse_mode=ParseMode.MARKDOWN)

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_input = message.text

    # Получаем или создаем thread
    thread_id = user_threads.get(user_id)
    if not thread_id:
        thread = await client.beta.threads.create()
        thread_id = thread.id
        user_threads[user_id] = thread_id

    # Отправляем сообщение в thread
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    # Запускаем ассистента
    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ожидаем завершения (с таймаутом)
    while True:
        run_status = await client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break
        await asyncio.sleep(1)

    # Получаем ответ
    messages = await client.beta.threads.messages.list(thread_id=thread_id)
    reply = messages.data[0].content[0].text.value

    await message.answer(reply, parse_mode=ParseMode.MARKDOWN)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())