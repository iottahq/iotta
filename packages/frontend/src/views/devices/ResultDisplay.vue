<script setup lang="ts">
import { computed } from "vue";
import { RiCheckLine, RiErrorWarningLine } from "@remixicon/vue";

const props = defineProps<{
    result: { ok: boolean; data: unknown } | null;
}>();

const formatted = computed(() => {
    if (!props.result) return "";
    return JSON.stringify(props.result.data, null, 2);
});
</script>

<template>
    <div
        v-if="result"
        class="flex flex-col gap-1.5"
    >
        <!-- Status bar -->
        <div
            class="flex items-center gap-1.5 text-[10px] font-medium px-2 py-1 rounded-md w-fit"
            :class="result.ok
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : 'bg-destructive/10 text-destructive'
            "
        >
            <RiCheckLine v-if="result.ok" class="size-3" />
            <RiErrorWarningLine v-else class="size-3" />
            {{ result.ok ? "Success" : "Error" }}
        </div>

        <!-- Body -->
        <pre
            class="rounded-md border px-3 py-2.5 font-mono text-[11px] whitespace-pre-wrap break-all overflow-auto max-h-64"
            :class="result.ok
                ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-800 dark:text-emerald-300'
                : 'border-destructive/20 bg-destructive/5 text-destructive'
            "
        >{{ formatted }}</pre>
    </div>
</template>
