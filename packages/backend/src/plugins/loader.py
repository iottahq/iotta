"""
loader.py – Discovers and loads all protocol and device plugins.

On startup, the loader:
1. Scans plugins/protocols/ and registers all protocol plugins
2. Installs missing pip dependencies declared in plugin.yaml
3. Verifies min_iotta_version compatibility
4. Loads capabilities.yaml if present (convention: same directory as plugin.yaml)
5. Scans plugins/devices/ and reads each plugin.yaml
6. Loads credentials.json, protocols.json, actions.json if present (convention-based)
7. Validates device plugin dependencies (required protocols must be installed)
8. Validates declared methods against protocol capabilities
9. Makes all plugins available to the rest of the application

Hot-reload is supported – call reload_protocols(), reload_devices(), or reload_all()
to pick up new or updated plugins without restarting the server.
"""

import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml
from packaging.version import Version
from src.logging import get_logger
from src.plugins.base_protocol import BaseProtocol
from src.version import IOTTA_VERSION

logger = get_logger("core")

PLUGINS_ROOT = Path(__import__("os").getenv("IOTTA_PLUGINS_DIR", "/plugins"))
PROTOCOLS_DIR = PLUGINS_ROOT / "protocols"
DEVICES_DIR = PLUGINS_ROOT / "devices"


def _check_min_version(min_version: str, plugin_name: str) -> bool:
    if not min_version:
        return True
    try:
        if Version(IOTTA_VERSION) < Version(min_version):
            logger.warning(
                f"Plugin '{plugin_name}' requires iotta >={min_version} "
                f"but current version is {IOTTA_VERSION} – skipping"
            )
            return False
        return True
    except Exception:
        logger.warning(
            f"Plugin '{plugin_name}' has invalid min_iotta_version: '{min_version}' – ignoring check"
        )
        return True


def _ensure_pip_dependencies(deps: list[str], plugin_name: str) -> bool:
    if not deps:
        return True

    missing = []
    for dep in deps:
        module_name = dep.split(">=")[0].split("==")[0].split("!=")[0].strip()
        import_name = _pip_to_import_name(module_name)
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(dep)

    if not missing:
        return True

    logger.info(f"Plugin '{plugin_name}' requires: {missing} – installing...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--root-user-action=ignore",
                *missing,
            ],
            check=True,
        )
        logger.info(f"Successfully installed dependencies for '{plugin_name}'")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies for '{plugin_name}': {e}")
        return False


def _pip_to_import_name(package: str) -> str:
    mapping = {
        "pyyaml": "yaml",
        "pillow": "PIL",
        "python-dotenv": "dotenv",
        "paho-mqtt": "paho",
    }
    return mapping.get(package.lower(), package.lower())


def _load_capabilities(protocol_dir: Path, protocol_name: str) -> dict | None:
    """
    Loads capabilities.yaml from the protocol plugin directory if present.
    Convention: capabilities.yaml must live in the same directory as plugin.yaml.
    """
    capabilities_file = protocol_dir / "capabilities.yaml"
    if not capabilities_file.exists():
        return None
    try:
        with open(capabilities_file, "r") as f:
            data = yaml.safe_load(f) or {}
        capabilities = data.get("capabilities", {})
        logger.debug(
            f"Loaded {len(capabilities)} capability/capabilities for '{protocol_name}': "
            f"{list(capabilities.keys())}"
        )
        return capabilities
    except Exception as e:
        logger.warning(f"Failed to load capabilities.yaml for '{protocol_name}': {e}")
        return None


def _load_json_if_exists(path: Path, label: str, device_id: str) -> dict | None:
    """Load a JSON file if it exists, return None otherwise."""
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {label} for '{device_id}': {e}")
        return None


def _validate_methods(
    protocols_config: dict,
    device_id: str,
    protocol_capabilities: dict[str, dict],
) -> None:
    """
    Warns if a device plugin declares methods that don't exist in the
    corresponding protocol's capabilities.
    """
    for proto_id, proto_config in protocols_config.items():
        methods = proto_config.get("methods")
        if not methods or methods == "all":
            continue

        capabilities = protocol_capabilities.get(proto_id)
        if not capabilities:
            continue

        for method in methods:
            if method not in capabilities:
                logger.warning(
                    f"Device plugin '{device_id}': method '{method}' not found in "
                    f"capabilities of protocol '{proto_id}'"
                )


class PluginLoader:
    def __init__(self):
        self._protocols: dict[str, dict] = {}
        self._devices: dict[str, dict] = {}

    # Protocol plugins

    def load_protocols(self) -> None:
        if not PROTOCOLS_DIR.exists():
            logger.warning(f"Protocols directory not found: {PROTOCOLS_DIR}")
            return

        for protocol_dir in sorted(PROTOCOLS_DIR.iterdir()):
            if not protocol_dir.is_dir():
                continue
            manifest_file = protocol_dir / "plugin.yaml"
            if not manifest_file.exists():
                logger.warning(f"No plugin.yaml in {protocol_dir.name}, skipping")
                continue

            with open(manifest_file, "r") as f:
                meta_peek = yaml.safe_load(f) or {}

            entry = meta_peek.get("entry", "main.py")
            plugin_file = protocol_dir / entry

            if not plugin_file.exists():
                logger.warning(
                    f"Entry file '{entry}' not found in {protocol_dir.name}, skipping"
                )
                continue

            self._load_protocol(protocol_dir, plugin_file, manifest_file)

    def _load_protocol(
        self, protocol_dir: Path, plugin_file: Path, manifest_file: Path
    ) -> None:
        name = protocol_dir.name
        try:
            meta = {}
            if manifest_file.exists():
                with open(manifest_file, "r") as f:
                    meta = yaml.safe_load(f) or {}

            if not _check_min_version(meta.get("min_iotta_version", ""), name):
                return

            pip_deps = meta.get("dependencies", {}).get("pip", [])
            if not _ensure_pip_dependencies(pip_deps, name):
                logger.error(
                    f"Skipping protocol plugin '{name}' due to missing dependencies"
                )
                return

            module_key = f"iotta.protocols.{name}"
            if module_key in sys.modules:
                del sys.modules[module_key]

            spec = importlib.util.spec_from_file_location(module_key, plugin_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_key] = module
            spec.loader.exec_module(module)

            protocol_class = None
            for attr in vars(module).values():
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseProtocol)
                    and attr is not BaseProtocol
                ):
                    protocol_class = attr
                    break

            if protocol_class is None:
                logger.warning(f"No BaseProtocol subclass found in {name}/plugin.py")
                return

            protocol_id = meta.get("id") or protocol_class.protocol_name or name

            capabilities = _load_capabilities(protocol_dir, protocol_id)
            if capabilities is not None:
                meta["capabilities"] = capabilities

            self._protocols[protocol_id] = {"class": protocol_class, "meta": meta}

            logger.info(
                f"Loaded protocol plugin: {meta.get('name', protocol_id)} "
                f"v{meta.get('version', '?')} by {meta.get('author', {}).get('name', 'unknown')} "
                f"[{meta.get('author', {}).get('organisation', '')}]"
            )

        except Exception as e:
            logger.error(f"Failed to load protocol plugin '{name}': {e}")

    # Device plugins

    def load_devices(self) -> None:
        if not DEVICES_DIR.exists():
            logger.warning(f"Devices directory not found: {DEVICES_DIR}")
            return

        for device_dir in sorted(DEVICES_DIR.iterdir()):
            if not device_dir.is_dir():
                continue
            manifest_file = device_dir / "plugin.yaml"
            if not manifest_file.exists():
                logger.warning(f"No plugin.yaml in {device_dir.name}, skipping")
                continue
            self._load_device(device_dir, manifest_file)

    def _load_device(self, device_dir: Path, manifest_file: Path) -> None:
        device_id = device_dir.name
        try:
            with open(manifest_file, "r") as f:
                manifest = yaml.safe_load(f)

            if not manifest:
                logger.warning(f"Empty plugin.yaml in {device_id}, skipping")
                return

            for field in ("name", "version"):
                if field not in manifest:
                    logger.warning(
                        f"Device plugin '{device_id}' missing field: {field}"
                    )
                    return

            if not _check_min_version(manifest.get("min_iotta_version", ""), device_id):
                return

            # Convention-based file loading – no references needed in plugin.yaml
            credentials = _load_json_if_exists(
                device_dir / "credentials.json", "credentials.json", device_id
            )
            if credentials is not None:
                manifest["_credentials"] = credentials

            protocols_config = _load_json_if_exists(
                device_dir / "protocols.json", "protocols.json", device_id
            )
            if protocols_config is not None:
                manifest["_protocols"] = protocols_config

            actions = _load_json_if_exists(
                device_dir / "actions.json", "actions.json", device_id
            )
            if actions is not None:
                manifest["_actions"] = actions

            # Legacy: fall back to config.json if the split files don't exist
            if "_protocols" not in manifest and "_actions" not in manifest:
                config_file = manifest.get("config")
                if config_file:
                    config_path = device_dir / config_file
                    legacy = _load_json_if_exists(config_path, config_file, device_id)
                    if legacy:
                        manifest["_config"] = legacy
                        logger.debug(
                            f"Loaded legacy config '{config_file}' for '{device_id}'"
                        )

            # Validate declared methods against protocol capabilities
            if "_protocols" in manifest:
                protocol_capabilities = {
                    pid: (self._protocols[pid]["meta"].get("capabilities") or {})
                    for pid in self._protocols
                }
                _validate_methods(
                    manifest["_protocols"], device_id, protocol_capabilities
                )

            missing = [
                p
                for p in manifest.get("dependencies", {}).get("protocols", [])
                if p not in self._protocols
            ]
            if missing:
                logger.warning(
                    f"Device plugin '{device_id}' requires missing protocols: {missing}"
                )
                return

            self._devices[device_id] = manifest
            logger.info(
                f"Loaded device plugin: {manifest.get('name', device_id)} "
                f"v{manifest.get('version', '?')} by {manifest.get('author', {}).get('name', 'unknown')} "
                f"[{manifest.get('author', {}).get('organisation', '')}]"
            )

        except Exception as e:
            logger.error(f"Failed to load device plugin '{device_id}': {e}")

    # Hot-reload

    def reload_protocols(self) -> None:
        logger.info("Hot-reloading protocol plugins...")
        self._protocols.clear()
        self.load_protocols()
        logger.info(f"Reloaded {len(self._protocols)} protocol plugin(s)")

    def reload_devices(self) -> None:
        logger.info("Hot-reloading device plugins...")
        self._devices.clear()
        self.load_devices()
        logger.info(f"Reloaded {len(self._devices)} device plugin(s)")

    def reload_all(self) -> None:
        logger.info("Hot-reloading all plugins...")
        self._protocols.clear()
        self._devices.clear()
        self.load_all()

    # Public API

    def load_all(self) -> None:
        logger.info(f"iotta v{IOTTA_VERSION} – loading plugins...")
        self.load_protocols()
        logger.info(
            f"Loaded {len(self._protocols)} protocol plugin(s): {list(self._protocols.keys())}"
        )
        self.load_devices()
        logger.info(
            f"Loaded {len(self._devices)} device plugin(s): {list(self._devices.keys())}"
        )

    def get_protocol_class(self, protocol_id: str) -> type[BaseProtocol] | None:
        entry = self._protocols.get(protocol_id)
        return entry["class"] if entry else None

    def get_protocol_meta(self, protocol_id: str) -> dict | None:
        entry = self._protocols.get(protocol_id)
        return entry["meta"] if entry else None

    def get_protocol_capabilities(self, protocol_id: str) -> dict | None:
        entry = self._protocols.get(protocol_id)
        if not entry:
            return None
        return entry["meta"].get("capabilities")

    def get_device(self, device_id: str) -> dict | None:
        return self._devices.get(device_id)

    def all_protocols(self) -> list[dict]:
        return [{**entry["meta"], "id": pid} for pid, entry in self._protocols.items()]

    def all_devices(self) -> list[dict]:
        return [{**manifest, "id": did} for did, manifest in self._devices.items()]


# Singleton
plugin_loader = PluginLoader()
