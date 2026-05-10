# FTP / FTPS Protocol Plugin

Connects to any device that exposes a filesystem over FTP or FTPS. Supports plain FTP, explicit FTPS (STARTTLS), and implicit FTPS (port 990).

---

## Requirements

- FTP server accessible on the network
- Port 21 (plain/explicit) or 990 (implicit FTPS)

---

## Configuration

```json
"ftp": {
  "host": "{ip}",
  "port": 21,
  "tls": "none",
  "username": "{username}",
  "password": "{password}",
  "persistent": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `host` | string | ✅ | FTP server host or IP |
| `port` | integer | ✅ | Port (default: 21) |
| `tls` | string | ❌ | TLS mode: `none`, `explicit`, `implicit` (default: `none`) |
| `username` | string | ❌ | FTP username (default: `anonymous`) |
| `password` | string | ❌ | FTP password |
| `persistent` | boolean | ❌ | Keep connection alive (default: false) |

---

## Actions

| Action | Description | Input |
|---|---|---|
| `list` | List files in a directory | `path` |
| `upload` | Upload a file | `path`, `file` (multipart) |
| `download` | Download a file | `path` |
| `delete` | Delete a file | `path` |
| `mkdir` | Create a directory | `path` |

---

## TLS Modes

| Mode | Description |
|---|---|
| `none` | Plain FTP, no encryption |
| `explicit` | STARTTLS – encryption negotiated after connect |
| `implicit` | TLS active immediately on connect (port 990) |

---

## Notes

- File uploads use `multipart/form-data` instead of JSON
- `persistent: false` is recommended – many FTP servers drop idle connections
- Implicit FTPS skips certificate verification (self-signed certs supported)