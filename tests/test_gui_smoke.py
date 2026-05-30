import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.filterwarnings("ignore", "sipPyTypeDict.*", DeprecationWarning)

from PyQt6 import QtGui, QtWidgets

import app.gui as gui_module
from app.gui import Ui_MainWindow
from app.profiles.store import create_chrome_profiles, load_profiles

class GuiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings("ignore", "sipPyTypeDict.*", DeprecationWarning)
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_app_gui_can_be_executed_by_file_path(self):
        root = Path(__file__).resolve().parents[1]
        script = (
            "import runpy\n"
            "from PyQt6 import QtWidgets\n"
            "QtWidgets.QWidget.show = lambda self: print('SHOW_CALLED')\n"
            "QtWidgets.QApplication.exec = lambda self: print('EXEC_CALLED') or 0\n"
            f"runpy.run_path({str(root / 'app' / 'gui.py')!r}, run_name='__main__')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SHOW_CALLED", result.stdout)
        self.assertIn("EXEC_CALLED", result.stdout)

    def test_window_has_modern_sidebar_layout_and_run_controls(self):
        window = Ui_MainWindow()

        nav_labels = [button.text() for button in window.nav_buttons]
        stylesheet = window.styleSheet()
        main_margins = window.main_layout.contentsMargins()
        content_margins = window.content_layout.contentsMargins()

        self.assertEqual(nav_labels, ["Profiles", "Settings", "Logs"])
        self.assertEqual(window.pages.count(), 3)
        self.assertEqual(window.sidebar.objectName(), "Sidebar")
        self.assertFalse(hasattr(window, "quick_widget"))
        self.assertLessEqual(window.sidebar.width(), 190)
        self.assertLessEqual(window.table.verticalHeader().defaultSectionSize(), 40)
        self.assertLessEqual(main_margins.left(), 12)
        self.assertLessEqual(main_margins.top(), 12)
        self.assertLessEqual(main_margins.right(), 12)
        self.assertLessEqual(main_margins.bottom(), 12)
        self.assertLessEqual(content_margins.left(), 12)
        self.assertLessEqual(content_margins.top(), 12)
        self.assertLessEqual(content_margins.right(), 12)
        self.assertLessEqual(content_margins.bottom(), 12)
        self.assertEqual(window.header_title.text(), "YouTube -> TikTok")
        self.assertEqual(window.group_create.title(), "Create profiles")
        self.assertEqual(window.button_run_all.text(), "Run")
        self.assertEqual(window.button_stop.text(), "Stop")
        self.assertTrue(hasattr(window, "logs_view"))
        self.assertTrue(window.logs_view.isReadOnly())
        self.assertEqual(window.input_poll_interval.minimum(), 1)
        self.assertEqual(window.input_split_threshold.value(), 10)
        self.assertIn("#F8FAFC", stylesheet)
        self.assertIn("#FFFFFF", stylesheet)
        self.assertIn("#111827", stylesheet)
        self.assertIn("#D1D5DB", stylesheet)
        self.assertNotIn("#0B0F19", stylesheet)
        self.assertNotIn("#172033", stylesheet)
        self.assertNotIn("#2563EB", stylesheet)
        self.assertIn("QTableWidget::item", stylesheet)
        self.assertIn("QLabel {", stylesheet)

    def test_settings_are_grouped_compactly(self):
        window = Ui_MainWindow()

        groups = [
            window.settings_timing_group,
            window.settings_split_schedule_group,
            window.settings_storage_group,
            window.settings_telegram_group,
        ]

        self.assertEqual([group.title() for group in groups], ["Timing", "Split schedule", "Storage", "Telegram"])
        self.assertEqual(window.settings_groups_layout.count(), 4)
        self.assertLessEqual(window.settings_layout.count(), 3)
        self.assertLessEqual(window.settings_layout.spacing(), 8)
        self.assertEqual(window.split_threshold_label.text(), "Split video > (min)")
        self.assertEqual(
            window.input_split_threshold.toolTip(),
            "Videos longer than this many minutes are split into 3 equal parts.",
        )
        self.assertGreaterEqual(window.input_split_schedule_gap.value(), 1)
        self.assertIsInstance(window.input_split_schedule_enabled.isChecked(), bool)

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
                window.profiles[0]["channel_url"] = "https://www.youtube.com/@hoangacc/videos"
                window.table.cellWidget(0, 4).setCurrentText("videos")

                window.run_all_profiles()

            profile = load_profiles(profiles_path)[0]
            self.assertEqual(profile["channel_url"], "https://www.youtube.com/@hoangacc/videos")
            self.assertEqual(profile["channel_mode"], "videos")

    def test_profile_table_actions_are_readable_in_compact_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles_path = root / "data" / "profiles.json"
            create_chrome_profiles(profiles_path, root / "profiles", 1, "acc", "", "")

            with patch.object(gui_module, "PROFILES_PATH", profiles_path):
                window = Ui_MainWindow()

            expected_widths = {
                4: 76,
                6: 64,
                7: 64,
                8: 72,
            }
            for column, minimum_width in expected_widths.items():
                self.assertGreaterEqual(window.table.columnWidth(column), minimum_width)

            self.assertGreaterEqual(window.table.cellWidget(0, 4).minimumWidth(), 76)
            self.assertGreaterEqual(window.table.cellWidget(0, 6).minimumWidth(), 64)
            self.assertGreaterEqual(window.table.cellWidget(0, 7).minimumWidth(), 64)
            self.assertGreaterEqual(window.table.cellWidget(0, 8).minimumWidth(), 72)

    def test_profile_table_has_compact_metadata_columns_and_saves_note_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles_path = root / "data" / "profiles.json"
            create_chrome_profiles(profiles_path, root / "profiles", 1, "acc", "", "")

            with patch.object(gui_module, "PROFILES_PATH", profiles_path):
                window = Ui_MainWindow()
                note_input = window.table.cellWidget(0, 1)
                group_input = window.table.cellWidget(0, 2)
                note_input.setText("note edit")
                group_input.setText("group edit")
                window.table.cellWidget(0, 7).click()

            profile = load_profiles(profiles_path)[0]
            self.assertEqual(profile["note"], "note edit")
            self.assertEqual(profile["group"], "group edit")
            self.assertLessEqual(window.table.columnWidth(0), 130)
            self.assertLessEqual(window.table.columnWidth(1), 150)
            self.assertLessEqual(window.table.columnWidth(2), 130)
            self.assertGreater(window.table.columnWidth(3), window.table.columnWidth(1))

    def test_channel_url_cell_opens_multiline_dialog_and_has_green_count_badge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles_path = root / "data" / "profiles.json"
            profiles = create_chrome_profiles(profiles_path, root / "profiles", 1, "acc", "", "")
            from app.profiles.store import update_profile_channel

            update_profile_channel(
                profiles_path,
                profiles[0]["id"],
                "https://www.youtube.com/@a/videos\nhttps://www.youtube.com/@b/videos",
                "videos",
            )

            with patch.object(gui_module, "PROFILES_PATH", profiles_path):
                window = Ui_MainWindow()

                cell = window.table.cellWidget(0, 3)
                button = cell.findChild(QtWidgets.QPushButton, "ChannelUrlOpenButton")
                badge = cell.findChild(QtWidgets.QLabel, "ChannelUrlCountBadge")

                self.assertIsNotNone(button)
                self.assertNotIn("\n", button.text())
                self.assertEqual(badge.text(), "2 URLs")
                self.assertEqual(badge.palette().color(QtGui.QPalette.ColorRole.WindowText).name().lower(), "#166534")
                self.assertEqual(
                    window.table.horizontalHeader().sectionResizeMode(3),
                    QtWidgets.QHeaderView.ResizeMode.Stretch,
                )

                dialog = window.create_channel_url_dialog(window.profiles[0], "videos")
                editor = dialog.findChild(QtWidgets.QPlainTextEdit)
                save_button = dialog.findChild(QtWidgets.QPushButton, "ChannelUrlDialogSaveButton")
                self.assertEqual(editor.toPlainText().count("\n"), 1)
                editor.setPlainText("https://www.youtube.com/@c/videos")
                save_button.click()
                self.assertEqual(load_profiles(profiles_path)[0]["channel_url"], "https://www.youtube.com/@c/videos")

    def test_save_settings_persists_split_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(gui_module, "APP_DB_PATH", root / "app.db"):
                window = Ui_MainWindow()
                window.input_split_threshold.setValue(15)
                window.input_split_schedule_enabled.setChecked(True)
                window.input_split_schedule_gap.setValue(4)
                window.save_settings()

                self.assertEqual(window.database.get_setting("split_threshold_minutes"), "15")
                self.assertEqual(window.database.get_setting("split_schedule_enabled"), "1")
                self.assertEqual(window.database.get_setting("split_schedule_gap_hours"), "4")

if __name__ == "__main__":
    unittest.main()
