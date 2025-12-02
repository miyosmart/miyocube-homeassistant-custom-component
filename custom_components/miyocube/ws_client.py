import asyncio
import json
import logging
import websockets

_LOGGER = logging.getLogger(__name__)

class WSClient:
    def __init__(self, url, on_message, api_key, reconnect_interval=15, timeout=60):
        self._url = url
        self._on_message = on_message
        self._api_key = api_key
        self._reconnect_interval = reconnect_interval
        self._timeout = timeout
        self._ws = None
        self._task = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the background connection task."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._runner())

    async def stop(self):
        """Stops and disconnects."""
        self._stop_event.set()
        if self._ws:
            await self._ws.close()
        if self._task:
            await self._task

    async def send(self, data: dict):
        """Sends data through the websocket."""
        if self._ws:
            try:
                data["id"] = 1
                data["apiKey"] = self._api_key                
                await self._ws.send(json.dumps(data))
            except Exception as e:
                _LOGGER.error("WS send error: %s", e)

    async def _runner(self):
        """Main loop connecting and reconnecting."""
        while not self._stop_event.is_set():
            try:
                _LOGGER.info("Connecting to WebSocket: %s", self._url)
                async with websockets.connect(self._url) as ws:
                    self._ws = ws
                    _LOGGER.info("WebSocket connected")
                    await self._listen()
            except Exception as e:
                _LOGGER.error("WS connection error: %s", e)

            if not self._stop_event.is_set():
                _LOGGER.warning("WS disconnected, retrying in %s seconds...", self._reconnect_interval)
                await asyncio.sleep(self._reconnect_interval)

    async def _listen(self):
        """Listen for incoming messages with a timeout."""
        while not self._stop_event.is_set():
            try:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
            except asyncio.TimeoutError:
                _LOGGER.warning("WS timeout, sending ping")
                try:
                    await self._ws.ping()
                except:
                    break
                continue
            except Exception as e:
                _LOGGER.error("WS listen error: %s", e)
                break

            try:
                data = json.loads(msg)
            except:
                _LOGGER.error("Bad WS message: %s", msg)
                continue

            await self._on_message(data)
