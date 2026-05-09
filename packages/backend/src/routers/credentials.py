"""
credentials.py – CRUD router for credentials.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any
from uuid import UUID

from src.database import get_db
from src.models.credential import Credential

router = APIRouter(prefix="/credentials", tags=["credentials"])


# Schemas

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


# Endpoints

@router.get("/", response_model=list[CredentialRead])
def list_credentials(db: Session = Depends(get_db)):
    return db.query(Credential).all()


@router.get("/{credential_id}", response_model=CredentialRead)
def get_credential(credential_id: UUID, db: Session = Depends(get_db)):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.post("/", response_model=CredentialRead, status_code=201)
def create_credential(body: CredentialCreate, db: Session = Depends(get_db)):
    credential = Credential(name=body.name, data=body.data)
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.patch("/{credential_id}", response_model=CredentialRead)
def update_credential(credential_id: UUID, body: CredentialUpdate, db: Session = Depends(get_db)):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    if body.name is not None:
        credential.name = body.name
    if body.data is not None:
        credential.data = body.data
    db.commit()
    db.refresh(credential)
    return credential


@router.delete("/{credential_id}", status_code=204)
def delete_credential(credential_id: UUID, db: Session = Depends(get_db)):
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(credential)
    db.commit()