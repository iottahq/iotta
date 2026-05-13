"""
routers/groups.py – CRUD router for device groups.

Each group has a generated API token (stored encrypted).
The token is accessible at any time via GET /groups/{id}/token.
"""

import json
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.crypto import decrypt, encrypt
from src.database import get_db
from src.models.group import Group

router = APIRouter(prefix="/groups", tags=["groups"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: str | None = None


class GroupRead(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class GroupReadWithToken(GroupRead):
    token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_token() -> str:
    return f"iotta_{secrets.token_hex(32)}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[GroupRead])
def list_groups(db: Session = Depends(get_db)):
    return db.query(Group).all()


@router.get("/{group_id}", response_model=GroupRead)
def get_group(group_id: UUID, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/{group_id}/token", response_model=GroupReadWithToken)
def get_group_token(group_id: UUID, db: Session = Depends(get_db)):
    """Returns the group's API token in plaintext."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupReadWithToken(
        id=group.id,
        name=group.name,
        token=decrypt(group.token),
    )


@router.post("/", response_model=GroupReadWithToken, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    """
    Creates a new group and generates an API token for it.
    The token is returned in plaintext and stored encrypted.
    """
    raw_token = _generate_token()
    group = Group(
        name=body.name,
        token=encrypt(raw_token),
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return GroupReadWithToken(
        id=group.id,
        name=group.name,
        token=raw_token,
    )


@router.patch("/{group_id}", response_model=GroupRead)
def update_group(group_id: UUID, body: GroupUpdate, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if body.name is not None:
        group.name = body.name
    db.commit()
    db.refresh(group)
    return group


@router.post("/{group_id}/rotate-token", response_model=GroupReadWithToken)
def rotate_token(group_id: UUID, db: Session = Depends(get_db)):
    """Generates a new token for the group. The old token stops working immediately."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    raw_token = _generate_token()
    group.token = encrypt(raw_token)
    db.commit()
    return GroupReadWithToken(
        id=group.id,
        name=group.name,
        token=raw_token,
    )


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: UUID, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()