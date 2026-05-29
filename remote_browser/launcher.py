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
import tempfile
import subprocess
import psutil
import asyncio
import shutil

from pyee import EventEmitter
from typing import Union, Dict, Callable, List

from .type.browser import Browser

# from .remote import RemoteBrowser
from .options import BrowserOptions
from .exceptions import ExecutableNotFound, BrowserError
from .browser_map import find_browser_executable
from .utils import free_port, get_ws_endpoint

from .remote import RemoteCDP


class LaunchBrowser(RemoteCDP):
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        
    
    def __init__(self, options: Union[BrowserOptions, None] = None, property_browser: dict = {}, browser_type: Browser = Browser.CHROME, exit_callback: Callable = None, loop: asyncio.AbstractEventLoop = None) -> None:
        # super().__init__()
        # self._exit_callback = exit_callback
        self._pid = None
        self.__list_pid = set()
        
        if not options:
            options = BrowserOptions()
        
        profile_path            = property_browser.get('profile_path', None)
        language                = property_browser.get('language', 'en')
        xChrome                 = property_browser.get('xChrome', 0)
        yChrome                 = property_browser.get('yChrome', 0)
        width                   = property_browser.get('width', 1920)
        height                  = property_browser.get('height', 1080)
        scale_browser           = float(property_browser.get('scale', 1))
        extension_list          = property_browser.get('extensions', [])
        proxy                   = property_browser.get('proxy', None)
        user_agent              = property_browser.get('user-agent', None)
        browser_executable      = property_browser.get('browser_path', find_browser_executable(browser_type))
        start_is_app            = property_browser.get('app', False)
        args_browser            = property_browser.get('args', [])
        headless                = property_browser.get('headless', False)
        
        for arg in options.arguments:
            if any([_ in arg for _ in ("--headless", "headless")]):
                options.arguments.remove(arg)
                headless = True
        
        if headless:
            options.add_argument('--headless=new')
            
        if start_is_app:
            options.add_argument(f'--app={start_is_app}')
        if not browser_executable:
            raise ExecutableNotFound(f"Browser Executable '{browser_type}' Not Found")
        
        #Configure language và profile_path
        options.binary_location = browser_executable
        keep_profile = bool(profile_path)
        if profile_path:
            for data in options.arguments:
                if 'user-data-dir' in data:
                    options.arguments.remove(data)
                    break
            keep_profile = True
        else:
            profile_path = tempfile.mkdtemp('tlsoftware')
            keep_profile = False
        options.add_argument(f'--user-data-dir="{profile_path}"')
        options.add_argument(f'--lang={language}')
        
        #Config tọa độ, size, scale browser
        options.add_argument("--window-position={},{}".format(xChrome*(width-50), yChrome*(height-50)))
        options.add_argument("--window-size={},{}".format(str(width), str(height)))
        options.add_argument("--force-device-scale-factor={}".format(scale_browser))
        
        # Thêm danh sách extension
        if not isinstance(extension_list, list):
            extension_list = []
        if extension_list:
            options.add_argument('--load-extension="{}"'.format(','.join(list(set(extension_list)))))

        # Config Proxy
        if proxy:
            options.add_argument('--proxy-server={}'.format(proxy))
        
        
        #Config UserAgent
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        
        #Config debug_address
        if not options.debugger_address:
            debug_port = free_port()
            debug_host = '127.0.0.1'
            options.debugger_address = f'{debug_host}:{debug_port}'
        else:
            debug_host, debug_port = options.debugger_address.split(':')
        options.add_argument("--remote-debugging-host=%s" % debug_host)
        options.add_argument("--remote-debugging-port=%s" % debug_port)
        
        # Save file save_preferences profile
        options.save_preferences()
        self._options = options
        self._user_data_dir = profile_path
        self._keep_profile = keep_profile
        
        # Open browser
        self.__start_browser(args_browser)
        # if not self.is_running():
        #     raise BrowserError("Can't open browser, is browser closed:\n")
        super().__init__(options.debugger_address, loop=loop, exit_callback=exit_callback, headless = headless)
        #Tạo biến toàn cục class
    
    def get_pid(self):
        chrome_processes = []
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                executable_name = self._options.binary_location.split('\\')[-1]
                cmdline = process.info['cmdline']
                if cmdline and process.info['name'] == executable_name and (self._options.debugger_address.split(':')[-1] in ' '.join(cmdline) or self._user_data_dir.split('\\')[-1] in cmdline):
                    chrome_processes.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        for process in chrome_processes:
            try:
                process: psutil.Process
                pid = process.pid
                if pid not in self.__list_pid: 
                    self.__list_pid.add(pid)
            except:pass
    
    def is_running(self):
        self.get_pid()
        return bool(self.__list_pid)
    
    def __start_browser(self, args_browser):
        args = self._options.to_command_args()
        browser_args = [self._options.binary_location, args] + args_browser
        app_processtor = subprocess.Popen(' '.join(browser_args))
        self._pid = app_processtor.pid
        self.__list_pid.add(app_processtor.pid)
    
    def quit_browser(self):
        if getattr(self, '_browser_quit', False):
            return
        self._browser_quit = True
        if self._loop and not self._loop.is_closed():
            super().quit_browser()
            super().close_remote(False)
        if not self._keep_profile:
            for _ in range(5):
                try:
                    shutil.rmtree(self._user_data_dir, ignore_errors=False)
                    break
                except:
                    self.sleep(0.1)
    
    @property
    def pid(self):
        return self._pid
