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
    group_id: string; // always required, never null
}

export interface DeviceCreate {
    name: string;
    plugin_id: string;
    credential_id: string;
    group_id: string; // required
}

export interface DeviceUpdate {
    name?: string;
    plugin_id?: string;
    credential_id?: string;
    group_id?: string; // optional for updates, but never set to null
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

export interface GroupCreate {
    name: string;
}

export interface GroupUpdate {
    name?: string;
}

export interface ApiTokenDevice {
    device_id: string;
    allowed_actions: string[];
}

export interface ApiToken {
    id: string;
    name: string;
    group_id: string;
    expires_at: string | null;
    created_at: string;
    last_used_at: string | null;
    devices: ApiTokenDevice[];
}

export interface ApiTokenWithValue extends ApiToken {
    token: string;
}

export interface TokenCreate {
    name: string;
    expires_at: string | null;
}

export interface TokenDeviceAdd {
    device_id: string;
    allowed_actions: string[];
}

export interface TokenDeviceUpdate {
    allowed_actions: string[];
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

export interface RegistryPlugin {
    id: string;
    type: "devices" | "protocols";
    name: string;
    version: string;
    status?: string;
    scope?: string;
    description?: string;
    author?: { name?: string; organisation?: string; url?: string };
    license?: string;
    tags?: string[];
    dependencies?: Record<string, unknown>;
    min_iotta_version?: string;
    path: string;
    icon_url?: string;
}

export interface RegistryIndex {
    version: string;
    generated_at: string;
    plugins: {
        devices: RegistryPlugin[];
        protocols: RegistryPlugin[];
    };
}

export interface RegistryInstallResult {
    installed: boolean;
    id: string;
    type: string;
    version: string;
    name: string;
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

export async function fetchAssetBlobUrl(path: string): Promise<string> {
    const token = tokenStore.get();
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
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
        execute: (
            deviceId: string,
            action: string,
            body: Record<string, unknown> = {},
        ) => post<unknown>(`/devices/${deviceId}/action/${action}`, body),
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
        create: (body: GroupCreate) => post<Group>("/groups/", body),
        update: (id: string, b: GroupUpdate) => patch<Group>(`/groups/${id}`, b),
        delete: (id: string) => del(`/groups/${id}`),
    },

    tokens: {
        list: (groupId: string) =>
            get<ApiToken[]>(`/groups/${groupId}/tokens`),
        create: (groupId: string, body: TokenCreate) =>
            post<ApiTokenWithValue>(`/groups/${groupId}/tokens`, body),
        delete: (groupId: string, tokenId: string) =>
            del(`/groups/${groupId}/tokens/${tokenId}`),
        rotate: (groupId: string, tokenId: string) =>
            post<ApiTokenWithValue>(`/groups/${groupId}/tokens/${tokenId}/rotate`),
        addDevice: (groupId: string, tokenId: string, body: TokenDeviceAdd) =>
            post<ApiTokenDevice>(`/groups/${groupId}/tokens/${tokenId}/devices`, body),
        updateDevice: (groupId: string, tokenId: string, deviceId: string, body: TokenDeviceUpdate) =>
            request<ApiTokenDevice>("PUT", `/groups/${groupId}/tokens/${tokenId}/devices/${deviceId}`, body),
        removeDevice: (groupId: string, tokenId: string, deviceId: string) =>
            del(`/groups/${groupId}/tokens/${tokenId}/devices/${deviceId}`),
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
        registry: {
            fetch: () => get<RegistryIndex>("/plugins/registry"),
            install: (type: string, id: string) =>
                post<RegistryInstallResult>(`/plugins/registry/install/${type}/${id}`),
            installGit: async (url: string): Promise<RegistryInstallResult> => {
                const token = tokenStore.get();
                const form = new FormData();
                form.append("url", url);
                const res = await fetch(`${BASE_URL}/plugins/registry/install-git`, {
                    method: "POST",
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                    body: form,
                });
                if (!res.ok) {
                    let detail = res.statusText;
                    try { detail = (await res.json()).detail ?? detail; } catch {}
                    throw new ApiError(res.status, detail);
                }
                return res.json();
            },
            installZip: async (file: File): Promise<RegistryInstallResult> => {
                const token = tokenStore.get();
                const form = new FormData();
                form.append("file", file);
                const res = await fetch(`${BASE_URL}/plugins/registry/install-zip`, {
                    method: "POST",
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                    body: form,
                });
                if (!res.ok) {
                    let detail = res.statusText;
                    try { detail = (await res.json()).detail ?? detail; } catch {}
                    throw new ApiError(res.status, detail);
                }
                return res.json();
            },
            uninstall: (type: string, id: string) =>
                del(`/plugins/registry/${type}/${id}`),
        },
    },
    
} as const;