<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { Device, PluginMeta } from "@/lib/api";
import { RiRefreshLine, RiExternalLinkLine } from "@remixicon/vue";

defineProps<{
    device: Device;
    pluginMeta: PluginMeta | null;
    online: boolean | null;
    latency: number | null;
    pinging: boolean;
    docsUrl: string;
}>();

const emit = defineEmits<{
    ping: [];
}>();

function openDocs(url: string) {
    window.open(url, "_blank");
}
</script>

<template>
    <div class="flex items-center gap-4 px-6 py-3 border-b border-border shrink-0">
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
                <h1 class="text-sm font-semibold truncate">{{ device.name }}</h1>

                <!-- Online badge -->
                <span
                    class="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full border shrink-0"
                    :class="
                        online === null
                            ? 'border-border text-muted-foreground'
                            : online
                                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                : 'border-zinc-400/30 bg-zinc-400/10 text-zinc-500'
                    "
                >
                    <span
                        class="block size-1.5 rounded-full shrink-0"
                        :class="
                            online === null
                                ? 'bg-muted-foreground/40 animate-pulse'
                                : online ? 'bg-emerald-500' : 'bg-zinc-400'
                        "
                    />
                    <span>
                        {{ online === null
                            ? "checking…"
                            : online
                                ? `online${latency !== null ? ` · ${latency}ms` : ""}`
                                : "offline"
                        }}
                    </span>
                </span>
            </div>

            <p class="text-[10px] text-muted-foreground font-mono mt-0.5">
                {{ device.plugin_id }}
                <span v-if="pluginMeta?.version" class="opacity-60">· v{{ pluginMeta.version }}</span>
            </p>
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
            <Button
                variant="ghost"
                size="icon"
                :disabled="pinging"
                aria-label="Ping device"
                @click="emit('ping')"
            >
                <RiRefreshLine class="size-3.5" :class="pinging ? 'animate-spin' : ''" />
            </Button>
            <Button
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="openDocs(docsUrl)"
            >
                <RiExternalLinkLine class="size-3.5" />
                API Docs
            </Button>
        </div>
    </div>
</template>