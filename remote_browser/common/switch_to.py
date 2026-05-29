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

import asyncio
import time

from ..exceptions import SwitchWindowError
from .webelement import WebElement
from .target import Target
from typing import Callable
try:
    from ..launcher import LaunchBrowser
except: pass

class SwitchTo:
    def __init__(self, browser: "LaunchBrowser", loop: asyncio.AbstractEventLoop = None):
        """
        Initialize the SwitchTo class to support switching between tabs and iframes.
        :param browser: LaunchBrowser object controlling the browser.
        """
        self._browser = browser
        if not loop:
            event_loop = asyncio.get_event_loop()
            loop = event_loop if event_loop.is_running() else asyncio.new_event_loop()
        
        self._loop = loop
    
    def _activate_window(self, target_id: str):
        """
        Perform an action to ensure the tab becomes active, 
        such as clicking an element in the current tab or using `Target.activate` if supported.
        """
        try:
            self._loop.run_until_complete(self._browser.connection.send('Target.activateTarget', {
                "targetId": target_id
            }))
        except Exception as e:
            raise SwitchWindowError(f'Cannot switch to tab with window ID: "{target_id}"')

    def window(self, target_id: str):
        """
        Switch to a specific tab (window) based on target ID.
        :param target_id: Target ID of the tab to switch to.
        """
        if target_id not in self._browser._window_handles:
            raise ValueError(f"Target ID {target_id} does not exist in the list of tabs.")
    
        self._activate_window(target_id)
        if self._browser._current_target and self._browser._current_target._ws:
            self.run_async(self._browser._current_target._ws.close())
        target = Target(self._browser._debugger_address, target_id, loop=self._loop)
        self._browser._current_target = target
        self._browser.base_target = target
    
    def run_async(self, callback: asyncio.Condition):
        return self._loop.run_until_complete(callback)

    def frame(self, element_frame: WebElement, timeout: int = 15, poll_interval: float = 0.5):
        backend_node_id = element_frame._backend_node_id
        resp = self.run_async(self._browser._current_target.send_cdp('DOM.describeNode', {'backendNodeId': backend_node_id}))
        frame_id = resp.get('result', {}).get('node', {}).get('frameId', None)
        
        target_id = None
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:
            # Kiểm tra targets
            targets = self._browser.targets()
            for target in targets:
                if target['targetId'] == frame_id:
                    target_id = target['targetId']
                    break
            
            if target_id:
                break

            # Nếu không tìm thấy trong targets, kiểm tra frame tree
            frame_info = self.__find_frame_in_tree__(frame_id)
            if frame_info:
                target_id = frame_info['frameId']
                break
            
            # Đợi trước khi thử lại
            time.sleep(poll_interval)
        
        if not target_id:
            raise SwitchWindowError("The iframe has changed or reloaded.")

        if not self._browser._current_target._is_frame:
            self._browser.base_target = self._browser._current_target
        self.run_async(self._browser._current_target.attach_frame(target_id))
        return self._browser

    
    def default_content(self):
        self._browser._current_target = self._browser.base_target
        self.run_async(self._browser._current_target.detach_frame())
        # sessionId = self._browser._current_target.current_sessionId
        # self._browser._current_target.current_sessionId = None
        # if sessionId:
        #     print(self._browser.send_cdp('Target.detachFromTarget', {
        #         "sessionId": sessionId
        #     }))
    
    def parent_frame(self):
        if not self._browser._current_target:
            raise SwitchWindowError("No current target available to switch to the parent frame.")
        
        targetId = self._browser._current_frame_id
        frame_info = self.__find_frame_in_tree__(targetId)

        if frame_info is None:
            raise SwitchWindowError(f"No parent frame found for target ID: {targetId}")
        parent_id = frame_info['parentId']
        self._browser._current_target.current_sessionId = None
        if self._browser._current_target.id == parent_id:
            self.default_content()
        else:
            # resp = self._browser.send_cdp('Target.attachToTarget', {"targetId": parent_id, "flatten": True})
            # session_id = resp.get('sessionId', None)
            # if not session_id:
            #     raise SwitchWindowError(f"Cannot attach to parent frame with ID {parent_id}.")
            # self._browser._current_target.current_sessionId = session_id
            # print(self._browser._current_target.current_sessionId)
            self.run_async(self._browser._current_target.attach_frame(targetId))
            return self._browser
    
    def __find_frame_in_tree__(self, target_id):
        frames_resp = self._browser.send_cdp('Page.getFrameTree')
        frame_tree = frames_resp.get('result', {}).get('frameTree', {})
        def _find(tree, target_id):
            current_frame = tree.get('frame', {})
            current_frame_id = current_frame.get('id')
            parent_frame_id = current_frame.get('parentId', None)

            if current_frame_id == target_id:
                return {"parentId": parent_frame_id, "frameId": current_frame_id}

            for child in tree.get('childFrames', []):
                result = _find(child, target_id)
                if result:
                    return result

            return None
        return _find(frame_tree, target_id)
