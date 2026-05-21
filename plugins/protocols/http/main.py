"""
main.py – HTTP protocol plugin for iotta.

Supports GET, POST, PUT, PATCH, DELETE, HEAD with optional auth (bearer, basic, api-key).
Uses httpx for async HTTP requests.
"""

from typing import Any, Callable

import httpx
from src.logging import get_logger
from src.plugins.base_protocol import BaseProtocol

logger = get_logger("http")


class HTTPProtocol(BaseProtocol):
    protocol_name = "http"

    def __init__(self, config: dict):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(
                base_url=self.config.get("base_url", ""),
                timeout=self.config.get("timeout", 10),
                headers=self._build_headers(),
                verify=self.config.get("verify_ssl", True),
            )
            logger.info(f"Client ready for {self.config.get('base_url')}")
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    # ── Actions ───────────────────────────────────────────────────────────────

    async def execute_action(self, action: str, payload: dict) -> dict:
        if not self._client:
            return {"success": False, "error": "Not connected"}

        method = action.upper()
        path = payload.get("path", "/")
        body = payload.get("body", None)
        params = payload.get("params", None)

        try:
            if method == "HEAD":
                response = await self._client.head(path, params=params)
                return {
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }

            response = await self._client.request(
                method=method,
                url=path,
                json=body,
                params=params,
            )
            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "body": self._parse_response(response),
            }
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Subscribe ─────────────────────────────────────────────────────────────

    async def subscribe(self, callback: Callable[[dict], None]) -> None:
        logger.debug("HTTP protocol does not support push subscriptions")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_headers(self) -> dict:
        headers = {}
        auth = self.config.get("auth", {})
        auth_type = auth.get("type", "none")

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth.get('token', '')}"
        elif auth_type == "basic":
            import base64
            credentials = base64.b64encode(
                f"{auth.get('username', '')}:{auth.get('password', '')}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth_type == "api-key":
            headers[auth.get("header", "X-API-Key")] = auth.get("key", "")

        return headers

    def _parse_response(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text