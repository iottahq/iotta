"""
main.py – FTP/FTPS protocol plugin for iotta.

Uses aioftp for async-native FTP/FTPS support.
Supports plain FTP, explicit FTPS (STARTTLS), and implicit FTPS (port 990).

Connection strategy: connect-per-operation.
Every action opens a fresh connection, executes, then closes it.
"""

import asyncio
import ssl
import time
from typing import Callable

import aioftp
from src.logging import get_logger
from src.plugins.base_protocol import BaseProtocol

logger = get_logger("ftp")

CONNECT_TIMEOUT = 8
OP_TIMEOUT = 120


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class FTPProtocol(BaseProtocol):
    protocol_name = "ftp"

    def __init__(self, config: dict):
        super().__init__(config)

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Probe once at startup to verify reachability."""
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT + 2):
                async with self._open() as client:
                    pass
            logger.info(f"Connected to {self.config.get('host')}")
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        pass

    @property
    def is_connected(self) -> bool:
        return True

    # ── Actions ───────────────────────────────────────────────────────────────

    async def execute_action(self, action: str, payload: dict) -> dict:
        try:
            async with asyncio.timeout(OP_TIMEOUT):
                return await self._run_action(action, payload)
        except TimeoutError:
            return {"success": False, "error": "FTP operation timeout"}
        except Exception as e:
            logger.error(f"Action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_action(self, action: str, payload: dict) -> dict:
        path = payload.get("path", "/")

        async with self._open() as client:
            if action == "list":
                files = []
                async for item_path, info in client.list(path):
                    name = item_path.name
                    if name in (".", ".."):
                        continue
                    files.append(
                        {
                            "name": name,
                            "type": info.get("type", "file"),
                            "size": int(info.get("size", 0)),
                            "date": info.get("modify", ""),
                        }
                    )
                return {"success": True, "files": files, "path": path}

            elif action == "upload":
                data = payload.get("data")
                if not data:
                    return {"success": False, "error": "No data provided"}
                async with client.upload_stream(path) as stream:
                    await stream.write(data)
                return {"success": True, "path": path}

            elif action == "download":
                buf = bytearray()
                async with client.download_stream(path) as stream:
                    async for chunk in stream.iter_by_block():
                        buf.extend(chunk)
                return {"success": True, "data": bytes(buf)}

            elif action == "delete":
                await client.remove(path)
                return {"success": True, "path": path}

            elif action == "mkdir":
                await client.make_directory(path)
                return {"success": True, "path": path}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

    # ── Ping ──────────────────────────────────────────────────────────────────

    async def ping(self) -> dict:
        t0 = time.monotonic()
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT + 2):
                async with self._open() as client:
                    pass
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            return {"ok": True, "latency_ms": latency_ms, "error": None}
        except Exception as e:
            return {"ok": False, "latency_ms": None, "error": str(e)}

    # ── Subscribe ─────────────────────────────────────────────────────────────

    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        """FTP is stateless – no push subscriptions possible."""

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _open(self) -> aioftp.Client:
        host = self.config.get("host")
        port = int(self.config.get("port", 21))
        username = self.config.get("username", "anonymous")
        password = self.config.get("password", "")
        tls = self.config.get("tls", "none")

        ssl_ctx = _make_ssl_context() if tls in ("implicit", "explicit") else None

        return aioftp.Client.context(
            host,
            port=port,
            user=username,
            password=password,
            ssl=ssl_ctx,
            connection_timeout=CONNECT_TIMEOUT,
        )

    def _parse_date(self, info: dict) -> str:
        return info.get("modify", "")
