# iotta.

**IoT to anyone. Any device. One API.**

iotta is a self-hosted protocol gateway that turns any device into a unified REST API — no matter what protocol it speaks. MQTT, FTP, HTTP, WebSocket, and more.

> ⚠️ iotta is currently in early development. Expect breaking changes.

---

## What it does

Most devices speak different protocols. A 3D printer uses MQTT and FTP. A smart plug uses HTTP. A sensor uses WebSocket. Integrating them all means learning every protocol, every quirk, every auth method.

Every device. Same endpoints. Bearer token auth. OpenAPI spec generated and included per device and platform.

---

## How it works

iotta uses two types of plugins:

- **Protocol plugins** — adapters for MQTT, FTP, HTTP, WebSocket, and more
- **Device plugins** — describe how a specific device communicates, no code required

Configure a device once via the built-in editor. Get a bearer token from the group. Start integrating.

Works with n8n, Node-RED, Home Assistant, or anything that speaks HTTP.

---

## Quick start

```bash
git clone https://github.com/iottahq/iotta.git
cd iotta
docker compose up --build
````

Open [http://localhost:8000](http://localhost:8000) to access the API.
Open [http://localhost:8000/docs](http://localhost:8000/docs) for the Swagger UI.

> The one-liner `docker run iottahq/iotta` will be available once iotta reaches a stable release.
> A dedicated UI will be added later.

---

## Stack

* **Backend** — Python, FastAPI
* **Frontend** — Vue 3, TypeScript, shadcn-vue
* **Deployment** — Docker, docker-compose

### Why this stack?

iotta is built around protocol interoperability and dynamic API generation.

* **Python + FastAPI** — async networking, a massive protocol ecosystem, automatic OpenAPI generation, and rapid plugin development
* **Vue 3 + TypeScript** — ideal for schema-driven configuration UIs and reactive device management
* **shadcn-vue** — consistent, composable UI primitives without building an admin system from scratch
* **Docker + docker-compose** — simple self-hosted deployment and isolated protocol dependencies

The stack is optimized for one thing:

> turning fragmented device protocols into predictable, developer-friendly APIs.

---

## License

Personal and internal use is free under the [Sustainable Use License](LICENSE.md).
Enterprise features require a paid license. See [LICENSE_EE.md](LICENSE_EE.md).
Copyright © 2025 Elias Bergmann.