# WebSocket Protocol Plugin

Connects to any device that exposes a WebSocket endpoint. Supports sending messages, receiving real-time status updates, and automatic reconnect.

---

## Requirements

- Device must expose a WebSocket endpoint (ws:// or wss://)

---

## Configuration

```json
"ws": {
  "url": "ws://{ip}:{port}/ws",
  "headers": {
    "Authorization": "Bearer {token}"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | ✅ | WebSocket URL (ws:// or wss://) |
| `headers` | object | ❌ | Additional HTTP headers for the handshake |

---

## Actions

| Action | Description | Input |
|---|---|---|
| `send` | Send a JSON message to the device | any JSON payload |

---

## Stream

Subscribe to incoming messages from the device:

```json
"stream": {
  "status": {
    "protocol": "ws",
    "label": "Live Status"
  }
}
```

---

## Example device config

```json
"protocols": {
  "ws": {
    "url": "ws://{ip}:8765/ws",
    "headers": {}
  }
},
"actions": {
  "send": {
    "command": {
      "protocol": "ws",
      "label": "Send Command",
      "example": { "cmd": "toggle" }
    }
  },
  "stream": {
    "status": {
      "protocol": "ws",
      "label": "Live Status"
    }
  }
}
```

---

## Notes

- JSON messages are parsed automatically; binary frames are hex-encoded
- Reconnect is handled by iotta's built-in reconnect loop (every 30s)
- `wss://` (TLS) is supported but certificate verification is not enforced for self-signed certs
