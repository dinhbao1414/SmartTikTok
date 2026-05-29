#####################################################################################
##   _______ _       _____  ____  ______ _________          __     _____  ______   ##
##  |__   __| |     / ____|/ __ \|  ____|__   __\ \        / /\   |  __ \|  ____|  ##
##     | |  | |    | (___ | |  | | |__     | |   \ \  /\  / /  \  | |__) | |__     ##
##     | |  | |     \___ \| |  | |  __|    | |    \ \/  \/ / /\ \ |  _  /|  __|    ##
##     | |  | |____ ____) | |__| | |       | |     \  /\  / ____ \| | \ \| |____   ##
##     |_|  |______|_____/ \____/|_|       |_|      \/  \/_/    \_\_|  \_\______|  ##
##                                                                                 ##
#####################################################################################

## Remote Browser Module BUIDER BY LTT Dev - TLSOFTWARE - ZALO: 0358768395

################## CONTACT ###################
##      __AUTHOR__    : LTT Dev             ##
##      __TELEGRAM__  : @ltts_dev           ##
##      __ZALO__      : 0358768395          ##
##      __FACEBOOK__  : TaiLe.TLSoftware    ##
##############################################

import asyncio
import time
import random
import math
import uuid

from typing import List, Dict, Union, Tuple
from pyee import EventEmitter

from ..utils import convert_json_values, SCRIPT_PREV_LOAD_SHOW_MOUSE
from ..type.browser_support import By
from ..type.key import KEY_MAPPING
from ..cdp.connection import CDPConnection
from ..exceptions import CDPException, SwitchWindowError
from ..type.browser_support import By
from ..listener import lister_event
from .webelement import WebElement

class TargetInfo:
    def __init__(self, resp: dict) -> None:
        self.resp = resp
        self._id = self.process_data('targetId')
        self._type = self.process_data('type')
        self._url = self.process_data('url')
        self._title = self.process_data('title')
        self._attached = self.process_data('attached')
        self._can_access_opener = self.process_data('canAccessOpener')
        self._browser_context = self.process_data('browserContextId')
    
    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        return self._title

    @property
    def attached(self):
        return self._attached

    @property
    def can_access_opener(self):
        return self._can_access_opener

    @property
    def browser_context(self):
        return self._browser_context
    
    def process_data(self, key:str):
        return self.resp.get(key, None)
    
class Target(EventEmitter):
    def __init__(self, host: str, target_id: str, is_frame: bool = False, loop: Union[asyncio.AbstractEventLoop, None] = None) -> None:
        super().__init__()
        self.targets = {}
        self._connections = {}
        self._id = target_id
        self._host = host
        self._ws = None
        self._loop = loop
        self._alert = None
        self._x, self._y = 0, 0
        self._dom_element = None
        self._current_sessionId = None
        self._is_frame = is_frame
        self.__uuid_session__ = str(uuid.uuid4())
        self._net_load = False
        self._is_shadow_root = False
        lister_event.on(f'cdp_event_{self.__uuid_session__}', self.event_handler)
        self.on('Network.loadingFailed', lambda e: self._loop.create_task(self.load_while(e)))
        self.on('Page.screencastFrame', lambda e: self._loop.create_task(self.screencap_handler(e)))
        self._loop.run_until_complete(self._init())
        
    @property
    def current_sessionId(self):
        return self._current_sessionId
    
    @current_sessionId.setter
    def current_sessionId(self, sessionId: str):
        self._current_sessionId = sessionId
        
    async def load_while(self, e):
        error_type = [
            'net::ERR_TUNNEL_CONNECTION_FAILED',
            'net::ERR_ABORTED'
        ]
        if self._net_load:
            return
        if e['type'] == "Document" and e['errorText'] in error_type:
            self._net_load = True
            await asyncio.sleep(10)
            await self.refresh()
            self._net_load = False
        
    def event_handler(self, data):
        if "method" in data:
            self.emit(data["method"], data.get("params", {}))
        
    async def _init(self):
        if not self._ws:
            self._ws = CDPConnection(f'ws://{self._host}/devtools/page/{self._id}', self._loop, self.__uuid_session__, self)
            await self._ws.connect()
            await self._ws.send("Page.enable", {})
            override_js = """
                window.alert = function(message) {
                    console.log("Intercepted alert:", message);
                };

                window.confirm = function(message) {
                    console.log("Intercepted confirm:", message);
                    return true;  // Luôn chọn "OK"
                };

                window.prompt = function(message, defaultText) {
                    console.log("Intercepted prompt:", message);
                    return defaultText || "";  // Trả về giá trị mặc định
                };
            """
            await self._ws.send('Page.addScriptToEvaluateOnNewDocument', {
                'source': SCRIPT_PREV_LOAD_SHOW_MOUSE,
            })
            await self._ws.send('Page.addScriptToEvaluateOnNewDocument', {
                'source': override_js,
            })
            self._ws.on('Page.javascriptDialogOpening', lambda event: self._loop.create_task(self.alert_set_event(event)))
            await self.send_cdp("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": self._x,
                "y": self._y,
            })
            # await self._ws.send('Log.enable')
            # await self._ws.send('HeapProfiler.enable')
            # await self.send_cdp('Network.enable')
            await self.send_cdp('Runtime.enable')
    
    async def inject_onload_javascript(self, content: str):
        if not self._ws:
            await self._init()
        return await self._ws.send('Page.addScriptToEvaluateOnNewDocument', {
            'source': content,
        })
        
    async def alert_set_event(self, event):
        # print(f"Dialog open: {event}")
        await self.send_cdp("Page.handleJavaScriptDialog", {
                "accept": True,
                "promptText": ""
            }
        )
        
    async def send_cdp(self, method: str, params: dict = {}, timeout:int = 5):
        if not self._ws:
            await self._init()
        # print(await self._ws.send('Page.addScriptToEvaluateOnNewDocument', {'source': """
        #     document.addEventListener("DOMContentLoaded", function() {
        #         var lts_name_element = "LTS_ELEMENT_CURSOR";
            
        #         var lts_cursor = document.getElementById(lts_name_element);
        #         console.log(lts_name_element)
        #     })
        # """}))
        return await self._ws.send(method, params, self.current_sessionId, timeout)
    
    async def _wait_for(self, event_name: str, timeout: int = 15):
        if not self._ws:
            await self._init()
        return await self._ws.wait_for(event_name, timeout)
        
        
    @property
    def id(self):
        return self._id

    async def info(self):
        for _ in range(3):
            try:
                resp = await self.send_cdp("Target.getTargetInfo")
                break
            except:
                await asyncio.sleep(0.5)
        return TargetInfo(resp['result']['targetInfo'])
    
    @property
    async def current_url(self):
        info = await self.info()
        return info.url

    @property
    async def title(self):
        info = await self.info()
        return info.title
    
    @property
    async def page_source(self):
        await asyncio.sleep(1)
        for _ in range(5):
            elem = await self._dom_element_
            source = await elem.source
            if source:
                return source
            await asyncio.sleep(0.2)
    
    def find_shadow_host(self, node, shadow_type = 'all'):
        shadows = []

        if 'shadowRoots' in node:
            for shadow in node['shadowRoots']:
                if shadow['shadowRootType'] == shadow_type or shadow_type == 'all':
                    shadows.append(shadow)

        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                found = self.find_shadow_host(child, shadow_type)
                if found:
                    shadows.extend(found)

        return shadows
    
    @property
    async def _dom_element_(self) -> WebElement:
        if not self._is_frame:
            frame = await self.base_frame
            self._id = frame.get("id")

        resp = await self.send_cdp('DOM.getDocument', {
            'depth': -1,
            'targetId': self._id
        })
        root_node = resp.get('result').get("root", {})
            
        node_id = root_node.get("nodeId")
        backend_node_id = root_node.get('backendNodeId')
        if not node_id:
            raise RuntimeError("Không lấy được nodeId từ DOM.getDocument.")

        self._dom_element = WebElement(
            self,
            frame_id=self._id,
            node_id=node_id,
            backend_node_id=backend_node_id,
            loop=self._loop
        )
        return self._dom_element
    
    @property
    async def base_frame(self):
        try:
            res = await self.send_cdp("Page.getFrameTree")
            return res['result']["frameTree"]['frame']
        except CDPException as e:
            if not (e.code == -32601 and e.message == "'Page.getFrameTree' wasn't found"):
                raise e
        if res:
            return res["frame"]
        
    async def refresh(self, wait_load: bool = False, timeout: int = 10):
        await self.send_cdp("Page.reload")
        if wait_load:
            await self.wait_load(timeout)

    async def __find_in_shadow__(self, by: By, selector: str):
        resp = await self.send_cdp('DOM.getDocument', {
            'depth': -1,
            'targetId': self._id
        })
        elements = []
        root_node = resp.get('result').get("root", {})
        shadows = self.find_shadow_host(root_node, 'open')
        for shadow in shadows:
            web_element = WebElement(self, frame_id=self._id, node_id=shadow.get('nodeId'), backend_node_id=shadow.get('backendNodeId'))
            elements.append(web_element)
        
        results = []
        for element in elements:
            try:
                elem = await element.find_elements(by=by, value=selector)
                if elem:
                    results.extend(elem)
            except: pass
        
        return results
            
    async def find_element(self, by: By, value: str, timeout: int = 5) -> WebElement:
        results = await self.find_elements(by, value, timeout)
        if results:
            return results[0]
    
    async def find_elements(self, by: By, selector: str, timeout: int = 5, exists_ok: bool = False) -> WebElement:
        start = time.monotonic()
        elem = []
        while not elem and timeout and (time.monotonic() - start) < timeout:
            try:
                web_elem = await self._dom_element_
                elem = await web_elem.find_elements(by=by, value=selector, exists_ok=exists_ok)
                if elem:
                    break
                elem = await self.__find_in_shadow__(by, selector)
                if elem:
                    break
                if (not timeout) or (time.monotonic() - start) > timeout:
                    break
            except:
                pass
            finally:
                await asyncio.sleep(1)
        # if not elem:
        #     raise NoSuchElementException()
        return elem

    async def get(self, url: str, wait_load = False, timeout: int = 15):
        if not self._ws:
            await self._init()
        if url == 'about:blank':
            wait_load = False
        await self.send_cdp("Page.navigate", {"url": url})
        await asyncio.sleep(1)
        if wait_load:
            await self.wait_load(timeout)
        await self._on_loaded()
        
    async def wait_load(self, timeout):
        _start = time.monotonic()
        while not self._ws.page_loaded and time.monotonic() - _start < timeout:
            await asyncio.sleep(0.5)
        await self._on_loaded()

    async def _on_loaded(self, *args, **kwargs):
        self._global_this_ = {}
        self._document_elem = None
        self._isolated_context_id_ = None
        self._exec_context_id_ = None
        self._ws.page_loaded = True
    
    async def click(self, x: int = None, y: int = None, smooth: bool = True):
        x = x or self._x
        y = y or self._y
        await self.move_to(x, y, smooth=smooth)
        await asyncio.sleep(random.uniform(0.08, 0.5))
        await self.mouse_down()
        await asyncio.sleep(random.uniform(0.008, 0.02))
        await self.mouse_up()
        await asyncio.sleep(random.uniform(0.08, 0.2))


    def dynamic_bezier_curve(self, t, p0, p1, p2, p3, curve_strength):
        """
        Tính toán điểm trên đường cong Bézier bậc 3 với độ cong tùy chỉnh.
        
        -- GPT hỗ trợ
        """
        adjusted_p1 = (p0[0] + (p1[0] - p0[0]) * curve_strength, p0[1] + (p1[1] - p0[1]) * curve_strength)
        adjusted_p2 = (p3[0] + (p2[0] - p3[0]) * curve_strength, p3[1] + (p2[1] - p3[1]) * curve_strength)

        x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * adjusted_p1[0] + 3 * (1 - t) * t**2 * adjusted_p2[0] + t**3 * p3[0]
        y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * adjusted_p1[1] + 3 * (1 - t) * t**2 * adjusted_p2[1] + t**3 * p3[1]

        return x, y

    async def local_storage(self):
        resp = await self.send_cdp('Runtime.evaluate', {
            "expression": "JSON.stringify(localStorage)",
            "returnByValue": True
        })
        if resp:
            result_str = resp.get('result', {}).get('result', {}).get('value', {})
            return convert_json_values(result_str)
        return {}
    
    async def move_to(self, x, y, max_steps: int = 70, min_delay: float = 0.003, max_delay: float = 0.01, hold: bool = False, smooth: bool = True):
        """
        Di chuyển chuột nhanh và mượt từ vị trí hiện tại đến (x, y).

        :param x: Vị trí x đích.
        :param y: Vị trí y đích.
        :param max_steps: Số bước tối đa để hoàn thành di chuyển.
        :param min_delay: Thời gian chờ tối thiểu giữa mỗi bước.
        :param max_delay: Thời gian chờ tối đa giữa mỗi bước.
        
        GPT hỗ trợ 1 phần trong di chyển ngẫu nhiên
        """
        lts_mouse = await self.local_storage()
        last_x = lts_mouse.get('lts_last_x', 0)
        last_y = lts_mouse.get('lts_last_y', 0)
        start_x, start_y = last_x or self._x, last_y or self._y
        end_x, end_y = x, y

        if smooth:
            distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
            if float(distance) == 0.0:
                return
            steps = max(10, int(max_steps * min(1, distance / 300)))
            delay = max(min_delay, max_delay * min(1, 300 / distance))

            curve_strength = min(1, max(0.1, distance / 500))

            control_x1 = start_x + (end_x - start_x) * random.uniform(0.2, 0.4)
            control_y1 = start_y + (end_y - start_y) * random.uniform(0.2, 0.4)

            control_x2 = start_x + (end_x - start_x) * random.uniform(0.6, 0.8)
            control_y2 = start_y + (end_y - start_y) * random.uniform(0.6, 0.8)

            for step in range(steps + 1):
                t = step / steps  # Tham số t từ 0 đến 1
                current_x, current_y = self.dynamic_bezier_curve(
                    t, 
                    (start_x, start_y), 
                    (control_x1, control_y1), 
                    (control_x2, control_y2), 
                    (end_x, end_y),
                    curve_strength
                )

                # Làm tròn tọa độ
                current_x = round(current_x)
                current_y = round(current_y)
                await self.mouse_move(current_x, current_y, hold)
                await asyncio.sleep(delay)
        else:
            await self.mouse_move(end_x, end_y, hold)

    async def mouse_move(self, x:int, y:int, hold: bool=False):
        # Gửi sự kiện di chuyển chuột
        move_kwargs = {
            "type": "mouseMoved",
            "x": x,
            "y": y,
        }
        if hold:
            move_kwargs.update({'button': 'left'})
        await self.send_cdp("Input.dispatchMouseEvent", move_kwargs)
        # Cập nhật vị trí hiện tại
        self._x = x
        self._y = y
    
    async def move_to_random(self, max_steps: int = 70, min_delay: float = 0.003, max_delay: float = 0.01):
        """
        Di chuyển chuột đến một vị trí ngẫu nhiên trên trang.

        :param max_steps: Số bước tối đa để hoàn thành di chuyển.
        :param min_delay: Thời gian chờ tối thiểu giữa mỗi bước.
        :param max_delay: Thời gian chờ tối đa giữa mỗi bước.
        """
        # Lấy kích thước trang từ CDP
        viewport = await self.send_cdp("Page.getLayoutMetrics")
        if not viewport:
            return
        layout = viewport.get("contentSize", {})
        page_width = layout.get("width", 800)
        page_height = layout.get("height", 600)

        # Chọn vị trí ngẫu nhiên
        random_x = random.randint(0, page_width)
        random_y = random.randint(0, page_height)

        # Sử dụng hàm move_to để di chuyển đến vị trí ngẫu nhiên
        await self.move_to(random_x, random_y, max_steps=max_steps, min_delay=min_delay, max_delay=max_delay)
    
    async def mouse_up(self, x: str = None, y = None):
        x = x or self._x
        y = y or self._y
        await self.send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
    
    async def mouse_down(self, x: int = None, y: int = None):
        x = x or self._x
        y = y or self._y
        await self.send_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        
    async def click_element(self, element: WebElement):
        rect = await element.get_bounding_client_rect()
        x = random.randint(rect['x'], rect['x'] + rect['width'] - 5)
        y = random.randint(rect['y'], rect['y'] + rect['height'] - 5)
        await self.click(x, y)
    
            
    async def execute_script(self, script: str, *args):
        # resp = await self.send_cdp('Runtime.evaluate', {
        #     "expression": script
        # })
        # return resp
        __dom = await self._dom_element_
        resp = await __dom.execute_script(script, *args)
        return resp
    
    async def event_keyboard(self, key: Union[str, dict], type_event: str = 'keyDown'):
        if not isinstance(key, (str, dict)):
            raise ValueError("Invalid key format")
        # js_default = {'type': type_event}
        js_default = {
            "type": type_event,
            "key": key,
            "modifiers": 0
        }
        if isinstance(key, str):
            if key in KEY_MAPPING:
                key_code, virtual_key_code = KEY_MAPPING[key]
                js_default["code"] = key_code
                js_default["windowsVirtualKeyCode"] = virtual_key_code
                # js_default.update({
                #     'key': KEY_MAPPING[key][0],
                #     'code': KEY_MAPPING[key][0],
                #     'location': 0
                # })
            else:
                js_default.update({'text': key, 'key': key, 'code': key})
        else:
            js_default.update({
                'key': key['key'],
                'code': key['code'],
                'location': key.get('location', 0)  # Add location if specified
            })
        resp = await self.send_cdp('Input.dispatchKeyEvent', js_default)
        return resp

    async def key_down(self, key: Union[str, dict]):
        return await self.event_keyboard(key, 'keyDown')

    async def key_up(self, key: Union[str, dict]):
        return await self.event_keyboard(key, 'keyUp')

    async def send_text(self, text: str, send_char: bool = True):
        for char in text:
            if char in ["\n", '\\n']:
                char = "\r"

            key_event = {
                "type": "keyDown",
                "key": char,
                "modifiers": 0
            }

            # Nếu ký tự có trong KEY_MAPPING, gửi keyDown
            if char in KEY_MAPPING:
                key_code, virtual_key_code = KEY_MAPPING[char]
                key_event["code"] = key_code
                key_event["windowsVirtualKeyCode"] = virtual_key_code
                await self.send_cdp("Input.dispatchKeyEvent", key_event)
                if send_char:
                    await asyncio.sleep(random.uniform(0.03, 0.07))

            # Gửi ký tự trực tiếp bằng 'char'
            key_event["type"] = "char"
            key_event["text"] = char
            await self.send_cdp("Input.dispatchKeyEvent", key_event)
            if send_char:
                await asyncio.sleep(random.uniform(0.03, 0.07))

            # Gửi keyUp nếu có mã phím
            if char in KEY_MAPPING:
                key_event["type"] = "keyUp"
                del key_event["text"]
                await self.send_cdp("Input.dispatchKeyEvent", key_event)

    
    async def add_cookie(self, cookie_dict: Dict[str, Union[str, int, bool]]) -> None:
        if not (cookie_dict.get("url") or cookie_dict.get("domain") or cookie_dict.get("path")):
            cookie_dict["url"] = await self.current_url
        if "sameSite" in cookie_dict:
            assert cookie_dict["sameSite"] in ["Strict", "Lax", "None"]
        args = {"cookies": [cookie_dict]}
        await self.send_cdp("Storage.setCookies", args)

    async def delete_cookie(self, name: str, url: str = None, domain: str = None, path: str = None) -> None:
        args = {"name": name}
        if url:
            args["url"] = url
        if domain:
            args["domain"] = domain
        if path:
            args["path"] = path
        await self.send_cdp("Network.deleteCookies", args)

    async def delete_all_cookie(self):
        await self.send_cdp('Network.clearBrowserCookies')
    
    async def attach_frame(self, targetId: str):
        resp = await self.send_cdp('Target.attachToTarget', {"targetId": targetId, "flatten": True})
        sessionId = resp.get('result', {}).get('sessionId')
        if sessionId:
            self.current_sessionId = sessionId
            await self.send_cdp('Page.addScriptToEvaluateOnNewDocument', {
                'source': SCRIPT_PREV_LOAD_SHOW_MOUSE,
            })
        else:
            raise SwitchWindowError(f"Cannot attach to frame with ID {targetId}.")

    async def detach_frame(self):
        sessionId = self.current_sessionId
        self.current_sessionId = None
        if sessionId:
            await self.send_cdp('Target.detachFromTarget', {
                "sessionId": sessionId
            })
            
    async def scrollTo(self, total_scroll_x=1000, total_scroll_y=1000, step_x=50, step_y=50, delay=0.05):
        scrolled_x = 0
        scrolled_y = 0
        
        while scrolled_x < total_scroll_x or scrolled_y < total_scroll_y:
            delta_x = min(step_x, total_scroll_x - scrolled_x) if scrolled_x < total_scroll_x else 0
            delta_y = min(step_y, total_scroll_y - scrolled_y) if scrolled_y < total_scroll_y else 0

            await self.send_cdp('Input.dispatchMouseEvent', {
                'type': 'mouseWheel',
                'x': 0,
                'y': 0,
                'deltaX': delta_x,
                'deltaY': delta_y
            })

            scrolled_x += delta_x
            scrolled_y += delta_y

            await asyncio.sleep(delay)
    
    async def select_all(self):
        key_data = KEY_MAPPING['A']
        key_code, virtual_key_code = key_data
        key_event = {
            "type": "keyDown",
            "key": key_code,
            "code": key_code,
            "windowsVirtualKeyCode": virtual_key_code,
            "modifiers": 2
        }
        await self.send_cdp("Input.dispatchKeyEvent", key_event)
        key_event['type'] = 'keyUp'
        await self.send_cdp("Input.dispatchKeyEvent", key_event)
    
    async def backspace(self):
        key_code, virtual_key_code = KEY_MAPPING['Backspace']
        key_event = {
            "key": key_code,
            "code": key_code,
            "windowsVirtualKeyCode": virtual_key_code,
            "type": "keyDown",
            "modifiers": 0
        }
        await self.send_cdp("Input.dispatchKeyEvent", key_event)
        key_event['type'] = 'keyUp'
        await self.send_cdp("Input.dispatchKeyEvent", key_event)
    
    async def get_cookies(self):
        cookies = await self.send_cdp("Network.getCookies")
        return cookies['result']["cookies"]

    async def getAllCookie(self):
        cookies = await self.send_cdp("Network.getAllCookies")
        return cookies['result']["cookies"]

    async def start_stream(self):
        start = await self.send_cdp('Page.startScreencast', {
            "format": "jpeg",
            "quality": 80,
            "maxWidth": 1920,
            "maxHeight": 1080,
            "everyNthFrame": 1
        })
    
    async def drag_and_hold(self, start_x: int = None, start_y: int = None, end_x: int = None, end_y: int = None):
        start_x, start_y = start_x or self._x, start_y or self._y
        await self.move_to(start_x, start_y)
        await self.send_cdp('Input.dispatchMouseEvent', {
            'type': "mousePressed",
            'x': start_x,
            'y': start_y,
            'button': 'left'
        })
        await self.move_to(end_x, end_y, min_delay=0.02, max_delay=0.08, hold=True)

        await self.send_cdp('Input.dispatchMouseEvent', {'type': "mouseReleased", "x": end_x, "y": end_y, 'button': 'left'})
    
