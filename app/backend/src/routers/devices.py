"""
devices.py – CRUD router for devices.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

from src.database import get_db
from src.models.device import Device
from src.models.credential import Credential
from src.plugins.loader import plugin_loader

router = APIRouter(prefix="/devices", tags=["devices"])


# Schemas

class DeviceCreate(BaseModel):
    name: str
    plugin_id: str
    credential_id: UUID


class DeviceUpdate(BaseModel):
    name: str | None = None
    plugin_id: str | None = None
    credential_id: UUID | None = None


class DeviceRead(BaseModel):
    id: UUID
    name: str
    plugin_id: str
    credential_id: UUID

    class Config:
        from_attributes = True


# Endpoints

@router.get("/", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: UUID, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/", response_model=DeviceRead, status_code=201)
def create_device(body: DeviceCreate, db: Session = Depends(get_db)):
    # Check plugin exists
    if not plugin_loader.get_device(body.plugin_id):
        raise HTTPException(status_code=400, detail=f"Device plugin '{body.plugin_id}' not found")

    # Check credential exists
    credential = db.query(Credential).filter(Credential.id == body.credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    device = Device(
        name=body.name,
        plugin_id=body.plugin_id,
        credential_id=body.credential_id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(device_id: UUID, body: DeviceUpdate, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.plugin_id is not None:
        if not plugin_loader.get_device(body.plugin_id):
            raise HTTPException(status_code=400, detail=f"Device plugin '{body.plugin_id}' not found")
        device.plugin_id = body.plugin_id

    if body.credential_id is not None:
        credential = db.query(Credential).filter(Credential.id == body.credential_id).first()
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
        device.credential_id = body.credential_id

    if body.name is not None:
        device.name = body.name

    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: UUID, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()