"""
main.py – FTP/FTPS protocol plugin for iotta.

Supports plain FTP, explicit FTPS (STARTTLS), and implicit FTPS (port 990).
Bambu Lab printers use implicit FTPS on port 990 with a quirky TLS close.
"""

import asyncio
import ftplib
import io
import logging
import socket
import ssl
from typing import Callable

from src.plugins.base_protocol import BaseProtocol

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 8
OP_TIMEOUT      = 120


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """
    Implicit FTPS – TLS is active immediately on connect (no STARTTLS).
    Required for devices like Bambu Lab printers that use port 990.
    """

    def connect(self, host: str, port: int = 990, timeout: int = CONNECT_TIMEOUT, **kwargs):
        self.host    = host
        self.port    = port
        self.timeout = timeout

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(timeout)

        self.sock    = ctx.wrap_socket(sock, server_hostname=host)
        self.af      = self.sock.family
        self.file    = self.sock.makefile("r", encoding="utf-8", errors="replace")
        self.welcome = self.getresp()

        return self.welcome

    def quit_safe(self):
        """
        Some devices (e.g. Bambu Lab) don't close TLS cleanly.
        Force-close the socket instead of waiting for a proper QUIT response.
        """
        try:
            self.voidcmd("QUIT")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


class FTPProtocol(BaseProtocol):
    protocol_name = "ftp"

    def __init__(self, config: dict):
        super().__init__(config)
        self._ftp: ftplib.FTP | None = None

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self._connect_sync),
                timeout=CONNECT_TIMEOUT + 2,
            )
            logger.info(f"FTP connected to {self.config.get('host')}")
            return True
        except asyncio.TimeoutError:
            logger.error("FTP connection timeout")
            return False
        except Exception as e:
            logger.error(f"FTP connect failed: {e}")
            return False

    def _connect_sync(self):
        host     = self.config.get("host")
        port     = int(self.config.get("port", 21))
        username = self.config.get("username", "anonymous")
        password = self.config.get("password", "")
        tls      = self.config.get("tls", "none")  # none | implicit | explicit

        if tls == "implicit":
            ftp = ImplicitFTP_TLS()
            ftp.connect(host, port, timeout=CONNECT_TIMEOUT)
            ftp.login(username, password)
            ftp.prot_p()
            ftp.set_pasv(True)
            ftp.sock.settimeout(OP_TIMEOUT)
        elif tls == "explicit":
            ftp = ftplib.FTP_TLS()
            ftp.connect(host, port, timeout=CONNECT_TIMEOUT)
            ftp.login(username, password)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=CONNECT_TIMEOUT)
            ftp.login(username, password)

        self._ftp = ftp

    async def disconnect(self) -> None:
        if self._ftp:
            try:
                if isinstance(self._ftp, ImplicitFTP_TLS):
                    self._ftp.quit_safe()
                else:
                    self._ftp.quit()
            except Exception:
                pass
            self._ftp = None

    @property
    def is_connected(self) -> bool:
        return self._ftp is not None

    # ── Actions ───────────────────────────────────────────────────────────────

    async def execute_action(self, action: str, payload: dict) -> dict:
        if not self._ftp:
            return {"success": False, "error": "Not connected"}

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._execute_sync, action, payload),
                timeout=OP_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "FTP operation timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_sync(self, action: str, payload: dict) -> dict:
        path = payload.get("path", "/")

        if action == "list":
            lines = []
            self._ftp.retrlines(f"LIST {path}", lines.append)
            return {"success": True, "files": self._parse_list(lines), "path": path}

        elif action == "upload":
            local_data = payload.get("data")  # bytes
            if not local_data:
                return {"success": False, "error": "No data provided"}
            self._ftp.storbinary(f"STOR {path}", io.BytesIO(local_data))
            return {"success": True, "path": path}

        elif action == "download":
            buf = io.BytesIO()
            self._ftp.retrbinary(f"RETR {path}", buf.write)
            return {"success": True, "data": buf.getvalue()}

        elif action == "delete":
            self._ftp.delete(path)
            return {"success": True, "path": path}

        elif action == "mkdir":
            self._ftp.mkd(path)
            return {"success": True, "path": path}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    # ── Status ────────────────────────────────────────────────────────────────

    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        """FTP is stateless – no push subscriptions possible."""
        logger.debug("FTP protocol does not support push subscriptions")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_list(self, lines: list[str]) -> list[dict]:
        files = []
        for line in lines:
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            name = parts[8]
            if name in (".", ".."):
                continue
            files.append({
                "name":  name,
                "type":  "dir" if parts[0].startswith("d") else "file",
                "size":  int(parts[4]) if parts[4].isdigit() else 0,
                "date":  f"{parts[5]} {parts[6]} {parts[7]}",
            })
        return files