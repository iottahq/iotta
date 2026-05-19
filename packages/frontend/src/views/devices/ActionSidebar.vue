<script setup lang="ts">
import { RiPlayLine, RiDownloadLine, RiRadioLine } from "@remixicon/vue";

interface ActionEntry {
    name: string;
    label: string;
    category: "send" | "request" | "stream";
}

defineProps<{
    actions: ActionEntry[];
    selected: string | null;
    connectedStreams: Record<string, boolean>;
}>();

const emit = defineEmits<{
    select: [name: string];
}>();

const categoryIcons = {
    send: RiPlayLine,
    request: RiDownloadLine,
    stream: RiRadioLine,
} as const;

const categoryLabels = {
    send: "Send",
    request: "Request",
    stream: "Stream",
} as const;
</script>

<template>
    <aside class="w-56 shrink-0 border-r border-border flex flex-col overflow-y-auto bg-sidebar">
        <template
            v-for="category in (['send', 'request', 'stream'] as const)"
            :key="category"
        >
            <!-- Only render section if there are actions in this category -->
            <template v-if="actions.some((a) => a.category === category)">
                <!-- Section label -->
                <div class="px-3 pt-4 pb-1.5 flex items-center gap-1.5">
                    <component
                        :is="categoryIcons[category]"
                        class="size-3 text-muted-foreground/70"
                    />
                    <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                        {{ categoryLabels[category] }}
                    </span>
                </div>

                <!-- Actions in this category -->
                <button
                    v-for="action in actions.filter((a) => a.category === category)"
                    :key="action.name"
                    class="flex items-center gap-2 w-full px-3 py-2 text-left text-xs transition-colors rounded-none"
                    :class="
                        selected === action.name
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                            : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    "
                    @click="emit('select', action.name)"
                >
                    <!-- Stream connected indicator -->
                    <span
                        v-if="category === 'stream'"
                        class="shrink-0 size-1.5 rounded-full"
                        :class="connectedStreams[action.name] ? 'bg-emerald-500' : 'bg-muted-foreground/30'"
                    />
                    <span class="truncate">{{ action.label }}</span>
                </button>

                <div class="mx-3 my-1 h-px bg-border/60 last:hidden" />
            </template>
        </template>
    </aside>
</template>
