"""
routers/devices.py – CRUD router for devices.

Management endpoints (create, update, delete) require admin/JWT access.
Device API access (actions, ping) is controlled via scoped tokens in device sub-apps.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.auth import require_auth
from src.database import get_db
from src.models.credential import Credential
from src.models.device import Device
from src.models.group import Group
from src.plugins.loader import plugin_loader

router = APIRouter(prefix="/devices", tags=["devices"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class DeviceCreate(BaseModel):
    name: str
    plugin_id: str
    credential_id: UUID
    group_id: UUID


class DeviceUpdate(BaseModel):
    name: str | None = None
    plugin_id: str | None = None
    credential_id: UUID | None = None
    group_id: UUID | None = None


class DeviceRead(BaseModel):
    id: UUID
    name: str
    plugin_id: str
    credential_id: UUID
    group_id: UUID

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_device_manager():
    from src.device_manager import device_manager
    return device_manager


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[DeviceRead])
def list_devices(
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    return db.query(Device).filter(Device.group_id.isnot(None)).all()


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/", response_model=DeviceRead, status_code=201)
async def create_device(
    body: DeviceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    if not plugin_loader.get_device(body.plugin_id):
        raise HTTPException(status_code=400, detail=f"Device plugin '{body.plugin_id}' not found")

    if not db.query(Credential).filter(Credential.id == body.credential_id).first():
        raise HTTPException(status_code=404, detail="Credential not found")

    group = db.query(Group).filter(Group.id == body.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    device = Device(
        name=body.name,
        plugin_id=body.plugin_id,
        credential_id=body.credential_id,
        group_id=body.group_id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    manager = _get_device_manager()
    if manager:
        await manager.mount(device.id)

    return device


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: UUID,
    body: DeviceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.plugin_id is not None:
        if not plugin_loader.get_device(body.plugin_id):
            raise HTTPException(status_code=400, detail=f"Device plugin '{body.plugin_id}' not found")
        device.plugin_id = body.plugin_id

    if body.credential_id is not None:
        if not db.query(Credential).filter(Credential.id == body.credential_id).first():
            raise HTTPException(status_code=404, detail="Credential not found")
        device.credential_id = body.credential_id

    if body.group_id is not None:
        group = db.query(Group).filter(Group.id == body.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        device.group_id = body.group_id

    if body.name is not None:
        device.name = body.name

    db.commit()
    db.refresh(device)

    manager = _get_device_manager()
    if manager:
        await manager.unmount(device.id)
        await manager.mount(device.id)

    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    manager = _get_device_manager()
    if manager:
        await manager.unmount(device.id)

    db.delete(device)
    db.commit()
