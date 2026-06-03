"""
plugin_registry.py – Router for the public plugin registry.

Endpoints:
  GET  /plugins/registry                      → fetch registry index from GitHub
  POST /plugins/registry/install/{type}/{id}  → download & install a plugin from registry
  POST /plugins/registry/install-git          → install from a git repository URL
  POST /plugins/registry/install-zip          → install from an uploaded zip file
  DELETE /plugins/registry/{type}/{id}        → uninstall a registry-installed plugin
"""

import io
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from src.logging import get_logger
from src.plugins.loader import DEVICES_DIR, PROTOCOLS_DIR, plugin_loader

logger = get_logger("core")
router = APIRouter(prefix="/plugins/registry", tags=["plugin-registry"])

REGISTRY_URL = "https://raw.githubusercontent.com/iottahq/iotta-plugins/main/registry.json"
REPO_TARBALL_URL = "https://codeload.github.com/iottahq/iotta-plugins/tar.gz/refs/heads/main"
TARBALL_PREFIX = "iotta-plugins-main"  # top-level dir name inside the tarball


def _target_dir(plugin_type: str, plugin_id: str) -> Path:
    if plugin_type == "devices":
        return DEVICES_DIR / plugin_id
    if plugin_type == "protocols":
        return PROTOCOLS_DIR / plugin_id
    raise HTTPException(status_code=400, detail=f"Unknown plugin type: {plugin_type}")


@router.get("")
async def fetch_registry():
    """Fetch the live registry index from the iottahq/plugins GitHub repo."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(REGISTRY_URL)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Registry fetch failed: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Registry unreachable: {e}")


@router.post("/install/{plugin_type}/{plugin_id}")
async def install_plugin(plugin_type: str, plugin_id: str):
    """
    Download the plugin from GitHub and install it into the local plugins directory.
    Downloads the full repo tarball and extracts only the requested plugin folder.
    """
    if plugin_type not in ("devices", "protocols"):
        raise HTTPException(status_code=400, detail=f"Unknown plugin type: {plugin_type}")

    target_dir = _target_dir(plugin_type, plugin_id)
    prefix = f"{TARBALL_PREFIX}/{plugin_type}/{plugin_id}/"

    logger.info(f"Installing plugin '{plugin_type}/{plugin_id}' from registry...")

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(REPO_TARBALL_URL)
            resp.raise_for_status()
            tarball_bytes = resp.content
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Failed to download plugin repo: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Download failed: {e}")

    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
        members = [m for m in tar.getmembers() if m.name.startswith(prefix)]
        if not members:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{plugin_type}/{plugin_id}' not found in registry repo",
            )

        target_dir.mkdir(parents=True, exist_ok=True)

        for member in members:
            rel_path = member.name[len(prefix):]
            if not rel_path:
                continue
            dest = target_dir / rel_path
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                f = tar.extractfile(member)
                if f:
                    dest.write_bytes(f.read())

    # Verify plugin.yaml exists
    manifest_path = target_dir / "plugin.yaml"
    if not manifest_path.exists():
        import shutil
        shutil.rmtree(target_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail="Installed plugin is missing plugin.yaml")

    with open(manifest_path) as f:
        meta = yaml.safe_load(f) or {}

    # Hot-reload so the plugin is immediately available
    if plugin_type == "devices":
        plugin_loader.reload_devices()
    else:
        plugin_loader.reload_all()

    logger.info(f"Successfully installed '{plugin_type}/{plugin_id}' v{meta.get('version', '?')}")
    return {
        "installed": True,
        "id": plugin_id,
        "type": plugin_type,
        "version": meta.get("version"),
        "name": meta.get("name"),
    }


def _detect_plugin_type(meta: dict) -> str:
    """Infer plugin type from plugin.yaml: presence of 'entry' means protocol, otherwise device."""
    return "protocols" if meta.get("entry") else "devices"


def _install_from_dir(source_dir: Path) -> dict:
    """
    Validate a directory contains a valid plugin, auto-detect its type, move it to the
    plugins dir, hot-reload. Returns the install result dict.
    """
    manifest_path = source_dir / "plugin.yaml"
    if not manifest_path.exists():
        raise HTTPException(status_code=422, detail="No plugin.yaml found in the repository root")

    with open(manifest_path) as f:
        meta = yaml.safe_load(f) or {}

    plugin_id = meta.get("id")
    if not plugin_id:
        raise HTTPException(status_code=422, detail="plugin.yaml is missing required field: id")

    plugin_type = _detect_plugin_type(meta)

    target_dir = _target_dir(plugin_type, plugin_id)
    if target_dir.exists():
        shutil.rmtree(target_dir)

    shutil.copytree(source_dir, target_dir)

    if plugin_type == "devices":
        plugin_loader.reload_devices()
    else:
        plugin_loader.reload_all()

    logger.info(f"Installed custom plugin '{plugin_type}/{plugin_id}' v{meta.get('version', '?')}")
    return {
        "installed": True,
        "id": plugin_id,
        "type": plugin_type,
        "version": meta.get("version"),
        "name": meta.get("name"),
    }


@router.post("/install-git")
async def install_from_git(url: str = Form(...)):
    """Clone a git repository and install its root as a plugin. Type is auto-detected from plugin.yaml."""
    logger.info(f"Installing plugin from git: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = Path(tmpdir) / "repo"
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(clone_dir)],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as e:
            raise HTTPException(
                status_code=422,
                detail=f"git clone failed: {e.stderr.decode().strip() or e.stdout.decode().strip()}",
            )
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="git is not available on this server")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="git clone timed out")

        shutil.rmtree(clone_dir / ".git", ignore_errors=True)
        return _install_from_dir(clone_dir)


@router.post("/install-zip")
async def install_from_zip(file: UploadFile = File(...)):
    """Extract an uploaded zip and install its contents as a plugin. Type is auto-detected from plugin.yaml."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=422, detail="Uploaded file must be a .zip archive")

    logger.info(f"Installing plugin from zip: {file.filename}")
    contents = await file.read()

    with tempfile.TemporaryDirectory() as tmpdir:
        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir()

        try:
            with zipfile.ZipFile(io.BytesIO(contents)) as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=422, detail="Uploaded file is not a valid zip archive")

        # Support both flat zips (files at root) and wrapped zips (single top-level folder)
        entries = list(extract_dir.iterdir())
        if len(entries) == 1 and entries[0].is_dir() and not (extract_dir / "plugin.yaml").exists():
            plugin_dir = entries[0]
        else:
            plugin_dir = extract_dir

        return _install_from_dir(plugin_dir)


@router.delete("/{plugin_type}/{plugin_id}")
async def uninstall_plugin(plugin_type: str, plugin_id: str):
    """Remove a plugin from the local plugins directory."""
    import shutil

    target_dir = _target_dir(plugin_type, plugin_id)

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_type}/{plugin_id}' is not installed")

    shutil.rmtree(target_dir)

    if plugin_type == "devices":
        plugin_loader.reload_devices()
    else:
        plugin_loader.reload_all()

    logger.info(f"Uninstalled plugin '{plugin_type}/{plugin_id}'")
    return {"uninstalled": True, "id": plugin_id, "type": plugin_type}
