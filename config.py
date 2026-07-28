import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/convertmaster")
