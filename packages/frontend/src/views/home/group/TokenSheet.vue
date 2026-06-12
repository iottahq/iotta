<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { api, type ApiToken, type ApiTokenWithValue, type Device, ApiError } from "@/lib/api";
import RotateDialog from "./RotateDialog.vue";
import DeleteTokenDialog from "./DeleteTokenDialog.vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    RiAddLine,
    RiArrowLeftLine,
    RiCheckLine,
    RiCloseLine,
    RiDeleteBinLine,
    RiErrorWarningLine,
    RiFileCopyLine,
    RiKeyLine,
    RiLoader4Line,
    RiPencilLine,
    RiRefreshLine,
    RiShieldLine,
    RiTimeLine,
} from "@remixicon/vue";

const props = defineProps<{
    groupId: string | null;
    groupName: string;
    devices: Device[];
}>();

const emit = defineEmits<{ close: [] }>();

// ── State ─────────────────────────────────────────────────────────────────────

const tokens = ref<ApiToken[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

// New token form
const showNewForm = ref(false);
const newName = ref("");
const newExpiry = ref("");
const creating = ref(false);
const createError = ref<string | null>(null);
const createdToken = ref<ApiTokenWithValue | null>(null);
const createdCopied = ref(false);

// Token detail view
const selectedToken = ref<ApiToken | null>(null);

// Delete token
const deleteTarget = ref<ApiToken | null>(null);
const deleteConfirmName = ref("");
const deleting = ref(false);
const deleteError = ref<string | null>(null);

// Rotate token
const rotateTarget = ref<ApiToken | null>(null);
const rotatedToken = ref<ApiTokenWithValue | null>(null);
const rotatedCopied = ref(false);
const rotating = ref<string | null>(null);

// Device assignment
const addingDevice = ref(false);
const addDeviceId = ref("");
const availableActions = ref<{ name: string; label: string; tags: string[] }[]>([]);
const loadingActions = ref(false);
const allActionsSelected = ref(true);
const selectedActions = ref<string[]>([]);
const addDeviceError = ref<string | null>(null);
const savingDevice = ref(false);
const removingDevice = ref<string | null>(null);
const editingDevice = ref<string | null>(null);
const editAllActionsSelected = ref(true);
const editSelectedActions = ref<string[]>([]);
const savingEditDevice = ref(false);
const editDeviceError = ref<string | null>(null);

const addDeviceActions = computed<string[]>(() =>
    allActionsSelected.value ? ["*"] : selectedActions.value
);

const editDeviceActions = computed<string[]>(() =>
    editAllActionsSelected.value ? ["*"] : editSelectedActions.value
);

// ── Load ──────────────────────────────────────────────────────────────────────

watch(() => props.groupId, async (id) => {
    if (!id) return;
    loading.value = true;
    error.value = null;
    try {
        tokens.value = await api.tokens.list(id);
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to load tokens";
    } finally {
        loading.value = false;
    }
}, { immediate: true });

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
    if (!iso) return "Never";
    return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function isExpired(token: ApiToken): boolean {
    if (!token.expires_at) return false;
    return new Date(token.expires_at) < new Date();
}

// ── Create token ──────────────────────────────────────────────────────────────

async function createToken() {
    if (!props.groupId || !newName.value.trim()) return;
    creating.value = true;
    createError.value = null;
    try {
        const t = await api.tokens.create(props.groupId, {
            name: newName.value.trim(),
            expires_at: newExpiry.value ? new Date(newExpiry.value).toISOString() : null,
        });
        tokens.value.push(t);
        createdToken.value = t;
        showNewForm.value = false;
        newName.value = "";
        newExpiry.value = "";
    } catch (e) {
        createError.value = e instanceof ApiError ? e.detail : "Failed to create token";
    } finally {
        creating.value = false;
    }
}

async function copyCreated() {
    if (!createdToken.value) return;
    await navigator.clipboard.writeText(createdToken.value.token);
    createdCopied.value = true;
    setTimeout(() => (createdCopied.value = false), 2000);
}

// ── Rotate ────────────────────────────────────────────────────────────────────

async function rotate(token: ApiToken) {
    if (!props.groupId) return;
    rotating.value = token.id;
    rotatedToken.value = null;
    try {
        const t = await api.tokens.rotate(props.groupId, token.id);
        rotatedToken.value = t;
        const idx = tokens.value.findIndex((x) => x.id === token.id);
        if (idx >= 0) tokens.value[idx] = t;
        if (selectedToken.value?.id === token.id) selectedToken.value = t;
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to rotate token";
    } finally {
        rotating.value = null;
    }
}

async function copyRotated() {
    if (!rotatedToken.value) return;
    await navigator.clipboard.writeText(rotatedToken.value.token);
    rotatedCopied.value = true;
    setTimeout(() => (rotatedCopied.value = false), 2000);
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function confirmDelete() {
    if (!props.groupId || !deleteTarget.value) return;
    deleting.value = true;
    deleteError.value = null;
    try {
        await api.tokens.delete(props.groupId, deleteTarget.value.id);
        tokens.value = tokens.value.filter((t) => t.id !== deleteTarget.value!.id);
        if (selectedToken.value?.id === deleteTarget.value.id) selectedToken.value = null;
        deleteTarget.value = null;
        deleteConfirmName.value = "";
    } catch (e) {
        deleteError.value = e instanceof ApiError ? e.detail : "Failed to delete token";
    } finally {
        deleting.value = false;
    }
}

// ── Device assignment ─────────────────────────────────────────────────────────

function assignedDeviceIds(token: ApiToken): string[] {
    return token.devices.map((d) => d.device_id);
}

function unassignedDevices(token: ApiToken): Device[] {
    const assigned = new Set(assignedDeviceIds(token));
    return props.devices.filter((d) => !assigned.has(d.id));
}

function deviceName(deviceId: string): string {
    return props.devices.find((d) => d.id === deviceId)?.name ?? deviceId.slice(0, 8);
}

async function loadActionsForDevice(deviceId: string) {
    const device = props.devices.find((d) => d.id === deviceId);
    if (!device) { availableActions.value = []; return; }
    loadingActions.value = true;
    try {
        const detail = await api.plugins.devices.get(device.plugin_id) as any;
        const raw = detail?._actions?.actions ?? detail?._config?.actions ?? {};
        availableActions.value = Object.entries<any>(raw).map(([name, def]) => ({
            name,
            label: def.label ?? name,
            tags: def.tags ?? [],
        }));
    } catch {
        availableActions.value = [];
    } finally {
        loadingActions.value = false;
    }
}

function openAddDevice(token: ApiToken) {
    selectedToken.value = token;
    addingDevice.value = true;
    addDeviceId.value = unassignedDevices(token)[0]?.id ?? "";
    allActionsSelected.value = true;
    selectedActions.value = [];
    addDeviceError.value = null;
    loadActionsForDevice(addDeviceId.value);
}

watch(addDeviceId, (id) => { if (id) loadActionsForDevice(id); });

async function saveDevice() {
    if (!props.groupId || !selectedToken.value || !addDeviceId.value) return;
    savingDevice.value = true;
    addDeviceError.value = null;
    try {
        const td = await api.tokens.addDevice(props.groupId, selectedToken.value.id, {
            device_id: addDeviceId.value,
            allowed_actions: addDeviceActions.value,
        });
        const tok = tokens.value.find((t) => t.id === selectedToken.value!.id);
        if (tok) {
            tok.devices.push(td);
            selectedToken.value = { ...tok };
        }
        addingDevice.value = false;
    } catch (e) {
        addDeviceError.value = e instanceof ApiError ? e.detail : "Failed to add device";
    } finally {
        savingDevice.value = false;
    }
}

async function removeDevice(token: ApiToken, deviceId: string) {
    if (!props.groupId) return;
    removingDevice.value = deviceId;
    try {
        await api.tokens.removeDevice(props.groupId, token.id, deviceId);
        const tok = tokens.value.find((t) => t.id === token.id);
        if (tok) {
            tok.devices = tok.devices.filter((d) => d.device_id !== deviceId);
            selectedToken.value = { ...tok };
        }
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to remove device";
    } finally {
        removingDevice.value = null;
    }
}

async function openEditDevice(deviceId: string, currentActions: string[]) {
    editingDevice.value = deviceId;
    editDeviceError.value = null;
    editAllActionsSelected.value = currentActions.includes("*");
    editSelectedActions.value = currentActions.includes("*") ? [] : [...currentActions];
    await loadActionsForDevice(deviceId);
}

async function saveEditDevice() {
    if (!props.groupId || !selectedToken.value || !editingDevice.value) return;
    savingEditDevice.value = true;
    editDeviceError.value = null;
    try {
        const td = await api.tokens.updateDevice(props.groupId, selectedToken.value.id, editingDevice.value, {
            allowed_actions: editDeviceActions.value,
        });
        const tok = tokens.value.find((t) => t.id === selectedToken.value!.id);
        if (tok) {
            const idx = tok.devices.findIndex((d) => d.device_id === editingDevice.value);
            if (idx >= 0) tok.devices[idx] = td;
            selectedToken.value = { ...tok };
        }
        editingDevice.value = null;
    } catch (e) {
        editDeviceError.value = e instanceof ApiError ? e.detail : "Failed to update device";
    } finally {
        savingEditDevice.value = false;
    }
}

function actionsLabel(actions: string[]): string {
    if (actions.includes("*")) return "All actions";
    return actions.join(", ") || "No actions";
}
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="groupId"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('close')"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('close')" />

                <div class="relative z-10 w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[85vh]">

                    <!-- Header -->
                    <div class="flex items-center gap-2 px-5 py-4 border-b border-border shrink-0">
                        <!-- Back button (token detail) -->
                        <Button v-if="selectedToken" variant="ghost" size="icon-sm" class="-ml-1 shrink-0" @click="selectedToken = null; addingDevice = false; rotatedToken = null">
                            <RiArrowLeftLine class="size-3.5" />
                        </Button>
                        <RiShieldLine v-else class="size-4 text-muted-foreground shrink-0" />

                        <!-- Title -->
                        <div class="flex-1 min-w-0">
                            <p class="text-xs font-semibold truncate">{{ selectedToken ? selectedToken.name : 'Access Tokens' }}</p>
                            <p class="text-[10px] text-muted-foreground truncate">
                                <template v-if="selectedToken">
                                    Expires: {{ formatDate(selectedToken.expires_at) }}
                                    <span v-if="isExpired(selectedToken)" class="text-destructive ml-1">(expired)</span>
                                </template>
                                <template v-else>{{ groupName }}</template>
                            </p>
                        </div>

                        <!-- Token actions (detail view) -->
                        <template v-if="selectedToken">
                            <Button variant="outline" size="sm" class="gap-1.5 shrink-0" :disabled="rotating === selectedToken.id" @click="rotateTarget = selectedToken">
                                <RiLoader4Line v-if="rotating === selectedToken.id" class="size-3.5 animate-spin" />
                                <RiRefreshLine v-else class="size-3.5" />
                                Rotate
                            </Button>
                            <Button variant="outline" size="icon-sm" class="shrink-0 text-destructive hover:bg-destructive/10" @click="deleteTarget = selectedToken; deleteConfirmName = ''">
                                <RiDeleteBinLine class="size-3.5" />
                            </Button>
                        </template>

                        <!-- Close -->
                        <Button variant="ghost" size="icon-sm" class="shrink-0" @click="emit('close')">
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>

                    <!-- Error banner -->
                    <div v-if="error" class="mx-5 mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        {{ error }}
                    </div>

                    <!-- Newly created token banner -->
                    <div v-if="createdToken" class="mx-5 mt-3 rounded-md border border-emerald-500/30 bg-emerald-500/5 px-3 py-2.5">
                        <p class="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-1.5">Token created — copy it now. It won't be shown again.</p>
                        <div class="font-mono text-[10px] text-muted-foreground break-all bg-muted/40 rounded px-2 py-1.5 mb-2">{{ createdToken.token }}</div>
                        <div class="flex gap-2">
                            <Button variant="outline" size="sm" class="gap-1.5 flex-1" @click="copyCreated">
                                <RiCheckLine v-if="createdCopied" class="size-3.5 text-emerald-500" />
                                <RiFileCopyLine v-else class="size-3.5" />
                                {{ createdCopied ? "Copied!" : "Copy token" }}
                            </Button>
                            <Button variant="ghost" size="sm" class="gap-1.5" @click="createdToken = null">
                                <RiCloseLine class="size-3.5" />
                                Dismiss
                            </Button>
                        </div>
                    </div>

                    <!-- Rotated token banner -->
                    <div v-if="rotatedToken" class="mx-5 mt-3 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2.5">
                        <p class="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1.5">New token value — copy it now. The old token is invalid.</p>
                        <div class="font-mono text-[10px] text-muted-foreground break-all bg-muted/40 rounded px-2 py-1.5 mb-2">{{ rotatedToken.token }}</div>
                        <div class="flex gap-2">
                            <Button variant="outline" size="sm" class="gap-1.5 flex-1" @click="copyRotated">
                                <RiCheckLine v-if="rotatedCopied" class="size-3.5 text-emerald-500" />
                                <RiFileCopyLine v-else class="size-3.5" />
                                {{ rotatedCopied ? "Copied!" : "Copy token" }}
                            </Button>
                            <Button variant="ghost" size="sm" class="gap-1.5" @click="rotatedToken = null">
                                <RiCloseLine class="size-3.5" />
                                Dismiss
                            </Button>
                        </div>
                    </div>

                    <!-- Token detail view -->
                    <template v-if="selectedToken">
                        <div class="flex-1 overflow-y-auto px-5 pb-5">
                            <div class="flex items-center justify-between mb-2 mt-2">
                                <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Devices</p>
                                <Button
                                    v-if="unassignedDevices(selectedToken).length > 0"
                                    variant="ghost"
                                    size="icon-sm"
                                    class="h-6 w-6"
                                    @click="addingDevice ? addingDevice = false : openAddDevice(selectedToken)"
                                >
                                    <RiAddLine class="size-3.5" />
                                </Button>
                            </div>

                            <!-- Add device form -->
                            <div v-if="addingDevice" class="mb-3 rounded-lg border border-border p-3 flex flex-col gap-2.5">
                                <div class="flex flex-col gap-1">
                                    <label class="text-[10px] font-medium text-muted-foreground">Device</label>
                                    <select
                                        v-model="addDeviceId"
                                        class="h-7 w-full rounded-md border border-input bg-transparent px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                                    >
                                        <option v-for="d in unassignedDevices(selectedToken)" :key="d.id" :value="d.id">{{ d.name }}</option>
                                    </select>
                                </div>
                                <div class="flex flex-col gap-1.5">
                                    <label class="text-[10px] font-medium text-muted-foreground">Allowed actions</label>
                                    <div v-if="loadingActions" class="flex items-center gap-1.5 text-xs text-muted-foreground py-1">
                                        <RiLoader4Line class="size-3.5 animate-spin" /> Loading…
                                    </div>
                                    <template v-else>
                                        <label class="flex items-center gap-2 text-xs cursor-pointer py-0.5">
                                            <input type="checkbox" :checked="allActionsSelected" @change="allActionsSelected = !allActionsSelected; if (allActionsSelected) selectedActions = []" />
                                            All actions
                                        </label>
                                        <div v-if="availableActions.length > 0" class="flex flex-col gap-0.5 border border-border rounded-md px-2.5 py-1.5 mt-0.5">
                                            <label
                                                v-for="action in availableActions"
                                                :key="action.name"
                                                class="flex items-center gap-2 text-xs cursor-pointer py-0.5"
                                                :class="allActionsSelected ? 'opacity-40 pointer-events-none' : ''"
                                            >
                                                <input
                                                    type="checkbox"
                                                    :checked="allActionsSelected || selectedActions.includes(action.name)"
                                                    :disabled="allActionsSelected"
                                                    @change="
                                                        selectedActions.includes(action.name)
                                                            ? selectedActions = selectedActions.filter(a => a !== action.name)
                                                            : selectedActions.push(action.name)
                                                    "
                                                />
                                                <span class="flex-1">{{ action.label }}</span>
                                                <span v-for="tag in action.tags" :key="tag" class="text-[9px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground font-mono">{{ tag }}</span>
                                            </label>
                                        </div>
                                    </template>
                                </div>
                                <div v-if="addDeviceError" class="flex items-start gap-1.5 text-destructive text-xs">
                                    <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                                    {{ addDeviceError }}
                                </div>
                                <div class="flex gap-2 justify-end">
                                    <Button variant="ghost" size="sm" @click="addingDevice = false">Cancel</Button>
                                    <Button size="sm" class="gap-1.5" :disabled="savingDevice || !addDeviceId" @click="saveDevice">
                                        <RiLoader4Line v-if="savingDevice" class="size-3.5 animate-spin" />
                                        Add
                                    </Button>
                                </div>
                            </div>

                            <div v-if="selectedToken.devices.length === 0 && !addingDevice" class="text-xs text-muted-foreground text-center py-6">
                                No devices assigned yet
                            </div>

                            <div v-for="td in selectedToken.devices" :key="td.device_id" class="rounded-lg border border-border mb-2 overflow-hidden">
                                <div class="flex items-start justify-between gap-2 px-3 py-2.5">
                                    <div class="flex-1 min-w-0">
                                        <p class="text-xs font-medium truncate">{{ deviceName(td.device_id) }}</p>
                                        <p class="text-[10px] text-muted-foreground mt-0.5 font-mono truncate">{{ actionsLabel(td.allowed_actions) }}</p>
                                    </div>
                                    <div class="flex gap-0.5 shrink-0">
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            class="text-muted-foreground"
                                            :disabled="!!removingDevice"
                                            @click="editingDevice === td.device_id ? editingDevice = null : openEditDevice(td.device_id, td.allowed_actions)"
                                        >
                                            <RiPencilLine class="size-3.5" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            class="text-muted-foreground hover:text-destructive"
                                            :disabled="removingDevice === td.device_id"
                                            @click="removeDevice(selectedToken, td.device_id)"
                                        >
                                            <RiLoader4Line v-if="removingDevice === td.device_id" class="size-3.5 animate-spin" />
                                            <RiDeleteBinLine v-else class="size-3.5" />
                                        </Button>
                                    </div>
                                </div>

                                <!-- Inline edit form -->
                                <div v-if="editingDevice === td.device_id" class="border-t border-border px-3 py-3 bg-muted/20 flex flex-col gap-2.5">
                                    <div class="flex flex-col gap-1.5">
                                        <label class="text-[10px] font-medium text-muted-foreground">Allowed actions</label>
                                        <div v-if="loadingActions" class="flex items-center gap-1.5 text-xs text-muted-foreground py-1">
                                            <RiLoader4Line class="size-3.5 animate-spin" /> Loading…
                                        </div>
                                        <template v-else>
                                            <label class="flex items-center gap-2 text-xs cursor-pointer py-0.5">
                                                <input type="checkbox" :checked="editAllActionsSelected" @change="editAllActionsSelected = !editAllActionsSelected; if (editAllActionsSelected) editSelectedActions = []" />
                                                All actions
                                            </label>
                                            <div v-if="availableActions.length > 0" class="flex flex-col gap-0.5 border border-border rounded-md px-2.5 py-1.5 mt-0.5">
                                                <label
                                                    v-for="action in availableActions"
                                                    :key="action.name"
                                                    class="flex items-center gap-2 text-xs cursor-pointer py-0.5"
                                                    :class="editAllActionsSelected ? 'opacity-40 pointer-events-none' : ''"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        :checked="editAllActionsSelected || editSelectedActions.includes(action.name)"
                                                        :disabled="editAllActionsSelected"
                                                        @change="
                                                            editSelectedActions.includes(action.name)
                                                                ? editSelectedActions = editSelectedActions.filter(a => a !== action.name)
                                                                : editSelectedActions.push(action.name)
                                                        "
                                                    />
                                                    <span class="flex-1">{{ action.label }}</span>
                                                    <span v-for="tag in action.tags" :key="tag" class="text-[9px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground font-mono">{{ tag }}</span>
                                                </label>
                                            </div>
                                        </template>
                                    </div>
                                    <div v-if="editDeviceError" class="flex items-start gap-1.5 text-destructive text-xs">
                                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                                        {{ editDeviceError }}
                                    </div>
                                    <div class="flex gap-2 justify-end">
                                        <Button variant="ghost" size="sm" @click="editingDevice = null">Cancel</Button>
                                        <Button size="sm" class="gap-1.5" :disabled="savingEditDevice" @click="saveEditDevice">
                                            <RiLoader4Line v-if="savingEditDevice" class="size-3.5 animate-spin" />
                                            Save
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </template>

                    <!-- Token list view -->
                    <template v-else>
                        <div class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
                            <div v-if="loading" class="flex items-center justify-center py-12 text-muted-foreground">
                                <RiLoader4Line class="size-4 animate-spin mr-2" />
                                <span class="text-xs">Loading…</span>
                            </div>

                            <template v-else>
                                <!-- New token form -->
                                <div v-if="showNewForm" class="rounded-lg border border-border p-4 flex flex-col gap-3">
                                    <p class="text-xs font-semibold">New token</p>
                                    <div class="flex flex-col gap-1.5">
                                        <label class="text-[10px] font-medium text-muted-foreground">Name</label>
                                        <Input v-model="newName" placeholder="e.g. n8n Workflow" class="h-7 text-xs" @keydown.enter="createToken" />
                                    </div>
                                    <div class="flex flex-col gap-1.5">
                                        <label class="text-[10px] font-medium text-muted-foreground">Expires (optional)</label>
                                        <Input v-model="newExpiry" type="date" class="h-7 text-xs" />
                                    </div>
                                    <div v-if="createError" class="flex items-start gap-1.5 text-destructive text-xs">
                                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                                        {{ createError }}
                                    </div>
                                    <div class="flex gap-2 justify-end">
                                        <Button variant="ghost" size="sm" @click="showNewForm = false">Cancel</Button>
                                        <Button size="sm" class="gap-1.5" :disabled="creating || !newName.trim()" @click="createToken">
                                            <RiLoader4Line v-if="creating" class="size-3.5 animate-spin" />
                                            Create
                                        </Button>
                                    </div>
                                </div>

                                <div v-if="tokens.length === 0 && !showNewForm" class="flex flex-col items-center justify-center py-16 text-center gap-3">
                                    <RiKeyLine class="size-8 text-muted-foreground/30" />
                                    <div>
                                        <p class="text-xs font-medium">No tokens yet</p>
                                        <p class="text-[10px] text-muted-foreground mt-0.5">Create a token to grant scoped API access</p>
                                    </div>
                                </div>

                                <div
                                    v-for="token in tokens"
                                    :key="token.id"
                                    class="rounded-lg border border-border px-3 py-2.5 flex items-start gap-2.5 cursor-pointer hover:border-primary/40 hover:bg-muted/30 transition-colors"
                                    @click="selectedToken = token; addingDevice = false; rotatedToken = null"
                                >
                                    <RiKeyLine class="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center gap-2">
                                            <p class="text-xs font-medium truncate">{{ token.name }}</p>
                                            <span v-if="isExpired(token)" class="text-[10px] text-destructive shrink-0">expired</span>
                                        </div>
                                        <div class="flex items-center gap-3 mt-0.5">
                                            <span class="text-[10px] text-muted-foreground flex items-center gap-1">
                                                <RiTimeLine class="size-3" />
                                                {{ formatDate(token.expires_at) }}
                                            </span>
                                            <span class="text-[10px] text-muted-foreground">
                                                {{ token.devices.length }} device{{ token.devices.length !== 1 ? "s" : "" }}
                                            </span>
                                            <span v-if="token.last_used_at" class="text-[10px] text-muted-foreground">
                                                Used {{ formatDate(token.last_used_at) }}
                                            </span>
                                        </div>
                                    </div>
                                    <RiArrowLeftLine class="size-3.5 text-muted-foreground/40 rotate-180 shrink-0 mt-0.5" />
                                </div>
                            </template>
                        </div>

                        <div class="px-5 py-3 border-t border-border shrink-0">
                            <Button class="w-full gap-1.5" size="sm" variant="outline" @click="showNewForm = !showNewForm">
                                <RiAddLine class="size-3.5" />
                                New token
                            </Button>
                        </div>
                    </template>

                </div>
            </div>
        </Transition>

        <RotateDialog
            :show="!!rotateTarget"
            :token="rotateTarget"
            :rotating="rotating === rotateTarget?.id"
            @cancel="rotateTarget = null"
            @confirm="rotate(rotateTarget!).then(() => rotateTarget = null)"
        />

        <DeleteTokenDialog
            :show="!!deleteTarget"
            :token="deleteTarget"
            :deleting="deleting"
            @cancel="deleteTarget = null; deleteConfirmName = ''"
            @confirm="confirmDelete"
        />
    </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
