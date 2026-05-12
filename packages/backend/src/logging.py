"""
logging.py – Centralised logging for iotta.

Usage:
    from src.logging import get_logger

    # Protocol plugin (no device context)
    logger = get_logger("mqtt")
    logger.info("Connected")          # → [mqtt] Connected

    # Device manager (with device context)
    logger = get_logger("bambu-lab-a1", device_id="f1e1b0aa-c43f-...")
    logger.info("Mounted")            # → [bambu-lab-a1 → f1e1b0aa] Mounted

    # Update device context on an existing adapter
    logger = get_logger("ftp", device_id=device_id)
"""

import logging
from typing import Any


class _IottaFormatter(logging.Formatter):
    """Formats log records with an optional plugin/device prefix."""

    def format(self, record: logging.LogRecord) -> str:
        plugin_id: str = getattr(record, "plugin_id", "")
        device_id: str = getattr(record, "device_id", "")

        if plugin_id and device_id:
            short = device_id.split("-")[0]
            record.prefix = f"[{plugin_id} → {short}] "
        elif plugin_id:
            record.prefix = f"[{plugin_id}] "
        elif device_id:
            short = device_id.split("-")[0]
            record.prefix = f"[{short}] "
        else:
            record.prefix = ""

        return super().format(record)


def setup_logging() -> None:
    """Configure the root logger with iotta's formatter. Call once at startup."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        _IottaFormatter(
            fmt="%(asctime)s  %(levelname)-8s  %(prefix)s%(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.root.setLevel(logging.INFO)
    logging.root.handlers = [handler]


# Single shared logger that all adapters wrap
_root = logging.getLogger("iotta")


def get_logger(
    plugin_id: str,
    device_id: str | None = None,
) -> logging.LoggerAdapter:
    """
    Return a LoggerAdapter that tags every record with plugin_id and
    optionally device_id.  The formatter renders these as a prefix.

    Args:
        plugin_id:  Plugin identifier, e.g. "mqtt", "ftp", "bambu-lab-a1".
        device_id:  Full UUID string of the device (first segment is shown).
    """
    extra: dict[str, Any] = {"plugin_id": plugin_id, "device_id": device_id or ""}
    return logging.LoggerAdapter(_root, extra=extra)