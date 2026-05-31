import os
import sys
import requests
import zipfile
import shutil
import subprocess
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.paths import APP_STATE_DIR
from app.version import DEFAULT_APP_VERSION, read_app_version, write_app_version

# Import packaging.version for proper semantic version comparison
try:
    from packaging import version
    PACKAGING_AVAILABLE = True
except ImportError:
    PACKAGING_AVAILABLE = False

class UpdateWorker(QThread):
    """Worker thread for downloading and updating files"""
    progress_updated = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    update_finished = pyqtSignal(bool, str)
    
    def __init__(self, repo_url, download_url, current_dir):
        super().__init__()
        self.repo_url = repo_url
        self.download_url = download_url
        self.current_dir = current_dir
    
    def run(self):
        try:
            self.progress_updated.emit("Đang tải xuống phiên bản mới...")
            self.progress_percentage.emit(0)
            
            # Download the file
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # Xác định tên file dựa trên URL
            if self.download_url.endswith('.rar'):
                download_path = os.path.join(self.current_dir, "SmartTikTok_Update.rar")
            else:
                download_path = os.path.join(self.current_dir, "SmartTikTok_Update.zip")
                
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Calculate and emit progress percentage
                    if total_size > 0:
                        percentage = int((downloaded_size / total_size) * 100)  # 100% for download only
                        self.progress_percentage.emit(percentage)
                        self.progress_updated.emit(f"Đang tải xuống... {percentage}%")
            
            self.progress_percentage.emit(100)
            self.progress_updated.emit("Tải xuống hoàn tất! Đang chuẩn bị cập nhật...")
            
            # Tạo script update.bat để giải nén ngoài tiến trình ứng dụng
            bat_path = os.path.join(self.current_dir, "update.bat")
            zip_name = os.path.basename(download_path)
            
            # Kịch bản bat: chờ 3 giây -> giải nén đè -> chạy lại app -> xoá file zip và bat
            bat_content = f"""@echo off
chcp 65001 > nul
echo Dang cho ung dung dong lai...
timeout /t 3 /nobreak > nul

echo Dang giai nen ban cap nhat...
tar -xf "{zip_name}" 

echo Giai nen hoan tat! Khoi dong lai SmartTikTok...
if exist SmartTikTok.exe (
    start "" "SmartTikTok.exe"
) else (
    start "" "launcher.exe"
)

echo Dang don dep...
del "{zip_name}"
del "%~f0"
"""
            with open(bat_path, 'w', encoding='utf-8') as bat_file:
                bat_file.write(bat_content)
            
            # Phát tín hiệu hoàn tất, và đẩy thông báo cài đặt tự động
            self.update_finished.emit(True, bat_path)
            
        except Exception as e:
            error_msg = str(e)
            if "Permission denied" in error_msg or "PermissionError" in error_msg:
                error_msg = "Lỗi quyền truy cập: Vui lòng kiểm tra quyền ghi file trong thư mục hiện tại."
            self.update_finished.emit(False, f"Lỗi tải xuống: {error_msg}")

class UpdateDialog(QDialog):
    """Dialog hiển thị thông tin cập nhật"""
    def __init__(self, current_version, latest_version, release_notes, repo_url):
        super().__init__()
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_notes = release_notes
        self.repo_url = repo_url
        self.update_worker = None
        self.should_restart = False
        self.bat_path = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🔄 Cập nhật phiên bản mới")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("🎉 Có phiên bản mới!")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c5aa0;
                margin-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Version info
        version_info = QLabel(f"Phiên bản hiện tại: {self.current_version}\nPhiên bản mới: {self.latest_version}")
        version_info.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #495057;
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }
        """)
        layout.addWidget(version_info)
        
        # Release notes
        notes_label = QLabel("📝 Nội dung cập nhật:")
        notes_label.setStyleSheet("font-weight: bold; color: #495057;")
        layout.addWidget(notes_label)
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.release_notes)
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(150)
        self.notes_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
            }
        """)
        layout.addWidget(self.notes_text)
        
        # Progress label (initially hidden)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                text-align: center;
            }
        """)
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                color: #495057;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.update_button = QPushButton("🔄 Cài đặt và Khởi động lại")
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.update_button.clicked.connect(self.start_update)
        
        button_layout.addWidget(self.update_button)
        layout.addLayout(button_layout)
    
    def start_update(self):
        """Bắt đầu quá trình tải bản cập nhật"""
        self.update_button.setEnabled(False)
        self.progress_label.show()
        self.progress_bar.show()
        
        # Get download URL for SmartTikTok from latest release
        download_url = self.get_rar_download_url()
        if not download_url:
            QMessageBox.critical(self, "Lỗi", "Không thể tìm thấy file bản cập nhật (.zip/.rar) trong release mới nhất.")
            self.update_button.setEnabled(True)
            self.progress_label.hide()
            self.progress_bar.hide()
            return
            
        current_dir = str(APP_STATE_DIR)
        
        self.update_worker = UpdateWorker(self.repo_url, download_url, current_dir)
        self.update_worker.progress_updated.connect(self.update_progress)
        self.update_worker.progress_percentage.connect(self.update_progress_bar)
        self.update_worker.update_finished.connect(self.on_update_finished)
        self.update_worker.start()
    
    def update_progress(self, message):
        """Cập nhật tiến trình"""
        self.progress_label.setText(message)
    
    def update_progress_bar(self, percentage):
        """Cập nhật thanh tiến trình"""
        self.progress_bar.setValue(percentage)
    
    def get_rar_download_url(self):
        """Lấy URL download của file cập nhật từ GitHub releases"""
        try:
            api_url = self.repo_url.replace('github.com', 'api.github.com/repos')
            response = requests.get(f"{api_url}/releases", timeout=10)
            if response.status_code == 200:
                releases = response.json()
                if releases:
                    latest_release = releases[0]
                    for asset in latest_release.get('assets', []):
                        if asset['name'].endswith('.zip') or asset['name'].endswith('.rar'):
                            return asset['browser_download_url']
            return None
        except Exception as e:
            print(f"Lỗi khi lấy URL download: {e}")
            return None
    
    def on_update_finished(self, success, result_data):
        """Xử lý khi cập nhật hoàn tất"""
        if success:
            self.bat_path = result_data
            self.update_button.setText("Đang khởi động lại...")
            self.should_restart = True
            
            # Chạy file BAT ẩn dứoi nền và đóng App
            try:
                write_app_version(self.latest_version)
               
                subprocess.Popen(self.bat_path, cwd=os.getcwd(), shell=True)
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi cập nhật", f"Không thể tự động áp dụng bản vá: {e}\nFile cập nhật đã nằm sẵn trong thư mục ứng dụng.")
        else:
            QMessageBox.critical(self, "Lỗi cập nhật", result_data)
            self.update_button.setEnabled(True)
            self.progress_label.hide()
            self.progress_bar.hide()
            self.update_button.setText("🔄 Thử lại")

class VersionManager:
    """Quản lý phiên bản và cập nhật"""
    
    def __init__(self, repo_url, current_version=DEFAULT_APP_VERSION):
        self.repo_url = repo_url.rstrip('/')
        self.current_version = current_version
        self.api_url = self.repo_url.replace('github.com', 'api.github.com/repos')
    
    def get_current_version(self):
        """Lấy phiên bản hiện tại từ file version.json hoặc config"""
        try:
            return read_app_version(default=self.current_version)
        except:
            pass
        return self.current_version
    
    def get_latest_version_info(self):
        """Lấy thông tin phiên bản mới nhất từ GitHub"""
        try:
            # Try to get all releases first
            response = requests.get(f"{self.api_url}/releases", timeout=10)
            if response.status_code == 200:
                releases = response.json()
                if releases:  # If there are releases
                    # Get the first release (most recent)
                    latest_release = releases[0]
                    return {
                        'version': latest_release['tag_name'].lstrip('v'),
                        'notes': latest_release.get('body', 'Không có mô tả'),
                        'published_at': latest_release['published_at']
                    }
            
            # If no releases, get latest commit info
            response = requests.get(f"{self.api_url}/commits/main", timeout=10)
            if response.status_code == 200:
                data = response.json()
                commit_date = data['commit']['committer']['date']
                commit_message = data['commit']['message']
                commit_sha = data['sha'][:7]
                
                return {
                    'version': f"main-{commit_sha}",
                    'notes': f"Latest commit: {commit_message}",
                    'published_at': commit_date
                }
                
        except Exception as e:
            print(f"Lỗi khi kiểm tra phiên bản: {e}")
            return None
    
    def check_for_updates(self):
        """Kiểm tra có phiên bản mới không"""
        current = self.get_current_version()
        latest_info = self.get_latest_version_info()
        
        if not latest_info:
            return False, None, None, None
        
        latest = latest_info['version']
        
        # Improved version comparison using packaging.version for semantic versioning
        try:
            if PACKAGING_AVAILABLE:
                # Use semantic version comparison
                current_version = version.parse(current)
                latest_version = version.parse(latest)
                
                # Check if latest version is actually newer than current
                if latest_version > current_version:
                    print(f"Update available: {current} -> {latest}")
                    return True, current, latest, latest_info['notes']
                else:
                    print(f"Current version {current} is up to date (latest: {latest})")
                    return False, current, latest, None
            else:
                # Fallback to simple string comparison
                if latest != current:
                    print(f"Version difference detected: {current} vs {latest}")
                    return True, current, latest, latest_info['notes']
                else:
                    print(f"Versions match: {current}")
                    return False, current, latest, None
                    
        except Exception as e:
            print(f"Error comparing versions: {e}")
            # Fallback to simple string comparison
            if latest != current:
                return True, current, latest, latest_info['notes']
            return False, current, latest, None
    
    def show_update_dialog(self, parent=None):
        """Hiển thị dialog cập nhật nếu có phiên bản mới"""
        has_update, current, latest, notes = self.check_for_updates()
        
        if has_update:
            dialog = UpdateDialog(current, latest, notes, self.repo_url)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted and dialog.should_restart:
                # Restart the application
                self.restart_application()
                return True
        
        return False
    
    def restart_application(self):
        """Khởi động lại ứng dụng"""
        try:
            latest_info = self.get_latest_version_info()
            if latest_info:
                write_app_version(latest_info['version'])
            
            # Tìm file chính để restart - ưu tiên file exe
            python = sys.executable  # Định nghĩa python executable
            main_file = None
            command = None
            current_dir = str(APP_STATE_DIR)
            
            # Kiểm tra file exe trước
            if os.path.exists(os.path.join(current_dir, "SmartTikTok.exe")):
                main_file = os.path.join(current_dir, "SmartTikTok.exe")
                command = [main_file]
            elif os.path.exists(os.path.join(current_dir, "launcher.exe")):
                main_file = os.path.join(current_dir, "launcher.exe")
                command = [main_file]
            # Nếu không có exe, dùng file Python
            elif os.path.exists(os.path.join(current_dir, "ui.py")):
                main_file = os.path.join(current_dir, "ui.py")
                command = [python, main_file]
            elif os.path.exists(os.path.join(current_dir, "launcher.py")):
                main_file = os.path.join(current_dir, "launcher.py")
                command = [python, main_file]
            elif len(sys.argv) > 0 and os.path.exists(sys.argv[0]):
                main_file = sys.argv[0]
                if main_file.endswith('.exe'):
                    command = [main_file]
                else:
                    command = [python, main_file]
            
            if command:
                # Sử dụng subprocess để tránh lỗi path
                subprocess.Popen(command, cwd=current_dir)
                # Đóng ứng dụng hiện tại
                sys.exit(0)
            else:
                # Fallback to original method - python đã được định nghĩa ở trên
                os.execl(python, python, *sys.argv)
        except Exception as e:
            print(f"Lỗi khi khởi động lại: {e}")
            QMessageBox.information(None, "Cập nhật hoàn tất", 
                                   "Cập nhật thành công! Vui lòng khởi động lại ứng dụng thủ công.")
