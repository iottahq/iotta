<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import ResultDisplay from "./ResultDisplay.vue";
import { RiPlayLine, RiLoader4Line } from "@remixicon/vue";

const props = defineProps<{
    actionName: string | null;
    actionDef: Record<string, any> | null;
    body: string;
    running: boolean;
    result: { ok: boolean; data: unknown } | null;
}>();

const emit = defineEmits<{
    "update:body": [v: string];
    run: [];
}>();

const hasFileUpload = computed(() =>
    Object.values<any>(props.actionDef?.input ?? {}).some((v) => v.type === "bytes"),
);

const endpoint = computed(() =>
    props.actionName ? `POST /action/${props.actionName}` : ""
);
</script>

<template>
    <!-- Empty state -->
    <div
        v-if="!actionName"
        class="flex flex-col items-center justify-center h-full text-center gap-2 text-muted-foreground select-none"
    >
        <p class="text-xs">Select an action</p>
    </div>

    <div v-else class="flex flex-col gap-5 h-full overflow-y-auto px-6 py-5">
        <!-- Action title + endpoint -->
        <div class="flex flex-col gap-1">
            <h2 class="text-sm font-semibold">{{ actionDef?.label ?? actionName }}</h2>
            <code class="text-[11px] font-mono text-muted-foreground">{{ endpoint }}</code>
        </div>

        <div class="h-px bg-border" />

        <div v-if="hasFileUpload" class="text-[11px] text-muted-foreground italic">
            File upload action — use the
            <span class="underline underline-offset-2 cursor-pointer text-foreground">API Docs</span>
            to upload via multipart/form-data.
        </div>
        <template v-else>
            <div class="flex flex-col gap-1.5">
                <label class="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Body</label>
                <textarea
                    :value="body"
                    rows="8"
                    spellcheck="false"
                    class="w-full rounded-md border border-border bg-muted/20 px-3 py-2.5 font-mono text-[11px] text-foreground resize-none outline-none focus:border-ring focus:ring-1 focus:ring-ring/30 transition-colors"
                    @input="emit('update:body', ($event.target as HTMLTextAreaElement).value)"
                />
            </div>
            <Button
                size="sm"
                class="gap-1.5 w-fit"
                :disabled="running"
                @click="emit('run')"
            >
                <RiLoader4Line v-if="running" class="size-3.5 animate-spin" />
                <RiPlayLine v-else class="size-3.5" />
                Run
            </Button>
            <ResultDisplay :result="result" />
        </template>
    </div>
</template>
