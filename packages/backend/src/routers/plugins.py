"""
plugins.py – Router for plugin management.

Endpoints:
  GET  /plugins/protocols          → list all loaded protocol plugins
  GET  /plugins/devices            → list all loaded device plugins
  GET  /plugins/protocols/{id}     → get a specific protocol plugin
  GET  /plugins/devices/{id}       → get a specific device plugin
  POST /plugins/protocols/reload   → hot-reload all protocol plugins
  POST /plugins/devices/reload     → hot-reload all device plugins
  POST /plugins/reload             → hot-reload everything
"""

from fastapi import APIRouter, HTTPException
from src.plugins.loader import plugin_loader

router = APIRouter(prefix="/plugins", tags=["plugins"])


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/protocols")
def list_protocols():
    return {
        "count": len(plugin_loader.all_protocols()),
        "items": plugin_loader.all_protocols(),
    }


@router.get("/devices")
def list_devices():
    return {
        "count": len(plugin_loader.all_devices()),
        "items": plugin_loader.all_devices(),
    }


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/protocols/{protocol_id}")
def get_protocol(protocol_id: str):
    meta = plugin_loader.get_protocol_meta(protocol_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Protocol plugin '{protocol_id}' not found")
    return meta


@router.get("/devices/{device_id}")
def get_device(device_id: str):
    device = plugin_loader.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device plugin '{device_id}' not found")
    return device


# ── Hot-reload ────────────────────────────────────────────────────────────────

@router.post("/protocols/reload")
def reload_protocols():
    plugin_loader.reload_protocols()
    return {
        "message": "Protocol plugins reloaded",
        "count": len(plugin_loader.all_protocols()),
        "items": plugin_loader.all_protocols(),
    }


@router.post("/devices/reload")
def reload_devices():
    plugin_loader.reload_devices()
    return {
        "message": "Device plugins reloaded",
        "count": len(plugin_loader.all_devices()),
        "items": plugin_loader.all_devices(),
    }


@router.post("/reload")
def reload_all():
    plugin_loader.reload_all()
    return {
        "message": "All plugins reloaded",
        "protocols": len(plugin_loader.all_protocols()),
        "devices": len(plugin_loader.all_devices()),
    }