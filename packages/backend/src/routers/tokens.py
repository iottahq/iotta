"""
routers/tokens.py – Scoped API token management.

Tokens grant fine-grained, per-device, per-action access within a group.
The raw token value is only returned on create and rotate — never again.

Endpoints:
  GET    /groups/{group_id}/tokens                                  → list tokens
  POST   /groups/{group_id}/tokens                                  → create token
  GET    /groups/{group_id}/tokens/{token_id}                       → get token detail
  DELETE /groups/{group_id}/tokens/{token_id}                       → delete token
  POST   /groups/{group_id}/tokens/{token_id}/rotate                → issue new token value, same config
  POST   /groups/{group_id}/tokens/{token_id}/devices               → add device to token
  PUT    /groups/{group_id}/tokens/{token_id}/devices/{device_id}   → update allowed actions for device
  DELETE /groups/{group_id}/tokens/{token_id}/devices/{device_id}   → remove device from token
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.device import Device
from src.models.group import Group
from src.models.token import Token, TokenDevice, generate_raw_token, hash_token

router = APIRouter(tags=["tokens"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class TokenDeviceRead(BaseModel):
    device_id: UUID
    allowed_actions: list[str]

    class Config:
        from_attributes = True


class TokenRead(BaseModel):
    id: UUID
    name: str
    group_id: UUID
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None
    devices: list[TokenDeviceRead]

    class Config:
        from_attributes = True


class TokenReadWithValue(TokenRead):
    token: str


class TokenCreate(BaseModel):
    name: str
    expires_at: datetime | None = None


class TokenDeviceAdd(BaseModel):
    device_id: UUID
    allowed_actions: list[str]  # ["*"] or specific names e.g. ["print", "status"]


class TokenDeviceUpdate(BaseModel):
    allowed_actions: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_group_or_404(group_id: UUID, db: Session) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _get_token_or_404(token_id: UUID, group_id: UUID, db: Session) -> Token:
    token = db.query(Token).filter(
        Token.id == token_id,
        Token.group_id == group_id,
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


def _serialize(token: Token) -> TokenRead:
    return TokenRead(
        id=token.id,
        name=token.name,
        group_id=token.group_id,
        expires_at=token.expires_at,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        devices=[
            TokenDeviceRead(device_id=td.device_id, allowed_actions=td.allowed_actions)
            for td in token.devices
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/groups/{group_id}/tokens", response_model=list[TokenRead])
def list_tokens(group_id: UUID, db: Session = Depends(get_db)):
    _get_group_or_404(group_id, db)
    return [_serialize(t) for t in db.query(Token).filter(Token.group_id == group_id).all()]


@router.post("/groups/{group_id}/tokens", response_model=TokenReadWithValue, status_code=201)
def create_token(group_id: UUID, body: TokenCreate, db: Session = Depends(get_db)):
    _get_group_or_404(group_id, db)
    raw = generate_raw_token()
    token = Token(
        name=body.name,
        token_hash=hash_token(raw),
        group_id=group_id,
        expires_at=body.expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return TokenReadWithValue(**_serialize(token).model_dump(), token=raw)


@router.get("/groups/{group_id}/tokens/{token_id}", response_model=TokenRead)
def get_token(group_id: UUID, token_id: UUID, db: Session = Depends(get_db)):
    return _serialize(_get_token_or_404(token_id, group_id, db))


@router.delete("/groups/{group_id}/tokens/{token_id}", status_code=204)
def delete_token(group_id: UUID, token_id: UUID, db: Session = Depends(get_db)):
    token = _get_token_or_404(token_id, group_id, db)
    db.delete(token)
    db.commit()


@router.post("/groups/{group_id}/tokens/{token_id}/rotate", response_model=TokenReadWithValue)
def rotate_token(group_id: UUID, token_id: UUID, db: Session = Depends(get_db)):
    """Issue a new token value. All config (devices, actions, expiry) is preserved."""
    token = _get_token_or_404(token_id, group_id, db)
    raw = generate_raw_token()
    token.token_hash = hash_token(raw)
    db.commit()
    db.refresh(token)
    return TokenReadWithValue(**_serialize(token).model_dump(), token=raw)


@router.post(
    "/groups/{group_id}/tokens/{token_id}/devices",
    response_model=TokenDeviceRead,
    status_code=201,
)
def add_device(
    group_id: UUID,
    token_id: UUID,
    body: TokenDeviceAdd,
    db: Session = Depends(get_db),
):
    token = _get_token_or_404(token_id, group_id, db)

    device = db.query(Device).filter(
        Device.id == body.device_id,
        Device.group_id == group_id,
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found in this group")

    existing = db.query(TokenDevice).filter(
        TokenDevice.token_id == token.id,
        TokenDevice.device_id == body.device_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Device already assigned to this token")

    td = TokenDevice(
        token_id=token.id,
        device_id=body.device_id,
        allowed_actions=body.allowed_actions,
    )
    db.add(td)
    db.commit()
    db.refresh(td)
    return TokenDeviceRead(device_id=td.device_id, allowed_actions=td.allowed_actions)


@router.put(
    "/groups/{group_id}/tokens/{token_id}/devices/{device_id}",
    response_model=TokenDeviceRead,
)
def update_device_permissions(
    group_id: UUID,
    token_id: UUID,
    device_id: UUID,
    body: TokenDeviceUpdate,
    db: Session = Depends(get_db),
):
    token = _get_token_or_404(token_id, group_id, db)
    td = db.query(TokenDevice).filter(
        TokenDevice.token_id == token.id,
        TokenDevice.device_id == device_id,
    ).first()
    if not td:
        raise HTTPException(status_code=404, detail="Device not assigned to this token")
    td.allowed_actions = body.allowed_actions
    db.commit()
    db.refresh(td)
    return TokenDeviceRead(device_id=td.device_id, allowed_actions=td.allowed_actions)


@router.delete(
    "/groups/{group_id}/tokens/{token_id}/devices/{device_id}",
    status_code=204,
)
def remove_device(
    group_id: UUID,
    token_id: UUID,
    device_id: UUID,
    db: Session = Depends(get_db),
):
    token = _get_token_or_404(token_id, group_id, db)
    td = db.query(TokenDevice).filter(
        TokenDevice.token_id == token.id,
        TokenDevice.device_id == device_id,
    ).first()
    if not td:
        raise HTTPException(status_code=404, detail="Device not assigned to this token")
    db.delete(td)
    db.commit()
