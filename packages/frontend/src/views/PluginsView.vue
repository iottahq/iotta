<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api, type PluginMeta, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    RiSearchLine,
    RiRefreshLine,
    RiPlugLine,
    RiSignalWifiLine,
    RiExternalLinkLine,
    RiErrorWarningLine,
    RiLoader4Line,
} from "@remixicon/vue";

// ── State ──────────────────────────────────────────────────────────────────────

type Tab = "protocols" | "devices";

const activeTab = ref<Tab>("protocols");
const search = ref("");
const reloading = ref(false);

const protocols = ref<PluginMeta[]>([]);
const devices = ref<PluginMeta[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// ── Data fetching ──────────────────────────────────────────────────────────────

async function load() {
    loading.value = true;
    error.value = null;
    try {
        const [p, d] = await Promise.all([
            api.plugins.protocols.list(),
            api.plugins.devices.list(),
        ]);
        protocols.value = p.items;
        devices.value = d.items;
    } catch (e) {
        error.value =
            e instanceof ApiError ? e.detail : "Failed to load plugins";
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

// ── Filtered lists ─────────────────────────────────────────────────────────────

const filtered = computed(() => {
    const q = search.value.toLowerCase().trim();
    const list =
        activeTab.value === "protocols" ? protocols.value : devices.value;
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
    devices: devices.value.length,
}));
</script>

<template>
    <div class="flex flex-col h-full">
        <!-- Header -->
        <div
            class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border"
        >
            <div>
                <h1 class="text-sm font-semibold">Plugins</h1>
                <p class="text-xs text-muted-foreground mt-0.5">
                    Loaded protocol and device adapters
                </p>
            </div>
            <Button
                variant="outline"
                size="sm"
                :disabled="reloading"
                @click="reload"
                class="gap-1.5"
            >
                <RiLoader4Line v-if="reloading" class="size-3.5 animate-spin" />
                <RiRefreshLine v-else class="size-3.5" />
                Reload all
            </Button>
        </div>

        <!-- Tabs + Search -->
        <div class="flex items-center gap-2 px-6 py-3 border-b border-border">
            <!-- Tab switcher -->
            <div class="flex items-center gap-px bg-muted rounded-md p-0.5">
                <button
                    v-for="tab in ['protocols', 'devices'] as Tab[]"
                    :key="tab"
                    @click="
                        activeTab = tab;
                        search = '';
                    "
                    :class="[
                        'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                        activeTab === tab
                            ? 'bg-background text-foreground shadow-xs'
                            : 'text-muted-foreground hover:text-foreground',
                    ]"
                >
                    <RiSignalWifiLine
                        v-if="tab === 'protocols'"
                        class="size-3.5"
                    />
                    <RiPlugLine v-else class="size-3.5" />
                    {{ tab === "protocols" ? "Protocols" : "Devices" }}
                    <span
                        class="ml-0.5 tabular-nums text-[10px] text-muted-foreground"
                    >
                        {{
                            tab === "protocols"
                                ? counts.protocols
                                : counts.devices
                        }}
                    </span>
                </button>
            </div>

            <!-- Search -->
            <div class="relative flex-1 max-w-xs">
                <RiSearchLine
                    class="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none"
                />
                <Input
                    v-model="search"
                    placeholder="Search…"
                    class="pl-7 h-7 text-xs"
                />
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto px-6 py-4">
            <!-- Loading -->
            <div
                v-if="loading"
                class="flex items-center justify-center py-16 text-muted-foreground"
            >
                <RiLoader4Line class="size-5 animate-spin mr-2" />
                <span class="text-xs">Loading plugins…</span>
            </div>

            <!-- Error -->
            <div
                v-else-if="error"
                class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2.5 text-xs"
            >
                <RiErrorWarningLine class="size-4 shrink-0 mt-px" />
                {{ error }}
            </div>

            <!-- Empty search -->
            <div
                v-else-if="filtered.length === 0"
                class="flex flex-col items-center justify-center py-16 text-center"
            >
                <RiSearchLine class="size-8 text-muted-foreground/40 mb-3" />
                <p class="text-xs text-muted-foreground">
                    No plugins match
                    <span class="font-medium text-foreground"
                        >"{{ search }}"</span
                    >
                </p>
            </div>

            <!-- Grid -->
            <div
                v-else
                class="grid gap-2"
                style="
                    grid-template-columns: repeat(
                        auto-fill,
                        minmax(280px, 1fr)
                    );
                "
            >
                <div
                    v-for="plugin in filtered"
                    :key="plugin.id"
                    class="group flex flex-col gap-2.5 rounded-lg border border-border bg-card px-4 py-3 hover:border-primary/40 hover:bg-accent/5 transition-colors"
                >
                    <!-- Top row: name + version -->
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="flex items-center gap-1.5">
                                <span
                                    class="text-xs font-semibold text-foreground truncate"
                                    >{{ plugin.name }}</span
                                >
                                <span
                                    v-if="plugin.status"
                                    :class="[
                                        'shrink-0 text-[9px] font-medium px-1.5 py-px rounded-full border',
                                        plugin.status === 'stable'
                                            ? 'border-emerald-500/30 text-emerald-600 bg-emerald-500/10'
                                            : 'border-amber-500/30 text-amber-600 bg-amber-500/10',
                                    ]"
                                >
                                    {{ plugin.status }}
                                </span>
                            </div>
                            <p
                                class="text-[10px] text-muted-foreground font-mono mt-0.5"
                            >
                                {{ plugin.id }}
                            </p>
                        </div>
                        <span
                            class="shrink-0 text-[10px] text-muted-foreground tabular-nums"
                            >v{{ plugin.version }}</span
                        >
                    </div>

                    <!-- Description -->
                    <p
                        v-if="plugin.description"
                        class="text-[11px] text-muted-foreground leading-relaxed line-clamp-2"
                    >
                        {{ plugin.description.trim() }}
                    </p>

                    <!-- Tags -->
                    <div
                        v-if="plugin.tags?.length"
                        class="flex flex-wrap gap-1"
                    >
                        <span
                            v-for="tag in plugin.tags"
                            :key="tag"
                            class="text-[10px] px-1.5 py-px rounded bg-muted text-muted-foreground"
                        >
                            {{ tag }}
                        </span>
                    </div>

                    <!-- Footer: author -->
                    <div
                        v-if="plugin.author?.name"
                        class="flex items-center justify-between gap-2 pt-1 border-t border-border/60"
                    >
                        <span
                            class="text-[10px] text-muted-foreground truncate"
                        >
                            {{ plugin.author.name }}
                            <span
                                v-if="plugin.author.organisation"
                                class="opacity-60"
                                >· {{ plugin.author.organisation }}</span
                            >
                        </span>
                        <a
                            v-if="plugin.author.url"
                            :href="plugin.author.url"
                            target="_blank"
                            rel="noopener"
                            class="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <RiExternalLinkLine class="size-3" />
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
