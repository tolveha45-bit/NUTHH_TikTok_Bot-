import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0").strip())
except ValueError:
    OWNER_ID = 0

DATABASE_PATH = "nuthh.db"
DOWNLOAD_DIR = "downloads"

MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 600

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

if OWNER_ID == 0:
    raise RuntimeError("OWNER_ID is missing or invalid in .env")
