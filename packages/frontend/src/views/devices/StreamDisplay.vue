<script setup lang="ts">
import { RiRadioLine, RiStopLine } from "@remixicon/vue";
import { Button } from "@/components/ui/button";

defineProps<{
    name: string;
    label: string;
    connected: boolean;
    messages: unknown[];
}>();

const emit = defineEmits<{
    toggle: [];
}>();
</script>

<template>
    <div class="flex flex-col gap-4">
        <!-- Endpoint + toggle -->
        <div class="flex items-center justify-between gap-3">
            <code class="text-[11px] font-mono text-muted-foreground">
                WS /stream/{{ name }}
            </code>
            <Button
                size="sm"
                class="gap-1.5 shrink-0"
                :variant="connected ? 'destructive' : 'default'"
                @click="emit('toggle')"
            >
                <RiStopLine v-if="connected" class="size-3.5" />
                <RiRadioLine v-else class="size-3.5" />
                {{ connected ? "Disconnect" : "Connect" }}
            </Button>
        </div>

        <!-- Message feed -->
        <div
            class="rounded-md border border-border bg-muted/20 overflow-hidden"
            :class="connected || messages.length ? '' : 'opacity-50'"
        >
            <!-- Feed header -->
            <div class="flex items-center gap-2 px-3 py-1.5 border-b border-border/60 bg-muted/30">
                <span
                    class="size-1.5 rounded-full shrink-0"
                    :class="connected ? 'bg-emerald-500 animate-pulse' : 'bg-muted-foreground/30'"
                />
                <span class="text-[10px] text-muted-foreground">
                    {{ connected ? "Live" : "Disconnected" }}
                    <span v-if="messages.length" class="tabular-nums">· {{ messages.length }} message{{ messages.length !== 1 ? "s" : "" }}</span>
                </span>
            </div>

            <!-- Messages -->
            <div class="flex flex-col-reverse overflow-auto max-h-72 divide-y divide-border/40">
                <div
                    v-if="!messages.length"
                    class="flex items-center justify-center py-8 text-[11px] text-muted-foreground italic"
                >
                    {{ connected ? "Waiting for messages…" : "Not connected" }}
                </div>
                <div
                    v-for="(msg, i) in messages"
                    :key="i"
                    class="px-3 py-2 font-mono text-[10px] text-foreground whitespace-pre-wrap break-all"
                >{{ JSON.stringify(msg, null, 2) }}</div>
            </div>
        </div>
    </div>
</template>
