# Bambu Lab A1

Device plugin for the Bambu Lab A1 FDM 3D printer. Supports print control, file management, AMS, camera snapshot, and real-time status via MQTT and FTPS.

---

## Requirements

- Firmware **≥ 01.04**
- **LAN mode** must be enabled in the printer settings (`Settings → Network → LAN Mode`)
- Printer and iotta must be on the same local network

---

## Credentials

| Field | Type | Description |
|---|---|---|
| `ip` | string | Local IP address of the printer |
| `serial` | string | Serial number (found in printer settings) |
| `access_code` | secret | LAN access code (found in printer settings) |

---

## Actions

Full API documentation is available at:

```
http://<iotta-host>:8000/devices/{device-id}/docs
```

All available actions, input schemas, and examples are listed there.


---

## Protocols

| Protocol | Purpose |
|---|---|
| MQTT (port 8883, TLS) | Print control, status updates |
| FTPS (port 990, implicit TLS) | File management |
| Camera (port 6000, TLS) | Snapshot and live feed |

---

## Notes

- The printer uses `bblp` as the MQTT and FTP username – this is handled automatically
- FTPS connections are not kept persistent as the printer drops idle connections
- The camera stream delivers individual JPEG frames – use the `snapshot` action for a single frame
- AMS slot indexing starts at `0`