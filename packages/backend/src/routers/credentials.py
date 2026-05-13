"""
routers/credentials.py – CRUD router for credentials.

credential.data is stored encrypted and decrypted on read.
"""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.crypto import decrypt, encrypt
from src.database import get_db
from src.models.credential import Credential

router = APIRouter(prefix="/credentials", tags=["credentials"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class CredentialCreate(BaseModel):
    name: str
    data: dict[str, Any]


class CredentialUpdate(BaseModel):
    name: str | None = None
    data: dict[str, Any] | None = None


class CredentialRead(BaseModel):
    id: UUID
    name: str
    data: dict[str, Any]

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────


def _decrypt_credential(credential: Credential) -> CredentialRead:
    return CredentialRead(
        id=credential.id,
        name=credential.name,
        data=json.loads(decrypt(credential.data)),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[CredentialRead])
def list_credentials(db: Session = Depends(get_db)):
    return [_decrypt_credential(c) for c in db.query(Credential).all()]


@router.get("/{credential_id}", response_model=CredentialRead)
def get_credential(credential_id: UUID, db: Session = Depends(get_db)):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return _decrypt_credential(credential)


@router.post("/", response_model=CredentialRead, status_code=201)
def create_credential(body: CredentialCreate, db: Session = Depends(get_db)):
    credential = Credential(
        name=body.name,
        data=encrypt(json.dumps(body.data)),
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return _decrypt_credential(credential)


@router.patch("/{credential_id}", response_model=CredentialRead)
def update_credential(
    credential_id: UUID, body: CredentialUpdate, db: Session = Depends(get_db)
):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    if body.name is not None:
        credential.name = body.name
    if body.data is not None:
        credential.data = encrypt(json.dumps(body.data))
    db.commit()
    db.refresh(credential)
    return _decrypt_credential(credential)


@router.delete("/{credential_id}", status_code=204)
def delete_credential(credential_id: UUID, db: Session = Depends(get_db)):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(credential)
    db.commit()
