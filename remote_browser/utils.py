#####################################################################################
##   _______ _       _____  ____  ______ _________          __     _____  ______   ##
##  |__   __| |     / ____|/ __ \|  ____|__   __\ \        / /\   |  __ \|  ____|  ##
##     | |  | |    | (___ | |  | | |__     | |   \ \  /\  / /  \  | |__) | |__     ##
##     | |  | |     \___ \| |  | |  __|    | |    \ \/  \/ / /\ \ |  _  /|  __|    ##
##     | |  | |____ ____) | |__| | |       | |     \  /\  / ____ \| | \ \| |____   ##
##     |_|  |______|_____/ \____/|_|       |_|      \/  \/_/    \_\_|  \_\______|  ##
##                                                                                 ##
#####################################################################################

## CDPWebdriver BUIDER BY LTT Dev - TLSOFTWARE - ZALO: 0358768395

################## CONTACT ###################
##      __AUTHOR__    : LTT Dev             ##
##      __TELEGRAM__  : @ltts_dev           ##
##      __ZALO__      : 0358768395          ##
##      __FACEBOOK__  : TaiLe.TLSoftware    ##
##############################################


import socket
import time
import math
import json
import random
import os

from urllib.request import urlopen
from urllib.error import URLError
from http.client import HTTPException

from .exceptions import BrowserError

def module_path():
    return os.path.dirname(__file__)

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def get_ws_endpoint(url) -> str:
    url = url + '/json/version'
    timeout = time.time() + 30
    while (True):
        if time.time() > timeout:
            raise BrowserError('Browser closed unexpectedly:\n')
        try:
            with urlopen(url) as f:
                data = json.loads(f.read().decode())
            break
        except (URLError, HTTPException):
            pass
        time.sleep(0.1)

    return data['webSocketDebuggerUrl']


def get_point(box_model, border_padding: int = 5, key='content'):
    avoid_ratio = 0.2
    points = box_model[key]
    left = min(points[:, 0])
    right = max(points[:, 0])
    top = min(points[:, 1])
    bottom = max(points[:, 1])

    # Tính vùng an toàn, trừ border_padding
    left += border_padding
    right -= border_padding
    top += border_padding
    bottom -= border_padding

    # Điều chỉnh vùng an toàn, tránh khu vực bên phải
    safe_right = right - avoid_ratio * (right - left)  # Trừ đi phần dành cho icon

    # Kiểm tra kích thước hợp lệ
    if left >= safe_right or top >= bottom:
        raise ValueError("Box quá nhỏ để tạo tọa độ với border_padding được chỉ định.")

    # Tính trung tâm và độ lệch chuẩn
    center_x = (left + safe_right) / 2
    center_y = (top + bottom) / 2
    std_dev_x = (safe_right - left) / 6
    std_dev_y = (bottom - top) / 6

    # Sinh giá trị x, y gần trung tâm nhưng tránh vùng icon
    for _ in range(100):  # Thử tối đa 100 lần để đảm bảo tìm được điểm hợp lệ
        x = random.gauss(center_x, std_dev_x)
        y = random.gauss(center_y, std_dev_y)

        # Đảm bảo x, y nằm trong phạm vi hợp lệ
        if left <= x <= safe_right and top <= y <= bottom:
            return math.floor(x), math.floor(y)

    # Nếu không tìm được giá trị sau nhiều lần thử
    raise ValueError("Không thể tạo tọa độ hợp lệ gần trung tâm và tránh icon.")


def convert_json_values(data):
    if data is None:
        return {}
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return data
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                result[key] = parsed_value
            except json.JSONDecodeError:
                result[key] = value
        else:
            result[key] = value
    return result

def find_shadow_host(node, shadow_type = 'all'):
    shadows = []

    if 'shadowRoots' in node:
        for shadow in node['shadowRoots']:
            if shadow['shadowRootType'] == shadow_type.lower() or shadow_type.lower() == 'all':
                shadows.append(shadow)

    if 'children' in node and isinstance(node['children'], list):
        for child in node['children']:
            found = find_shadow_host(child, shadow_type.lower())
            if found:
                shadows.extend(found)

    return shadows

SCRIPT_CREATE_MOUSE = '''
    let debounceTimer;

    function setCursorLocation(cursor) {
        const last_x = localStorage.getItem('lts_last_x');
        const last_y = localStorage.getItem('lts_last_y');
        if (last_x && last_y) {
            cursor.style.left = `${parseFloat(last_x) - scrollX - 3}px`;
            cursor.style.top = `${parseFloat(last_y) - scrollY - 3}px`;
        } else {
            cursor.style.left = "0px";
            cursor.style.top = "0px";
        }
    }

    function createCustomCursor() {
        let cursor = document.querySelector('#LTS-Cursor');
        if (!cursor) {
            const svgNS = "http://www.w3.org/2000/svg";
            const svg = document.createElementNS(svgNS, "svg");
            svg.setAttribute("width", "40");
            svg.setAttribute("height", "40");
            svg.setAttribute("viewBox", "-2.4 -2.4 28.80 28.80");
            svg.style.position = "fixed";
            svg.style.pointerEvents = "none";
            svg.style.transition = "transform 0.1s ease-out, opacity 0.1s ease-out";
            svg.style.zIndex = "999999";
            svg.id = "LTS-Cursor";

            const path = document.createElementNS(svgNS, "path");
            path.setAttribute("d", "M4 4l7.07 17 2.51-7.39L21 11.07z");
            path.setAttribute("fill", "white");
            path.setAttribute("stroke", "black");
            path.setAttribute("stroke-width", "1.368");
            path.setAttribute("stroke-linecap", "round");
            path.setAttribute("stroke-linejoin", "round");

            svg.appendChild(path);
            document.body.appendChild(svg);
            document.body.style.cursor = "none";

            setCursorLocation(svg);
            document.addEventListener("mousemove", (event) => {
                svg.style.left = `${event.clientX - 3}px`;
                svg.style.top = `${event.clientY - 3}px`;

                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    localStorage.setItem('lts_last_x', event.clientX);
                    localStorage.setItem('lts_last_y', event.clientY);
                    console.log("Position saved:", event.clientX, event.clientY);
                }, 100);
            });
            
            document.addEventListener("mousedown", (event) => {
                if (event.button === 0) {
                    svg.style.transform = "scale(1.3)";
                } else if (event.button === 2) {
                    svg.style.transform = "rotate(45deg)";
                }
            });

            document.addEventListener("mouseup", () => {
                svg.style.transform = "scale(1) rotate(0deg)";
            });

            document.addEventListener("mouseleave", () => {
                svg.style.opacity = "1";
            });
        } else {
            setCursorLocation(cursor);
        }
    };

'''

SCRIPT_SHOW_MOUSE = f'{SCRIPT_CREATE_MOUSE}\ncreateCustomCursor()'

SCRIPT_PREV_LOAD_SHOW_MOUSE = f'''
if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", () => {{
        {SCRIPT_CREATE_MOUSE}
        createCustomCursor();
    }});
}} else {{
    createCustomCursor();
}}
'''

SCRIPT_CHECK_VISIBLE = '''
    const element = arguments[0];
    const container = element.parentElement;

    const element_rect = element.getBoundingClientRect();
    const container_rect = container.getBoundingClientRect();

    const isVisible = (
        element_rect.top >= container_rect.top &&
        element_rect.left >= container_rect.left &&
        element_rect.bottom <= container_rect.bottom &&
        element_rect.right <= container_rect.right &&
        element_rect.x <= container_rect.height &&
        element_rect.y <= container_rect.width
    )
    if (!isVisible) {
        element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }
    return !isVisible;
'''
