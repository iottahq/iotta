<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { api, type RegistryPlugin, type RegistryIndex, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import PluginInstallCustomModal from "@/views/plugins/PluginInstallCustomModal.vue";
import {
    RiSearchLine,
    RiPlugLine,
    RiSignalWifiLine,
    RiDownloadLine,
    RiCheckLine,
    RiLoader4Line,
    RiErrorWarningLine,
    RiCloseLine,
    RiExternalLinkLine,
    RiStoreLine,
    RiUploadLine,
} from "@remixicon/vue";

const props = defineProps<{
    show: boolean;
    installedDeviceIds: string[];
    installedProtocolIds: string[];
}>();

const emit = defineEmits<{
    "update:show": [value: boolean];
    installed: [plugin: RegistryPlugin];
}>();

type Tab = "devices" | "protocols";

const activeTab = ref<Tab>("devices");
const search = ref("");
const registry = ref<RegistryIndex | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

// Per-plugin install state: id → "idle" | "installing" | "done" | "error"
const installState = ref<Map<string, "idle" | "installing" | "done" | "error">>(new Map());

function stateOf(id: string) {
    return installState.value.get(id) ?? "idle";
}

function isInstalled(plugin: RegistryPlugin) {
    if (plugin.type === "devices") return props.installedDeviceIds.includes(plugin.id);
    return props.installedProtocolIds.includes(plugin.id);
}

async function install(plugin: RegistryPlugin) {
    installState.value = new Map(installState.value).set(plugin.id, "installing");
    try {
        await api.plugins.registry.install(plugin.type, plugin.id);
        installState.value = new Map(installState.value).set(plugin.id, "done");
        emit("installed", plugin);
    } catch (e) {
        installState.value = new Map(installState.value).set(plugin.id, "error");
    }
}

async function load() {
    loading.value = true;
    error.value = null;
    registry.value = null;
    installState.value = new Map();
    try {
        registry.value = await api.plugins.registry.fetch();
    } catch (e) {
        error.value = e instanceof ApiError ? e.detail : "Failed to reach plugin registry";
    } finally {
        loading.value = false;
    }
}

watch(() => props.show, (val) => {
    if (val) {
        search.value = "";
        activeTab.value = "devices";
        load();
    }
});

const filtered = computed(() => {
    if (!registry.value) return [];
    const q = search.value.toLowerCase().trim();
    const list = registry.value.plugins[activeTab.value];
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
    devices: registry.value?.plugins.devices.length ?? 0,
    protocols: registry.value?.plugins.protocols.length ?? 0,
}));

const showCustomInstall = ref(false);
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div class="absolute inset-0 bg-black/50" @click="emit('update:show', false)" />

                <div class="relative z-10 flex flex-col w-full max-w-3xl max-h-[80vh] rounded-xl border border-border bg-card shadow-2xl overflow-hidden">

                    <!-- Header -->
                    <div class="flex items-center gap-3 px-5 py-4 border-b border-border shrink-0">
                        <RiStoreLine class="size-4 text-muted-foreground shrink-0" />
                        <div class="flex-1 min-w-0">
                            <h2 class="text-sm font-semibold">Plugin Store</h2>
                            <p class="text-xs text-muted-foreground">Browse and install plugins from the iottahq registry</p>
                        </div>
                        <button
                            class="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors border border-border rounded-md px-2 py-1"
                            title="Install from git or zip"
                            @click="showCustomInstall = true"
                        >
                            <RiUploadLine class="size-3.5" />
                            From source
                        </button>
                        <button
                            class="text-muted-foreground hover:text-foreground transition-colors"
                            @click="emit('update:show', false)"
                        >
                            <RiCloseLine class="size-4" />
                        </button>
                    </div>

                    <!-- Tabs + Search -->
                    <div class="flex items-center gap-2 px-5 py-2.5 border-b border-border shrink-0">
                        <div class="flex items-center gap-px bg-muted rounded-md p-0.5">
                            <button
                                v-for="tab in ['devices', 'protocols'] as Tab[]"
                                :key="tab"
                                @click="activeTab = tab; search = '';"
                                :class="[
                                    'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                                    activeTab === tab
                                        ? 'bg-background text-foreground shadow-xs'
                                        : 'text-muted-foreground hover:text-foreground',
                                ]"
                            >
                                <RiPlugLine v-if="tab === 'devices'" class="size-3.5" />
                                <RiSignalWifiLine v-else class="size-3.5" />
                                {{ tab === "devices" ? "Devices" : "Protocols" }}
                                <span class="ml-0.5 tabular-nums text-[10px] text-muted-foreground">
                                    {{ tab === "devices" ? counts.devices : counts.protocols }}
                                </span>
                            </button>
                        </div>

                        <div class="relative flex-1 max-w-xs">
                            <RiSearchLine class="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
                            <Input v-model="search" placeholder="Search…" class="pl-7 h-7 text-xs" />
                        </div>
                    </div>

                    <!-- Body -->
                    <div class="flex-1 overflow-y-auto px-5 py-4">

                        <!-- Loading -->
                        <div v-if="loading" class="flex items-center justify-center py-16 text-muted-foreground">
                            <RiLoader4Line class="size-5 animate-spin mr-2" />
                            <span class="text-xs">Fetching registry…</span>
                        </div>

                        <!-- Error -->
                        <div v-else-if="error" class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs">
                            <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                            {{ error }}
                        </div>

                        <!-- Empty search -->
                        <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
                            <RiSearchLine class="size-8 text-muted-foreground/40 mb-3" />
                            <p class="text-xs text-muted-foreground">
                                No plugins match
                                <span class="font-medium text-foreground">"{{ search }}"</span>
                            </p>
                        </div>

                        <!-- Grid -->
                        <div
                            v-else
                            class="grid gap-2"
                            style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));"
                        >
                            <div
                                v-for="plugin in filtered"
                                :key="plugin.id"
                                class="flex flex-col gap-2.5 rounded-lg border border-border bg-background px-4 py-3"
                            >
                                <!-- Top row -->
                                <div class="flex items-start justify-between gap-2">
                                    <div class="shrink-0 w-8 h-8 rounded-md border border-border bg-muted/30 flex items-center justify-center overflow-hidden">
                                        <img
                                            v-if="plugin.icon_url"
                                            :src="plugin.icon_url"
                                            :alt="plugin.name"
                                            class="w-full h-full object-contain p-0.5"
                                        />
                                        <RiPlugLine v-else class="size-4 text-muted-foreground/40" />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            <span class="text-xs font-semibold truncate">{{ plugin.name }}</span>
                                            <span
                                                v-if="plugin.status"
                                                :class="[
                                                    'shrink-0 text-[9px] font-medium px-1.5 py-px rounded-full border',
                                                    plugin.status === 'stable'
                                                        ? 'border-emerald-500/30 text-emerald-600 bg-emerald-500/10'
                                                        : 'border-amber-500/30 text-amber-600 bg-amber-500/10',
                                                ]"
                                            >{{ plugin.status }}</span>
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
                                <div class="flex items-center justify-between gap-2 pt-1 border-t border-border/60">
                                    <span v-if="plugin.author?.name" class="text-[10px] text-muted-foreground truncate">
                                        {{ plugin.author.name }}
                                        <span v-if="plugin.author.organisation" class="opacity-60">· {{ plugin.author.organisation }}</span>
                                    </span>
                                    <span v-else class="flex-1" />

                                    <div class="flex items-center gap-2 shrink-0">
                                        <a
                                            v-if="plugin.author?.url"
                                            :href="plugin.author.url"
                                            target="_blank"
                                            rel="noopener"
                                            class="text-muted-foreground hover:text-foreground transition-colors"
                                        >
                                            <RiExternalLinkLine class="size-3" />
                                        </a>

                                        <!-- Already installed -->
                                        <span
                                            v-if="isInstalled(plugin) || stateOf(plugin.id) === 'done'"
                                            class="flex items-center gap-1 text-[10px] text-emerald-600 font-medium"
                                        >
                                            <RiCheckLine class="size-3" />
                                            Installed
                                        </span>

                                        <!-- Install button -->
                                        <Button
                                            v-else
                                            size="sm"
                                            variant="outline"
                                            class="h-6 px-2 gap-1 text-[10px]"
                                            :disabled="stateOf(plugin.id) === 'installing'"
                                            @click="install(plugin)"
                                        >
                                            <RiLoader4Line v-if="stateOf(plugin.id) === 'installing'" class="size-3 animate-spin" />
                                            <RiDownloadLine v-else class="size-3" />
                                            {{ stateOf(plugin.id) === 'installing' ? 'Installing…' : 'Install' }}
                                        </Button>

                                        <!-- Error indicator -->
                                        <span
                                            v-if="stateOf(plugin.id) === 'error'"
                                            class="text-[10px] text-destructive"
                                            title="Installation failed"
                                        >
                                            <RiErrorWarningLine class="size-3" />
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
    <PluginInstallCustomModal
        :show="showCustomInstall"
        @update:show="showCustomInstall = $event"
        @installed="load"
    />
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
