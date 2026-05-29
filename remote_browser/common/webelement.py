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
import asyncio
import numpy as np
import random
import inspect
import math
from .deserialize import *

from typing import Union, List

from ..utils import get_point, find_shadow_host, SCRIPT_CHECK_VISIBLE
from ..exceptions import CDPException, NoSuchElementException
from ..type.browser_support import By

class StaleElementReferenceException(StaleJSRemoteObjReference):
    def __init__(self, elem):
        message = f"Page or Frame has been reloaded, or the element removed, {elem}"
        super().__init__(_object=elem, message=message)
        
class WebElement(JSRemoteObj):
        
    def __getattribute__(self, item):
        res = super().__getattribute__(item)
        if res is None or item == "_loop":
            return res
        loop = self._loop
        if loop and (not loop.is_running()):
            if inspect.iscoroutinefunction(res):
                def syncified(*args, **kwargs):
                    return self._loop.run_until_complete(res(*args, **kwargs))

                return syncified
            if inspect.isawaitable(res):
                return self._loop.run_until_complete(res)
        return res
    
    def __init__(self, 
            target, 
            frame_id: Union[int, None], 
            isolated_exec_id: Union[int, None] = None, 
            obj_id=None, 
            node_id=None, 
            backend_node_id: str = None, 
            loop=None, 
            class_name: str = None,
            context_id: int = None, 
            is_iframe: bool = False ) -> None:
        
        self._loop = loop
        if not (obj_id is None or node_id is None or backend_node_id is None):
            raise ValueError("either js, obj_id or node_id need to be specified")
        self._node_id = node_id
        self._backend_node_id = backend_node_id
        self._class_name = class_name
        self._started = False
        self.___context_id__ = context_id
        self._obj_ids = {context_id: obj_id}
        self._frame_id = frame_id
        self._is_iframe = is_iframe
        self._stale = False
        if obj_id and context_id:
            self._obj_ids[context_id] = obj_id
        self.___obj_id__ = None
        super().__init__(target=target, frame_id=frame_id, obj_id=obj_id, isolated_exec_id=isolated_exec_id)
    
    @property
    def frame_id(self):
        return self._frame_id
        
    # @property
    # async def source(self):
    #     try:
    #         res = await self.execute_script('return obj.outerHTML')
    #         return res
    #     except:
    #         pass
    
    @property
    async def source(self):
        try:
            args = self._args_builder
            res = await self.__target__.send_cdp("DOM.getOuterHTML", args)
            return res['result']["outerHTML"]
        except:
            pass


    @property
    async def is_frame(self):
        ars = self._args_builder
        resp = await self.__target__.send_cdp('DOM.describeNode', ars)
        result = resp.get('result', {})
        nodeName = result.get('node', {}).get('nodeName', '')
        if nodeName.lower() == 'iframe':
            return result
        
    @property
    async def text(self):
        resp = await self.get_att('textContent')
        return str(resp)
    
    @property
    def _args_builder(self) -> dict:
        if self._node_id:
            return {"nodeId": self._node_id}
        elif self.__obj_id__:
            return {"objectId": self.__obj_id__}
        elif self._backend_node_id:
            return {"backendNodeId": self._backend_node_id}
        else:
            raise ValueError(f"missing remote element id's for {self}")
    
    @property
    async def shadowRoot(self):
        resp = await self.__target__.send_cdp('DOM.describeNode', {
            "objectId": self.__obj_id__
        })
        shadow_list = find_shadow_host(resp.get('result', {}).get('node', {}))
        if not shadow_list:
            return None
        else:
            shadow = shadow_list[0]
            response = await self.__target__.send_cdp("DOM.resolveNode", {
                "backendNodeId": shadow['backendNodeId']
            })
            # self._backend_node_id = shadow['backendNodeId']
            objectId = response.get('result', {}).get('object', {}).get('objectId')
            # print(objectId)
            super().__setattr__('___obj_id__', objectId)
            return WebElement(
                target=self.__target__,
                frame_id= await self.__frame_id__,
                obj_id=objectId,
                backend_node_id=shadow['nodeId'],
                loop=self._loop,
            )
    
    async def send_file(self, file_path: str):
        if not os.path.exists(file_path):
            raise ValueError("File NOT FOUND !")
        resp = await self.__target__.send_cdp('DOM.setFileInputFiles', {
            "files": [file_path],
            "backendNodeId": self._backend_node_id
        })
    async def find_elements(self, by: By, value: str, exists_ok = False) -> List["WebElement"]:
        if by == By.ID:
            selector = f'[id="{value}"]'
        elif by == By.CLASS_NAME:
            selector = f".{value}"
        elif by == By.NAME:
            selector = f'[name="{value}"]'
        elif by == By.TAG_NAME:
            selector = value
        elif by == By.CSS_SELECTOR:
            selector = value
        elif by == By.XPATH:
            selector = """return document.evaluate(
                arguments[0],
                document,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                null,
            );"""
        else:
            raise ValueError(f"Unsupported locator strategy: {by}")
        try:
            if by == By.XPATH:
                resp = await self.execute_script(selector, value)
                elements = list(resp)
            else:
                resp = await self.execute_script('return obj.querySelectorAll(arguments[0])', selector)
                elements = resp
            
            if exists_ok:
                visible_elements = []
                for element in elements:
                    if element._class_name in [
                        'HTMLOptionElement',
                        # 'SVGSVGElement'
                    ]:
                        visible_elements.append(element)
                        continue
                    is_visible = await self.is_element_visible(element)
                    if is_visible:
                        visible_elements.append(element)

                return visible_elements
            else:
                return elements
        except: 
            import traceback; traceback.print_exc();
            return []
            # args = {"selector": selector, "nodeId": self._node_id}
            # resp = await self.__target__.send_cdp("DOM.querySelectorAll", args)
            
            # if 'result' in resp and 'nodeIds' in resp['result']:
            
            #     node_ids = resp['result']['nodeIds']
            #     for node_id in node_ids:
            #         elements.append(WebElement(self.__target__, frame_id=self._frame_id, node_id=node_id, loop=self._loop))
        # return elements
    @property
    async def rect(self):
        rect = await self.execute_script('obj.getBoundingClientRect()')
        print(rect)
        
    async def is_element_visible(self, element) -> bool:
        try:
            visible = await self.execute_script(
                """
                const elem = arguments[0];
                const style = window.getComputedStyle(elem);
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    (elem.offsetWidth > 0 || elem.getBoundingClientRect().width > 0) &&
                    (elem.offsetHeight > 0 || elem.getBoundingClientRect().height > 0)
                );

                """, element
            )
            return visible
        except Exception as e:
            return False
    
    async def find_element(self, by: By, value: str) -> "WebElement":
        elements = await self.find_elements(by, value)
        if elements:
            return elements[0]
    
    async def scroll_to(self):
        # await self.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", self)
        for _ in range(3):
            try:
                isVisible = await self.execute_script(SCRIPT_CHECK_VISIBLE, self)
                print("Scrolling", isVisible)
                return isVisible
            except:
                await asyncio.sleep(0.6)
    
    
    
    async def get_att(self, name: str) -> Union[str, None]:
        return await self.execute_script(f"return obj[arguments[0]]", name)
    
    async def set_att(self, name: str, value: str):
        return await self.execute_script(f"obj.setAttribute(arguments[0], arguments[1])", name, value)
    
    async def click(self, smooth: bool = True):
        scrolled = await self.scroll_to()
        if scrolled:
            await asyncio.sleep(1.5)
        else:
            await asyncio.sleep(random.uniform(0.08, 0.5))
        model_box = await self.box_model
        if model_box:
            x, y = get_point(model_box)
            await self.__target__.click(x, y, smooth = smooth)
            return self
        else:
            await self.execute_script('obj.click()')
        
    async def clear_text(self):
        scrolled = await self.scroll_to()
        if scrolled:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(random.uniform(0.08, 0.5))
        tag_name = await self.get_att("tagName")
        tag_name = tag_name.lower() if tag_name else ""
        
        if tag_name in ["input", "textarea"]:
            await self.execute_script("arguments[0].value = '';", self)
            return self
        else:
            raise ValueError(f"clear_text is not supported for elements of type {tag_name}")
    
    @property
    async def rect(self):
        resp = await self.execute_script('''
            const rect = obj.getBoundingClientRect();
            return rect;
        ''')
        if isinstance(resp, (JSObject, dict)):
            return dict(resp)
        
    @property
    async def box_model(self):
        try:
            args = self._args_builder
            res = await self.__target__.send_cdp("DOM.getBoxModel", args)
            model = res['result']['model']
            keys = ['content', 'padding', 'border', 'margin']
            for key in keys:
                quad = model[key]
                model[key] = np.array([[quad[0], quad[1]], [quad[2], quad[3]], [quad[4], quad[5]], [quad[6], quad[7]]])
            return model
        except:
            pass
    
    async def __obj_id_for_context__(self, context_id: int = None):
        if not self._obj_ids.get(context_id):
            args = {}
            if self._backend_node_id:
                args["backendNodeId"] = self._backend_node_id
            elif self._node_id:
                args["nodeId"] = self._node_id
            else:
                raise ValueError(f"missing remote element id's for {self}")

            if context_id:
                args["executionContextId"] = context_id
            try:
                res = await self.__target__.send_cdp("DOM.resolveNode", args)
            except CDPError as e:
                if e.code == -32000 and e.message == 'No node with given id found':
                    raise StaleElementReferenceException(self)
                else:
                    raise e
            if not res:
                return
            res = res.get('result', {})
            object_dict = res.get("object", {})
            obj_id = object_dict.get("objectId")
            if obj_id:
                if self.__context_id__ == context_id:
                    self.___obj_id__ = obj_id
                # if not context_id:
                    
                self._obj_ids[context_id] = obj_id
            class_name = object_dict.get("className")
            if class_name:
                self._class_name = class_name
        return self._obj_ids.get(context_id)
    
    @property
    async def obj_id(self):
        return await self.__obj_id_for_context__()
    
    async def execute_raw_script(self, script: str, *args, await_res: bool = False, serialization: str = None,
                                max_depth: int = 2, timeout: float = 2, execution_context_id: str = None,
                                unique_context: bool = None):
        return await self.__exec_raw__(script, *args, await_res=await_res, serialization=serialization,
                                    max_depth=max_depth, timeout=timeout,
                                    execution_context_id=execution_context_id,
                                    unique_context=unique_context)

    async def execute_script(self, script: str, *args, max_depth: int = 2, serialization: str = None,
                            timeout: float = 2, execution_context_id: str = None, unique_context: bool = None):
        return await self.__exec__(script, *args, max_depth=max_depth, serialization=serialization,
                                timeout=timeout, unique_context=unique_context,
                                execution_context_id=execution_context_id)

    async def execute_async_script(self, script: str, *args, max_depth: int = 2, serialization: str = None,
                                timeout: float = 2, execution_context_id: str = None, unique_context: bool = None):
        return await self.__exec_async__(script, *args, max_depth=max_depth, serialization=serialization,
                                        timeout=timeout, unique_context=unique_context,
                                        execution_context_id=execution_context_id)
    
    def __repr__(self):
        return (f'{self.__class__.__name__}("{self._class_name}", '
                f'obj_id={self.__obj_id__}, node_id="{self._node_id}", backend_node_id={self._backend_node_id}, '
                f'context_id={self.__context_id__})')

    def __eq__(self, other):
        if isinstance(other, WebElement):
            if other.__target__ == self.__target__:
                if other.__obj_id__ and self.__obj_id__:
                    return other.__obj_id__.split(".")[0] == self.__obj_id__.split(".")[0]
                elif other._backend_node_id == self._backend_node_id:
                    return True
                elif other._node_id == self._node_id:
                    return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
