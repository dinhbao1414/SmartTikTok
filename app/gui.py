from pathlib import Path
import sys
import threading

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6 import QtCore, QtGui, QtWidgets

from app.branding import app_icon_path, is_valid_ico
from app.database import AppDatabase
from app.paths import APP_DB_PATH, DOWNLOADS_DIR, PROFILES_DIR, PROFILES_PATH, resolve_app_path
from app.profiles.store import (
    create_chrome_profiles,
    delete_profile_record,
    load_profiles,
    repair_profile_paths,
    split_channel_urls,
    update_profile_channel,
    update_profile_fields,
)
from app.version import DEFAULT_APP_VERSION, read_app_version
from app.workers.upload_worker import YoutubeToTikTokWorker
from version_manager import VersionManager


DEFAULT_PROFILES_DIR = PROFILES_DIR
APP_VERSION = DEFAULT_APP_VERSION
UPDATE_REPO_URL = "https://github.com/dinhbao1414/SmartTikTok"
CHANNEL_MODE_LABELS = {
    "shorts": "Video ngắn",
    "videos": "Video dài",
}
STATUS_LABELS = {
    "Idle": "Chờ",
    "Running": "Đang chạy",
    "uploaded": "Đã đăng",
    "failed": "Lỗi",
    "skipped": "Bỏ qua",
    "discovered": "Đã phát hiện",
    "downloading": "Đang tải",
    "downloaded": "Đã tải",
    "uploading": "Đang đăng",
}


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
        self.app_version = read_app_version(APP_VERSION)
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
        self.reload_profiles()
        self.refresh_logs()

    def setup_ui(self):
        self.setObjectName("MainWindow")
        self.setWindowTitle(f"SmartTikTok v{self.app_version}")
        self._app_icon = self.create_app_icon()
        if self._app_icon is not None:
            self.setWindowIcon(self._app_icon)
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

        brand_row = QtWidgets.QHBoxLayout()
        brand_row.setSpacing(8)
        self.logo_label = QtWidgets.QLabel(parent=self.sidebar)
        self.logo_label.setObjectName("LogoLabel")
        self.logo_label.setFixedSize(36, 36)
        self.logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if self._app_icon is not None:
            self.logo_label.setPixmap(self._app_icon.pixmap(32, 32))
        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(1)
        self.brand_label = QtWidgets.QLabel("SmartTikTok", parent=self.sidebar)
        self.brand_label.setObjectName("BrandLabel")
        self.brand_caption = QtWidgets.QLabel("YT -> TikTok", parent=self.sidebar)
        self.brand_caption.setObjectName("MutedLabel")
        brand_text.addWidget(self.brand_label)
        brand_text.addWidget(self.brand_caption)
        brand_row.addWidget(self.logo_label)
        brand_row.addLayout(brand_text, 1)
        self.sidebar_layout.addLayout(brand_row)
        self.sidebar_layout.addSpacing(10)

        self.nav_buttons = []
        for index, label in enumerate(["Hồ sơ", "Cài đặt", "Nhật ký"]):
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
        self.header_title = QtWidgets.QLabel("Quản lý YouTube -> TikTok", parent=self.header)
        self.header_title.setObjectName("HeaderTitle")
        self.header_subtitle = QtWidgets.QLabel("Hồ sơ, cài đặt, nhật ký", parent=self.header)
        self.header_subtitle.setObjectName("MutedLabel")
        title_box.addWidget(self.header_title)
        title_box.addWidget(self.header_subtitle)
        header_layout.addLayout(title_box, 1)

        self.setup_run_controls(header_layout)
        self.content_layout.addWidget(self.header)

    def create_app_icon(self):
        icon_path = app_icon_path()
        if not icon_path.exists() or not is_valid_ico(icon_path):
            return None
        icon = QtGui.QIcon(str(icon_path))
        return None if icon.isNull() else icon

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
        self.group_create = QtWidgets.QGroupBox("Tạo hồ sơ", parent=self.profiles_tab)
        self.profiles_layout.addWidget(self.group_create)

        layout = QtWidgets.QGridLayout(self.group_create)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        self.spin_count = QtWidgets.QSpinBox(parent=self.group_create)
        self.spin_count.setRange(1, 999)
        self.spin_count.setValue(1)

        self.input_name = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_name.setPlaceholderText("Ví dụ: Acc")

        self.input_note = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_group = QtWidgets.QLineEdit(parent=self.group_create)

        self.input_profile_dir = QtWidgets.QLineEdit(parent=self.group_create)
        self.input_profile_dir.setText(str(DEFAULT_PROFILES_DIR))
        self.button_browse = QtWidgets.QPushButton("Chọn", parent=self.group_create)

        self.button_create = QtWidgets.QPushButton("Tạo", parent=self.group_create)
        self.button_reload = QtWidgets.QPushButton("Tải lại", parent=self.group_create)

        layout.addWidget(QtWidgets.QLabel("Số lượng"), 0, 0)
        layout.addWidget(self.spin_count, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Tiền tố tên"), 0, 2)
        layout.addWidget(self.input_name, 0, 3)
        layout.addWidget(QtWidgets.QLabel("Nhóm"), 0, 4)
        layout.addWidget(self.input_group, 0, 5)

        layout.addWidget(QtWidgets.QLabel("Ghi chú"), 1, 0)
        layout.addWidget(self.input_note, 1, 1, 1, 3)
        layout.addWidget(QtWidgets.QLabel("Thư mục hồ sơ"), 1, 4)
        layout.addWidget(self.input_profile_dir, 1, 5)
        layout.addWidget(self.button_browse, 1, 6)

        layout.addWidget(self.button_create, 0, 6)
        layout.addWidget(self.button_reload, 2, 6)

        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(5, 1)

    def setup_run_controls(self, controls):
        self.button_run_all = QtWidgets.QPushButton("Chạy", parent=self.header)
        self.button_run_all.setObjectName("PrimaryButton")
        self.button_stop = QtWidgets.QPushButton("Dừng", parent=self.header)
        self.button_stop.setObjectName("DangerButton")
        self.button_stop.setEnabled(False)
        controls.addWidget(self.button_run_all)
        controls.addWidget(self.button_stop)

    def setup_table(self):
        self.table = QtWidgets.QTableWidget(parent=self.profiles_tab)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Tên",
            "Ghi chú",
            "Nhóm",
            "Kênh YouTube",
            "Chế độ",
            "Trạng thái",
            "Mở",
            "Lưu",
            "Xóa",
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

    def channel_mode_label(self, channel_mode):
        return CHANNEL_MODE_LABELS.get((channel_mode or "shorts").strip().lower(), CHANNEL_MODE_LABELS["shorts"])

    def selected_channel_mode(self, combo):
        return combo.currentData() or "shorts"

    def status_label(self, status):
        return STATUS_LABELS.get(str(status or "Idle"), str(status or "Chờ"))

    def setup_settings_tab(self):
        self.settings_layout = QtWidgets.QVBoxLayout(self.settings_tab)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(8)

        self.settings_groups_layout = QtWidgets.QHBoxLayout()
        self.settings_groups_layout.setSpacing(8)

        self.settings_timing_group = QtWidgets.QGroupBox("Thời gian", parent=self.settings_tab)
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
            "Video dài hơn số phút này sẽ được cắt thành 3 phần bằng nhau."
        )
        self.input_short_pad_threshold = QtWidgets.QSpinBox(parent=self.settings_timing_group)
        self.input_short_pad_threshold.setRange(1, 3600)
        self.input_short_pad_threshold.setValue(55)
        self.input_short_pad_threshold.setSuffix(" giây")
        self.input_short_pad_threshold.setToolTip(
            "Video ngắn đạt ngưỡng này sẽ được kéo dài đến 61 giây."
        )
        self.input_daily_upload_limit = QtWidgets.QSpinBox(parent=self.settings_timing_group)
        self.input_daily_upload_limit.setRange(1, 999)
        self.input_daily_upload_limit.setValue(3)
        self.input_daily_upload_limit.setToolTip(
            "Số video tối đa được upload mỗi ngày cho từng tài khoản TikTok. Video cắt 3 phần sẽ tính là 3."
        )

        timing_layout.addWidget(QtWidgets.QLabel("Chu kỳ quét (giây)", parent=self.settings_timing_group), 0, 0)
        timing_layout.addWidget(self.input_poll_interval, 0, 1)
        self.split_threshold_label = QtWidgets.QLabel("Cắt video > (phút)", parent=self.settings_timing_group)
        timing_layout.addWidget(self.split_threshold_label, 1, 0)
        timing_layout.addWidget(self.input_split_threshold, 1, 1)
        self.short_pad_threshold_label = QtWidgets.QLabel("Kéo dài video ngắn >= (giây)", parent=self.settings_timing_group)
        timing_layout.addWidget(self.short_pad_threshold_label, 2, 0)
        timing_layout.addWidget(self.input_short_pad_threshold, 2, 1)
        self.daily_upload_limit_label = QtWidgets.QLabel("Giới hạn upload/ngày", parent=self.settings_timing_group)
        timing_layout.addWidget(self.daily_upload_limit_label, 3, 0)
        timing_layout.addWidget(self.input_daily_upload_limit, 3, 1)
        timing_layout.setColumnStretch(1, 1)

        self.settings_split_schedule_group = QtWidgets.QGroupBox("Lịch đăng phần cắt", parent=self.settings_tab)
        split_schedule_layout = QtWidgets.QGridLayout(self.settings_split_schedule_group)
        split_schedule_layout.setContentsMargins(8, 8, 8, 8)
        split_schedule_layout.setHorizontalSpacing(8)
        split_schedule_layout.setVerticalSpacing(6)

        self.input_split_schedule_enabled = QtWidgets.QCheckBox("Bật", parent=self.settings_split_schedule_group)
        self.input_split_schedule_gap = QtWidgets.QSpinBox(parent=self.settings_split_schedule_group)
        self.input_split_schedule_gap.setRange(1, 168)
        self.input_split_schedule_gap.setValue(3)
        self.input_split_schedule_gap.setSuffix(" giờ")
        self.input_split_schedule_gap.setToolTip("Khoảng cách giữa các phần video đã cắt.")
        split_schedule_layout.addWidget(self.input_split_schedule_enabled, 0, 0, 1, 2)
        split_schedule_layout.addWidget(QtWidgets.QLabel("Giãn cách", parent=self.settings_split_schedule_group), 1, 0)
        split_schedule_layout.addWidget(self.input_split_schedule_gap, 1, 1)
        split_schedule_layout.setColumnStretch(1, 1)

        self.settings_storage_group = QtWidgets.QGroupBox("Lưu trữ", parent=self.settings_tab)
        storage_layout = QtWidgets.QGridLayout(self.settings_storage_group)
        storage_layout.setContentsMargins(8, 8, 8, 8)
        storage_layout.setHorizontalSpacing(8)
        storage_layout.setVerticalSpacing(6)

        self.input_download_dir = QtWidgets.QLineEdit(parent=self.settings_storage_group)
        storage_layout.addWidget(QtWidgets.QLabel("Thư mục tải về", parent=self.settings_storage_group), 0, 0)
        storage_layout.addWidget(self.input_download_dir, 0, 1)
        storage_layout.setColumnStretch(1, 1)

        self.settings_telegram_group = QtWidgets.QGroupBox("Telegram", parent=self.settings_tab)
        telegram_layout = QtWidgets.QGridLayout(self.settings_telegram_group)
        telegram_layout.setContentsMargins(8, 8, 8, 8)
        telegram_layout.setHorizontalSpacing(8)
        telegram_layout.setVerticalSpacing(6)

        self.input_telegram_token = QtWidgets.QLineEdit(parent=self.settings_telegram_group)
        self.input_telegram_chat_id = QtWidgets.QLineEdit(parent=self.settings_telegram_group)
        self.button_check_updates = QtWidgets.QPushButton("Kiểm tra cập nhật", parent=self.settings_tab)
        self.button_save_settings = QtWidgets.QPushButton("Lưu cài đặt", parent=self.settings_tab)

        telegram_layout.addWidget(QtWidgets.QLabel("Token bot", parent=self.settings_telegram_group), 0, 0)
        telegram_layout.addWidget(self.input_telegram_token, 0, 1)
        telegram_layout.addWidget(QtWidgets.QLabel("ID chat", parent=self.settings_telegram_group), 1, 0)
        telegram_layout.addWidget(self.input_telegram_chat_id, 1, 1)
        telegram_layout.setColumnStretch(1, 1)

        self.settings_groups_layout.addWidget(self.settings_timing_group, 1)
        self.settings_groups_layout.addWidget(self.settings_split_schedule_group, 1)
        self.settings_groups_layout.addWidget(self.settings_storage_group, 2)
        self.settings_groups_layout.addWidget(self.settings_telegram_group, 2)

        save_layout = QtWidgets.QHBoxLayout()
        save_layout.addStretch(1)
        save_layout.addWidget(self.button_check_updates)
        save_layout.addWidget(self.button_save_settings)

        self.settings_layout.addLayout(self.settings_groups_layout)
        self.settings_layout.addLayout(save_layout)
        self.settings_layout.addStretch(1)

    def setup_logs_tab(self):
        layout = QtWidgets.QVBoxLayout(self.logs_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.button_refresh_logs = QtWidgets.QPushButton("Làm mới nhật ký", parent=self.logs_tab)
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
            QLabel#LogoLabel {
                background: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
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
        self.button_check_updates.clicked.connect(self.check_updates)
        self.button_refresh_logs.clicked.connect(self.refresh_logs)

    def choose_profiles_dir(self):
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục hồ sơ Chrome",
            self.input_profile_dir.text() or str(DEFAULT_PROFILES_DIR),
        )
        if selected:
            self.input_profile_dir.setText(selected)

    def create_profiles(self):
        profiles_dir = resolve_app_path(self.input_profile_dir.text(), DEFAULT_PROFILES_DIR)
        self.database.set_setting("profiles_dir", profiles_dir)
        profiles = create_chrome_profiles(
            data_path=PROFILES_PATH,
            profiles_dir=profiles_dir,
            count=self.spin_count.value(),
            name_prefix=self.input_name.text(),
            note=self.input_note.text(),
            group=self.input_group.text(),
        )
        self.profiles = profiles
        self.render_table()
        self.statusbar.showMessage(f"Đã tạo {self.spin_count.value()} hồ sơ Chrome", 5000)

    def reload_profiles(self):
        repair_profile_paths(PROFILES_PATH, resolve_app_path(self.input_profile_dir.text(), DEFAULT_PROFILES_DIR))
        self.profiles = load_profiles(PROFILES_PATH)
        self.render_table()
        self.statusbar.showMessage(f"Đã tải {len(self.profiles)} hồ sơ", 3000)

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
            for mode, label in CHANNEL_MODE_LABELS.items():
                mode_combo.addItem(label, mode)
            selected_mode = (profile.get("channel_mode") or "shorts").strip().lower()
            selected_index = mode_combo.findData(selected_mode)
            mode_combo.setCurrentIndex(max(0, selected_index))
            mode_combo.setMinimumWidth(compact_column_widths[4])
            self.apply_high_contrast_palette(mode_combo)
            self.table.setCellWidget(row, 4, mode_combo)

            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(self.status_label(profile.get("last_status", "Idle"))))

            button_open = QtWidgets.QPushButton("Mở", parent=self.table)
            button_open.setMinimumWidth(compact_column_widths[6])
            button_open.clicked.connect(lambda _, p=profile: self.open_profile(p))
            self.table.setCellWidget(row, 6, button_open)

            save_button = QtWidgets.QPushButton("Lưu", parent=self.table)
            save_button.setMinimumWidth(compact_column_widths[7])
            save_button.clicked.connect(
                lambda _, p=profile, note=note_input, group=group_input, mode=mode_combo: self.save_profile_row(
                    p,
                    note.text(),
                    group.text(),
                    p.get("channel_url", ""),
                    self.selected_channel_mode(mode),
                )
            )
            self.table.setCellWidget(row, 7, save_button)

            button_delete = QtWidgets.QPushButton("Xóa", parent=self.table)
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
            QtWidgets.QMessageBox.warning(self, "Chế độ kênh không hợp lệ", str(error))
            return
        self.reload_profiles()
        self.statusbar.showMessage("Đã lưu hồ sơ", 3000)

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
                    channel_mode=self.selected_channel_mode(mode_combo),
                )
            except ValueError as error:
                QtWidgets.QMessageBox.warning(self, "Chế độ kênh không hợp lệ", str(error))
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
        button.setText(urls[0] if urls else "Thêm URL kênh")
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
        badge.setText(f"{count} URL")
        layout.addWidget(button, 1)
        layout.addWidget(badge)
        return cell

    def create_channel_url_dialog(self, profile, channel_mode):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("URL kênh YouTube")
        dialog.resize(640, 360)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        editor = QtWidgets.QPlainTextEdit(parent=dialog)
        editor.setPlainText(profile.get("channel_url", ""))
        editor.setPlaceholderText("Dán mỗi dòng một URL kênh YouTube")
        layout.addWidget(editor, 1)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        save_button = QtWidgets.QPushButton("Lưu", parent=dialog)
        save_button.setObjectName("ChannelUrlDialogSaveButton")
        close_button = QtWidgets.QPushButton("Đóng", parent=dialog)
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
        channel_mode = self.selected_channel_mode(mode_combo) if mode_combo else profile.get("channel_mode", "shorts")
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
        try:
            short_pad_threshold = int(float(self.database.get_setting("short_pad_threshold_seconds", "55")))
        except ValueError:
            short_pad_threshold = 55
        self.input_short_pad_threshold.setValue(max(1, short_pad_threshold))
        try:
            daily_upload_limit = int(float(self.database.get_setting("daily_upload_limit_per_account", "3")))
        except ValueError:
            daily_upload_limit = 3
        self.input_daily_upload_limit.setValue(max(1, daily_upload_limit))
        self.input_split_schedule_enabled.setChecked(
            self.database.get_setting("split_schedule_enabled", "0") == "1"
        )
        try:
            split_schedule_gap = int(float(self.database.get_setting("split_schedule_gap_hours", "3")))
        except ValueError:
            split_schedule_gap = 3
        self.input_split_schedule_gap.setValue(max(1, split_schedule_gap))
        profiles_dir = resolve_app_path(self.database.get_setting("profiles_dir", str(DEFAULT_PROFILES_DIR)), DEFAULT_PROFILES_DIR)
        download_dir = resolve_app_path(self.database.get_setting("download_dir", str(DOWNLOADS_DIR)), DOWNLOADS_DIR)
        self.input_profile_dir.setText(str(profiles_dir))
        self.input_download_dir.setText(str(download_dir))
        self.input_telegram_token.setText(self.database.get_setting("telegram_bot_token", ""))
        self.input_telegram_chat_id.setText(self.database.get_setting("telegram_chat_id", ""))

    def save_settings(self):
        self.database.set_setting("poll_interval_seconds", self.input_poll_interval.value())
        self.database.set_setting("split_threshold_minutes", self.input_split_threshold.value())
        self.database.set_setting("short_pad_threshold_seconds", self.input_short_pad_threshold.value())
        self.database.set_setting("daily_upload_limit_per_account", self.input_daily_upload_limit.value())
        self.database.set_setting("split_schedule_enabled", "1" if self.input_split_schedule_enabled.isChecked() else "0")
        self.database.set_setting("split_schedule_gap_hours", self.input_split_schedule_gap.value())
        self.database.set_setting("profiles_dir", resolve_app_path(self.input_profile_dir.text(), DEFAULT_PROFILES_DIR))
        self.database.set_setting("download_dir", resolve_app_path(self.input_download_dir.text(), DOWNLOADS_DIR))
        self.database.set_setting("telegram_bot_token", self.input_telegram_token.text())
        self.database.set_setting("telegram_chat_id", self.input_telegram_chat_id.text())
        self.statusbar.showMessage("Đã lưu cài đặt", 3000)

    def check_updates(self):
        self.statusbar.showMessage("Đang kiểm tra cập nhật...", 3000)
        try:
            self.app_version = read_app_version(APP_VERSION)
            manager = VersionManager(UPDATE_REPO_URL, current_version=self.app_version)
            manager.show_update_dialog(parent=self)
            self.statusbar.showMessage("Đã kiểm tra cập nhật", 3000)
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "Kiểm tra cập nhật", f"Không thể kiểm tra cập nhật: {error}")
            self.statusbar.showMessage("Kiểm tra cập nhật lỗi", 3000)

    def refresh_logs(self):
        self._logs_refresh_pending = False
        logs = self.database.get_recent_logs(limit=60)
        lines = []
        for log in logs:
            created_at = str(log["created_at"])[11:19]
            profile = str(log["profile_id"] or "")
            profile_tail = profile[-6:] if profile else "-"
            job = log["job_id"] or "-"
            lines.append(f"{created_at} | {log['level']} | HS:{profile_tail} | CV:{job} | {log['message']}")
        self.logs_view.setPlainText("\n".join(lines))

    @QtCore.pyqtSlot()
    def schedule_refresh_logs(self):
        if self._logs_refresh_pending:
            return
        self._logs_refresh_pending = True
        QtCore.QTimer.singleShot(500, self.refresh_logs)

    @QtCore.pyqtSlot(str, str)
    def handle_worker_profile_status(self, _profile_id, _status):
        self.schedule_reload_profiles()

    @QtCore.pyqtSlot()
    def schedule_reload_profiles(self):
        if self._profiles_refresh_pending:
            return
        self._profiles_refresh_pending = True
        QtCore.QTimer.singleShot(800, self._reload_profiles_from_timer)

    @QtCore.pyqtSlot()
    def _reload_profiles_from_timer(self):
        self._profiles_refresh_pending = False
        self.reload_profiles()

    def confirm_action(self, title, message, locked_button):
        locked_button.setEnabled(False)
        reply = QtWidgets.QMessageBox.question(
            self,
            title,
            message,
            QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Ok:
            locked_button.setEnabled(True)
            return False
        return True

    def run_all_profiles(self):
        if self.worker_thread:
            return
        if not self.confirm_action("Xác nhận chạy", "Bắt đầu quét YouTube và đăng TikTok?", self.button_run_all):
            return
        self.save_settings()
        if not self.save_visible_channel_assignments():
            self.button_run_all.setEnabled(True)
            return
        self.worker = YoutubeToTikTokWorker(PROFILES_PATH, APP_DB_PATH)
        queued = QtCore.Qt.ConnectionType.QueuedConnection
        self.worker.log_created.connect(self.schedule_refresh_logs, queued)
        self.worker.profile_status.connect(self.handle_worker_profile_status, queued)
        self.worker.finished.connect(self.worker_finished, queued)
        self.worker_thread = threading.Thread(
            target=self.worker.run_forever,
            name="SmartTikTokWorker",
            daemon=True,
        )
        self.worker_thread.start()
        self.button_run_all.setEnabled(False)
        self.button_stop.setEnabled(True)
        self.statusbar.showMessage("Đang chạy", 3000)

    def stop_worker(self):
        if not self.worker:
            return
        if not self.confirm_action("Xác nhận dừng", "Dừng tiến trình đang chạy?", self.button_stop):
            return
        if self.worker:
            self.worker.stop()
        self.button_stop.setEnabled(False)
        self.statusbar.showMessage("Đang dừng", 3000)

    @QtCore.pyqtSlot()
    def worker_finished(self):
        self.worker_thread = None
        self.worker = None
        self.button_run_all.setEnabled(True)
        self.button_stop.setEnabled(False)
        self.reload_profiles()
        self.refresh_logs()
        self.statusbar.showMessage("Đã dừng", 3000)

    def open_profile(self, profile):
        profile_id = profile.get("id")
        if profile_id in self.open_browsers:
            self.statusbar.showMessage("Hồ sơ đang mở", 4000)
            return

        profile_path = Path(profile.get("profile_path", ""))
        profile_path.mkdir(parents=True, exist_ok=True)
        try:
            from Controller.BrowserController import ChromeProfileBrowser

            browser = ChromeProfileBrowser(profile_path)
            browser.open("https://www.google.com")
            self.open_browsers[profile_id] = browser
            self.statusbar.showMessage(f"Đã mở hồ sơ: {profile.get('name', '')}", 5000)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Không thể mở Chrome", str(error))

    def delete_profile(self, profile):
        profile_id = profile.get("id")
        reply = QtWidgets.QMessageBox.question(
            self,
            "Xóa hồ sơ",
            f"Xóa hồ sơ '{profile.get('name', '')}' và thư mục dữ liệu?",
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
            self.statusbar.showMessage("Đã xóa hồ sơ", 5000)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Không thể xóa hồ sơ", str(error))

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        if self.worker_thread and self.worker_thread.is_alive():
            self.statusbar.showMessage("Đang dừng trước khi đóng", 3000)
            self.worker_thread.join(10)
            if self.worker_thread.is_alive():
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

