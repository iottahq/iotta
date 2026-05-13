"""
crypto.py – Symmetric encryption for sensitive DB fields.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
The secret key is read from the IOTTA_SECRET_KEY environment variable.

Generate a key with:
    openssl rand -hex 32

Usage:
    from src.crypto import encrypt, decrypt

    stored  = encrypt("my-secret")   # store this in DB
    plain   = decrypt(stored)        # original value
"""

import base64
import os

from cryptography.fernet import Fernet

_RAW_KEY = os.getenv("IOTTA_SECRET_KEY", "")


def _get_fernet() -> Fernet:
    if not _RAW_KEY:
        raise RuntimeError(
            "IOTTA_SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
        )
    # Fernet requires a 32-byte url-safe base64 key
    # We accept a hex string and derive the key from it
    key_bytes = bytes.fromhex(_RAW_KEY[:64].ljust(64, "0"))
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64 Fernet token (str)."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def check_secret_key_configured() -> None:
    if not _RAW_KEY:
        raise RuntimeError(
            "IOTTA_SECRET_KEY is not set. "
            "Copy .env.example to .env and generate a key with: openssl rand -hex 32"
        )
    try:
        _get_fernet()
    except Exception as e:
        raise RuntimeError(f"IOTTA_SECRET_KEY is invalid: {e}")
