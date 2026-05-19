<script setup lang="ts">
defineProps<{
    title: string;
    rows: { label: string; value: string; mono?: boolean }[];
}>();
</script>

<template>
    <section class="flex flex-col gap-2">
        <h2 class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            {{ title }}
        </h2>
        <div class="rounded-lg border border-border overflow-hidden">
            <div
                v-for="row in rows"
                :key="row.label"
                class="flex items-start gap-3 px-4 py-2.5 border-b border-border/60 last:border-0"
            >
                <span class="text-[11px] text-muted-foreground w-28 shrink-0 pt-px">
                    {{ row.label }}
                </span>
                <span
                    class="text-[11px] text-foreground break-all"
                    :class="row.mono ? 'font-mono' : ''"
                >
                    {{ row.value || "—" }}
                </span>
            </div>
        </div>
    </section>
</template>
