"""
base_protocol.py – Abstract Base Class for all protocol plugins.

Every protocol plugin (MQTT, FTP, HTTP, WebSocket, ...) must implement this interface.
The loader uses this to validate and register protocol plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseProtocol(ABC):
    """
    Abstract base class for all iotta protocol plugins.

    A protocol plugin knows how to:
    - connect/disconnect to a device using a specific protocol
    - execute actions (publish, write, POST, ...)
    - subscribe to status updates and emit them via callback
    """

    # Must be set in every protocol plugin
    protocol_name: str = ""

    def __init__(self, config: dict):
        """
        config: resolved credentials from the device instance
        e.g. { "host": "192.168.1.42", "port": 8883, "password": "abc123" }
        """
        self.config = config

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the device. Returns True on success."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly close the connection."""
        ...

    @abstractmethod
    async def execute_action(self, action: str, payload: dict) -> dict:
        """
        Execute a named action on the device.
        action:  name of the action as defined in plugin.yaml
        payload: parameters for the action
        returns: result dict
        """
        ...

    @abstractmethod
    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        """
        Subscribe to status updates from the device.
        callback: called with status dict whenever the device sends an update
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Override in subclass if connection state is trackable."""
        return False

    def __repr__(self) -> str:
        return f"<Protocol: {self.protocol_name}>"