# HTTP / HTTPS Protocol Plugin

Connects to any device that exposes a REST API over HTTP or HTTPS. Supports GET, POST, PUT, DELETE with bearer, basic, and api-key authentication.

---

## Requirements

- HTTP server accessible on the network
- Port 80 (HTTP) or 443 (HTTPS)

---

## Configuration

```json
"http": {
  "base_url": "http://{ip}",
  "timeout": 10,
  "verify_ssl": false,
  "persistent": false,
  "auth": {
    "type": "bearer",
    "token": "{token}"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `base_url` | string | ✅ | Base URL of the device API |
| `timeout` | integer | ❌ | Request timeout in seconds (default: 10) |
| `verify_ssl` | boolean | ❌ | Verify SSL certificate (default: true) |
| `persistent` | boolean | ❌ | Keep connection alive (default: false) |
| `auth` | object | ❌ | Authentication configuration |

### Auth types

| Type | Fields | Description |
|---|---|---|
| `bearer` | `token` | `Authorization: Bearer <token>` |
| `basic` | `username`, `password` | HTTP Basic Auth |
| `api-key` | `header`, `key` | Custom header with API key |
| `none` | – | No authentication |

---

## Actions

| Action | Description | Input |
|---|---|---|
| `GET` | Fetch data from an endpoint | `path`, `params` |
| `POST` | Send data to an endpoint | `path`, `body` |
| `PUT` | Update data at an endpoint | `path`, `body` |
| `DELETE` | Delete a resource | `path` |

Example action definition:

```json
"status": {
  "protocol": "http",
  "label": "Get Status",
  "method": "GET",
  "path": "/api/status"
}
```

---

## Notes

- `verify_ssl: false` allows self-signed certificates
- Responses are automatically parsed as JSON if possible, otherwise returned as plain text
- HTTP is stateless – `persistent` only controls the underlying TCP connection pool