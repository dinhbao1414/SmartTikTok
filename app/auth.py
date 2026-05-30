import hashlib
import os
import platform
import subprocess
import uuid
from datetime import datetime, timedelta

import requests
from PyQt6 import QtCore, QtWidgets


LICENSE_URL = "https://scoder.vn/api/check_username_by_product/"
LICENSE_TOKEN = os.environ.get("YTT_LICENSE_TOKEN", "8dae3c780478f98fcba82088660d3f46a7059349")
PRODUCT_NAME = "SmartTikTok"


def _run_command(command):
    try:
        return subprocess.check_output(
            command,
            shell=True,
            timeout=10,
            stderr=subprocess.DEVNULL,
        ).decode(errors="ignore").strip()
    except Exception:
        return ""


def get_mainboard_uuid():
    value = _run_command("wmic csproduct get uuid")
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[1]

    return _run_command(
        "powershell -NoProfile -Command "
        "\"Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID\""
    )


def get_cpu_id():
    value = _run_command("wmic cpu get Name,ProcessorId")
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) >= 2:
        parts = lines[1].split()
        if parts:
            return parts[-1]

    value = _run_command(
        "powershell -NoProfile -Command "
        "\"Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty ProcessorId\""
    )
    return value.strip()


def get_device_fingerprint():
    raw = "|".join([
        get_mainboard_uuid(),
        get_cpu_id(),
        platform.node(),
        str(uuid.getnode()),
    ])
    return str(int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16) % 10**8)


def default_machine_id():
    try:
        import machineid

        return str(machineid.hashed_id())
    except Exception:
        raw = f"{platform.node()}|{uuid.getnode()}|{get_mainboard_uuid()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class Auth:
    def __init__(
        self,
        job_name=PRODUCT_NAME,
        machine_id_provider=default_machine_id,
        fingerprint_provider=get_device_fingerprint,
    ):
        self.job_name = job_name
        job_hash = str(int(hashlib.sha256(self.job_name.encode("utf-8")).hexdigest(), 16) % 10**8)
        self.machine_id = f"{machine_id_provider()}{job_hash}{fingerprint_provider()}"
        self.payload = {"machine_id": self.machine_id, "job_name": self.job_name}


def _license_parts(auth, username):
    month = datetime.now().month
    day = datetime.now().day
    number_by_day = int(month) * int(day)
    current_time = datetime.now().strftime("%Y-%m-%d")
    username_secret = str(len(username) * number_by_day)

    return {
        "product_name": str(int(hashlib.sha256(auth.job_name.encode("utf-8")).hexdigest(), 16)),
        "device_key": str(int(hashlib.sha256(auth.machine_id.encode("utf-8")).hexdigest(), 16) % 10**20),
        "current_time": str(int(hashlib.sha256(current_time.encode("utf-8")).hexdigest(), 32) * number_by_day),
        "username_secret": str(int(hashlib.sha256(username_secret.encode("utf-8")).hexdigest(), 16) * number_by_day),
    }


def _license_response(auth, request_get=requests.get, timeout=30):
    headers = {"Authorization": f"Token {LICENSE_TOKEN}"}
    response = request_get(
        LICENSE_URL,
        headers=headers,
        data={"device_key": auth.machine_id, "product_name": auth.job_name},
        timeout=timeout,
    )
    return response.json()


def check_active_key(auth=None, request_get=requests.get):
    try:
        auth = auth or Auth()
        response = _license_response(auth, request_get=request_get)
        username = response.get("user_name")
        data = response.get("data", "")
        if not username or not data:
            return False

        parts = _license_parts(auth, username)
        return all(value in data for value in parts.values()) and _decode_days_remaining(data, parts) >= 0
    except Exception:
        return False


def _decode_days_remaining(data, parts):
    encoded_days = data
    for value in parts.values():
        encoded_days = encoded_days.replace(value, "")

    for days in range(0, 3600):
        hashed_value = str(int(hashlib.sha256(str(days).encode("utf-8")).hexdigest(), 32) % 10**8)
        if hashed_value == encoded_days:
            return days
    return -1


def get_expiry_info(auth=None, request_get=requests.get):
    fallback = {
        "success": False,
        "days_remaining": 0,
        "expiry_date": None,
        "expiry_date_str": "Khong xac dinh",
    }
    try:
        auth = auth or Auth()
        response = _license_response(auth, request_get=request_get, timeout=180)
        username = response.get("user_name")
        data = response.get("data", "")
        if not username or not data:
            return fallback

        parts = _license_parts(auth, username)
        if not all(value in data for value in parts.values()):
            return fallback

        days_remaining = _decode_days_remaining(data, parts)
        if days_remaining < 0:
            return fallback

        expiry_date = datetime.now() + timedelta(days=days_remaining)
        return {
            "success": True,
            "days_remaining": days_remaining,
            "expiry_date": expiry_date,
            "expiry_date_str": expiry_date.strftime("%d/%m/%Y"),
        }
    except Exception:
        return fallback


class LoginForm(QtWidgets.QWidget):
    def __init__(self, auth=None):
        super().__init__()
        self.authentication = auth or Auth()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Đăng Ký thiết bị SmartTiktok")
        self.resize(460, 240)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Đăng ký thiết bị")
        title.setObjectName("AuthTitle")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        instruction = QtWidgets.QLabel("Gửi key này cho người quản lý để kích hoạt phần mềm.")
        instruction.setWordWrap(True)
        instruction.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.key_input = QtWidgets.QLineEdit(self.authentication.machine_id)
        self.key_input.setReadOnly(True)

        self.copy_button = QtWidgets.QPushButton("Copy key")
        self.copy_button.clicked.connect(self.copy_key)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(instruction)
        layout.addWidget(self.key_input)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.status_label)

        self.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                color: #111827;
                font-family: "Segoe UI", Arial;
                font-size: 13px;
            }
            QLabel#AuthTitle {
                font-size: 18px;
                font-weight: 700;
            }
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 7px;
            }
            QPushButton {
                background: #111827;
                color: #FFFFFF;
                border: 1px solid #111827;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 650;
            }
        """)

    def copy_key(self):
        QtWidgets.QApplication.clipboard().setText(self.authentication.machine_id)
        self.status_label.setText("Da copy key")
        QtCore.QTimer.singleShot(3000, lambda: self.status_label.setText(""))
