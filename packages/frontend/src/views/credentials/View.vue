<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api, type Credential, type PluginMeta, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    RiAddLine,
    RiErrorWarningLine,
    RiKeyLine,
    RiLoader4Line,
    RiPencilLine,
} from "@remixicon/vue";
import NewDialog from "./NewDialog.vue";
import EditDialog from "./EditDialog.vue";
import DeleteDialog from "./DeleteDialog.vue";

// ── State ──────────────────────────────────────────────────────────────────

const credentials = ref<Credential[]>([]);
const devices = ref<
    { id: string; name: string; credential_id: string; plugin_id: string }[]
>([]);
const plugins = ref<PluginMeta[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Edit dialog
const selected = ref<Credential | null>(null);
const saving = ref(false);
const saveError = ref<string | null>(null);

// Delete dialog
const confirmDelete = ref(false);
const deleting = ref(false);

// New dialog
const showNew = ref(false);
const creating = ref(false);
const createError = ref<string | null>(null);

// ── Helpers ────────────────────────────────────────────────────────────────

function devicesUsing(credId: string) {
    return devices.value.filter((d) => d.credential_id === credId);
}

function pluginName(pluginId: string): string {
    return plugins.value.find((p) => p.id === pluginId)?.name ?? pluginId;
}

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

// ── New dialog ─────────────────────────────────────────────────────────────

function openNew() {
    createError.value = null;
    showNew.value = true;
}

async function createCredential(name: string, data: Record<string, string>) {
    creating.value = true;
    createError.value = null;
    try {
        const cred = await api.credentials.create({ name, data });
        credentials.value.push(cred);
        showNew.value = false;
    } catch (e) {
        createError.value = e instanceof ApiError ? e.detail : "Failed to create";
    } finally {
        creating.value = false;
    }
}

// ── Edit dialog ────────────────────────────────────────────────────────────

function openEdit(cred: Credential) {
    selected.value = cred;
    saveError.value = null;
    confirmDelete.value = false;
}

function closeEdit() {
    selected.value = null;
    confirmDelete.value = false;
}

async function saveCredential(name: string, data: Record<string, string>) {
    if (!selected.value) return;
    saving.value = true;
    saveError.value = null;
    try {
        const updated = await api.credentials.update(selected.value.id, {
            name,
            data,
        });
        const idx = credentials.value.findIndex((c) => c.id === updated.id);
        if (idx !== -1) credentials.value[idx] = updated;
        // Sync the dialog's view with the freshly saved data
        selected.value = updated;
    } catch (e) {
        saveError.value = e instanceof ApiError ? e.detail : "Failed to save";
    } finally {
        saving.value = false;
    }
}

// ── Delete dialog ──────────────────────────────────────────────────────────

async function deleteCredential() {
    if (!selected.value) return;
    deleting.value = true;
    try {
        await api.credentials.delete(selected.value.id);
        credentials.value = credentials.value.filter(
            (c) => c.id !== selected.value!.id,
        );
        closeEdit();
    } catch (e) {
        saveError.value = e instanceof ApiError ? e.detail : "Failed to delete";
    } finally {
        deleting.value = false;
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
                    class="flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors group"
                    @click="openEdit(cred)"
                >
                    <div
                        class="shrink-0 flex items-center justify-center size-7 rounded-md bg-muted/60 text-muted-foreground"
                    >
                        <RiKeyLine class="size-3.5" />
                    </div>
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
                            <template v-else>Not used by any device</template>
                        </p>
                    </div>
                    <div class="shrink-0 flex items-center gap-2">
                        <span class="text-[10px] text-muted-foreground tabular-nums">
                            {{ Object.keys(cred.data).length }} 
                            field
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
    
    <NewDialog
        :show="showNew"
        :saving="creating"
        :error="createError"
        @update:show="showNew = $event"
        @create="createCredential"
    />
    
    <EditDialog
        :credential="selected"
        :saving="saving"
        :error="saveError"
        :used-by-devices="selected ? devicesUsing(selected.id) : []"
        :plugin-name="pluginName"
        @save="saveCredential"
        @close="closeEdit"
        @delete="confirmDelete = true"
    />
    
    <DeleteDialog
        :show="confirmDelete"
        :credential="selected"
        :deleting="deleting"
        :used-by-count="selected ? devicesUsing(selected.id).length : 0"
        @cancel="confirmDelete = false"
        @confirm="deleteCredential"
    />
</template>
