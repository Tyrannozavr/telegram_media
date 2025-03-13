from os import getenv
from pathlib import Path

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
