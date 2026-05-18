/**
 * api.ts – iotta API client
 *
 * Central fetch wrapper with Bearer token auth (JWT).
 * Token is stored in localStorage under "iotta_token".
 */

export interface User {
    id: string;
	first_name: string;
	last_name: string;
	email: string;
	is_admin: boolean;
}

export interface Device {
    id: string;
    name: string;
    plugin_id: string;
    credential_id: string;
    group_id: string | null;
}

export interface DeviceCreate {
    name: string;
    plugin_id: string;
    credential_id: string;
    group_id?: string | null;
}

export interface DeviceUpdate {
    name?: string;
    plugin_id?: string;
    credential_id?: string;
    group_id?: string | null;
}

export interface Credential {
    id: string;
    name: string;
    data: Record<string, unknown>;
}

export interface CredentialCreate {
    name: string;
    data: Record<string, unknown>;
}

export interface CredentialUpdate {
    name?: string;
    data?: Record<string, unknown>;
}

export interface Group {
    id: string;
    name: string;
}

export interface GroupWithToken extends Group {
    token: string;
}

export interface GroupCreate {
    name: string;
}

export interface GroupUpdate {
    name?: string;
}

export interface PluginMeta {
    id: string;
    name: string;
    version: string;
    description?: string;
    status?: string;
    author?: {
        name?: string;
        organisation?: string;
        url?: string;
    };
    tags?: string[];
}

export interface PluginList<T> {
    count: number;
    items: T[];
}

export interface PingResult {
    online: boolean;
    protocols: Record<
        string,
        {
        ok: boolean;
        latency_ms: number | null;
        error: string | null;
        }
    >;
}

export interface SetupStatus {
    configured: boolean;
}

export interface SetupRequest {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

const TOKEN_KEY = "iotta_token";

export const tokenStore = {
    get(): string {
        return localStorage.getItem(TOKEN_KEY) ?? "";
    },
    set(token: string): void {
        localStorage.setItem(TOKEN_KEY, token);
    },
    clear(): void {
        localStorage.removeItem(TOKEN_KEY);
    },
    has(): boolean {
        return !!localStorage.getItem(TOKEN_KEY);
    },
};

const BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
    constructor(
        public readonly status: number,
        public readonly detail: string,
    ) {
        super(`${status}: ${detail}`);
        this.name = "ApiError";
    }
}

async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    requiresAuth = true,
): Promise<T> {
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };
    
    if (requiresAuth) {
        const token = tokenStore.get();
        if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    
    const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const json = await res.json();
            detail = json.detail ?? detail;
        } catch {
        /* ignore */
        }
        throw new ApiError(res.status, detail);
    }
    
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
}

const get = <T>(path: string, auth = true) =>
  request<T>("GET", path, undefined, auth);
const post = <T>(path: string, body?: unknown, auth = true) =>
  request<T>("POST", path, body, auth);
const patch = <T>(path: string, body: unknown) =>
  request<T>("PATCH", path, body);
const del = (path: string) => request<void>("DELETE", path);

function openStream(
    deviceId: string,
    action: string,
    onMessage: (data: unknown) => void,
    onClose?: () => void,
    onError?: (e: Event) => void,
): WebSocket {
    const token = tokenStore.get();
    const url = `ws://localhost:8000/devices/${deviceId}/stream/${action}${token ? `?token=${token}` : ""}`;
    const ws = new WebSocket(url);
    
    ws.onmessage = (e) => {
        try {
            onMessage(JSON.parse(e.data));
        } catch {
            onMessage(e.data);
        }
    };
    if (onClose) ws.onclose = onClose;
    if (onError) ws.onerror = onError;
    
    return ws;
}

export const api = {
    auth: {
        setupStatus: () => get<SetupStatus>("/auth/setup/status", false),
        setup: (body: SetupRequest) =>
        post<TokenResponse>("/auth/setup", body, false),
        login: (body: LoginRequest) =>
        post<TokenResponse>("/auth/login", body, false),
        me: () => get<User>("/auth/me"),
    },
    
    health: {
        check: () => get<{ status: string }>("/health", false),
    },
    
    devices: {
        list: () => get<Device[]>("/devices/"),
        get: (id: string) => get<Device>(`/devices/${id}`),
        create: (body: DeviceCreate) => post<Device>("/devices/", body),
        update: (id: string, b: DeviceUpdate) => patch<Device>(`/devices/${id}`, b),
        delete: (id: string) => del(`/devices/${id}`),
        ping: (id: string) => get<PingResult>(`/devices/${id}/ping`),
    },
    
    actions: {
        send: (
            deviceId: string,
            action: string,
            body: Record<string, unknown> = {},
        ) => post<unknown>(`/devices/${deviceId}/send/${action}`, body),
        request: (deviceId: string, action: string, path?: string) =>
        get<unknown>(
            `/devices/${deviceId}/request/${action}${path ? `?path=${encodeURIComponent(path)}` : ""}`,
        ),
    },
    
    credentials: {
        list: () => get<Credential[]>("/credentials/"),
        get: (id: string) => get<Credential>(`/credentials/${id}`),
        create: (body: CredentialCreate) => post<Credential>("/credentials/", body),
        update: (id: string, b: CredentialUpdate) =>
        patch<Credential>(`/credentials/${id}`, b),
        delete: (id: string) => del(`/credentials/${id}`),
    },
    
    groups: {
        list: () => get<Group[]>("/groups/"),
        get: (id: string) => get<Group>(`/groups/${id}`),
        getToken: (id: string) => get<GroupWithToken>(`/groups/${id}/token`),
        create: (body: GroupCreate) => post<GroupWithToken>("/groups/", body),
        update: (id: string, b: GroupUpdate) => patch<Group>(`/groups/${id}`, b),
        rotateToken: (id: string) =>
        post<GroupWithToken>(`/groups/${id}/rotate-token`),
        delete: (id: string) => del(`/groups/${id}`),
    },
    
    plugins: {
        protocols: {
            list: () => get<PluginList<PluginMeta>>("/plugins/protocols"),
            get: (id: string) => get<PluginMeta>(`/plugins/protocols/${id}`),
            reload: () => post<PluginList<PluginMeta>>("/plugins/protocols/reload"),
        },
        devices: {
            list: () => get<PluginList<PluginMeta>>("/plugins/devices"),
            get: (id: string) => get<PluginMeta>(`/plugins/devices/${id}`),
            reload: () => post<PluginList<PluginMeta>>("/plugins/devices/reload"),
        },
        reloadAll: () =>
            post<{ message: string; protocols: number; devices: number }>(
                "/plugins/reload",
            ),
    },
    
    ws: {
        stream: openStream,
    },
} as const;
