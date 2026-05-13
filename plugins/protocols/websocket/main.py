"""
main.py – WebSocket protocol plugin for iotta.

Connects to any device that exposes a WebSocket endpoint.
Supports send, subscribe, and auto-reconnect via iotta's reconnect loop.

Uses websockets (asyncio-native) for the connection.
"""

import asyncio
import json
import time
from typing import Callable

import websockets
from websockets.exceptions import ConnectionClosed

from src.logging import get_logger
from src.plugins.base_protocol import BaseProtocol

logger = get_logger("ws")

CONNECT_TIMEOUT = 10


class WebSocketProtocol(BaseProtocol):
    protocol_name = "ws"

    def __init__(self, config: dict):
        super().__init__(config)
        self._ws = None
        self._connected = False
        self._callback: Callable[[dict], None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._listener_task: asyncio.Task | None = None

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        url = self.config.get("url")
        if not url:
            logger.error("No 'url' specified in WebSocket config")
            return False

        headers = self.config.get("headers", {})

        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                self._ws = await websockets.connect(url, additional_headers=headers)
            self._connected = True
            self._loop = asyncio.get_event_loop()
            self._listener_task = asyncio.create_task(self._listen())
            logger.info(f"Connected to {url}")
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    # ── Listener ──────────────────────────────────────────────────────────────

    async def _listen(self) -> None:
        """Background task that reads incoming messages and fires the callback."""
        try:
            async for raw in self._ws:
                if not self._callback:
                    continue
                try:
                    data = json.loads(raw) if isinstance(raw, str) else {"raw": raw.hex()}
                except Exception:
                    data = {"raw": raw}
                if self._loop:
                    self._loop.call_soon_threadsafe(self._callback, data)
        except ConnectionClosed:
            logger.info("Connection closed by remote")
            self._connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Listener error: {e}")
            self._connected = False

    # ── Actions ───────────────────────────────────────────────────────────────

    async def execute_action(self, action: str, payload: dict) -> dict:
        if not self._ws or not self._connected:
            return {"success": False, "error": "Not connected"}

        message = payload.get("payload", payload)

        try:
            if isinstance(message, dict):
                await self._ws.send(json.dumps(message))
            else:
                await self._ws.send(str(message))
            return {"success": True}
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Subscribe ─────────────────────────────────────────────────────────────

    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._callback = callback

    # ── Ping ──────────────────────────────────────────────────────────────────

    async def ping(self) -> dict:
        if not self._ws or not self._connected:
            return {"ok": False, "latency_ms": None, "error": "Not connected"}

        t0 = time.monotonic()
        try:
            pong = await self._ws.ping()
            await asyncio.wait_for(pong, timeout=5)
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            return {"ok": True, "latency_ms": latency_ms, "error": None}
        except Exception as e:
            self._connected = False
            return {"ok": False, "latency_ms": None, "error": str(e)}
