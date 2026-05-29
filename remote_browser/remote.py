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

import os
import atexit
import base64
import asyncio
import uuid
import time
from datetime import datetime, timedelta

from pyee import EventEmitter
from typing import Dict, Any, Union, List, Callable

from .cdp.connection import CDPConnection

from .common.target import Target
from .common.switch_to import SwitchTo
from .common.webelement import WebElement
from .common.timeout import Timeout
from .common.config import Config

from .type.browser_support import By, Type
from .utils import get_ws_endpoint, SCRIPT_SHOW_MOUSE, get_point
from .exceptions import RemoteException, TargetError
from .listener import lister_event

class RemoteCDP(EventEmitter):
    def __enter__(self):
        return self
    
    def close_remote(self, close_browser = False):
        if getattr(self, '_remote_closed', False):
            return
        self._remote_closed = True
        if close_browser:
            self.quit_browser()
        try:
            self.run_async(self.connection.close())
            self.run_async(self._current_target._ws.close())
        except Exception as e:
            pass
        if self._exit_callback:
            self._exit_callback()
        
        # Đảm bảo chỉ đóng loop được quản lý bởi class
        if self._loop and (self._loop_created or self._close_loop) and not self._loop.is_closed():
            # Lấy tất cả các task trong event loop này
            all_tasks = asyncio.all_tasks(self._loop)
            for task in all_tasks:
                try:
                    task.cancel()
                    self._loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error cancelling task: {e}")
            try:
                self._loop.stop()
                self._loop.close()
            except Exception as e:
                print(f"Error closing event loop: {e}")

    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Đóng browser nếu cần
        self.close_remote(False)

                
    def __update_window_handles__(self, switch_attach_page: bool = False):
        pages = self.pages()
        for page in pages:
            if switch_attach_page and page['attached']:
                self.switch_to.window(page['targetId'])
            
            if not str(page['url']).startswith('devtools'):
                targetId = page['targetId']
                if targetId not in self._window_handles:
                    self._window_handles.append(targetId)
        
    def __init__(self, debugger_address: str = None, exit_callback: Callable = None, headless: bool = False, loop: asyncio.AbstractEventLoop = None, close_loop: bool = False):
        super().__init__()
        
        self.__uuid_session__ = str(uuid.uuid4())
        self._current_frame_id = None
        self._window_handles: List[str] = []
        self._current_target: Target = None
        self._exit_callback = exit_callback
        self._remote_closed = False
        self._browser_quit = False
        self._loop_created = False
        self._close_loop = close_loop
        if not debugger_address:
            raise RemoteException("Debugger Adderss Error")
        self._url_debugger = f'http://{debugger_address}'
        self._debugger_address = debugger_address
        
        self._ws_endpoint = get_ws_endpoint(self._url_debugger)
        if not loop:
            loop = asyncio.new_event_loop()
            self._loop_created = True

        self._loop = loop
        self.connection = CDPConnection(self._ws_endpoint, self._loop, self.__uuid_session__)
        self.run_async(self.connection.connect())
        lister_event.on(f'cdp_event_{self.__uuid_session__}', self.event_handler)
        self.run_async(self.connection.send('Target.setDiscoverTargets', {"discover": True}))

        self.on('Target.targetCreated', lambda e:self._loop.create_task(self.target_handler(e)))
        self.on('Target.targetDestroyed', lambda e: self._loop.create_task(self._target_destroy_handler(e)))

        self.__update_window_handles__()
        self.switch_to.window(self.window_handles[0])
        if headless:
            self.run_async(self.__config_headless())
        atexit.register(self.quit_browser)

    async def __config_headless(self):
        content = """Object.defineProperty(window, "navigator", {
            Object.defineProperty(window, "navigator", {
                value: new Proxy(navigator, {
                has: (target, key) => (key === "webdriver" ? false : key in target),
                get: (target, key) =>
                    key === "webdriver"
                    ? false
                    : typeof target[key] === "function"
                    ? target[key].bind(target)
                    : target[key],
                }),
            });
        """
        userAgent = await self._current_target.execute_script(
                "return navigator.userAgent"
            )
        
        await self._current_target.inject_onload_javascript(content)
        await self._current_target.send_cdp('Network.setUserAgentOverride', {
            "userAgent": userAgent.replace("Headless", "")
        })
        await self._current_target.inject_onload_javascript("""
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
            Object.defineProperty(navigator.connection, 'rtt', {get: () => 100});
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed',
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                },
                runtime: {
                    OnInstalledReason: {
                        CHROME_UPDATE: 'chrome_update',
                        INSTALL: 'install',
                        SHARED_MODULE_UPDATE: 'shared_module_update',
                        UPDATE: 'update'
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic'
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        ARM64: 'arm64',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        MIPS: 'mips',
                        MIPS64: 'mips64',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformOs: {
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        MAC: 'mac',
                        OPENBSD: 'openbsd',
                        WIN: 'win'
                    },
                    RequestUpdateCheckStatus: {
                        NO_UPDATE: 'no_update',
                        THROTTLED: 'throttled',
                        UPDATE_AVAILABLE: 'update_available'
                    }
                }
            }

            if (!window.Notification) {
                window.Notification = {
                    permission: 'denied'
                }
            }

            const originalQuery = window.navigator.permissions.query
            window.navigator.permissions.__proto__.query = parameters =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: window.Notification.permission })
                    : originalQuery(parameters)

            const oldCall = Function.prototype.call
            function call() {
                return oldCall.apply(this, arguments)
            }
            Function.prototype.call = call

            const nativeToStringFunctionString = Error.toString().replace(/Error/g, 'toString')
            const oldToString = Function.prototype.toString

            function functionToString() {
                if (this === window.navigator.permissions.query) {
                    return 'function query() { [native code] }'
                }
                if (this === functionToString) {
                    return nativeToStringFunctionString
                }
                return oldCall.call(oldToString, this)
            }
            // eslint-disable-next-line
            Function.prototype.toString = functionToString
            """
        )
    
    async def _target_destroy_handler(self, params: dict):
        if 'targetId' in params:
            targetId = params.get('targetId', None)
            if not targetId:
                return
            if targetId in self.window_handles:
                self.window_handles.remove(targetId)

    async def target_handler(self, data):
        targetInfo = data['targetInfo']
        if targetInfo['type'] == 'page':
            targetId = targetInfo['targetId']
            self._window_handles.append(targetId)
            
            
    def event_handler(self, data):
        if 'method' in data:
            self.emit(data['method'], data['params'])
            
    def clear_cache_and_cookie(self):
        self.run_async(self.connection.send("Network.clearBrowserCache"))
        self.run_async(self.connection.send("Network.clearBrowserCookies"))
        
    def run_async(self, coudition_call: asyncio.Condition):
        return self._loop.run_until_complete(coudition_call)
        
    @property
    def local_storage(self):
        resp = self.run_async(self._current_target.local_storage())
        return resp
    
    @property
    def switch_to(self):
        return SwitchTo(self, self._loop)
    
    @property
    def window_handles(self):
        # self.__update_window_handles__()
        return self._window_handles
    
    @property
    def base_target(self):
        return self._base_target
    
    @base_target.setter
    def base_target(self, target: Target):
        if not isinstance(target, Target):
            raise TargetError("Target not invalid")
        self._base_target = target
    
    @property
    def window_id(self):
        return self.run_async(self.connection.send('Browser.WindowID'))
    
    @property
    def ws_endpoint(self):
        return self._ws_endpoint
    
    @property
    def page_source(self):
        return self.run_async(self._current_target.page_source)
    
    @property
    def current_url(self):
        return self.run_async(self._current_target.current_url)
    
    @property
    def title(self):
        return self.run_async(self._current_target.title)
    
    def targets(self):
        all_targets = self.run_async(self.connection.send('Target.getTargets', {})).get('result', {}).get('targetInfos', {})
        return all_targets
    
    def pages(self):
        return [target for target in self.targets() if target['type'] == 'page' and 'chrome-extension' not in target['url']]
    
    def execute_script(self, script: str, *args):
        for _ in range(3):
            try:
                result = self.run_async(self._current_target.execute_script(script, *args))
                self.sleep(0.5)
                return result
            except: 
                self.sleep(0.5)
        
    def show_mouse(self):
        self.run_async(self._current_target.execute_script(SCRIPT_SHOW_MOUSE))
    
    def get(self, url: str, wait_load = False):
        self.run_async(self._current_target.get(url, wait_load))
        
    def refresh(self, wait_load = False):
        self.run_async(self._current_target.refresh(wait_load))
    
    def find_element(self, by: By, value: str, timeout: Union[int, None] = None) -> WebElement:
        _timeout = timeout or Timeout.ELEMENT_ACTION
        resp = self.run_async(self._current_target.find_element(by, value, _timeout))
        return resp

    def find_elements(self, by: By, value: str, timeout: Union[int, None] = None) -> List[WebElement]:
        _timeout = timeout or Timeout.ELEMENT_ACTION
        resp = self.run_async(self._current_target.find_elements(by, value, _timeout))
        return resp
    
    def new_tab(self, url: str = 'about:blank'):
        resp = self.run_async(self.connection.send('Target.createTarget', {"url": url}))
        targetId = resp['result']['targetId']
        self.switch_to.window(targetId)
    
    def send_text(self, text: str, send_enter: bool = False, clear_text: bool = True):
        if clear_text:
            self.clear_text()
        if send_enter:
            text += '\n'
        return self.run_async(self._current_target.send_text(text, send_char=Config.SEND_CHAR))

    def press(self, key: Type):
        self.run_async(self._current_target.key_down(key))
        self.run_async(self._current_target.key_up(key))
    
    def click_element(self, element_or_by: Union[str, WebElement], selector: str = '', timeout: Union[int, None] = None):
        _timeout = timeout or Timeout.ELEMENT_ACTION
        if isinstance(element_or_by, WebElement):
            element = element_or_by
        else:
            element = self.find_element(element_or_by, selector, _timeout)
        if element:
            element.click(Config.MOVE_SMOOTH)
        return element
    
    def click_send_text(self, element_or_by: Union[str, WebElement], selector: str = '', text: str = "LTT_Dev", send_enter: bool = False, clear_text: bool = True, timeout: Union[int, None] = None):
        _timeout = timeout or Timeout.ELEMENT_ACTION
        element = self.click_element(element_or_by, selector, _timeout)
        
        if element:
            self.send_text(
                text = text, 
                send_enter = send_enter,
                clear_text = clear_text
            )
        
        return element
    
    def sleep(self, timeout: float):
        # self.run_async(asyncio.sleep(timeout))
        time.sleep(timeout)
    
    def click(self, x: int = None, y: int = None):
        self.run_async(self._current_target.click(x, y))
        return self
    
    def move_to(self, x: int, y:int):
        self.run_async(self._current_target.move_to(x, y, smooth=Config.MOVE_SMOOTH))
        return self

    def move_to_random(self):
        return self.run_async(self._current_target.move_to_random(10, max_delay=0.005))

    def wait_load(self, timeout: Union[int, None] = None):
        _timeout = timeout or Timeout.PAGE_LOAD_TIMEOUT
        return self.run_async(self._current_target.wait_load(_timeout))
    
    def send_cdp(self, method: str, params: dict = {}, *, timeout: Union[int, None] = None):
        _timeout = timeout or Timeout.CDP_TIMEOUT
        return self.run_async(self._current_target.send_cdp(method, params, _timeout))
    
    def add_cookie(self, cookie_dict: Dict[str, Union[str, int, bool]]) -> None:
        return self.run_async(self._current_target.add_cookie(cookie_dict=cookie_dict))
    
    def add_cookie_string(self, cookie_string: str, domain: str = '.tiktok.com', expiry_date: int = 30, secure: bool = True, httpOnly: bool = False):
        expiry_time = (datetime.now() + timedelta(days=expiry_date)).timestamp()
        json_cookie = {'name': '', 'value': '', 'path': '/', "expiry": int(expiry_time), "secure": secure, "httpOnly": httpOnly}
        if domain is not None: json_cookie['domain'] = domain
        cookies = [cookie.strip() for cookie in cookie_string.split(";")]
        for cookie in cookies:
            try:
                name, value = cookie.split("=")
                json_cookie['name'] = name; json_cookie['value'] = value
                self.add_cookie(json_cookie)
            except:
                pass
    
    def delete_cookie(self, name: str, url: str = None, domain: str = None, path: str = None) -> None:
        return self.run_async(self._current_target.delete_cookie(name, url, domain, path))
    
    def delete_all_cookie(self):
        return self.run_async(self._current_target.delete_all_cookie())
    
    def mouse_down(self, x:int = None, y: int = None):
        self.run_async(self._current_target.mouse_down(x, y))
    
    def move_to_element(self, element: WebElement):
        if not isinstance(element, WebElement):
            return
        model_box = element.box_model
        if model_box:
            x, y = get_point(model_box)
            self.move_to(x, y)
    
    def mouse_up(self, x:int = None, y: int = None):
        self.run_async(self._current_target.mouse_up(x, y))
    
    def scrollTo(self, total_scroll_x=1000, total_scroll_y=1000, step_x=50, step_y=50, delay=0.05):
        self.run_async(self._current_target.scrollTo(total_scroll_x, total_scroll_y, step_x, step_y, delay))
        
    @property
    def timeouts(self):
        return Timeout
    
    def send_key_combination(self, keys: List):
        return self.run_async(self._current_target.send_key_combination(keys))
    
    def clear_text(self):
        self.run_async(self._current_target.select_all())
        self.run_async(self._current_target.backspace())
    
    def get_cookies(self):
        return self.run_async(self._current_target.get_cookies())
    
    def get_all_cookies(self):
        return self.run_async(self._current_target.getAllCookie())
    
    def save_screenshot(self, file_path: str):
        response_data = self.send_cdp('Page.captureScreenshot', {
            "format": "png",
            "captureBeyondViewport": True
        })
        screenshot_data = response_data["result"]["data"]
        file_path = os.path.abspath(file_path)
        _dir = os.path.dirname(file_path)
        if not os.path.exists(_dir):
            os.makedirs(_dir)
        if not os.path.exists(file_path):
            open(file_path, 'w+')
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(screenshot_data))
    
    def drag_and_hold(self, start_x: int = None, start_y: int = None, end_x: int = None, end_y: int = None):
        self.run_async(self._current_target.drag_and_hold(start_x, start_y, end_x, end_y))
    
    @property
    def configs(self):
        return Config
    
    def quit_browser(self):
        """
        Gửi lệnh 'Browser.close' để đóng trình duyệt.
        Ví dụ:
            remote_browser = RemoteBrowser(connection)
            remote_browser.quit_browser()
        """
        if getattr(self, '_browser_quit', False):
            return
        self._browser_quit = True
        if self._loop and self._loop.is_closed():
            return
        self.run_async(self.connection.send('Browser.close'))
        
    def close(self, tab_handler: str = 'current'):
        """
        Args:
            tab_handler (str): ID của tab cần đóng. Mặc định là 'current' để đóng tab hiện tại.
        Example:
            remote = RemoteCDP(debugger_address="localhost:9222")
            remote.new_tab("https://www.example.com")
            remote.close(tab_handler=remote.window_handles[1])
        """
        self.run_async(self.connection.send('Target.closeTarget', {
            'targetId': str(self._current_target._id) if tab_handler == 'current' else tab_handler
        }))
