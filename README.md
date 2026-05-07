# iotta.

**Any device. One API.**

iotta is a self-hosted protocol gateway that turns any device into a unified REST API — no matter what protocol it speaks. MQTT, FTP, HTTP, WebSocket, and more.

> ⚠️ iotta is currently in early development. Expect breaking changes.

---

## What it does

Most devices speak different protocols. A 3D printer uses MQTT and FTP. A smart plug uses HTTP. A sensor uses WebSocket. Integrating them all means learning every protocol, every quirk, every auth method.

iotta solves this with a single unified API:

```
GET  /device/{id}/status       → current device state
POST /device/{id}/action       → send a command
WS   /device/{id}/live         → real-time status stream
GET  /device/{id}/files        → list files
POST /device/{id}/upload       → upload a file
```

Every device. Same endpoints. Bearer token auth. OpenAPI spec included.

---

## How it works

iotta uses two types of plugins:

- **Protocol plugins** — adapters for MQTT, FTP, HTTP, WebSocket, and more
- **Device plugins** — describe how a specific device communicates, no code required

Configure a device once via the built-in editor. Get a bearer token. Start integrating.

Works with n8n, Node-RED, Home Assistant, or anything that speaks HTTP.

---

## Quick start

```bash
docker run -p 8080:8080 iottahq/iotta
```

Open [http://localhost:8080](http://localhost:8080) to access the dashboard.

---

## Stack

- **Backend** — Python, FastAPI
- **Frontend** — Vue 3, TypeScript, shadcn-vue
- **Deployment** — Docker, docker-compose

---

## License

Personal and internal use is free under the [Sustainable Use License](LICENSE.md).  
Enterprise features require a paid license. See [LICENSE_EE.md](LICENSE_EE.md).  
Copyright © 2025 Elias Bergmann.