<script setup lang="ts">
interface ActionEntry {
    name: string;
    label: string;
}

defineProps<{
    actions: ActionEntry[];
    selected: string | null;
}>();

const emit = defineEmits<{
    select: [name: string];
}>();
</script>

<template>
    <aside class="w-56 shrink-0 border-r border-border flex flex-col overflow-y-auto bg-sidebar">
        <div class="px-3 pt-4 pb-1.5">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">Actions</span>
        </div>

        <div v-if="actions.length === 0" class="px-3 py-4 text-[11px] text-muted-foreground/60">
            No actions defined
        </div>

        <button
            v-for="action in actions"
            :key="action.name"
            class="flex items-center gap-2 w-full px-3 py-2 text-left text-xs transition-colors rounded-none"
            :class="
                selected === action.name
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
            "
            @click="emit('select', action.name)"
        >
            <span class="truncate">{{ action.label }}</span>
        </button>
    </aside>
</template>
