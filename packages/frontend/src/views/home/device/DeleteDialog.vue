<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { RiDeleteBinLine, RiLoader4Line } from "@remixicon/vue";

defineProps<{
    show: boolean;
    deviceName: string;
    deleting: boolean;
}>();

const emit = defineEmits<{
    cancel: [];
    confirm: [];
}>();
</script>

<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="show"
                class="fixed inset-0 z-[60] flex items-center justify-center"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('cancel')" />
                <div
                    class="relative z-10 w-full max-w-xs rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4"
                >
                    <h2 class="text-sm font-semibold">Delete device?</h2>
                    <p class="text-xs text-muted-foreground mt-1.5">
                        <span class="font-medium text-foreground">{{ deviceName }}</span>
                        will be permanently deleted and unmounted.
                    </p>
                    <div class="flex gap-2 justify-end mt-4">
                        <Button variant="outline" size="sm" @click="emit('cancel')">
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            size="sm"
                            class="gap-1.5"
                            :disabled="deleting"
                            @click="emit('confirm')"
                        >
                            <RiLoader4Line v-if="deleting" class="size-3.5 animate-spin" />
                            <RiDeleteBinLine v-else class="size-3.5" />
                            Delete
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>