from os import getenv

from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
LONG_POLLING_TIMEOUT = 600
