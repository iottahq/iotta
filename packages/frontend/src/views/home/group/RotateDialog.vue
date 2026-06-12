<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { ApiToken } from "@/lib/api";
import { RiLoader4Line, RiRefreshLine } from "@remixicon/vue";

defineProps<{
    show: boolean;
    token: ApiToken | null;
    rotating: boolean;
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
                v-if="show && token"
                class="fixed inset-0 z-[60] flex items-center justify-center"
            >
                <div class="absolute inset-0 bg-black/50" @click="emit('cancel')" />
                <div class="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card shadow-xl px-6 py-5 mx-4 flex flex-col gap-4">

                    <div>
                        <h2 class="text-sm font-semibold">Rotate token?</h2>
                        <p class="text-xs text-muted-foreground mt-1">
                            The current value of
                            <span class="font-medium text-foreground">{{ token.name }}</span>
                            will be immediately invalidated. All integrations using it will lose access until updated.
                        </p>
                    </div>

                    <div class="flex gap-2 justify-end">
                        <Button variant="outline" size="sm" @click="emit('cancel')">
                            Cancel
                        </Button>
                        <Button
                            size="sm"
                            class="gap-1.5"
                            :disabled="rotating"
                            @click="emit('confirm')"
                        >
                            <RiLoader4Line v-if="rotating" class="size-3.5 animate-spin" />
                            <RiRefreshLine v-else class="size-3.5" />
                            Rotate
                        </Button>
                    </div>

                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
