import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.filterwarnings("ignore", "sipPyTypeDict.*", DeprecationWarning)

from PyQt6 import QtWidgets

import gui as gui_module
from gui import Ui_MainWindow
from profile_store import create_chrome_profiles, load_profiles

class GuiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings("ignore", "sipPyTypeDict.*", DeprecationWarning)
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_window_has_modern_sidebar_layout_and_run_controls(self):
        window = Ui_MainWindow()

        nav_labels = [button.text() for button in window.nav_buttons]

        self.assertEqual(nav_labels, ["Profiles", "Settings", "Logs"])
        self.assertEqual(window.pages.count(), 3)
        self.assertEqual(window.sidebar.objectName(), "Sidebar")
        self.assertEqual(window.header_title.text(), "YouTube To TikTok")
        self.assertIn("#0B0F19", window.styleSheet())
        self.assertEqual(window.button_run_all.text(), "Run")
        self.assertEqual(window.button_stop.text(), "Stop")
        self.assertTrue(hasattr(window, "logs_view"))
        self.assertTrue(window.logs_view.isReadOnly())
        self.assertEqual(window.input_poll_interval.minimum(), 1)
        self.assertEqual(window.input_split_threshold.value(), 10)
        self.assertIn("color: #F8FAFC", window.styleSheet())
        self.assertIn("QTableWidget::item", window.styleSheet())
        self.assertIn("QLabel {", window.styleSheet())

    def test_close_event_waits_for_running_worker_thread(self):
        class FakeWorker:
            def __init__(self):
                self.stopped = False

            def stop(self):
                self.stopped = True

        class FakeThread:
            def __init__(self):
                self.wait_timeout = None

            def isRunning(self):
                return True

            def wait(self, timeout):
                self.wait_timeout = timeout
                return True

        class FakeEvent:
            def __init__(self):
                self.accepted = False
                self.ignored = False

            def accept(self):
                self.accepted = True

            def ignore(self):
                self.ignored = True

        window = Ui_MainWindow()
        worker = FakeWorker()
        thread = FakeThread()
        event = FakeEvent()
        window.worker = worker
        window.worker_thread = thread

        window.closeEvent(event)

        self.assertTrue(worker.stopped)
        self.assertEqual(thread.wait_timeout, 10000)
        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

    def test_run_saves_visible_channel_mode_before_worker_starts(self):
        class FakeSignal:
            def __init__(self):
                self.callbacks = []

            def connect(self, callback):
                self.callbacks.append(callback)

        class FakeThread:
            def __init__(self, parent=None):
                self.started = FakeSignal()
                self.finished = FakeSignal()
                self.was_started = False

            def start(self):
                self.was_started = True

            def quit(self):
                return None

            def deleteLater(self):
                return None

        class FakeWorker:
            def __init__(self, profiles_path, db_path):
                self.profiles_path = profiles_path
                self.db_path = db_path
                self.log_created = FakeSignal()
                self.profile_status = FakeSignal()
                self.finished = FakeSignal()

            def moveToThread(self, thread):
                self.thread = thread

            def run_forever(self):
                return None

            def deleteLater(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles_path = root / "data" / "profiles.json"
            create_chrome_profiles(profiles_path, root / "profiles", 1, "acc", "", "")

            with (
                patch.object(gui_module, "PROFILES_PATH", profiles_path),
                patch.object(gui_module, "APP_DB_PATH", root / "app.db"),
                patch.object(gui_module.QtCore, "QThread", FakeThread),
                patch.object(gui_module, "YoutubeToTikTokWorker", FakeWorker),
            ):
                window = Ui_MainWindow()
                window.table.cellWidget(0, 3).setText("https://www.youtube.com/@hoangacc/videos")
                window.table.cellWidget(0, 4).setCurrentText("videos")

                window.run_all_profiles()

            profile = load_profiles(profiles_path)[0]
            self.assertEqual(profile["channel_url"], "https://www.youtube.com/@hoangacc/videos")
            self.assertEqual(profile["channel_mode"], "videos")

    def test_save_settings_persists_split_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(gui_module, "APP_DB_PATH", root / "app.db"):
                window = Ui_MainWindow()
                window.input_split_threshold.setValue(15)
                window.save_settings()

                self.assertEqual(window.database.get_setting("split_threshold_minutes"), "15")

if __name__ == "__main__":
    unittest.main()
