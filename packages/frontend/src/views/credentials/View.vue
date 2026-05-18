<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api, type Credential, type PluginMeta, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    RiAddLine,
    RiCloseLine,
    RiDeleteBinLine,
    RiErrorWarningLine,
    RiEyeLine,
    RiEyeOffLine,
    RiKeyLine,
    RiLoader4Line,
    RiPencilLine,
    RiSave3Line,
} from "@remixicon/vue";

// ── State ──────────────────────────────────────────────────────────────────

const credentials = ref<Credential[]>([]);
const devices = ref<
    { id: string; name: string; credential_id: string; plugin_id: string }[]
>([]);
const plugins = ref<PluginMeta[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Detail modal
const selected = ref<Credential | null>(null);
const editingName = ref("");
const editingData = ref<Record<string, string>>({});
const revealed = ref<Record<string, boolean>>({});
const saving = ref(false);
const saveError = ref<string | null>(null);
const confirmDelete = ref(false);
const deleting = ref(false);

// New credential modal
const showNew = ref(false);
const newName = ref("");
const newPlugin = ref("");
const newData = ref<Record<string, string>>({});
const creatingError = ref<string | null>(null);
const creating = ref(false);

// ── Data loading ───────────────────────────────────────────────────────────

async function load() {
    loading.value = true;
    error.value = null;
    try {
        const [creds, devs, plugs] = await Promise.all([
        api.credentials.list(),
        api.devices.list(),
        api.plugins.devices.list(),
        ]);
        credentials.value = creds;
        devices.value = devs;
        plugins.value = plugs.items;
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to load";
    } finally {
        loading.value = false;
    }
}

onMounted(load);

// ── Helpers ────────────────────────────────────────────────────────────────

function devicesUsing(credId: string) {
    return devices.value.filter((d) => d.credential_id === credId);
}

function pluginName(pluginId: string) {
    return plugins.value.find((p) => p.id === pluginId)?.name ?? pluginId;
}

/** Fields defined by the plugin for a given device's plugin_id */
function credentialFields(
    pluginId: string,
): { field: string; type: string; label: string }[] {
    // We only have what the API exposes; fall back to the raw data keys
    return [];
}

function isSecret(key: string, pluginId?: string): boolean {
    // Heuristic: treat fields named access_code, token, password, secret as secret
    return /password|secret|access_code|token|key/i.test(key);
}

function maskValue(val: string) {
    return "•".repeat(Math.min(val.length, 12));
}

// ── Detail modal ───────────────────────────────────────────────────────────

function openDetail(cred: Credential) {
    selected.value = cred;
    editingName.value = cred.name;
    editingData.value = Object.fromEntries(
        Object.entries(cred.data).map(([k, v]) => [k, String(v)]),
    );
    revealed.value = {};
    saveError.value = null;
    confirmDelete.value = false;
}

function closeDetail() {
    selected.value = null;
    confirmDelete.value = false;
}

async function saveDetail() {
    if (!selected.value) return;
    saving.value = true;
    saveError.value = null;
    try {
        const updated = await api.credentials.update(selected.value.id, {
            name: editingName.value.trim() || undefined,
            data: editingData.value,
        });
        const idx = credentials.value.findIndex((c) => c.id === updated.id);
        if (idx !== -1) credentials.value[idx] = updated;
        selected.value = updated;
        editingName.value = updated.name;
        editingData.value = Object.fromEntries(
            Object.entries(updated.data).map(([k, v]) => [k, String(v)]),
        );
    } catch (e) {
        saveError.value = e instanceof ApiError ? e.detail : "Failed to save";
    } finally {
        saving.value = false;
    }
}

async function deleteCredential() {
    if (!selected.value) return;
    deleting.value = true;
    try {
        await api.credentials.delete(selected.value.id);
        credentials.value = credentials.value.filter(
            (c) => c.id !== selected.value!.id, 
        );
        closeDetail();
    } catch (e) {
        saveError.value = e instanceof ApiError ? e.detail : "Failed to delete";
    } finally {
        deleting.value = false;
    }
}

// ── New credential ─────────────────────────────────────────────────────────

function openNew() {
    newName.value = "";
    newPlugin.value = plugins.value[0]?.id ?? "";
    newData.value = {};
    creatingError.value = null;
    showNew.value = true;
}

async function createCredential() {
    if (!newName.value.trim()) return;
    creating.value = true;
    creatingError.value = null;
    try {
        const cred = await api.credentials.create({
        name: newName.value.trim(),
        data: newData.value,
        });
        credentials.value.push(cred);
        showNew.value = false;
    } catch (e) {
        creatingError.value = e instanceof ApiError ? e.detail : "Failed";
    } finally {
        creating.value = false;
    }
}
</script>

<template>
    <div class="flex flex-col h-full">
        <!-- Header -->
        <div
            class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border"
        >
            <div>
                <h1 class="text-sm font-semibold">Credentials</h1>
                <p class="text-xs text-muted-foreground mt-0.5">
                Stored device credentials — encrypted at rest
                </p>
            </div>
            <Button size="sm" class="gap-1.5" @click="openNew">
                <RiAddLine class="size-3.5" />
                New
            </Button>
        </div>
    
        <!-- Content -->
        <div class="flex-1 overflow-auto px-6 py-4">
            <!-- Loading -->
            <div
                v-if="loading"
                class="flex items-center justify-center py-16 text-muted-foreground"
            >
                <RiLoader4Line class="size-5 animate-spin mr-2" />
                <span class="text-xs">Loading…</span>
            </div>
        
            <!-- Error -->
            <div
                v-else-if="error"
                class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs"
            >
                <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                {{ error }}
            </div>
        
            <!-- Empty -->
            <div
                v-else-if="credentials.length === 0"
                class="flex flex-col items-center justify-center py-20 text-center gap-3"
            >
                <RiKeyLine class="size-10 text-muted-foreground/30" />
                <div>
                    <p class="text-xs font-medium text-foreground">No credentials yet</p>
                    <p class="text-xs text-muted-foreground mt-0.5">
                        Add credentials to connect your devices
                    </p>
                </div>
                <Button size="sm" class="gap-1.5 mt-1" @click="openNew">
                    <RiAddLine class="size-3.5" />
                    New credential
                </Button>
            </div>
        
            <!-- List -->
            <div
                v-else
                class="flex flex-col divide-y divide-border rounded-lg border border-border overflow-hidden"
            >
                <button
                    v-for="cred in credentials"
                    :key="cred.id"
                    @click="openDetail(cred)"
                    class="flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors group"
                >
                    <!-- Icon -->
                    <div
                        class="shrink-0 flex items-center justify-center size-7 rounded-md bg-muted/60 text-muted-foreground"
                    >
                        <RiKeyLine class="size-3.5" />
                    </div>
            
                    <!-- Name + device usage -->
                    <div class="flex-1 min-w-0">
                        <p class="text-xs font-medium text-foreground truncate">
                            {{ cred.name }}
                        </p>
                        <p class="text-[10px] text-muted-foreground mt-0.5 truncate">
                            <template v-if="devicesUsing(cred.id).length > 0">
                                Used by:
                                <span v-for="(dev, i) in devicesUsing(cred.id)" :key="dev.id">
                                    {{ dev.name }}
                                    <span v-if="i < devicesUsing(cred.id).length - 1">,</span>
                                </span>
                            </template>
                            <template v-else> Not used by any device </template>
                        </p>
                    </div>
            
                    <!-- Fields count -->
                    <div class="shrink-0 flex items-center gap-2">
                        <span class="text-[10px] text-muted-foreground tabular-nums">
                            {{ Object.keys(cred.data).length }} field
                            {{ Object.keys(cred.data).length !== 1 ? "s" : "" }}
                        </span>
                        <RiPencilLine
                            class="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        />
                    </div>
                </button>
            </div>
        </div>
    </div>
    
    <!-- ── Detail Modal ──────────────────────────────────────────────────── -->
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="selected"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="closeDetail"
            >
                <div class="absolute inset-0 bg-black/50" @click="closeDetail" />
                <div
                class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 max-h-[90vh] overflow-y-auto"
                >
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold">Edit credential</h2>
                        <Button variant="ghost" size="icon-sm" @click="closeDetail">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>
            
                    <div class="flex flex-col gap-4">
                        <!-- Name -->
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input v-model="editingName" placeholder="Credential name" />
                        </div>
            
                        <!-- Fields -->
                        <div class="flex flex-col gap-3">
                            <label class="text-xs font-medium">Fields</label>
                            <div
                                v-for="(val, key) in editingData"
                                :key="key"
                                class="flex flex-col gap-1"
                            >
                                <label class="text-[10px] font-mono text-muted-foreground">
                                    {{ key }}
                                </label>
                                <div class="relative">
                                    <Input
                                        :model-value="
                                        revealed[key] || !isSecret(key) ? val : maskValue(val)
                                        "
                                        :type="
                                        isSecret(key) && !revealed[key] ? 'password' : 'text'
                                        "
                                        class="pr-8 font-mono text-[11px]"
                                        @update:model-value="editingData[key] = $event as string"
                                    />
                                    <button
                                        v-if="isSecret(key)"
                                        type="button"
                                        @click="revealed[key] = !revealed[key]"
                                        class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                    >
                                        <RiEyeLine v-if="!revealed[key]" class="size-3.5" />
                                        <RiEyeOffLine v-else class="size-3.5" />
                                    </button>
                                </div>
                            </div>
                        </div>
            
                        <!-- Used by -->
                        <div
                            v-if="devicesUsing(selected.id).length > 0"
                            class="flex flex-col gap-1.5"
                        >
                            <label class="text-xs font-medium text-muted-foreground">
                                Used by
                            </label>
                            <div class="flex flex-wrap gap-1.5">
                                <span
                                    v-for="dev in devicesUsing(selected.id)"
                                    :key="dev.id"
                                    class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
                                >
                                    {{ dev.name }}
                                <span class="opacity-60">
                                    · {{ pluginName(dev.plugin_id) }}</span
                                >
                                </span>
                            </div>
                        </div>
            
                        <!-- Error -->
                        <div
                            v-if="saveError"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                            {{ saveError }}
                        </div>
            
                        <!-- Actions -->
                        <div class="flex gap-2 justify-between">
                            <Button
                                variant="destructive"
                                size="sm"
                                class="gap-1.5"
                                @click="confirmDelete = true"
                            >
                                <RiDeleteBinLine class="size-3.5" />
                                Delete
                            </Button>
                            <Button
                                size="sm"
                                class="gap-1.5"
                                :disabled="saving"
                                @click="saveDetail"
                            >
                                <RiLoader4Line v-if="saving" class="size-3.5 animate-spin" />
                                <RiSave3Line v-else class="size-3.5" />
                                Save
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
    
    <!-- ── Delete Confirm ────────────────────────────────────────────────── -->
    <Teleport to="body">
        <Transition name="fade">
        <div
            v-if="confirmDelete && selected"
            class="fixed inset-0 z-[60] flex items-center justify-center"
        >
            <div
                class="absolute inset-0 bg-black/50"
                @click="confirmDelete = false"
            />
            <div
                class="relative z-10 w-full max-w-xs rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
            >
                <h2 class="text-sm font-semibold">Delete credential?</h2>
                <p class="text-xs text-muted-foreground mt-1.5">
                    <span class="font-medium text-foreground">{{ selected.name }}</span>
                    will be permanently deleted.
                    <template v-if="devicesUsing(selected.id).length > 0">
                        <span class="text-destructive">
                            {{ devicesUsing(selected.id).length }} 
                            device 
                            {{ devicesUsing(selected.id).length !== 1 ? "s" : "" }}
                            will stop working.
                        </span>
                    </template>
                </p>
                <div class="flex gap-2 justify-end mt-4">
                    <Button variant="outline" size="sm" @click="confirmDelete = false">
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        size="sm"
                        class="gap-1.5"
                        :disabled="deleting"
                        @click="deleteCredential"
                    >
                        <RiLoader4Line v-if="deleting" class="size-3.5 animate-spin" />
                        <RiDeleteBinLine v-else class="size-3.5" />
                        Delete
                    </Button>
                </div>
            </div>
        </div>
        </Transition>
    </Teleport>
    
    <!-- ── New Credential Modal ──────────────────────────────────────────── -->
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="showNew"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="showNew = false"
            >
                <div class="absolute inset-0 bg-black/50" @click="showNew = false" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
                >
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold">New credential</h2>
                        <Button variant="ghost" size="icon-sm" @click="showNew = false">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>
                    <div class="flex flex-col gap-3">
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input
                                v-model="newName"
                                placeholder="e.g. Bambu Lab A1 – Home"
                                autofocus
                            />
                        </div>
                        <p class="text-[10px] text-muted-foreground -mt-1">
                            You can fill in the credential fields after creation when you
                            register a device.
                        </p>
                        <div
                            v-if="creatingError"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                            {{ creatingError }}
                        </div>
                        <div class="flex gap-2 justify-end mt-1">
                            <Button variant="outline" size="sm" @click="showNew = false"
                                >Cancel</Button
                            >
                            <Button
                                size="sm"
                                class="gap-1.5"
                                :disabled="creating || !newName.trim()"
                                @click="createCredential"
                            >
                                <RiLoader4Line v-if="creating" class="size-3.5 animate-spin" />
                                <RiAddLine v-else class="size-3.5" />
                                Create
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
