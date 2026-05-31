import sys
import traceback
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6 import QtGui, QtWidgets

from app.auth import LoginForm, check_active_key
from app.branding import APP_USER_MODEL_ID, app_icon_path, is_valid_ico, set_windows_app_user_model_id
from app.gui import Ui_MainWindow


def _startup_log_path():
    return Path(sys.executable).with_name("launcher_startup.log") if getattr(sys, "frozen", False) else (
        Path(__file__).resolve().parents[1] / "launcher_startup.log"
    )


def startup_log(message):
    try:
        with _startup_log_path().open("a", encoding="utf-8") as file:
            file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
    except Exception:
        pass

def _app_icon_path():
    return app_icon_path()


def _set_windows_app_user_model_id(app_id):
    return set_windows_app_user_model_id(app_id)


def _create_app_icon():
    icon_path = _app_icon_path()
    if not icon_path.exists() or not is_valid_ico(icon_path):
        return None
    icon = QtGui.QIcon(str(icon_path))
    return None if icon.isNull() else icon


def _apply_window_icon(target, icon):
    if target is not None and icon is not None and hasattr(target, "setWindowIcon"):
        target.setWindowIcon(icon)


def run(
    app_factory=QtWidgets.QApplication,
    main_window_factory=Ui_MainWindow,
    login_form_factory=LoginForm,
    active_key_checker=check_active_key,
    argv=None,
):
    _set_windows_app_user_model_id(APP_USER_MODEL_ID)
    app = app_factory(sys.argv if argv is None else argv)
    icon = _create_app_icon()
    _apply_window_icon(app, icon)

    try:
        startup_log("launcher: checking license")
        if active_key_checker():
            startup_log("launcher: license active")
            window = main_window_factory()
        else:
            startup_log("launcher: license inactive")
            window = login_form_factory()
    except Exception:
        startup_log("launcher: fatal exception")
        startup_log(traceback.format_exc())
        window = login_form_factory()

    _apply_window_icon(window, icon)
    window.show()
    return app.exec()


def main():
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
