import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from os import getenv
from pathlib import Path

import redis
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
LONG_POLLING_TIMEOUT = 600

# Получаем путь к директории проекта
BASE_DIR = Path(__file__).resolve().parent

# Путь к статическим файлам
FONTS_DIR = BASE_DIR / "static" / "fonts"
IMAGES_DIR = BASE_DIR / "static" / "images"
#
# # Пример использования
# font_path = FONTS_DIR / "arial.ttf"
# image_path = IMAGES_DIR / "logo.png"


REDIS = getenv("REDIS_URL", "redis://localhost:6379")
storage = redis.StrictRedis.from_url(
    REDIS, 
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

log_directory = "logging"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)


# Настройка логирования
logger = logging.getLogger("my_logger")
logger.setLevel(logging.ERROR)

current_date = datetime.now().strftime("%Y-%m-%d")
log_file_name = f"app_{current_date}.log"


# Создаем обработчик, который будет записывать логи в файл с ежедневной ротацией
handler = TimedRotatingFileHandler(
    filename=os.path.join(log_directory, log_file_name),  # Имя файла с датой
    when="midnight",  # Ротация каждый день в полночь
    interval=1,  # Каждый день
    backupCount=7  # Хранить последние 7 файлов
)

# Форматирование логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(handler)