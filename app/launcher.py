import sys
import traceback
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6 import QtGui, QtWidgets

from app.auth import LoginForm, check_active_key
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


def run(
    app_factory=QtWidgets.QApplication,
    main_window_factory=Ui_MainWindow,
    login_form_factory=LoginForm,
    active_key_checker=check_active_key,
    argv=None,
):
    app = app_factory(sys.argv if argv is None else argv)
    icon_path = Path(__file__).resolve().parents[1] / "logo" / "output.ico"
    if icon_path.exists() and hasattr(app, "setWindowIcon"):
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))

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

    window.show()
    return app.exec()


def main():
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
