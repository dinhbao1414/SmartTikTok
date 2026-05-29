from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROFILES_PATH = DATA_DIR / "profiles.json"
APP_DB_PATH = DATA_DIR / "app.db"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video"
