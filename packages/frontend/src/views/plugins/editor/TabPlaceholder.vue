<script setup lang="ts">
defineProps<{
    label: string;
    issue: number;
}>();
</script>

<template>
    <div class="flex-1 flex items-center justify-center py-20 text-center px-6">
        <div>
            <p class="text-xs font-medium text-foreground">{{ label }}</p>
            <p class="text-xs text-muted-foreground mt-1">Coming soon · Issue #{{ issue }}</p>
        </div>
    </div>
</template>