"""
device_manager.py – Creates and mounts a FastAPI sub-app per registered device.

Each device gets its own isolated FastAPI app with:
- POST /devices/{id}/action/{name}
- GET  /devices/{id}/ping
- GET  /devices/{id}/docs
- GET  /devices/{id}/openapi.json

Protocol connections are persistent per device.
Access is enforced per group token.
"""

import asyncio
from uuid import UUID

from fastapi import Depends, FastAPI, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from src.crypto import decrypt
from src.database import SessionLocal
from src.logging import get_logger
from src.models.credential import Credential
from src.models.device import Device
from src.models.group import Group
from src.permissions import require_device_access
from src.plugins.base_protocol import BaseProtocol
from src.plugins.loader import plugin_loader

logger = get_logger("core")

_sub_app_security = HTTPBearer()


def _make_auth_dependency(device_group_id: UUID | None):
    import os
    import secrets

    from src.crypto import decrypt

    ADMIN_TOKEN = os.getenv("IOTTA_ADMIN_TOKEN", "")

    async def check_auth(
        credentials: HTTPAuthorizationCredentials = Security(_sub_app_security),
    ):
        token = credentials.credentials


        db: Session = SessionLocal()
        try:
            from src.models.user import User
            from src.routers.auth import decode_token

            user_id = decode_token(token)
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return
        except Exception:
            pass
        finally:
            db.close()

        if ADMIN_TOKEN and secrets.compare_digest(token.encode(), ADMIN_TOKEN.encode()):
            return

        db: Session = SessionLocal()
        try:
            groups = db.query(Group).all()
            for group in groups:
                try:
                    decrypted = decrypt(group.token)
                except Exception:
                    continue
                if secrets.compare_digest(token.encode(), decrypted.encode()):
                    require_device_access(device_group_id, group)
                    return
        finally:
            db.close()

        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return check_auth


def _resolve_plugin_config(plugin: dict) -> tuple[dict, dict]:
    """
    Returns (protocols_config, actions) from a device plugin.

    Supports both the new split format (_protocols / _actions)
    and the legacy single-file format (_config).
    """
    # New split format
    if "_protocols" in plugin or "_actions" in plugin:
        return (
            plugin.get("_protocols") or {},
            plugin.get("_actions") or {},
        )

    # Legacy single-file format
    config = plugin.get("_config") or {}
    return (
        config.get("protocols") or {},
        config.get("actions") or {},
    )


class DeviceConnections:
    def __init__(self):
        self._connections: dict[str, BaseProtocol] = {}
        self._configs: dict[str, tuple] = {}

    async def connect(self, protocol_id, protocol_class, config):
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

    def get(self, protocol_id):
        return self._connections.get(protocol_id)

    async def reconnect(self, protocol_id, protocol_class=None, config=None):
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

    async def disconnect_all(self):
        async def _safe(pid, proto):
            try:
                await asyncio.wait_for(proto.disconnect(), timeout=5.0)
            except Exception as e:
                logger.error(f"Error disconnecting '{pid}': {e}")

        await asyncio.gather(*[_safe(pid, p) for pid, p in list(self._connections.items())])
        self._connections.clear()


class DeviceManager:
    def __init__(self, root_app: FastAPI):
        self._root_app = root_app
        self._apps: dict[str, FastAPI] = {}
        self._connections: dict[str, DeviceConnections] = {}
        self._plugin_ids: dict[str, str] = {}
        self._deleting: set[str] = set()

    async def mount_all(self):
        db: Session = SessionLocal()
        try:
            devices = db.query(Device).all()
            for device in devices:
                await self._mount_device(device, db)
            logger.info(f"Mounted {len(self._apps)} device app(s)")
        finally:
            db.close()
        asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        while True:
            await asyncio.sleep(30)
            for device_id, connections in list(self._connections.items()):
                if device_id in self._deleting:
                    continue
                plugin_id = self._plugin_ids.get(device_id, "device")
                dlog = get_logger(plugin_id, device_id=device_id)
                for protocol_id in list(connections._configs.keys()):
                    protocol = connections._connections.get(protocol_id)
                    is_down = (
                        not (await protocol.ping()).get("ok") if protocol else True
                    )
                    if is_down:
                        dlog.warning(
                            f"Protocol '{protocol_id}' is down – reconnecting..."
                        )
                        ok = await connections.reconnect(protocol_id)
                        if ok:
                            dlog.info(f"Protocol '{protocol_id}' reconnected")
                        else:
                            dlog.error(f"Protocol '{protocol_id}' reconnect failed")

    async def mount(self, device_id: UUID):
        db: Session = SessionLocal()
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device:
                await self._mount_device(device, db)
        finally:
            db.close()

    async def unmount(self, device_id: UUID):
        key = str(device_id)
        self._deleting.add(key)
        plugin_id = self._plugin_ids.get(key, "device")
        dlog = get_logger(plugin_id, device_id=key)
        if key in self._connections:
            await self._connections[key].disconnect_all()
            del self._connections[key]
        if key in self._apps:
            mount_path = f"/devices/{key}"
            self._root_app.router.routes = [
                r
                for r in self._root_app.router.routes
                if not (hasattr(r, "path") and r.path == mount_path)
            ]
            del self._apps[key]
            self._plugin_ids.pop(key, None)
            dlog.info("Unmounted")
        self._deleting.discard(key)

    async def _mount_device(self, device: Device, db: Session):
        device_id = str(device.id)
        plugin_id = device.plugin_id
        dlog = get_logger(plugin_id, device_id=device_id)

        plugin = plugin_loader.get_device(plugin_id)
        if not plugin:
            dlog.warning(f"Unknown plugin '{plugin_id}' – skipping")
            return

        protocols_config, actions = _resolve_plugin_config(plugin)

        if not protocols_config and not actions:
            dlog.warning("No protocols or actions defined – skipping")
            return

        credential = (
            db.query(Credential).filter(Credential.id == device.credential_id).first()
        )
        if not credential:
            dlog.warning("No credentials – skipping")
            return

        import json

        cred_data = json.loads(decrypt(credential.data))

        resolved_protocols = {
            proto_id: _resolve(proto_config, cred_data)
            for proto_id, proto_config in protocols_config.items()
        }

        connections = DeviceConnections()
        for proto_id, proto_config in resolved_protocols.items():
            protocol_class = plugin_loader.get_protocol_class(proto_id)
            if protocol_class:
                await connections.connect(proto_id, protocol_class, proto_config)

        self._connections[device_id] = connections
        self._plugin_ids[device_id] = plugin_id

        auth_dep = _make_auth_dependency(device.group_id)

        sub_app = self._build_sub_app(
            device, actions, cred_data, connections, plugin, auth_dep
        )
        mount_path = f"/devices/{device_id}"
        self._root_app.mount(mount_path, sub_app)
        self._apps[device_id] = sub_app

        dlog.info(f"Mounted: {device.name} at {mount_path}")

    def _build_sub_app(
        self, device, actions, credentials, connections, plugin, auth_dep
    ) -> FastAPI:
        meta = {k: v for k, v in plugin.items() if not k.startswith("_")}
        sub_app = FastAPI(
            title=device.name,
            description=meta.get("description", ""),
            version=meta.get("version", "1.0.0"),
            dependencies=[Depends(auth_dep)],
        )
        for action_name, action_def in actions.get("actions", {}).items():
            self._register_action(sub_app, action_name, action_def, credentials, connections)
        self._register_ping(sub_app, connections)
        return sub_app

    def _register_ping(self, app, connections):
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

    def _register_action(self, app, name, action, credentials, connections):
        from fastapi import File, Form, UploadFile

        label = action.get("label", name)
        example = action.get("example", {})
        inputs = action.get("input", {})
        has_file_upload = any(v.get("type") == "bytes" for v in inputs.values())

        if has_file_upload:

            @app.post(f"/action/{name}", summary=label, tags=["actions"])
            async def action_handler(file: UploadFile = File(...), path: str = Form(...)):
                protocol_id = action.get("protocol")
                protocol = connections.get(protocol_id)
                if not protocol:
                    return JSONResponse(
                        {"success": False, "error": f"Protocol '{protocol_id}' not connected"},
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
                f"/action/{name}",
                summary=label,
                tags=["actions"],
                openapi_extra={
                    "requestBody": {
                        "content": {"application/json": {"example": example}}
                    }
                },
            )
            async def action_handler(body: dict = {}):
                protocol_id = action.get("protocol")
                protocol = connections.get(protocol_id)
                if not protocol:
                    return JSONResponse(
                        {"success": False, "error": f"Protocol '{protocol_id}' not connected"},
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
                exec_payload = {
                    "topic": _resolve_str(action.get("topic", ""), credentials),
                    "payload": resolved_payload,
                    "path": body.get("path", action.get("input", {}).get("path", {}).get("default", "/")),
                }
                if action.get("response_topic"):
                    exec_payload["response_topic"] = _resolve_str(action["response_topic"], credentials)
                return await protocol.execute_action(action.get("method", name), exec_payload)

        action_handler.__name__ = f"action_{name}"


# Helpers


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


device_manager: DeviceManager | None = None


def init_device_manager(app: FastAPI) -> DeviceManager:
    global device_manager
    device_manager = DeviceManager(app)
    return device_manager
