"""
permissions.py – Device access control helpers.

Separated from auth.py to avoid circular imports.
"""

from uuid import UUID

from fastapi import HTTPException, status
from src.models.group import Group


def require_device_access(device_group_id: UUID | None, auth: Group | None) -> None:
    """
    Checks whether the authenticated token has access to a specific device.

    Rules:
    - Admin token (auth=None)              → always allowed
    - Group token, device in same group    → allowed
    - Group token, device has no group     → denied (admin-only)
    - Group token, device in other group   → denied
    """
    if auth is None:
        return

    if device_group_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This device has no group assigned and requires admin access.",
        )

    if device_group_id != auth.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: device does not belong to your group.",
        )
