import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "SmartTikTok"


def _compiled_info():
    compiled = globals().get("__compiled__")
    if compiled is None:
        compiled = getattr(sys.modules.get("__main__"), "__compiled__", None)
    return compiled

def _is_packaged_app():
    return bool(getattr(sys, "frozen", False) or _compiled_info() is not None)


def _path_from_runtime_value(value):
    if not value:
        return None
    try:
        return Path(str(value)).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _same_path(left, right):
    return left is not None and right is not None and left == right


def _as_app_dir(candidate):
    path = _path_from_runtime_value(candidate)
    if path is None:
        return None
    if path.name.lower() == f"{APP_NAME}.runtime".lower():
        return path.parent
    return path


def _onefile_parent_app_dir():
    parent_pid = os.environ.get("NUITKA_ONEFILE_PARENT")
    if not parent_pid:
        return None

    try:
        import psutil

        parent_exe = _path_from_runtime_value(psutil.Process(int(parent_pid)).exe())
    except (OSError, RuntimeError, TypeError, ValueError):
        return None

    current_exe = _path_from_runtime_value(sys.executable)
    if parent_exe is None or _same_path(parent_exe, current_exe):
        return None
    return _as_app_dir(parent_exe.parent)


def _portable_app_dir():
    compiled = _compiled_info()
    current_exe_dir = _path_from_runtime_value(Path(sys.executable).parent)
    if getattr(compiled, "onefile", False):
        containing_dir = _as_app_dir(getattr(compiled, "containing_dir", None))
        if containing_dir is not None and not _same_path(containing_dir, current_exe_dir):
            return containing_dir

        original_argv0 = _path_from_runtime_value(getattr(compiled, "original_argv0", None))
        original_dir = _as_app_dir(original_argv0.parent if original_argv0 is not None else None)
        if original_dir is not None and not _same_path(original_dir, current_exe_dir):
            return original_dir

        parent_app_dir = _onefile_parent_app_dir()
        if parent_app_dir is not None:
            return parent_app_dir

        cwd = Path.cwd().resolve()
        if (cwd / f"{APP_NAME}.exe").exists() and not _same_path(cwd, current_exe_dir):
            return cwd

    argv0 = sys.argv[0] if sys.argv else None
    return _as_app_dir(Path(argv0 or sys.executable).resolve().parent)


def resolve_app_path(value, default=None):
    if not value:
        return Path(default) if default is not None else APP_STATE_DIR
    path = Path(str(value))
    if path.is_absolute():
        return path
    if default is not None:
        default_path = Path(default)
        if path == Path(default_path.name):
            return default_path
    return APP_STATE_DIR / path


APP_STATE_DIR = _portable_app_dir() if _is_packaged_app() else ROOT_DIR
DATA_DIR = APP_STATE_DIR / "data"
PROFILES_DIR = APP_STATE_DIR / "profiles"
PROFILES_PATH = DATA_DIR / "profiles.json"
APP_DB_PATH = DATA_DIR / "app.db"
DOWNLOADS_DIR = APP_STATE_DIR / "downloads"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload?from=webapp&tab=video"
