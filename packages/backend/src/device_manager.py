"""
device_manager.py – Creates and mounts a FastAPI sub-app per registered device.

Each device gets its own isolated FastAPI app with:
- POST /devices/{id}/send/{action}
- GET  /devices/{id}/request/{action}
- WS   /devices/{id}/stream/{action}
- GET  /devices/{id}/docs
- GET  /devices/{id}/openapi.json

Protocol connections are persistent per device – no connect/disconnect per request.
"""

import asyncio
from uuid import UUID

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.logging import get_logger
from src.models.credential import Credential
from src.models.device import Device
from src.plugins.base_protocol import BaseProtocol
from src.plugins.loader import plugin_loader

logger = get_logger("core")


class DeviceConnections:
    """Holds persistent protocol connections for a single device."""

    def __init__(self):
        self._connections: dict[str, BaseProtocol] = {}
        self._configs: dict[str, tuple] = {}

    async def connect(
        self, protocol_id: str, protocol_class: type[BaseProtocol], config: dict
    ) -> BaseProtocol | None:
        if protocol_id in self._connections:
            return self._connections[protocol_id]

        self._configs[protocol_id] = (protocol_class, config)

        protocol = protocol_class(config)
        connected = await protocol.connect()
        if connected:
            self._connections[protocol_id] = protocol
            return protocol

        logger.error(f"Failed to connect protocol '{protocol_id}'")
        return None

    def get(self, protocol_id: str) -> BaseProtocol | None:
        return self._connections.get(protocol_id)

    async def reconnect(
        self, protocol_id: str, protocol_class=None, config: dict = None
    ) -> bool:
        if protocol_class is None or config is None:
            if protocol_id not in self._configs:
                return False
            protocol_class, config = self._configs[protocol_id]

        if protocol_id in self._connections:
            try:
                await self._connections[protocol_id].disconnect()
            except Exception:
                pass
            del self._connections[protocol_id]

        protocol = protocol_class(config)
        connected = await protocol.connect()
        if connected:
            self._connections[protocol_id] = protocol
            return True
        return False

    async def disconnect_all(self) -> None:
        for protocol_id, protocol in self._connections.items():
            try:
                await protocol.disconnect()
                logger.info(f"Disconnected protocol '{protocol_id}'")
            except Exception as e:
                logger.error(f"Error disconnecting '{protocol_id}': {e}")
        self._connections.clear()


class DeviceManager:
    def __init__(self, root_app: FastAPI):
        self._root_app = root_app
        self._apps: dict[str, FastAPI] = {}
        self._connections: dict[str, DeviceConnections] = {}
        self._plugin_ids: dict[str, str] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def mount_all(self) -> None:
        db: Session = SessionLocal()
        try:
            devices = db.query(Device).all()
            for device in devices:
                await self._mount_device(device, db)
            logger.info(f"Mounted {len(self._apps)} device app(s)")
        finally:
            db.close()

        asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Background task that checks and reconnects dead protocol connections every 30s."""
        while True:
            await asyncio.sleep(30)
            for device_id, connections in self._connections.items():
                plugin_id = self._plugin_ids.get(device_id, "device")
                dlog = get_logger(plugin_id, device_id=device_id)

                for protocol_id in list(connections._configs.keys()):
                    protocol = connections._connections.get(protocol_id)
                    if protocol:
                        result = await protocol.ping()
                        is_down = not result.get("ok")
                    else:
                        is_down = True

                    if is_down:
                        dlog.warning(
                            f"Protocol '{protocol_id}' is down – reconnecting..."
                        )
                        ok = await connections.reconnect(protocol_id)
                        if ok:
                            dlog.info(f"Protocol '{protocol_id}' reconnected")
                        else:
                            dlog.error(f"Protocol '{protocol_id}' reconnect failed")

    async def mount(self, device_id: UUID) -> None:
        db: Session = SessionLocal()
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device:
                await self._mount_device(device, db)
        finally:
            db.close()

    async def unmount(self, device_id: UUID) -> None:
        key = str(device_id)
        plugin_id = self._plugin_ids.get(key, "device")
        dlog = get_logger(plugin_id, device_id=key)

        if key in self._connections:
            await self._connections[key].disconnect_all()
            del self._connections[key]
        if key in self._apps:
            mount_path = f"/devices/{key}"
            self._root_app.routes = [
                r
                for r in self._root_app.routes
                if not (hasattr(r, "path") and r.path == mount_path)
            ]
            del self._apps[key]
            self._plugin_ids.pop(key, None)
            dlog.info("Unmounted")

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _mount_device(self, device: Device, db: Session) -> None:
        device_id = str(device.id)
        plugin_id = device.plugin_id
        dlog = get_logger(plugin_id, device_id=device_id)

        plugin = plugin_loader.get_device(plugin_id)
        if not plugin:
            dlog.warning(f"Unknown plugin '{plugin_id}' – skipping")
            return

        config = plugin.get("_config", {})
        if not config:
            dlog.warning("No config – skipping")
            return

        credential = (
            db.query(Credential).filter(Credential.id == device.credential_id).first()
        )
        if not credential:
            dlog.warning("No credentials – skipping")
            return

        resolved_protocols = {
            proto_id: _resolve(proto_config, credential.data)
            for proto_id, proto_config in config.get("protocols", {}).items()
        }

        connections = DeviceConnections()
        for proto_id, proto_config in resolved_protocols.items():
            protocol_class = plugin_loader.get_protocol_class(proto_id)
            if protocol_class:
                await connections.connect(proto_id, protocol_class, proto_config)

        self._connections[device_id] = connections
        self._plugin_ids[device_id] = plugin_id

        sub_app = self._build_sub_app(
            device, config, credential.data, connections, plugin
        )
        mount_path = f"/devices/{device_id}"
        self._root_app.mount(mount_path, sub_app)
        self._apps[device_id] = sub_app

        dlog.info(f"Mounted: {device.name} at {mount_path}")

    def _build_sub_app(
        self, device, config, credentials, connections, plugin
    ) -> FastAPI:
        meta = {k: v for k, v in plugin.items() if not k.startswith("_")}

        sub_app = FastAPI(
            title=device.name,
            description=meta.get("description", ""),
            version=meta.get("version", "1.0.0"),
        )

        actions = config.get("actions", {})

        for action_name, action_def in actions.get("send", {}).items():
            self._register_send(
                sub_app, action_name, action_def, credentials, connections
            )

        for action_name, action_def in actions.get("request", {}).items():
            self._register_request(
                sub_app, action_name, action_def, credentials, connections
            )

        for action_name, action_def in actions.get("stream", {}).items():
            self._register_stream(
                sub_app, action_name, action_def, credentials, connections
            )

        self._register_ping(sub_app, connections)

        return sub_app

    # ── Route registration ────────────────────────────────────────────────────

    def _register_ping(self, app: FastAPI, connections: DeviceConnections):
        @app.get("/ping", summary="Ping device", tags=["device"])
        async def ping():
            results = {}
            all_ok = True

            for protocol_id in connections._configs.keys():
                protocol = connections._connections.get(protocol_id)
                result = (
                    await protocol.ping()
                    if protocol
                    else {"ok": False, "latency_ms": None, "error": "Not connected"}
                )
                results[protocol_id] = result
                if not result.get("ok"):
                    all_ok = False

            if not results:
                all_ok = False

            return {"online": all_ok, "protocols": results}

    def _register_send(self, app, name, action, credentials, connections):
        from fastapi import File, Form, UploadFile

        label = action.get("label", name)
        example = action.get("example", {})
        inputs = action.get("input", {})
        has_file_upload = any(v.get("type") == "bytes" for v in inputs.values())

        if has_file_upload:

            @app.post(f"/send/{name}", summary=label, tags=["send"])
            async def send_action(file: UploadFile = File(...), path: str = Form(...)):
                protocol_id = action.get("protocol")
                protocol = connections.get(protocol_id)
                if not protocol:
                    return JSONResponse(
                        {
                            "success": False,
                            "error": f"Protocol '{protocol_id}' not connected",
                        },
                        status_code=503,
                    )
                if not protocol.is_connected:
                    return JSONResponse(
                        {"success": False, "error": "Device not connected"},
                        status_code=503,
                    )
                data = await file.read()
                return await protocol.execute_action(
                    action.get("method", name), {"path": path, "data": data}
                )
        else:

            @app.post(
                f"/send/{name}",
                summary=label,
                tags=["send"],
                openapi_extra={
                    "requestBody": {
                        "content": {"application/json": {"example": example}}
                    }
                },
            )
            async def send_action(body: dict = {}):
                protocol_id = action.get("protocol")
                protocol = connections.get(protocol_id)
                if not protocol:
                    return JSONResponse(
                        {
                            "success": False,
                            "error": f"Protocol '{protocol_id}' not connected",
                        },
                        status_code=503,
                    )
                if not protocol.is_connected:
                    return JSONResponse(
                        {"success": False, "error": "Device not connected"},
                        status_code=503,
                    )
                resolved_payload = _resolve(
                    action.get("payload", {}), {**credentials, **body}
                )
                return await protocol.execute_action(
                    action.get("method", name),
                    {
                        "topic": _resolve_str(action.get("topic", ""), credentials),
                        "payload": resolved_payload,
                    },
                )

        send_action.__name__ = f"send_{name}"

    def _register_request(self, app, name, action, credentials, connections):
        label = action.get("label", name)
        default_path = action.get("input", {}).get("path", {}).get("default")

        @app.get(f"/request/{name}", summary=label, tags=["request"])
        async def request_action(
            path: str = Query(default=None, description="Directory or file path"),
        ):
            protocol_id = action.get("protocol")
            if protocol_id == "camera":
                return JSONResponse(
                    {"success": False, "error": "Camera not yet implemented"},
                    status_code=501,
                )
            protocol = connections.get(protocol_id)
            if not protocol:
                return JSONResponse(
                    {
                        "success": False,
                        "error": f"Protocol '{protocol_id}' not connected",
                    },
                    status_code=503,
                )
            return await protocol.execute_action(
                action.get("method", name),
                {"path": path or default_path or "/"},
            )

        request_action.__name__ = f"request_{name}"

    def _register_stream(self, app, name, action, credentials, connections):
        @app.websocket(f"/stream/{name}")
        async def stream_action(websocket: WebSocket):
            await websocket.accept()
            protocol_id = action.get("protocol")
            protocol = connections.get(protocol_id)
            if not protocol:
                await websocket.close(code=1008)
                return
            try:

                async def on_message(data: dict):
                    try:
                        await websocket.send_json(data)
                    except Exception:
                        pass

                await protocol.subscribe(on_message)
                while True:
                    try:
                        await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"ping": True})
                    except WebSocketDisconnect:
                        break
            finally:
                await protocol.subscribe(lambda _: None)

        stream_action.__name__ = f"stream_{name}"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_str(value: str, context: dict) -> str:
    for k, v in context.items():
        value = value.replace(f"{{{k}}}", str(v))
    return value


def _resolve(obj, context: dict):
    if isinstance(obj, str):
        return _resolve_str(obj, context)
    if isinstance(obj, dict):
        return {k: _resolve(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(i, context) for i in obj]
    return obj


# Singleton
device_manager: DeviceManager | None = None


def init_device_manager(app: FastAPI) -> DeviceManager:
    global device_manager
    device_manager = DeviceManager(app)
    return device_manager
