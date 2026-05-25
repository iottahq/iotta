"""
routers/plugin_editor.py – Plugin editor endpoints.

Endpoints:
  POST /plugins/devices/create   → write plugin files to disk + reload
  PUT  /plugins/devices/{id}     → overwrite existing plugin files + reload
  DELETE /plugins/devices/{id}   → delete plugin directory + reload
"""

import json
import shutil
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.plugins.loader import DEVICES_DIR, plugin_loader

router = APIRouter(prefix="/plugins", tags=["plugins"])


# Schemas


class PluginEditorPayload(BaseModel):
    """
    All files that make up a device plugin, as parsed objects.
    The backend serialises them back to YAML/JSON and writes to disk.
    """

    plugin_yaml: dict
    credentials_json: list | None = None
    protocols_json: dict | None = None
    actions_json: dict | None = None


class PluginEditorResponse(BaseModel):
    id: str
    message: str


# Helpers


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

    return plugin_dir


def _plugin_id_from_payload(payload: PluginEditorPayload) -> str:
    plugin_id = payload.plugin_yaml.get("id", "").strip()
    if not plugin_id:
        raise HTTPException(status_code=422, detail="plugin_yaml.id is required")
    # Basic sanity: only lowercase, digits, hyphens
    import re
    if not re.match(r"^[a-z0-9][a-z0-9\-]*$", plugin_id):
        raise HTTPException(
            status_code=422,
            detail="plugin_yaml.id must be lowercase alphanumeric with hyphens only",
        )
    return plugin_id


# Endpoints

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
        # Plugin was written but failed to load (e.g. validation error)
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