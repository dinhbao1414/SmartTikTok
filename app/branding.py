import ctypes
import sys
from pathlib import Path


APP_USER_MODEL_ID = "SmartTikTok.UploadTool"


def runtime_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def app_icon_path():
    return runtime_root() / "logo" / "output.ico"


def is_valid_ico(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    if len(data) < 22 or data[:4] != b"\x00\x00\x01\x00":
        return False
    count = int.from_bytes(data[4:6], "little")
    directory_end = 6 + 16 * count
    return 1 <= count <= 20 and len(data) >= directory_end


def set_windows_app_user_model_id(app_id=APP_USER_MODEL_ID):
    if sys.platform != "win32":
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False
