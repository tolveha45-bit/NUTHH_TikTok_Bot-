import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATABASE_PATH = os.getenv("DATABASE_PATH", "nuthh.db")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
TEMP_DIR = os.path.join(DOWNLOAD_DIR, "temp")
COMPLETED_DIR = os.path.join(DOWNLOAD_DIR, "completed")

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "7"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "3600"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(COMPLETED_DIR, exist_ok=True)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

if OWNER_ID <= 0:
    raise RuntimeError("OWNER_ID is missing or invalid in .env")
