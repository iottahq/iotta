# MQTT Protocol Plugin

Connects to any device that communicates over MQTT. Supports TLS, persistent connections, publish actions, and real-time status updates via topic subscriptions.

---

## Requirements

- MQTT broker accessible on the network
- Port 8883 (TLS) or 1883 (plain)

---

## Configuration

```json
"mqtt": {
  "host": "{ip}",
  "port": 8883,
  "tls": true,
  "username": "myuser",
  "password": "{access_code}",
  "persistent": true,
  "subscribe_topics": [
    "device/{serial}/report"
  ],
  "on_connect_publish": {
    "topic": "device/{serial}/request",
    "payload": {
      "command": "pushall"
    }
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `host` | string | ✅ | MQTT broker host or IP |
| `port` | integer | ✅ | Port (8883 for TLS, 1883 for plain) |
| `tls` | boolean | ❌ | Enable TLS (default: false) |
| `username` | string | ❌ | MQTT username |
| `password` | string | ❌ | MQTT password |
| `persistent` | boolean | ❌ | Keep connection alive (default: true) |
| `subscribe_topics` | array | ❌ | Topics to subscribe to for status updates |
| `on_connect_publish` | object | ❌ | Message to publish immediately after connecting |

---

## Actions (send)

Publish a message to a topic:

```json
{
  "topic": "device/ABC123/request",
  "payload": {
    "print": {
      "command": "pause"
    }
  }
}
```

---

## Stream

Subscribe to a topic and receive real-time updates via WebSocket:

```json
"stream": {
  "status": {
    "protocol": "mqtt",
    "topic": "device/{serial}/report",
    "emit_as": "websocket"
  }
}
```

---

## Notes

- TLS connections skip certificate verification (self-signed certs supported)
- With `persistent: true` the connection stays open and automatically reconnects
- With `persistent: false` a new connection is made per request
