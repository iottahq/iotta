<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api, type PluginMeta, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import ContextMenu from "@/views/home/ContextMenu.vue";
import type { ContextMenuItem } from "@/views/home/ContextMenu.vue";
import PluginEditorDialog from "@/views/plugins/editor/View.vue";
import {
    RiSearchLine,
    RiRefreshLine,
    RiPlugLine,
    RiSignalWifiLine,
    RiExternalLinkLine,
    RiErrorWarningLine,
    RiLoader4Line,
    RiAddLine,
    RiPencilLine,
    RiDeleteBinLine,
} from "@remixicon/vue";

type Tab = "protocols" | "devices";

const activeTab = ref<Tab>("protocols");
const search = ref("");
const reloading = ref(false);

const protocols = ref<PluginMeta[]>([]);
const devices = ref<PluginMeta[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Context menu 

const contextMenu = ref<{ x: number; y: number; items: ContextMenuItem[] } | null>(null);

// Plugin editor

const showEditor   = ref(false);
const editPluginId = ref<string | null>(null);

function openNewPlugin() {
    editPluginId.value = null;
    showEditor.value   = true;
}

function openEditPlugin(pluginId: string) {
    editPluginId.value = pluginId;
    showEditor.value   = true;
}

function onPluginSaved(_id: string) {
    load();
}

// Delete

const deleteTarget  = ref<PluginMeta | null>(null);
const deleting      = ref(false);
const deleteError   = ref<string | null>(null);
const affectedCount = ref(0);

async function openDeleteConfirm(plugin: PluginMeta) {
    deleteTarget.value = plugin;
    deleteError.value  = null;
    try {
        const devList = await api.devices.list();
        affectedCount.value = devList.filter((d) => d.plugin_id === plugin.id).length;
    } catch {
        affectedCount.value = 0;
    }
}

async function confirmDelete() {
    if (!deleteTarget.value) return;
    deleting.value    = true;
    deleteError.value = null;
    try {
        await fetch(
            `http://localhost:8000/plugins/devices/${deleteTarget.value.id}/files`,
            {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("iotta_token") ?? ""}`,
                },
            },
        );
        deleteTarget.value = null;
        await load();
    } catch (e) {
        deleteError.value = e instanceof Error ? e.message : "Failed to delete plugin.";
    } finally {
        deleting.value = false;
    }
}

// Context menu handler

function onDevicePluginContextMenu(e: MouseEvent, plugin: PluginMeta) {
    e.preventDefault();
    const isCore = (plugin as any).scope === "core";
    contextMenu.value = {
        x: e.clientX,
        y: e.clientY,
        items: [
            {
                label: isCore ? "Edit (core plugin)" : "Edit",
                icon: RiPencilLine,
                action: () => openEditPlugin(plugin.id),
            },
            { label: "", separator: true, action: () => {} },
            {
                label: "Delete",
                icon: RiDeleteBinLine,
                variant: "destructive",
                action: () => openDeleteConfirm(plugin),
            },
        ],
    };
}

// Load

async function load() {
    loading.value = true;
    error.value   = null;
    try {
        const [p, d] = await Promise.all([
            api.plugins.protocols.list(),
            api.plugins.devices.list(),
        ]);
        protocols.value = p.items;
        devices.value   = d.items;
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to load plugins";
    } finally {
        loading.value = false;
    }
}

async function reload() {
    reloading.value = true;
    try {
        await api.plugins.reloadAll();
        await load();
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Reload failed";
    } finally {
        reloading.value = false;
    }
}

onMounted(load);

const filtered = computed(() => {
    const q    = search.value.toLowerCase().trim();
    const list = activeTab.value === "protocols" ? protocols.value : devices.value;
    if (!q) return list;
    return list.filter(
        (p) =>
            p.name.toLowerCase().includes(q) ||
            p.id.toLowerCase().includes(q) ||
            p.description?.toLowerCase().includes(q) ||
            p.tags?.some((t) => t.toLowerCase().includes(q)),
    );
});

const counts = computed(() => ({
    protocols: protocols.value.length,
    devices:   devices.value.length,
}));

function scopeOf(plugin: PluginMeta): string {
    return (plugin as any).scope ?? "community";
}
</script>

<template>
    <div class="flex flex-col h-full">
        <!-- Header -->
        <div class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border">
            <div>
                <h1 class="text-sm font-semibold">Plugins</h1>
                <p class="text-xs text-muted-foreground mt-0.5">
                    Loaded protocol and device adapters
                </p>
            </div>
            <Button variant="outline" size="sm" :disabled="reloading" @click="reload" class="gap-1.5">
                <RiLoader4Line v-if="reloading" class="size-3.5 animate-spin" />
                <RiRefreshLine v-else class="size-3.5" />
                Reload all
            </Button>
        </div>

        <!-- Tabs + Search -->
        <div class="flex items-center gap-2 px-6 py-3 border-b border-border">
            <div class="flex items-center gap-px bg-muted rounded-md p-0.5">
                <button
                    v-for="tab in ['protocols', 'devices'] as Tab[]"
                    :key="tab"
                    @click="activeTab = tab; search = '';"
                    :class="[
                        'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                        activeTab === tab
                            ? 'bg-background text-foreground shadow-xs'
                            : 'text-muted-foreground hover:text-foreground',
                    ]"
                >
                    <RiSignalWifiLine v-if="tab === 'protocols'" class="size-3.5" />
                    <RiPlugLine v-else class="size-3.5" />
                    {{ tab === "protocols" ? "Protocols" : "Devices" }}
                    <span class="ml-0.5 tabular-nums text-[10px] text-muted-foreground">
                        {{ tab === "protocols" ? counts.protocols : counts.devices }}
                    </span>
                </button>
            </div>

            <div class="relative flex-1 max-w-xs">
                <RiSearchLine class="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
                <Input v-model="search" placeholder="Search…" class="pl-7 h-7 text-xs" />
            </div>

            <Button
                v-if="activeTab === 'devices'"
                size="sm"
                class="gap-1.5 ml-auto"
                @click="openNewPlugin"
            >
                <RiAddLine class="size-3.5" />
                New plugin
            </Button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto px-6 py-4">
            <div v-if="loading" class="flex items-center justify-center py-16 text-muted-foreground">
                <RiLoader4Line class="size-5 animate-spin mr-2" />
                <span class="text-xs">Loading plugins…</span>
            </div>

            <div v-else-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs">
                <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                {{ error }}
            </div>

            <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
                <RiSearchLine class="size-8 text-muted-foreground/40 mb-3" />
                <p class="text-xs text-muted-foreground">
                    No plugins match
                    <span class="font-medium text-foreground">"{{ search }}"</span>
                </p>
            </div>

            <div
                v-else
                class="grid gap-2"
                style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));"
            >
                <div
                    v-for="plugin in filtered"
                    :key="plugin.id"
                    class="group flex flex-col gap-2.5 rounded-lg border border-border bg-card px-4 py-3 hover:border-primary/40 hover:bg-accent/5 transition-colors"
                    :class="activeTab === 'devices' ? 'cursor-context-menu' : ''"
                    @contextmenu="activeTab === 'devices' ? onDevicePluginContextMenu($event, plugin) : undefined"
                >
                    <!-- Top row -->
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="flex items-center gap-1.5 flex-wrap">
                                <span class="text-xs font-semibold text-foreground truncate">{{ plugin.name }}</span>

                                <span
                                    v-if="plugin.status"
                                    :class="[
                                        'shrink-0 text-[9px] font-medium px-1.5 py-px rounded-full border',
                                        plugin.status === 'stable'
                                            ? 'border-emerald-500/30 text-emerald-600 bg-emerald-500/10'
                                            : 'border-amber-500/30 text-amber-600 bg-amber-500/10',
                                    ]"
                                >{{ plugin.status }}</span>

                                <!-- scope badge (device plugins only) -->
                                <span
                                    v-if="activeTab === 'devices'"
                                    :class="[
                                        'shrink-0 text-[9px] font-medium px-1.5 py-px rounded-full border',
                                        scopeOf(plugin) === 'core'
                                            ? 'border-sky-500/30 text-sky-600 bg-sky-500/10'
                                            : 'border-violet-500/30 text-violet-600 bg-violet-500/10',
                                    ]"
                                >{{ scopeOf(plugin) }}</span>

                                <!-- TODO: registry badge – issue #36
                                <span class="shrink-0 text-[9px] font-medium px-1.5 py-px rounded-full border border-border text-muted-foreground/50 cursor-not-allowed" title="Plugin registry coming soon">
                                    registry
                                </span>
                                -->
                            </div>
                            <p class="text-[10px] text-muted-foreground font-mono mt-0.5">{{ plugin.id }}</p>
                        </div>
                        <span class="shrink-0 text-[10px] text-muted-foreground tabular-nums">v{{ plugin.version }}</span>
                    </div>

                    <!-- Description -->
                    <p v-if="plugin.description" class="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                        {{ plugin.description.trim() }}
                    </p>

                    <!-- Tags -->
                    <div v-if="plugin.tags?.length" class="flex flex-wrap gap-1">
                        <span v-for="tag in plugin.tags" :key="tag" class="text-[10px] px-1.5 py-px rounded bg-muted text-muted-foreground">
                            {{ tag }}
                        </span>
                    </div>

                    <!-- Footer -->
                    <div
                        v-if="plugin.author?.name || activeTab === 'devices'"
                        class="flex items-center justify-between gap-2 pt-1 border-t border-border/60"
                    >
                        <span v-if="plugin.author?.name" class="text-[10px] text-muted-foreground truncate">
                            {{ plugin.author.name }}
                            <span v-if="plugin.author.organisation" class="opacity-60">· {{ plugin.author.organisation }}</span>
                        </span>
                        <span v-else class="flex-1" />

                        <div class="flex items-center gap-1 shrink-0">
                            <a
                                v-if="plugin.author?.url"
                                :href="plugin.author.url"
                                target="_blank"
                                rel="noopener"
                                class="text-muted-foreground hover:text-foreground transition-colors"
                                @click.stop
                            >
                                <RiExternalLinkLine class="size-3" />
                            </a>
                            <button
                                v-if="activeTab === 'devices'"
                                class="text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
                                :title="scopeOf(plugin) === 'core' ? 'Edit core plugin' : 'Edit plugin'"
                                @click.stop="openEditPlugin(plugin.id)"
                            >
                                <RiPencilLine class="size-3" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Context menu -->
    <ContextMenu
        v-if="contextMenu"
        :x="contextMenu.x"
        :y="contextMenu.y"
        :items="contextMenu.items"
        @close="contextMenu = null"
    />

    <!-- Plugin editor -->
    <PluginEditorDialog
        :show="showEditor"
        :edit-plugin-id="editPluginId"
        @update:show="showEditor = $event"
        @saved="onPluginSaved"
    />

    <!-- Delete confirmation -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="deleteTarget" class="fixed inset-0 z-[60] flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50" @click="deleteTarget = null" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4">
                    <h2 class="text-sm font-semibold">Delete plugin?</h2>
                    <p class="text-xs text-muted-foreground mt-1.5">
                        The plugin directory for
                        <span class="font-medium text-foreground font-mono">{{ deleteTarget.id }}</span>
                        will be permanently deleted from disk.
                    </p>

                    <div v-if="affectedCount > 0" class="mt-2 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        <span>
                            <span class="font-medium">{{ affectedCount }} device{{ affectedCount !== 1 ? "s" : "" }}</span>
                            use this plugin and will no longer mount after deletion.
                        </span>
                    </div>

                    <div v-if="scopeOf(deleteTarget) === 'core'" class="mt-2 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        This is a <span class="font-medium mx-0.5">core plugin</span>. Deleting it may break other functionality.
                    </div>

                    <div v-if="deleteError" class="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs">
                        <RiErrorWarningLine class="size-3.5 shrink-0 mt-px" />
                        {{ deleteError }}
                    </div>

                    <div class="flex gap-2 justify-end mt-4">
                        <Button variant="outline" size="sm" @click="deleteTarget = null">Cancel</Button>
                        <Button variant="destructive" size="sm" class="gap-1.5" :disabled="deleting" @click="confirmDelete">
                            <RiLoader4Line v-if="deleting" class="size-3.5 animate-spin" />
                            <RiDeleteBinLine v-else class="size-3.5" />
                            Delete anyway
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>