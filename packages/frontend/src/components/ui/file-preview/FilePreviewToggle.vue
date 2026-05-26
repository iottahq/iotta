<script setup lang="ts">
import { RiCodeLine } from "@remixicon/vue";
import { Button } from "@/components/ui/button";

defineProps<{
    show: boolean;
    filename: string;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
}>();
</script>

<template>
    <Button
        variant="ghost"
        size="sm"
        class="gap-1.5 -ml-2"
        :class="show ? 'text-primary' : 'text-muted-foreground'"
        @click="emit('update:show', !show)"
    >
        <RiCodeLine class="size-3.5" />
        {{ show ? `Hide ${filename}` : `View ${filename}` }}
    </Button>
</template>