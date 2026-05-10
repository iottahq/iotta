"""
plugin.py – MQTT protocol plugin for iotta.

Supports TLS (insecure), persistent connection, publish actions,
and subscribe to status topics with callback emission.
Uses paho-mqtt for MQTT communication.
"""

import asyncio
import json
import logging
import ssl
from typing import Callable

import paho.mqtt.client as mqtt

from src.plugins.base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


class MQTTProtocol(BaseProtocol):
    protocol_name = "mqtt"

    def __init__(self, config: dict):
        super().__init__(config)
        self._client: mqtt.Client | None = None
        self._connected = False
        self._callback: Callable[[dict], None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # Connection

    async def connect(self) -> bool:
        try:
            self._loop = asyncio.get_event_loop()
            self._client = self._build_client()

            host = self.config.get("host")
            port = int(self.config.get("port", 8883))

            self._client.connect_async(host, port, keepalive=30)
            self._client.loop_start()

            # Wait up to 10 seconds for connection
            for _ in range(100):
                if self._connected:
                    return True
                await asyncio.sleep(0.1)

            logger.error(f"MQTT connection timeout to {host}:{port}")
            return False

        except Exception as e:
            logger.error(f"MQTT connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._client.loop_stop)
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # Actions

    async def execute_action(self, action: str, payload: dict) -> dict:
        if not self._client or not self._connected:
            return {"success": False, "error": "Not connected"}

        topic = payload.get("topic")
        message = payload.get("payload", {})

        if not topic:
            return {"success": False, "error": "No topic specified"}

        try:
            result = self._client.publish(
                topic,
                json.dumps(message),
                qos=payload.get("qos", 1),
            )
            await asyncio.sleep(0.5)
            return {"success": result.rc == mqtt.MQTT_ERR_SUCCESS}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Status

    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._callback = callback
        topics = self.config.get("subscribe_topics", [])
        if self._client and self._connected and topics:
            for topic in topics:
                self._client.subscribe(topic)
                logger.info(f"MQTT subscribed to: {topic}")

    # Client builder

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        username = self.config.get("username")
        password = self.config.get("password")
        if username:
            client.username_pw_set(username, password)

        if self.config.get("tls", False):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)
            client.tls_insecure_set(True)

        client.on_connect    = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message    = self._on_message

        return client

    # Callbacks

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info(f"MQTT connected to {self.config.get('host')}")
            # Re-subscribe after reconnect
            for topic in self.config.get("subscribe_topics", []):
                client.subscribe(topic)
        else:
            logger.warning(f"MQTT connection refused, rc={rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None, reasoncode=None):
        self._connected = False
        logger.info(f"MQTT disconnected (rc={rc})")

    def _on_message(self, client, userdata, msg):
        if not self._callback:
            return
        try:
            data = json.loads(msg.payload.decode())
        except Exception:
            return
        if self._loop:
            self._loop.call_soon_threadsafe(self._callback, data)