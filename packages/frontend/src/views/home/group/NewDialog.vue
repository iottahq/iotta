<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    RiCheckLine,
    RiCloseLine,
    RiErrorWarningLine,
    RiLoader4Line,
} from "@remixicon/vue";

defineProps<{
    show: boolean;
    name: string;
    saving: boolean;
    error: string | null;
}>();

const emit = defineEmits<{
    "update:show": [v: boolean];
    "update:name": [v: string];
    create: [];
}>();
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show"
                class="fixed inset-0 z-50 flex items-center justify-center"
                @click.self="emit('update:show', false)"
            >
                <div
                    class="absolute inset-0 bg-black/50"
                    @click="emit('update:show', false)"
                />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
                >
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold">New group</h2>
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            @click="emit('update:show', false)"
                        >
                            <RiCloseLine class="size-3.5" />
                        </Button>
                    </div>
                    <div class="flex flex-col gap-3">
                        <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-medium">Name</label>
                            <Input
                                :model-value="name"
                                placeholder="e.g. 3D Printers"
                                @update:model-value="
                                    emit('update:name', $event as string)
                                "
                                @keydown.enter="emit('create')"
                                autofocus
                            />
                        </div>
                        <div
                            v-if="error"
                            class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2 text-xs"
                        >
                            <RiErrorWarningLine
                                class="size-3.5 shrink-0 mt-px"
                            />
                            {{ error }}
                        </div>
                        <div class="flex gap-2 justify-end mt-1">
                            <Button
                                variant="outline"
                                size="sm"
                                @click="emit('update:show', false)"
                                >Cancel</Button
                            >
                            <Button
                                size="sm"
                                :disabled="saving || !name.trim()"
                                @click="emit('create')"
                                class="gap-1.5"
                            >
                                <RiLoader4Line
                                    v-if="saving"
                                    class="size-3.5 animate-spin"
                                />
                                <RiCheckLine v-else class="size-3.5" />
                                Create
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
