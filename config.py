import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklaymiz
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Google Gemini API kaliti (ixtiyoriy)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Videolar vaqtincha saqlanadigan papka
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Agar Instagram cookies bo'lsa (ixtiyoriy, yopiq profillar yoki cheklovlar uchun)
COOKIES_FILE = BASE_DIR / "cookies.txt"

# Telegram Bot API orqali yuborish mumkin bo'lgan maksimal hajm (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes
