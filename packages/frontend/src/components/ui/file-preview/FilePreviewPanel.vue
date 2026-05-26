<script setup lang="ts">
import { RiCloseLine } from "@remixicon/vue";

defineProps<{
    show: boolean;
    filename: string;
    content: string;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
}>();
</script>

<template>
    <Transition name="slide-right">
        <div
            v-if="show"
            class="flex-1 min-w-0 self-stretch border-l border-border bg-muted/20 flex flex-col overflow-hidden"
        >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-border shrink-0">
                <span class="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide font-mono">
                    {{ filename }}
                </span>
                <button
                    class="text-muted-foreground hover:text-foreground transition-colors"
                    @click="emit('update:show', false)"
                >
                    <RiCloseLine class="size-3.5" />
                </button>
            </div>
            <pre class="flex-1 overflow-y-auto overflow-x-auto px-4 py-3 font-mono text-[10px] text-foreground whitespace-pre leading-relaxed">{{ content }}</pre>
        </div>
    </Transition>
</template>

<style scoped>
.slide-right-enter-active,
.slide-right-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-right-enter-from,
.slide-right-leave-to    { opacity: 0; transform: translateX(8px); }
.slide-right-enter-to,
.slide-right-leave-from  { opacity: 1; transform: translateX(0); }
</style>