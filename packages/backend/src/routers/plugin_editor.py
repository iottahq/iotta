"""
routers/plugin_editor.py – Plugin editor endpoints.

Endpoints:
  POST /plugins/devices/create         → write plugin files to disk + reload
  PUT  /plugins/devices/{id}           → overwrite existing plugin files + reload
  DELETE /plugins/devices/{id}/files   → delete plugin directory + reload
  GET  /plugins/devices/{id}/assets/{filename} → serve a plugin asset file
"""

import base64
import json
import mimetypes
import shutil
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.plugins.loader import DEVICES_DIR, plugin_loader

router = APIRouter(prefix="/plugins", tags=["plugins"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class IconPayload(BaseModel):
    """A base64-encoded icon file."""
    filename: str
    base64: str
    mime_type: str


class PluginEditorPayload(BaseModel):
    """
    All files that make up a device plugin, as parsed objects.
    The backend serialises them back to YAML/JSON and writes to disk.
    """
    plugin_yaml: dict
    credentials_json: list | None = None
    protocols_json: dict | None = None
    actions_json: dict | None = None
    icon: IconPayload | None = None


class PluginEditorResponse(BaseModel):
    id: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_plugin(plugin_id: str, payload: PluginEditorPayload) -> Path:
    """
    Write all plugin files into /plugins/devices/{plugin_id}/.
    Returns the plugin directory path.
    """
    plugin_dir = DEVICES_DIR / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # plugin.yaml
    with open(plugin_dir / "plugin.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            payload.plugin_yaml,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    # credentials.json (optional)
    if payload.credentials_json is not None:
        with open(plugin_dir / "credentials.json", "w", encoding="utf-8") as f:
            json.dump(payload.credentials_json, f, indent=4, ensure_ascii=False)

    # protocols.json (optional)
    if payload.protocols_json is not None:
        with open(plugin_dir / "protocols.json", "w", encoding="utf-8") as f:
            json.dump(payload.protocols_json, f, indent=4, ensure_ascii=False)

    # actions.json (optional)
    if payload.actions_json is not None:
        with open(plugin_dir / "actions.json", "w", encoding="utf-8") as f:
            json.dump(payload.actions_json, f, indent=4, ensure_ascii=False)

    # icon (optional) – stored as icon.svg or icon.png etc.
    if payload.icon is not None:
        _write_icon(plugin_dir, payload.icon)

    return plugin_dir


def _write_icon(plugin_dir: Path, icon: IconPayload) -> None:
    """Decode and write the icon file. Removes any pre-existing icon.*."""
    # Remove old icons first
    for old in plugin_dir.glob("icon.*"):
        old.unlink(missing_ok=True)

    ext = _ext_from_mime(icon.mime_type, icon.filename)
    icon_path = plugin_dir / f"icon{ext}"

    data = base64.b64decode(icon.base64)
    with open(icon_path, "wb") as f:
        f.write(data)


def _ext_from_mime(mime_type: str, filename: str) -> str:
    """Derive a safe file extension from mime type or original filename."""
    mime_map = {
        "image/svg+xml": ".svg",
        "image/png":     ".png",
        "image/jpeg":    ".jpg",
        "image/webp":    ".webp",
    }
    if mime_type in mime_map:
        return mime_map[mime_type]
    # Fallback: use original extension
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ".png"


def _plugin_id_from_payload(payload: PluginEditorPayload) -> str:
    plugin_id = payload.plugin_yaml.get("id", "").strip()
    if not plugin_id:
        raise HTTPException(status_code=422, detail="plugin_yaml.id is required")
    import re
    if not re.match(r"^[a-z0-9][a-z0-9\-]*$", plugin_id):
        raise HTTPException(
            status_code=422,
            detail="plugin_yaml.id must be lowercase alphanumeric with hyphens only",
        )
    return plugin_id


def _find_icon(plugin_dir: Path) -> Path | None:
    """Return the icon file path if one exists, else None."""
    for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
        p = plugin_dir / f"icon{ext}"
        if p.exists():
            return p
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/devices/create", response_model=PluginEditorResponse, status_code=201)
def create_plugin(body: PluginEditorPayload):
    """
    Create a new device plugin on disk and reload device plugins.
    Fails with 409 if a plugin with that id already exists.
    """
    plugin_id = _plugin_id_from_payload(body)

    plugin_dir = DEVICES_DIR / plugin_id
    if plugin_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Plugin '{plugin_id}' already exists. Use PUT to update it.",
        )

    _write_plugin(plugin_id, body)
    plugin_loader.reload_devices()

    if not plugin_loader.get_device(plugin_id):
        raise HTTPException(
            status_code=422,
            detail=f"Plugin '{plugin_id}' was written but failed to load. Check plugin_yaml fields.",
        )

    return PluginEditorResponse(
        id=plugin_id,
        message=f"Plugin '{plugin_id}' created and loaded successfully.",
    )


@router.put("/devices/{plugin_id}", response_model=PluginEditorResponse)
def update_plugin(plugin_id: str, body: PluginEditorPayload):
    """
    Overwrite an existing device plugin on disk and reload.
    The id in the URL must match plugin_yaml.id.
    """
    body_id = _plugin_id_from_payload(body)
    if body_id != plugin_id:
        raise HTTPException(
            status_code=422,
            detail=f"URL plugin_id '{plugin_id}' does not match plugin_yaml.id '{body_id}'.",
        )

    plugin_dir = DEVICES_DIR / plugin_id
    if not plugin_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' not found. Use POST /plugins/devices/create to create it.",
        )

    _write_plugin(plugin_id, body)
    plugin_loader.reload_devices()

    return PluginEditorResponse(
        id=plugin_id,
        message=f"Plugin '{plugin_id}' updated and reloaded successfully.",
    )


@router.delete("/devices/{plugin_id}/files", status_code=204)
def delete_plugin(plugin_id: str):
    """
    Delete a device plugin directory from disk and reload.
    Note: does NOT delete devices registered with this plugin_id –
    those will simply fail to mount after reload.
    """
    plugin_dir = DEVICES_DIR / plugin_id
    if not plugin_dir.exists():
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found.")

    shutil.rmtree(plugin_dir)
    plugin_loader.reload_devices()


@router.get("/devices/{plugin_id}/assets/{filename}")
def get_plugin_asset(plugin_id: str, filename: str):
    """
    Serve a static asset from the plugin directory.
    Primarily used for icons: GET /plugins/devices/{id}/assets/icon
    The {filename} can omit the extension – the endpoint will find the
    first match (icon.svg, icon.png, etc.).
    """
    plugin_dir = DEVICES_DIR / plugin_id
    if not plugin_dir.exists():
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found.")

    # Exact match first
    exact = plugin_dir / filename
    if exact.exists() and exact.is_file():
        return FileResponse(exact, media_type=_media_type(exact))

    # Extension-less lookup (e.g. "icon" → "icon.svg")
    for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
        candidate = plugin_dir / f"{filename}{ext}"
        if candidate.exists():
            return FileResponse(candidate, media_type=_media_type(candidate))

    raise HTTPException(
        status_code=404,
        detail=f"Asset '{filename}' not found in plugin '{plugin_id}'.",
    )


def _media_type(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"