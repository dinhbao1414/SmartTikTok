from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6 import QtCore, QtGui, QtWidgets

from app.database import AppDatabase
from app.paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_PATH, ROOT_DIR
from app.profiles.store import (
    create_chrome_profiles,
    delete_profile_record,
    load_profiles,
    split_channel_urls,
    update_profile_channel,
    update_profile_fields,
)
from app.workers.upload_worker import YoutubeToTikTokWorker


DEFAULT_PROFILES_DIR = ROOT_DIR / "profiles"


class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.open_browsers = {}
        self.profiles = []
        self.database = AppDatabase(APP_DB_PATH)
        self.database.initialize()
        self.worker_thread = None
        self.worker = None
        self._logs_refresh_pending = False
        self._profiles_refresh_pending = False
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
        self.reload_profiles()
        self.refresh_logs()

    def setup_ui(self):
        self.setObjectName("MainWindow")
        self.setWindowTitle("YouTube To TikTok Uploader")
        self.resize(1280, 760)

        self.centralwidget = QtWidgets.QWidget(parent=self)
        self.centralwidget.setObjectName("AppRoot")
        self.setCentralWidget(self.centralwidget)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.setup_sidebar()

        self.content_shell = QtWidgets.QFrame(parent=self.centralwidget)
        self.content_shell.setObjectName("ContentShell")
        self.content_layout = QtWidgets.QVBoxLayout(self.content_shell)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_shell, 1)

        self.setup_header()

        self.profiles_tab = QtWidgets.QWidget()
        self.settings_tab = QtWidgets.QWidget()
        self.logs_tab = QtWidgets.QWidget()

        self.pages = QtWidgets.QStackedWidget(parent=self.content_shell)
        self.pages.setObjectName("Pages")
        self.pages.addWidget(self.profiles_tab)
        self.pages.addWidget(self.settings_tab)
        self.pages.addWidget(self.logs_tab)
        self.content_layout.addWidget(self.pages, 1)

        self.setup_profiles_tab()
        self.setup_settings_tab()
        self.setup_logs_tab()
        self.set_active_page(0)

        self.statusbar = QtWidgets.QStatusBar(parent=self)
        self.setStatusBar(self.statusbar)
        self.apply_modern_style()

    def setup_sidebar(self):
        self.sidebar = QtWidgets.QFrame(parent=self.centralwidget)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(184)
        self.sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 12, 10, 12)
        self.sidebar_layout.setSpacing(6)
        self.main_layout.addWidget(self.sidebar)

        self.brand_label = QtWidgets.QLabel("YT -> TikTok", parent=self.sidebar)
        self.brand_label.setObjectName("BrandLabel")
        self.brand_caption = QtWidgets.QLabel("Profile uploader", parent=self.sidebar)
        self.brand_caption.setObjectName("MutedLabel")
        self.sidebar_layout.addWidget(self.brand_label)
        self.sidebar_layout.addWidget(self.brand_caption)
        self.sidebar_layout.addSpacing(10)

        self.nav_buttons = []
        for index, label in enumerate(["Profiles", "Settings", "Logs"]):
            button = QtWidgets.QPushButton(label, parent=self.sidebar)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _, i=index: self.set_active_page(i))
            self.nav_buttons.append(button)
            self.sidebar_layout.addWidget(button)
        self.sidebar_layout.addStretch(1)

    def setup_header(self):
        self.header = QtWidgets.QFrame(parent=self.content_shell)
        self.header.setObjectName("Header")
        header_layout = QtWidgets.QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(1)
        self.header_title = QtWidgets.QLabel("YouTube -> TikTok", parent=self.header)
        self.header_title.setObjectName("HeaderTitle")
        self.header_subtitle = QtWidgets.QLabel("Profiles, settings, logs", parent=self.header)
        self.header_subtitle.setObjectName("MutedLabel")
        title_box.addWidget(self.header_title)
        title_box.addWidget(self.header_subtitle)
        header_layout.addLayout(title_box, 1)

        self.setup_run_controls(header_layout)
        self.content_layout.addWidget(self.header)

    def set_active_page(self, index):
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def setup_profiles_tab(self):
        self.profiles_layout = QtWidgets.QVBoxLayout(self.profiles_tab)
        self.profiles_layout.setContentsMargins(0, 0, 0, 0)
        self.profiles_layout.setSpacing(8)
        self.setup_create_panel()
        self.setup_table()

    def setup_create_panel(self):
        self.group_create = QtWidgets.QGroupBox("Create profiles", parent=self.profiles_tab)
        self.profiles_layout.addWidget(self.group_create)

        layout = QtWidgets.QGridLayout(self.group_create)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        self.spin_count = QtWidgets.QSpinBox(parent=self.group_create)
        self.spin_count.setRange(1, 999)
        self.spin_count.setValue(1)

        self.input_name = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_name.setPlaceholderText("Example: Acc")

        self.input_note = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_group = QtWidgets.QLineEdit(parent=self.group_create)

        self.input_profile_dir = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_profile_dir.setText(str(DEFAULT_PROFILES_DIR))
        self.button_browse = QtWidgets.QPushButton("Browse", parent=self.group_create)

        self.button_create = QtWidgets.QPushButton("Create", parent=self.group_create)
        self.button_reload = QtWidgets.QPushButton("Reload", parent=self.group_create)

        layout.addWidget(QtWidgets.QLabel("Count"), 0, 0)
        layout.addWidget(self.spin_count, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Name prefix"), 0, 2)
        layout.addWidget(self.input_name, 0, 3)
        layout.addWidget(QtWidgets.QLabel("Group"), 0, 4)
        layout.addWidget(self.input_group, 0, 5)

        layout.addWidget(QtWidgets.QLabel("Note"), 1, 0)
        layout.addWidget(self.input_note, 1, 1, 1, 3)
        layout.addWidget(QtWidgets.QLabel("Profile folder"), 1, 4)
        layout.addWidget(self.input_profile_dir, 1, 5)
        layout.addWidget(self.button_browse, 1, 6)

        layout.addWidget(self.button_create, 0, 6)
        layout.addWidget(self.button_reload, 2, 6)

        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(5, 1)

    def setup_run_controls(self, controls):
        self.button_run_all = QtWidgets.QPushButton("Run", parent=self.header)
        self.button_run_all.setObjectName("PrimaryButton")
        self.button_stop = QtWidgets.QPushButton("Stop", parent=self.header)
        self.button_stop.setObjectName("DangerButton")
        self.button_stop.setEnabled(False)
        controls.addWidget(self.button_run_all)
        controls.addWidget(self.button_stop)

    def setup_table(self):
        self.table = QtWidgets.QTableWidget(parent=self.profiles_tab)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Note",
            "Group",
            "Channel URL",
            "Mode",
            "Status",
            "Open",
            "Save",
            "Delete",
        ])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(8, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.profiles_layout.addWidget(self.table)

    def apply_high_contrast_palette(self, widget):
        palette = widget.palette()
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#111827"))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#111827"))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#111827"))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#F8FAFC"))
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#F8FAFC"))
        widget.setPalette(palette)

    def setup_settings_tab(self):
        self.settings_layout = QtWidgets.QVBoxLayout(self.settings_tab)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(8)

        self.settings_groups_layout = QtWidgets.QHBoxLayout()
        self.settings_groups_layout.setSpacing(8)

        self.settings_timing_group = QtWidgets.QGroupBox("Timing", parent=self.settings_tab)
        timing_layout = QtWidgets.QGridLayout(self.settings_timing_group)
        timing_layout.setContentsMargins(8, 8, 8, 8)
        timing_layout.setHorizontalSpacing(8)
        timing_layout.setVerticalSpacing(6)

        self.input_poll_interval = QtWidgets.QSpinBox(parent=self.settings_timing_group)
        self.input_poll_interval.setRange(1, 3600)
        self.input_poll_interval.setValue(10)
        self.input_split_threshold = QtWidgets.QSpinBox(parent=self.settings_timing_group)
        self.input_split_threshold.setRange(1, 1440)
        self.input_split_threshold.setValue(10)
        self.input_split_threshold.setToolTip(
            "Videos longer than this many minutes are split into 3 equal parts."
        )

        timing_layout.addWidget(QtWidgets.QLabel("Poll interval (sec)", parent=self.settings_timing_group), 0, 0)
        timing_layout.addWidget(self.input_poll_interval, 0, 1)
        self.split_threshold_label = QtWidgets.QLabel("Split video > (min)", parent=self.settings_timing_group)
        timing_layout.addWidget(self.split_threshold_label, 1, 0)
        timing_layout.addWidget(self.input_split_threshold, 1, 1)
        timing_layout.setColumnStretch(1, 1)

        self.settings_split_schedule_group = QtWidgets.QGroupBox("Split schedule", parent=self.settings_tab)
        split_schedule_layout = QtWidgets.QGridLayout(self.settings_split_schedule_group)
        split_schedule_layout.setContentsMargins(8, 8, 8, 8)
        split_schedule_layout.setHorizontalSpacing(8)
        split_schedule_layout.setVerticalSpacing(6)

        self.input_split_schedule_enabled = QtWidgets.QCheckBox("Enable", parent=self.settings_split_schedule_group)
        self.input_split_schedule_gap = QtWidgets.QSpinBox(parent=self.settings_split_schedule_group)
        self.input_split_schedule_gap.setRange(1, 168)
        self.input_split_schedule_gap.setValue(3)
        self.input_split_schedule_gap.setSuffix(" h")
        self.input_split_schedule_gap.setToolTip("Delay between split video parts.")
        split_schedule_layout.addWidget(self.input_split_schedule_enabled, 0, 0, 1, 2)
        split_schedule_layout.addWidget(QtWidgets.QLabel("Gap", parent=self.settings_split_schedule_group), 1, 0)
        split_schedule_layout.addWidget(self.input_split_schedule_gap, 1, 1)
        split_schedule_layout.setColumnStretch(1, 1)

        self.settings_storage_group = QtWidgets.QGroupBox("Storage", parent=self.settings_tab)
        storage_layout = QtWidgets.QGridLayout(self.settings_storage_group)
        storage_layout.setContentsMargins(8, 8, 8, 8)
        storage_layout.setHorizontalSpacing(8)
        storage_layout.setVerticalSpacing(6)

        self.input_download_dir = QtWidgets.QLineEdit(parent=self.settings_storage_group)
        storage_layout.addWidget(QtWidgets.QLabel("Download folder", parent=self.settings_storage_group), 0, 0)
        storage_layout.addWidget(self.input_download_dir, 0, 1)
        storage_layout.setColumnStretch(1, 1)

        self.settings_telegram_group = QtWidgets.QGroupBox("Telegram", parent=self.settings_tab)
        telegram_layout = QtWidgets.QGridLayout(self.settings_telegram_group)
        telegram_layout.setContentsMargins(8, 8, 8, 8)
        telegram_layout.setHorizontalSpacing(8)
        telegram_layout.setVerticalSpacing(6)

        self.input_telegram_token = QtWidgets.QLineEdit(parent=self.settings_telegram_group)
        self.input_telegram_chat_id = QtWidgets.QLineEdit(parent=self.settings_telegram_group)
        self.button_save_settings = QtWidgets.QPushButton("Save settings", parent=self.settings_tab)

        telegram_layout.addWidget(QtWidgets.QLabel("Bot token", parent=self.settings_telegram_group), 0, 0)
        telegram_layout.addWidget(self.input_telegram_token, 0, 1)
        telegram_layout.addWidget(QtWidgets.QLabel("Chat id", parent=self.settings_telegram_group), 1, 0)
        telegram_layout.addWidget(self.input_telegram_chat_id, 1, 1)
        telegram_layout.setColumnStretch(1, 1)

        self.settings_groups_layout.addWidget(self.settings_timing_group, 1)
        self.settings_groups_layout.addWidget(self.settings_split_schedule_group, 1)
        self.settings_groups_layout.addWidget(self.settings_storage_group, 2)
        self.settings_groups_layout.addWidget(self.settings_telegram_group, 2)

        save_layout = QtWidgets.QHBoxLayout()
        save_layout.addStretch(1)
        save_layout.addWidget(self.button_save_settings)

        self.settings_layout.addLayout(self.settings_groups_layout)
        self.settings_layout.addLayout(save_layout)
        self.settings_layout.addStretch(1)

    def setup_logs_tab(self):
        layout = QtWidgets.QVBoxLayout(self.logs_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.button_refresh_logs = QtWidgets.QPushButton("Refresh logs", parent=self.logs_tab)
        self.logs_view = QtWidgets.QPlainTextEdit(parent=self.logs_tab)
        self.logs_view.setReadOnly(True)
        self.logs_view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.button_refresh_logs)
        layout.addWidget(self.logs_view)

    def apply_modern_style(self):
        self.setStyleSheet("""
            QWidget#AppRoot {
                background: #F8FAFC;
                color: #111827;
                font-family: "Segoe UI Variable", "Segoe UI", Arial;
                font-size: 13px;
            }
            QWidget {
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
            }
            QFrame#Sidebar {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
            }
            QFrame#ContentShell {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
            }
            QFrame#Header {
                background: transparent;
            }
            QLabel#BrandLabel {
                color: #111827;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#HeaderTitle {
                color: #111827;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#MutedLabel {
                color: #6B7280;
                font-size: 12px;
            }
            QGroupBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
                color: #111827;
                font-weight: 650;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                color: #111827;
                background: #FFFFFF;
            }
            QPushButton {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 18px;
            }
            QPushButton:hover {
                background: #F3F4F6;
                border-color: #9CA3AF;
            }
            QPushButton:pressed {
                background: #E5E7EB;
            }
            QPushButton:disabled {
                color: #9CA3AF;
                background: #F9FAFB;
                border-color: #E5E7EB;
            }
            QPushButton#PrimaryButton {
                background: #111827;
                border-color: #111827;
                color: #FFFFFF;
                font-weight: 650;
                min-width: 70px;
            }
            QPushButton#PrimaryButton:hover {
                background: #374151;
            }
            QPushButton#DangerButton {
                background: #FFFFFF;
                border-color: #D1D5DB;
                color: #991B1B;
                min-width: 64px;
            }
            QPushButton#DangerButton:hover {
                background: #FEF2F2;
                border-color: #FCA5A5;
            }
            QPushButton#NavButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 7px 8px;
                text-align: left;
                color: #374151;
                font-weight: 600;
            }
            QPushButton#NavButton:hover {
                background: #F3F4F6;
                border-color: #E5E7EB;
            }
            QPushButton#NavButton[active="true"] {
                background: #F3F4F6;
                border-color: #D1D5DB;
                color: #111827;
            }
            QLineEdit, QSpinBox, QComboBox {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px 7px;
                min-height: 18px;
                selection-background-color: #374151;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #6B7280;
            }
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F8FAFC;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                gridline-color: #E5E7EB;
                selection-background-color: #E5E7EB;
                selection-color: #111827;
            }
            QTableWidget::item {
                color: #111827;
                padding: 5px;
            }
            QHeaderView::section {
                background: #F3F4F6;
                color: #111827;
                border: none;
                border-bottom: 1px solid #D1D5DB;
                padding: 6px 7px;
                font-weight: 650;
            }
            QPlainTextEdit {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 12px;
            }
            QStatusBar {
                background: #F8FAFC;
                color: #6B7280;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def setup_connections(self):
        self.button_create.clicked.connect(self.create_profiles)
        self.button_reload.clicked.connect(self.reload_profiles)
        self.button_browse.clicked.connect(self.choose_profiles_dir)
        self.button_run_all.clicked.connect(self.run_all_profiles)
        self.button_stop.clicked.connect(self.stop_worker)
        self.button_save_settings.clicked.connect(self.save_settings)
        self.button_refresh_logs.clicked.connect(self.refresh_logs)

    def choose_profiles_dir(self):
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose Chrome profile folder",
            self.input_profile_dir.text() or str(DEFAULT_PROFILES_DIR),
        )
        if selected:
            self.input_profile_dir.setText(selected)

    def create_profiles(self):
        profiles = create_chrome_profiles(
            data_path=PROFILES_PATH,
            profiles_dir=Path(self.input_profile_dir.text() or DEFAULT_PROFILES_DIR),
            count=self.spin_count.value(),
            name_prefix=self.input_name.text(),
            note=self.input_note.text(),
            group=self.input_group.text(),
        )
        self.profiles = profiles
        self.render_table()
        self.statusbar.showMessage(f"Created {self.spin_count.value()} Chrome profiles", 5000)

    def reload_profiles(self):
        self.profiles = load_profiles(PROFILES_PATH)
        self.render_table()
        self.statusbar.showMessage(f"Loaded {len(self.profiles)} profiles", 3000)

    def render_table(self):
        compact_column_widths = {
            0: 110,
            1: 140,
            2: 120,
            3: 420,
            4: 76,
            5: 90,
            6: 64,
            7: 64,
            8: 72,
        }
        for column, width in compact_column_widths.items():
            self.table.setColumnWidth(column, width)

        self.table.setRowCount(len(self.profiles))
        for row, profile in enumerate(self.profiles):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(profile.get("name", ""))))

            note_input = QtWidgets.QLineEdit(parent=self.table)
            note_input.setText(profile.get("note", ""))
            self.apply_high_contrast_palette(note_input)
            self.table.setCellWidget(row, 1, note_input)

            group_input = QtWidgets.QLineEdit(parent=self.table)
            group_input.setText(profile.get("group", ""))
            self.apply_high_contrast_palette(group_input)
            self.table.setCellWidget(row, 2, group_input)

            channel_cell = self._create_channel_url_cell(profile)
            self.table.setCellWidget(row, 3, channel_cell)

            mode_combo = QtWidgets.QComboBox(parent=self.table)
            mode_combo.addItems(["shorts", "videos"])
            mode_combo.setCurrentText(profile.get("channel_mode", "shorts"))
            mode_combo.setMinimumWidth(compact_column_widths[4])
            self.apply_high_contrast_palette(mode_combo)
            self.table.setCellWidget(row, 4, mode_combo)

            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(profile.get("last_status", "Idle"))))

            button_open = QtWidgets.QPushButton("Open", parent=self.table)
            button_open.setMinimumWidth(compact_column_widths[6])
            button_open.clicked.connect(lambda _, p=profile: self.open_profile(p))
            self.table.setCellWidget(row, 6, button_open)

            save_button = QtWidgets.QPushButton("Save", parent=self.table)
            save_button.setMinimumWidth(compact_column_widths[7])
            save_button.clicked.connect(
                lambda _, p=profile, note=note_input, group=group_input, mode=mode_combo: self.save_profile_row(
                    p,
                    note.text(),
                    group.text(),
                    p.get("channel_url", ""),
                    mode.currentText(),
                )
            )
            self.table.setCellWidget(row, 7, save_button)

            button_delete = QtWidgets.QPushButton("Delete", parent=self.table)
            button_delete.setMinimumWidth(compact_column_widths[8])
            button_delete.clicked.connect(lambda _, p=profile: self.delete_profile(p))
            self.table.setCellWidget(row, 8, button_delete)

    def save_channel(self, profile, channel_url, channel_mode):
        return self.save_profile_row(
            profile,
            profile.get("note", ""),
            profile.get("group", ""),
            channel_url,
            channel_mode,
        )

    def save_profile_row(self, profile, note, group, channel_url, channel_mode):
        try:
            update_profile_fields(
                PROFILES_PATH,
                profile.get("id"),
                note=note,
                group=group,
                channel_url=channel_url,
                channel_mode=channel_mode,
            )
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "Invalid channel mode", str(error))
            return
        self.reload_profiles()
        self.statusbar.showMessage("Saved profile", 3000)

    def save_visible_channel_assignments(self):
        for row, profile in enumerate(self.profiles):
            note_input = self.table.cellWidget(row, 1)
            group_input = self.table.cellWidget(row, 2)
            mode_combo = self.table.cellWidget(row, 4)
            if not note_input or not group_input or not mode_combo:
                continue
            try:
                update_profile_fields(
                    PROFILES_PATH,
                    profile.get("id"),
                    note=note_input.text(),
                    group=group_input.text(),
                    channel_url=profile.get("channel_url", ""),
                    channel_mode=mode_combo.currentText(),
                )
            except ValueError as error:
                QtWidgets.QMessageBox.warning(self, "Invalid channel mode", str(error))
                return False
        self.profiles = load_profiles(PROFILES_PATH)
        return True

    def _create_channel_url_cell(self, profile):
        cell = QtWidgets.QWidget(parent=self.table)
        layout = QtWidgets.QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        urls = split_channel_urls(profile.get("channel_url", ""))
        button = QtWidgets.QPushButton(parent=cell)
        button.setObjectName("ChannelUrlOpenButton")
        button.setText(urls[0] if urls else "Add channel URLs")
        button.setToolTip(profile.get("channel_url", ""))
        button.setMinimumWidth(180)
        button.clicked.connect(lambda _, p=profile: self.open_channel_url_dialog(p))

        badge = QtWidgets.QLabel(parent=cell)
        badge.setObjectName("ChannelUrlCountBadge")
        badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        badge.setMinimumWidth(54)
        badge_palette = badge.palette()
        badge_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#166534"))
        badge.setPalette(badge_palette)
        badge.setStyleSheet(
            "QLabel#ChannelUrlCountBadge {"
            "background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; "
            "border-radius: 6px; padding: 3px 6px; font-weight: 700;"
            "}"
        )

        count = len(urls)
        badge.setText(f"{count} URL" if count == 1 else f"{count} URLs")
        layout.addWidget(button, 1)
        layout.addWidget(badge)
        return cell

    def create_channel_url_dialog(self, profile, channel_mode):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Channel URLs")
        dialog.resize(640, 360)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        editor = QtWidgets.QPlainTextEdit(parent=dialog)
        editor.setPlainText(profile.get("channel_url", ""))
        editor.setPlaceholderText("Paste one YouTube channel URL per line")
        layout.addWidget(editor, 1)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        save_button = QtWidgets.QPushButton("Save", parent=dialog)
        save_button.setObjectName("ChannelUrlDialogSaveButton")
        close_button = QtWidgets.QPushButton("Close", parent=dialog)
        buttons.addWidget(save_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def save_and_close():
            self.save_channel(profile, editor.toPlainText(), channel_mode)
            dialog.accept()

        save_button.clicked.connect(save_and_close)
        close_button.clicked.connect(dialog.reject)
        return dialog

    def open_channel_url_dialog(self, profile):
        mode_combo = None
        try:
            row = self.profiles.index(profile)
            mode_combo = self.table.cellWidget(row, 4)
        except ValueError:
            pass
        channel_mode = mode_combo.currentText() if mode_combo else profile.get("channel_mode", "shorts")
        self.create_channel_url_dialog(profile, channel_mode).exec()

    def load_settings(self):
        try:
            poll_interval = int(self.database.get_setting("poll_interval_seconds", "10"))
        except ValueError:
            poll_interval = 10
        self.input_poll_interval.setValue(max(1, poll_interval))
        try:
            split_threshold = int(float(self.database.get_setting("split_threshold_minutes", "10")))
        except ValueError:
            split_threshold = 10
        self.input_split_threshold.setValue(max(1, split_threshold))
        self.input_split_schedule_enabled.setChecked(
            self.database.get_setting("split_schedule_enabled", "0") == "1"
        )
        try:
            split_schedule_gap = int(float(self.database.get_setting("split_schedule_gap_hours", "3")))
        except ValueError:
            split_schedule_gap = 3
        self.input_split_schedule_gap.setValue(max(1, split_schedule_gap))
        self.input_download_dir.setText(self.database.get_setting("download_dir", str(DOWNLOADS_DIR)))
        self.input_telegram_token.setText(self.database.get_setting("telegram_bot_token", ""))
        self.input_telegram_chat_id.setText(self.database.get_setting("telegram_chat_id", ""))

    def save_settings(self):
        self.database.set_setting("poll_interval_seconds", self.input_poll_interval.value())
        self.database.set_setting("split_threshold_minutes", self.input_split_threshold.value())
        self.database.set_setting("split_schedule_enabled", "1" if self.input_split_schedule_enabled.isChecked() else "0")
        self.database.set_setting("split_schedule_gap_hours", self.input_split_schedule_gap.value())
        self.database.set_setting("download_dir", self.input_download_dir.text() or str(DOWNLOADS_DIR))
        self.database.set_setting("telegram_bot_token", self.input_telegram_token.text())
        self.database.set_setting("telegram_chat_id", self.input_telegram_chat_id.text())
        self.statusbar.showMessage("Saved settings", 3000)

    def refresh_logs(self):
        self._logs_refresh_pending = False
        logs = self.database.get_recent_logs(limit=60)
        lines = []
        for log in logs:
            created_at = str(log["created_at"])[11:19]
            profile = str(log["profile_id"] or "")
            profile_tail = profile[-6:] if profile else "-"
            job = log["job_id"] or "-"
            lines.append(f"{created_at} | {log['level']} | P:{profile_tail} | J:{job} | {log['message']}")
        self.logs_view.setPlainText("\n".join(lines))

    def schedule_refresh_logs(self):
        if self._logs_refresh_pending:
            return
        self._logs_refresh_pending = True
        QtCore.QTimer.singleShot(500, self.refresh_logs)

    def schedule_reload_profiles(self):
        if self._profiles_refresh_pending:
            return
        self._profiles_refresh_pending = True
        QtCore.QTimer.singleShot(800, self._reload_profiles_from_timer)

    def _reload_profiles_from_timer(self):
        self._profiles_refresh_pending = False
        self.reload_profiles()

    def run_all_profiles(self):
        if self.worker_thread:
            return
        self.save_settings()
        if not self.save_visible_channel_assignments():
            return
        self.worker_thread = QtCore.QThread(self)
        self.worker = YoutubeToTikTokWorker(PROFILES_PATH, APP_DB_PATH)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run_forever)
        self.worker.log_created.connect(self.schedule_refresh_logs)
        self.worker.profile_status.connect(lambda _profile_id, _status: self.schedule_reload_profiles())
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.worker_finished)
        self.worker_thread.start()
        self.button_run_all.setEnabled(False)
        self.button_stop.setEnabled(True)
        self.statusbar.showMessage("Worker running", 3000)

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
        self.button_stop.setEnabled(False)
        self.statusbar.showMessage("Stopping worker", 3000)

    def worker_finished(self):
        self.worker_thread = None
        self.worker = None
        self.button_run_all.setEnabled(True)
        self.button_stop.setEnabled(False)
        self.reload_profiles()
        self.refresh_logs()
        self.statusbar.showMessage("Worker stopped", 3000)

    def open_profile(self, profile):
        profile_id = profile.get("id")
        if profile_id in self.open_browsers:
            self.statusbar.showMessage("Profile already open", 4000)
            return

        profile_path = Path(profile.get("profile_path", ""))
        profile_path.mkdir(parents=True, exist_ok=True)
        try:
            from Controller.BrowserController import ChromeProfileBrowser

            browser = ChromeProfileBrowser(profile_path)
            browser.open("https://www.google.com")
            self.open_browsers[profile_id] = browser
            self.statusbar.showMessage(f"Opened profile: {profile.get('name', '')}", 5000)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Cannot open Chrome", str(error))

    def delete_profile(self, profile):
        profile_id = profile.get("id")
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete profile",
            f"Delete profile '{profile.get('name', '')}' and its data folder?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        browser = self.open_browsers.pop(profile_id, None)
        if browser:
            try:
                browser.close()
            except Exception:
                pass

        try:
            delete_profile_record(PROFILES_PATH, profile_id)
            self.reload_profiles()
            self.statusbar.showMessage("Deleted profile", 5000)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Cannot delete profile", str(error))

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        if self.worker_thread and self.worker_thread.isRunning():
            self.statusbar.showMessage("Stopping worker before close", 3000)
            if not self.worker_thread.wait(10000):
                event.ignore()
                return
        for browser in list(self.open_browsers.values()):
            try:
                browser.close()
            except Exception:
                pass
        self.open_browsers.clear()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui_MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

