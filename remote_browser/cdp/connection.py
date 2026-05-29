from pyee import EventEmitter
import asyncio
import websockets
import json
import logging
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from ..listener import lister_event

# Cấu hình logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

class CDPConnection(EventEmitter):
    def __init__(self, url, loop, uuid: str, target=None):
        super().__init__()
        self.url = url
        self.connection = None
        self.message_id = 0
        self.pending_responses = {}
        self._loop: asyncio.AbstractEventLoop = loop
        self._connected = False
        self.page_loaded = False
        self.__target__ = target
        self.__uuid__ = uuid
        self.message_queue = asyncio.Queue()  # Dùng queue để quản lý message

    async def connect(self):
        try:
            self.connection = await websockets.connect(self.url, max_size=2**20 * 10)
            self._connected = True
            self._loop.create_task(self._recv_loop())  # Nhận message
            self._loop.create_task(self._process_messages())  # Xử lý message từ queue
            self.emit("connect", f"Connected to {self.url}")
            self.on('Page.frameStartedLoading', self._start_load)
            self.on('Page.frameDetached', self._on_loaded)
            self._loop.set_debug(False)
            logger.info(f"Connected to WebSocket at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")

    def _start_load(self, _):
        self.page_loaded = False

    def _on_loaded(self, _):
        self.page_loaded = True

    async def _recv_loop(self):
        try:
            while self._connected:
                try:
                    message = await asyncio.wait_for(self.connection.recv(), timeout=1)
                    await self.message_queue.put(message)  # Thay vì xử lý ngay, thêm vào queue
                except asyncio.TimeoutError:
                    pass
                except ConnectionClosedOK:
                    break
                except ConnectionClosedError as e:
                    break
        except Exception as e:
            logger.error(f"Error in recv loop: {e}")
        finally:
            self._connected = False
            await self.cleanup_connection()

    async def _process_messages(self):
        async def worker():
            while self._connected or not self.message_queue.empty():
                try:
                    message = await self.message_queue.get()
                    await self.handle_message(message)
                except Exception as e:
                    logger.error(f"Error while processing message: {e}")

        workers = [asyncio.create_task(worker()) for _ in range(5)]
        await asyncio.gather(*workers)


    async def cleanup_connection(self):
        try:
            if self.connection and not self.connection.closed:
                await self.connection.close()
                logger.info("WebSocket connection cleaned up.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def handle_message(self, message):
        try:
            data = json.loads(message)
            lister_event.emit(f'cdp_event_{self.__uuid__}', data)
            if "id" in data and data["id"] in self.pending_responses:
                self.pending_responses[data["id"]].set_result(data)
                del self.pending_responses[data["id"]]
            elif "method" in data:
                self.emit(data["method"], data.get("params", {}))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")

    async def send(self, method, params=None, sessionId: str = None, timeout=1):
        self.message_id += 1
        message_id = self.message_id
        message = {
            "id": message_id,
            "method": method,
            "params": params or {}
        }
        if sessionId:
            message.update({'sessionId': sessionId})

        if not self.connection or not self.connection.open:
            logger.warning("Connection is closed. Cannot send message.")
            return

        await self.connection.send(json.dumps(message))
        future = self._loop.create_future()
        self.pending_responses[message_id] = future

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to method {method}")
        finally:
            self.pending_responses.pop(message_id, None)

    async def wait_for(self, event_name, timeout=5):
        future = self._loop.create_future()

        def handler(event_data):
            if event_name in event_data:
                future.set_result(event_data)

        self.on(event_name, handler)

        try:
            logger.info(f"Waiting for event: {event_name}")
            await asyncio.wait_for(future, timeout)
            return future.result()
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while waiting for event: {event_name}")
            return None
        finally:
            self.remove_listener(event_name, handler)

    async def close(self):
        if self.connection:
            await self.connection.close()
            self._connected = False
            self.emit("close", "Connection closed")
            logger.info("WebSocket connection closed.")
        return
