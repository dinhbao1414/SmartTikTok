import json
from datetime import datetime
from pathlib import Path

from app.paths import APP_STATE_DIR

DEFAULT_APP_VERSION = "1.0.8"
VERSION_FILE_NAME = "version.json"


def version_file_path(base_dir=None):
    return Path(base_dir) / VERSION_FILE_NAME if base_dir is not None else APP_STATE_DIR / VERSION_FILE_NAME


def read_app_version(default=DEFAULT_APP_VERSION, base_dir=None):
    path = version_file_path(base_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = str(data.get("version", "")).strip()
        return value or default
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def write_app_version(app_version, base_dir=None, updated_at=None):
    path = version_file_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": str(app_version).strip(),
        "updated_at": updated_at or datetime.now().isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
